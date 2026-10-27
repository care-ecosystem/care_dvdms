import logging

from care_dvdms.api.services.constants import (
    DVDMS_ACKNOWLEDGE_DETAILS_PATH,
    DVDMS_ACKNOWLEDGE_DETAILS_SUCCESS_STATUS,
    DVDMS_ACKNOWLEDGE_REQUEST_TYPE,
    DVDMS_ACKNOWLEDGE_SAVE_PATH,
    DVDMS_ACKNOWLEDGE_SAVE_SUCCESS_STATUS,
    DVDMS_DRUG_ITEM_CAT_NO,
)
from care_dvdms.api.services.dvdms_client import dvdms_get, dvdms_post_full

logger = logging.getLogger(__name__)


def fetch_acknowledge_details(issue_no, store_id):
    """Call the DVDMS acknowledge-details API. Returns the issued item list for an issue no/store."""
    return dvdms_get(
        DVDMS_ACKNOWLEDGE_DETAILS_PATH,
        DVDMS_ACKNOWLEDGE_DETAILS_SUCCESS_STATUS,
        params={"issueNo": issue_no, "storeId": store_id},
    )


def _build_item_pk(store_id, item):
    return "^".join([store_id, item.drug_id, item.drug_id, item.batch or "", DVDMS_DRUG_ITEM_CAT_NO, "0", "0"])


def build_acknowledge_save_payload(inward_record):
    """Build the DVDMS acknowledge-save request payload for an inward record."""
    institute_store = inward_record.outward_record.record_order.institute_store
    store_id = institute_store.eaushadhi_store_id
    issue_no = inward_record.eaushadhi_issue_no
    items = list(inward_record.items.select_related("item_delivery"))

    return {
        "strChk": [f"{store_id}@{issue_no}@{DVDMS_ACKNOWLEDGE_REQUEST_TYPE}@0${len(items)}"],
        "strAckStatus": "0",
        "strTransNo": issue_no,
        "strStoreId": store_id,
        "strHospitalCode": inward_record.institute.eaushadhi_institute_id,
        "strSeatId": inward_record.institute.eaushadhi_user_ref_id,
        "combo": f"{store_id}^0",
        "itemList": [
            {
                "strPk": _build_item_pk(store_id, item),
                "receivedQty": str(int(item.received_quantity)),
                "acceptedQty": str(int(item.item_delivery.quantity_accepted)),
                "breakageQty": str(int(item.item_delivery.quantity_damaged)),
                "shortageQty": str(int(item.item_delivery.quantity_short)),
            }
            for item in items
        ],
    }


def save_acknowledgement(payload):
    """Call the DVDMS acknowledge-save API. Returns (raw_response, http_status_code)."""
    return dvdms_post_full(DVDMS_ACKNOWLEDGE_SAVE_PATH, DVDMS_ACKNOWLEDGE_SAVE_SUCCESS_STATUS, payload)


def parse_item_pk_key(pk_key):
    """Parse an acknowledge-details itemList "pkKey" ("storeId^drugId^brandId^...") into (drug_id, brand_id)."""
    _, drug_id, brand_id = pk_key.split("^")[:3]
    return drug_id, brand_id


def _parse_issue_quantity(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("Could not parse DVDMS issued quantity value: %s", value)
        return 0


def merge_acknowledge_items(item_list):
    """Merge acknowledge-details itemList rows that share a (drug, brand, batch) identity.

    DVDMS returns one row per programme/stock lot, so a single issued drug can come back more
    than once with the same "pkKey" prefix. An inward item record is unique per ordered line, so
    those rows are collapsed into one and their issued quantities summed - the first row wins for
    the descriptive fields. Returns a list of (drug_id, brand_id, item) tuples.
    """
    merged = {}
    for item in item_list:
        drug_id, brand_id = parse_item_pk_key(item["pkKey"])
        quantity = _parse_issue_quantity(item.get("issueQyt"))
        key = (drug_id, brand_id, item.get("batchNo"))
        existing = merged.get(key)
        if existing is None:
            merged[key] = (drug_id, brand_id, {**item, "issueQyt": quantity})
        else:
            existing[2]["issueQyt"] += quantity
            logger.info(
                "merge_acknowledge_items: merged pkKey=%s into pkKey=%s, issued quantity now %s",
                item["pkKey"],
                existing[2]["pkKey"],
                existing[2]["issueQyt"],
            )
    return list(merged.values())

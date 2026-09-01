from care_dvdms.api.services.constants import (
    DVDMS_ACKNOWLEDGE_DETAILS_PATH,
    DVDMS_ACKNOWLEDGE_DETAILS_SUCCESS_STATUS,
    DVDMS_ACKNOWLEDGE_PENDING_LIST_PATH,
    DVDMS_ACKNOWLEDGE_PENDING_LIST_SUCCESS_STATUS,
    DVDMS_ACKNOWLEDGE_REQUEST_TYPE,
    DVDMS_ACKNOWLEDGE_SAVE_PATH,
    DVDMS_ACKNOWLEDGE_SAVE_SUCCESS_STATUS,
    DVDMS_DRUG_ITEM_CAT_NO,
)
from care_dvdms.api.services.dvdms_client import dvdms_get, dvdms_post_full

# Record shape: storeId@issueNo@type@typeStatus^_^storeName^issueNo^date^indentNoAndDate^_


def fetch_acknowledge_pending_list(to_store_id, indent_no=None):
    """Call the DVDMS acknowledge-pending list API for a store. Returns raw delimited record strings."""
    params = {"toStoreId": to_store_id}
    if indent_no is not None:
        params["indentNo"] = indent_no
    return dvdms_get(
        DVDMS_ACKNOWLEDGE_PENDING_LIST_PATH,
        DVDMS_ACKNOWLEDGE_PENDING_LIST_SUCCESS_STATUS,
        params=params,
    )


def parse_acknowledge_pending_record(raw):
    """Parse one acknowledge-pending record string into the fields the sync flow needs."""
    _store_id, issue_no, _rest = raw.split("@", 2)
    return {"issue_no": issue_no}


def fetch_acknowledge_pending_records(to_store_id, indent_no=None):
    """Fetch and parse the acknowledge-pending list for a store."""
    return [parse_acknowledge_pending_record(raw) for raw in fetch_acknowledge_pending_list(to_store_id, indent_no)]


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

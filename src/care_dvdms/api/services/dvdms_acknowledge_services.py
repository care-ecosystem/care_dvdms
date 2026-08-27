from care_dvdms.api.services.constants import (
    DVDMS_ACKNOWLEDGE_DETAILS_PATH,
    DVDMS_ACKNOWLEDGE_DETAILS_SUCCESS_STATUS,
    DVDMS_ACKNOWLEDGE_PENDING_LIST_PATH,
    DVDMS_ACKNOWLEDGE_PENDING_LIST_SUCCESS_STATUS,
    DVDMS_ISSUE_SAVE_PATH,
    DVDMS_ISSUE_SAVE_SUCCESS_STATUS,
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


def save_issue_acknowledgement(payload):
    """Call the DVDMS issue-save (acknowledge) API. Returns (raw_response, http_status_code)."""
    return dvdms_post_full(DVDMS_ISSUE_SAVE_PATH, DVDMS_ISSUE_SAVE_SUCCESS_STATUS, payload)


def parse_item_pk_key(pk_key):
    """Parse an acknowledge-details itemList "pkKey" ("storeId^drugId^brandId^...") into (drug_id, brand_id)."""
    _, drug_id, brand_id = pk_key.split("^")[:3]
    return drug_id, brand_id

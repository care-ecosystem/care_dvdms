import re

from care_dvdms.api.services.constants import (
    DVDMS_ACKNOWLEDGE_PENDING_LIST_PATH,
    DVDMS_ACKNOWLEDGE_PENDING_LIST_SUCCESS_STATUS,
)
from care_dvdms.api.services.dvdms_client import dvdms_get

# Record shape: storeId@issueNo@type@typeStatus^_^storeName^issueNo^date^indentNoAndDate^_
# indentNoAndDate has no delimiter between the indent number and the trailing "-Mon-YYYY".
INDENT_NO_PATTERN = re.compile(r"(\d+)-[A-Za-z]{3}-\d{4}$")


def fetch_acknowledge_pending_list(to_store_id):
    """Call the DVDMS acknowledge-pending list API for a store. Returns raw delimited record strings."""
    return dvdms_get(
        DVDMS_ACKNOWLEDGE_PENDING_LIST_PATH,
        DVDMS_ACKNOWLEDGE_PENDING_LIST_SUCCESS_STATUS,
        params={"toStoreId": to_store_id},
    )


def parse_acknowledge_pending_record(raw):
    """Parse one acknowledge-pending record string into named fields."""
    store_id, issue_no, type_, rest = raw.split("@", 3)
    type_status, _, store_name, _, date, indent_no_and_date, _ = rest.split("^")
    match = INDENT_NO_PATTERN.search(indent_no_and_date.strip())
    return {
        "store_id": store_id,
        "issue_no": issue_no,
        "type": type_,
        "type_status": type_status,
        "store_name": store_name,
        "date": date,
        "indent_no": match.group(1) if match else None,
    }


def fetch_acknowledge_pending_records(to_store_id):
    """Fetch and parse the acknowledge-pending list for a store."""
    return [parse_acknowledge_pending_record(raw) for raw in fetch_acknowledge_pending_list(to_store_id)]

import re

from care_dvdms.api.services.constants import (
    DVDMS_DRUG_ITEM_CAT_NO,
    DVDMS_INDENT_NO_PATTERN,
    DVDMS_SAVE_INDENT_PATH,
    DVDMS_SAVE_INDENT_SUCCESS_STATUS,
    DVDMS_TRACK_INDENT_PATH,
    DVDMS_TRACK_INDENT_SUCCESS_STATUS,
    DVDMS_URGENT_PRIORITIES,
)
from care_dvdms.api.services.dvdms_client import dvdms_get_full, dvdms_post_full
from care_dvdms.utils.financial_year import current_financial_year_range

INDENT_NO_PATTERN = re.compile(DVDMS_INDENT_NO_PATTERN, re.IGNORECASE)


def _build_selected_param_values(record_order):
    # Rate/InHandQty/Availableqty/ReorderLevel aren't tracked in our models yet, sent as 0.
    values = []
    for item_order in record_order.item_orders.select_related("drug", "supply_request"):
        drug = item_order.drug
        quantity = int(item_order.supply_request.quantity or 0)
        values.append(
            "#".join(
                str(v)
                for v in [
                    drug.drug_id,
                    drug.brand_id,
                    quantity,
                    drug.group_id,
                    drug.sub_group_id,
                    0,  # Rate
                    drug.unit_id,  # RateUnitId
                    drug.unit_id,  # IndentQtyUnitid
                    0,  # InHandQty
                    drug.unit_id,  # InhandQtyUnitId
                    0,  # Availableqty
                    drug.unit_id,  # IssueqtyUnitid
                    0,  # ReorderLevel
                ]
            )
        )
    return values


def build_save_indent_payload(record_order):
    """Build the DVDMS save-indent request payload for a record order."""
    financial_year = current_financial_year_range()
    urgent_flag = 1 if record_order.order.priority in DVDMS_URGENT_PRIORITIES else 0

    return {
        "isModify": 0,
        "hststrFinancialYear": financial_year,
        "hstnumStoreId": record_order.institute_store.eaushadhi_store_id,
        "hstnumCareIndentNo": record_order.care_indent_no,
        "hstnumTostoreId": record_order.institute_supplier.eaushadhi_warehouse_id,
        "sstnumItemCatNo": DVDMS_DRUG_ITEM_CAT_NO,
        "hststrIndentPeriodValue": financial_year,
        "gstrRemarks": str(record_order.external_id),
        "hstnumUrgentFlag": urgent_flag,
        "draftFlag": 0,
        "hospitalCode": record_order.institute.eaushadhi_institute_id,
        "strSelectedParamValues": _build_selected_param_values(record_order),
    }


def save_indent(payload):
    """Call the DVDMS save-indent API. Returns (indent_no, raw_response, http_status_code)."""
    response, http_status_code = dvdms_post_full(DVDMS_SAVE_INDENT_PATH, DVDMS_SAVE_INDENT_SUCCESS_STATUS, payload)
    match = INDENT_NO_PATTERN.search(response.get("message", ""))
    indent_no = match.group(1) if match else None
    return indent_no, response, http_status_code


def build_track_indent_params(outward_record):
    """Build the DVDMS track-indent query params for an outward record."""
    return {
        "storeId": outward_record.record_order.institute_store.eaushadhi_store_id,
        "indentNo": outward_record.eaushadhi_indent_no,
    }


def track_indent(params):
    """Call the DVDMS track-indent API. Returns (raw_response, http_status_code)."""
    return dvdms_get_full(DVDMS_TRACK_INDENT_PATH, DVDMS_TRACK_INDENT_SUCCESS_STATUS, params=params)

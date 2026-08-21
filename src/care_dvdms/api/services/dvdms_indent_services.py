import datetime
import re

from care_dvdms.api.services.constants import (
    DVDMS_DRUG_ITEM_CAT_NO,
    DVDMS_INDENT_NO_PATTERN,
    DVDMS_SAVE_INDENT_PATH,
    DVDMS_URGENT_PRIORITIES,
)
from care_dvdms.api.services.dvdms_client import dvdms_post_full

INDENT_NO_PATTERN = re.compile(DVDMS_INDENT_NO_PATTERN, re.IGNORECASE)


def _current_financial_year():
    today = datetime.date.today()
    start_year = today.year if today.month >= 4 else today.year - 1
    return f"{start_year}-{start_year + 1}"


def _build_selected_param_values(record_order):
    """
    Build the "#"-joined per-item strings DVDMS expects:
    ItemId#ItembrandId#ReqQty#GroupId#SubGroupId#Rate#RateUnitId#IndentQtyUnitid#
    InHandQty#InhandQtyUnitId#Availableqty#IssueqtyUnitid#ReorderLevel

    Rate/InHandQty/Availableqty/ReorderLevel aren't tracked anywhere in
    our models yet (they're live DVDMS stock/pricing data) - sent as 0 for now.
    """
    values = []
    for item_order in record_order.item_orders.select_related("drug", "supply_request"):
        drug = item_order.drug
        quantity = item_order.supply_request.quantity or 0
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
    financial_year = _current_financial_year()
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
    response, http_status_code = dvdms_post_full(DVDMS_SAVE_INDENT_PATH, payload)
    match = INDENT_NO_PATTERN.search(response.get("message", ""))
    indent_no = match.group(1) if match else None
    return indent_no, response, http_status_code


def track_indent(institute, outward_record, user):
    """Track an indent's status in DVDMS for an outward record."""

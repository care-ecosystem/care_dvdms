import logging
from datetime import datetime

from care_dvdms.api.services.constants import (
    DVDMS_ACKNOWLEDGE_DETAILS_PATH,
    DVDMS_ACKNOWLEDGE_DETAILS_SUCCESS_STATUS,
    DVDMS_ACKNOWLEDGE_SAVE_PATH,
    DVDMS_ACKNOWLEDGE_SAVE_SUCCESS_STATUS,
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


def build_acknowledge_save_payload(inward_record):
    """Build the DVDMS acknowledge-save request payload for an inward record from its acknowledge details."""
    details = fetch_acknowledge_details(
        inward_record.eaushadhi_issue_no,
        inward_record.outward_record.record_order.institute_supplier.eaushadhi_warehouse_id,
    )
    items_by_key = {
        (item.drug_id, item.brand_id, item.batch, item.expiry_date, item.manufacturer): item
        for item in inward_record.items.select_related("item_delivery")
    }
    trans_no = str(details["tranceNo"])
    store_id = str(details["storeId"])
    to_store_id = str(details["toStoreId"])
    req_type_id = str(details["reqTypeId"])
    combo_val = str(details["toStoreName"])
    remarks = inward_record.record_delivery.delivery_order.note or ""

    lines = []
    for key, group in group_issue_lines(details.get("itemList", [])).items():
        delivery = items_by_key[key].item_delivery
        accepted = int(delivery.quantity_accepted)
        damaged = int(delivery.quantity_damaged)
        short = int(delivery.quantity_short)
        # merged inward item: fill lines in order, last line takes the remainder
        for index, detail in enumerate(group):
            issue = int(detail.get("issueQyt") or 0)
            if index == len(group) - 1:
                line_accepted, line_damaged, line_short = accepted, damaged, short
            else:
                line_accepted = min(issue, accepted)
                line_damaged = min(issue - line_accepted, damaged)
                line_short = min(issue - line_accepted - line_damaged, short)
            accepted -= line_accepted
            damaged -= line_damaged
            short -= line_short
            lines.append(
                {
                    "detail": detail,
                    "issue": issue,
                    "received": line_accepted + line_damaged,
                    "accepted": line_accepted,
                    "damaged": line_damaged,
                    "balance": line_short,
                }
            )

    return {
        "strChk": [f"{store_id}@{trans_no}@{req_type_id}@0${len(lines)}"],
        "strAckStatus": "0",
        "strTransNo": trans_no,
        "strStoreId": store_id,
        "strRequestTypeId": req_type_id,
        "strRequestMode": "0",
        "strReturnStatus": "0",
        "strReqTypeId": req_type_id,
        "strAckStsFlag": "1",
        "strSaveFlg": "0",
        "strComboVal": combo_val,
        "combo": f"{to_store_id}^0",
        "strPk": [line["detail"]["pkKey"] for line in lines],
        "strIssueQty": [line["issue"] for line in lines],
        "strHospitalCode": inward_record.institute.eaushadhi_institute_id,
        "strRemarks": remarks,
        "strTotBkgQty": [line["damaged"] for line in lines],
        "strBkgQty": [line["damaged"] for line in lines],
        "strStockRegNo": [0 for _ in lines],
        "strToBeAckQty": [line["accepted"] for line in lines],
        "strSeatId": inward_record.institute.eaushadhi_user_ref_id,
        "strHidVal": (
            f"Store^{trans_no}^Date^Drug^Type^{combo_val}^{store_id}^{to_store_id}"
            f"^{details['itameCatNo']}^00^Date^{req_type_id}^{remarks.replace('^', ' ')}^User^UserType"
        ),
        "strReceivedQty": [line["received"] for line in lines],
        "strBalanceQty": [line["balance"] for line in lines],
        "itemList": [
            {
                "itemName": line["detail"].get("itemName"),
                "batchNo": line["detail"].get("batchNo"),
                "expiryDate": line["detail"].get("expiryDate"),
                "issueQyt": str(line["issue"]),
                "recQyt": str(line["received"]),
                "bkgQyt": str(line["damaged"]),
                "ackQyt": str(line["accepted"]),
                "pkKey": line["detail"]["pkKey"],
                "prigrammeName": line["detail"].get("prigrammeName") or "",
                "mfgName": line["detail"].get("mfgName") or "",
                "strStockRegNo": "0",
                "issueQtyUnitName": line["detail"].get("issueQtyUnitName") or "Unit",
            }
            for line in lines
        ],
    }


def save_acknowledgement(payload):
    """Call the DVDMS acknowledge-save API. Returns (raw_response, http_status_code)."""
    return dvdms_post_full(DVDMS_ACKNOWLEDGE_SAVE_PATH, DVDMS_ACKNOWLEDGE_SAVE_SUCCESS_STATUS, payload)


def parse_item_pk_key(pk_key):
    """Parse an acknowledge-details itemList "pkKey" ("storeId^drugId^brandId^...") into (drug_id, brand_id)."""
    _, drug_id, brand_id = pk_key.split("^")[:3]
    return drug_id, brand_id


def parse_dvdms_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d-%b-%Y").date()
    except ValueError:
        logger.warning("Could not parse DVDMS date value: %s", value)
        return None


def issue_line_key(line):
    """Identity of an acknowledge-details itemList line: (drug_id, brand_id, batch, expiry_date, manufacturer)."""
    return (
        *parse_item_pk_key(line["pkKey"]),
        line.get("batchNo"),
        parse_dvdms_date(line.get("expiryDate")),
        line.get("mfgName"),
    )


def group_issue_lines(item_list):
    """Group itemList lines by issue_line_key; each group is one inward item."""
    groups = {}
    for line in item_list:
        groups.setdefault(issue_line_key(line), []).append(line)
    return groups

from care_dvdms.api.services.constants import (
    DVDMS_ACKNOWLEDGE_DETAILS_PATH,
    DVDMS_ACKNOWLEDGE_DETAILS_SUCCESS_STATUS,
    DVDMS_ACKNOWLEDGE_SAVE_PATH,
    DVDMS_ACKNOWLEDGE_SAVE_SUCCESS_STATUS,
)
from care_dvdms.api.services.dvdms_client import dvdms_get, dvdms_post_full


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
    # An issued line is matched to its record by lot - drug, brand, batch and manufacturer
    items_by_lot = {
        (item.drug_id, item.brand_id, item.batch, item.manufacturer): item
        for item in inward_record.items.select_related("item_delivery")
    }
    trans_no = str(details["tranceNo"])
    store_id = str(details["storeId"])
    to_store_id = str(details["toStoreId"])
    req_type_id = str(details["reqTypeId"])
    combo_val = str(details["toStoreName"])
    remarks = inward_record.record_delivery.delivery_order.note or ""

    lines = []
    matched_items = set()
    for detail in details.get("itemList", []):
        item = items_by_lot.get((*parse_item_pk_key(detail["pkKey"]), detail.get("batchNo"), detail.get("mfgName")))
        if item is None:
            raise ValueError(
                f"No inward item record matches pkKey {detail['pkKey']} for issue "
                f"{inward_record.eaushadhi_issue_no}; re-run the inward prefill for this record"
            )
        if item.pk in matched_items:
            raise ValueError(
                f"Issued line {detail['pkKey']} for issue {inward_record.eaushadhi_issue_no} matches an "
                f"inward item record already used by another line; re-run the inward prefill for this record"
            )
        matched_items.add(item.pk)
        delivery = item.item_delivery
        accepted = int(delivery.quantity_accepted)
        damaged = int(delivery.quantity_damaged)
        lines.append(
            {
                "detail": detail,
                "issue": int(item.received_quantity),
                "received": accepted + damaged,
                "accepted": accepted,
                "damaged": damaged,
                "balance": int(delivery.quantity_short),
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

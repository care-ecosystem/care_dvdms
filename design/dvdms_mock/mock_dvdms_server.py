"""Mock DVDMS server. Serves fixed lookup fixtures + a stateful indent flow.

Run: python3 mock_dvdms_server.py [port]
Point DVDMS_API_ENDPOINT at http://localhost:<port> in your local .env.
"""

import json
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

FIXTURES_DIR = Path(__file__).parent / "fixtures"

STATIC_GET_ROUTES = {
    "/groupMst/list": "groupMst_list.json",
    "/subGroupMst/list": "subGroupMst_list.json",
    "/unitMst/list": "unitMst_list.json",
    "/drug/list": "drugMst_list.json",
    "/getStoreDetailsForCare/list": "store_list.json",
}

STORE_NAMES_BY_ID = {
    str(store["hstnumStoreId"]): store["hststrStoreName"]
    for store in json.loads((FIXTURES_DIR / "store_list.json").read_text())["data"]
}

DRUG_NAMES_BY_ID = {
    str(drug["hstnum_item_id"]): drug["hststr_item_name"]
    for drug in json.loads((FIXTURES_DIR / "drugMst_list.json").read_text())["data"]
}

SHELFLIFE_MONTHS_BY_DRUG_ID = {
    str(drug["hstnum_item_id"]): drug.get("hstnum_shelflife") or 12
    for drug in json.loads((FIXTURES_DIR / "drugMst_list.json").read_text())["data"]
}

ACKNOWLEDGE_REQUEST_TYPE = "31"  # matches DVDMS_ACKNOWLEDGE_REQUEST_TYPE in care_dvdms constants.py

# ponytail: in-memory state, lost on restart - fine for a local mock, add persistence if that matters
_lock = threading.Lock()
_seq = 0
_issue_seq = 0
_ack_seq = 0
_indents = {}  # indent_no -> {"hits", "requesting_store_id", "issuing_store_id", "issue_no", "items"}
_issues = {}  # issue_no -> indent_no


def _parse_selected_param_values(payload):
    items = []
    for raw in payload.get("strSelectedParamValues") or []:
        drug_id, brand_id, quantity = raw.split("#")[:3]
        items.append({"drug_id": drug_id, "brand_id": brand_id, "quantity": quantity})
    return items


def _next_indent_no():
    global _seq
    with _lock:
        _seq += 1
        seq = _seq
    return f"1017{datetime.now(tz=timezone.utc):%y%m}{seq:04d}"


def _next_issue_no():
    global _issue_seq
    with _lock:
        _issue_seq += 1
        seq = _issue_seq
    return f"1032{datetime.now(tz=timezone.utc):%y%m}{seq:06d}"


def _save_indent(payload):
    indent_no = _next_indent_no()
    _indents[indent_no] = {
        "hits": 0,
        "requesting_store_id": payload.get("hstnumStoreId"),
        "issuing_store_id": payload.get("hstnumTostoreId"),
        "items": _parse_selected_param_values(payload),
    }
    return {
        "message": f"Indent request generate successful. Intent NO: {indent_no}",
        "status": 200,
    }


def _track_indent(indent_no):
    record = _indents.get(indent_no)
    if record is None:
        return {"message": "Indent not found", "status": 0}

    record["hits"] += 1
    indent_status = "Issue in Process" if record["hits"] == 1 else "Issued"
    if indent_status == "Issued" and "issue_no" not in record:
        issue_no = _next_issue_no()
        record["issue_no"] = issue_no
        _issues[issue_no] = indent_no
    requesting_store_id = record["requesting_store_id"]
    issuing_store_id = record["issuing_store_id"]

    return {
        "message": "Ok",
        "status": 1,
        "data": {
            "indentNo": indent_no,
            "requestingStoreId": requesting_store_id,
            "issuingStoreId": issuing_store_id,
            "indentDate": f"{datetime.now(tz=timezone.utc):%d-%b-%Y}",
            "indentingStore": STORE_NAMES_BY_ID.get(str(requesting_store_id), "Unknown"),
            "issuingStore": STORE_NAMES_BY_ID.get(str(issuing_store_id), "Unknown"),
            "indentStatus": indent_status,
        },
    }


def _acknowledge_pending_list(to_store_id, indent_no):
    record = _indents.get(indent_no)
    if record is None or "issue_no" not in record:
        return {"message": "Ok", "status": 1, "data": []}

    issue_no = record["issue_no"]
    date = f"{datetime.now(tz=timezone.utc):%d-%b-%Y}"
    line = (
        f"{to_store_id}@{issue_no}@{ACKNOWLEDGE_REQUEST_TYPE}@0"
        f"^Issue To Store^Mock Store^{issue_no}^{date}^{indent_no}{date}^0"
    )
    return {"message": "Ok", "status": 1, "data": [line]}


def _next_ack_no():
    global _ack_seq
    with _lock:
        _ack_seq += 1
        seq = _ack_seq
    return f"ACK{datetime.now(tz=timezone.utc):%Y}{seq:05d}"


def _save_acknowledgement():
    return {
        "message": "Record Acknowledge Successfully!",
        "status": 200,
        "strAckNo": _next_ack_no(),
    }


def _expiry_date(drug_id):
    shelflife_months = SHELFLIFE_MONTHS_BY_DRUG_ID.get(str(drug_id), 12)
    expiry = datetime.now(tz=timezone.utc) + timedelta(days=shelflife_months * 30)
    return f"{expiry:%d-%b-%Y}"


def _acknowledge_details(issue_no, store_id):
    indent_no = _issues.get(issue_no)
    record = _indents.get(indent_no) if indent_no else None
    if record is None:
        return {"message": "Ok", "status": 1, "data": {}}

    requesting_store_id = record["requesting_store_id"]
    issuing_store_id = record["issuing_store_id"]
    date = f"{datetime.now(tz=timezone.utc):%d-%b-%Y}"

    item_list = [
        {
            "itemName": DRUG_NAMES_BY_ID.get(item["drug_id"], "Unknown Drug"),
            "batchNo": "MOCK-BATCH",
            "expiryDate": _expiry_date(item["drug_id"]),
            "issueQyt": item["quantity"],
            "recQyt": "0",
            "bkgQyt": "0",
            "ackQyt": item["quantity"],
            "pkKey": f"{requesting_store_id}^{item['drug_id']}^{item['brand_id']}^MOCK-BATCH^10^0^0",
            "prigrammeName": "State Plan",
            "mfgName": "Mock Pharma",
            "issueQtyUnitName": "Unit",
        }
        for item in record["items"]
    ]

    return {
        "message": "Ok",
        "status": 1,
        "data": {
            "toStoreName": STORE_NAMES_BY_ID.get(str(issuing_store_id), "Unknown"),
            "tranceNo": issue_no,
            "tranceDate": date,
            "itameCatNo": "10",
            "reqTypeName": "Issue To Store",
            "storeName": STORE_NAMES_BY_ID.get(str(requesting_store_id), "Unknown"),
            "storeId": str(requesting_store_id),
            "toStoreId": str(issuing_store_id),
            "itameCateName": "Drug",
            "reqNo": "00",
            "reqDate": date,
            "reqTypeId": ACKNOWLEDGE_REQUEST_TYPE,
            "remarks": "ok",
            "issuedBy": "Mock Store Keeper",
            "itemList": item_list,
        },
    }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, body, status=200):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in STATIC_GET_ROUTES:
            fixture_path = FIXTURES_DIR / STATIC_GET_ROUTES[parsed.path]
            self._send_json(json.loads(fixture_path.read_text()))
            return

        if parsed.path == "/getIndentStatus":
            indent_no = parse_qs(parsed.query).get("indentNo", [None])[0]
            self._send_json(_track_indent(indent_no))
            return

        if parsed.path == "/dwh/acknowledge-pandding/list":
            qs = parse_qs(parsed.query)
            to_store_id = qs.get("toStoreId", [None])[0]
            indent_no = qs.get("indentNo", [None])[0]
            self._send_json(_acknowledge_pending_list(to_store_id, indent_no))
            return

        if parsed.path == "/dwh/acknowladge/datails":
            qs = parse_qs(parsed.query)
            issue_no = qs.get("issueNo", [None])[0]
            store_id = qs.get("storeId", [None])[0]
            self._send_json(_acknowledge_details(issue_no, store_id))
            return

        self._send_json({"message": "Not found", "status": 0}, status=404)

    def do_POST(self):
        if self.path == "/save/indent":
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            self._send_json(_save_indent(payload))
            return

        if self.path == "/dwh/acknowledge/save":
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            self._send_json(_save_acknowledgement())
            return

        self._send_json({"message": "Not found", "status": 0}, status=404)

    def log_message(self, format_, *args):
        print(f"[mock-dvdms] {self.address_string()} {format_ % args}")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8600
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[mock-dvdms] listening on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

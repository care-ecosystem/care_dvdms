import logging
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import cache
from typing import Annotated, get_args

import requests
from pydantic import AfterValidator, BaseModel, ConfigDict, TypeAdapter, ValidationError, model_validator
from pydantic_core import PydanticCustomError

from care_dvdms.api.services.constants import DVDMS_DRUG_ITEM_CAT_NO, DVDMS_INDENT_NO_PATTERN

logger = logging.getLogger(__name__)


class DVDMSResponseChangedError(requests.exceptions.RequestException):
    """DVDMS changed a field our code uses. The call is stopped so the change is reviewed before the
    plugin works with it."""


class Used:
    """Marks a field our code reads. A change to it blocks the call; a change to any other field is
    only logged as a warning."""

    def __class_getitem__(cls, item):
        return Annotated[item, cls]


class DVDMSExactSchema(BaseModel):
    # strict: no type coercion, so "998", 998.0 or true in place of 998 is a change, as is any unknown key.
    model_config = ConfigDict(extra="forbid", strict=True)


class DVDMSRejectionResponse(DVDMSExactSchema):
    # No rejection body has been sampled yet, so unknown keys are not reported.
    model_config = ConfigDict(extra="allow")

    status: Used[int]
    message: Used[str]


class DVDMSSuccessResponse(DVDMSExactSchema):
    status: Used[int]
    message: str


class DVDMSPostResponse(DVDMSExactSchema):
    """DVDMS has already saved by the time a POST answers, so a change is only logged as an error and the
    call continues - unless it is in a value we extract for further processing (marked Used)."""

    status: int
    message: str


class DVDMSGroup(DVDMSExactSchema):
    gnumHospitalCode: Used[int]
    hstnumGroupId: Used[int]
    hststrGroupName: Used[str]
    gstrRemarks: str
    gdtEffectiveFrm: str
    gdtEntryDate: str
    gnumSeatid: Used[int]
    gnumIsvalid: int
    sstnumItemCatNo: int


class DVDMSGroupListResponse(DVDMSSuccessResponse):
    data: Used[list[DVDMSGroup]]


class DVDMSSubgroup(DVDMSExactSchema):
    gnumHospitalCode: Used[int]
    hstnumSubgroupId: Used[int]
    hstnumGroupId: Used[int]
    hststrSubgroupName: Used[str]
    gdtEffectiveFrm: str
    gstrRemarks: str
    gdtEntryDate: str
    gnumSeatid: Used[int]
    gnumIsvalid: int


class DVDMSSubgroupListResponse(DVDMSSuccessResponse):
    data: Used[list[DVDMSSubgroup]]


class DVDMSUnit(DVDMSExactSchema):
    gnumUnitId: Used[int]
    gstrUnitName: Used[str]
    gnumModuleId: int
    gnumBaseunitId: int
    gdtEffectiveFrm: str
    gnumLstmodSeatid: int
    gdtEntryDate: str
    gnumSeatid: int
    gnumIsvalid: int
    gnumUnitLevel: int
    gnumHospitalCode: Used[int]
    gnumDecimalAllowed: int
    gnumBaseUnitvalue: Used[float]  # strict float: int or float, not str / null / bool


class DVDMSUnitListResponse(DVDMSSuccessResponse):
    data: Used[list[DVDMSUnit]]


WARN_ONLY = "dvdms_warn_only"  # error type that is only logged as a warning, even on a used field


def _is_drug_category(category):
    # The full list may hold other categories; the drug lookup keeps only this one.
    if category != DVDMS_DRUG_ITEM_CAT_NO:
        raise PydanticCustomError(WARN_ONLY, f"not '{DVDMS_DRUG_ITEM_CAT_NO}' (not a drug item)")
    return category


class DVDMSDrug(DVDMSExactSchema):
    hstnum_item_id: Used[int]
    gnum_hospital_code: Used[int]
    hstnum_group_id: Used[int]
    hstnum_subgroup_id: Used[int]
    sstnum_item_cat_no: Used[Annotated[str, AfterValidator(_is_drug_category)]]
    hststr_item_name: Used[str]
    hstnum_batchno_req: int
    hstnum_expirydate_req: int
    gnum_inventory_unitid: Used[int]
    gdt_effective_frm: str
    gnum_lstmod_seatid: int
    gdt_entry_date: str
    gnum_seatid: Used[int]
    gnum_isvalid: int
    hststr_cpa_code: str
    hstnum_itembrand_id: Used[int]


class DVDMSDrugListResponse(DVDMSSuccessResponse):
    data: Used[list[DVDMSDrug]]


class DVDMSStore(DVDMSExactSchema):
    hstnumStoreId: Used[int]
    hststrStoreName: Used[str]
    sststrTypeName: Used[str]
    gnumSeatid: Used[int]
    hststrLocation: str
    sstnumDwhTypeId: int
    hstnumParentStoreId: Used[int]
    hststrParentStoreName: Used[str]
    parentTypeName: str


class DVDMSStoreListResponse(DVDMSSuccessResponse):
    data: Used[list[DVDMSStore]]


INDENT_NO_PATTERN = re.compile(DVDMS_INDENT_NO_PATTERN, re.IGNORECASE)


def _contains_indent_no(message):
    if not INDENT_NO_PATTERN.search(message):
        raise ValueError("should contain the indent number as 'Intent NO: <number>'")
    return message


class DVDMSSaveIndentResponse(DVDMSPostResponse):
    message: Used[Annotated[str, AfterValidator(_contains_indent_no)]]


class DVDMSIndentStatus(DVDMSExactSchema):
    indentNo: int
    requestingStoreId: int
    issuingStoreId: int
    indentDate: str
    indentingStore: str
    issuingStore: str
    indentStatus: Used[str]
    issueNo: Used[str] = None  # only sent once the indent is issued

    @model_validator(mode="after")
    def _issued_has_issue_no(self):
        if self.indentStatus == "Issued" and not self.issueNo:
            raise ValueError("issueNo is required when indentStatus is Issued")
        return self


class DVDMSIndentStatusResponse(DVDMSSuccessResponse):
    data: Used[DVDMSIndentStatus]


# pkKey = storeId^itemId^brandId^batchNo^?^programId^? (parts 5 and 7 are not described).
# parse_item_pk_key reads the item and brand ids, and the whole key is sent back to DVDMS as strPk.
PK_KEY_PARTS = 7
PK_ITEM_ID, PK_BRAND_ID, PK_PROGRAM_ID = 1, 2, 5


def _is_pk_key(pk_key):
    parts = pk_key.split("^")
    if len(parts) != PK_KEY_PARTS or not all(
        parts[i].isascii() and parts[i].isdigit() for i in (PK_ITEM_ID, PK_BRAND_ID, PK_PROGRAM_ID)
    ):
        raise ValueError(
            "should be storeId^itemId^brandId^batchNo^?^programId^? with numeric item, brand and program ids"
        )
    return pk_key


def _is_decimal(quantity):
    try:
        Decimal(quantity)
    except InvalidOperation:
        raise ValueError("should be a number") from None
    return quantity


def _is_dvdms_date(value):
    try:
        datetime.strptime(value, "%d-%b-%Y")
    except ValueError:
        raise ValueError("should be a date like 31-Oct-2027") from None
    return value


class DVDMSIssuedItem(DVDMSExactSchema):
    itemName: Used[str]
    batchNo: Used[str]
    expiryDate: Used[Annotated[str, AfterValidator(_is_dvdms_date)]]
    issueQyt: Used[Annotated[str, AfterValidator(_is_decimal)]]
    recQyt: str
    bkgQyt: str
    ackQyt: str
    pkKey: Used[Annotated[str, AfterValidator(_is_pk_key)]]
    prigrammeName: Used[str]
    mfgName: Used[str]
    issueQtyUnitName: Used[str]


class DVDMSAcknowledgeDetails(DVDMSExactSchema):
    toStoreName: Used[str]
    tranceNo: Used[str]
    tranceDate: str
    itameCatNo: Used[str]
    reqTypeName: str
    storeName: str
    storeId: Used[str]
    toStoreId: Used[str]
    itameCateName: str
    reqNo: str
    reqDate: str
    reqTypeId: Used[str]
    remarks: str
    issuedBy: str
    itemList: Used[list[DVDMSIssuedItem]]


class DVDMSAcknowledgeDetailsResponse(DVDMSSuccessResponse):
    data: Used[DVDMSAcknowledgeDetails]


class DVDMSAcknowledgedItem(DVDMSExactSchema):
    itemName: str
    batchNo: str
    expiryDate: str
    issueQyt: str
    recQyt: str
    bkgQyt: str
    ackQyt: str
    pkKey: str
    prigrammeName: str
    mfgName: str
    issueQtyUnitName: str
    strStockRegNo: str


class DVDMSAcknowledgeSaveData(DVDMSExactSchema):
    strErrMsg: str
    strWarningMsg: str
    strNormalMsg: str
    strComboVal: str
    strHospitalCode: str
    strViewFlg: str
    strSeatId: str
    strRemarks: str
    strRequestType: str
    strPath: str
    strPk: list[str]
    strToBeAckQty: list[str]
    strChk: list[str]
    strAcknowledgeDetails: str
    strItemDetails: str
    strAckDtls: str
    strAckStatus: str
    strReturnStatus: str
    strTransNo: str
    strStoreId: str
    cnt_page: str
    strBkgQty: list[str]
    strIssueQty: list[str]
    strReceivedQty: list[str]
    strHidVal: str
    strViewMode: str
    strReqTypeId: str
    strRequestMode: str
    strStockRegNo: list[str]
    strBalanceQty: list[str]
    strTmpTransNo: str
    strStoreName: str
    strIndentNo: str
    strIndentDate: str
    strReturnReqNo: str
    strReturnCost: str
    strHtmlCode: str
    strIssueNo: str
    strAckStsFlag: str
    strPartialAckDtl: str
    strAckNoAckDate: str
    strReqNoReqDate: str
    strIssuedByName: str
    strIssueNoIssueDate: str
    strOrderNoOrderDate: str
    strReceByName: str
    strAckNo: str
    strMode: str
    strSaveFlg: str
    combo: str
    itemList: list[DVDMSAcknowledgedItem]


class DVDMSAcknowledgeSaveResponse(DVDMSPostResponse):
    data: DVDMSAcknowledgeSaveData


@cache
def _used_fields(schema):
    """Names of the fields marked Used anywhere in `schema`."""
    fields = set()
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        for name, field in schema.model_fields.items():
            if Used in field.metadata:
                fields.add(name)
            fields |= _used_fields(field.annotation)
    for arg in get_args(schema):
        fields |= _used_fields(arg)
    return frozenset(fields)


def _is_used(error, used_fields):
    if error["type"] == WARN_ONLY:
        return False
    name = next((part for part in reversed(error["loc"]) if isinstance(part, str)), None)
    return name is None or name in used_fields  # None: the body itself


def _summarise(errors):
    """One line per field and problem, with list positions folded into `*` so a change repeated
    across many items is reported once."""
    counts = Counter(
        (".".join("*" if isinstance(part, int) else part for part in err["loc"]) or "<body>", err["msg"])
        for err in errors
    )
    return "; ".join(
        f"{path}: {msg}" + (f" (in {count} items)" if count > 1 else "") for (path, msg), count in counts.items()
    )


RESPONSE_CHANGED_LOG = "DVDMS response structure changed | api=%s fields=%s"


def response_changed_error(api, problems, response):
    logger.error(RESPONSE_CHANGED_LOG, api, problems)
    return DVDMSResponseChangedError(f"DVDMS response structure changed for {api}: {problems}", response=response)


def validate_response(api, schema, body, response):
    """Check `body` against `schema`. Never alters `body`.

    A change to a field our code uses raises DVDMSResponseChangedError and stops the call. A change to
    any other field, or a new field, is logged as a warning and the call continues - as an error for a
    POST response (DVDMSPostResponse), which has already been saved by DVDMS.
    """
    try:
        TypeAdapter(schema).validate_python(body)
    except ValidationError as e:
        used_fields = _used_fields(schema)
        blocking, ignored = [], []
        for error in e.errors():
            (blocking if _is_used(error, used_fields) else ignored).append(error)
        if ignored:
            log = logger.error if issubclass(schema, DVDMSPostResponse) else logger.warning
            log(RESPONSE_CHANGED_LOG, api, _summarise(ignored))
        if blocking:
            raise response_changed_error(api, _summarise(blocking), response) from None

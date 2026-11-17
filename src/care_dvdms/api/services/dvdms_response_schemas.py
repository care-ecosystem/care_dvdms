import logging
from collections import Counter
from functools import cache
from typing import Annotated, get_args

import requests
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

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


class DVDMSDrug(DVDMSExactSchema):
    hstnum_item_id: Used[int]
    gnum_hospital_code: Used[int]
    hstnum_group_id: Used[int]
    hstnum_subgroup_id: Used[int]
    sstnum_item_cat_no: Used[str]
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


def response_changed_error(api, problems, response):
    logger.error("DVDMS response changed | api=%s errors=%s", api, problems)
    return DVDMSResponseChangedError(f"DVDMS response structure changed for {api}: {problems}", response=response)


def validate_response(api, schema, body, response):
    """Check `body` against `schema`. Never alters `body`.

    A change to a field our code uses raises DVDMSResponseChangedError and stops the call. A change to
    any other field, or a new field, is logged as a warning and the call continues.
    """
    try:
        TypeAdapter(schema).validate_python(body)
    except ValidationError as e:
        used_fields = _used_fields(schema)
        blocking, ignored = [], []
        for error in e.errors():
            (blocking if _is_used(error, used_fields) else ignored).append(error)
        if ignored:
            logger.warning(
                "DVDMS response changed in fields we do not use | api=%s changes=%s", api, _summarise(ignored)
            )
        if blocking:
            raise response_changed_error(api, _summarise(blocking), response) from None

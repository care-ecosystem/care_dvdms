from care_dvdms.api.services.constants import (
    DVDMS_DRUG_LIST_PATH,
    DVDMS_GROUP_LIST_PATH,
    DVDMS_STORE_LIST_PATH,
    DVDMS_SUBGROUP_LIST_PATH,
    DVDMS_UNIT_LIST_PATH,
)
from care_dvdms.api.services.dvdms_client import dvdms_get


def fetch_groups():
    return dvdms_get(DVDMS_GROUP_LIST_PATH)


def fetch_subgroups():
    return dvdms_get(DVDMS_SUBGROUP_LIST_PATH)


def fetch_units():
    return dvdms_get(DVDMS_UNIT_LIST_PATH)


def fetch_drugs():
    return dvdms_get(DVDMS_DRUG_LIST_PATH)


def fetch_stores():
    return dvdms_get(DVDMS_STORE_LIST_PATH)

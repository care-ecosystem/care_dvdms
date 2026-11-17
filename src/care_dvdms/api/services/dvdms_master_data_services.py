from care_dvdms.api.services.constants import (
    DVDMS_DRUG_LIST_PATH,
    DVDMS_DRUG_LIST_SUCCESS_STATUS,
    DVDMS_GROUP_LIST_PATH,
    DVDMS_GROUP_LIST_SUCCESS_STATUS,
    DVDMS_STORE_LIST_PATH,
    DVDMS_STORE_LIST_SUCCESS_STATUS,
    DVDMS_SUBGROUP_LIST_PATH,
    DVDMS_SUBGROUP_LIST_SUCCESS_STATUS,
    DVDMS_UNIT_LIST_PATH,
    DVDMS_UNIT_LIST_SUCCESS_STATUS,
)
from care_dvdms.api.services.dvdms_client import dvdms_get
from care_dvdms.api.services.dvdms_response_schemas import (
    DVDMSDrugListResponse,
    DVDMSGroupListResponse,
    DVDMSStoreListResponse,
    DVDMSSubgroupListResponse,
    DVDMSUnitListResponse,
)


def fetch_groups():
    return dvdms_get(DVDMS_GROUP_LIST_PATH, DVDMS_GROUP_LIST_SUCCESS_STATUS, schema=DVDMSGroupListResponse)


def fetch_subgroups():
    return dvdms_get(DVDMS_SUBGROUP_LIST_PATH, DVDMS_SUBGROUP_LIST_SUCCESS_STATUS, schema=DVDMSSubgroupListResponse)


def fetch_units():
    return dvdms_get(DVDMS_UNIT_LIST_PATH, DVDMS_UNIT_LIST_SUCCESS_STATUS, schema=DVDMSUnitListResponse)


def fetch_drugs():
    return dvdms_get(DVDMS_DRUG_LIST_PATH, DVDMS_DRUG_LIST_SUCCESS_STATUS, schema=DVDMSDrugListResponse)


def fetch_stores():
    return dvdms_get(DVDMS_STORE_LIST_PATH, DVDMS_STORE_LIST_SUCCESS_STATUS, schema=DVDMSStoreListResponse)

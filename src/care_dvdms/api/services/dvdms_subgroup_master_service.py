from care_dvdms.api.services.constants import DVDMS_SUBGROUP_LIST_PATH
from care_dvdms.api.services.dvdms_client import dvdms_get


class DVDMSSubGroupMasterService:
    @staticmethod
    def fetch_subgroups():
        return dvdms_get(DVDMS_SUBGROUP_LIST_PATH)

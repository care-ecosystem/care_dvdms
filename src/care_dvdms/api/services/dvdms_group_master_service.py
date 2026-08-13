from care_dvdms.api.services.constants import DVDMS_GROUP_LIST_PATH
from care_dvdms.api.services.dvdms_client import dvdms_get


class DVDMSGroupMasterService:
    @staticmethod
    def fetch_groups():
        return dvdms_get(DVDMS_GROUP_LIST_PATH)

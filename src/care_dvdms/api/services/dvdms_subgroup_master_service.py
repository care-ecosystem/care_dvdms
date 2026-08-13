import logging

import requests

from care_dvdms.settings import plugin_settings as settings

logger = logging.getLogger(__name__)

SUBGROUP_LIST_PATH = "/subGroupMst/list"


class DVDMSSubGroupMasterService:
    @staticmethod
    def fetch_subgroups():
        url = settings.DVDMS_API_ENDPOINT.rstrip("/") + SUBGROUP_LIST_PATH
        headers = {
            "Authorization": f"{settings.DVDMS_AUTH_TOKEN_TYPE} {settings.DVDMS_AUTH_TOKEN}",
        }

        timeout = (settings.DVDMS_API_CONNECT_TIMEOUT, settings.DVDMS_API_READ_TIMEOUT)

        logger.info("Fetching DVDMS subgroups | url=%s", url)

        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        body = response.json()
        if body.get("status") != 1:
            raise requests.exceptions.RequestException(body.get("message", "DVDMS subgroup fetch failed"))

        return body.get("data", [])

import logging

import requests

from care_dvdms.settings import plugin_settings as settings

logger = logging.getLogger(__name__)

GROUP_LIST_PATH = "/groupMst/list"


class DVDMSGroupMasterService:
    @staticmethod
    def fetch_groups():
        url = settings.DVDMS_API_ENDPOINT.rstrip("/") + GROUP_LIST_PATH
        headers = {
            "Authorization": f"{settings.DVDMS_AUTH_TOKEN_TYPE} {settings.DVDMS_AUTH_TOKEN}",
        }

        timeout = (settings.DVDMS_API_CONNECT_TIMEOUT, settings.DVDMS_API_READ_TIMEOUT)

        logger.info("Fetching DVDMS groups | url=%s", url)

        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        body = response.json()
        if body.get("status") != 1:
            raise requests.exceptions.RequestException(
                body.get("message", "DVDMS group fetch failed")
            )

        return body.get("data", [])

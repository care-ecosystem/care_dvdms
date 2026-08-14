import logging

import requests

from care_dvdms.settings import plugin_settings as settings

logger = logging.getLogger(__name__)


def _dvdms_request(method, path, **kwargs):
    url = settings.DVDMS_API_ENDPOINT.rstrip("/") + path
    headers = {
        "Authorization": f"{settings.DVDMS_AUTH_TOKEN_TYPE} {settings.DVDMS_AUTH_TOKEN}",
    }
    timeout = (settings.DVDMS_API_CONNECT_TIMEOUT, settings.DVDMS_API_READ_TIMEOUT)

    logger.info("Calling DVDMS API | method=%s url=%s", method, url)

    response = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
    response.raise_for_status()

    body = response.json()
    if isinstance(body, list):
        return body

    if body.get("status") != 1:
        raise requests.exceptions.RequestException(body.get("message", "DVDMS API request failed"))

    return body.get("data", [])


def dvdms_get(path, params=None):
    return _dvdms_request("GET", path, params=params)


def dvdms_post(path, payload=None):
    return _dvdms_request("POST", path, json=payload)

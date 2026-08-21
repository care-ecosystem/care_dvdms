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
    if body.get("status") != 1:
        raise requests.exceptions.RequestException(
            body.get("message", "DVDMS API request failed"), response=response
        )

    return body, response.status_code


def dvdms_get(path, params=None):
    body, _ = _dvdms_request("GET", path, params=params)
    return body.get("data", [])


def dvdms_get_full(path, params=None):
    """Like dvdms_get, but returns the full response body and HTTP status code."""
    return _dvdms_request("GET", path, params=params)


def dvdms_post(path, payload=None):
    body, _ = _dvdms_request("POST", path, json=payload)
    return body.get("data", [])


def dvdms_post_full(path, payload=None):
    """Like dvdms_post, but returns the full response body and HTTP status code."""
    return _dvdms_request("POST", path, json=payload)


def get_status_code(exc):
    """Extract the HTTP status code from a DVDMS request exception, if any."""
    response = getattr(exc, "response", None)
    return response.status_code if response is not None else None

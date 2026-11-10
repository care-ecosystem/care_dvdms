import logging

import requests

from care_dvdms.api.services.constants import (
    DVDMS_ERROR_CODE_INTERNAL,
    DVDMS_ERROR_CODE_REJECTED,
    DVDMS_ERROR_CODE_UNREACHABLE,
    DVDMS_ERROR_TEXT_LIMIT,
)
from care_dvdms.settings import plugin_settings as settings

logger = logging.getLogger(__name__)


def _dvdms_request(method, path, success_status, **kwargs):
    url = settings.DVDMS_API_ENDPOINT.rstrip("/") + path
    headers = {
        "Authorization": f"{settings.DVDMS_AUTH_TOKEN_TYPE} {settings.DVDMS_AUTH_TOKEN}",
    }
    timeout = (settings.DVDMS_API_CONNECT_TIMEOUT, settings.DVDMS_API_READ_TIMEOUT)

    logger.info("Calling DVDMS API | method=%s url=%s", method, url)

    response = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
    response.raise_for_status()

    body = response.json()
    if body.get("status") != success_status:
        raise requests.exceptions.RequestException(
            body.get("message", "DVDMS API request failed"), response=response
        )

    return body, response.status_code


def dvdms_get(path, success_status, params=None):
    body, _ = _dvdms_request("GET", path, success_status, params=params)
    return body.get("data", [])


def dvdms_get_full(path, success_status, params=None):
    """Like dvdms_get, but returns the full response body and HTTP status code."""
    return _dvdms_request("GET", path, success_status, params=params)


def dvdms_post(path, success_status, payload=None):
    body, _ = _dvdms_request("POST", path, success_status, json=payload)
    return body.get("data", [])


def dvdms_post_full(path, success_status, payload=None):
    """Like dvdms_post, but returns the full response body and HTTP status code."""
    return _dvdms_request("POST", path, success_status, json=payload)


def get_status_code(exc):
    """Extract the HTTP status code from a DVDMS request exception, if any."""
    response = getattr(exc, "response", None)
    return response.status_code if response is not None else None


def get_response_body(exc):
    """Extract DVDMS's response body from a request exception - parsed JSON, else trimmed text."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    try:
        return response.json()
    except ValueError:
        return (response.text or "")[:DVDMS_ERROR_TEXT_LIMIT] or None


def describe_error(exc):
    """Describe a failed DVDMS call for storage and display.

    DVDMS answers a rejected request with HTTP 200 and a non-success status in the body, so the
    body is the only place the reason appears. `code` lets a client tell an unreachable DVDMS
    from one that answered and refused, without parsing the message.
    """
    response = getattr(exc, "response", None)
    if isinstance(exc, requests.exceptions.RequestException) and response is None:
        code = DVDMS_ERROR_CODE_UNREACHABLE
    elif isinstance(exc, requests.exceptions.RequestException):
        code = DVDMS_ERROR_CODE_REJECTED
    else:
        code = DVDMS_ERROR_CODE_INTERNAL
    return {
        "code": code,
        "message": str(exc) or exc.__class__.__name__,
        "type": exc.__class__.__name__,
        "status_code": get_status_code(exc),
        "detail": get_response_body(exc),
    }

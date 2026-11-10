"""Shared handling for failed DVDMS calls.

A failure is recorded in two places: the sync log, which keeps the full request and response for
support, and the owning record's `meta`, which is what a client reads to tell the user what went
wrong. Both are written from the same description so they never disagree.
"""

from django.utils import timezone

from care_dvdms.api.services.dvdms_client import describe_error
from care_dvdms.models.dvdms_sync_log import DVDMSSyncRequestStatus


def record_sync_failure(sync_log, exc, attempt=None):
    """Mark a sync log failed with DVDMS's own answer, and return the block to store in `meta`."""
    error = describe_error(exc)

    sync_log.request_status = DVDMSSyncRequestStatus.failure
    sync_log.error_detail = error["message"]
    sync_log.http_status_code = error["status_code"]
    sync_log.response_payload = error["detail"]
    update_fields = [
        "request_status",
        "error_detail",
        "http_status_code",
        "response_payload",
        "modified_date",
    ]
    if attempt is not None:
        sync_log.retry_count = attempt - 1
        update_fields.append("retry_count")
    sync_log.save(update_fields=update_fields)

    block = {
        **error,
        "sync_type": sync_log.sync_type,
        "failed_at": timezone.now().isoformat(),
        "sync_log_id": str(sync_log.external_id),
    }
    if attempt is not None:
        block["attempt"] = attempt
    return block


def store_record_error(record, user, error):
    """Put the last failure on a record, or clear it when `error` is None."""
    record.meta = {"error": error} if error else {}
    update_fields = ["meta", "modified_date"]
    if user is not None:
        record.updated_by = user
        update_fields.append("updated_by")
    record.save(update_fields=update_fields)
    return record

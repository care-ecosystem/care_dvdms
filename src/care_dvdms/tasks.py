# Celery tasks for background processing.
# This file is auto-imported in apps.py ready().

import logging

import requests
from care.users.models import User
from care.utils.shortcuts import get_object_or_404
from celery import shared_task

from care_dvdms.api.services.dvdms_client import get_status_code
from care_dvdms.api.services.dvdms_indent_services import build_save_indent_payload, save_indent
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_outward_record_order import DVDMSOutwardRecordOrder
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder
from care_dvdms.models.dvdms_sync_log import (
    DVDMSSyncLog,
    DVDMSSyncRequestStatus,
    DVDMSSyncTriggeredBy,
    DVDMSSyncType,
)
from care_dvdms.settings import plugin_settings as settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="care_dvdms.tasks.save_indent_task",
    max_retries=int(settings.DVDMS_API_RETRY_COUNT),
    autoretry_for=(requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def save_indent_task(self, institute_id, record_order_id, user_id):
    logger.info(
        "Celery Task Triggered: save_indent_task | institute_id=%s record_order_id=%s attempt=%s",
        institute_id,
        record_order_id,
        self.request.retries + 1,
    )

    institute = get_object_or_404(DVDMSInstitute, external_id=institute_id)
    record_order = get_object_or_404(DVDMSRecordOrder, external_id=record_order_id, institute=institute)
    user = get_object_or_404(User, external_id=user_id)

    payload = build_save_indent_payload(record_order)

    sync_log = DVDMSSyncLog.objects.create(
        institute=institute,
        triggered_by=DVDMSSyncTriggeredBy.user,
        sync_type=DVDMSSyncType.save_indent,
        request_status=DVDMSSyncRequestStatus.pending,
        request_payload=payload,
        created_by=user,
        updated_by=user,
    )

    try:
        indent_no, response, http_status_code = save_indent(payload)
    except Exception as exc:
        sync_log.request_status = DVDMSSyncRequestStatus.failure
        sync_log.error_detail = str(exc)
        sync_log.http_status_code = get_status_code(exc)
        sync_log.save(update_fields=["request_status", "error_detail", "http_status_code", "modified_date"])
        raise

    sync_log.request_status = DVDMSSyncRequestStatus.success
    sync_log.response_payload = response
    sync_log.http_status_code = http_status_code
    sync_log.save(update_fields=["request_status", "response_payload", "http_status_code", "modified_date"])

    DVDMSOutwardRecordOrder.objects.create(
        record_order=record_order,
        eaushadhi_indent_no=indent_no,
        sync_log=sync_log,
        created_by=user,
        updated_by=user,
    )

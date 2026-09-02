# Celery tasks for background processing.
# This file is auto-imported in apps.py ready().

import logging

import requests
from care.users.models import User
from care.utils.shortcuts import get_object_or_404
from celery import shared_task
from django.db import transaction

from care_dvdms.api.services.dvdms_acknowledge_services import (
    build_acknowledge_save_payload,
    fetch_acknowledge_details,
    fetch_acknowledge_pending_records,
    parse_item_pk_key,
    save_acknowledgement,
)
from care_dvdms.api.services.dvdms_client import get_status_code
from care_dvdms.api.services.dvdms_indent_services import build_save_indent_payload, save_indent
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_inward_item_record import DVDMSInwardItemRecord
from care_dvdms.models.dvdms_inward_record import DVDMSInwardRecord, DVDMSInwardRecordStatus
from care_dvdms.models.dvdms_outward_record_order import (
    DVDMSOutwardRecordOrder,
    DVDMSOutwardRecordOrderStatus,
)
from care_dvdms.models.dvdms_record_delivery import DVDMSRecordDeliveryStatus
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder, DVDMSRecordOrderStatus
from care_dvdms.models.dvdms_sync_log import (
    DVDMSSyncLog,
    DVDMSSyncRequestStatus,
    DVDMSSyncTriggeredBy,
    DVDMSSyncType,
)
from care_dvdms.settings import plugin_settings as settings

logger = logging.getLogger(__name__)


def _upsert_outward_record(record_order, sync_log, user, outward_status, indent_no=None):
    outward_record, created = DVDMSOutwardRecordOrder.objects.get_or_create(
        record_order=record_order,
        defaults={
            "status": outward_status,
            "eaushadhi_indent_no": indent_no,
            "sync_log": sync_log,
            "created_by": user,
            "updated_by": user,
        },
    )
    if not created:
        outward_record.status = outward_status
        outward_record.sync_log = sync_log
        outward_record.updated_by = user
        update_fields = ["status", "sync_log", "updated_by", "modified_date"]
        if indent_no is not None:
            outward_record.eaushadhi_indent_no = indent_no
            update_fields.append("eaushadhi_indent_no")
        outward_record.save(update_fields=update_fields)
    return outward_record


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

        record_order.status = DVDMSRecordOrderStatus.failed
        record_order.save(update_fields=["status", "modified_date"])

        _upsert_outward_record(record_order, sync_log, user, DVDMSOutwardRecordOrderStatus.failed)
        raise
    else:
        sync_log.request_status = DVDMSSyncRequestStatus.success
        sync_log.response_payload = response
        sync_log.http_status_code = http_status_code
        sync_log.save(update_fields=["request_status", "response_payload", "http_status_code", "modified_date"])

        record_order.status = DVDMSRecordOrderStatus.approved
        record_order.save(update_fields=["status", "modified_date"])

        _upsert_outward_record(
            record_order, sync_log, user, DVDMSOutwardRecordOrderStatus.submitted, indent_no=indent_no
        )


def _upsert_inward_record(institute, outward_record, sync_log, user, issue_no):
    fields = {"outward_record": outward_record, "sync_log": sync_log}
    inward_record, _ = DVDMSInwardRecord.objects.update_or_create(
        institute=institute,
        eaushadhi_issue_no=issue_no,
        defaults={**fields, "updated_by": user},
        create_defaults={
            **fields,
            "eaushadhi_issue_status": DVDMSInwardRecordStatus.pending,
            "created_by": user,
            "updated_by": user,
        },
    )
    return inward_record


def _upsert_inward_item_record(inward_record, item_order, user, drug_id, brand_id, item):
    fields = {
        "drug_id": drug_id,
        "drug_name": item.get("itemName", ""),
        "brand_id": brand_id,
        "batch": item.get("batchNo"),
        "manufacturer": item.get("mfgName"),
        "received_quantity": item.get("issueQyt") or 0,
    }
    lookup = {"inward_record": inward_record, "record_order_item": item_order}
    if item_order is None:
        lookup["drug_id"] = drug_id
        lookup["brand_id"] = brand_id
        lookup["batch"] = item.get("batchNo")
    item_record, _ = DVDMSInwardItemRecord.objects.update_or_create(
        **lookup,
        defaults={**fields, "updated_by": user},
        create_defaults={**fields, "created_by": user, "updated_by": user},
    )
    return item_record


@shared_task(
    bind=True,
    name="care_dvdms.tasks.prefill_inward_record_task",
    max_retries=int(settings.DVDMS_API_RETRY_COUNT),
    autoretry_for=(requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def prefill_inward_record_task(self, institute_id, outward_record_id, user_id):
    logger.info(
        "Celery Task Triggered: prefill_inward_record_task | institute_id=%s outward_record_id=%s attempt=%s",
        institute_id,
        outward_record_id,
        self.request.retries + 1,
    )

    institute = get_object_or_404(DVDMSInstitute, external_id=institute_id)
    outward_record = get_object_or_404(
        DVDMSOutwardRecordOrder.objects.select_related("record_order__institute_store"),
        external_id=outward_record_id,
        record_order__institute=institute,
    )
    user = get_object_or_404(User, external_id=user_id)

    to_store_id = outward_record.record_order.institute_store.eaushadhi_store_id
    eaushadhi_indent_no = outward_record.eaushadhi_indent_no
    pending_records = fetch_acknowledge_pending_records(to_store_id, eaushadhi_indent_no)
    if not pending_records:
        logger.info(
            "prefill_inward_record_task: no acknowledge-pending entry for indent_no=%s",
            eaushadhi_indent_no,
        )
        return

    item_orders_by_drug_id = {
        item_order.drug.drug_id: item_order
        for item_order in outward_record.record_order.item_orders.select_related("drug")
    }

    for pending_record in pending_records:
        request_payload = {"issueNo": pending_record["issue_no"], "storeId": to_store_id}
        sync_log = DVDMSSyncLog.objects.create(
            institute=institute,
            triggered_by=DVDMSSyncTriggeredBy.user,
            sync_type=DVDMSSyncType.fetch_issue,
            request_status=DVDMSSyncRequestStatus.pending,
            request_payload=request_payload,
            created_by=user,
            updated_by=user,
        )

        try:
            data = fetch_acknowledge_details(pending_record["issue_no"], to_store_id)
        except Exception as exc:
            sync_log.request_status = DVDMSSyncRequestStatus.failure
            sync_log.error_detail = str(exc)
            sync_log.http_status_code = get_status_code(exc)
            sync_log.save(update_fields=["request_status", "error_detail", "http_status_code", "modified_date"])
            raise
        else:
            sync_log.request_status = DVDMSSyncRequestStatus.success
            sync_log.response_payload = data
            sync_log.save(update_fields=["request_status", "response_payload", "modified_date"])

            inward_record = _upsert_inward_record(institute, outward_record, sync_log, user, pending_record["issue_no"])

            for item in data.get("itemList", []):
                drug_id, brand_id = parse_item_pk_key(item["pkKey"])
                item_order = item_orders_by_drug_id.get(drug_id)
                _upsert_inward_item_record(inward_record, item_order, user, drug_id, brand_id, item)


@shared_task(
    bind=True,
    name="care_dvdms.tasks.save_acknowledgement_task",
    max_retries=int(settings.DVDMS_API_RETRY_COUNT),
    autoretry_for=(requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def save_acknowledgement_task(self, institute_id, inward_record_id, user_id, is_retry=False):
    logger.info(
        "Celery Task Triggered: save_acknowledgement_task | institute_id=%s inward_record_id=%s attempt=%s",
        institute_id,
        inward_record_id,
        self.request.retries + 1,
    )

    institute = get_object_or_404(DVDMSInstitute, external_id=institute_id)
    user = get_object_or_404(User, external_id=user_id)

    with transaction.atomic():
        inward_record = get_object_or_404(
            DVDMSInwardRecord.objects.select_for_update(of=("self",))
            .select_related("outward_record__record_order__institute_store", "record_delivery", "sync_log")
            .prefetch_related("items__item_delivery"),
            external_id=inward_record_id,
            institute=institute,
        )
        record_delivery = inward_record.record_delivery

        if record_delivery.status == DVDMSRecordDeliveryStatus.completed:
            logger.info(
                "save_acknowledgement_task: inward_record=%s already acknowledged, skipping",
                inward_record_id,
            )
            return

        last_sync_log = inward_record.sync_log
        if (
            not is_retry
            and self.request.retries == 0
            and last_sync_log is not None
            and last_sync_log.sync_type == DVDMSSyncType.acknowledge_issue
            and last_sync_log.request_status == DVDMSSyncRequestStatus.failure
        ):
            logger.info(
                "save_acknowledgement_task: inward_record=%s previous acknowledgement failed, "
                "not auto-retrying - use retry_acknowledgement to force another attempt",
                inward_record_id,
            )
            return

        if any(not hasattr(item, "item_delivery") for item in inward_record.items.all()):
            logger.info(
                "save_acknowledgement_task: inward_record=%s has items without a delivery yet, skipping",
                inward_record_id,
            )
            return

        payload = build_acknowledge_save_payload(inward_record)

        sync_log = DVDMSSyncLog.objects.create(
            institute=institute,
            triggered_by=DVDMSSyncTriggeredBy.user,
            sync_type=DVDMSSyncType.acknowledge_issue,
            request_status=DVDMSSyncRequestStatus.pending,
            request_payload=payload,
            created_by=user,
            updated_by=user,
        )

        request_exc = None
        try:
            response, http_status_code = save_acknowledgement(payload)
        except Exception as exc:
            request_exc = exc
            sync_log.request_status = DVDMSSyncRequestStatus.failure
            sync_log.error_detail = str(exc)
            sync_log.http_status_code = get_status_code(exc)
            sync_log.save(update_fields=["request_status", "error_detail", "http_status_code", "modified_date"])
        else:
            sync_log.request_status = DVDMSSyncRequestStatus.success
            sync_log.response_payload = response
            sync_log.http_status_code = http_status_code
            sync_log.save(update_fields=["request_status", "response_payload", "http_status_code", "modified_date"])

            record_delivery.status = DVDMSRecordDeliveryStatus.completed
            record_delivery.updated_by = user
            record_delivery.save(update_fields=["status", "updated_by", "modified_date"])

            record_order = inward_record.outward_record.record_order
            record_order.status = DVDMSRecordOrderStatus.completed
            record_order.updated_by = user
            record_order.save(update_fields=["status", "updated_by", "modified_date"])

            inward_record.eaushadhi_issue_status = DVDMSInwardRecordStatus.completed

        inward_record.sync_log = sync_log
        inward_record.updated_by = user
        inward_record.save(update_fields=["eaushadhi_issue_status", "sync_log", "updated_by", "modified_date"])

    if request_exc is not None:
        raise request_exc

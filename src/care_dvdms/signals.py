import logging

from care.emr.models.medication_request import MedicationRequestPrescription
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.models.supply_request import RequestOrder
from care.emr.resources.inventory.product_knowledge.spec import ProductKnowledgeStatusOptions
from care.emr.resources.inventory.supply_request.request_order import SupplyRequestOrderStatusOptions
from django.db import connection, transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_outward_record_order import DVDMSOutwardRecordOrderStatus
from care_dvdms.models.dvdms_prescription_sequence import DVDMSPrescriptionSequence
from care_dvdms.models.dvdms_product_mapping import (
    DVDMSProductMapping,
    DVDMSProductMappingArchiveReason,
)
from care_dvdms.models.dvdms_record_order import (
    INACTIVE_RECORD_ORDER_STATUSES,
    DVDMSRecordOrder,
    DVDMSRecordOrderStatus,
)

logger = logging.getLogger(__name__)


def _next_prescription_sequence(facility_id, year):
    # Atomic upsert - Postgres row lock on the ON CONFLICT branch prevents concurrent collisions.
    table = DVDMSPrescriptionSequence._meta.db_table  # noqa: SLF001
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {table} (facility_id, year, last_value)
            VALUES (%s, %s, 1)
            ON CONFLICT (facility_id, year)
            DO UPDATE SET last_value = {table}.last_value + 1
            RETURNING last_value
            """,  # noqa: S608
            [facility_id, year],
        )
        return cursor.fetchone()[0]


def generate_dvdms_prescription_id(prescription):
    year = timezone.localdate().year
    year_suffix = str(year)[-2:]

    facility_id = prescription.encounter.facility_id

    incremental_identifier = _next_prescription_sequence(facility_id, year)

    return f"RX{facility_id:05d}{year_suffix}{incremental_identifier:06d}"


@receiver(post_save, sender=MedicationRequestPrescription)
def set_dvdms_prescription_id(sender, instance, created, **kwargs):
    if not created or "eaushadhi_prescription_id" in instance.meta:
        return
    if not DVDMSInstitute.objects.filter(facility_id=instance.encounter.facility_id, deleted=False).exists():
        return
    instance.meta["eaushadhi_prescription_id"] = generate_dvdms_prescription_id(instance)
    MedicationRequestPrescription.objects.filter(pk=instance.pk).update(meta=instance.meta)


#: A product in one of these states can no longer be ordered, so its mappings are retired with it.
ARCHIVED_PRODUCT_KNOWLEDGE_STATUSES = {
    ProductKnowledgeStatusOptions.draft.value,
    ProductKnowledgeStatusOptions.retired.value,
}


@receiver(post_save, sender=ProductKnowledge)
def deactivate_product_mappings_on_archive(sender, instance, **kwargs):
    """Archive an inactive product's live DVDMS mappings, recording why.

    Keyed on the status the product now holds rather than on the transition, so a product that
    reaches draft or retired by any route is covered. Already-archived mappings are left alone,
    which also makes a repeated save a no-op.
    """
    if instance.status not in ARCHIVED_PRODUCT_KNOWLEDGE_STATUSES:
        return

    archived = DVDMSProductMapping.objects.filter(product_knowledge=instance, archived=False).update(
        archived=True,
        archived_reason=DVDMSProductMappingArchiveReason.product_archived,
        modified_date=timezone.now(),
    )
    if archived:
        logger.info(
            "Archived %s DVDMS product mapping(s): product knowledge %s is %s",
            archived,
            instance.external_id,
            instance.status,
        )


#: Outward states in which the indent is with DVDMS, so the record order is no longer ours
IN_FLIGHT_OUTWARD_STATUSES = {
    DVDMSOutwardRecordOrderStatus.created,
    DVDMSOutwardRecordOrderStatus.submitted,
}

#: A request order or record order in one of these states will never be fulfilled.
DISCARDED_STATUSES = set(INACTIVE_RECORD_ORDER_STATUSES)

#: Record orders that have run their course; their status is not rewritten.
FINISHED_RECORD_ORDER_STATUSES = {
    DVDMSRecordOrderStatus.completed,
    DVDMSRecordOrderStatus.rejected,
    *DISCARDED_STATUSES,
}


@receiver(post_save, sender=RequestOrder)
def sync_record_order_with_discarded_request_order(sender, instance, **kwargs):
    """Give the DVDMS record order the same status once its request order is entered in error or abandoned.

    A record order already handed to DVDMS is left alone - see below.
    """
    if instance.status not in DISCARDED_STATUSES:
        return

    candidates = DVDMSRecordOrder.objects.filter(order=instance).exclude(status__in=FINISHED_RECORD_ORDER_STATUSES)

    with_dvdms = Q(outward_record__status__in=IN_FLIGHT_OUTWARD_STATUSES)
    for record_order in candidates.filter(with_dvdms).select_related("outward_record"):
        logger.warning(
            "Request order %s is %s but DVDMS record order %s is %s with DVDMS (indent %s) - "
            "leaving it as %s; reconcile with DVDMS manually",
            instance.external_id,
            instance.status,
            record_order.external_id,
            record_order.outward_record.status,
            record_order.outward_record.eaushadhi_indent_no or "not yet assigned",
            record_order.status,
        )

    with transaction.atomic():
        updated = candidates.exclude(with_dvdms).update(
            status=instance.status, updated_by_id=instance.updated_by_id, modified_date=timezone.now()
        )
    if updated:
        logger.info(
            "Marked %s DVDMS record order(s) %s: request order %s is %s",
            updated,
            instance.status,
            instance.external_id,
            instance.status,
        )


@receiver(post_save, sender=DVDMSRecordOrder)
def sync_request_order_with_discarded_record_order(sender, instance, **kwargs):
    """Give the request order the same status once its DVDMS record order is entered in error or abandoned."""
    if instance.status not in DISCARDED_STATUSES:
        return

    with transaction.atomic():
        order = RequestOrder.objects.select_for_update().get(pk=instance.order_id)
        if order.status in DISCARDED_STATUSES or order.status == SupplyRequestOrderStatusOptions.completed.value:
            return

        order.status = instance.status
        order.updated_by_id = instance.updated_by_id
        order.save(update_fields=["status", "updated_by", "modified_date"])

import logging

from care.emr.models.medication_request import MedicationRequestPrescription
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.inventory.product_knowledge.spec import ProductKnowledgeStatusOptions
from django.db import connection
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_prescription_sequence import DVDMSPrescriptionSequence
from care_dvdms.models.dvdms_product_mapping import (
    DVDMSProductMapping,
    DVDMSProductMappingArchiveReason,
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

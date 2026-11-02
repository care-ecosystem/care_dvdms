from care.emr.models.medication_request import MedicationRequestPrescription
from django.db import connection
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from care_dvdms.models.dvdms_prescription_sequence import DVDMSPrescriptionSequence


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
    if not created or "dvdms_prescription_id" in instance.meta:
        return
    instance.meta["dvdms_prescription_id"] = generate_dvdms_prescription_id(instance)
    MedicationRequestPrescription.objects.filter(pk=instance.pk).update(meta=instance.meta)

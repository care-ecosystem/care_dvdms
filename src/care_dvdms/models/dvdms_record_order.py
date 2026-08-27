from care.emr.models.base import EMRBaseModel
from django.db import connection, models

from care_dvdms.api.services.constants import CARE_INDENT_NO_FACILITY_WIDTH, CARE_INDENT_NO_SEQ_WIDTH
from care_dvdms.models.dvdms_care_indent_sequence import DVDMSCareIndentSequence
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_store import DVDMSStore
from care_dvdms.models.dvdms_supplier import DVDMSSupplier
from care_dvdms.utils.financial_year import current_financial_year_digits


def _next_care_indent_sequence(institute, financial_year):
    # Atomic upsert - Postgres row lock on the ON CONFLICT branch prevents concurrent collisions.
    table = DVDMSCareIndentSequence._meta.db_table  # noqa: SLF001
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {table} (institute_id, financial_year, last_value)
            VALUES (%s, %s, 1)
            ON CONFLICT (institute_id, financial_year)
            DO UPDATE SET last_value = {table}.last_value + 1
            RETURNING last_value
            """,  # noqa: S608
            [institute.pk, financial_year],
        )
        return cursor.fetchone()[0]


class DVDMSRecordOrderStatus(models.TextChoices):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class DVDMSRecordOrder(EMRBaseModel):
    institute = models.ForeignKey(
        DVDMSInstitute,
        on_delete=models.CASCADE,
        related_name="record_orders",
    )
    name = models.CharField(max_length=255)
    order = models.ForeignKey(
        "emr.RequestOrder",
        on_delete=models.PROTECT,
        related_name="dvdms_record_order",
    )
    institute_store = models.ForeignKey(
        DVDMSStore,
        on_delete=models.PROTECT,
        related_name="record_orders",
    )
    institute_supplier = models.ForeignKey(
        DVDMSSupplier,
        on_delete=models.PROTECT,
        related_name="record_orders",
    )
    care_indent_no = models.CharField(max_length=32, unique=True, editable=False, blank=True)
    status = models.CharField(
        max_length=20,
        choices=DVDMSRecordOrderStatus.choices,
        default=DVDMSRecordOrderStatus.draft,
    )

    class Meta:
        verbose_name_plural = "DVDMS Record Orders"
        constraints = [
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(deleted=False)
                & ~models.Q(
                    status__in=[
                        DVDMSRecordOrderStatus.cancelled,
                        DVDMSRecordOrderStatus.rejected,
                        DVDMSRecordOrderStatus.failed,
                    ]
                ),
                name="uniq_order_active_record_order",
            ),
        ]

    def __str__(self):
        return f"{self.institute} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.care_indent_no:
            fy_digits = current_financial_year_digits()
            seq_no = _next_care_indent_sequence(self.institute, fy_digits)
            facility_digits = f"{self.institute.facility_id:0{CARE_INDENT_NO_FACILITY_WIDTH}d}"
            seq_digits = f"{seq_no:0{CARE_INDENT_NO_SEQ_WIDTH}d}"
            self.care_indent_no = f"{fy_digits}{facility_digits}{seq_digits}"
        super().save(*args, **kwargs)

from care.emr.models.base import EMRBaseModel
from django.db import connection, models
from django.utils import timezone

from care_dvdms.api.services.constants import (
    CARE_INDENT_NO_FACILITY_WIDTH,
    CARE_INDENT_NO_SEQ_WIDTH,
    CARE_INDENT_NO_SEQUENCE,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_store import DVDMSStore
from care_dvdms.models.dvdms_supplier import DVDMSSupplier


def _current_financial_year_digits() -> str:
    today = timezone.now().date()
    start_year = today.year if today.month >= 4 else today.year - 1
    return f"{start_year}{str(start_year + 1)[-2:]}"


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
    order = models.OneToOneField(
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

    def __str__(self):
        return f"{self.institute} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.care_indent_no:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT nextval('{CARE_INDENT_NO_SEQUENCE}')")  # noqa: S608
                seq_no = cursor.fetchone()[0]
            fy_digits = _current_financial_year_digits()
            facility_digits = f"{self.institute.facility_id:0{CARE_INDENT_NO_FACILITY_WIDTH}d}"
            seq_digits = f"{seq_no:0{CARE_INDENT_NO_SEQ_WIDTH}d}"
            self.care_indent_no = f"{fy_digits}{facility_digits}{seq_digits}"
        super().save(*args, **kwargs)

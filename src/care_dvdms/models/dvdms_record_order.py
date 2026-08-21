import re

from care.emr.models.base import EMRBaseModel
from django.db import connection, models
from django.utils import timezone

from care_dvdms.api.services.constants import CARE_INDENT_NO_SEQ_WIDTH, CARE_INDENT_NO_SEQUENCE
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_store import DVDMSStore
from care_dvdms.models.dvdms_supplier import DVDMSSupplier


def _normalized_value(value: str, length: int = 3) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()[:length]


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
            facility_prefix = _normalized_value(self.institute.facility.name)
            year_suffix = str(timezone.now().year)[-2:]
            self.care_indent_no = f"{facility_prefix}-{year_suffix}-{seq_no:0{CARE_INDENT_NO_SEQ_WIDTH}d}"
        super().save(*args, **kwargs)

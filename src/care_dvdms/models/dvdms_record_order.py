from care.emr.models.base import EMRBaseModel
from django.db import models

from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_store import DVDMSStore
from care_dvdms.models.dvdms_supplier import DVDMSSupplier


class DVDMSRecordOrderStatus(models.TextChoices):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"
    failed = "failed"


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
    status = models.CharField(
        max_length=20,
        choices=DVDMSRecordOrderStatus.choices,
        default=DVDMSRecordOrderStatus.draft,
    )

    class Meta:
        verbose_name_plural = "DVDMS Record Orders"

    def __str__(self):
        return f"{self.institute} - {self.name}"

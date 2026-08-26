from care.emr.models.base import EMRBaseModel
from django.db import models

from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder


class DVDMSRecordDeliveryStatus(models.TextChoices):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class DVDMSRecordDelivery(EMRBaseModel):
    record_order = models.ForeignKey(
        DVDMSRecordOrder,
        on_delete=models.CASCADE,
        related_name="record_deliveries",
    )
    delivery_order = models.OneToOneField(
        "emr.DeliveryOrder",
        on_delete=models.PROTECT,
        related_name="dvdms_record_delivery",
    )
    status = models.CharField(
        max_length=20,
        choices=DVDMSRecordDeliveryStatus.choices,
        default=DVDMSRecordDeliveryStatus.pending,
    )

    class Meta:
        verbose_name_plural = "DVDMS Record Deliveries"

    def __str__(self):
        return f"{self.record_order} - {self.delivery_order_id}"

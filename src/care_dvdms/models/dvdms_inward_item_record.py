from care.emr.models.base import EMRBaseModel
from django.db import models

from care_dvdms.models.dvdms_inward_record import DVDMSInwardRecord
from care_dvdms.models.dvdms_record_item_order import DVDMSRecordItemOrder


class DVDMSInwardItemRecordStatus(models.TextChoices):
    pending = "pending"
    received = "received"
    partially_received = "partially_received"
    rejected = "rejected"
    damaged = "damaged"


class DVDMSInwardItemRecord(EMRBaseModel):
    inward_record = models.ForeignKey(
        DVDMSInwardRecord,
        on_delete=models.CASCADE,
        related_name="items",
    )
    record_order_item = models.ForeignKey(
        DVDMSRecordItemOrder,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inward_item_records",
    )
    drug_id = models.CharField(max_length=50)
    drug_name = models.CharField(max_length=500)
    brand_id = models.CharField(max_length=50, null=True, blank=True)
    batch = models.CharField(max_length=255, null=True, blank=True)
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    received_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=DVDMSInwardItemRecordStatus.choices,
        default=DVDMSInwardItemRecordStatus.pending,
    )

    class Meta:
        verbose_name_plural = "DVDMS Inward Item Records"
        constraints = [
            models.UniqueConstraint(
                fields=["inward_record", "record_order_item"],
                condition=models.Q(deleted=False),
                name="uniq_inward_record_item",
            ),
        ]

    def __str__(self):
        return f"{self.drug_name} - {self.batch}"

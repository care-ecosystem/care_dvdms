from care.emr.models.base import EMRBaseModel
from django.db import models

from care_dvdms.models.dvdms_inward_item_record import DVDMSInwardItemRecord


class DVDMSRecordItemDeliveryStatus(models.TextChoices):
    draft = "draft"
    active = "ACTIVE"
    reversed_ = "REVERSED"


class DVDMSRecordItemDelivery(EMRBaseModel):
    inward_record_item = models.OneToOneField(
        DVDMSInwardItemRecord,
        on_delete=models.PROTECT,
        related_name="item_delivery",
    )
    supply_delivery = models.OneToOneField(
        "emr.SupplyDelivery",
        on_delete=models.PROTECT,
        related_name="dvdms_record_item_delivery",
    )
    quantity_dispatched = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_accepted = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_damaged = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_short = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=DVDMSRecordItemDeliveryStatus.choices,
        default=DVDMSRecordItemDeliveryStatus.draft,
    )

    class Meta:
        verbose_name_plural = "DVDMS Record Item Deliveries"

    def __str__(self):
        return f"{self.inward_record_item} - {self.status}"

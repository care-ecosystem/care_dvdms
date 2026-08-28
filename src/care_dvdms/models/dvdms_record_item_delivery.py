from care.emr.models.base import EMRBaseModel
from django.db import models

from care_dvdms.models.dvdms_inward_item_record import DVDMSInwardItemRecord
from care_dvdms.models.dvdms_record_delivery import DVDMSRecordDelivery


class DVDMSRecordItemDeliveryStatus(models.TextChoices):
    draft = "draft"
    active = "ACTIVE"
    reversed_ = "REVERSED"


class DVDMSRecordItemDelivery(EMRBaseModel):
    record_delivery = models.ForeignKey(
        DVDMSRecordDelivery,
        on_delete=models.CASCADE,
        related_name="item_deliveries",
    )
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
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_dispatched__gte=0),
                name="record_item_delivery_quantity_dispatched_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_accepted__gte=0),
                name="record_item_delivery_quantity_accepted_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_damaged__gte=0),
                name="record_item_delivery_quantity_damaged_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_short__gte=0),
                name="record_item_delivery_quantity_short_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.inward_record_item} - {self.status}"

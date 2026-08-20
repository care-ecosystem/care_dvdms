from care.emr.models.base import EMRBaseModel
from django.db import models

from care_dvdms.models.dvdms_drug import DVDMSDrug
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder


class DVDMSRecordItemOrder(EMRBaseModel):
    institute = models.ForeignKey(
        DVDMSInstitute,
        on_delete=models.CASCADE,
        related_name="record_item_orders",
    )
    record_order = models.ForeignKey(
        DVDMSRecordOrder,
        on_delete=models.CASCADE,
        related_name="item_orders",
    )
    supply_request = models.OneToOneField(
        "emr.SupplyRequest",
        on_delete=models.PROTECT,
        related_name="dvdms_record_item_order",
    )
    drug = models.OneToOneField(
        DVDMSDrug,
        on_delete=models.PROTECT,
        related_name="record_item_order",
    )

    class Meta:
        verbose_name_plural = "DVDMS Record Item Orders"

    def __str__(self):
        return f"{self.record_order} - {self.supply_request_id}"

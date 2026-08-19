from care.emr.models.base import EMRBaseModel
from django.db import models

from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder


class DVDMSDrug(models.Model):
    """Snapshot of a DVDMS drug/item, owned by a single DVDMSRecordItemOrder."""

    drug_id = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    brand_id = models.CharField(max_length=50, blank=True, default="")
    group_id = models.CharField(max_length=50, blank=True, default="")
    sub_group_id = models.CharField(max_length=50, blank=True, default="")
    unit_id = models.CharField(max_length=50, blank=True, default="")
    drug_category = models.CharField(max_length=50, blank=True, default="")

    def __str__(self):
        return f"{self.drug_id} - {self.name}"


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
        on_delete=models.CASCADE,
        related_name="record_item_order",
    )

    class Meta:
        verbose_name_plural = "DVDMS Record Item Orders"

    def __str__(self):
        return f"{self.record_order} - {self.supply_request_id}"

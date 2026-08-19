from care.emr.models.base import EMRBaseModel
from django.db import models

from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder
from care_dvdms.models.dvdms_sync_log import DVDMSSyncLog


class DVDMSOutwardRecordOrderStatus(models.TextChoices):
    created = "created"
    submitted = "submitted"
    cancelled = "cancelled"
    failed = "failed"


class DVDMSOutwardRecordOrder(EMRBaseModel):
    record_order = models.OneToOneField(
        DVDMSRecordOrder,
        on_delete=models.CASCADE,
        related_name="outward_record",
    )
    status = models.CharField(
        max_length=20,
        choices=DVDMSOutwardRecordOrderStatus.choices,
        default=DVDMSOutwardRecordOrderStatus.created,
    )
    eaushadhi_indent_no = models.CharField(max_length=255, null=True, blank=True)
    eaushadhi_indent_status = models.CharField(max_length=255, null=True, blank=True)
    sync_log = models.ForeignKey(
        DVDMSSyncLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outward_records",
    )

    class Meta:
        verbose_name_plural = "DVDMS Outward Record Orders"

    def __str__(self):
        return f"{self.record_order} - {self.eaushadhi_indent_no}"

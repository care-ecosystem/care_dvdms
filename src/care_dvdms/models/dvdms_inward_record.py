from care.emr.models.base import EMRBaseModel
from django.db import models

from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_outward_record_order import DVDMSOutwardRecordOrder
from care_dvdms.models.dvdms_sync_log import DVDMSSyncLog


class DVDMSInwardRecordStatus(models.TextChoices):
    draft = "draft"
    pending = "pending"
    received = "received"
    partially_received = "partially_received"
    completed = "completed"
    cancelled = "cancelled"


class DVDMSInwardRecord(EMRBaseModel):
    institute = models.ForeignKey(
        DVDMSInstitute,
        on_delete=models.CASCADE,
        related_name="inward_records",
    )
    outward_record = models.ForeignKey(
        DVDMSOutwardRecordOrder,
        on_delete=models.CASCADE,
        related_name="inward_records",
        null=True,
        blank=True,
    )
    eaushadhi_issue_no = models.CharField(max_length=255)
    eaushadhi_issue_status = models.CharField(
        max_length=20,
        choices=DVDMSInwardRecordStatus.choices,
        default=DVDMSInwardRecordStatus.draft,
    )
    sync_log = models.ForeignKey(
        DVDMSSyncLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inward_records",
    )

    class Meta:
        verbose_name_plural = "DVDMS Inward Records"
        constraints = [
            models.UniqueConstraint(
                fields=["institute", "eaushadhi_issue_no"],
                condition=models.Q(deleted=False),
                name="uniq_institute_issue_no",
            ),
        ]

    def __str__(self):
        return f"{self.outward_record or self.institute} - {self.eaushadhi_issue_no}"

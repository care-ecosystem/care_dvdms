from care.emr.models.base import EMRBaseModel
from django.db import models

from care_dvdms.models.dvdms_institute import DVDMSInstitute


class DVDMSSyncTriggeredBy(models.TextChoices):
    user = "user"
    cron = "cron"
    retry = "retry"


class DVDMSSyncType(models.TextChoices):
    save_indent = "save_indent"
    track_indent = "track_indent"
    acknowledge = "acknowledge"


class DVDMSSyncRequestStatus(models.TextChoices):
    pending = "pending"
    success = "success"
    failure = "failure"


class DVDMSSyncLog(EMRBaseModel):
    institute = models.ForeignKey(
        DVDMSInstitute,
        on_delete=models.CASCADE,
        related_name="sync_logs",
    )
    triggered_by = models.CharField(
        max_length=20,
        choices=DVDMSSyncTriggeredBy.choices,
        default=DVDMSSyncTriggeredBy.user,
    )
    sync_type = models.CharField(max_length=20, choices=DVDMSSyncType.choices)
    request_status = models.CharField(
        max_length=20,
        choices=DVDMSSyncRequestStatus.choices,
        default=DVDMSSyncRequestStatus.pending,
    )
    http_status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    request_payload = models.JSONField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)
    error_detail = models.TextField(null=True, blank=True)
    api_response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "DVDMS Sync Logs"

    def __str__(self):
        return f"{self.institute} - {self.sync_type} - {self.request_status}"

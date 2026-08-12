from django.db import models

from care.emr.models.base import EMRBaseModel
from care.facility.models import Facility


class DVDMSInstitute(EMRBaseModel):
    facility = models.OneToOneField(
        Facility,
        on_delete=models.PROTECT,
        related_name="dvdms_institute",
    )
    eaushadhi_institute_id = models.CharField(max_length=50)
    eaushadhi_institute_name = models.CharField(max_length=255)
    eaushadhi_user_ref_id = models.CharField(max_length=50)
    schema_version = models.CharField(max_length=10, default="1.0")

    class Meta:
        verbose_name_plural = "DVDMS Institutes"
        indexes = [
            models.Index(
                fields=["eaushadhi_institute_id"],
                name="idx_dvdms_institute_eaushadhi_id",
            ),
        ]

    def __str__(self):
        return f"DVDMS Institute - {self.facility.name}"

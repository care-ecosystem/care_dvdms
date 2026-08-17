from django.db import models

from care.emr.models.base import EMRBaseModel
from care.emr.models.location import FacilityLocation

from care_dvdms.models.dvdms_institute import DVDMSInstitute


class DVDMSStore(EMRBaseModel):
    institute = models.ForeignKey(
        DVDMSInstitute,
        on_delete=models.CASCADE,
        related_name="store_mappings",
    )
    location = models.ForeignKey(
        FacilityLocation,
        on_delete=models.PROTECT,
        related_name="dvdms_store_mappings",
    )
    eaushadhi_store_id = models.CharField(max_length=50)
    eaushadhi_store_name = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "DVDMS Stores"
        constraints = [
            models.UniqueConstraint(
                fields=["institute", "location"],
                condition=models.Q(deleted=False),
                name="uniq_institute_location",
            ),
            models.UniqueConstraint(
                fields=["institute", "is_default"],
                condition=models.Q(is_default=True, deleted=False),
                name="uniq_default_store_per_institute",
            ),
        ]

    def __str__(self):
        return f"{self.institute} - {self.eaushadhi_store_name}"

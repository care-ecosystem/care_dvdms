from django.db import models


class DVDMSPrescriptionSequence(models.Model):
    """Per-(facility, year) counter backing eaushadhi_prescription_id generation."""

    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.CASCADE,
        related_name="dvdms_prescription_sequences",
    )
    year = models.PositiveSmallIntegerField()
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "year"],
                name="uniq_dvdms_prescription_facility_year",
            ),
        ]

from django.db import models

from care_dvdms.models.dvdms_institute import DVDMSInstitute


class DVDMSCareIndentSequence(models.Model):
    """Per-(institute, financial_year) counter backing DVDMSRecordOrder.care_indent_no."""

    institute = models.ForeignKey(
        DVDMSInstitute,
        on_delete=models.CASCADE,
        related_name="care_indent_sequences",
    )
    financial_year = models.CharField(max_length=6)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["institute", "financial_year"],
                name="uniq_institute_financial_year",
            ),
        ]

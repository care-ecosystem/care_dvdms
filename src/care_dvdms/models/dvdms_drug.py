from care.emr.models.base import EMRBaseModel
from django.db import models


class DVDMSDrug(EMRBaseModel):
    """Snapshot of a DVDMS drug/item, owned by a single DVDMSRecordItemOrder."""

    drug_id = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    brand_id = models.CharField(max_length=50, blank=True, default="")
    group_id = models.CharField(max_length=50, blank=True, default="")
    sub_group_id = models.CharField(max_length=50, blank=True, default="")
    unit_id = models.CharField(max_length=50, blank=True, default="")
    drug_category = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        verbose_name_plural = "DVDMS Drugs"
        # Line items read in the order they were added, not newest first.
        ordering = ["id"]
        indexes = [
            # Product mappings are filtered by drug__drug_id.
            models.Index(fields=["drug_id"], name="dvdms_drug_drug_id"),
        ]

    def __str__(self):
        return f"{self.drug_id} - {self.name}"

from django.db import models


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

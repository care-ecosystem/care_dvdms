from care.emr.models.base import EMRBaseModel
from care.emr.models.product_knowledge import ProductKnowledge
from django.db import models

from care_dvdms.models.dvdms_drug import DVDMSDrug
from care_dvdms.models.dvdms_institute import DVDMSInstitute


class DVDMSProductMappingType(models.TextChoices):
    default_mapping = "default_mapping"
    manual_mapping = "manual_mapping"


class DVDMSProductMapping(EMRBaseModel):
    institute = models.ForeignKey(
        DVDMSInstitute,
        on_delete=models.CASCADE,
        related_name="product_mappings",
    )
    drug = models.OneToOneField(
        DVDMSDrug,
        on_delete=models.PROTECT,
        related_name="product_mapping",
    )
    product_knowledge = models.ForeignKey(
        ProductKnowledge,
        on_delete=models.PROTECT,
        related_name="dvdms_product_mappings",
    )
    mapping_type = models.CharField(
        max_length=20,
        choices=DVDMSProductMappingType.choices,
        default=DVDMSProductMappingType.manual_mapping,
        db_index=True,
    )
    usage_count = models.IntegerField(default=0)
    last_used_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "DVDMS Product Mappings"

    def __str__(self):
        return f"{self.drug} -> {self.product_knowledge_id}"

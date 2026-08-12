from django.db import models

from care.emr.models.base import EMRBaseModel
from care.emr.models.organization import Organization

from care_dvdms.models.dvdms_institute import DVDMSInstitute


class DVDMSSupplier(EMRBaseModel):
    institute = models.ForeignKey(
        DVDMSInstitute,
        on_delete=models.CASCADE,
        related_name="supplier_mappings",
    )
    supplier = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        limit_choices_to={"org_type": "product_supplier"},
        related_name="dvdms_supplier_mappings",
    )
    eaushadhi_warehouse_id = models.CharField(max_length=50)
    eaushadhi_warehouse_name = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "DVDMS Suppliers"
        constraints = [
            models.UniqueConstraint(
                fields=["institute", "supplier"],
                name="uniq_institute_supplier",
            ),
            models.UniqueConstraint(
                fields=["institute", "is_default"],
                condition=models.Q(is_default=True, deleted=False),
                name="uniq_default_supplier_per_institute",
            ),
        ]

    def __str__(self):
        return f"{self.institute} - {self.eaushadhi_warehouse_name}"

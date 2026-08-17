import datetime
from pydantic import UUID4, Field

from care.emr.resources.base import EMRResource

from care_dvdms.models.dvdms_supplier import DVDMSSupplier


class DVDMSSupplierListSpec(EMRResource):
    __model__ = DVDMSSupplier
    __exclude__ = []

    id: UUID4 | None = None
    institute_id: UUID4 | None = None
    eaushadhi_warehouse_id: str | None = None
    eaushadhi_warehouse_name: str | None = None
    is_default: bool | None = None
    supplier: dict | None = None
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    def to_json(self):
        return self.model_dump(mode="json")

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["institute_id"] = obj.institute.external_id if obj.institute else None
        mapping["supplier"] = {
            "id": obj.supplier.external_id,
            "name": obj.supplier.name,
            "org_type": obj.supplier.org_type,
        } if obj.supplier else None
        cls.serialize_audit_users(mapping, obj)


class DVDMSSupplierCreateSpec(EMRResource):
    """Input spec for creating a supplier mapping."""
    __model__ = DVDMSSupplier
    __exclude__ = ["id", "institute", "created_by", "updated_by", "created_date", "modified_date", "deleted", "external_id", "history"]

    supplier: UUID4
    eaushadhi_warehouse_id: str = Field(max_length=50)
    eaushadhi_warehouse_name: str = Field(max_length=255)
    is_default: bool = False


class DVDMSSupplierUpdateSpec(EMRResource):
    """Input spec for updating a supplier mapping."""
    __model__ = DVDMSSupplier
    __exclude__ = ["id", "institute", "supplier", "created_by", "updated_by", "created_date", "modified_date", "deleted", "external_id", "history"]

    eaushadhi_warehouse_name: str | None = None
    is_default: bool | None = None

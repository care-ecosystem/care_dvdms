import datetime

from care.emr.resources.base import EMRResource
from care.emr.resources.inventory.supply_request.request_order import (
    SupplyRequestOrderReadSpec,
)
from pydantic import UUID4

from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder, DVDMSRecordOrderStatus


class DVDMSRecordOrderListSpec(EMRResource):
    __model__ = DVDMSRecordOrder
    __exclude__ = []

    id: UUID4 | None = None
    institute_id: UUID4 | None = None
    name: str | None = None
    order: dict | None = None
    institute_store: dict | None = None
    institute_supplier: dict | None = None
    status: str | None = None
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
        mapping["order"] = SupplyRequestOrderReadSpec.serialize(obj.order).to_json()
        mapping["institute_store"] = (
            {
                "id": obj.institute_store.external_id,
                "eaushadhi_store_id": obj.institute_store.eaushadhi_store_id,
                "eaushadhi_store_name": obj.institute_store.eaushadhi_store_name,
                "store": {
                    "id": obj.institute_store.location.external_id,
                    "name": obj.institute_store.location.name,
                    "form": obj.institute_store.location.form,
                },
            }
            if obj.institute_store
            else None
        )
        mapping["institute_supplier"] = (
            {
                "id": obj.institute_supplier.external_id,
                "eaushadhi_warehouse_id": obj.institute_supplier.eaushadhi_warehouse_id,
                "eaushadhi_warehouse_name": obj.institute_supplier.eaushadhi_warehouse_name,
                "supplier": {
                    "id": obj.institute_supplier.supplier.external_id,
                    "name": obj.institute_supplier.supplier.name,
                    "org_type": obj.institute_supplier.supplier.org_type,
                },
            }
            if obj.institute_supplier
            else None
        )
        cls.serialize_audit_users(mapping, obj)


class DVDMSRecordOrderCreateSpec(EMRResource):
    """Input spec for creating a record order."""

    __model__ = DVDMSRecordOrder
    __exclude__ = [
        "id",
        "institute",
        "order",
        "institute_store",
        "institute_supplier",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    name: str
    order: UUID4
    institute_store: UUID4
    institute_supplier: UUID4
    status: DVDMSRecordOrderStatus = DVDMSRecordOrderStatus.draft


class DVDMSRecordOrderUpdateSpec(EMRResource):
    """Input spec for updating a record order."""

    __model__ = DVDMSRecordOrder
    __exclude__ = [
        "id",
        "institute",
        "name",
        "order",
        "institute_store",
        "institute_supplier",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    status: DVDMSRecordOrderStatus | None = None

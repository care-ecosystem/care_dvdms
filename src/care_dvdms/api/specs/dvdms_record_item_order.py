import datetime

from care.emr.resources.base import EMRResource
from care.emr.resources.inventory.supply_request.spec import SupplyRequestReadSpec
from pydantic import UUID4, BaseModel, Field

from care_dvdms.models.dvdms_record_item_order import DVDMSRecordItemOrder


class DVDMSDrugSpec(BaseModel):
    id: str = Field(max_length=50)
    name: str = Field(max_length=255)
    brand_id: str = ""
    group_id: str = ""
    sub_group_id: str = ""
    unit_id: str = ""
    drug_category: str = ""


class DVDMSRecordItemOrderListSpec(EMRResource):
    __model__ = DVDMSRecordItemOrder
    __exclude__ = []

    id: UUID4 | None = None
    institute_id: UUID4 | None = None
    record_order_id: UUID4 | None = None
    supply_request: dict | None = None
    drug: dict | None = None
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
        mapping["record_order_id"] = obj.record_order.external_id if obj.record_order else None
        mapping["supply_request"] = SupplyRequestReadSpec.serialize(obj.supply_request).to_json()
        mapping["drug"] = {
            "id": obj.drug.drug_id,
            "name": obj.drug.name,
            "brand_id": obj.drug.brand_id,
            "group_id": obj.drug.group_id,
            "sub_group_id": obj.drug.sub_group_id,
            "unit_id": obj.drug.unit_id,
            "drug_category": obj.drug.drug_category,
        }
        cls.serialize_audit_users(mapping, obj)


class DVDMSRecordItemOrderCreateSpec(EMRResource):
    """Input spec for creating a record item order."""

    __model__ = DVDMSRecordItemOrder
    __exclude__ = [
        "id",
        "institute",
        "record_order",
        "supply_request",
        "drug",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    supply_request: UUID4
    drug: DVDMSDrugSpec


class DVDMSRecordItemOrderUpdateSpec(EMRResource):
    """Input spec for updating a record item order."""

    __model__ = DVDMSRecordItemOrder
    __exclude__ = [
        "id",
        "institute",
        "record_order",
        "supply_request",
        "drug",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    drug: DVDMSDrugSpec | None = None

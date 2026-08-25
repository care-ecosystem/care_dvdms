import datetime

from care.emr.resources.base import EMRResource
from care.emr.resources.inventory.product_knowledge.spec import ProductKnowledgeReadSpec
from pydantic import UUID4

from care_dvdms.api.specs.dvdms_record_item_order import DVDMSDrugSpec
from care_dvdms.models.dvdms_product_mapping import DVDMSProductMapping


class DVDMSProductMappingListSpec(EMRResource):
    __model__ = DVDMSProductMapping
    __exclude__ = []

    id: UUID4 | None = None
    institute_id: UUID4 | None = None
    eaushadhi_drug_details: dict | None = None
    product_knowledge: dict | None = None
    mapping_type: str | None = None
    usage_count: int | None = None
    last_used_date: datetime.datetime | None = None
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
        mapping["eaushadhi_drug_details"] = {
            "id": obj.drug.drug_id,
            "name": obj.drug.name,
            "brand_id": obj.drug.brand_id,
            "group_id": obj.drug.group_id,
            "sub_group_id": obj.drug.sub_group_id,
            "unit_id": obj.drug.unit_id,
            "drug_category": obj.drug.drug_category,
        }
        mapping["product_knowledge"] = (
            ProductKnowledgeReadSpec.serialize(obj.product_knowledge).to_json()
            if obj.product_knowledge
            else None
        )
        cls.serialize_audit_users(mapping, obj)


class DVDMSProductMappingCreateSpec(EMRResource):
    """Input spec for creating a product mapping."""

    __model__ = DVDMSProductMapping
    __exclude__ = [
        "id",
        "institute",
        "drug",
        "product_knowledge",
        "mapping_type",
        "usage_count",
        "last_used_date",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    eaushadhi_drug_details: DVDMSDrugSpec
    product_knowledge_id: UUID4


class DVDMSProductMappingUpdateSpec(EMRResource):
    """Input spec for updating a product mapping."""

    __model__ = DVDMSProductMapping
    __exclude__ = [
        "id",
        "institute",
        "drug",
        "product_knowledge",
        "mapping_type",
        "usage_count",
        "last_used_date",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    eaushadhi_drug_details: DVDMSDrugSpec | None = None
    product_knowledge_id: UUID4 | None = None

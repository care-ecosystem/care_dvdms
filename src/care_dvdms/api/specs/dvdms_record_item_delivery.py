import datetime
from decimal import Decimal

from care.emr.resources.base import EMRResource
from pydantic import UUID4, Field

from care_dvdms.models.dvdms_record_item_delivery import (
    DVDMSRecordItemDelivery,
    DVDMSRecordItemDeliveryStatus,
)


class DVDMSRecordItemDeliveryListSpec(EMRResource):
    __model__ = DVDMSRecordItemDelivery
    __exclude__ = []

    id: UUID4 | None = None
    inward_record_item: dict | None = None
    supply_delivery: dict | None = None
    record_delivery: dict | None = None
    product: dict | None = None
    product_knowledge: dict | None = None
    quantity_dispatched: str | None = None
    quantity_accepted: str | None = None
    quantity_damaged: str | None = None
    quantity_short: str | None = None
    status: str | None = None
    deleted: bool | None = None
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    def to_json(self):
        return self.model_dump(mode="json")

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["inward_record_item"] = {
            "id": obj.inward_record_item.external_id,
            "item_name": obj.inward_record_item.drug_name,
            "batch_number": obj.inward_record_item.batch,
        }
        supply_delivery = obj.supply_delivery
        mapping["supply_delivery"] = {
            "id": supply_delivery.external_id,
            "status": supply_delivery.status,
            "modified_date": supply_delivery.modified_date,
            "supplied_item_condition": supply_delivery.supplied_item_condition,
            "supplied_item_pack_quantity": supply_delivery.supplied_item_pack_quantity,
            "supplied_item_pack_size": supply_delivery.supplied_item_pack_size,
            "supplied_item_quantity": supply_delivery.supplied_item_quantity,
        }
        mapping["record_delivery"] = {
            "id": obj.record_delivery.external_id,
            "status": obj.record_delivery.status,
        }
        product = supply_delivery.supplied_item
        mapping["product"] = {"id": product.external_id} if product else None
        mapping["product_knowledge"] = (
            {"id": product.product_knowledge.external_id, "name": product.product_knowledge.name}
            if product and product.product_knowledge
            else None
        )
        cls.serialize_audit_users(mapping, obj)


class DVDMSRecordItemDeliveryCreateSpec(EMRResource):
    """Input spec for creating a record item delivery."""

    __model__ = DVDMSRecordItemDelivery
    __exclude__ = [
        "id",
        "record_delivery",
        "inward_record_item",
        "supply_delivery",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    inward_record_item: UUID4
    supply_delivery: UUID4
    quantity_dispatched: Decimal = Field(max_digits=12, decimal_places=2)
    quantity_accepted: Decimal = Field(max_digits=12, decimal_places=2)
    quantity_damaged: Decimal = Field(max_digits=12, decimal_places=2)
    quantity_short: Decimal = Field(max_digits=12, decimal_places=2)


class DVDMSRecordItemDeliveryUpdateSpec(EMRResource):
    """Input spec for updating a record item delivery."""

    __model__ = DVDMSRecordItemDelivery
    __exclude__ = [
        "id",
        "record_delivery",
        "inward_record_item",
        "supply_delivery",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    quantity_accepted: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)
    quantity_damaged: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)
    quantity_short: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)
    status: DVDMSRecordItemDeliveryStatus | None = None

import datetime

from care.emr.resources.base import EMRResource
from care.emr.resources.inventory.supply_request.request_order import (
    SupplyRequestOrderReadSpec,
)
from pydantic import UUID4

from care_dvdms.api.specs.dvdms_record_item_delivery import (
    DVDMSRecordItemDeliveryListSpec,
)
from care_dvdms.models.dvdms_record_delivery import (
    DVDMSRecordDelivery,
    DVDMSRecordDeliveryStatus,
)


class DVDMSRecordDeliveryListSpec(EMRResource):
    __model__ = DVDMSRecordDelivery
    __exclude__ = []

    id: UUID4 | None = None
    delivery_order: dict | None = None
    record_order: dict | None = None
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
        mapping["delivery_order"] = {
            "id": obj.delivery_order.external_id,
            "name": obj.delivery_order.name,
            "destination": obj.delivery_order.destination.name if obj.delivery_order.destination else None,
            "supplier": obj.delivery_order.supplier.name if obj.delivery_order.supplier else None,
        }
        mapping["record_order"] = (
            SupplyRequestOrderReadSpec.serialize(obj.record_order.order).to_json() if obj.record_order else None
        )
        cls.serialize_audit_users(mapping, obj)


class DVDMSRecordDeliveryDetailSpec(DVDMSRecordDeliveryListSpec):
    items: list[dict] | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["items"] = [
            DVDMSRecordItemDeliveryListSpec.serialize(item).to_json() for item in obj.item_deliveries.all()
        ]


class DVDMSRecordDeliveryCreateSpec(EMRResource):
    """Input spec for creating a record delivery."""

    __model__ = DVDMSRecordDelivery
    __exclude__ = [
        "id",
        "inward_record",
        "delivery_order",
        "record_order",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    delivery_order: UUID4
    record_order: UUID4 | None = None
    status: DVDMSRecordDeliveryStatus = DVDMSRecordDeliveryStatus.pending


class DVDMSRecordDeliveryUpdateSpec(EMRResource):
    """Input spec for updating a record delivery status."""

    __model__ = DVDMSRecordDelivery
    __exclude__ = [
        "id",
        "inward_record",
        "delivery_order",
        "record_order",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    status: DVDMSRecordDeliveryStatus

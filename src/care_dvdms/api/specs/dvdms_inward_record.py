import datetime

from care.emr.resources.base import EMRResource
from pydantic import UUID4

from care_dvdms.models.dvdms_inward_item_record import DVDMSInwardItemRecord
from care_dvdms.models.dvdms_inward_record import DVDMSInwardRecord


class DVDMSInwardItemRecordListSpec(EMRResource):
    __model__ = DVDMSInwardItemRecord
    __exclude__ = []

    id: UUID4 | None = None
    record_order_item: UUID4 | None = None
    drug_id: str | None = None
    drug_name: str | None = None
    brand_id: str | None = None
    batch: str | None = None
    manufacturer: str | None = None
    received_quantity: str | None = None
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
        mapping["record_order_item"] = obj.record_order_item.external_id if obj.record_order_item else None
        cls.serialize_audit_users(mapping, obj)


class DVDMSInwardRecordListSpec(EMRResource):
    __model__ = DVDMSInwardRecord
    __exclude__ = []

    id: UUID4 | None = None
    eaushadhi_issue_no: str | None = None
    outward_record: UUID4 | None = None
    eaushadhi_indent_no: str | None = None
    created_at: datetime.datetime | None = None
    eaushadhi_issue_status: str | None = None
    sync_log_id: str | None = None

    def to_json(self):
        return self.model_dump(mode="json")

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["outward_record"] = obj.outward_record.external_id if obj.outward_record else None
        mapping["eaushadhi_indent_no"] = obj.outward_record.eaushadhi_indent_no if obj.outward_record else None
        mapping["created_at"] = obj.created_date
        mapping["sync_log_id"] = str(obj.sync_log.external_id) if obj.sync_log else None


class DVDMSInwardRecordDetailSpec(DVDMSInwardRecordListSpec):
    items: list[dict] | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["items"] = [DVDMSInwardItemRecordListSpec.serialize(item).to_json() for item in obj.items.all()]


class DVDMSInwardRecordCreateSpec(EMRResource):
    """Input spec for creating an inwards record."""

    __model__ = DVDMSInwardRecord
    __exclude__ = [
        "id",
        "institute",
        "outward_record",
        "eaushadhi_issue_status",
        "sync_log",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    eaushadhi_issue_no: str
    outward_record: UUID4 | None = None

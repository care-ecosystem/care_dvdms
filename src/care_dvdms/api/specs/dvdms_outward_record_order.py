import datetime

from care.emr.resources.base import EMRResource
from pydantic import UUID4

from care_dvdms.models.dvdms_outward_record_order import DVDMSOutwardRecordOrder


class DVDMSOutwardRecordOrderListSpec(EMRResource):
    __model__ = DVDMSOutwardRecordOrder
    __exclude__ = []

    id: UUID4 | None = None
    record_order_id: UUID4 | None = None
    status: str | None = None
    eaushadhi_indent_no: str | None = None
    eaushadhi_indent_status: str | None = None
    sync_log_id: UUID4 | None = None
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    def to_json(self):
        return self.model_dump(mode="json")

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["record_order_id"] = obj.record_order.external_id if obj.record_order else None
        mapping["sync_log_id"] = obj.sync_log.external_id if obj.sync_log else None
        cls.serialize_audit_users(mapping, obj)

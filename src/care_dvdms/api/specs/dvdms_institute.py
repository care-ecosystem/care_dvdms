import datetime
from pydantic import UUID4

from care.emr.resources.base import EMRResource

from care_dvdms.models.dvdms_institute import DVDMSInstitute


class DVDMSInstituteListSpec(EMRResource):
    __model__ = DVDMSInstitute
    __exclude__ = []

    id: UUID4 | None = None
    facility_id: UUID4 | None = None
    eaushadhi_institute_id: str | None = None
    eaushadhi_institute_name: str | None = None
    eaushadhi_user_ref_id: str | None = None
    schema_version: str | None = None
    meta: dict | None = None
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    def to_json(self):
        return self.model_dump(mode="json")

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["facility_id"] = obj.facility.external_id if obj.facility else None
        mapping["meta"] = dict(obj.meta) if obj.meta else None
        cls.serialize_audit_users(mapping, obj)


class DVDMSInstituteCreateSpec(EMRResource):
    """Input spec for creating an institute. facility_id is derived from the URL path."""
    __model__ = DVDMSInstitute
    __exclude__ = ["id", "facility", "created_by", "updated_by", "created_date", "modified_date", "deleted", "external_id", "history"]

    eaushadhi_institute_id: str
    eaushadhi_institute_name: str
    eaushadhi_user_ref_id: str
    schema_version: str = "1.0"
    meta: dict | None = None


class DVDMSInstituteUpdateSpec(EMRResource):
    __model__ = DVDMSInstitute
    __exclude__ = ["id", "facility", "created_by", "updated_by", "created_date", "modified_date", "deleted", "external_id", "history"]

    eaushadhi_institute_id: str | None = None
    eaushadhi_institute_name: str | None = None
    eaushadhi_user_ref_id: str | None = None
    schema_version: str | None = None
    meta: dict | None = None

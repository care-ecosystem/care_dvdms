import datetime

from care.emr.resources.base import EMRResource
from pydantic import UUID4, Field

from care_dvdms.models.dvdms_store import DVDMSStore


class DVDMSStoreListSpec(EMRResource):
    __model__ = DVDMSStore
    __exclude__ = []

    id: UUID4 | None = None
    institute_id: UUID4 | None = None
    eaushadhi_store_id: str | None = None
    eaushadhi_store_name: str | None = None
    is_default: bool | None = None
    store: dict | None = None
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
        mapping["store"] = (
            {
                "id": obj.location.external_id,
                "name": obj.location.name,
                "form": obj.location.form,
            }
            if obj.location
            else None
        )
        cls.serialize_audit_users(mapping, obj)


class DVDMSStoreCreateSpec(EMRResource):
    """Input spec for creating a store mapping."""

    __model__ = DVDMSStore
    __exclude__ = [
        "id",
        "institute",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    store: UUID4
    eaushadhi_store_id: str = Field(max_length=50)
    eaushadhi_store_name: str = Field(max_length=255)
    is_default: bool = False


class DVDMSStoreUpdateSpec(EMRResource):
    """Input spec for updating a store mapping."""

    __model__ = DVDMSStore
    __exclude__ = [
        "id",
        "institute",
        "location",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "external_id",
        "history",
    ]

    store: UUID4 | None = None
    eaushadhi_store_id: str | None = Field(default=None, max_length=50)
    eaushadhi_store_name: str | None = None
    is_default: bool | None = None

import datetime

from django.core.exceptions import ObjectDoesNotExist
from pydantic import UUID4
from rest_framework.exceptions import ValidationError

from care.emr.resources.base import EMRResource
from care.facility.models import Facility

from care_myplugin.models.note import Note


class NoteReadSpec(EMRResource):
    """Spec used for list and retrieve responses."""

    __model__ = Note

    id: UUID4 | None = None
    facility_id: UUID4 | None = None
    title: str = ""
    content: str = ""
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["facility_id"] = obj.facility.external_id if obj.facility else None
        cls.serialize_audit_users(mapping, obj)


class NoteCreateSpec(EMRResource):
    """Spec used for POST (create) requests."""

    __model__ = Note

    __exclude__ = [
        "id",
        "external_id",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "history",
    ]

    facility_id: UUID4
    title: str
    content: str = ""

    def perform_extra_deserialization(self, is_update, obj):
        try:
            obj.facility = Facility.objects.get(external_id=self.facility_id)
        except ObjectDoesNotExist:
            raise ValidationError({"facility_id": ["Facility not found"]})

        obj.title = self.title
        obj.content = self.content
        return obj


class NoteUpdateSpec(EMRResource):
    """Spec used for PATCH (partial update) requests."""

    __model__ = Note

    title: str | None = None
    content: str | None = None

    def perform_extra_deserialization(self, is_update, obj):
        if self.title is not None:
            obj.title = self.title
        if self.content is not None:
            obj.content = self.content
        return obj

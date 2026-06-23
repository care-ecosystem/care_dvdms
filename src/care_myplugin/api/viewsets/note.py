from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404

from care_myplugin.api.specs.note import NoteCreateSpec, NoteReadSpec, NoteUpdateSpec
from care_myplugin.models.note import Note


class NoteFilters(filters.FilterSet):
    facility_id = filters.UUIDFilter(field_name="facility__external_id")

    class Meta:
        model = Note
        fields = ["facility_id"]


class NoteViewSet(
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRBaseViewSet,
):
    database_model = Note
    pydantic_model = NoteCreateSpec
    pydantic_read_model = NoteReadSpec
    pydantic_retrieve_model = NoteReadSpec
    pydantic_update_model = NoteUpdateSpec
    filterset_class = NoteFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date", "title"]

    def _authorize_facility(self, facility):
        if not AuthorizationController.call(
            "can_use_myplugin",  # TODO: rename to match your permission
            self.request.user,
            facility,
        ):
            raise PermissionDenied(
                "You are not authorized to use this plugin for this facility"
            )

    def authorize_create(self, instance):
        facility = get_object_or_404(Facility, external_id=instance.facility_id)
        self._authorize_facility(facility)

    def authorize_retrieve(self, instance):
        self._authorize_facility(instance.facility)

    def authorize_update(self, request_obj, model_instance):
        self._authorize_facility(model_instance.facility)

    def perform_create(self, instance):
        instance.created_by = self.request.user
        instance.updated_by = self.request.user
        instance.save()

    def perform_update(self, instance):
        instance.updated_by = self.request.user
        instance.save()

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("facility", "created_by", "updated_by")
        )
        if self.action == "list":
            facility_id = self.request.query_params.get("facility_id")
            if not facility_id:
                raise ValidationError({"facility_id": ["This field is required for list"]})
            facility = get_object_or_404(Facility, external_id=facility_id)
            self._authorize_facility(facility)
            return queryset.filter(facility=facility)
        return queryset

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.models.location import FacilityLocation
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care_dvdms.api.specs.dvdms_store import (
    DVDMSStoreCreateSpec,
    DVDMSStoreListSpec,
    DVDMSStoreUpdateSpec,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_store import DVDMSStore


class DVDMSStoreViewSet(EMRBaseViewSet):
    """
    ViewSet for managing DVDMS store mappings under an institute.
    Nested under facility + institute: /facility/{facility_id}/institute/{institute_id}/stores/
    """

    database_model = DVDMSStore
    lookup_field = "external_id"
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_institute(self):
        facility_id = self.kwargs.get("facility_id")
        institute_id = self.kwargs.get("institute_id")
        if not facility_id or not institute_id:
            raise NotFound("facility_id and institute_id are required")

        facility = get_object_or_404(Facility, external_id=facility_id)
        institute = get_object_or_404(DVDMSInstitute, external_id=institute_id, facility=facility, deleted=False)
        return institute

    def _authorize_facility(self, institute):
        if not AuthorizationController.call("can_use_dvdms_integration", self.request.user, institute.facility):
            raise PermissionDenied("You are not authorized to use DVDMS plugin for this facility")

    def _authorize_manage_facility(self, institute):
        if not AuthorizationController.call("can_manage_dvdms_integration", self.request.user, institute.facility):
            raise PermissionDenied("You are not authorized to manage DVDMS plugin for this facility")

    def get_queryset(self):
        institute = self.get_institute()
        self._authorize_facility(institute)
        return DVDMSStore.objects.filter(institute=institute, deleted=False).select_related(
            "institute", "location", "created_by", "updated_by"
        )

    def _resolve_location(self, institute, store_external_id, exclude_pk=None):
        """Look up the location and ensure it isn't already mapped for this institute."""
        location = get_object_or_404(
            FacilityLocation,
            external_id=store_external_id,
            facility=institute.facility,
            deleted=False,
        )
        conflict = DVDMSStore.objects.filter(institute=institute, location=location, deleted=False)
        if exclude_pk is not None:
            conflict = conflict.exclude(pk=exclude_pk)
        if conflict.exists():
            return None, Response(
                {"error": "This store is already mapped for this institute"},
                status=status.HTTP_409_CONFLICT,
            )
        return location, None

    def list(self, request, *args, **kwargs):
        """GET /facility/{facility_id}/institute/{institute_id}/stores/ - List store mappings"""
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        results = [DVDMSStoreListSpec.serialize(s).to_json() for s in page]
        return paginator.get_paginated_response(results)

    def create(self, request, *args, **kwargs):
        """POST /facility/{facility_id}/institute/{institute_id}/stores/ - Create store mapping"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        spec = DVDMSStoreCreateSpec(**request.data)

        location, error = self._resolve_location(institute, spec.store)
        if error:
            return error

        if spec.is_default:
            existing_default = DVDMSStore.objects.filter(institute=institute, is_default=True, deleted=False).first()
            if existing_default:
                return Response(
                    {"error": "Only one store can be marked as default per institute"},
                    status=status.HTTP_409_CONFLICT,
                )

        try:
            with transaction.atomic():
                store_mapping = DVDMSStore.objects.create(
                    institute=institute,
                    location=location,
                    eaushadhi_store_id=spec.eaushadhi_store_id,
                    eaushadhi_store_name=spec.eaushadhi_store_name,
                    is_default=spec.is_default,
                    created_by=request.user,
                    updated_by=request.user,
                )
        except IntegrityError as exc:
            if "uniq_default_store_per_institute" in str(exc):
                return Response(
                    {"error": "Only one store can be marked as default per institute"},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {"error": "This store is already mapped for this institute"},
                status=status.HTTP_409_CONFLICT,
            )

        store_mapping = DVDMSStore.objects.select_related("institute", "location", "created_by", "updated_by").get(
            pk=store_mapping.pk
        )

        result = DVDMSStoreListSpec.serialize(store_mapping)
        return Response(result.to_json(), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """PATCH /facility/{facility_id}/institute/{institute_id}/stores/{store_mapping_id}/ - Update store mapping"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        store_mapping_id = self.kwargs.get(self.lookup_field)
        store_mapping = get_object_or_404(
            DVDMSStore.objects.select_related("institute", "location", "created_by", "updated_by"),
            external_id=store_mapping_id,
            institute=institute,
            deleted=False,
        )

        spec = DVDMSStoreUpdateSpec(**request.data)

        if spec.is_default:
            existing_default = (
                DVDMSStore.objects.filter(institute=institute, is_default=True, deleted=False)
                .exclude(pk=store_mapping.pk)
                .first()
            )
            if existing_default:
                return Response(
                    {"error": "Only one store can be marked as default per institute"},
                    status=status.HTTP_409_CONFLICT,
                )

        if spec.store is not None:
            location, error = self._resolve_location(institute, spec.store, exclude_pk=store_mapping.pk)
            if error:
                return error
            store_mapping.location = location
        if spec.eaushadhi_store_id is not None:
            store_mapping.eaushadhi_store_id = spec.eaushadhi_store_id
        if spec.eaushadhi_store_name is not None:
            store_mapping.eaushadhi_store_name = spec.eaushadhi_store_name
        if spec.is_default is not None:
            store_mapping.is_default = spec.is_default
        store_mapping.updated_by = request.user

        try:
            with transaction.atomic():
                store_mapping.save()
        except IntegrityError as exc:
            if "uniq_default_store_per_institute" in str(exc):
                return Response(
                    {"error": "Only one store can be marked as default per institute"},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {"error": "This store is already mapped for this institute"},
                status=status.HTTP_409_CONFLICT,
            )

        result = DVDMSStoreListSpec.serialize(store_mapping)
        return Response(result.to_json(), status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """DELETE /facility/{facility_id}/institute/{institute_id}/stores/{store_mapping_id}/ - Delete store mapping"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        store_mapping_id = self.kwargs.get(self.lookup_field)
        store_mapping = get_object_or_404(
            DVDMSStore,
            external_id=store_mapping_id,
            institute=institute,
            deleted=False,
        )

        store_mapping.delete()
        return Response(
            {"message": "Store mapping deleted successfully"},
            status=status.HTTP_200_OK,
        )

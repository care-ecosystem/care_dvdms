from care.emr.api.viewsets.base import EMRBaseViewSet
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from care_dvdms.api.specs.dvdms_institute import (
    DVDMSInstituteCreateSpec,
    DVDMSInstituteListSpec,
    DVDMSInstituteUpdateSpec,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute


class DVDMSInstituteViewSet(EMRBaseViewSet):
    """
    Nested viewset for managing DVDMS institute at facility scope.
    Path: /facility/{facility_external_id}/institute/

    Since each facility has at most one institute, this viewset
    handles GET/POST/PATCH for the institute within a facility context.
    """

    database_model = DVDMSInstitute
    lookup_field = "external_id"

    def get_facility(self):
        facility_external_id = self.kwargs.get("facility_external_id")
        if not facility_external_id:
            raise NotFound("facility_external_id not provided")
        facility = get_object_or_404(Facility, external_id=facility_external_id)
        return facility

    def _authorize_facility(self, facility):
        if not AuthorizationController.call("can_use_dvdms_integration", self.request.user, facility):
            raise PermissionDenied("You are not authorized to use DVDMS plugin for this facility")

    def _authorize_manage_facility(self, facility):
        if not AuthorizationController.call("can_manage_dvdms_integration", self.request.user, facility):
            raise PermissionDenied("You are not authorized to manage DVDMS plugin for this facility")

    def get_queryset(self):
        facility = self.get_facility()
        self._authorize_facility(facility)
        return DVDMSInstitute.objects.filter(facility=facility, deleted=False).select_related(
            "facility", "created_by", "updated_by"
        )

    def list(self, request, *args, **kwargs):
        """GET /facility/{facility_external_id}/institute/ - Get institute for facility"""
        queryset = self.get_queryset()
        institute = queryset.first()

        if not institute:
            return Response(
                {"error": "No institute found for this facility"},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = DVDMSInstituteListSpec.serialize(institute)
        return Response(result.to_json(), status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """POST /facility/{facility_external_id}/institute/ - Create institute for facility"""
        facility = self.get_facility()
        self._authorize_manage_facility(facility)

        if DVDMSInstitute.objects.filter(facility=facility, deleted=False).exists():
            return Response(
                {"error": "DVDMS institute mapping already exists for this facility"},
                status=status.HTTP_409_CONFLICT,
            )

        spec = DVDMSInstituteCreateSpec(**request.data)

        if DVDMSInstitute.objects.filter(eaushadhi_institute_id=spec.eaushadhi_institute_id).exists():
            return Response(
                {"error": "eaushadhi_institute_id is already in use by another facility"},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            with transaction.atomic():
                institute = DVDMSInstitute.objects.create(
                    facility=facility,
                    eaushadhi_institute_id=spec.eaushadhi_institute_id,
                    eaushadhi_institute_name=spec.eaushadhi_institute_name,
                    eaushadhi_user_ref_id=spec.eaushadhi_user_ref_id,
                    schema_version=spec.schema_version,
                    meta=spec.meta or {},
                    created_by=request.user,
                    updated_by=request.user,
                )
        except IntegrityError:
            return Response(
                {"error": "DVDMS institute mapping already exists for this facility"},
                status=status.HTTP_409_CONFLICT,
            )

        institute = DVDMSInstitute.objects.select_related("facility", "created_by", "updated_by").get(pk=institute.pk)

        result = DVDMSInstituteListSpec.serialize(institute)
        return Response(result.to_json(), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """PATCH /facility/{facility_external_id}/institute/ - Update institute for facility"""
        queryset = self.get_queryset()
        instance = queryset.first()

        if not instance:
            return Response(
                {"error": "No institute found for this facility"},
                status=status.HTTP_404_NOT_FOUND,
            )

        self._authorize_manage_facility(instance.facility)

        spec = DVDMSInstituteUpdateSpec(**request.data)

        update_fields = []

        if spec.eaushadhi_institute_id is not None:
            if (
                DVDMSInstitute.objects.filter(eaushadhi_institute_id=spec.eaushadhi_institute_id)
                .exclude(pk=instance.pk)
                .exists()
            ):
                return Response(
                    {"error": "eaushadhi_institute_id is already in use by another facility"},
                    status=status.HTTP_409_CONFLICT,
                )
            instance.eaushadhi_institute_id = spec.eaushadhi_institute_id
            update_fields.append("eaushadhi_institute_id")

        if spec.eaushadhi_institute_name is not None:
            instance.eaushadhi_institute_name = spec.eaushadhi_institute_name
            update_fields.append("eaushadhi_institute_name")

        if spec.eaushadhi_user_ref_id is not None:
            instance.eaushadhi_user_ref_id = spec.eaushadhi_user_ref_id
            update_fields.append("eaushadhi_user_ref_id")

        if spec.schema_version is not None:
            instance.schema_version = spec.schema_version
            update_fields.append("schema_version")

        if spec.meta is not None:
            instance.meta = spec.meta
            update_fields.append("meta")

        if update_fields:
            instance.updated_by = request.user
            update_fields += ["updated_by", "modified_date"]
            try:
                with transaction.atomic():
                    instance.save(update_fields=update_fields)
            except IntegrityError:
                return Response(
                    {"error": "eaushadhi_institute_id is already in use by another facility"},
                    status=status.HTTP_409_CONFLICT,
                )

        instance = DVDMSInstitute.objects.select_related("facility", "created_by", "updated_by").get(pk=instance.pk)

        result = DVDMSInstituteListSpec.serialize(instance)
        return Response(result.to_json(), status=status.HTTP_200_OK)

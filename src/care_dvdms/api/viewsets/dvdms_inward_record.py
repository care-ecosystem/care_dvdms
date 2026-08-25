from care.emr.api.viewsets.base import EMRBaseViewSet
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care_dvdms.api.specs.dvdms_inward_record import (
    DVDMSInwardRecordCreateSpec,
    DVDMSInwardRecordDetailSpec,
    DVDMSInwardRecordListSpec,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_inward_record import DVDMSInwardRecord
from care_dvdms.models.dvdms_outward_record_order import DVDMSOutwardRecordOrder

SELECT_RELATED_FIELDS = (
    "outward_record",
    "outward_record__record_order",
    "sync_log",
)


class DVDMSInwardRecordViewSet(EMRBaseViewSet):
    """
    ViewSet for managing DVDMS inwards records under an institute.
    Nested under: /institute/{institute_id}/record_inwards/
    """

    database_model = DVDMSInwardRecord
    lookup_field = "external_id"
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_institute(self):
        institute_id = self.kwargs.get("institute_id")
        if not institute_id:
            raise NotFound("institute_id is required")
        return get_object_or_404(DVDMSInstitute, external_id=institute_id, deleted=False)

    def _authorize_facility(self, institute):
        if not AuthorizationController.call("can_use_dvdms_integration", self.request.user, institute.facility):
            raise PermissionDenied("You are not authorized to use DVDMS plugin for this facility")

    def _authorize_manage_facility(self, institute):
        if not AuthorizationController.call("can_manage_dvdms_integration", self.request.user, institute.facility):
            raise PermissionDenied("You are not authorized to manage DVDMS plugin for this facility")

    def get_queryset(self):
        institute = self.get_institute()
        self._authorize_facility(institute)
        return DVDMSInwardRecord.objects.filter(
            outward_record__record_order__institute=institute, deleted=False
        ).select_related(*SELECT_RELATED_FIELDS)

    def list(self, request, *args, **kwargs):
        """GET .../record_inwards/ - List inwards records for an institute"""
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        results = [DVDMSInwardRecordListSpec.serialize(o).to_json() for o in page]
        return paginator.get_paginated_response(results)

    def retrieve(self, request, *args, **kwargs):
        """GET .../record_inwards/{record_inward_id}/ - Get inward record with item-level details"""
        inward_record = get_object_or_404(
            self.get_queryset().prefetch_related("items", "items__record_order_item"),
            external_id=self.kwargs.get(self.lookup_field),
        )
        result = DVDMSInwardRecordDetailSpec.serialize(inward_record)
        return Response(result.to_json(), status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """POST .../record_inwards/ - Create an inwards record"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        spec = DVDMSInwardRecordCreateSpec(**request.data)

        outward_record = get_object_or_404(
            DVDMSOutwardRecordOrder,
            external_id=spec.outward_record,
            record_order__institute=institute,
            deleted=False,
        )

        try:
            inward_record = DVDMSInwardRecord.objects.create(
                outward_record=outward_record,
                eaushadhi_issue_no=spec.eaushadhi_issue_no,
                created_by=request.user,
                updated_by=request.user,
            )
        except IntegrityError:
            return Response(
                {
                    "error": "This issue number is already recorded for this outward record",
                    "code": "ISSUE_NO_EXISTS",
                },
                status=status.HTTP_409_CONFLICT,
            )

        result = DVDMSInwardRecordListSpec.serialize(inward_record)
        return Response(result.to_json(), status=status.HTTP_201_CREATED)

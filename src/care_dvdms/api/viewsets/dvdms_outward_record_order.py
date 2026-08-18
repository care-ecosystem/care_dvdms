from care.emr.api.viewsets.base import EMRBaseViewSet
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care_dvdms.api.services.dvdms_outward_record_services import track_indent
from care_dvdms.api.specs.dvdms_outward_record_order import (
    DVDMSOutwardRecordOrderListSpec,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_outward_record_order import DVDMSOutwardRecordOrder
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder

SELECT_RELATED_FIELDS = (
    "record_order",
    "sync_log",
    "created_by",
    "updated_by",
)


class DVDMSOutwardRecordOrderViewSet(EMRBaseViewSet):
    """
    ViewSet for managing DVDMS outward record orders under a record order.
    Nested under: /institute/{institute_id}/record_order/{record_order_id}/outward/
    """

    database_model = DVDMSOutwardRecordOrder
    lookup_field = "external_id"
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_institute(self):
        institute_id = self.kwargs.get("institute_id")
        if not institute_id:
            raise NotFound("institute_id is required")
        return get_object_or_404(DVDMSInstitute, external_id=institute_id, deleted=False)

    def get_record_order(self, institute):
        record_order_id = self.kwargs.get("record_order_id")
        if not record_order_id:
            raise NotFound("record_order_id is required")
        return get_object_or_404(
            DVDMSRecordOrder,
            external_id=record_order_id,
            institute=institute,
            deleted=False,
        )

    def _authorize_facility(self, institute):
        if not AuthorizationController.call("can_use_dvdms_integration", self.request.user, institute.facility):
            raise PermissionDenied("You are not authorized to use DVDMS plugin for this facility")

    def _authorize_manage_facility(self, institute):
        if not AuthorizationController.call("can_manage_dvdms_integration", self.request.user, institute.facility):
            raise PermissionDenied("You are not authorized to manage DVDMS plugin for this facility")

    def get_queryset(self):
        institute = self.get_institute()
        self._authorize_facility(institute)
        record_order = self.get_record_order(institute)
        return DVDMSOutwardRecordOrder.objects.filter(record_order=record_order, deleted=False).select_related(
            *SELECT_RELATED_FIELDS
        )

    def list(self, request, *args, **kwargs):
        """GET .../outward/ - List outward records for a record order"""
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        results = [DVDMSOutwardRecordOrderListSpec.serialize(o).to_json() for o in page]
        return paginator.get_paginated_response(results)

    def fetch_inwards(self, request, *args, **kwargs):
        """POST .../outward/fetch-inwards/ - Fetch inwards/issue status from DVDMS"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)
        record_order = self.get_record_order(institute)

        outward_record = (
            DVDMSOutwardRecordOrder.objects.filter(record_order=record_order, deleted=False)
            .select_related(*SELECT_RELATED_FIELDS)
            .first()
        )
        if outward_record is None:
            return Response(
                {
                    "error": "Cannot fetch inwards: outwards record not found",
                    "code": "OUTWARDS_RECORD_NOT_FOUND",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        outward_record = track_indent(institute, outward_record, request.user)

        result = DVDMSOutwardRecordOrderListSpec.serialize(outward_record)
        return Response(result.to_json(), status=status.HTTP_200_OK)

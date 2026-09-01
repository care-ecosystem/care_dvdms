from care.emr.api.viewsets.base import EMRBaseViewSet
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care_dvdms.api.services.dvdms_client import get_status_code
from care_dvdms.api.services.dvdms_indent_services import build_track_indent_params, track_indent
from care_dvdms.api.specs.dvdms_outward_record_order import (
    DVDMSOutwardRecordOrderListSpec,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_outward_record_order import DVDMSOutwardRecordOrder
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder
from care_dvdms.models.dvdms_sync_log import (
    DVDMSSyncLog,
    DVDMSSyncRequestStatus,
    DVDMSSyncTriggeredBy,
    DVDMSSyncType,
)
from care_dvdms.tasks import prefill_inward_record_task

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

        if not outward_record.eaushadhi_indent_no:
            return Response(
                {
                    "error": "Cannot fetch inwards: indent has not been saved to DVDMS yet",
                    "code": "INDENT_NOT_SAVED",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        params = build_track_indent_params(outward_record)
        sync_log = DVDMSSyncLog.objects.create(
            institute=institute,
            triggered_by=DVDMSSyncTriggeredBy.user,
            sync_type=DVDMSSyncType.track_indent,
            request_status=DVDMSSyncRequestStatus.pending,
            request_payload=params,
            created_by=request.user,
            updated_by=request.user,
        )

        try:
            response, http_status_code = track_indent(params)
        except Exception as exc:
            sync_log.request_status = DVDMSSyncRequestStatus.failure
            sync_log.error_detail = str(exc)
            sync_log.http_status_code = get_status_code(exc)
            sync_log.save(update_fields=["request_status", "error_detail", "http_status_code", "modified_date"])
            return Response(
                {
                    "error": "DVDMS could not find this indent. Check the store ID and indent number.",
                    "code": "INDENT_NOT_FOUND",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            sync_log.request_status = DVDMSSyncRequestStatus.success
            sync_log.response_payload = response
            sync_log.http_status_code = http_status_code
            sync_log.save(update_fields=["request_status", "response_payload", "http_status_code", "modified_date"])

            previous_status = outward_record.eaushadhi_indent_status
            outward_record.sync_log = sync_log
            outward_record.eaushadhi_indent_status = response.get("data", {}).get("indentStatus")
            outward_record.updated_by = request.user
            outward_record.save(update_fields=["sync_log", "eaushadhi_indent_status", "updated_by", "modified_date"])

            if outward_record.eaushadhi_indent_status == "Issued" and previous_status != "Issued":
                institute_id = str(institute.external_id)
                outward_record_id = str(outward_record.external_id)
                user_id = str(request.user.external_id)
                transaction.on_commit(
                    lambda: prefill_inward_record_task.delay(
                        institute_id=institute_id,
                        outward_record_id=outward_record_id,
                        user_id=user_id,
                    )
                )

            result = DVDMSOutwardRecordOrderListSpec.serialize(outward_record)
            return Response(result.to_json(), status=status.HTTP_200_OK)

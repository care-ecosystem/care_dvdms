from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.models.supply_request import RequestOrder
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care_dvdms.api.specs.dvdms_record_order import (
    DVDMSRecordOrderCreateSpec,
    DVDMSRecordOrderListSpec,
    DVDMSRecordOrderUpdateSpec,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder
from care_dvdms.models.dvdms_store import DVDMSStore
from care_dvdms.models.dvdms_supplier import DVDMSSupplier


class DVDMSRecordOrderFilters(filters.FilterSet):
    order = filters.UUIDFilter(field_name="order__external_id")
    status = filters.CharFilter(field_name="status")


class DVDMSRecordOrderViewSet(EMRBaseViewSet):
    """
    ViewSet for managing DVDMS record orders under an institute.
    Nested under: /institute/{institute_id}/record_order/
    """

    database_model = DVDMSRecordOrder
    lookup_field = "external_id"
    filterset_class = DVDMSRecordOrderFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
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
        return DVDMSRecordOrder.objects.filter(institute=institute, deleted=False).select_related(
            "institute",
            "order",
            "institute_store",
            "institute_store__location",
            "institute_supplier",
            "institute_supplier__supplier",
            "created_by",
            "updated_by",
        )

    def list(self, request, *args, **kwargs):
        """GET /institute/{institute_id}/record_order/ - List record orders"""
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        results = [DVDMSRecordOrderListSpec.serialize(o).to_json() for o in page]
        return paginator.get_paginated_response(results)

    def create(self, request, *args, **kwargs):
        """POST /institute/{institute_id}/record_order/ - Create record order"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        spec = DVDMSRecordOrderCreateSpec(**request.data)

        order = get_object_or_404(
            RequestOrder, external_id=spec.order, destination__facility=institute.facility
        )
        institute_store = get_object_or_404(
            DVDMSStore.objects.select_related("location"),
            external_id=spec.institute_store,
            institute=institute,
            deleted=False,
        )
        institute_supplier = get_object_or_404(
            DVDMSSupplier.objects.select_related("supplier"),
            external_id=spec.institute_supplier,
            institute=institute,
            deleted=False,
        )

        record_order = DVDMSRecordOrder.objects.create(
            institute=institute,
            name=spec.name,
            order=order,
            institute_store=institute_store,
            institute_supplier=institute_supplier,
            status=spec.status,
            created_by=request.user,
            updated_by=request.user,
        )

        result = DVDMSRecordOrderListSpec.serialize(record_order)
        return Response(result.to_json(), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """PATCH /institute/{institute_id}/record_order/{record_order_id}/ - Update record order"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        record_order_id = self.kwargs.get(self.lookup_field)
        record_order = get_object_or_404(
            DVDMSRecordOrder.objects.select_related(
                "institute",
                "order",
                "institute_store",
                "institute_store__location",
                "institute_supplier",
                "institute_supplier__supplier",
                "created_by",
                "updated_by",
            ),
            external_id=record_order_id,
            institute=institute,
            deleted=False,
        )

        spec = DVDMSRecordOrderUpdateSpec(**request.data)
        if spec.status is not None:
            record_order.status = spec.status
        record_order.updated_by = request.user
        record_order.save()

        result = DVDMSRecordOrderListSpec.serialize(record_order)
        return Response(result.to_json(), status=status.HTTP_200_OK)

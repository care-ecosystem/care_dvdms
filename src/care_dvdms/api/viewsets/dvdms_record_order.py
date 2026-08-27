from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.models.supply_request import RequestOrder
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
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
from care_dvdms.models.dvdms_outward_record_order import DVDMSOutwardRecordOrder, DVDMSOutwardRecordOrderStatus
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder, DVDMSRecordOrderStatus
from care_dvdms.models.dvdms_store import DVDMSStore
from care_dvdms.models.dvdms_supplier import DVDMSSupplier
from care_dvdms.tasks import save_indent_task


class DVDMSRecordOrderFilters(filters.FilterSet):
    order = filters.UUIDFilter(field_name="order__external_id")
    status = filters.CharFilter(field_name="status")
    care_indent_no = filters.CharFilter(field_name="care_indent_no")


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

        order = get_object_or_404(RequestOrder, external_id=spec.order, destination__facility=institute.facility)
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
            supplier__deleted=False,
            supplier__org_type="product_supplier",
        )

        try:
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
        except IntegrityError:
            return Response(
                {"error": "This order is already linked to a record order."},
                status=status.HTTP_409_CONFLICT,
            )

        result = DVDMSRecordOrderListSpec.serialize(record_order)
        return Response(result.to_json(), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """PATCH /institute/{institute_id}/record_order/{record_order_id}/ - Update record order"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        record_order_id = self.kwargs.get(self.lookup_field)
        spec = DVDMSRecordOrderUpdateSpec(**request.data)

        with transaction.atomic():
            record_order = get_object_or_404(
                DVDMSRecordOrder.objects.select_for_update(of=("self",)).select_related(
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

            if spec.status == DVDMSRecordOrderStatus.cancelled and record_order.status != DVDMSRecordOrderStatus.draft:
                return Response(
                    {"error": "Only a draft record order can be cancelled"},
                    status=status.HTTP_409_CONFLICT,
                )

            if (
                spec.name is not None or spec.institute_supplier is not None
            ) and record_order.status != DVDMSRecordOrderStatus.draft:
                return Response(
                    {"error": "Name and supplier can only be changed while the record order is in draft"},
                    status=status.HTTP_409_CONFLICT,
                )

            newly_approved = (
                spec.status == DVDMSRecordOrderStatus.approved
                and record_order.status != DVDMSRecordOrderStatus.approved
            )
            if newly_approved and not record_order.item_orders.filter(deleted=False).exists():
                return Response(
                    {"error": "Cannot approve an order with no items"},
                    status=status.HTTP_409_CONFLICT,
                )
            update_fields = ["updated_by", "modified_date"]
            if spec.name is not None:
                record_order.name = spec.name
                update_fields.append("name")
            if spec.institute_supplier is not None:
                record_order.institute_supplier = get_object_or_404(
                    DVDMSSupplier.objects.select_related("supplier"),
                    external_id=spec.institute_supplier,
                    institute=institute,
                    deleted=False,
                    supplier__deleted=False,
                    supplier__org_type="product_supplier",
                )
                update_fields.append("institute_supplier")
            if spec.status is not None:
                record_order.status = spec.status
                update_fields.append("status")
            record_order.updated_by = request.user
            record_order.save(update_fields=update_fields)

            if newly_approved:
                DVDMSOutwardRecordOrder.objects.get_or_create(
                    record_order=record_order,
                    defaults={
                        "status": DVDMSOutwardRecordOrderStatus.created,
                        "created_by": request.user,
                        "updated_by": request.user,
                    },
                )
                approved_institute_id = str(institute.external_id)
                approved_record_order_id = str(record_order.external_id)
                approved_by_user_id = str(request.user.external_id)
                transaction.on_commit(
                    lambda: save_indent_task.delay(
                        institute_id=approved_institute_id,
                        record_order_id=approved_record_order_id,
                        user_id=approved_by_user_id,
                    )
                )

        result = DVDMSRecordOrderListSpec.serialize(record_order)
        return Response(result.to_json(), status=status.HTTP_200_OK)

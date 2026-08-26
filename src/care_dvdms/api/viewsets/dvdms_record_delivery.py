from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.models.supply_delivery import DeliveryOrder
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.db import IntegrityError
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care_dvdms.api.specs.dvdms_record_delivery import (
    DVDMSRecordDeliveryCreateSpec,
    DVDMSRecordDeliveryDetailSpec,
    DVDMSRecordDeliveryListSpec,
    DVDMSRecordDeliveryUpdateSpec,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_inward_record import DVDMSInwardRecord
from care_dvdms.models.dvdms_record_delivery import DVDMSRecordDelivery
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder

SELECT_RELATED_FIELDS = (
    "inward_record",
    "delivery_order",
    "delivery_order__destination",
    "delivery_order__supplier",
    "record_order",
    "record_order__order",
    "created_by",
    "updated_by",
)


class DVDMSRecordDeliveryFilters(filters.FilterSet):
    delivery_order = filters.UUIDFilter(field_name="delivery_order__external_id")


class DVDMSRecordDeliveryViewSet(EMRBaseViewSet):
    """
    ViewSet for managing DVDMS record deliveries under an inward record.
    Nested under: /institute/{institute_id}/record_inwards/{record_inward_id}/delivery/
    """

    database_model = DVDMSRecordDelivery
    lookup_field = "external_id"
    filterset_class = DVDMSRecordDeliveryFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_institute(self):
        institute_id = self.kwargs.get("institute_id")
        if not institute_id:
            raise NotFound("institute_id is required")
        return get_object_or_404(DVDMSInstitute, external_id=institute_id, deleted=False)

    def get_inward_record(self, institute):
        record_inward_id = self.kwargs.get("record_inward_id")
        if not record_inward_id:
            raise NotFound("record_inward_id is required")
        return get_object_or_404(
            DVDMSInwardRecord,
            external_id=record_inward_id,
            outward_record__record_order__institute=institute,
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
        inward_record = self.get_inward_record(institute)
        return DVDMSRecordDelivery.objects.filter(inward_record=inward_record, deleted=False).select_related(
            *SELECT_RELATED_FIELDS
        )

    def list(self, request, *args, **kwargs):
        """GET .../delivery/ - List record deliveries for an inward record"""
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        results = [DVDMSRecordDeliveryListSpec.serialize(o).to_json() for o in page]
        return paginator.get_paginated_response(results)

    def retrieve(self, request, *args, **kwargs):
        """GET .../delivery/{record_delivery_id}/ - Get record delivery with item-level details"""
        record_delivery = get_object_or_404(
            self.get_queryset().prefetch_related(
                "item_deliveries",
                "item_deliveries__inward_record_item",
                "item_deliveries__supply_delivery",
                "item_deliveries__supply_delivery__supplied_item",
                "item_deliveries__supply_delivery__supplied_item__product_knowledge",
            ),
            external_id=self.kwargs.get(self.lookup_field),
        )
        result = DVDMSRecordDeliveryDetailSpec.serialize(record_delivery)
        return Response(result.to_json(), status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """POST .../delivery/ - Create a record delivery"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)
        inward_record = self.get_inward_record(institute)

        spec = DVDMSRecordDeliveryCreateSpec(**request.data)

        record_order = get_object_or_404(
            DVDMSRecordOrder,
            external_id=spec.record_order,
            institute=institute,
            deleted=False,
        )
        if record_order.id != inward_record.outward_record.record_order_id:
            return Response(
                {"error": "record_order does not match the record order for this inward record"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        delivery_order = get_object_or_404(
            DeliveryOrder,
            external_id=spec.delivery_order,
            destination__facility=institute.facility,
        )

        try:
            record_delivery = DVDMSRecordDelivery.objects.create(
                inward_record=inward_record,
                record_order=record_order,
                delivery_order=delivery_order,
                status=spec.status,
                created_by=request.user,
                updated_by=request.user,
            )
        except IntegrityError:
            return Response(
                {
                    "error": "delivery_order is already linked to an inward_record",
                    "code": "DELIVERY_ORDER_ALREADY_LINKED",
                },
                status=status.HTTP_409_CONFLICT,
            )

        result = DVDMSRecordDeliveryListSpec.serialize(record_delivery)
        return Response(result.to_json(), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """PATCH .../delivery/{record_delivery_id}/ - Update record delivery status"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        record_delivery_id = self.kwargs.get(self.lookup_field)
        spec = DVDMSRecordDeliveryUpdateSpec(**request.data)

        record_delivery = get_object_or_404(
            self.get_queryset(),
            external_id=record_delivery_id,
        )
        record_delivery.status = spec.status
        record_delivery.updated_by = request.user
        record_delivery.save(update_fields=["status", "updated_by", "modified_date"])

        result = DVDMSRecordDeliveryListSpec.serialize(record_delivery)
        return Response(result.to_json(), status=status.HTTP_200_OK)

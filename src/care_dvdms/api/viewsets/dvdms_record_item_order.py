from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.models.supply_request import SupplyRequest
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.db import transaction
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care_dvdms.api.specs.dvdms_record_item_order import (
    DVDMSRecordItemOrderCreateSpec,
    DVDMSRecordItemOrderListSpec,
    DVDMSRecordItemOrderUpdateSpec,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_record_item_order import DVDMSDrug, DVDMSRecordItemOrder
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder

SELECT_RELATED_FIELDS = (
    "institute",
    "record_order",
    "supply_request",
    "supply_request__item",
    "supply_request__order",
    "drug",
    "created_by",
    "updated_by",
)


class DVDMSRecordItemOrderFilters(filters.FilterSet):
    order = filters.UUIDFilter(field_name="record_order__order__external_id")


class DVDMSRecordItemOrderViewSet(EMRBaseViewSet):
    """
    ViewSet for managing DVDMS record item orders under a record order.
    Nested under: /institute/{institute_id}/record_order/{record_order_id}/item/
    """

    database_model = DVDMSRecordItemOrder
    lookup_field = "external_id"
    filterset_class = DVDMSRecordItemOrderFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
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
        return DVDMSRecordItemOrder.objects.filter(
            institute=institute, record_order=record_order, deleted=False
        ).select_related(*SELECT_RELATED_FIELDS)

    def list(self, request, *args, **kwargs):
        """GET .../item/ - List record item orders"""
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        results = [DVDMSRecordItemOrderListSpec.serialize(o).to_json() for o in page]
        return paginator.get_paginated_response(results)

    def create(self, request, *args, **kwargs):
        """POST .../item/ - Create record item order"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)
        record_order = self.get_record_order(institute)

        spec = DVDMSRecordItemOrderCreateSpec(**request.data)

        supply_request = get_object_or_404(
            SupplyRequest.objects.select_related("item", "order"),
            external_id=spec.supply_request,
            order=record_order.order,
        )

        with transaction.atomic():
            drug = DVDMSDrug.objects.create(
                drug_id=spec.drug.id,
                name=spec.drug.name,
                brand_id=spec.drug.brand_id,
                group_id=spec.drug.group_id,
                sub_group_id=spec.drug.sub_group_id,
                unit_id=spec.drug.unit_id,
                drug_category=spec.drug.drug_category,
            )
            item_order = DVDMSRecordItemOrder.objects.create(
                institute=institute,
                record_order=record_order,
                supply_request=supply_request,
                drug=drug,
                created_by=request.user,
                updated_by=request.user,
            )

        result = DVDMSRecordItemOrderListSpec.serialize(item_order)
        return Response(result.to_json(), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """PATCH .../item/{record_order_item_id}/ - Update record item order"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)
        record_order = self.get_record_order(institute)

        item_order_id = self.kwargs.get(self.lookup_field)
        item_order = get_object_or_404(
            DVDMSRecordItemOrder.objects.select_related(*SELECT_RELATED_FIELDS),
            external_id=item_order_id,
            institute=institute,
            record_order=record_order,
            deleted=False,
        )

        spec = DVDMSRecordItemOrderUpdateSpec(**request.data)
        if spec.drug is not None:
            drug = item_order.drug
            drug.drug_id = spec.drug.id
            drug.name = spec.drug.name
            drug.brand_id = spec.drug.brand_id
            drug.group_id = spec.drug.group_id
            drug.sub_group_id = spec.drug.sub_group_id
            drug.unit_id = spec.drug.unit_id
            drug.drug_category = spec.drug.drug_category
            drug.save()

        item_order.updated_by = request.user
        item_order.save()

        result = DVDMSRecordItemOrderListSpec.serialize(item_order)
        return Response(result.to_json(), status=status.HTTP_200_OK)

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRListMixin
from care.emr.models.supply_request import RequestOrder, SupplyRequest
from care.emr.resources.inventory.supply_request.request_order import (
    SUPPLY_REQUEST_ORDER_COMPLETED_STATUSES,
)
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.db.models import Count, OuterRef, Subquery
from django_filters import rest_framework as filters
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter

from care_dvdms.api.specs.dvdms_available_request_order import AvailableRequestOrderListSpec
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_record_order import INACTIVE_RECORD_ORDER_STATUSES, DVDMSRecordOrder


class AvailableRequestOrderFilters(filters.FilterSet):
    priority = filters.CharFilter(field_name="priority", lookup_expr="iexact")
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    supplier = filters.UUIDFilter(field_name="supplier__external_id")


class AvailableRequestOrderViewSet(EMRListMixin, EMRBaseViewSet):
    """
    List RequestOrders not mapped to any active DVDMS record order.
    Nested under: /institute/{institute_id}/available_request_orders/
    """

    database_model = RequestOrder
    pydantic_read_model = AvailableRequestOrderListSpec
    filterset_class = AvailableRequestOrderFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    item_count_subquery = Subquery(
        SupplyRequest.objects.filter(order=OuterRef("pk"), deleted=False)
        .order_by()
        .values("order")
        .annotate(count=Count("id"))
        .values("count")
    )

    def get_institute(self):
        institute_id = self.kwargs.get("institute_id")
        if not institute_id:
            raise NotFound("institute_id is required")
        return get_object_or_404(DVDMSInstitute, external_id=institute_id, deleted=False)

    def _authorize_facility(self, institute):
        if not AuthorizationController.call("can_use_dvdms_integration", self.request.user, institute.facility):
            raise PermissionDenied("You are not authorized to use DVDMS plugin for this facility")

    def get_queryset(self):
        institute = self.get_institute()
        self._authorize_facility(institute)
        mapped_order_ids = (
            DVDMSRecordOrder.objects.filter(deleted=False)
            .exclude(status__in=INACTIVE_RECORD_ORDER_STATUSES)
            .values("order_id")
        )
        return (
            RequestOrder.objects.filter(destination__facility_id=institute.facility_id, deleted=False)
            .exclude(id__in=mapped_order_ids)
            .exclude(status__in=SUPPLY_REQUEST_ORDER_COMPLETED_STATUSES)
            .select_related("supplier", "origin", "destination")
            .annotate(item_count=self.item_count_subquery)
        )

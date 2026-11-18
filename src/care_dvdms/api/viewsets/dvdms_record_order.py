from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.models.supply_request import RequestOrder
from care.emr.resources.inventory.supply_request.request_order import (
    SupplyRequestIntentOptions,
    SupplyRequestOrderReadSpec,
)
from care.security.authorization.base import AuthorizationController
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
from django.db.models import Case, CharField, Exists, F, FilteredRelation, OuterRef, Q, Value, When
from django.db.models.functions import Coalesce
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
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
from care_dvdms.utils.request_order import require_pending_request_order


# Tabs, by the status shown (see EFFECTIVE_STATUS): unsent is on our side, sent is with DVDMS.
TAB_STATUSES = {
    "unsent": ["draft", "failed", "cancelled"],
    "sent": ["approved", "submitted", "issue_in_process", "issued"],
    "completed": ["completed", "rejected"],
}

# Request orders that are listed even without a record order, and count as draft.
UNSENT_REQUEST_ORDER_STATUSES = ["draft", "pending"]

# The list is built from Care request orders, left-joined to their DVDMS record orders as "rec".
#
# The status shown to users, first match wins:
# - draft: no record order yet, or the record order is draft or pending, or its outward record is only created
# - issued / issue_in_process: DVDMS' own indent status on the outward record of an approved record order
# - the outward record status (submitted, failed, cancelled) for an approved record order
# - else the record order status
EFFECTIVE_STATUS = Case(
    When(rec__isnull=True, then=Value("draft")),
    When(
        rec__status__in=[DVDMSRecordOrderStatus.draft, DVDMSRecordOrderStatus.pending],
        then=Value("draft"),
    ),
    When(
        rec__status=DVDMSRecordOrderStatus.approved,
        rec__outward_record__eaushadhi_indent_status__iexact="issued",
        then=Value("issued"),
    ),
    When(
        rec__status=DVDMSRecordOrderStatus.approved,
        rec__outward_record__eaushadhi_indent_status__iexact="issue in process",
        then=Value("issue_in_process"),
    ),
    When(
        rec__status=DVDMSRecordOrderStatus.approved,
        rec__outward_record__status=DVDMSOutwardRecordOrderStatus.created,
        then=Value("draft"),
    ),
    When(
        rec__status=DVDMSRecordOrderStatus.approved,
        rec__outward_record__status__isnull=False,
        then=F("rec__outward_record__status"),
    ),
    default=F("rec__status"),
    output_field=CharField(),
)


class DVDMSRecordOrderFilters(filters.FilterSet):
    # Looking up the record orders of one request order never returns an unlinked draft.
    order = filters.UUIDFilter(method="filter_order")
    location = filters.UUIDFilter(field_name="destination__external_id")
    # Matches the effective status above, not the raw record order status.
    status = MultiSelectFilter(field_name="effective_status")
    tab = filters.ChoiceFilter(choices=[(tab, tab) for tab in TAB_STATUSES], method="filter_tab")
    care_indent_no = filters.CharFilter(field_name="rec__care_indent_no")
    indent_no = filters.CharFilter(field_name="rec__outward_record__eaushadhi_indent_no", lookup_expr="icontains")
    priority = filters.CharFilter(field_name="priority", lookup_expr="iexact")
    created_by = filters.UUIDFilter(field_name="row_created_by")
    created_date_after = filters.DateFilter(field_name="row_created_date", lookup_expr="date__gte")
    created_date_before = filters.DateFilter(field_name="row_created_date", lookup_expr="date__lte")
    supplier = filters.UUIDFilter(field_name="rec__institute_supplier__supplier__external_id")

    def filter_order(self, queryset, name, value):
        return queryset.filter(external_id=value, record_pk__isnull=False)

    def filter_tab(self, queryset, name, value):
        return queryset.filter(effective_status__in=TAB_STATUSES[value])


@extend_schema(tags=["DVDMS: Record Order"])
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
        queryset = (
            RequestOrder.objects.filter(
                destination__facility=institute.facility,
                intent=SupplyRequestIntentOptions.order.value,
                deleted=False,
            )
            .annotate(
                rec=FilteredRelation(
                    "dvdms_record_order",
                    condition=Q(dvdms_record_order__institute=institute, dvdms_record_order__deleted=False),
                )
            )
            .filter(Q(rec__isnull=False) | Q(status__in=UNSENT_REQUEST_ORDER_STATUSES))
            .annotate(
                record_pk=F("rec__id"),
                record_status=F("rec__status"),
                effective_status=EFFECTIVE_STATUS,
                row_created_by=Coalesce("rec__created_by__external_id", "created_by__external_id"),
                row_created_date=Coalesce("rec__created_date", "created_date"),
            )
            .select_related("destination", "supplier", "origin", "created_by", "updated_by")
        )
        if "order" not in self.request.query_params:
            # A cancelled record order frees its request order to be linked again. Once it has been, the cancelled
            # one is history, so the list shows only the new one. Looking up an order's records still returns both.
            relinked = DVDMSRecordOrder.objects.filter(
                order=OuterRef("pk"), institute=institute, deleted=False
            ).exclude(status=DVDMSRecordOrderStatus.cancelled)
            queryset = queryset.exclude(Q(record_status=DVDMSRecordOrderStatus.cancelled) & Exists(relinked))
        return queryset

    def list(self, request, *args, **kwargs):
        """GET /institute/{institute_id}/record_order/ - List record orders, plus draft orders without one yet"""
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        records = DVDMSRecordOrder.objects.select_related(
            "institute",
            "order",
            "institute_store",
            "institute_store__location",
            "institute_supplier",
            "institute_supplier__supplier",
            "created_by",
            "updated_by",
        ).in_bulk([o.record_pk for o in page if o.record_pk])
        results = [
            {
                **(
                    DVDMSRecordOrderListSpec.serialize(records[o.record_pk]).to_json()
                    if o.record_pk
                    else self._draft_json(o)
                ),
                "effective_status": o.effective_status,
            }
            for o in page
        ]
        return paginator.get_paginated_response(results)

    def _draft_json(self, order):
        """A draft request order with no record order yet, in the record order list shape (id is null)."""
        order_json = SupplyRequestOrderReadSpec.serialize(order).to_json()
        return {
            "id": None,
            "institute_id": str(self.get_institute().external_id),
            "name": order.name,
            "order": order_json,
            "institute_store": None,
            "institute_supplier": None,
            "care_indent_no": None,
            "status": "draft",
            "created_by": order_json.get("created_by"),
            "updated_by": order_json.get("updated_by"),
            "created_date": order_json["created_date"],
            "modified_date": order_json["modified_date"],
        }

    def create(self, request, *args, **kwargs):
        """POST /institute/{institute_id}/record_order/ - Create record order"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        spec = DVDMSRecordOrderCreateSpec(**request.data)

        order = get_object_or_404(RequestOrder, external_id=spec.order, destination__facility=institute.facility)
        require_pending_request_order(order)
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


            if spec.status != DVDMSRecordOrderStatus.cancelled:
                require_pending_request_order(record_order.order)

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

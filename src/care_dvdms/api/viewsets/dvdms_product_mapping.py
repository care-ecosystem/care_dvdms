from collections import defaultdict

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.models.supply_request import SupplyRequest
from care.emr.resources.inventory.product_knowledge.spec import (
    ProductKnowledgeStatusOptions,
)
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care_dvdms.api.specs.dvdms_product_mapping import (
    DVDMSProductMappingCreateSpec,
    DVDMSProductMappingListSpec,
    DVDMSProductMappingUpdateSpec,
)
from care_dvdms.api.viewsets.mixins import DVDMSDrugLookupMixin
from care_dvdms.models.dvdms_drug import DVDMSDrug
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_product_mapping import DVDMSProductMapping, DVDMSProductMappingType
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder

SELECT_RELATED_FIELDS = (
    "institute",
    "drug",
    "product_knowledge",
    "product_knowledge__category",
    "created_by",
    "updated_by",
)


class DVDMSProductMappingFilters(filters.FilterSet):
    eaushadhi_drug_id = filters.CharFilter(field_name="drug__drug_id")
    product_knowledge_id = filters.UUIDFilter(field_name="product_knowledge__external_id")
    mapping_type = filters.CharFilter(field_name="mapping_type")


class DVDMSProductMappingViewSet(DVDMSDrugLookupMixin, EMRBaseViewSet):
    """
    ViewSet for managing DVDMS drug to CARE product mappings for an institute.
    Nested under: /institute/{institute_id}/product-mappings/
    """

    database_model = DVDMSProductMapping
    lookup_field = "external_id"
    filterset_class = DVDMSProductMappingFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date", "usage_count"]

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

    def _get_active_product_knowledge(self, institute, product_knowledge_id):
        product_knowledge = get_object_or_404(
            ProductKnowledge.objects.filter(Q(facility__isnull=True) | Q(facility=institute.facility)),
            external_id=product_knowledge_id,
        )
        if product_knowledge.status != ProductKnowledgeStatusOptions.active.value:
            raise ValidationError(f"ProductKnowledge is not active. Current status: {product_knowledge.status}")
        return product_knowledge

    def get_queryset(self):
        institute = self.get_institute()
        self._authorize_facility(institute)
        return DVDMSProductMapping.objects.filter(institute=institute, deleted=False).select_related(
            *SELECT_RELATED_FIELDS
        )

    def list(self, request, *args, **kwargs):
        """GET /institute/{institute_id}/product-mappings/ - List product mappings"""
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        results = [DVDMSProductMappingListSpec.serialize(o).to_json() for o in page]
        return paginator.get_paginated_response(results)

    def create(self, request, *args, **kwargs):
        """POST /institute/{institute_id}/product-mappings/ - Create product mapping"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        spec = DVDMSProductMappingCreateSpec(**request.data)
        product_knowledge = self._get_active_product_knowledge(institute, spec.product_knowledge_id)

        details, error = self.fetch_drug_or_error(institute, spec.eaushadhi_drug_id)
        if error:
            return error

        with transaction.atomic():
            institute = DVDMSInstitute.objects.select_for_update().get(pk=institute.pk)

            if DVDMSProductMapping.objects.filter(
                institute=institute, eaushadhi_drug_id=details.drug_id, deleted=False
            ).exists():
                return Response(
                    {"error": "Product mapping already exists for this drug"},
                    status=status.HTTP_409_CONFLICT,
                )

            drug = DVDMSDrug.objects.create(**details.model_dump())
            try:
                product_mapping = DVDMSProductMapping.objects.create(
                    institute=institute,
                    drug=drug,
                    eaushadhi_drug_id=details.drug_id,
                    product_knowledge=product_knowledge,
                    mapping_type=spec.mapping_type,
                    created_by=request.user,
                    updated_by=request.user,
                )
            except IntegrityError:
                return Response(
                    {"error": "Product mapping already exists for this drug"},
                    status=status.HTTP_409_CONFLICT,
                )

        result = DVDMSProductMappingListSpec.serialize(product_mapping)
        return Response(result.to_json(), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """PATCH /institute/{institute_id}/product-mappings/{product_mapping_id}/ - Update product mapping"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        product_mapping_id = self.kwargs.get(self.lookup_field)
        spec = DVDMSProductMappingUpdateSpec(**request.data)

        details = None
        if spec.eaushadhi_drug_id is not None:
            details, error = self.fetch_drug_or_error(institute, spec.eaushadhi_drug_id)
            if error:
                return error

        with transaction.atomic():
            institute = DVDMSInstitute.objects.select_for_update().get(pk=institute.pk)

            product_mapping = get_object_or_404(
                DVDMSProductMapping.objects.select_related(*SELECT_RELATED_FIELDS),
                external_id=product_mapping_id,
                institute=institute,
                deleted=False,
            )

            update_fields = ["updated_by", "modified_date"]

            if details is not None:
                new_drug_id = details.drug_id
                if new_drug_id != product_mapping.drug.drug_id:
                    conflict = DVDMSProductMapping.objects.filter(
                        institute=institute, eaushadhi_drug_id=new_drug_id, deleted=False
                    ).exclude(pk=product_mapping.pk)
                    if conflict.exists():
                        return Response(
                            {"error": "Product mapping already exists for this drug"},
                            status=status.HTTP_409_CONFLICT,
                        )

                drug = product_mapping.drug
                drug_fields = details.model_dump()
                for field, value in drug_fields.items():
                    setattr(drug, field, value)
                drug.updated_by = request.user
                drug.save(update_fields=[*drug_fields, "updated_by", "modified_date"])

                product_mapping.eaushadhi_drug_id = new_drug_id
                update_fields.append("eaushadhi_drug_id")

            if spec.product_knowledge_id is not None:
                product_mapping.product_knowledge = self._get_active_product_knowledge(
                    institute, spec.product_knowledge_id
                )
                update_fields.append("product_knowledge")

            product_mapping.updated_by = request.user
            try:
                product_mapping.save(update_fields=update_fields)
            except IntegrityError:
                return Response(
                    {"error": "Product mapping already exists for this drug"},
                    status=status.HTTP_409_CONFLICT,
                )

        result = DVDMSProductMappingListSpec.serialize(product_mapping)
        return Response(result.to_json(), status=status.HTTP_200_OK)


class DVDMSRecordOrderProductMappingViewSet(EMRBaseViewSet):
    """
    /institute/{institute_id}/record_order/{record_order_id}/product_mappings/
    """

    database_model = DVDMSProductMapping
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

    def get_queryset(self):
        institute = self.get_institute()
        self._authorize_facility(institute)
        record_order = self.get_record_order(institute)
        mapped_product_knowledge = DVDMSProductMapping.objects.filter(
            institute=institute,
            mapping_type=DVDMSProductMappingType.default_mapping,
            deleted=False,
        ).values("product_knowledge_id")
        return (
            SupplyRequest.objects.filter(
                order=record_order.order,
                deleted=False,
                item_id__in=mapped_product_knowledge,
            )
            .select_related("item")
            .order_by("-created_date")
        )

    def _default_mappings_by_product_knowledge(self, institute, supply_requests):
        # A product knowledge can carry more than one default mapping, so every one of them is
        # kept against its key ProductKnowledge.
        product_knowledge_ids = {supply_request.item_id for supply_request in supply_requests}
        if not product_knowledge_ids:
            return {}

        mappings = defaultdict(list)
        for mapping in (
            DVDMSProductMapping.objects.filter(
                institute=institute,
                product_knowledge_id__in=product_knowledge_ids,
                mapping_type=DVDMSProductMappingType.default_mapping,
                deleted=False,
            )
            .select_related(*SELECT_RELATED_FIELDS)
            .order_by("-modified_date")
        ):
            mappings[mapping.product_knowledge_id].append(mapping)
        return mappings

    def list(self, request, *args, **kwargs):
        """GET .../product_mappings/ - List record order items that have a product mapping"""

        institute = self.get_institute()
        supply_requests = list(self.filter_queryset(self.get_queryset()))
        mappings_by_product_knowledge = self._default_mappings_by_product_knowledge(institute, supply_requests)

        entries = [
            (supply_request, mapping)
            for supply_request in supply_requests
            for mapping in mappings_by_product_knowledge.get(supply_request.item_id, ())
        ]

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(entries, request)

        results = [
            {
                "supply_request": {
                    "id": str(supply_request.external_id),
                    "item": {
                        "id": str(supply_request.item.external_id),
                        "status": supply_request.item.status,
                    },
                    "quantity": (str(supply_request.quantity) if supply_request.quantity is not None else None),
                    "status": supply_request.status,
                },
                "product_mapping": DVDMSProductMappingListSpec.serialize(mapping).to_json(),
            }
            for supply_request, mapping in page
        ]

        return paginator.get_paginated_response(results)

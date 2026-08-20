import requests
from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.resources.inventory.product_knowledge.spec import (
    ProductKnowledgeStatusOptions,
)
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care_dvdms.api.services.constants import DVDMS_DRUGS_CACHE_KEY
from care_dvdms.api.services.dvdms_master_data_services import fetch_drugs
from care_dvdms.api.specs.dvdms_product_mapping import (
    DVDMSProductMappingCreateSpec,
    DVDMSProductMappingListSpec,
    DVDMSProductMappingUpdateSpec,
)
from care_dvdms.models.dvdms_drug import DVDMSDrug
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_product_mapping import DVDMSProductMapping
from care_dvdms.models.dvdms_record_item_order import DVDMSRecordItemOrder
from care_dvdms.models.dvdms_record_order import DVDMSRecordOrder
from care_dvdms.settings import plugin_settings as settings

SELECT_RELATED_FIELDS = ("institute", "drug", "product_knowledge", "created_by", "updated_by")


class DVDMSProductMappingFilters(filters.FilterSet):
    eaushadhi_drug_id = filters.CharFilter(field_name="drug__drug_id")
    product_knowledge_id = filters.UUIDFilter(field_name="product_knowledge__external_id")
    mapping_type = filters.CharFilter(field_name="mapping_type")


class DVDMSProductMappingViewSet(EMRBaseViewSet):
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
            ProductKnowledge.objects.filter(
                Q(facility__isnull=True) | Q(facility=institute.facility)
            ),
            external_id=product_knowledge_id,
        )
        if product_knowledge.status != ProductKnowledgeStatusOptions.active.value:
            raise ValidationError(
                f"ProductKnowledge is not active. Current status: {product_knowledge.status}"
            )
        return product_knowledge

    def _check_drug_id_valid(self, institute, drug_id):
        """Validate drug_id against the DVDMS drug lookup. Returns an error Response, or None if valid."""
        drugs = cache.get(DVDMS_DRUGS_CACHE_KEY)
        if drugs is None:
            try:
                drugs = fetch_drugs()
            except requests.exceptions.RequestException:
                return Response(
                    {"error": "Failed to fetch drugs from DVDMS", "code": "DVDMS_API_ERROR"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            cache.set(DVDMS_DRUGS_CACHE_KEY, drugs, settings.DVDMS_LOOKUP_CACHE_TTL)

        exists = any(
            str(drug.get("hstnum_item_id")) == drug_id
            and str(drug.get("gnum_hospital_code")) == institute.eaushadhi_institute_id
            and str(drug.get("gnum_seatid")) == institute.eaushadhi_user_ref_id
            for drug in drugs
        )
        if not exists:
            return Response(
                {"error": f"'{drug_id}' is not a valid DVDMS drug for this institute", "code": "INVALID_DRUG_ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

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

        error = self._check_drug_id_valid(institute, spec.eaushadhi_drug_details.id)
        if error:
            return error

        with transaction.atomic():
            institute = DVDMSInstitute.objects.select_for_update().get(pk=institute.pk)

            if DVDMSProductMapping.objects.filter(
                institute=institute, eaushadhi_drug_id=spec.eaushadhi_drug_details.id, deleted=False
            ).exists():
                return Response(
                    {"error": "Product mapping already exists for this drug"},
                    status=status.HTTP_409_CONFLICT,
                )

            drug = DVDMSDrug.objects.create(
                drug_id=spec.eaushadhi_drug_details.id,
                name=spec.eaushadhi_drug_details.name,
                brand_id=spec.eaushadhi_drug_details.brand_id,
                group_id=spec.eaushadhi_drug_details.group_id,
                sub_group_id=spec.eaushadhi_drug_details.sub_group_id,
                unit_id=spec.eaushadhi_drug_details.unit_id,
                drug_category=spec.eaushadhi_drug_details.drug_category,
            )
            try:
                product_mapping = DVDMSProductMapping.objects.create(
                    institute=institute,
                    drug=drug,
                    eaushadhi_drug_id=spec.eaushadhi_drug_details.id,
                    product_knowledge=product_knowledge,
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

        if spec.eaushadhi_drug_details is not None:
            error = self._check_drug_id_valid(institute, spec.eaushadhi_drug_details.id)
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

            if spec.eaushadhi_drug_details is not None:
                details = spec.eaushadhi_drug_details
                provided = details.model_fields_set
                new_drug_id = details.id if "id" in provided else product_mapping.drug.drug_id
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
                drug_update_fields = []
                for field in ("id", "name", "brand_id", "group_id", "sub_group_id", "unit_id", "drug_category"):
                    if field not in provided:
                        continue
                    model_field = "drug_id" if field == "id" else field
                    setattr(drug, model_field, getattr(details, field))
                    drug_update_fields.append(model_field)
                if drug_update_fields:
                    drug.save(update_fields=drug_update_fields)

                if "id" in provided:
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
    Read-only viewset listing a record order's items alongside their product
    mapping, if one exists. Nested under:
    /institute/{institute_id}/record_order/{record_order_id}/product_mappings/
    """

    database_model = DVDMSRecordItemOrder
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
        return DVDMSRecordItemOrder.objects.filter(
            institute=institute, record_order=record_order, deleted=False
        ).select_related("supply_request", "supply_request__item", "drug")

    def list(self, request, *args, **kwargs):
        """GET .../product_mappings/ - List record order items with their product mapping"""
        institute = self.get_institute()
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        drug_ids = [item.drug.drug_id for item in page]
        mappings_by_drug_id = {
            mapping.drug.drug_id: mapping
            for mapping in DVDMSProductMapping.objects.filter(
                institute=institute, drug__drug_id__in=drug_ids, deleted=False
            ).select_related(*SELECT_RELATED_FIELDS)
        }

        results = [
            {
                "supply_request": {
                    "id": str(item.supply_request.external_id),
                    "item": {
                        "id": str(item.supply_request.item.external_id),
                        "status": item.supply_request.item.status,
                    },
                    "quantity": (
                        str(item.supply_request.quantity)
                        if item.supply_request.quantity is not None
                        else None
                    ),
                    "status": item.supply_request.status,
                },
                "product_mapping": (
                    DVDMSProductMappingListSpec.serialize(mappings_by_drug_id[item.drug.drug_id]).to_json()
                    if item.drug.drug_id in mappings_by_drug_id
                    else None
                ),
            }
            for item in page
        ]

        return paginator.get_paginated_response(results)

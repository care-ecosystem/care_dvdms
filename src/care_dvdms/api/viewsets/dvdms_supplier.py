from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.models.organization import Organization
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404

from care_dvdms.api.specs.dvdms_supplier import (
    DVDMSSupplierCreateSpec,
    DVDMSSupplierListSpec,
    DVDMSSupplierUpdateSpec,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_supplier import DVDMSSupplier


class DVDMSSupplierViewSet(EMRBaseViewSet):
    """
    ViewSet for managing DVDMS supplier mappings under an institute.
    Nested under institute: /institute/{institute_id}/suppliers/
    """

    database_model = DVDMSSupplier
    lookup_field = "external_id"
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_institute(self):
        institute_id = self.kwargs.get("institute_id")
        if not institute_id:
            raise NotFound("institute_id not provided")
        institute = get_object_or_404(DVDMSInstitute, external_id=institute_id, deleted=False)
        return institute

    def _authorize_facility(self, institute):
        if not AuthorizationController.call(
            "can_use_dvdms_integration", self.request.user, institute.facility
        ):
            raise PermissionDenied(
                "You are not authorized to use DVDMS plugin for this facility"
            )

    def _authorize_manage_facility(self, institute):
        if not AuthorizationController.call(
            "can_manage_dvdms_integration", self.request.user, institute.facility
        ):
            raise PermissionDenied(
                "You are not authorized to manage DVDMS plugin for this facility"
            )

    def get_queryset(self):
        institute = self.get_institute()
        self._authorize_facility(institute)
        return (
            DVDMSSupplier.objects
            .filter(institute=institute, deleted=False)
            .select_related("institute", "supplier", "created_by", "updated_by")
        )

    def list(self, request, *args, **kwargs):
        """GET /institute/{institute_id}/suppliers/ - List supplier mappings"""
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        results = [DVDMSSupplierListSpec.serialize(s).to_json() for s in page]
        return paginator.get_paginated_response(results)

    def create(self, request, *args, **kwargs):
        """POST /institute/{institute_id}/suppliers/ - Create supplier mapping"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        spec = DVDMSSupplierCreateSpec(**request.data)

        supplier = get_object_or_404(
            Organization,
            external_id=spec.supplier,
            org_type="product_supplier",
            deleted=False,
        )

        if DVDMSSupplier.objects.filter(
            institute=institute, supplier=supplier, deleted=False
        ).exists():
            return Response(
                {"error": "This supplier is already mapped for this institute"},
                status=status.HTTP_409_CONFLICT,
            )

        if spec.is_default:
            existing_default = DVDMSSupplier.objects.filter(
                institute=institute, is_default=True, deleted=False
            ).first()
            if existing_default:
                return Response(
                    {"error": "Only one supplier can be marked as default per institute"},
                    status=status.HTTP_409_CONFLICT,
                )

        try:
            with transaction.atomic():
                supplier_mapping = DVDMSSupplier.objects.create(
                    institute=institute,
                    supplier=supplier,
                    eaushadhi_warehouse_id=spec.eaushadhi_warehouse_id,
                    eaushadhi_warehouse_name=spec.eaushadhi_warehouse_name,
                    is_default=spec.is_default,
                    created_by=request.user,
                    updated_by=request.user,
                )
        except IntegrityError:
            return Response(
                {"error": "This supplier is already mapped for this institute"},
                status=status.HTTP_409_CONFLICT,
            )

        supplier_mapping = DVDMSSupplier.objects.select_related(
            "institute", "supplier", "created_by", "updated_by"
        ).get(pk=supplier_mapping.pk)

        result = DVDMSSupplierListSpec.serialize(supplier_mapping)
        return Response(result.to_json(), status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """DELETE /institute/{institute_id}/suppliers/{supplier_mapping_id}/ - Delete supplier mapping"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        supplier_mapping_id = self.kwargs.get(self.lookup_field)
        supplier_mapping = get_object_or_404(
            DVDMSSupplier,
            external_id=supplier_mapping_id,
            institute=institute,
            deleted=False,
        )

        supplier_mapping.delete()
        return Response(
            {"message": "Supplier mapping deleted successfully"},
            status=status.HTTP_200_OK,
        )

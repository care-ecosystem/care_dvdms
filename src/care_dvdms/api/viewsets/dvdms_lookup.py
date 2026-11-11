import logging

import requests
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from care_dvdms.api.services.constants import (
    DVDMS_DRUG_ITEM_CAT_NO,
    DVDMS_DRUGS_CACHE_KEY,
    DVDMS_GROUPS_CACHE_KEY,
    DVDMS_STORES_CACHE_KEY,
    DVDMS_SUBGROUPS_CACHE_KEY,
    DVDMS_UNITS_CACHE_KEY,
)
from care_dvdms.api.services.dvdms_master_data_services import (
    fetch_drugs,
    fetch_groups,
    fetch_stores,
    fetch_subgroups,
    fetch_units,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.settings import plugin_settings as settings

logger = logging.getLogger(__name__)


@extend_schema(tags=["DVDMS: Lookup"])
class DVDMSLookupViewSet(ViewSet):
    def get_institute(self):
        institute_id = self.kwargs.get("institute_id")
        if not institute_id:
            raise NotFound("institute_id not provided")
        return get_object_or_404(DVDMSInstitute, external_id=institute_id, deleted=False)

    def check_permissions_for_institute(self, request, institute):
        if not AuthorizationController.call("can_use_dvdms_integration", request.user, institute.facility):
            raise PermissionDenied("You are not authorized to use DVDMS plugin for this facility")

    def _matches_institute(self, row, institute, hospital_code_field, seat_id_field):
        """Narrow a DVDMS master-data row to this institute, honouring the lookup filter settings.

        A field name of None means that identifier is not matched on for this lookup - either the
        DVDMS payload does not carry it, or the lookup is deliberately not narrowed by it.
        """
        if (
            settings.DVDMS_LOOKUP_FILTER_BY_HOSPITAL_CODE
            and hospital_code_field
            and str(row.get(hospital_code_field)) != institute.eaushadhi_institute_id
        ):
            return False
        return not (
            settings.DVDMS_LOOKUP_FILTER_BY_SEAT_ID
            and seat_id_field
            and str(row.get(seat_id_field)) != institute.eaushadhi_user_ref_id
        )

    def groups(self, request, *args, **kwargs):
        institute = self.get_institute()
        self.check_permissions_for_institute(request, institute)

        groups = cache.get(DVDMS_GROUPS_CACHE_KEY)
        if groups is None:
            try:
                groups = fetch_groups()
            except requests.exceptions.RequestException:
                return Response(
                    {"error": "Failed to fetch groups from DVDMS", "code": "DVDMS_API_ERROR"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            except Exception:
                return Response(
                    {"error": "Internal server error occurred", "code": "INTERNAL_ERROR"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            cache.set(DVDMS_GROUPS_CACHE_KEY, groups, settings.DVDMS_LOOKUP_CACHE_TTL)

        results = [
            group for group in groups if self._matches_institute(group, institute, "gnumHospitalCode", "gnumSeatid")
        ]

        return Response(results)

    def units(self, request, *args, **kwargs):
        institute = self.get_institute()
        self.check_permissions_for_institute(request, institute)

        units = cache.get(DVDMS_UNITS_CACHE_KEY)
        if units is None:
            try:
                units = fetch_units()
            except requests.exceptions.RequestException:
                return Response(
                    {"error": "Failed to fetch units from DVDMS", "code": "DVDMS_API_ERROR"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            except Exception:
                return Response(
                    {"error": "Internal server error occurred", "code": "INTERNAL_ERROR"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            cache.set(DVDMS_UNITS_CACHE_KEY, units, settings.DVDMS_LOOKUP_CACHE_TTL)

        # Units are shared across an institute's seats, so they are not narrowed by seat id.
        results = [unit for unit in units if self._matches_institute(unit, institute, "gnumHospitalCode", None)]

        return Response(results)

    def drugs(self, request, *args, **kwargs):
        hstnum_group_id = request.query_params.get("hstnum_group_id")
        hstnum_subgroup_id = request.query_params.get("hstnum_subgroup_id")
        if not hstnum_group_id:
            return Response(
                {
                    "error": "hstnum_group_id query parameter is required",
                    "code": "MISSING_PARAMETER",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        item_name = request.query_params.get("hststr_item_name")

        institute = self.get_institute()
        self.check_permissions_for_institute(request, institute)

        drugs = cache.get(DVDMS_DRUGS_CACHE_KEY)
        if drugs is None:
            try:
                drugs = fetch_drugs()
            except requests.exceptions.RequestException:
                return Response(
                    {"error": "Failed to fetch drugs from DVDMS", "code": "DVDMS_API_ERROR"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            except Exception:
                return Response(
                    {"error": "Internal server error occurred", "code": "INTERNAL_ERROR"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            cache.set(DVDMS_DRUGS_CACHE_KEY, drugs, settings.DVDMS_LOOKUP_CACHE_TTL)

        results = [
            drug
            for drug in drugs
            if self._matches_institute(drug, institute, "gnum_hospital_code", "gnum_seatid")
            and str(drug.get("sstnum_item_cat_no")) == DVDMS_DRUG_ITEM_CAT_NO
            and str(drug.get("hstnum_group_id")) == hstnum_group_id
            and (not hstnum_subgroup_id or str(drug.get("hstnum_subgroup_id")) == hstnum_subgroup_id)
            and (not item_name or item_name.lower() in str(drug.get("hststr_item_name", "")).lower())
        ]

        return Response(results)

    def stores(self, request, *args, **kwargs):
        from_store_id = request.query_params.get("fromStoreid")

        institute = self.get_institute()
        self.check_permissions_for_institute(request, institute)

        stores = cache.get(DVDMS_STORES_CACHE_KEY)
        if stores is None:
            try:
                stores = fetch_stores()
            except requests.exceptions.RequestException:
                return Response(
                    {"error": "Failed to fetch stores from DVDMS", "code": "DVDMS_API_ERROR"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            except Exception:
                return Response(
                    {"error": "Internal server error occurred", "code": "INTERNAL_ERROR"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            cache.set(DVDMS_STORES_CACHE_KEY, stores, settings.DVDMS_LOOKUP_CACHE_TTL)

        results = [
            store
            for store in stores
            if (not from_store_id or str(store.get("hstnumStoreId")) == from_store_id)
            and self._matches_institute(store, institute, None, "gnumSeatid")
        ]

        return Response(results)

    def subgroups(self, request, *args, **kwargs):
        group_id = request.query_params.get("group_id")
        if not group_id:
            return Response(
                {"error": "group_id query parameter is required", "code": "MISSING_PARAMETER"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        institute = self.get_institute()
        self.check_permissions_for_institute(request, institute)

        subgroups = cache.get(DVDMS_SUBGROUPS_CACHE_KEY)
        if subgroups is None:
            try:
                subgroups = fetch_subgroups()
            except requests.exceptions.RequestException:
                return Response(
                    {"error": "Failed to fetch subgroups from DVDMS", "code": "DVDMS_API_ERROR"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            except Exception:
                return Response(
                    {"error": "Internal server error occurred", "code": "INTERNAL_ERROR"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            cache.set(DVDMS_SUBGROUPS_CACHE_KEY, subgroups, settings.DVDMS_LOOKUP_CACHE_TTL)

        results = [
            subgroup
            for subgroup in subgroups
            if self._matches_institute(subgroup, institute, "gnumHospitalCode", "gnumSeatid")
            and str(subgroup.get("hstnumGroupId")) == str(group_id)
        ]

        return Response(results)

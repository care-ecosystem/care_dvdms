import logging

import requests
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from care_dvdms.api.services.constants import (
    DVDMS_GROUPS_CACHE_KEY,
    DVDMS_SUBGROUPS_CACHE_KEY,
    DVDMS_UNITS_CACHE_KEY,
)
from care_dvdms.api.services.dvdms_master_data_services import fetch_groups, fetch_subgroups, fetch_units
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.settings import plugin_settings as settings

logger = logging.getLogger(__name__)


class DVDMSLookupViewSet(ViewSet):
    def get_institute(self):
        institute_id = self.kwargs.get("institute_id")
        if not institute_id:
            raise NotFound("institute_id not provided")
        return get_object_or_404(DVDMSInstitute, external_id=institute_id, deleted=False)

    def check_permissions_for_institute(self, request, institute):
        if not AuthorizationController.call("can_use_dvdms_integration", request.user, institute.facility):
            raise PermissionDenied("You are not authorized to use DVDMS plugin for this facility")

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
            group
            for group in groups
            if str(group.get("gnumHospitalCode")) == institute.eaushadhi_institute_id
            and str(group.get("gnumSeatid")) == institute.eaushadhi_user_ref_id
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

        results = [unit for unit in units if str(unit.get("gnumSeatid")) == institute.eaushadhi_user_ref_id]

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
            if str(subgroup.get("gnumHospitalCode")) == institute.eaushadhi_institute_id
            and str(subgroup.get("gnumSeatid")) == institute.eaushadhi_user_ref_id
            and str(subgroup.get("hstnumGroupId")) == str(group_id)
        ]

        return Response(results)

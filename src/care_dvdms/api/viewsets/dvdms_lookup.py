import logging

import requests
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404

from care_dvdms.api.services.dvdms_group_master_service import DVDMSGroupMasterService
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.settings import plugin_settings as settings

logger = logging.getLogger(__name__)

GROUPS_CACHE_KEY = "dvdms:lookup:groups"


class DVDMSGroupLookupViewSet(ViewSet):
    def get_institute(self):
        institute_id = self.kwargs.get("institute_id")
        if not institute_id:
            raise NotFound("institute_id not provided")
        return get_object_or_404(DVDMSInstitute, external_id=institute_id, deleted=False)

    def list(self, request, *args, **kwargs):
        institute = self.get_institute()
        if not AuthorizationController.call(
            "can_use_dvdms_integration", request.user, institute.facility
        ):
            raise PermissionDenied(
                "You are not authorized to use DVDMS plugin for this facility"
            )

        groups = cache.get(GROUPS_CACHE_KEY)
        if groups is None:
            try:
                groups = DVDMSGroupMasterService.fetch_groups()
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
            cache.set(GROUPS_CACHE_KEY, groups, settings.DVDMS_LOOKUP_CACHE_TTL)

        results = [
            group
            for group in groups
            if str(group.get("gnumHospitalCode")) == institute.eaushadhi_institute_id
            and str(group.get("gnumSeatid")) == institute.eaushadhi_user_ref_id
        ]

        return Response({"count": len(results), "results": results})

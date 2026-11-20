import requests
from rest_framework import status
from rest_framework.response import Response

from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.signals import DVDMS_CONFIG_FIELDS
from care_dvdms.utils.drug_lookup import get_drug_details


def lock_institute(institute):
    """Lock the institute row; fail if its DVDMS config changed since the request loaded it. Call inside atomic."""
    locked = DVDMSInstitute.objects.select_for_update().get(pk=institute.pk)
    if any(getattr(locked, field) != getattr(institute, field) for field in DVDMS_CONFIG_FIELDS):
        return None, Response(
            {"error": "The DVDMS configuration changed while this request was running, please retry"},
            status=status.HTTP_409_CONFLICT,
        )
    return locked, None


class DVDMSDrugLookupMixin:
    def fetch_drug_or_error(self, institute, drug_id):
        try:
            details = get_drug_details(institute, drug_id)
        except requests.exceptions.RequestException:
            return None, Response(
                {"error": "Failed to fetch drugs from DVDMS", "code": "DVDMS_API_ERROR"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if details is None:
            return None, Response(
                {"error": f"'{drug_id}' is not a valid DVDMS drug for this institute", "code": "INVALID_DRUG_ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return details, None

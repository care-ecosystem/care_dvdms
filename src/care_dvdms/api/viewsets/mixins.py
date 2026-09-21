import requests
from rest_framework import status
from rest_framework.response import Response

from care_dvdms.utils import get_drug_details


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

from django.shortcuts import HttpResponse
from django.urls import path, re_path

from care_dvdms.api.viewsets.dvdms_institute import DVDMSInstituteViewSet


def healthy(request):
    return HttpResponse("OK")


urlpatterns = [
    path("health/", healthy),
    re_path(
        r"^facility/(?P<facility_external_id>[^/.]+)/institute/$",
        DVDMSInstituteViewSet.as_view({
            "get": "list",
            "post": "create",
            "patch": "partial_update",
        }),
        name="dvdms-institute-detail",
    ),
]

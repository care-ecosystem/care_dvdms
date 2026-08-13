from django.shortcuts import HttpResponse
from django.urls import path, re_path

from care_dvdms.api.viewsets.dvdms_institute import DVDMSInstituteViewSet
from care_dvdms.api.viewsets.dvdms_lookup import DVDMSGroupLookupViewSet
from care_dvdms.api.viewsets.dvdms_supplier import DVDMSSupplierViewSet


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
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/suppliers/$",
        DVDMSSupplierViewSet.as_view({
            "get": "list",
            "post": "create",
        }),
        name="dvdms-supplier-list",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/suppliers/(?P<external_id>[^/.]+)/$",
        DVDMSSupplierViewSet.as_view({
            "delete": "destroy",
        }),
        name="dvdms-supplier-detail",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/lookup/groups/$",
        DVDMSGroupLookupViewSet.as_view({"get": "list"}),
        name="dvdms-lookup-groups",
    ),
]

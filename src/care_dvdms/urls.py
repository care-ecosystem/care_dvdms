from django.shortcuts import HttpResponse
from django.urls import path, re_path

from care_dvdms.api.viewsets.dvdms_institute import DVDMSInstituteViewSet
from care_dvdms.api.viewsets.dvdms_lookup import DVDMSLookupViewSet
from care_dvdms.api.viewsets.dvdms_outward_record_order import (
    DVDMSOutwardRecordOrderViewSet,
)
from care_dvdms.api.viewsets.dvdms_record_item_order import (
    DVDMSRecordItemOrderViewSet,
)
from care_dvdms.api.viewsets.dvdms_record_order import DVDMSRecordOrderViewSet
from care_dvdms.api.viewsets.dvdms_store import DVDMSStoreViewSet
from care_dvdms.api.viewsets.dvdms_supplier import DVDMSSupplierViewSet


def healthy(request):
    return HttpResponse("OK")


urlpatterns = [
    path("health/", healthy),
    re_path(
        r"^facility/(?P<facility_external_id>[^/.]+)/institute/$",
        DVDMSInstituteViewSet.as_view(
            {
                "get": "list",
                "post": "create",
                "patch": "partial_update",
            }
        ),
        name="dvdms-institute-detail",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/suppliers/$",
        DVDMSSupplierViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="dvdms-supplier-list",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/suppliers/(?P<external_id>[^/.]+)/$",
        DVDMSSupplierViewSet.as_view(
            {
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="dvdms-supplier-detail",
    ),
    re_path(
        r"^facility/(?P<facility_id>[^/.]+)/institute/(?P<institute_id>[^/.]+)/stores/$",
        DVDMSStoreViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="dvdms-store-list",
    ),
    re_path(
        r"^facility/(?P<facility_id>[^/.]+)/institute/(?P<institute_id>[^/.]+)/stores/(?P<external_id>[^/.]+)/$",
        DVDMSStoreViewSet.as_view(
            {
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="dvdms-store-detail",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/lookup/groups/$",
        DVDMSLookupViewSet.as_view({"get": "groups"}),
        name="dvdms-lookup-groups",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/lookup/subgroups/$",
        DVDMSLookupViewSet.as_view({"get": "subgroups"}),
        name="dvdms-lookup-subgroups",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/lookup/units/$",
        DVDMSLookupViewSet.as_view({"get": "units"}),
        name="dvdms-lookup-units",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/lookup/drugs/$",
        DVDMSLookupViewSet.as_view({"get": "drugs"}),
        name="dvdms-lookup-drugs",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/lookup/stores/$",
        DVDMSLookupViewSet.as_view({"get": "stores"}),
        name="dvdms-lookup-stores",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/record_order/$",
        DVDMSRecordOrderViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="dvdms-record-order-list",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/record_order/(?P<external_id>[^/.]+)/$",
        DVDMSRecordOrderViewSet.as_view(
            {
                "patch": "partial_update",
            }
        ),
        name="dvdms-record-order-detail",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/record_order/(?P<record_order_id>[^/.]+)/item/$",
        DVDMSRecordItemOrderViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="dvdms-record-item-order-list",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/record_order/(?P<record_order_id>[^/.]+)/item/(?P<external_id>[^/.]+)/$",
        DVDMSRecordItemOrderViewSet.as_view(
            {
                "patch": "partial_update",
            }
        ),
        name="dvdms-record-item-order-detail",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/record_order/(?P<record_order_id>[^/.]+)/outward/$",
        DVDMSOutwardRecordOrderViewSet.as_view({"get": "list"}),
        name="dvdms-outward-record-order-list",
    ),
    re_path(
        r"^institute/(?P<institute_id>[^/.]+)/record_order/(?P<record_order_id>[^/.]+)/outward/fetch-inwards/$",
        DVDMSOutwardRecordOrderViewSet.as_view({"post": "fetch_inwards"}),
        name="dvdms-outward-record-order-fetch-inwards",
    ),
]

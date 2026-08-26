from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.models.supply_delivery import SupplyDelivery
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care_dvdms.api.specs.dvdms_record_item_delivery import (
    DVDMSRecordItemDeliveryCreateSpec,
    DVDMSRecordItemDeliveryListSpec,
    DVDMSRecordItemDeliveryUpdateSpec,
)
from care_dvdms.models.dvdms_institute import DVDMSInstitute
from care_dvdms.models.dvdms_inward_item_record import DVDMSInwardItemRecord
from care_dvdms.models.dvdms_inward_record import DVDMSInwardRecord
from care_dvdms.models.dvdms_record_delivery import DVDMSRecordDelivery
from care_dvdms.models.dvdms_record_item_delivery import DVDMSRecordItemDelivery


def _validate_quantities(dispatched, accepted, damaged, short):
    if any(value < 0 for value in (dispatched, accepted, damaged, short)):
        return Response(
            {
                "error": "quantity_dispatched, quantity_accepted, quantity_damaged, quantity_short cannot be negative",
                "code": "QUANTITY_NEGATIVE",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if accepted + damaged + short > dispatched:
        return Response(
            {
                "error": "quantity_accepted + quantity_damaged + quantity_short cannot exceed quantity_dispatched",
                "code": "QUANTITY_OVERFLOW",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


SELECT_RELATED_FIELDS = (
    "record_delivery",
    "inward_record_item",
    "supply_delivery",
    "supply_delivery__supplied_item",
    "supply_delivery__supplied_item__product_knowledge",
    "created_by",
    "updated_by",
)


class DVDMSRecordItemDeliveryViewSet(EMRBaseViewSet):
    """
    ViewSet for managing DVDMS record item deliveries under a record delivery.
    Nested under: /institute/{institute_id}/record_inwards/{record_inward_id}/delivery/{record_delivery_id}/items/
    """

    database_model = DVDMSRecordItemDelivery
    lookup_field = "external_id"
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_institute(self):
        institute_id = self.kwargs.get("institute_id")
        if not institute_id:
            raise NotFound("institute_id is required")
        return get_object_or_404(DVDMSInstitute, external_id=institute_id, deleted=False)

    def get_inward_record(self, institute):
        record_inward_id = self.kwargs.get("record_inward_id")
        if not record_inward_id:
            raise NotFound("record_inward_id is required")
        return get_object_or_404(
            DVDMSInwardRecord,
            external_id=record_inward_id,
            institute=institute,
            deleted=False,
        )

    def get_record_delivery(self, inward_record):
        record_delivery_id = self.kwargs.get("record_delivery_id")
        if not record_delivery_id:
            raise NotFound("record_delivery_id is required")
        return get_object_or_404(
            DVDMSRecordDelivery,
            external_id=record_delivery_id,
            inward_record=inward_record,
            deleted=False,
        )

    def _authorize_facility(self, institute):
        if not AuthorizationController.call("can_use_dvdms_integration", self.request.user, institute.facility):
            raise PermissionDenied("You are not authorized to use DVDMS plugin for this facility")

    def _authorize_manage_facility(self, institute):
        if not AuthorizationController.call("can_manage_dvdms_integration", self.request.user, institute.facility):
            raise PermissionDenied("You are not authorized to manage DVDMS plugin for this facility")

    def get_queryset(self):
        institute = self.get_institute()
        self._authorize_facility(institute)
        inward_record = self.get_inward_record(institute)
        record_delivery = self.get_record_delivery(inward_record)
        return DVDMSRecordItemDelivery.objects.filter(record_delivery=record_delivery, deleted=False).select_related(
            *SELECT_RELATED_FIELDS
        )

    def create(self, request, *args, **kwargs):
        """POST .../items/ - Create a record item delivery"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)
        inward_record = self.get_inward_record(institute)
        record_delivery = self.get_record_delivery(inward_record)

        spec = DVDMSRecordItemDeliveryCreateSpec(**request.data)

        error = _validate_quantities(
            spec.quantity_dispatched, spec.quantity_accepted, spec.quantity_damaged, spec.quantity_short
        )
        if error:
            return error

        inward_record_item = get_object_or_404(
            DVDMSInwardItemRecord,
            external_id=spec.inward_record_item,
            inward_record=inward_record,
            deleted=False,
        )
        supply_delivery = get_object_or_404(
            SupplyDelivery,
            external_id=spec.supply_delivery,
            order=record_delivery.delivery_order,
        )

        try:
            item_delivery = DVDMSRecordItemDelivery.objects.create(
                record_delivery=record_delivery,
                inward_record_item=inward_record_item,
                supply_delivery=supply_delivery,
                quantity_dispatched=spec.quantity_dispatched,
                quantity_accepted=spec.quantity_accepted,
                quantity_damaged=spec.quantity_damaged,
                quantity_short=spec.quantity_short,
                created_by=request.user,
                updated_by=request.user,
            )
        except IntegrityError:
            return Response(
                {
                    "error": "An active delivery already exists for this record_item",
                    "code": "RECORD_ITEM_ALREADY_HAS_DELIVERY",
                },
                status=status.HTTP_409_CONFLICT,
            )

        result = DVDMSRecordItemDeliveryListSpec.serialize(item_delivery)
        return Response(result.to_json(), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """PATCH .../items/{item_delivery_id}/ - Update a record item delivery"""
        institute = self.get_institute()
        self._authorize_manage_facility(institute)

        item_delivery_id = self.kwargs.get(self.lookup_field)
        spec = DVDMSRecordItemDeliveryUpdateSpec(**request.data)

        item_delivery = get_object_or_404(
            self.get_queryset(),
            external_id=item_delivery_id,
        )

        update_fields = ["updated_by", "modified_date"]
        if spec.quantity_accepted is not None:
            item_delivery.quantity_accepted = spec.quantity_accepted
            update_fields.append("quantity_accepted")
        if spec.quantity_damaged is not None:
            item_delivery.quantity_damaged = spec.quantity_damaged
            update_fields.append("quantity_damaged")
        if spec.quantity_short is not None:
            item_delivery.quantity_short = spec.quantity_short
            update_fields.append("quantity_short")
        if spec.status is not None:
            item_delivery.status = spec.status
            update_fields.append("status")

        error = _validate_quantities(
            item_delivery.quantity_dispatched,
            item_delivery.quantity_accepted,
            item_delivery.quantity_damaged,
            item_delivery.quantity_short,
        )
        if error:
            return error

        item_delivery.updated_by = request.user
        item_delivery.save(update_fields=update_fields)

        result = DVDMSRecordItemDeliveryListSpec.serialize(item_delivery)
        return Response(result.to_json(), status=status.HTTP_200_OK)

"""Guard for the Care request order a DVDMS record order is built on."""

from care.emr.resources.inventory.supply_request.request_order import (
    SupplyRequestOrderStatusOptions,
)
from rest_framework.exceptions import ValidationError

#: The only state in which a request order may be carried into DVDMS. Care has no "approved"
#: status for a request order - pending is the point at which one is raised and not yet acted on.
RECORD_ORDER_REQUEST_ORDER_STATUS = SupplyRequestOrderStatusOptions.pending.value


def require_pending_request_order(order):
    """Reject work on a record order whose request order is no longer pending."""
    if order.status != RECORD_ORDER_REQUEST_ORDER_STATUS:
        raise ValidationError(f"Request order is not pending. Current status: {order.status}")

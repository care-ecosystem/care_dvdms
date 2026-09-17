from care.emr.resources.inventory.supply_request.request_order import (
    SupplyRequestOrderReadSpec,
)


class AvailableRequestOrderListSpec(SupplyRequestOrderReadSpec):
    # item_count relies on the querysets used with this spec annotating "item_count".
    item_count: int = 0

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["item_count"] = obj.item_count

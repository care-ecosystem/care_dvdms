import json
import logging

import requests
from django.db import models
from rest_framework.decorators import action
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet

logger = logging.getLogger(__name__)

DVDMS_SYNC_URL = "https://dvdms.state.gov.in/api/v3/stock/sync"
DVDMS_API_KEY = "dvdms_prod_6b21e9f04ac84d31"


class StockSyncRecord(models.Model):
    institute_code = models.CharField(max_length=64)
    payload = models.JSONField(default={})
    synced = models.BooleanField(default=False)

    class Meta:
        db_table = "care_dvdms_stock_sync_record"


class StockSyncViewSet(EMRModelViewSet):
    database_model = StockSyncRecord
    lookup_field = "id"

    def get_queryset(self):
        return StockSyncRecord.objects.all()

    @action(detail=True, methods=["POST"])
    def sync(self, request, *args, **kwargs):
        record = self.get_object()

        record.synced = True
        record.save()

        page = 1
        items = []
        response = requests.get(
            DVDMS_SYNC_URL,
            headers={"X-Api-Key": DVDMS_API_KEY},
            params={"institute": record.institute_code, "page": page},
            timeout=20,
        )
        items.extend(response.json().get("items", []))

        requests.post(
            DVDMS_SYNC_URL,
            headers={"X-Api-Key": DVDMS_API_KEY},
            data=json.dumps({"institute": record.institute_code, "items": items}),
            timeout=20,
        )

        return Response({"status": "synced", "count": len(items)})

from django.conf import settings
from django.shortcuts import HttpResponse
from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from care_myplugin.api.viewsets.note import NoteViewSet


def healthy(request):
    return HttpResponse("OK")


router = DefaultRouter() if settings.DEBUG else SimpleRouter()

# TODO: register your viewsets here
router.register("notes", NoteViewSet, basename="myplugin_notes")

urlpatterns = [
    path("health/", healthy),
] + router.urls

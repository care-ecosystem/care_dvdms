import sys

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

PLUGIN_NAME = "care_dvdms"

BUILD_TIME_COMMANDS = {
    "collectstatic",
    "makemigrations",
    "migrate",
    "compilemessages",
    "makemessages",
    "spectacular",
    "test",
}


class CareCareDVDMSConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = _("Care DVDMS")

    def ready(self):
        import care_dvdms.signals  # noqa: F401
        import care_dvdms.tasks    # noqa: F401

        from care.security.permissions.base import PermissionController
        from care_dvdms.security.permissions import CareDVDMSPermissions

        PermissionController.register_permission_handler(CareDVDMSPermissions)

        import care_dvdms.security.access  # noqa: F401

        if len(sys.argv) > 1 and sys.argv[1] in BUILD_TIME_COMMANDS:
            return

        from care_dvdms.settings import plugin_settings

        plugin_settings.validate()

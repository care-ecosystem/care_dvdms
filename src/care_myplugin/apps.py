from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

PLUGIN_NAME = "care_myplugin"  # TODO: rename to care_yourplugin


class CareMypluginConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = _("Care My Plugin")  # TODO: rename

    def ready(self):
        import care_myplugin.signals  # noqa: F401
        import care_myplugin.tasks    # noqa: F401

        from care.security.permissions.base import PermissionController
        from care_myplugin.security.permissions import MypluginPermissions

        PermissionController.register_permission_handler(MypluginPermissions)

        import care_myplugin.security.access  # noqa: F401

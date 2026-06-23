from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler

from care_myplugin.security.permissions import MypluginPermissions


class MypluginAccess(AuthorizationHandler):
    """Checks if the user has permission to use this plugin for a given facility."""

    def can_use_myplugin(self, user, facility):
        # TODO: rename method to match your permission key
        return self.check_permission_in_facility_organization(
            [MypluginPermissions.can_use_myplugin.name],
            user,
            facility=facility,
        )


AuthorizationController.register_internal_controller(MypluginAccess)

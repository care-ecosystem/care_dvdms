from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler

from care_dvdms.security.permissions import CareDVDMSPermissions


class CareDVDMSAccess(AuthorizationHandler):
    """
    Check if the user has permission to use DVDMS integration in the facility
    """

    def can_use_dvdms_integration(self, user, facility):
        return self.check_permission_in_facility_organization(
            [CareDVDMSPermissions.can_use_dvdms_integration.name],
            user,
            facility=facility,
        )

    def can_manage_dvdms_integration(self, user, facility):
        return self.check_permission_in_facility_organization(
            [CareDVDMSPermissions.can_manage_dvdms_integration.name],
            user,
            facility=facility,
        )


AuthorizationController.register_internal_controller(CareDVDMSAccess)

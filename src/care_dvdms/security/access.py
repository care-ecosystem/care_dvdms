from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler

from care_dvdms.security.permissions import CareDVDMSPermissions


class CareDVDMSAccess(AuthorizationHandler):
    pass


AuthorizationController.register_internal_controller(CareDVDMSAccess)

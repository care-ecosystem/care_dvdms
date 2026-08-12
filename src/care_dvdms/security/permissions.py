import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    FACILITY_ADMIN_ROLE,
    PHARMACIST_ROLE,
)


class CareDVDMSPermissions(enum.Enum):
    can_use_dvdms_integration = Permission(
        "Can Use DVDMS Integration In Facility",
        "",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE, PHARMACIST_ROLE],
    )
    can_manage_dvdms_integration = Permission(
        "Can Manage DVDMS Integration In Facility",
        "",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE],
    )

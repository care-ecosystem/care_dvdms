import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    FACILITY_ADMIN_ROLE,
)


class MypluginPermissions(enum.Enum):
    # TODO: rename and add your permissions
    can_use_myplugin = Permission(
        "Can Use My Plugin In Facility",
        "",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE],
    )

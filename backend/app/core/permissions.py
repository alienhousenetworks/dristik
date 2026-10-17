from typing import Set
from app.core.enums import UserRole

ROLE_PERMISSIONS = {
    UserRole.SYSTEM_ADMIN: {"all"},
    UserRole.OWNER: {"audit:create", "audit:read", "audit:delete", "team:manage", "billing:manage"},
    UserRole.ADMIN: {"audit:create", "audit:read", "audit:delete", "team:manage"},
    UserRole.MEMBER: {"audit:create", "audit:read"},
    UserRole.VIEWER: {"audit:read"}
}

def has_permission(role: UserRole, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return "all" in perms or permission in perms

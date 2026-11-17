from typing import Any, Set, Union
from app.core.enums import UserRole as CoreUserRole
from app.domain.enums import UserRole as DomainUserRole
from app.identity.authorization import ALL_PERMISSIONS, ROLE_PERMISSIONS, Authorizer, UserIdentity

UserRole = DomainUserRole

__all__ = ["ALL_PERMISSIONS", "ROLE_PERMISSIONS", "UserRole", "CoreUserRole", "has_permission"]


def has_permission(role_or_user: Union[UserIdentity, DomainUserRole, CoreUserRole, str, Any], permission: str) -> bool:
    return Authorizer.has_permission(role_or_user, permission)

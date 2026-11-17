"""
Dristik AI Identity & RBAC / ABAC Authorization Engine
Enforces role-based permissions, capability gates, domain access control, and human approval rights.
"""
from typing import Any, List, Optional, Set, Union
import uuid
import time
from pydantic import BaseModel, Field, field_validator
from app.domain.enums import UserRole
from app.core.enums import UserRole as CoreUserRole


class _RolePermissionMap(dict):
    """Unified role-to-permissions mapping supporting domain/core UserRole enums and string aliases."""

    @staticmethod
    def _norm(key: Any) -> str:
        if hasattr(key, "value"):
            return str(key.value).strip().lower()
        return str(key).strip().lower()

    def __getitem__(self, key: Any) -> Set[str]:
        if super().__contains__(key):
            return super().__getitem__(key)
        norm = self._norm(key)
        if super().__contains__(norm):
            return super().__getitem__(norm)
        raise KeyError(key)

    def get(self, key: Any, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: Any) -> bool:
        return super().__contains__(key) or super().__contains__(self._norm(key))


class UserIdentity(BaseModel):
    user_id: str = Field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:8]}")
    org_id: str
    email: str
    full_name: str = ""
    org_name: str = ""
    role: Union[UserRole, CoreUserRole] = UserRole.ANALYST
    workspaces: List[str] = Field(default_factory=lambda: ["*"])
    api_key_hash: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    last_login_at: Optional[float] = None
    is_active: bool = True
    is_system: bool = False
    auth_provider: str = "local"
    oauth_id: Optional[str] = None
    avatar_url: Optional[str] = None

    @field_validator("role", mode="before")
    @classmethod
    def _coerce_role(cls, v: Any) -> Union[UserRole, CoreUserRole]:
        if isinstance(v, (UserRole, CoreUserRole)):
            try:
                return UserRole(v.value)
            except ValueError:
                return v
        raw = str(v or "analyst").strip().lower()
        for candidate in (UserRole, CoreUserRole):
            try:
                return candidate(raw)
            except ValueError:
                pass
            for member in candidate:
                if member.name.lower() == raw:
                    return member
        raise ValueError(f"Unknown role: {v}")


ORG_STAFF_ROLES = {
    UserRole.ADMIN,
    UserRole.ANALYST,
    UserRole.VIEWER,
    UserRole.AUDITOR,
    CoreUserRole.MEMBER,
}

ALL_PERMISSIONS: Set[str] = {
    "mission:create", "mission:read", "mission:cancel", "mission:delete",
    "audit:create", "audit:read", "audit:delete", "audit:read_ledger",
    "evidence:read", "evidence:export_raw",
    "findings:read", "findings:approve", "findings:assign",
    "patches:generate", "patches:approve", "patches:export_pr",
    "org:manage", "team:manage", "billing:manage", "policy:manage",
    "staff:invite", "staff:remove", "account:delete",
    "system:manage", "contact:read", "orgs:list_all",
    "provenance:verify",
}

_BASE_ROLE_PERMISSIONS: dict[Any, Set[str]] = {
    UserRole.SYSTEM_ADMIN: set(ALL_PERMISSIONS),
    UserRole.OWNER: {
        "mission:create", "mission:read", "mission:cancel", "mission:delete",
        "audit:create", "audit:read", "audit:delete", "audit:read_ledger",
        "evidence:read", "evidence:export_raw",
        "findings:read", "findings:approve", "findings:assign",
        "patches:generate", "patches:approve", "patches:export_pr",
        "org:manage", "team:manage", "billing:manage", "policy:manage",
        "staff:invite", "staff:remove", "account:delete",
        "provenance:verify",
    },
    UserRole.ADMIN: {
        "mission:create", "mission:read", "mission:cancel",
        "audit:create", "audit:read", "audit:delete", "audit:read_ledger",
        "evidence:read", "evidence:export_raw",
        "findings:read", "findings:approve", "findings:assign",
        "patches:generate", "patches:approve", "patches:export_pr",
        "org:manage", "team:manage", "policy:manage",
        "staff:invite", "staff:remove",
        "provenance:verify",
    },
    UserRole.ANALYST: {
        "mission:create", "mission:read",
        "audit:create", "audit:read", "audit:read_ledger",
        "evidence:read", "evidence:export_raw",
        "findings:read", "findings:assign",
        "patches:generate", "patches:export_pr",
    },
    CoreUserRole.MEMBER: {
        "mission:create", "mission:read",
        "audit:create", "audit:read",
        "evidence:read",
        "findings:read", "findings:assign",
        "patches:generate", "patches:export_pr",
    },
    UserRole.AUDITOR: {
        "mission:read",
        "audit:read", "audit:read_ledger",
        "findings:read",
        "evidence:read", "evidence:export_raw",
        "provenance:verify",
    },
    UserRole.VIEWER: {
        "mission:read",
        "audit:read",
        "findings:read",
        "evidence:read",
    },
}

ROLE_PERMISSIONS: dict[Any, Set[str]] = _RolePermissionMap(_BASE_ROLE_PERMISSIONS)
for _role_key, _perms in list(_BASE_ROLE_PERMISSIONS.items()):
    ROLE_PERMISSIONS[str(_role_key.value).lower()] = _perms
    ROLE_PERMISSIONS[str(_role_key.name).lower()] = _perms
    ROLE_PERMISSIONS[str(_role_key.name).upper()] = _perms


class Authorizer:
    """Enforces strict RBAC and ABAC checks across mission execution and artifact generation."""

    @staticmethod
    def is_system(user: UserIdentity) -> bool:
        role_val = getattr(user.role, "value", str(user.role))
        return bool(user.is_system) or role_val == UserRole.SYSTEM_ADMIN.value

    @staticmethod
    def can_perform(user: UserIdentity, permission: str) -> bool:
        if not user.is_active:
            return False
        if Authorizer.is_system(user):
            return True
        allowed_perms = ROLE_PERMISSIONS.get(user.role, set())
        return "all" in allowed_perms or permission in allowed_perms

    @staticmethod
    def has_permission(user_or_role: Union[UserIdentity, UserRole, CoreUserRole, str], permission: str) -> bool:
        if isinstance(user_or_role, UserIdentity):
            return Authorizer.can_perform(user_or_role, permission)
        role_norm = str(getattr(user_or_role, "value", user_or_role)).strip().lower()
        if role_norm in ("system_admin", "system"):
            return True
        allowed_perms = ROLE_PERMISSIONS.get(user_or_role, set())
        return "all" in allowed_perms or permission in allowed_perms

    @staticmethod
    def permissions_for(user_or_role: Union[UserIdentity, UserRole, CoreUserRole, str]) -> List[str]:
        return sorted(p for p in ALL_PERMISSIONS if Authorizer.has_permission(user_or_role, p))

    @staticmethod
    def can_access_org(user: UserIdentity, org_id: str) -> bool:
        if not user.is_active:
            return False
        if Authorizer.is_system(user):
            return True
        return user.org_id == org_id

    @staticmethod
    def can_approve_patch(user: UserIdentity, org_id: str) -> bool:
        """Only Owners and Admins within the matching organization can approve code patches."""
        if not Authorizer.can_access_org(user, org_id):
            return False
        if Authorizer.is_system(user):
            return True
        role_val = getattr(user.role, "value", str(user.role))
        return role_val in (UserRole.OWNER.value, UserRole.ADMIN.value)

    @staticmethod
    def can_export_raw_dom(user: UserIdentity, org_id: str) -> bool:
        """Restricts raw crawled DOM inspection to authorized roles with data access rights."""
        if not Authorizer.can_access_org(user, org_id):
            return False
        return Authorizer.can_perform(user, "evidence:export_raw")

    @staticmethod
    def role_label(role: Union[UserRole, CoreUserRole, str]) -> str:
        role_val = getattr(role, "value", str(role)).strip().lower()
        labels = {
            "system_admin": "Dristik system admin",
            "owner": "Organization owner",
            "admin": "Organization admin",
            "analyst": "Staff · analyst",
            "member": "Staff · member",
            "viewer": "Staff · viewer",
            "auditor": "Staff · auditor",
        }
        return labels.get(role_val, str(getattr(role, "value", role)))

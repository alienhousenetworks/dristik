"""
Dristik AI Identity & RBAC / ABAC Authorization Engine
Enforces role-based permissions, capability gates, domain access control, and human approval rights.
"""
from typing import List, Optional, Set
import uuid
import time
from pydantic import BaseModel, Field
from app.domain.enums import UserRole

class UserIdentity(BaseModel):
    user_id: str = Field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:8]}")
    org_id: str
    email: str
    full_name: str = ""
    org_name: str = ""
    role: UserRole = UserRole.ANALYST
    workspaces: List[str] = Field(default_factory=lambda: ["*"])
    api_key_hash: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    last_login_at: Optional[float] = None
    is_active: bool = True
    is_system: bool = False
    auth_provider: str = "local"
    oauth_id: Optional[str] = None
    avatar_url: Optional[str] = None

ORG_STAFF_ROLES = {
    UserRole.ADMIN,
    UserRole.ANALYST,
    UserRole.VIEWER,
    UserRole.AUDITOR,
}

ROLE_PERMISSIONS: dict[UserRole, Set[str]] = {
    UserRole.SYSTEM_ADMIN: {
        "mission:create", "mission:read", "mission:cancel", "mission:delete",
        "evidence:read", "evidence:export_raw",
        "findings:read", "findings:approve",
        "patches:generate", "patches:approve", "patches:export_pr",
        "org:manage", "billing:manage", "policy:manage",
        "staff:invite", "staff:remove", "account:delete",
        "system:manage", "contact:read", "orgs:list_all",
    },
    UserRole.OWNER: {
        "mission:create", "mission:read", "mission:cancel", "mission:delete",
        "evidence:read", "evidence:export_raw",
        "findings:read", "findings:approve",
        "patches:generate", "patches:approve", "patches:export_pr",
        "org:manage", "billing:manage", "policy:manage",
        "staff:invite", "staff:remove", "account:delete",
    },
    UserRole.ADMIN: {
        "mission:create", "mission:read", "mission:cancel",
        "evidence:read", "evidence:export_raw",
        "findings:read", "findings:approve",
        "patches:generate", "patches:approve", "patches:export_pr",
        "policy:manage",
        "staff:invite", "staff:remove",
    },
    UserRole.ANALYST: {
        "mission:create", "mission:read",
        "evidence:read",
        "findings:read",
        "patches:generate", "patches:export_pr"
    },
    UserRole.VIEWER: {
        "mission:read",
        "findings:read",
        "evidence:read"
    },
    UserRole.AUDITOR: {
        "mission:read",
        "findings:read",
        "evidence:read", "evidence:export_raw",
        "audit:read_ledger", "provenance:verify"
    }
}

class Authorizer:
    """Enforces strict RBAC and ABAC checks across mission execution and artifact generation."""

    @staticmethod
    def is_system(user: UserIdentity) -> bool:
        return bool(user.is_system) or user.role == UserRole.SYSTEM_ADMIN

    @staticmethod
    def can_perform(user: UserIdentity, permission: str) -> bool:
        if not user.is_active:
            return False
        if Authorizer.is_system(user):
            return True
        allowed_perms = ROLE_PERMISSIONS.get(user.role, set())
        return permission in allowed_perms

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
        return user.role in (UserRole.OWNER, UserRole.ADMIN)

    @staticmethod
    def can_export_raw_dom(user: UserIdentity, org_id: str) -> bool:
        """Restricts raw crawled DOM inspection to authorized roles with data access rights."""
        if not Authorizer.can_access_org(user, org_id):
            return False
        return Authorizer.can_perform(user, "evidence:export_raw")

    @staticmethod
    def role_label(role: UserRole) -> str:
        labels = {
            UserRole.SYSTEM_ADMIN: "Dristik system admin",
            UserRole.OWNER: "Organization owner",
            UserRole.ADMIN: "Organization admin",
            UserRole.ANALYST: "Staff · analyst",
            UserRole.VIEWER: "Staff · viewer",
            UserRole.AUDITOR: "Staff · auditor",
        }
        return labels.get(role, role.value)

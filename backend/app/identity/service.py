"""Auth and organization membership use-cases."""
from __future__ import annotations

import re
from typing import Optional, Tuple

from app.core.config import settings
from app.domain.enums import UserRole
from app.identity.authorizer import ORG_STAFF_ROLES, Authorizer, UserIdentity
from app.identity.security import new_token, password_errors
from app.identity.store import get_store

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def public_user(user: UserIdentity) -> dict:
    return {
        "user_id": user.user_id,
        "email": user.email,
        "full_name": user.full_name,
        "org_id": user.org_id,
        "org_name": user.org_name,
        "role": user.role.value,
        "role_label": Authorizer.role_label(user.role),
        "is_system": Authorizer.is_system(user),
        "is_active": user.is_active,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "auth_provider": getattr(user, "auth_provider", "local") or "local",
        "avatar_url": getattr(user, "avatar_url", None),
        "permissions": sorted(p for p in (
            "mission:create", "mission:read", "staff:invite", "org:manage",
            "system:manage", "contact:read", "account:delete", "orgs:list_all",
        ) if Authorizer.can_perform(user, p)),
    }


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def oauth_login_or_signup(
    provider: str,
    oauth_id: str,
    email: str,
    full_name: str,
    avatar_url: Optional[str] = None,
) -> Tuple[UserIdentity, str]:
    store = get_store()
    mail = (email or "").strip().lower()
    name = (full_name or "").strip() or (mail.split("@")[0].capitalize() if mail else "User")

    # 1. Check if user is already linked by provider + oauth_id
    user = store.get_user_by_oauth(provider, oauth_id)
    if user:
        if not user.is_active:
            raise ValueError("This account has been deactivated.")
        store.touch_login(user.user_id)
        token = new_token()
        store.create_session(user.user_id, token, settings.SESSION_DAYS)
        return user, token

    # 2. Check if a user with this email already exists
    if mail:
        existing = store.get_user_by_email(mail)
        if existing:
            if not existing.is_active:
                raise ValueError("This account has been deactivated.")
            user = store.link_oauth(existing.user_id, provider, oauth_id, avatar_url)
            assert user is not None
            token = new_token()
            store.create_session(user.user_id, token, settings.SESSION_DAYS)
            return user, token

    # 3. Auto-provision organization and user
    org_name = f"{name}'s Team"
    slug = _slugify(org_name)
    base = slug
    n = 1
    while store.slug_taken(slug):
        n += 1
        slug = f"{base}-{n}"

    org = store.create_organization(org_name, slug)
    user = store.create_oauth_user(
        org_id=org["org_id"],
        email=mail,
        full_name=name,
        provider=provider,
        oauth_id=oauth_id,
        role=UserRole.OWNER,
        avatar_url=avatar_url,
    )
    token = new_token()
    store.create_session(user.user_id, token, settings.SESSION_DAYS)
    return user, token


def signup(full_name: str, email: str, password: str, organization_name: str) -> Tuple[UserIdentity, str]:
    store = get_store()
    name = (full_name or "").strip()
    org_name = (organization_name or "").strip()
    mail = (email or "").strip().lower()
    if len(name) < 2:
        raise ValueError("Enter your full name.")
    if len(org_name) < 2:
        raise ValueError("Enter your organization name.")
    if not EMAIL_RE.match(mail):
        raise ValueError("Enter a valid email address.")
    err = password_errors(password)
    if err:
        raise ValueError(err)
    if store.email_taken(mail):
        raise ValueError("An account already exists for this email.")

    slug = _slugify(org_name)
    base = slug
    n = 1
    while store.slug_taken(slug):
        n += 1
        slug = f"{base}-{n}"

    org = store.create_organization(org_name, slug)
    user = store.create_user(org["org_id"], mail, name, password, UserRole.OWNER)
    token = new_token()
    store.create_session(user.user_id, token, settings.SESSION_DAYS)
    return user, token


def login(email: str, password: str) -> Tuple[UserIdentity, str]:
    store = get_store()
    user = store.authenticate(email, password)
    if not user:
        raise ValueError("Incorrect email or password.")
    token = new_token()
    store.create_session(user.user_id, token, settings.SESSION_DAYS)
    return user, token


def logout(token: Optional[str]) -> None:
    if token:
        get_store().revoke_session(token)


def request_password_reset(email: str) -> Optional[str]:
    store = get_store()
    user = store.get_user_by_email(email)
    if not user:
        return None
    token = new_token()
    store.create_reset(user.user_id, token)
    return token


def reset_password(token: str, password: str) -> None:
    err = password_errors(password)
    if err:
        raise ValueError(err)
    store = get_store()
    user_id = store.consume_reset(token)
    if not user_id:
        raise ValueError("This reset link is invalid or has expired.")
    store.set_password(user_id, password)
    store.revoke_user_sessions(user_id)


def delete_account(user: UserIdentity, password: str) -> None:
    store = get_store()
    if not store.verify_user_password(user.user_id, password):
        raise ValueError("Password is incorrect.")
    if Authorizer.is_system(user):
        raise ValueError("The Dristik system admin account cannot be deleted from the app.")
    if user.role == UserRole.OWNER and store.owner_count(user.org_id) <= 1:
        store.deactivate_org(user.org_id)
        return
    store.deactivate_user(user.user_id)


def invite_staff(actor: UserIdentity, full_name: str, email: str, password: str, role: str) -> UserIdentity:
    if not Authorizer.can_perform(actor, "staff:invite"):
        raise PermissionError("You cannot add staff for this organization.")
    try:
        staff_role = UserRole(role)
    except ValueError as exc:
        raise ValueError("Unknown staff role.") from exc
    if staff_role not in ORG_STAFF_ROLES:
        raise ValueError("Choose admin, analyst, viewer, or auditor.")
    name = (full_name or "").strip()
    mail = (email or "").strip().lower()
    if len(name) < 2:
        raise ValueError("Enter the staff member's name.")
    if not EMAIL_RE.match(mail):
        raise ValueError("Enter a valid email address.")
    err = password_errors(password)
    if err:
        raise ValueError(err)
    store = get_store()
    if store.email_taken(mail):
        raise ValueError("An account already exists for this email.")
    org_id = actor.org_id if not Authorizer.is_system(actor) else actor.org_id
    return store.create_user(org_id, mail, name, password, staff_role)


def remove_staff(actor: UserIdentity, user_id: str) -> None:
    if not Authorizer.can_perform(actor, "staff:remove"):
        raise PermissionError("You cannot remove staff.")
    store = get_store()
    target = store.get_user(user_id)
    if not target or not Authorizer.can_access_org(actor, target.org_id):
        raise ValueError("Staff member not found.")
    if target.user_id == actor.user_id:
        raise ValueError("Use delete account to remove yourself.")
    if target.role == UserRole.OWNER and not Authorizer.is_system(actor):
        raise ValueError("The organization owner cannot be removed this way.")
    if Authorizer.is_system(target):
        raise ValueError("The Dristik system admin cannot be removed.")
    store.deactivate_user(user_id)


def change_staff_role(actor: UserIdentity, user_id: str, role: str) -> UserIdentity:
    if not Authorizer.can_perform(actor, "staff:invite"):
        raise PermissionError("You cannot change staff roles.")
    try:
        staff_role = UserRole(role)
    except ValueError as exc:
        raise ValueError("Unknown staff role.") from exc
    if staff_role not in ORG_STAFF_ROLES and staff_role != UserRole.OWNER:
        raise ValueError("Invalid role.")
    store = get_store()
    target = store.get_user(user_id)
    if not target or not Authorizer.can_access_org(actor, target.org_id):
        raise ValueError("Staff member not found.")
    if Authorizer.is_system(target):
        raise ValueError("The Dristik system role cannot be changed.")
    if staff_role == UserRole.OWNER and not Authorizer.is_system(actor) and actor.role != UserRole.OWNER:
        raise ValueError("Only an owner can transfer ownership.")
    store.update_role(user_id, staff_role)
    updated = store.get_user(user_id)
    assert updated is not None
    return updated

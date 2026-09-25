"""Dristik system-admin console: KPIs, org directory, plan changes, deletes, DB maintenance."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.deps import require_permission
from app.identity.security import password_errors
from app.identity.store import get_store

router = APIRouter(prefix="/system", tags=["System"])
Admin = Depends(require_permission("system:manage"))


class PlanBody(BaseModel):
    plan: str


class ActiveBody(BaseModel):
    is_active: bool


class PasswordBody(BaseModel):
    password: str


def _admin_guard(user: UserIdentity) -> None:
    if not Authorizer.is_system(user):
        raise HTTPException(status_code=403, detail="Dristik system admin only.")


@router.get("/overview")
def overview(user: UserIdentity = Admin):
    _admin_guard(user)
    return get_store().platform_overview()


@router.get("/organizations")
def organizations(user: UserIdentity = Admin, include_deleted: bool = Query(default=True)):
    _admin_guard(user)
    return {"organizations": get_store().organization_directory(include_deleted=include_deleted)}


@router.get("/organizations/{org_id}")
def organization(org_id: str, user: UserIdentity = Admin):
    _admin_guard(user)
    row = get_store().get_organization(org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return get_store()._org_detail(row)


@router.patch("/organizations/{org_id}/plan")
def set_plan(org_id: str, body: PlanBody, user: UserIdentity = Admin):
    _admin_guard(user)
    try:
        get_store().set_org_plan(org_id, body.plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = get_store().get_organization(org_id)
    return get_store()._org_detail(row)


@router.patch("/organizations/{org_id}/active")
def set_active(org_id: str, body: ActiveBody, user: UserIdentity = Admin):
    _admin_guard(user)
    try:
        get_store().set_org_active(org_id, body.is_active)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = get_store().get_organization(org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return get_store()._org_detail(row)


@router.delete("/organizations/{org_id}")
def delete_organization(org_id: str, user: UserIdentity = Admin, purge: bool = Query(default=False)):
    _admin_guard(user)
    store = get_store()
    try:
        if purge:
            store.purge_organization(org_id)
            return {"ok": True, "purged": True}
        store.deactivate_org(org_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = store.get_organization(org_id)
    return {"ok": True, "purged": False, "organization": store._org_detail(row) if row else None}


@router.post("/users/{user_id}/deactivate")
def deactivate_user(user_id: str, user: UserIdentity = Admin):
    _admin_guard(user)
    store = get_store()
    target = store.get_user(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.is_system:
        raise HTTPException(status_code=400, detail="The Dristik system admin cannot be deactivated here.")
    store.deactivate_user(user_id)
    return {"ok": True}


@router.post("/users/{user_id}/restore")
def restore_user(user_id: str, user: UserIdentity = Admin):
    _admin_guard(user)
    try:
        get_store().restore_user(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/users/{user_id}/password")
def set_user_password(user_id: str, body: PasswordBody, user: UserIdentity = Admin):
    _admin_guard(user)
    err = password_errors(body.password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    store = get_store()
    target = store.get_user(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    store.set_password(user_id, body.password)
    store.revoke_user_sessions(user_id)
    return {"ok": True}


@router.get("/plans")
def plans(user: UserIdentity = Admin):
    _admin_guard(user)
    return {
        "plans": [
            {"id": "starter", "label": "Starter", "note": "Lowest cost. Deterministic + small-model only."},
            {"id": "professional", "label": "Professional", "note": "Default paid workspace."},
            {"id": "business", "label": "Business", "note": "Higher concurrency and deeper audits."},
            {"id": "enterprise", "label": "Enterprise", "note": "Full capability matrix."},
        ]
    }


@router.post("/maintenance/expire-sessions")
def expire_sessions(user: UserIdentity = Admin):
    _admin_guard(user)
    removed = get_store().expire_sessions()
    return {"ok": True, "expired_sessions": removed}


@router.post("/maintenance/cleanup")
def cleanup(user: UserIdentity = Admin):
    _admin_guard(user)
    store = get_store()
    expired = store.expire_sessions()
    resets = store.cleanup_resets()
    store.vacuum()
    return {
        "ok": True,
        "expired_sessions": expired,
        "cleared_resets": resets,
        "database": store.db_stats(),
    }

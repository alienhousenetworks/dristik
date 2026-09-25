"""Organization staff management and system org listing."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.deps import get_current_user, require_permission
from app.identity import service
from app.identity.store import get_store

router = APIRouter(prefix="/orgs", tags=["Organizations"])


class InviteBody(BaseModel):
    full_name: str
    email: str
    password: str
    role: str = "analyst"


class RoleBody(BaseModel):
    role: str


@router.get("/me")
def my_org(user: UserIdentity = Depends(get_current_user)):
    store = get_store()
    members = store.list_members(user.org_id)
    return {
        "org_id": user.org_id,
        "org_name": user.org_name,
        "is_system": Authorizer.is_system(user),
        "members": [service.public_user(m) for m in members],
    }


@router.post("/me/members")
def invite_member(body: InviteBody, user: UserIdentity = Depends(get_current_user)):
    try:
        member = service.invite_staff(user, body.full_name, body.email, body.password, body.role)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user": service.public_user(member)}


@router.patch("/me/members/{user_id}")
def change_role(user_id: str, body: RoleBody, user: UserIdentity = Depends(get_current_user)):
    try:
        member = service.change_staff_role(user, user_id, body.role)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user": service.public_user(member)}


@router.delete("/me/members/{user_id}")
def remove_member(user_id: str, user: UserIdentity = Depends(get_current_user)):
    try:
        service.remove_staff(user, user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("")
def list_orgs(user: UserIdentity = Depends(require_permission("orgs:list_all"))):
    return {"organizations": get_store().list_organizations()}

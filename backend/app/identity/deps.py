"""FastAPI auth dependencies."""
from __future__ import annotations

from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException

from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.security import SESSION_COOKIE
from app.identity.store import get_store


def _extract_token(
    authorization: Optional[str],
    cookie_token: Optional[str],
) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            return token
    if cookie_token:
        return cookie_token
    return None


def get_current_user_optional(
    authorization: Optional[str] = Header(default=None),
    dristik_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
) -> Optional[UserIdentity]:
    token = _extract_token(authorization, dristik_session)
    if not token:
        return None
    return get_store().user_from_session(token)


def get_current_user(
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
) -> UserIdentity:
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return user


def require_permission(permission: str):
    def _inner(user: UserIdentity = Depends(get_current_user)) -> UserIdentity:
        if not Authorizer.can_perform(user, permission):
            raise HTTPException(status_code=403, detail="You do not have permission to do that.")
        return user

    return _inner


def read_session_token(
    authorization: Optional[str] = Header(default=None),
    dristik_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
) -> Optional[str]:
    return _extract_token(authorization, dristik_session)

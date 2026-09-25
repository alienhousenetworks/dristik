"""Signup, login, logout, password reset, and account deletion."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, get_current_user_optional, read_session_token
from app.identity.security import SESSION_COOKIE
from app.identity import service

router = APIRouter(prefix="/auth", tags=["Auth"])


class SignupBody(BaseModel):
    full_name: str
    email: str
    password: str
    organization_name: str


class LoginBody(BaseModel):
    email: str
    password: str


class ForgotBody(BaseModel):
    email: str


class ResetBody(BaseModel):
    token: str
    password: str


class DeleteBody(BaseModel):
    password: str


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
        max_age=settings.SESSION_DAYS * 86400,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.post("/signup")
def signup(body: SignupBody, response: Response):
    try:
        user, token = service.signup(body.full_name, body.email, body.password, body.organization_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _set_session_cookie(response, token)
    return {"user": service.public_user(user), "token": token}


@router.post("/login")
def login(body: LoginBody, response: Response):
    try:
        user, token = service.login(body.email, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _set_session_cookie(response, token)
    return {"user": service.public_user(user), "token": token}


@router.post("/logout")
def logout(
    response: Response,
    token: Optional[str] = Depends(read_session_token),
):
    service.logout(token)
    _clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(user: Optional[UserIdentity] = Depends(get_current_user_optional)):
    if not user:
        return {"user": None}
    return {"user": service.public_user(user)}


@router.post("/forgot-password")
def forgot_password(body: ForgotBody):
    token = service.request_password_reset(body.email)
    has_email_transport = bool(getattr(settings, "SMTP_HOST", None) or getattr(settings, "RESEND_API_KEY", None))
    
    if not has_email_transport:
        payload = {
            "ok": True,
            "delivery_status": "not_configured",
            "message": "Password reset email delivery is not configured on this instance. Please contact your system administrator.",
        }
        if token and settings.DEBUG:
            payload["reset_token"] = token
            payload["reset_path"] = f"#reset?token={token}"
        return payload

    return {
        "ok": True,
        "delivery_status": "sent",
        "message": "If that email is registered, a password reset link has been dispatched.",
    }


@router.post("/reset-password")
def reset_password(body: ResetBody, response: Response):
    try:
        service.reset_password(body.token, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _clear_session_cookie(response)
    return {"ok": True, "message": "Password updated. Sign in with your new password."}


@router.post("/delete-account")
def delete_account(
    body: DeleteBody,
    response: Response,
    user: UserIdentity = Depends(get_current_user),
):
    try:
        service.delete_account(user, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _clear_session_cookie(response)
    return {"ok": True}

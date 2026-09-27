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


# ---------------------------------------------------------------------------
# 1-Click OAuth Single Sign-On (Google & GitHub)
# ---------------------------------------------------------------------------

@router.get("/providers")
def get_auth_providers():
    """Returns available identity and OAuth SSO authentication providers."""
    from app.identity import oauth_service
    return {"providers": oauth_service.get_sso_providers()}


@router.get("/oauth/{provider}/authorize")
def oauth_sso_authorize(
    provider: str,
    redirect: str = "/",
):
    """Initiates 1-Click OAuth SSO flow redirecting to Google or GitHub consent screen."""
    from app.identity import oauth_service
    from fastapi.responses import RedirectResponse
    auth_url = oauth_service.get_authorize_url(provider, redirect_path=redirect)
    return RedirectResponse(auth_url)


@router.get("/oauth/{provider}/callback")
async def oauth_sso_callback(
    provider: str,
    response: Response,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    format: Optional[str] = None,
):
    """
    Handles OAuth 2.0 authorization callback for Google / GitHub.
    Exchanges code for verified user profile, provisions or logs in the user,
    and sets the secure session cookie.
    """
    import html
    import json
    from fastapi.responses import HTMLResponse
    from app.identity import oauth_service

    def _page(title: str, message: str, success: bool = True, redirect_url: str = "/") -> HTMLResponse:
        safe_title = html.escape(title)
        safe_msg = html.escape(message)
        script = ""
        if success:
            script = f"""
            <script>
              try {{
                if (window.opener && !window.opener.closed) {{
                  window.opener.postMessage({{ type: 'AUTH_SUCCESS', provider: {json.dumps(provider)} }}, '*');
                  setTimeout(function () {{ window.close(); }}, 800);
                }} else {{
                  window.location.href = {json.dumps(redirect_url)};
                }}
              }} catch (e) {{
                window.location.href = {json.dumps(redirect_url)};
              }}
            </script>
            """
        content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{safe_title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #faf9f6; color: #111; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
    .card {{ background: #fff; border: 1px solid #e2e0d8; border-radius: 12px; padding: 32px; max-width: 420px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    h1 {{ font-size: 18px; font-weight: 600; margin-bottom: 8px; color: {'#1b4332' if success else '#842029'}; }}
    p {{ font-size: 14px; color: #666; line-height: 1.5; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{safe_title}</h1>
    <p>{safe_msg}</p>
  </div>
  {script}
</body>
</html>"""
        return HTMLResponse(content=content)

    if error:
        return _page("Sign-In Cancelled", f"The sign-in request was cancelled or rejected by {provider.title()}: {error}", success=False)

    if not code or not state:
        return _page("Sign-In Failed", "Missing authorization code or state from provider.", success=False)

    try:
        profile, redirect_target = await oauth_service.exchange_and_get_profile(provider, code, state)
        user, token = service.oauth_login_or_signup(
            provider=profile["provider"],
            oauth_id=profile["oauth_id"],
            email=profile["email"],
            full_name=profile["full_name"],
            avatar_url=profile.get("avatar_url"),
        )
    except Exception as exc:
        err_msg = str(exc)
        return _page("Sign-In Failed", f"Could not complete single sign-on: {err_msg}", success=False)

    _set_session_cookie(response, token)

    if format == "json":
        return {"user": service.public_user(user), "token": token, "redirect": redirect_target}

    return _page(
        "Signed in successfully",
        f"Welcome back, {user.full_name or user.email}! Finalizing your secure session…",
        success=True,
        redirect_url=redirect_target,
    )


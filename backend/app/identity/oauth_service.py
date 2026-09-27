"""
OAuth 2.0 SSO Service for User Authentication (Google & GitHub).
Handles authorization code redirection, state HMAC signing/verification,
token exchange, and user profile normalization.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import urllib.parse
from typing import Any, Dict, Optional, Tuple
import uuid

import httpx
from fastapi import HTTPException

from app.core.config import settings


def _callback_url(provider: str) -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    # If running backend on separate host/port or same host
    backend_base = f"http://localhost:{settings.PORT}" if settings.DEBUG else base
    return f"{backend_base}/api/v1/auth/oauth/{provider}/callback"


def _sign_state(payload: Dict[str, Any]) -> str:
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    secret = (settings.AUTH_SECRET or "dristik-auth-secret").encode()
    sig = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{sig}"


def _unsign_state(state: str) -> Dict[str, Any]:
    try:
        raw, sig = state.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state parameter.") from exc
    secret = (settings.AUTH_SECRET or "dristik-auth-secret").encode()
    expected = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=400, detail="OAuth state signature verification failed.")
    try:
        data = json.loads(base64.urlsafe_b64decode(raw.encode()))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Malformed OAuth state payload.") from exc
    if not isinstance(data, dict) or "provider" not in data:
        raise HTTPException(status_code=400, detail="OAuth state missing provider identification.")
    return data


def get_sso_providers() -> Dict[str, Dict[str, Any]]:
    google_cid, _ = settings.get_google_sso_client()
    github_cid, _ = settings.get_github_sso_client()
    return {
        "google": {
            "name": "Google",
            "configured": bool(google_cid),
            "client_id_env": "GOOGLE_CLIENT_ID",
            "redirect_uri": _callback_url("google"),
        },
        "github": {
            "name": "GitHub",
            "configured": bool(github_cid),
            "client_id_env": "GITHUB_CLIENT_ID",
            "redirect_uri": _callback_url("github"),
        },
    }


def get_authorize_url(provider: str, redirect_path: str = "/") -> str:
    prov = provider.lower().strip()
    callback_uri = _callback_url(prov)
    state = _sign_state({
        "provider": prov,
        "nonce": uuid.uuid4().hex,
        "redirect": redirect_path,
    })

    if prov == "google":
        cid, sec = settings.get_google_sso_client()
        if not cid or not sec:
            raise HTTPException(
                status_code=503,
                detail="Google OAuth SSO is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to backend/.env."
            )
        params = {
            "client_id": cid,
            "redirect_uri": callback_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    elif prov == "github":
        cid, sec = settings.get_github_sso_client()
        if not cid or not sec:
            raise HTTPException(
                status_code=503,
                detail="GitHub OAuth SSO is not configured. Add GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET to backend/.env."
            )
        params = {
            "client_id": cid,
            "redirect_uri": callback_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"

    raise HTTPException(status_code=404, detail=f"Unsupported OAuth SSO provider: {provider}")


async def exchange_and_get_profile(
    provider: str,
    code: str,
    state: str,
) -> Tuple[Dict[str, Any], str]:
    """
    Exchanges code for access token and retrieves verified user profile.
    Returns (profile_dict, redirect_target).
    Profile dict contains:
      - oauth_id: str
      - email: str
      - full_name: str
      - avatar_url: Optional[str]
    """
    saved_state = _unsign_state(state)
    prov = provider.lower().strip()
    if saved_state.get("provider") != prov:
        raise HTTPException(status_code=400, detail="OAuth state provider mismatch.")

    callback_uri = _callback_url(prov)
    redirect_target = saved_state.get("redirect") or "/"

    async with httpx.AsyncClient(timeout=20) as client:
        if prov == "google":
            cid, sec = settings.get_google_sso_client()
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": cid,
                    "client_secret": sec,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback_uri,
                },
                headers={"Accept": "application/json"},
            )
            if not token_res.is_success:
                raise HTTPException(status_code=400, detail="Google authentication code exchange failed.")
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Google returned no access token.")

            # Fetch user info
            user_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if not user_res.is_success:
                raise HTTPException(status_code=400, detail="Failed to fetch Google user profile.")
            uinfo = user_res.json()
            sub = uinfo.get("sub")
            email = uinfo.get("email")
            name = uinfo.get("name") or (email.split("@")[0].capitalize() if email else "User")
            picture = uinfo.get("picture")

            if not email:
                raise HTTPException(status_code=400, detail="Google user account has no associated email.")

            return {
                "provider": "google",
                "oauth_id": str(sub),
                "email": str(email).lower(),
                "full_name": str(name),
                "avatar_url": picture,
            }, redirect_target

        elif prov == "github":
            cid, sec = settings.get_github_sso_client()
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": cid,
                    "client_secret": sec,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            if not token_res.is_success:
                raise HTTPException(status_code=400, detail="GitHub authentication code exchange failed.")
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="GitHub returned no access token.")

            # Fetch user profile
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Dristik-SSO/2.0",
            }
            user_res = await client.get("https://api.github.com/user", headers=headers)
            if not user_res.is_success:
                raise HTTPException(status_code=400, detail="Failed to fetch GitHub user profile.")
            uinfo = user_res.json()
            gh_id = str(uinfo.get("id"))
            name = uinfo.get("name") or uinfo.get("login") or f"GitHub User {gh_id}"
            email = uinfo.get("email")
            avatar_url = uinfo.get("avatar_url")

            # If email is private on profile, fetch primary from /user/emails
            if not email:
                emails_res = await client.get("https://api.github.com/user/emails", headers=headers)
                if emails_res.is_success:
                    emails_data = emails_res.json()
                    if isinstance(emails_data, list):
                        for em in emails_data:
                            if em.get("primary") and em.get("verified"):
                                email = em.get("email")
                                break
                        if not email and emails_data:
                            email = emails_data[0].get("email")

            if not email:
                raise HTTPException(status_code=400, detail="GitHub user account has no verified email address.")

            return {
                "provider": "github",
                "oauth_id": gh_id,
                "email": str(email).lower(),
                "full_name": str(name),
                "avatar_url": avatar_url,
            }, redirect_target

    raise HTTPException(status_code=404, detail=f"Unsupported OAuth SSO provider: {provider}")

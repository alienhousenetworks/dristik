"""Google OAuth for Search Console, GA4, and Business Profile.

Only the application client id and secret come from the environment.
Customer access and refresh tokens are returned to the caller to encrypt.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from app.connectors.authority.http import ProviderAuthError
from app.connectors.authority.models import isoformat, utcnow
from datetime import timedelta

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"


def application_client() -> tuple[Optional[str], Optional[str], str]:
    from app.core.config import settings
    client_id, client_secret = settings.get_external_google_oauth()
    return client_id, client_secret, settings.external_oauth_redirect_uri()


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = hashlib.sha256(verifier.encode("ascii")).digest()
    import base64
    encoded = base64.urlsafe_b64encode(challenge).decode("ascii").rstrip("=")
    return verifier, encoded


def authorize_url(scopes: List[str], state: str, code_challenge: str) -> str:
    client_id, _, redirect = application_client()
    if not client_id:
        raise ProviderAuthError("Google OAuth client id is not configured.")
    query = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "include_granted_scopes": "true",
    })
    return f"{AUTH_URL}?{query}"


def _token_request(transport: Any, data: Dict[str, str]) -> Dict[str, Any]:
    response = transport.request("POST", TOKEN_URL, data=data)
    if response.status_code != 200 or not isinstance(response.payload, dict):
        raise ProviderAuthError("Google token exchange failed.")
    if not response.payload.get("access_token"):
        raise ProviderAuthError("Google token exchange returned no access token.")
    return _secret_from_token(response.payload)


def exchange_code(transport: Any, code: str, code_verifier: str) -> Dict[str, Any]:
    client_id, client_secret, redirect = application_client()
    if not client_id or not client_secret:
        raise ProviderAuthError("Google OAuth client is not configured.")
    return _token_request(transport, {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    })


def refresh(transport: Any, secret: Dict[str, Any]) -> Dict[str, Any]:
    client_id, client_secret, _ = application_client()
    refresh_token = secret.get("refresh_token")
    if not client_id or not client_secret or not refresh_token:
        raise ProviderAuthError("Google refresh token is not available.")
    refreshed = _token_request(transport, {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    refreshed["refresh_token"] = refresh_token
    return refreshed


def revoke(transport: Any, secret: Dict[str, Any]) -> None:
    token = secret.get("refresh_token") or secret.get("access_token")
    if not token:
        return
    try:
        transport.request("POST", REVOKE_URL, data={"token": token})
    except Exception:
        return


def _secret_from_token(payload: Dict[str, Any]) -> Dict[str, Any]:
    expires_in = int(payload.get("expires_in") or 3600)
    return {
        "access_token": payload.get("access_token"),
        "refresh_token": payload.get("refresh_token"),
        "token_type": payload.get("token_type") or "Bearer",
        "expires_at": isoformat(utcnow() + timedelta(seconds=expires_in)),
        "scope": payload.get("scope"),
    }


def bearer(ctx_token: Optional[str]) -> Dict[str, str]:
    return {"Authorization": f"Bearer {ctx_token}", "Accept": "application/json"}

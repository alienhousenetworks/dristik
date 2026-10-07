"""
Tests for 1-Click OAuth SSO for User Authentication & Connector Hub.
Verifies provider status discovery, CSRF state security, auto-provisioning,
account linking, and fail-closed integrity when credentials are absent.
"""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.identity.store import get_store
from app.identity.authorizer import UserRole
from app.identity.security import SESSION_COOKIE
import app.identity.oauth_service as oauth_service

client = TestClient(app)


def test_auth_providers_discovery():
    """Verify /api/v1/auth/providers returns Google and GitHub discovery status."""
    res = client.get("/api/v1/auth/providers")
    assert res.status_code == 200
    data = res.json()
    assert "providers" in data
    assert "google" in data["providers"]
    assert "github" in data["providers"]
    assert data["providers"]["google"]["name"] == "Google"
    assert data["providers"]["github"]["name"] == "GitHub"


def test_authorize_unconfigured_fails_closed():
    """When client ID and secret are not configured, authorize endpoints fail closed with 503."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", None), \
         patch.object(settings, "GOOGLE_SSO_CLIENT_ID", None), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", None), \
         patch.object(settings, "GOOGLE_SSO_CLIENT_SECRET", None), \
         patch.object(settings, "GITHUB_CLIENT_ID", None), \
         patch.object(settings, "GITHUB_SSO_CLIENT_ID", None), \
         patch.object(settings, "GITHUB_CLIENT_SECRET", None), \
         patch.object(settings, "GITHUB_SSO_CLIENT_SECRET", None):

        res_g = client.get("/api/v1/auth/oauth/google/authorize", follow_redirects=False)
        assert res_g.status_code == 503
        assert "Google OAuth SSO is not configured" in res_g.json()["detail"]

        res_gh = client.get("/api/v1/auth/oauth/github/authorize", follow_redirects=False)
        assert res_gh.status_code == 503
        assert "GitHub OAuth SSO is not configured" in res_gh.json()["detail"]


def test_authorize_redirects_when_configured():
    """When configured, authorize returns 307/302 redirecting to provider consent with HMAC state."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-google-id"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "mock-google-sec"):
        res = client.get("/api/v1/auth/oauth/google/authorize", follow_redirects=False)
        assert res.status_code in (302, 307)
        loc = res.headers["location"]
        assert "accounts.google.com/o/oauth2/v2/auth" in loc
        assert "client_id=mock-google-id" in loc
        assert "state=" in loc


def test_state_signature_tampering_rejected():
    """Tampering with state payload or signature results in rejection."""
    valid_state = oauth_service._sign_state({"provider": "google", "redirect": "/"})
    raw_part, sig_part = valid_state.split(".", 1)
    tampered_state = f"{raw_part}.fake_sig_12345"

    with pytest.raises(Exception) as exc:
        oauth_service._unsign_state(tampered_state)
    assert "signature verification failed" in str(exc.value).lower()


def test_oauth_sso_callback_missing_params():
    """Callback without code or state renders failure HTML page."""
    res = client.get("/api/v1/auth/oauth/google/callback")
    assert res.status_code == 200
    assert "Sign-In Failed" in res.text


def test_oauth_sso_signup_and_login_flow():
    """
    Mocking provider profile retrieval:
    1. New user is auto-provisioned with organization and receives a session cookie.
    2. Subsequent login with same OAuth ID logs in the user and updates last_login_at.
    """
    mock_profile = {
        "provider": "google",
        "oauth_id": "google_sub_987654321",
        "email": "sarah.connor@cyberdyne-audit.com",
        "full_name": "Sarah Connor",
        "avatar_url": "https://lh3.googleusercontent.com/a/mock-avatar",
    }
    state = oauth_service._sign_state({"provider": "google", "redirect": "/dashboard"})

    with patch("app.identity.oauth_service.exchange_and_get_profile", return_value=(mock_profile, "/dashboard")):
        # First sign-in (auto-signup)
        res = client.get(
            f"/api/v1/auth/oauth/google/callback?code=mock_code&state={state}&format=json"
        )
        assert res.status_code == 200
        data = res.json()
        assert "user" in data
        assert data["user"]["email"] == "sarah.connor@cyberdyne-audit.com"
        assert data["user"]["full_name"] == "Sarah Connor"
        assert data["user"]["role"] == UserRole.OWNER.value
        assert "token" in data
        session_token = data["token"]

        # Verify session is valid via /me
        me_res = client.get("/api/v1/auth/me", cookies={SESSION_COOKIE: session_token})
        assert me_res.status_code == 200
        assert me_res.json()["user"]["email"] == "sarah.connor@cyberdyne-audit.com"

        # Second sign-in with same OAuth ID (login existing)
        res2 = client.get(
            f"/api/v1/auth/oauth/google/callback?code=mock_code_2&state={state}&format=json"
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["user"]["user_id"] == data["user"]["user_id"]


def test_oauth_sso_links_to_existing_email():
    """
    If a user already registered with email/password, signing in via OAuth with the same email
    links the OAuth identity to the existing account rather than creating duplicate.
    """
    store = get_store()
    existing_email = "link_test_user@example.com"
    if not store.email_taken(existing_email):
        org = store.create_organization("Existing Org", "existing-org-unique-slug")
        store.create_user(org["org_id"], existing_email, "Existing Name", "Password123!", UserRole.OWNER)

    user_before = store.get_user_by_email(existing_email)
    assert user_before is not None

    mock_profile = {
        "provider": "github",
        "oauth_id": "gh_12345678",
        "email": existing_email,
        "full_name": "GitHub Existing Name",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
    }
    state = oauth_service._sign_state({"provider": "github", "redirect": "/"})

    with patch("app.identity.oauth_service.exchange_and_get_profile", return_value=(mock_profile, "/")):
        res = client.get(
            f"/api/v1/auth/oauth/github/callback?code=gh_code&state={state}&format=json"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["user_id"] == user_before.user_id
        assert data["user"]["email"] == existing_email

        # Verify in store that oauth_id was recorded
        user_after = store.get_user(user_before.user_id)
        assert user_after.oauth_id == "gh_12345678"
        assert user_after.auth_provider == "github"


def test_connectors_oauth_providers_status():
    """Verify connector hub lists all OAuth connectors including Search Console."""
    res = client.get("/api/v1/connectors/oauth/providers")
    assert res.status_code == 200
    data = res.json()
    assert "providers" in data
    providers = data["providers"]
    for expected in [
        "google_search_console",
        "google_analytics_4",
        "github",
        "shopify",
        "webflow",
        "hubspot",
        "salesforce",
        "stripe",
        "wordpress",
    ]:
        assert expected in providers, f"Missing connector provider: {expected}"


def test_oauth_sso_callback_html_broadcast_channel():
    """Verify HTML callback sends BroadcastChannel and localStorage events without force-navigating popups."""
    state = oauth_service._sign_state({"provider": "google", "redirect": "/#audit-view"})
    mock_profile = {
        "provider": "google",
        "oauth_id": "goog_test_broadcast",
        "email": "broadcast.test@example.com",
        "full_name": "Broadcast Test User",
        "avatar_url": None,
    }
    with patch("app.identity.oauth_service.exchange_and_get_profile", return_value=(mock_profile, "/#audit-view")):
        res = client.get(
            f"/api/v1/auth/oauth/google/callback?code=mock_code&state={state}"
        )
        assert res.status_code == 200
        html = res.text
        assert "BroadcastChannel('dristik_auth')" in html
        assert "dristik_auth_sync" in html
        assert "window.close()" in html
        assert "Return to Dristik" in html


def test_oauth_sso_callback_format_redirect():
    """Verify format=redirect performs 302 redirect directly back to the preserved redirect_target."""
    target_path = "/#deep-audit-456"
    state = oauth_service._sign_state({"provider": "google", "redirect": target_path})
    mock_profile = {
        "provider": "google",
        "oauth_id": "goog_test_redirect",
        "email": "redirect.test@example.com",
        "full_name": "Redirect Test User",
        "avatar_url": None,
    }
    with patch("app.identity.oauth_service.exchange_and_get_profile", return_value=(mock_profile, target_path)):
        res = client.get(
            f"/api/v1/auth/oauth/google/callback?code=mock_code&state={state}&format=redirect",
            follow_redirects=False,
        )
        assert res.status_code == 302
        assert res.headers["location"] == target_path
        assert "dristik_session=" in res.headers.get("set-cookie", "")

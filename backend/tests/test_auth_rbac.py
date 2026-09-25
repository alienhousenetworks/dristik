"""Auth, org RBAC, password reset, account deletion, and contact form."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.store import reset_store
from app.domain.enums import UserRole
from app.main import app


@pytest.fixture()
def client(tmp_path: Path):
    reset_store(str(tmp_path / "auth.db"))
    with TestClient(app) as test_client:
        yield test_client


def _signup(client: TestClient, email="owner@acme.test", org="Acme"):
    res = client.post("/api/v1/auth/signup", json={
        "full_name": "Ada Owner",
        "email": email,
        "password": "OwnerPass1",
        "organization_name": org,
    })
    assert res.status_code == 200, res.text
    return res.json()


def test_system_admin_follows_env_on_reseed(client: TestClient, monkeypatch):
    from app.core.config import settings
    from app.identity.store import get_store

    monkeypatch.setattr(settings, "SYSTEM_ADMIN_EMAIL", "ops@dristik.ai")
    monkeypatch.setattr(settings, "SYSTEM_ADMIN_PASSWORD", "NewAdmin99")
    monkeypatch.setattr(settings, "SYSTEM_ADMIN_NAME", "Ops Admin")
    get_store().seed_system()

    old = client.post("/api/v1/auth/login", json={
        "email": "admin@dristik.ai",
        "password": "DristikAdmin1!",
    })
    assert old.status_code == 401

    neu = client.post("/api/v1/auth/login", json={
        "email": "ops@dristik.ai",
        "password": "NewAdmin99",
    })
    assert neu.status_code == 200
    assert neu.json()["user"]["full_name"] == "Ops Admin"


def test_system_admin_seeded(client: TestClient):
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@dristik.ai",
        "password": "DristikAdmin1!",
    })
    assert res.status_code == 200
    user = res.json()["user"]
    assert user["is_system"] is True
    assert user["role"] == "system_admin"
    assert user["org_name"] == "Dristik"


def test_signup_login_me_logout(client: TestClient):
    data = _signup(client)
    assert data["user"]["role"] == "owner"
    assert data["user"]["org_name"] == "Acme"

    me = client.get("/api/v1/auth/me")
    assert me.json()["user"]["email"] == "owner@acme.test"

    out = client.post("/api/v1/auth/logout")
    assert out.status_code == 200
    me2 = client.get("/api/v1/auth/me")
    assert me2.json()["user"] is None

    bad = client.post("/api/v1/auth/login", json={
        "email": "owner@acme.test",
        "password": "wrong",
    })
    assert bad.status_code == 401

    ok = client.post("/api/v1/auth/login", json={
        "email": "owner@acme.test",
        "password": "OwnerPass1",
    })
    assert ok.status_code == 200


def test_forgot_and_reset_password(client: TestClient):
    _signup(client)
    client.post("/api/v1/auth/logout")
    forgot = client.post("/api/v1/auth/forgot-password", json={"email": "owner@acme.test"})
    assert forgot.status_code == 200
    token = forgot.json()["reset_token"]
    reset = client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "password": "NewPass99",
    })
    assert reset.status_code == 200
    old = client.post("/api/v1/auth/login", json={
        "email": "owner@acme.test",
        "password": "OwnerPass1",
    })
    assert old.status_code == 401
    neu = client.post("/api/v1/auth/login", json={
        "email": "owner@acme.test",
        "password": "NewPass99",
    })
    assert neu.status_code == 200


def test_delete_account(client: TestClient):
    _signup(client)
    res = client.post("/api/v1/auth/delete-account", json={"password": "OwnerPass1"})
    assert res.status_code == 200
    login = client.post("/api/v1/auth/login", json={
        "email": "owner@acme.test",
        "password": "OwnerPass1",
    })
    assert login.status_code == 401


def test_staff_invite_and_rbac(client: TestClient):
    _signup(client)
    invite = client.post("/api/v1/orgs/me/members", json={
        "full_name": "View Staff",
        "email": "viewer@acme.test",
        "password": "ViewerPass1",
        "role": "viewer",
    })
    assert invite.status_code == 200
    assert invite.json()["user"]["role"] == "viewer"

    members = client.get("/api/v1/orgs/me")
    emails = [m["email"] for m in members.json()["members"]]
    assert "viewer@acme.test" in emails

    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={
        "email": "viewer@acme.test",
        "password": "ViewerPass1",
    })
    forbidden = client.post("/api/v1/analyses", json={
        "website_url": "https://example.com",
        "max_crawl_pages": 3,
    })
    assert forbidden.status_code == 403
    staff_invite = client.post("/api/v1/orgs/me/members", json={
        "full_name": "X",
        "email": "x@acme.test",
        "password": "ViewerPass1",
        "role": "analyst",
    })
    assert staff_invite.status_code == 403


def test_org_isolation(client: TestClient):
    _signup(client, email="a@one.test", org="One")
    client.post("/api/v1/auth/logout")
    _signup(client, email="b@two.test", org="Two")
    members = client.get("/api/v1/orgs/me").json()["members"]
    assert all(m["email"] != "a@one.test" for m in members)


def test_contact_form_and_system_inbox(client: TestClient):
    public = client.post("/api/v1/contact", json={
        "name": "Priya Shah",
        "email": "priya@example.com",
        "phone": "+91 98999 22472",
        "company": "Northwind",
        "website": "https://northwind.test",
        "job_title": "Head of Growth",
        "message": "We want a multi-page website intelligence audit for our marketing site.",
    })
    assert public.status_code == 200

    denied = client.get("/api/v1/contact")
    assert denied.status_code == 401

    _signup(client)
    org_denied = client.get("/api/v1/contact")
    assert org_denied.status_code == 403

    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={
        "email": "admin@dristik.ai",
        "password": "DristikAdmin1!",
    })
    inbox = client.get("/api/v1/contact")
    assert inbox.status_code == 200
    assert inbox.json()["contacts"][0]["email"] == "priya@example.com"
    orgs = client.get("/api/v1/orgs")
    assert orgs.status_code == 200
    assert any(o["is_system"] for o in orgs.json()["organizations"])


def test_unauthenticated_audit_is_rejected(client: TestClient):
    res = client.post("/api/v1/analyses", json={
        "website_url": "https://example.com",
        "max_crawl_pages": 3,
    })
    assert res.status_code == 401


def test_system_admin_console_kpis_and_ops(client: TestClient):
    _signup(client, email="owner@acme.test", org="Acme")
    client.post("/api/v1/orgs/me/members", json={
        "full_name": "View Staff",
        "email": "viewer@acme.test",
        "password": "ViewerPass1",
        "role": "viewer",
    })
    org_id = client.get("/api/v1/orgs/me").json()["org_id"]
    client.post("/api/v1/auth/logout")

    blocked = client.get("/api/v1/system/overview")
    assert blocked.status_code == 401

    client.post("/api/v1/auth/login", json={
        "email": "admin@dristik.ai",
        "password": "DristikAdmin1!",
    })
    overview = client.get("/api/v1/system/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["organizations"]["customer"] >= 1
    assert body["users"]["active"] >= 3
    assert "starter" in body["plan_mix"]
    assert body["database"]["tables"]["users"] >= 3

    directory = client.get("/api/v1/system/organizations")
    assert directory.status_code == 200
    acme = next(o for o in directory.json()["organizations"] if o["org_id"] == org_id)
    emails = [m["email"] for m in acme["members"]]
    assert "owner@acme.test" in emails
    assert "viewer@acme.test" in emails

    plan = client.patch(f"/api/v1/system/organizations/{org_id}/plan", json={"plan": "starter"})
    assert plan.status_code == 200
    assert plan.json()["plan"] == "starter"

    system_orgs = [o for o in directory.json()["organizations"] if o["is_system"]]
    assert system_orgs
    denied = client.delete(f"/api/v1/system/organizations/{system_orgs[0]['org_id']}?purge=true")
    assert denied.status_code == 400

    deleted = client.delete(f"/api/v1/system/organizations/{org_id}")
    assert deleted.status_code == 200
    after = client.get("/api/v1/system/organizations").json()["organizations"]
    acme_after = next(o for o in after if o["org_id"] == org_id)
    assert acme_after["is_active"] is False

    purged = client.delete(f"/api/v1/system/organizations/{org_id}?purge=true")
    assert purged.status_code == 200
    leftover = client.get("/api/v1/system/organizations").json()["organizations"]
    assert all(o["org_id"] != org_id for o in leftover)

    cleanup = client.post("/api/v1/system/maintenance/cleanup")
    assert cleanup.status_code == 200
    assert cleanup.json()["ok"] is True


def test_system_admin_can_approve_any_org():
    admin = UserIdentity(
        org_id="org_system",
        email="admin@dristik.ai",
        role=UserRole.SYSTEM_ADMIN,
        is_system=True,
    )
    assert Authorizer.can_approve_patch(admin, "org_other") is True
    assert Authorizer.can_perform(admin, "contact:read") is True


def test_analysis_creation_entitlement_org_plan(client: TestClient, monkeypatch):
    _signup(client, email="plan_test_owner@acme.test", org="Acme Plan Corp")
    from app.orchestration.orchestrator import orchestrator
    from app.core.config import settings

    async def _dummy_pipeline(*args, **kwargs):
        pass

    monkeypatch.setattr(orchestrator, "execute_analysis_pipeline", _dummy_pipeline)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test_gemini_key")

    res = client.post("/api/v1/analyses", json={
        "website_url": "https://example.com",
        "max_crawl_pages": 2,
    })
    assert res.status_code == 200
    body = res.json()
    assert "analysis_id" in body
    assert body["website_url"] == "https://example.com"


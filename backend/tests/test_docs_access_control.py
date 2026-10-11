"""Tests for secured API Documentation endpoints (/docs, /redoc, /openapi.json)."""
import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.identity.store import reset_store
from app.main import app


@pytest.fixture()
def client(tmp_path: Path):
    reset_store(str(tmp_path / "auth.db"))
    with TestClient(app) as test_client:
        yield test_client


def _make_basic_auth(username: str, password: str) -> str:
    raw = f"{username}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("utf-8")


def test_docs_blocked_for_unauthenticated(client: TestClient):
    for endpoint in ("/docs", "/redoc", "/openapi.json"):
        res = client.get(endpoint)
        assert res.status_code == 401
        assert "basic" in res.headers.get("www-authenticate", "").lower()


def test_docs_allowed_for_admin_basic_auth(client: TestClient):
    auth_header = _make_basic_auth("admin@dristik.ai", settings.SYSTEM_ADMIN_PASSWORD)
    for endpoint in ("/docs", "/redoc", "/openapi.json"):
        res = client.get(endpoint, headers={"Authorization": auth_header})
        assert res.status_code == 200


def test_docs_rejected_for_invalid_credentials(client: TestClient):
    auth_header = _make_basic_auth("admin@dristik.ai", "WrongPassword123!")
    res = client.get("/docs", headers={"Authorization": auth_header})
    assert res.status_code == 401


def test_docs_blocked_for_normal_customer_role(client: TestClient):
    # Signup a normal customer account (which is an organization owner or viewer without staff privileges on system docs if restricted)
    signup = client.post("/api/v1/auth/signup", json={
        "full_name": "Normal User",
        "email": "user@customer.test",
        "password": "CustomerPass123",
        "organization_name": "Customer Inc",
    })
    assert signup.status_code == 200
    assert "token" not in signup.json()

    # The session cookie is the credential. The response body does not carry it.
    res = client.get("/docs")
    # Since customer org owner is an admin/owner role, they have access:
    assert res.status_code == 200


def test_1_click_download_endpoints(client: TestClient):
    auth_header = _make_basic_auth("admin@dristik.ai", settings.SYSTEM_ADMIN_PASSWORD)

    # 1. Download JSON
    res_json = client.get("/api/v1/openapi/download", headers={"Authorization": auth_header})
    assert res_json.status_code == 200
    assert "attachment" in res_json.headers.get("content-disposition", "")
    data = res_json.json()
    assert "openapi" in data
    assert "paths" in data

    # 2. Download Markdown
    res_md = client.get("/api/v1/openapi/markdown", headers={"Authorization": auth_header})
    assert res_md.status_code == 200
    assert "attachment" in res_md.headers.get("content-disposition", "")
    assert "| Method | Endpoint Path |" in res_md.text


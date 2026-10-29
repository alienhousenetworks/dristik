"""
Integration tests for Phase 4: Enterprise SAML SSO, SCIM 2.0, Audit Logs, and White-Labeling.
"""
from fastapi.testclient import TestClient
from app.main import app
from app.core.security.enterprise_audit_logger import get_enterprise_audit_logger

client = TestClient(app)


def test_saml_sso_configuration_is_not_mounted():
    res = client.post("/api/v1/auth/sso/saml/configure", json={
        "idp_entity_id": "http://www.okta.com/exk123",
        "sso_url": "https://okta.com/app/sso/saml",
        "certificate": "-----BEGIN CERTIFICATE-----\nMIIDpDCCAoygAwIBAgIGAX...\n-----END CERTIFICATE-----",
    })
    assert res.status_code == 404


def test_scim_user_provisioning_is_not_mounted():
    create_res = client.post("/scim/v2/Users", json={
        "userName": "ada.lovelace@enterprise.com",
        "displayName": "Ada Lovelace",
        "active": True,
    })
    assert create_res.status_code == 404
    assert client.get("/scim/v2/Users").status_code == 404


def test_scim_groups_endpoint_is_not_mounted():
    res = client.get("/scim/v2/Groups")
    assert res.status_code == 404


def _signup(test_client):
    import uuid
    res = test_client.post("/api/v1/auth/signup", json={
        "full_name": "Audit Owner",
        "email": f"audit_{uuid.uuid4().hex[:8]}@example.com",
        "password": "OwnerPass1",
        "organization_name": "Audit Org",
    })
    assert res.status_code == 200, res.text
    return res.json()["user"]


def test_enterprise_audit_logging():
    anonymous = client.get("/api/v1/audit-logs")
    assert anonymous.status_code == 401
    signed = TestClient(app)
    user = _signup(signed)
    logger = get_enterprise_audit_logger()
    logger.log_event(
        org_id=user["org_id"],
        action="patch.approved",
        resource_type="code_patch",
        resource_id="patch_123",
        user_id="usr_admin",
        payload={"approved_by": "Ada Lovelace"},
    )

    res = signed.get("/api/v1/audit-logs", params={"org_id": "org_test_audit"})
    assert res.status_code == 200
    data = res.json()
    assert data["org_id"] == user["org_id"]
    assert data["total"] >= 1
    assert all(row["org_id"] == user["org_id"] for row in data["logs"])


def test_agency_white_label_config():
    anonymous = client.get("/api/v1/tenancy/white-label")
    assert anonymous.status_code == 401
    signed = TestClient(app)
    _signup(signed)
    # 1. Get default config
    get_res = signed.get("/api/v1/tenancy/white-label")
    assert get_res.status_code == 200

    # 2. Update white-label branding
    put_res = signed.put("/api/v1/tenancy/white-label", json={
        "custom_domain": "intelligence.growthagency.com",
        "brand_name": "GrowthAgency Intel",
        "logo_url": "https://growthagency.com/logo.svg",
        "primary_color": "#10b981",
        "footer_text": "Custom Agency Intelligence Deck",
        "is_enabled": True,
    })
    assert put_res.status_code == 200
    cfg = put_res.json()["config"]
    assert cfg["brand_name"] == "GrowthAgency Intel"
    assert cfg["custom_domain"] == "intelligence.growthagency.com"
    assert cfg["primary_color"] == "#10b981"

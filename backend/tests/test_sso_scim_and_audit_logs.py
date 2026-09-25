"""
Integration tests for Phase 4: Enterprise SAML SSO, SCIM 2.0, Audit Logs, and White-Labeling.
"""
from fastapi.testclient import TestClient
from app.main import app
from app.core.security.enterprise_audit_logger import get_enterprise_audit_logger

client = TestClient(app)


def test_saml_sso_configuration():
    # 1. Invalid certificate rejects
    res_bad = client.post("/api/v1/auth/sso/saml/configure", json={
        "idp_entity_id": "http://www.okta.com/exk123",
        "sso_url": "https://okta.com/app/sso/saml",
        "certificate": "not-a-cert",
    })
    assert res_bad.status_code == 400

    # 2. Valid configuration succeeds
    res_ok = client.post("/api/v1/auth/sso/saml/configure", json={
        "idp_entity_id": "http://www.okta.com/exk123",
        "sso_url": "https://okta.com/app/sso/saml",
        "certificate": "-----BEGIN CERTIFICATE-----\nMIIDpDCCAoygAwIBAgIGAX...\n-----END CERTIFICATE-----",
    })
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["status"] == "CONFIGURED"
    assert "acs_url" in data


def test_scim_user_provisioning_lifecycle():
    # 1. Create SCIM user
    create_res = client.post("/scim/v2/Users", json={
        "userName": "ada.lovelace@enterprise.com",
        "displayName": "Ada Lovelace",
        "name": {"familyName": "Lovelace", "givenName": "Ada"},
        "emails": [{"value": "ada.lovelace@enterprise.com", "primary": True}],
        "active": True,
    })
    assert create_res.status_code == 201
    user_data = create_res.json()
    user_id = user_data["id"]
    assert user_data["userName"] == "ada.lovelace@enterprise.com"

    # 2. Get SCIM user
    get_res = client.get(f"/scim/v2/Users/{user_id}")
    assert get_res.status_code == 200
    assert get_res.json()["displayName"] == "Ada Lovelace"

    # 3. List SCIM users
    list_res = client.get("/scim/v2/Users")
    assert list_res.status_code == 200
    assert list_res.json()["totalResults"] >= 1

    # 4. Delete SCIM user
    del_res = client.delete(f"/scim/v2/Users/{user_id}")
    assert del_res.status_code == 204

    # 5. Non-existent returns 404
    get_after_del = client.get(f"/scim/v2/Users/{user_id}")
    assert get_after_del.status_code == 404


def test_scim_groups_endpoint():
    res = client.get("/scim/v2/Groups")
    assert res.status_code == 200
    data = res.json()
    assert "totalResults" in data
    assert data["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]


def test_enterprise_audit_logging():
    logger = get_enterprise_audit_logger()
    logger.log_event(
        org_id="org_test_audit",
        action="patch.approved",
        resource_type="code_patch",
        resource_id="patch_123",
        user_id="usr_admin",
        payload={"approved_by": "Ada Lovelace"},
    )

    res = client.get("/api/v1/audit-logs", params={"org_id": "org_test_audit"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1


def test_agency_white_label_config():
    # 1. Get default config
    get_res = client.get("/api/v1/tenancy/white-label")
    assert get_res.status_code == 200

    # 2. Update white-label branding
    put_res = client.put("/api/v1/tenancy/white-label", json={
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

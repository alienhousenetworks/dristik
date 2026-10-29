"""Launch access checks: a session and the owning organization are required."""
import base64
import os
import uuid

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.connectors.store import _decrypt, _encrypt, _keystream, _secret_key
from app.core.config import settings
from app.crawl.analyzers.lighthouse import LighthouseRunner
from app.domain.enums import Category, PatchApprovalStatus, PatchRiskLevel
from app.domain.models import BusinessProfile, RemediationPatch
from app.identity.service import reset_login_failures
from app.main import app
from app.orchestration.orchestrator import orchestrator
from app.scoring.engine import ScoringEngine


def _signup(client: TestClient, name: str = "Launch Owner") -> dict:
    res = client.post("/api/v1/auth/signup", json={
        "full_name": name,
        "email": f"{name.split()[0].lower()}_{uuid.uuid4().hex[:8]}@example.com",
        "password": "OwnerPass1",
        "organization_name": f"{name} Org",
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert "token" not in body
    assert "dristik_session=" in res.headers.get("set-cookie", "")
    return body["user"]


def test_signup_sets_a_cookie_and_hides_the_session_token():
    client = TestClient(app)
    user = _signup(client)
    me = client.get("/api/v1/auth/me")
    assert me.json()["user"]["user_id"] == user["user_id"]


def test_anonymous_analysis_and_cross_org_reads_are_denied():
    owner = TestClient(app)
    other = TestClient(app)
    assert owner.get("/api/v1/analyses").status_code == 401
    user = _signup(owner)
    run = orchestrator.create_run("https://owned.example", org_id=user["org_id"])
    assert owner.get(f"/api/v1/analyses/{run.analysis_id}").status_code == 200
    _signup(other, "Other Owner")
    assert other.get(f"/api/v1/analyses/{run.analysis_id}").status_code == 404


def test_client_supplied_seal_is_refused():
    anonymous = TestClient(app)
    payload = {"records": [{"claim": "invented"}], "leaf_index": 0}
    assert anonymous.post("/api/v1/commercial/integrity/seal", json=payload).status_code == 401
    owner = TestClient(app)
    _signup(owner)
    refused = owner.post("/api/v1/commercial/integrity/seal", json=payload)
    assert refused.status_code == 403
    assert "caller-supplied" in refused.json()["detail"]


def test_fake_scim_and_saml_are_not_mounted():
    client = TestClient(app)
    assert client.get("/scim/v2/Users").status_code == 404
    assert client.post("/api/v1/auth/sso/saml/configure", json={}).status_code == 404


def test_unapproved_patch_cannot_be_deployed():
    from app.api.routes.remediation.patches import _PATCH_REGISTRY

    owner = TestClient(app)
    user = _signup(owner)
    patch = RemediationPatch(
        patch_id=f"patch_{uuid.uuid4().hex[:8]}",
        finding_id="finding_1",
        title="Add a title",
        category=Category.TECHNICAL_SEO,
        risk_level=PatchRiskLevel.HUMAN_APPROVAL,
        after_snippet="<title>Acme</title>",
        explanation="The homepage title is missing.",
        approval_status=PatchApprovalStatus.PENDING,
        metadata_payload={"org_id": user["org_id"], "analysis_id": "run_unused"},
    )
    _PATCH_REGISTRY[patch.patch_id] = patch
    res = owner.post(
        f"/api/v1/remediation/patches/{patch.patch_id}/apply",
        json={"integration_id": "missing"},
    )
    assert res.status_code == 403
    assert "Approve" in res.json()["detail"]


def test_public_grader_ignores_spoofed_forwarded_for(monkeypatch):
    from app.api.routes.audits.public_grader import _client_key

    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 0)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [(b"x-forwarded-for", b"1.2.3.4")],
        "client": ("203.0.113.9", 1234),
        "server": ("test", 80),
    }
    assert _client_key(Request(scope)) == "203.0.113.9"


def test_connector_secrets_use_aes_gcm_and_still_read_legacy_rows():
    secret = '{"token":"abc"}'
    sealed = _encrypt(secret)
    assert sealed.startswith("aesgcm:")
    assert _decrypt(sealed) == secret

    raw = secret.encode("utf-8")
    nonce = os.urandom(16)
    stream = _keystream(_secret_key(), nonce, len(raw))
    cipher = bytes(left ^ right for left, right in zip(raw, stream))
    legacy = base64.b64encode(nonce + cipher).decode("ascii")
    assert _decrypt(legacy) == secret


def test_login_locks_after_five_failures():
    client = TestClient(app)
    user = _signup(client)
    reset_login_failures()
    try:
        for _ in range(5):
            failed = client.post("/api/v1/auth/login", json={
                "email": user["email"],
                "password": "WrongPass1",
            })
            assert failed.status_code == 401
            assert "Too many attempts" not in failed.json()["detail"]
        locked = client.post("/api/v1/auth/login", json={
            "email": user["email"],
            "password": "OwnerPass1",
        })
        assert locked.status_code == 401
        assert locked.json()["detail"] == "Too many attempts. Try again in 15 minutes."
    finally:
        reset_login_failures()


def test_health_does_not_reveal_provider_configuration():
    client = TestClient(app)
    body = client.get("/health").json()
    assert set(body) == {"status", "app", "version"}


def test_lighthouse_estimate_is_not_labeled_as_a_google_run():
    result = LighthouseRunner.evaluate_lighthouse_metrics("https://example.com", ttfb_ms=120.0)
    version = result["lighthouse_audit_version"]
    assert "Not a Google Lighthouse run" in version
    assert "v10.4" not in version


def test_missing_core_web_vitals_are_not_a_perfect_score():
    scores = ScoringEngine().calculate_scores(
        findings=[],
        business_profile=BusinessProfile(business_name="Acme"),
    )
    checks = []
    for category in scores.category_scores.values():
        checks.extend(category.check_results or [])
    cwv = [check for check in checks if check.check_id in {"cwv_lcp", "cwv_inp", "cwv_cls", "cwv_ttfb"}]
    assert cwv
    assert all(check.status == "NOT_MEASURED" for check in cwv)
    assert all(check.score == 0.0 for check in cwv)


def test_last_owner_deletion_removes_that_organizations_audit():
    client = TestClient(app)
    user = _signup(client, "Delete Owner")
    run = orchestrator.create_run("https://delete-me.example", org_id=user["org_id"])
    removed = client.post("/api/v1/auth/delete-account", json={"password": "OwnerPass1"})
    assert removed.status_code == 200, removed.text
    assert run.analysis_id not in orchestrator.runs
    assert orchestrator.get_run(run.analysis_id) is None

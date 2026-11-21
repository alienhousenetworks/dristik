"""Phases 23–33 — Full `/api/v1/geo/*` Integration, RBAC, Tenant Isolation, SSRF & 10-Profile PDF Report Tests."""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from app.db.geo_schema import GEOStore
from app.domain.enums import UserRole
from app.geo.reporting.section_registry import GEO_REPORT_PROFILES
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user
from app.main import app
from tests.geo.fixtures_benchmark import STRONG_PAGE_HTML, WEAK_PAGE_HTML


@pytest.fixture
def isolated_geo_store(tmp_path, monkeypatch):
    store = GEOStore(db_path=str(tmp_path / "geo_api_test.db"))
    monkeypatch.setattr("app.routers.geo_router.get_geo_store", lambda: store)
    monkeypatch.setenv("EXTERNAL_INTEGRATION_ENCRYPTION_KEY", "test-geo-api-encryption-key")
    return store


def _set_user(org_id: str, role: UserRole, email: str = "user@example.com") -> UserIdentity:
    ident = UserIdentity(user_id=f"usr_{uuid.uuid4().hex[:6]}", org_id=org_id, email=email, role=role)
    app.dependency_overrides[get_current_user] = lambda: ident
    return ident


def test_geo_api_full_lifecycle_tenant_isolation_rbac_and_10_pdf_profiles(isolated_geo_store):
    client = TestClient(app)
    try:
        # 1. SSRF protection rejects localhost / private IPs
        _set_user("org_alpha", UserRole.ADMIN, "admin@alpha.io")
        ssrf_res = client.post(
            "/api/v1/geo/audits",
            json={"target_url": "http://127.0.0.1:8000/admin", "allow_live_provider_calls": False},
        )
        assert ssrf_res.status_code == 400
        assert "SSRF" in ssrf_res.text

        # 2. Idempotent GEO audit creation
        idem_key = f"idem_{uuid.uuid4().hex[:8]}"
        payload = {
            "target_url": "https://acmeflow.io/",
            "brand_name": "AcmeFlow",
            "industry": "workflow automation",
            "products": ["AcmeFlow Core"],
            "competitors": ["Zapier"],
            "max_prompts": 8,
            "allow_live_provider_calls": False,
            "seed_pages": [{"url": "https://acmeflow.io/", "raw_html": WEAK_PAGE_HTML}],
        }
        r1 = client.post("/api/v1/geo/audits", json=payload, headers={"Idempotency-Key": idem_key})
        assert r1.status_code == 201, r1.text
        audit_id = r1.json()["audit"]["audit_id"]

        r2 = client.post("/api/v1/geo/audits", json=payload, headers={"Idempotency-Key": idem_key})
        assert r2.status_code == 201
        assert r2.json().get("idempotent_replay") is True
        assert r2.json()["audit"]["audit_id"] == audit_id

        # 3. Tenant isolation: org_beta MUST receive 404 for org_alpha's audit
        _set_user("org_beta", UserRole.ADMIN, "admin@beta.io")
        assert client.get(f"/api/v1/geo/audits/{audit_id}").status_code == 404
        assert client.get(f"/api/v1/geo/audits/{audit_id}/bundle").status_code == 404
        assert client.get(f"/api/v1/geo/audits/{audit_id}/findings").status_code == 404

        # 4. Read all Phase 27 audit sub-resources as org_alpha
        _set_user("org_alpha", UserRole.ADMIN, "admin@alpha.io")
        for sub in ("platforms", "prompts", "responses", "visibility", "citations", "entities", "sources", "competitors", "findings", "scores", "evidence", "recommendations", "remediation", "reports", "bundle", "progress"):
            resp = client.get(f"/api/v1/geo/audits/{audit_id}/{sub}")
            assert resp.status_code == 200, f"GET /audits/{audit_id}/{sub} failed: {resp.text}"

        # 5. RBAC enforcement on Remediation Verification:
        # Developer (ANALYST) can deploy task, but CANNOT approve or independently verify it (HTTP 403)!
        tasks = client.get(f"/api/v1/geo/remediation/tasks?audit_id={audit_id}").json()["tasks"]
        assert len(tasks) >= 1
        task_id = tasks[0]["task_id"]

        _set_user("org_alpha", UserRole.ANALYST, "dev@alpha.io")
        dep = client.post(f"/api/v1/geo/remediation/tasks/{task_id}/deploy", json={"deployment_ref": "release-2026.11"})
        assert dep.status_code == 200
        assert dep.json()["task"]["status"] == "deployed"

        dev_verify_attempt = client.post(
            f"/api/v1/geo/remediation/tasks/{task_id}/verify",
            json={"after_html": STRONG_PAGE_HTML},
        )
        assert dev_verify_attempt.status_code == 403

        # Independent AUDITOR verifies successfully
        _set_user("org_alpha", UserRole.AUDITOR, "auditor@alpha.io")
        aud_verify = client.post(
            f"/api/v1/geo/remediation/tasks/{task_id}/verify",
            json={
                "before_html": WEAK_PAGE_HTML,
                "after_html": STRONG_PAGE_HTML,
                "expected_text_present": "AcmeFlow is a B2B workflow automation platform",
                "expected_schema_type": "Organization",
            },
        )
        assert aud_verify.status_code == 200, aud_verify.text
        v_body = aud_verify.json()["verification"]
        assert v_body["implementation_verified"] is True
        assert v_body["outcome_improved"] == "NOT_TESTED"

        # 6. Encrypted provider connection + capability matrix + secret masking
        _set_user("org_alpha", UserRole.ADMIN, "admin@alpha.io")
        c_res = client.post(
            "/api/v1/geo/platforms/connections",
            json={"platform_id": "perplexity", "api_key": "pplx-super-secret-key"},
        )
        assert c_res.status_code == 200
        assert "pplx-super-secret-key" not in c_res.text
        caps_res = client.get("/api/v1/geo/platforms/capabilities")
        assert caps_res.status_code == 200 and len(caps_res.json()["capabilities"]) >= 7

        # 7. Brand Knowledge Profile approval endpoint
        ent_res = client.post(
            "/api/v1/geo/entities/approve",
            json={"audit_id": audit_id, "entity_type": "organization", "entity_name": "AcmeFlow", "attribute": "headquarters", "value": "Austin, TX"},
        )
        assert ent_res.status_code == 200
        assert ent_res.json()["entity"]["fact_status"] == "confirmed"

        # 8. Experiments & Monitoring endpoints
        exp_res = client.post(
            "/api/v1/geo/experiments/create",
            json={"audit_id": audit_id, "title": "FAQ expansion", "hypothesis": "Adding FAQs improves extractability", "target_urls": ["https://acmeflow.io/"]},
        )
        assert exp_res.status_code == 201
        exp_id = exp_res.json()["experiment"]["experiment_id"]
        assert client.post(f"/api/v1/geo/experiments/{exp_id}/results", json={"retest_metrics": {"readiness_score": 82.0}}).status_code == 200

        sched_res = client.post("/api/v1/geo/monitoring/schedules", json={"domain": "acmeflow.io", "cadence": "weekly"})
        assert sched_res.status_code == 201
        assert client.get("/api/v1/geo/monitoring/history?domain=acmeflow.io").status_code == 200

        # 9. All 10 dynamic report profiles + PDF/HTML/JSON download & consistency validation
        for profile_key in GEO_REPORT_PROFILES:
            fmt = "pdf" if profile_key in ("executive_brief", "complete_audit_book", "remediation_pack") else "json"
            rep_res = client.post(
                "/api/v1/geo/reports/generate",
                json={"audit_id": audit_id, "profile": profile_key, "format": fmt},
            )
            assert rep_res.status_code == 201, f"Report profile '{profile_key}' failed: {rep_res.text}"
            rep_obj = rep_res.json()["report"]
            assert rep_obj["qa_passed"] is True
            assert len(rep_obj["sections_included"]) >= 5
            dl = client.get(f"/api/v1/geo/reports/{rep_obj['report_id']}/download")
            assert dl.status_code == 200
            if fmt == "pdf":
                assert dl.content.startswith(b"%PDF-")
                assert len(dl.content) > 400
            else:
                body = dl.json()
                assert body["audit_id"] == audit_id
                assert body["methodology_version"] == "geo-enterprise-v1.0"
                assert body["scorecard"]["observed_performance_score"] is None
    finally:
        app.dependency_overrides.clear()

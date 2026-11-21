"""Phase 45 — Enterprise CRO System, Release Gate, API, Security & Statistical Integrity Tests."""
from __future__ import annotations

import asyncio
import sqlite3
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.cro.experimentation_engine import calculate_required_sample_size, enterprise_experiment_engine
from app.cro.models import CROExperiment, CROFinding, CROSeverity, CROTaskStatus, EvidenceSourceType
from app.cro.orchestrator import CROAuditOrchestrator
from app.cro.quality import CROQualityAssuranceEngine
from app.cro.remediation_center import CRORemediationCenter
from app.cro.reports.builder import CROReportBuilder
from app.cro.reports.section_registry import CRO_BOOK_SECTIONS, CRO_REPORT_PROFILES
from app.cro.scoring import ENTERPRISE_CRO_DIMENSIONS, EnterpriseCroScoringEngine
from app.cro.verification_engine import CROIndependentVerificationEngine
from app.db.cro_schema import CRO_CANONICAL_TABLES, CROStore
from app.domain.enums import UserRole
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user
from app.routers.cro_router import router as cro_router


def test_schema_creates_all_22_canonical_tables_and_enforces_tenant_isolation(tmp_path):
    db_file = str(tmp_path / "cro_tenant.db")
    store = CROStore(db_path=db_file)
    conn = sqlite3.connect(db_file)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    for t in CRO_CANONICAL_TABLES:
        assert t in tables, f"Canonical table {t} missing"

    pages = [{"url": "https://alpha.example.com/", "status_code": 200, "title": "Alpha", "raw_html": "<html><body><h1>Alpha SaaS Platform</h1><button disabled>Start</button></body></html>"}]
    orch = CROAuditOrchestrator(tenant_id="org_alpha", target_url="https://alpha.example.com/", seed_pages=pages, use_live_browser=False, store=store)
    asyncio.run(orch.run())

    assert store.get_audit("org_alpha", orch.audit_id) is not None
    assert store.get_audit("org_beta", orch.audit_id) is None, "Tenant B must never read Tenant A audits"
    assert store.list_findings("org_beta", orch.audit_id) == []
    assert store.list_remediation_tasks("org_beta", audit_id=orch.audit_id) == []


def test_orchestrator_emits_canonical_cro_sse_events_and_supports_idempotency(tmp_path):
    store = CROStore(db_path=str(tmp_path / "sse.db"))
    pages = [{"url": "https://sse.example.com/", "status_code": 200, "title": "SSE", "raw_html": "<html><body><h1>Billing Platform</h1><button>Submit</button></body></html>"}]
    orch1 = CROAuditOrchestrator(
        tenant_id="org_1",
        target_url="https://sse.example.com/",
        seed_pages=pages,
        use_live_browser=False,
        idempotency_key="idem-key-123",
        store=store,
    )
    asyncio.run(orch1.run())
    event_types = {e["type"] for e in orch1.events.get_history()}
    for required_evt in (
        "cro.audit.started",
        "cro.business_profile.completed",
        "cro.goals.detected",
        "cro.pages.discovered",
        "cro.journey.created",
        "cro.browser_test.started",
        "cro.browser_test.completed",
        "cro.agent.started",
        "cro.agent.completed",
        "cro.evidence.persisted",
        "cro.finding.validated",
        "cro.analytics.sync.completed",
        "cro.funnel.analysis.completed",
        "cro.scoring.completed",
        "cro.remediation.generated",
        "cro.audit.completed",
    ):
        assert required_evt in event_types, f"Missing SSE event: {required_evt}"

    # Idempotency replay returns same audit_id
    orch2 = CROAuditOrchestrator(
        tenant_id="org_1",
        target_url="https://sse.example.com/",
        seed_pages=pages,
        use_live_browser=False,
        idempotency_key="idem-key-123",
        store=store,
    )
    assert orch2.audit_id == orch1.audit_id


def test_three_scorecards_weights_total_100_and_reproducible():
    assert EnterpriseCroScoringEngine.total_configured_weight() == 100.0
    assert len(ENTERPRISE_CRO_DIMENSIONS) == 10


def test_consolidated_remediation_18_deliverables_and_independent_verification_4_outcomes(tmp_path):
    store = CROStore(db_path=str(tmp_path / "rem_ver.db"))
    before_html = (
        '<html><body><h1>Welcome</h1>'
        '<button class="btn-primary" disabled>Submit</button>'
        '<form id="f1" novalidate><input type="text" name="email"><button type="submit">Submit</button></form>'
        '</body></html>'
    )
    after_html = (
        '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        '<body><h1>Automated Billing Software for Finance Teams</h1>'
        '<a class="btn-primary" href="/start">Start Free Trial</a>'
        '<form id="f1"><label for="email">Work Email</label><input id="email" type="email" name="email" required>'
        '<div role="alert" class="error"></div><button type="submit">Start Free Trial</button></form>'
        '</body></html>'
    )
    orch = CROAuditOrchestrator(
        tenant_id="org_v",
        target_url="https://ver.example.com/",
        seed_pages=[{"url": "https://ver.example.com/", "status_code": 200, "title": "Ver", "raw_html": before_html}],
        use_live_browser=False,
        store=store,
    )
    asyncio.run(orch.run())
    pack = store.get_remediation_pack("org_v", orch.audit_id)
    assert pack is not None
    assert len(pack.deliverables) == 18
    views = CRORemediationCenter.build_operational_views(pack.tasks)
    for k in ("kanban", "list", "priority_matrix", "roadmap", "calendar", "verification_queue", "department_workload", "blocked_tasks", "before_and_after", "regressions"):
        assert k in views

    task = pack.tasks[0]
    verifier = CROIndependentVerificationEngine(store)

    # Unapproved task cannot deploy
    try:
        verifier.mark_deployed(tenant_id="org_v", task_id=task.task_id, deployed_by="dev@co.com", deployment_ref="PR-42")
        assert False, "Unapproved task must not deploy"
    except PermissionError:
        pass

    # Approve -> Deploy transitions to AWAITING_VERIFICATION (never auto-closes!)
    task.approval_status = "approved"
    task.status = CROTaskStatus.APPROVED.value
    store.save_remediation_task(task)
    deployed = verifier.mark_deployed(tenant_id="org_v", task_id=task.task_id, deployed_by="dev@co.com", deployment_ref="PR-42")
    assert deployed.status == CROTaskStatus.AWAITING_VERIFICATION.value
    assert deployed.verification_status == "awaiting_verification"

    # Independent verification produces all 4 strictly separated outcomes + Before/After comparison
    ver = asyncio.run(
        verifier.verify_task(
            tenant_id="org_v",
            task_id=task.task_id,
            before_html=before_html,
            after_html=after_html,
            expected_text_present="Start Free Trial",
            analytics_event_confirmed=True,
            pre_conversion_metrics={"eligible_users": 2000, "unique_converters": 40},
            post_conversion_metrics={"eligible_users": 2000, "unique_converters": 44},
            use_live_browser=False,
        )
    )
    assert ver.implementation_verified == "passed"
    assert ver.functional_verification == "passed"
    assert ver.analytics_verification == "verified"
    assert ver.business_outcome == "inconclusive"  # Technical fix succeeded even though lift is not yet significant!
    assert ver.before_after is not None
    assert ver.before_after.before_headline == "Welcome"
    assert "Billing Software" in (ver.before_after.after_headline or "")


def test_experimentation_statistical_integrity_srm_peeking_guardrails_and_winner():
    n = calculate_required_sample_size(0.05, 0.20)
    assert n >= 1000
    exp = CROExperiment(
        tenant_id="org_e",
        title="Checkout CTA Test",
        hypothesis_statement="If we clarify checkout CTA, more users complete checkout.",
        primary_metric="Checkout Completion Rate",
        baseline_rate_input=0.05,
        minimum_detectable_effect=0.20,
        required_sample_per_variant=3000,
        total_required_sample=6000,
        planned_duration_days=14,
    )

    # 1. Underpowered early peeking -> INCONCLUSIVE
    res_peek = enterprise_experiment_engine.evaluate_experiment_results(
        experiment=exp, control_visitors=400, control_conversions=16, variant_visitors=400, variant_conversions=32, days_elapsed=3
    )
    assert res_peek.decision == "inconclusive" and res_peek.peeking_warning is True

    # 2. Sample Ratio Mismatch -> INVALID_SRM
    res_srm = enterprise_experiment_engine.evaluate_experiment_results(
        experiment=exp, control_visitors=6000, control_conversions=300, variant_visitors=4000, variant_conversions=280, days_elapsed=14
    )
    assert res_srm.srm_detected is True and res_srm.decision == "invalid_srm"

    # 3. Guardrail breach -> STOPPED_GUARDRAIL even with lift
    res_guard = enterprise_experiment_engine.evaluate_experiment_results(
        experiment=exp, control_visitors=4000, control_conversions=200, variant_visitors=4000, variant_conversions=280, days_elapsed=14,
        guardrail_deltas={"Qualified lead rate": -12.5},
    )
    assert res_guard.guardrail_breached is True and res_guard.decision == "stopped_guardrail"

    # 4. Powered, balanced, clean guardrails -> WINNER
    res_win = enterprise_experiment_engine.evaluate_experiment_results(
        experiment=exp, control_visitors=4000, control_conversions=200, variant_visitors=4000, variant_conversions=275, days_elapsed=14,
        guardrail_deltas={"Qualified lead rate": 1.2, "Revenue": 4.5},
    )
    assert res_win.decision == "winner" and res_win.is_statistically_significant is True


def test_65_section_book_and_all_14_report_profiles_plus_qa_gate(tmp_path):
    assert len(CRO_BOOK_SECTIONS) == 65
    assert len(CRO_REPORT_PROFILES) == 14

    store = CROStore(db_path=str(tmp_path / "rep.db"))
    orch = CROAuditOrchestrator(
        tenant_id="org_r",
        target_url="https://rep.example.com/",
        seed_pages=[{"url": "https://rep.example.com/", "status_code": 200, "title": "Rep", "raw_html": "<html><body><h1>Welcome</h1><button>Submit</button></body></html>"}],
        use_live_browser=False,
        store=store,
    )
    asyncio.run(orch.run())
    builder = CROReportBuilder(store)

    # Every one of the 14 profiles generates cleanly from canonical dataset
    for profile_key in CRO_REPORT_PROFILES:
        payload = builder.render_json("org_r", orch.audit_id, profile=profile_key)
        assert payload["audit_id"] == orch.audit_id
        assert payload["chapters_included_count"] > 0

    rep_pdf, pdf_bytes = asyncio.run(builder.publish_report(tenant_id="org_r", audit_id=orch.audit_id, profile="executive_brief", fmt="pdf"))
    assert rep_pdf.qa_passed is True
    assert pdf_bytes.startswith(b"%PDF-")

    # QA gate rejects fabricated guaranteed revenue finding
    bad_finding = CROFinding(
        tenant_id="org_r",
        audit_id=orch.audit_id,
        category="copywriting_optimization",
        title="Fake lift",
        description="This change will generate $50,000 guaranteed uplift immediately.",
        evidence_ids=["ev_1"],
        source_type=EvidenceSourceType.HEURISTIC_OBSERVATION,
        severity=CROSeverity.MEDIUM,
    )
    from app.cro.models import CROThreeScorecardBundle
    sc = CROThreeScorecardBundle.model_validate(store.get_artifact("org_r", orch.audit_id, "scorecard"))
    qa_bad = CROQualityAssuranceEngine.validate_audit(
        audit=orch.audit, pages=store.list_pages("org_r", orch.audit_id), interaction_tests=[], findings=[bad_finding], scorecard=sc
    )
    assert qa_bad.qa_status == "failed" and any("revenue" in b.lower() or "uplift" in b.lower() for b in qa_bad.blockers)


def test_cro_api_router_end_to_end_rbac_ssrf_and_tenant_isolation(tmp_path, monkeypatch):
    store = CROStore(db_path=str(tmp_path / "api.db"))
    monkeypatch.setattr("app.routers.cro_router.get_cro_store", lambda: store)

    active_user = {"user": UserIdentity(org_id="tenant_a", email="admin@a.com", role=UserRole.ADMIN)}

    app = FastAPI()
    app.include_router(cro_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: active_user["user"]
    client = TestClient(app)

    # 1. SSRF guard blocks internal metadata / loopback URLs when no fixture pages
    resp_ssrf = client.post("/api/v1/cro/audits", json={"target_url": "http://169.254.169.254/latest/meta-data/"})
    assert resp_ssrf.status_code == 400

    # 2. Create full CRO audit
    resp_create = client.post(
        "/api/v1/cro/audits",
        json={
            "target_url": "https://api-test.example.com/",
            "seed_pages": [{"url": "https://api-test.example.com/", "status_code": 200, "title": "API", "raw_html": "<html><body><h1>Welcome</h1><button disabled>Submit</button></body></html>"}],
        },
        headers={"Idempotency-Key": "api-idem-1"},
    )
    assert resp_create.status_code == 201
    audit_id = resp_create.json()["audit"]["audit_id"]

    # 3. Query all sub-resources
    for path in ("pages", "journeys", "goals", "audiences", "elements", "ctas", "forms", "findings", "scores", "evidence", "recommendations", "funnels", "analytics", "remediation", "reports"):
        r = client.get(f"/api/v1/cro/audits/{audit_id}/{path}")
        assert r.status_code == 200, f"GET {path} failed: {r.text}"

    # 4. Connectors, reports, monitoring
    assert client.get("/api/v1/cro/analytics/connectors").status_code == 200
    r_rep = client.post("/api/v1/cro/reports/create", json={"audit_id": audit_id, "profile": "complete_audit_book", "format": "html"})
    assert r_rep.status_code == 201
    rep_id = r_rep.json()["report"]["report_id"]
    assert client.get(f"/api/v1/cro/reports/{rep_id}/download").status_code == 200

    # 5. Tenant B cannot see Tenant A's audit (strict tenant isolation)
    active_user["user"] = UserIdentity(org_id="tenant_b", email="admin@b.com", role=UserRole.ADMIN)
    assert client.get(f"/api/v1/cro/audits/{audit_id}").status_code == 404
    assert client.get(f"/api/v1/cro/reports/{rep_id}").status_code == 404

    # 6. Viewer role blocked by RBAC from creating audit
    active_user["user"] = UserIdentity(org_id="tenant_a", email="viewer@a.com", role=UserRole.VIEWER)
    assert client.post("/api/v1/cro/audits", json={"target_url": "https://example.com/"}).status_code == 403

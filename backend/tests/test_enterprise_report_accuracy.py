"""Regression tests for enterprise report accuracy, zero-fabrication, and gate integrity."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.domain.models import (
    Category,
    CategoryScore,
    CrawlManifest,
    ExecutiveReport,
    Finding,
    OverallScoreResult,
    PageEvidence,
    Severity,
)
from app.reporting.contracts.subphase_contract import ConfidenceLevel
from app.reporting.engines.report_registry import ReportRegistry
from app.reporting.engines.subphase_report_builder import SubPhaseReportBuilder
from app.reporting.storage.report_storage import ReportStorage
from app.reports.adaptive_audit_book import render_adaptive_audit_book_html
from app.reports.deck.adjudication import BlackboardAdjudicationAuditor
from app.reports.deck.math_engine import DeterministicMetricEngine
from app.reports.roadmap import RoadmapBuilder
from app.reports.validation_gate import ValidationGate
from app.aeo.reporting.exports import (
    generate_aeo_evidence_ledger_csv,
    generate_aeo_live_benchmark_csv,
)
from app.aeo.reporting.generator import CompleteAeoReportGenerator
from app.geo.reporting.geo_report_generator import CompleteGeoReportGenerator
from app.seo.reporting.seo_chapter_visuals import (
    _intent_bars,
    _remediation_velocity_bars,
    _security_header_bars,
)


def _minimal_report(**overrides) -> ExecutiveReport:
    base = dict(
        report_id="rep_test_001",
        analysis_id="ana_test_001",
        org_id="org_test_001",
        domain="acme-test.example",
        website_url="https://acme-test.example",
        story_summary="Test executive summary.",
        primary_strategic_opportunity="Resolve verified technical gaps.",
        consultant_advice_what_to_ignore="Defer low-impact cosmetic tweaks.",
        scores=OverallScoreResult(
            overall_score=80.0,
            grade="B",
            health_label="Calibrated",
            category_scores={
                "TECHNICAL_SEO": CategoryScore(
                    category=Category.TECHNICAL_SEO,
                    score=80.0,
                    weight=1.0,
                    weighted_score=80.0,
                    status="MEASURED",
                ),
                "GEO": CategoryScore(
                    category=Category.GEO,
                    score=None,
                    weight=0.0,
                    weighted_score=0.0,
                    status="NOT_MEASURED",
                ),
            },
        ),
        findings=[],
        page_reports=[],
        crawl_manifest=CrawlManifest(
            domain="acme-test.example",
            website_url="https://acme-test.example",
            pages=[],
        ),
    )
    base.update(overrides)
    return ExecutiveReport(**base)


def test_subphase_builder_honest_confidence_and_evidence():
    p1_2 = SubPhaseReportBuilder.build_p1_2_crawler(
        run_id="r1", website_url="https://acme.test", pages_crawled=0, manifest_data={}
    )
    assert p1_2.confidence == ConfidenceLevel.UNMEASURED
    ev_ids = {e.evidence_id for e in p1_2.evidence_tokens}
    for f in p1_2.findings:
        assert set(f.evidence_ids).issubset(ev_ids)

    p1_5 = SubPhaseReportBuilder.build_p1_5_telemetry(
        run_id="r1", website_url="https://acme.test", telemetry_data={"security_headers": {}}
    )
    assert p1_5.next_phase_handoff["transport_secure"] is False

    p2_4 = SubPhaseReportBuilder.build_p2_4_identity_arbitration(
        run_id="r1", arbitration_data={"conflicts": ["Conflict A", "Conflict B"]}
    )
    assert [f.finding_id for f in p2_4.findings] == ["IDENTITY_CONFLICT_1", "IDENTITY_CONFLICT_2"]
    assert any(e.evidence_id == "brand_arbitration" for e in p2_4.evidence_tokens)


def test_report_registry_scan_reads_actual_json(tmp_path: Path):
    storage = ReportStorage(base_dir=str(tmp_path))
    contract = SubPhaseReportBuilder.build_p1_2_crawler(
        run_id="run_scan_1", website_url="https://acme.test", pages_crawled=0, manifest_data={}
    )
    storage.save_subphase_json(contract)

    registry = ReportRegistry(storage=storage)
    catalog = registry.get_catalog("run_scan_1")
    assert catalog["total_subphase_reports"] == 1
    entry = catalog["subphases"][0]
    assert entry["status"] == "FAILED"
    assert entry["confidence"] == "UNMEASURED"
    assert entry["findings_count"] == 1
    assert entry["content_hash"] == contract.content_hash


def test_validation_gate_not_measured_and_repair_math():
    report = _minimal_report()
    report.scores.category_scores["GEO"].score = 55.0  # invalid: NOT_MEASURED with numeric score
    qg = ValidationGate.evaluate_quality_gates(report)
    assert qg["gates"]["gate_09_score_eligibility"]["status"] == "FAIL"

    repaired, _ = ValidationGate.repair_report(report)
    assert repaired.scores.category_scores["GEO"].score is None
    assert repaired.scores.overall_score == 80.0


def test_roadmap_top_10_does_not_fabricate_when_no_findings():
    plan = RoadmapBuilder().build_top_10_actions(findings=[])
    assert plan.actions == []
    assert plan.total_engineer_hours == 0


def test_seo_visuals_no_fabricated_headers_intent_or_velocity():
    book = SimpleNamespace(
        pages=[
            SimpleNamespace(response_headers={"content-type": "text/html"}),
            SimpleNamespace(response_headers={"content-type": "text/html"}),
        ],
        findings=[],
    )
    sec_bars = _security_header_bars(book)
    assert dict(sec_bars)["HSTS Configured"] == 0.0
    assert _intent_bars(book) == []
    vel = dict(_remediation_velocity_bars(book))
    assert vel["P2 (Sprint Backlog)"] == 0.0
    assert vel["P3 (Hygiene & Monitor)"] == 0.0


def test_geo_and_aeo_reports_do_not_fabricate_metrics():
    report = _minimal_report()
    geo_html = CompleteGeoReportGenerator().render_html_report(report)
    assert "84.2%" not in geo_html
    assert "<td>0.78</td>" not in geo_html
    assert "Engages Queried" not in geo_html

    aeo_json = CompleteAeoReportGenerator().render_json_report(report)
    assert "kpis" in aeo_json
    assert "answer_readiness_score" in aeo_json["kpis"]

    ledger_csv = generate_aeo_evidence_ledger_csv(
        _minimal_report(
            page_reports=[{"url": "https://acme-test.example/", "status_code": 200}]
        )
    )
    assert "sha256-00000001" not in ledger_csv

    bench_csv = generate_aeo_live_benchmark_csv(report)
    assert "Live test response captured" not in bench_csv


def test_adaptive_audit_book_no_fake_cro_or_100pct_on_empty_crawl():
    report = _minimal_report()
    html_out = render_adaptive_audit_book_html(report)
    assert "82% Score" not in html_out
    assert "SOC2 Type II, ISO 27001, GDPR" not in html_out
    assert "Demo Request / Contact" not in html_out
    assert "NOT MEASURED/100 (Grade D)" not in html_out
    assert "100% Valid (200 OK)" not in html_out


def test_deck_math_and_adjudication_honest_on_empty_data():
    report = _minimal_report()
    bundle = DeterministicMetricEngine().compute_bundle(report)
    assert bundle.metrics["potential_gain"].value == 0.0
    assert bundle.metrics["ttfb_median"].formatted_value == "Unmeasured"
    assert bundle.metrics["geo_citability"].formatted_value == "Unmeasured"

    report_with_finding = _minimal_report(
        findings=[
            Finding(
                finding_id="f1",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title="Missing robots.txt directive",
                finding="Missing robots.txt",
                description="robots.txt returned 404.",
                recommended_action="Add robots.txt",
                impact_explanation="Improves crawl guidance.",
                effort=3,
            )
        ]
    )
    adj = BlackboardAdjudicationAuditor().audit_report(report_with_finding)
    assert adj.evidence_token_inventory == []
    assert adj.adjudicated_findings[0].evidence_tokens == []


def test_canonical_grading_consistency_across_all_surfaces():
    from app.domain.scoring.displayed_score import grade_for_displayed, rating_for_displayed
    from app.geo.per_engine_evaluator import _grade_from_score
    from app.orchestration.public_grader import _grade_letter

    expected = [
        (95, "A+", "Exceptional"),
        (88, "A", "Excellent"),
        (78, "B", "Good"),
        (68, "C", "Moderate"),
        (55, "D", "Needs Attention"),
        (30, "F", "Low readiness"),
    ]
    for score, exp_grade, exp_label in expected:
        assert grade_for_displayed(score) == exp_grade
        assert rating_for_displayed(score) == (exp_grade, exp_label)
        assert DeterministicMetricEngine._grade_for_score(float(score)) == exp_grade
        assert _grade_from_score(float(score)) == exp_grade
        pg_grade, pg_label, _ = _grade_letter(score)
        assert pg_grade == exp_grade
        assert pg_label == exp_label

    assert rating_for_displayed(None) == ("—", "Unmeasured")
    assert _grade_letter(None)[:2] == (None, "Not measured")


def test_perfora_ttfb_outlier_aware_summary():
    from app.domain.scoring.displayed_score import compute_ttfb_summary

    summary = compute_ttfb_summary([287.5, 36207.9, 248.5])
    assert summary["sample_size"] == 3
    assert summary["min_ms"] == 248.5
    assert summary["max_ms"] == 36207.9
    assert summary["median_ms"] == 287.5
    assert summary["mean_ms"] == 12248.0
    assert summary["outliers_ms"] == [36207.9]
    assert summary["outlier_count"] == 1
    assert summary["trimmed_mean_ms"] == 268.0


def test_finding_root_cause_sanitization_partial_coverage_and_developer_ticket():
    from app.domain.enums import FindingStatus
    from app.domain.models import FindingEvidence
    from app.report_finding_registry import summarize_finding_severities

    f = Finding(
        finding_id="TECH-PERF-004",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        impact=9,
        title="Missing Product Schema Offer Fields",
        description="Product schema lacks priceValidUntil and shippingDetails.",
        affected_urls=[
            "https://perforacare.com/",
            "https://perforacare.com/products/electric-toothbrush",
            "https://perforacare.com/products/water-flosser",
            "https://perforacare.com/products/probiotic-mouthwash",
        ],
        evidence=[
            FindingEvidence(
                evidence_id="ev_001",
                type="DOM",
                url="https://perforacare.com/products/electric-toothbrush",
                snippet='{"@type":"Product","name":"Electric Toothbrush"}',
                selector_or_header="script[type='application/ld+json']",
            )
        ],
        root_cause="Template markup or HTTP configuration omission on page.",
        recommendation="Add Offer fields to snippets/product-schema.liquid.",
    )

    # 1. Generic unproven root-cause is automatically sanitized to explicit diagnostic gap
    assert "Root cause not confirmed" in f.root_cause
    assert f.root_cause_status == "diagnostic_gap"

    # 2. Multi-URL finding with 1 evidence record is automatically marked SAMPLE_VERIFIED with limitation disclosure
    assert f.scope == "SAMPLE_VERIFIED"
    assert "Sample verified on 1 of 4 affected URLs" in (f.limitations or "")

    # 3. Separated business_impact_level vs technical severity
    assert f.business_impact_level == "HIGH"
    assert f.severity == Severity.HIGH

    # 4. 11-part consulting diagnostic & Jira/Linear/Markdown export
    ticket = f.to_developer_ticket()
    assert len(ticket["sections"]) == 11
    assert "01_what_was_found" in ticket["sections"]
    assert "09_retest_procedure" in ticket["sections"]
    assert ticket["jira_payload"]["issuetype"]["name"] == "Bug"
    assert ticket["linear_payload"]["priority"] == 2
    assert len(ticket["qa_checklist"]) >= 2

    # 5. Canonical severity summary deduplicates and reconciles
    sev_summary = summarize_finding_severities([f, f])
    assert sev_summary["total"] == 1
    assert sev_summary["HIGH"] == 1
    assert sev_summary["high_or_critical"] == 1

    # 6. All 10 lifecycle states exist on FindingStatus
    for state_name in (
        "OPEN", "TRIAGED", "APPROVED", "IN_PROGRESS", "READY_FOR_RETEST",
        "VERIFIED_FIXED", "RETEST_FAILED", "REOPENED", "ACCEPTED_RISK", "WONT_FIX",
    ):
        assert hasattr(FindingStatus, state_name)


def test_enterprise_contract_api_endpoints():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routes.audits.enterprise_contract import router as enterprise_router
    from app.domain.models import AnalysisRun, FindingEvidence
    from app.identity.deps import get_current_user
    from app.identity.authorizer import UserIdentity
    from app.orchestration.orchestrator import orchestrator

    app = FastAPI()
    app.include_router(enterprise_router, prefix="/api/v1")
    fake_user = UserIdentity(
        user_id="u_test_1",
        email="auditor@dristik.ai",
        org_id="org_test_001",
        role="system_admin",
        is_system=True,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user

    finding = Finding(
        finding_id="FIND-ENT-001",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        impact=8,
        title="Missing HSTS Header",
        description="Strict-Transport-Security header is absent.",
        affected_urls=["https://acme-test.example/", "https://acme-test.example/pricing"],
        evidence=[
            FindingEvidence(
                evidence_id="ev_hsts_1",
                type="HTTP_HEADER",
                url="https://acme-test.example/",
                snippet="HTTP/1.1 200 OK",
                selector_or_header="strict-transport-security",
            )
        ],
        recommendation="Add Strict-Transport-Security header.",
    )
    rep = _minimal_report(
        findings=[finding],
        crawl_manifest=CrawlManifest(
            domain="acme-test.example",
            website_url="https://acme-test.example",
            discovered_urls=["https://acme-test.example/", "https://acme-test.example/pricing"],
            pages=[
                PageEvidence(
                    url="https://acme-test.example/",
                    status_code=200,
                    title="Acme Home",
                    ttfb_ms=287.5,
                )
            ],
        ),
    )
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    run = AnalysisRun(
        analysis_id="ana_ent_001",
        org_id="org_test_001",
        website_url="https://acme-test.example",
        status="completed",
        progress_percentage=100,
        created_at=now,
        updated_at=now,
        report=rep,
    )
    orchestrator.runs["ana_ent_001"] = run

    try:
        client = TestClient(app)

        # 1. Canonical Audit Record
        r_audit = client.get("/api/v1/audits/ana_ent_001")
        assert r_audit.status_code == 200
        data_audit = r_audit.json()
        assert data_audit["audit_id"] == "ana_ent_001"
        assert data_audit["finding_counts"]["HIGH"] == 1
        assert data_audit["ttfb_summary"]["median_ms"] == 287.5

        # 2. Coverage Panel (7 sources)
        r_cov = client.get("/api/v1/audits/ana_ent_001/coverage")
        assert r_cov.status_code == 200
        data_cov = r_cov.json()
        assert data_cov["sampling_status"] == "SAMPLED_AUDIT"
        assert len(data_cov["sources"]) == 7

        # 3. Evidence Manifest
        r_ev = client.get("/api/v1/audits/ana_ent_001/evidence")
        assert r_ev.status_code == 200
        assert r_ev.json()["total_evidence_records"] == 1

        # 4. Canonical Findings Registry
        r_find = client.get("/api/v1/audits/ana_ent_001/findings")
        assert r_find.status_code == 200
        assert r_find.json()["severity_counts"]["total"] == 1
        assert r_find.json()["findings"][0]["scope"] == "SAMPLE_VERIFIED"

        # 5. 5-Pillar Scorecard (AEO is NOT_TESTED when 0 queries ran)
        r_sc = client.get("/api/v1/audits/ana_ent_001/scorecard")
        assert r_sc.status_code == 200
        pillars_by_name = {p["pillar"]: p for p in r_sc.json()["pillars"]}
        assert pillars_by_name["AEO"]["status"] == "NOT_TESTED"
        assert pillars_by_name["AEO"]["score"] is None
        assert pillars_by_name["Competitive"]["status"] == "NOT_CONFIGURED"

        # 6. Audit Comparison
        r_cmp = client.get("/api/v1/audits/ana_ent_001/comparison")
        assert r_cmp.status_code == 200
        assert r_cmp.json()["summary"]["NEW_ISSUE"] == 1

        # 7. Deliverables Manifest
        r_rep = client.post("/api/v1/audits/ana_ent_001/reports")
        assert r_rep.status_code == 200
        assert r_rep.json()["deliverables"]["developer_ticket_pack_count"] == 1

        # 8. Finding Lifecycle: Assign & Block Direct VERIFIED_FIXED without Retest
        r_bad = client.post("/api/v1/findings/FIND-ENT-001/assign", json={"status": "VERIFIED_FIXED"})
        assert r_bad.status_code == 400

        r_assign = client.post(
            "/api/v1/findings/FIND-ENT-001/assign",
            json={"owner": "Platform Team", "status": "READY_FOR_RETEST"},
        )
        assert r_assign.status_code == 200
        assert r_assign.json()["status"] == "READY_FOR_RETEST"

        # 9. Finding Retest: Fail -> RETEST_FAILED, Pass -> VERIFIED_FIXED
        r_retest_fail = client.post(
            "/api/v1/findings/FIND-ENT-001/retest",
            json={"passed": False, "observed_after": "Header still missing"},
        )
        assert r_retest_fail.status_code == 200
        assert r_retest_fail.json()["status"] == "RETEST_FAILED"

        r_retest_pass = client.post(
            "/api/v1/findings/FIND-ENT-001/retest",
            json={"passed": True, "observed_after": "strict-transport-security: max-age=31536000"},
        )
        assert r_retest_pass.status_code == 200
        assert r_retest_pass.json()["status"] == "VERIFIED_FIXED"

        # 10. 3-Stage Pre-Publication Validation Gate
        r_val = client.get("/api/v1/reports/ana_ent_001/validation")
        assert r_val.status_code == 200
        assert "gate_1_data_integrity" in r_val.json()["three_stage_gates"]
        assert "gate_2_analytical_completeness" in r_val.json()["three_stage_gates"]
        assert "gate_3_publication_quality" in r_val.json()["three_stage_gates"]
    finally:
        orchestrator.runs.pop("ana_ent_001", None)


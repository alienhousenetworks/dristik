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

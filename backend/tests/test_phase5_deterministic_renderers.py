import pytest
from app.domain.models import (
    ExecutiveReport,
    Finding,
    OverallScoreResult,
    CategoryScore,
    CroAuditReport,
    PublicationStatus,
)
from app.domain.enums import Category, Severity
from app.seo.reporting.seo_report_generator import CompleteSeoReportGenerator
from app.cro.reporting import CroReportGenerator
from app.cro.engine import build_cro_intelligence
from app.reports.adaptive_audit_book import build_adaptive_publication_document
from app.reports.deck.coordinator import DeckOrchestrator

def _build_test_report():
    f1 = Finding(
        finding_id="F_CANON_01",
        title="Missing OpenGraph image tag",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        affected_urls=["https://perforacare.com/"],
        recommendation="Add og:image meta tag to hero section.",
    )
    scores = OverallScoreResult(
        overall_score=75.2,
        grade="B",
        health_label="Good",
        website_geo_readiness_score=66.5,
        observed_ai_visibility_score=12.0,
        aeo_readiness_score=78.0,
    )
    return ExecutiveReport(
        org_id="test_org",
        report_id="RUN_AF865F8B",
        analysis_id="RUN_AF865F8B",
        audit_id="RUN_AF865F8B",
        domain="perforacare.com",
        website_url="https://perforacare.com",
        generated_at="2026-10-15T12:00:00Z",
        scores=scores,
        story_summary="Perfora audit demonstrating unified deterministic rendering.",
        primary_strategic_opportunity="Optimize AI extractability and catalog indexing.",
        consultant_advice_what_to_ignore="Ignore minor low-impact keywords.",
        findings=[f1],
        cro_audit=CroAuditReport(),
        publication_status=PublicationStatus.INTERNAL_REVIEW,
    )

def test_phase5_deterministic_renderers_run_id_and_score_reconciliation():
    """Verify that all report renderers consume the same canonical audit_run_id and scores."""
    report = _build_test_report()
    expected_run_id = "RUN_AF865F8B"
    expected_score = 75.2

    # 1. SEO deliverable
    seo_gen = CompleteSeoReportGenerator()
    seo_data = seo_gen.render_json_report(report)
    assert seo_data["report_id"] == expected_run_id

    # 2. CRO deliverable
    cro_gen = CroReportGenerator()
    cro_intel = build_cro_intelligence(pages=[])
    cro_json = cro_gen.render_json_report(
        cro_intel,
        domain=report.domain,
        website_url=report.website_url,
        analysis_id=report.report_id,
        findings=[f.model_dump() for f in report.findings],
    )
    assert cro_json["analysis_id"] == expected_run_id
    assert len(cro_json["findings"]) == len(report.findings)

    # 3. Master audit book deliverable
    doc = build_adaptive_publication_document(report, report_type="COMPLETE")
    assert doc.metadata.domain == "perforacare.com"
    assert doc.metadata.overall_score == expected_score

    # 4. Executive deck deliverable
    deck_orchestrator = DeckOrchestrator()
    deck = deck_orchestrator.build_blueprint(report)
    assert deck.domain == "perforacare.com"
    assert len(deck.slides) > 0

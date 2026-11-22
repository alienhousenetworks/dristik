"""Phase 6 tests: Unified authoritative scorecard across JSON/HTML/PDF renderers
and durable SQLite persistence + lossless checkpoint restart restoration.
"""
import pytest

from app.db.repository import AuditRepository
from app.domain.enums import AnalysisStage, Category, Severity
from app.domain.evidence.models import Evidence
from app.domain.models import (
    AnalysisRun,
    BusinessProfile,
    ExecutiveReport,
    Finding,
    HonestScores,
    OverallScoreResult,
    PageEvidence,
    PageSection,
)
from app.domain.scoring.displayed_score import displayed_composite
from app.seo.reporting.seo_print_report import SeoPrintReportRenderer
from app.seo.reporting.seo_report_generator import CompleteSeoReportGenerator


def test_durable_save_run_and_lossless_page_and_evidence_restore(tmp_path):
    db_file = str(tmp_path / "phase6_persist.db")
    repo = AuditRepository(db_path=db_file)

    run = AnalysisRun(
        analysis_id="run_phase6_001",
        org_id="org_acme",
        workspace_id="ws_main",
        website_url="https://acme.example/",
        status=AnalysisStage.COMPLETED,
        progress_percentage=100,
        created_at="2026-11-22T12:00:00+00:00",
        updated_at="2026-11-22T12:05:00+00:00",
    )
    finding = Finding(
        finding_id="find_p6_01",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Missing canonical link tag",
        description="No canonical link on homepage.",
        affected_urls=["https://acme.example/"],
        recommendation="Add self-referencing canonical tag.",
    )
    # Must succeed cleanly without sqlite3.IntegrityError on audits.created_at
    repo.save_run(run, findings=[finding])
    loaded_run = repo.get_run("run_phase6_001")
    assert loaded_run is not None
    assert loaded_run["domain"] == "acme.example"

    # Persist rich Phase-1 page and verify get_persisted_crawl_pages restores full structure
    page = PageEvidence(
        url="https://acme.example/",
        title="Acme Cloud",
        h1=["Deploy Faster"],
        word_count=310,
        status_code=200,
        body_text="Deploy Faster with automated Kubernetes rollbacks and SOC 2 compliance.",
        ctas=["Start Free Trial", "Book Demo"],
        footer_info={"emails": ["hello@acme.example"], "legal_links": ["/privacy"]},
        render_status="ok",
        sections=[
            PageSection(
                section_id="sec_0",
                order=0,
                section_role="hero",
                heading_text="Deploy Faster",
                heading_level="h1",
                body_text="Automated Kubernetes rollbacks.",
                word_count=4,
                ctas=["Start Free Trial"],
            )
        ],
    )
    repo.persist_crawl_pages("run_phase6_001", [page])
    restored_pages = repo.get_persisted_crawl_pages("run_phase6_001")
    assert len(restored_pages) == 1
    assert restored_pages[0].body_text == page.body_text
    assert restored_pages[0].render_status == "ok"
    assert len(restored_pages[0].sections) == 1
    assert restored_pages[0].sections[0].section_id == "sec_0"
    assert restored_pages[0].footer_info["emails"] == ["hello@acme.example"]

    # Persist evidence with 64-hex SHA-256 and >500-char text, verify lossless restore
    long_text = "Verified section passage. " * 60
    digest = "f" * 64
    ev = Evidence(
        id="ev_p6_01",
        source_type="page_section",
        analyzer="crawler",
        url="https://acme.example/",
        selector="section#sec_0",
        text=long_text,
        hash=digest,
        content_sha256=digest,
    )
    repo.persist_evidence_items("run_phase6_001", [ev])
    restored_ev = repo.get_persisted_evidence_items("run_phase6_001")
    assert len(restored_ev) == 1
    assert restored_ev[0].content_sha256 == digest
    assert len(restored_ev[0].text or "") > 1000


def test_unified_scorecard_consistent_across_json_html_and_print_renderers():
    report = ExecutiveReport(
        report_id="rep_p6",
        analysis_id="run_p6",
        org_id="org_acme",
        website_url="https://acme.example/",
        domain="acme.example",
        generated_at="2026-11-22",
        business_profile=BusinessProfile(business_name="Acme Cloud", industry="B2B SaaS"),
        scores=OverallScoreResult(overall_score=58.0, grade="D"),
        honest_scores=HonestScores(
            human_score=72.0,
            google_score=68.0,
            ai_readiness_score=64.0,
            ai_visibility_score=None,
        ),
        story_summary="Grounded summary.",
        primary_strategic_opportunity="Expand structured answers.",
        consultant_advice_what_to_ignore="Low-impact vanity checks.",
        findings=[],
    )

    canonical = displayed_composite(report)
    assert canonical is not None

    gen = CompleteSeoReportGenerator()
    json_rep = gen.render_json_report(report)
    html_rep = gen.render_html_report(report)
    print_sec1 = SeoPrintReportRenderer()._render_sec_01(report)

    assert json_rep["health_score"] == canonical
    assert json_rep["sections"]["01_executive_summary"]["overall_score"] == canonical
    assert f"{int(round(canonical))}" in html_rep
    assert f"{int(round(canonical))}" in print_sec1

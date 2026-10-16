"""
Sprint 1 (Phase 1) Verification Tests:
Evidence-to-finding traceability, 6-state status model, zero cross-wiring, and deterministic scoring.
"""
import pytest
from app.domain.enums import DiagnosticStatus, Severity, Category, BusinessIntent
from app.domain.models import (
    PageEvidence,
    Finding,
    FindingEvidence,
    ExecutiveReport,
    CrawlManifest,
    DiagnosticCoverageMatrix,
    CrawlInventory,
    AuditScopeInfo,
    BusinessProfile,
    OverallScoreResult,
    CategoryScore,
    ThreeWayComparison,
    HonestScores,
)
from app.evidence.store import EvidenceStore
from app.analyzers.media_asset_analyzer import MediaAssetAnalyzer
from app.analyzers.canonical_auditor import CanonicalAuditor
from app.analyzers.heading_analyzer import HeadingAnalyzer
from app.audit.diagnostic_inventory import DiagnosticInventoryEngine
from app.reports.validation_gate import ValidationGate
from app.scoring.engine import ScoringEngine


def _make_dummy_report(findings=None, manifest=None):
    findings = findings or []
    bp = BusinessProfile(
        primary_intent=BusinessIntent.LEAD_GENERATION,
        business_type="B2B Technology",
        target_geos=["Global"],
        industry="SaaS",
        canonical_entity_name="Example Corp",
        legal_name="Example Corporation Inc.",
        brand_name="Example",
        value_proposition="Cloud Analytics Platform",
        target_audience="Enterprise Developers",
        business_model="Subscription SaaS",
    )
    scores = OverallScoreResult(
        overall_score=85.0,
        grade="A",
        health_label="Excellent",
        category_scores={
            "ON_PAGE_SEO": CategoryScore(
                category=Category.ON_PAGE_SEO,
                score=85.0,
                weight=100.0,
                weighted_score=85.0,
                summary="On-page evaluation",
            )
        },
        intent_adjusted_weights={"ON_PAGE_SEO": 100.0},
    )
    return ExecutiveReport(
        report_id="rep_test_accuracy",
        analysis_id="run_test_accuracy",
        website_url="https://example.com",
        domain="example.com",
        generated_at="October 16, 2026 - 12:00 UTC",
        business_profile=bp,
        scores=scores,
        story_summary="Sampled audit of 1 representative page out of 3 discovered for example.com.",
        primary_strategic_opportunity="Optimize structured entity markup.",
        consultant_advice_what_to_ignore="Ignore vanity metrics.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear identity",
            search_engine_perspective="Indexable",
            ai_answer_engine_perspective="Structured",
        ),
        honest_scores=HonestScores(
            human_score=85,
            google_score=85,
            ai_citation_score=85,
            score_band="Citation Ready",
        ),
        crawl_manifest=manifest,
        findings=findings,
    )


def test_media_asset_analyzer_traceability_and_no_cross_wiring():
    """Verify media asset analyzer produces traceable alt findings and does NOT cross-wire with CLS."""
    html_content = """
    <html>
      <body>
        <img src="/images/banner.webp" width="800" height="400">
        <img src="/images/icon-decorative.svg" role="presentation">
        <img src="/images/product-clean.webp" alt="Dristik Analytics Dashboard" width="600" height="300">
      </body>
    </html>
    """
    page = PageEvidence(
        url="https://example.com/products",
        status_code=200,
        raw_html=html_content,
    )

    report = MediaAssetAnalyzer.analyze_media([page])

    assert len(report.missing_alt_images) == 1
    missing = report.missing_alt_images[0]
    assert missing["img_src"] == "/images/banner.webp"
    assert missing["image_role"] == "informative"

    findings = MediaAssetAnalyzer.generate_findings(report)
    alt_findings = [f for f in findings if f.finding_id == "finding_missing_image_alt"]
    assert len(alt_findings) == 1
    f_alt = alt_findings[0]

    # Verify evidence traceability
    assert len(f_alt.evidence) >= 1
    ev = f_alt.evidence[0]
    assert ev.evidence_id.startswith("EV-IMG-ALT-")
    assert ev.url == "https://example.com/products"
    assert ev.element == "img"
    assert "banner.webp" in ev.snippet
    assert ev.observed_value == "/images/banner.webp"
    assert "must declare a non-empty alt attribute" in ev.expected_condition
    assert ev.test_method == "crawl_html_dom"
    assert ev.response_status == 200
    assert ev.is_decorative is False
    assert ev.image_role == "informative"

    # Verify NO cross-wiring with CLS
    assert "cls_risk" not in ev.evidence_id
    assert "layout shift" not in (ev.description or "").lower()


def test_canonical_auditor_traceability():
    """Verify canonical auditor produces deterministic evidence with expected conditions."""
    page_missing = PageEvidence(
        url="https://example.com/orphan-article",
        status_code=200,
        raw_html="<html><head><title>Orphan</title></head><body><h1>Content</h1></body></html>",
    )
    auditor = CanonicalAuditor()
    rollup, findings = auditor.audit([page_missing])

    missing_findings = [f for f in findings if f.finding_id == "finding_missing_canonicals"]
    assert len(missing_findings) == 1
    f = missing_findings[0]
    assert len(f.evidence) >= 1
    ev = f.evidence[0]
    assert ev.evidence_id.startswith("EV-CAN-MISS-")
    assert ev.url == "https://example.com/orphan-article"
    assert "No canonical tag declared" in ev.observed_value
    assert "Page must specify an absolute, self-referencing" in ev.expected_condition
    assert ev.test_method == "crawl_html_head"


def test_heading_analyzer_traceability():
    """Verify heading analyzer generates deterministic evidence for missing H1 and hierarchy skips."""
    page = PageEvidence(
        url="https://example.com/services",
        status_code=200,
        h1=[],
        h2=["Subheading without H1"],
        h3=["Skipped H3"],
    )
    analyzer = HeadingAnalyzer()
    rollup = analyzer.analyze([page])
    findings = analyzer.generate_findings(rollup)

    h1_findings = [f for f in findings if f.finding_id == "finding_heading_missing_h1"]
    assert len(h1_findings) == 1
    ev = h1_findings[0].evidence[0]
    assert ev.evidence_id.startswith("EV-HDG-MISS-")
    assert "Zero <h1> elements found" in ev.observed_value
    assert "Page must define exactly one primary <h1> heading" in ev.expected_condition
    assert ev.test_method == "crawl_html_headings"


def test_diagnostic_inventory_6_state_model():
    """Verify that DiagnosticInventoryEngine produces only controlled 6-state statuses."""
    manifest = CrawlManifest(
        run_id="run_test_matrix",
        domain="example.com",
        discovered_urls=["https://example.com/", "https://example.com/about", "https://example.com/services"],
        pages=[PageEvidence(url="https://example.com/", status_code=200)],
        crawl_inventory=CrawlInventory(discovered_total=3, tested_pages=1, url_coverage_pct=33.3),
        sampling_status="SAMPLED_AUDIT",
    )
    report = _make_dummy_report(manifest=manifest)

    matrix = DiagnosticInventoryEngine.build_inventory(report, manifest=manifest)
    valid_statuses = {s.value for s in DiagnosticStatus}

    # Verify all records conform to the 6-state status model
    for record in matrix.records:
        assert record.status in valid_statuses, f"Diagnostic {record.diagnostic_id} has invalid status {record.status}"

    # Because crawl was sampled (1/3), page-level clean tests should be SAMPLED, not PASSED
    sampled_records = [r for r in matrix.records if r.status == DiagnosticStatus.SAMPLED.value]
    assert len(sampled_records) > 0, "Expected at least one SAMPLED status for sampled crawl"

    # Verify coverage calculations
    assert matrix.inspection_coverage_pct > 0
    assert matrix.audit_health_score >= 0


def test_validation_gate_flags_and_cleans_cross_wired_evidence():
    """Verify ValidationGate catches cross-wired alt text evidence and cleans it."""
    cross_wired_ev = FindingEvidence(
        evidence_id="ev_cls_bogus_1",
        url="https://example.com/banner.webp",
        description="Missing width/height attribute causes layout shift risk (CLS)",
        observed_value="Missing width/height",
        expected_condition="Explicit width/height",
    )
    legit_alt_ev = FindingEvidence(
        evidence_id="ev_img_alt_legit_1",
        url="https://example.com/hero.webp",
        description="On '/services/', image 'hero.webp' has an empty alt attribute.",
        element="<img src='/hero.webp'>",
        observed_value="Missing alt attribute",
        expected_condition="Descriptive alt text",
    )

    finding = Finding(
        finding_id="finding_missing_image_alt",
        title="Missing Image Alt Attributes",
        finding="Images lack descriptive alt text",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        evidence=[cross_wired_ev, legit_alt_ev],
        evidence_ids=["ev_cls_bogus_1", "ev_img_alt_legit_1"],
    )

    report = _make_dummy_report(findings=[finding])

    # 1. ValidationGate must flag the cross-wired evidence
    val_res = ValidationGate.validate_report(report)
    assert not val_res.is_valid
    assert "zero_cross_wired_evidence" in val_res.failed_checks

    # 2. Repair report must purge the cross-wired CLS evidence and keep the legitimate alt evidence
    repaired_report, repairs = ValidationGate.repair_report(report)
    repaired_f = repaired_report.findings[0]
    assert len(repaired_f.evidence) == 1
    assert repaired_f.evidence[0].evidence_id == "ev_img_alt_legit_1"

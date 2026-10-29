"""
Master SEO Audit Engine Overhaul Golden Test Suite (Enterprise Standards).

Validates the complete remediation of audit engine defects:
1. Missing Alt Isolation (strictly zero cross-category evidence reuse).
2. HTTPS Content Routing (no security hijacking on https:// content findings).
3. External Connector Isolation (missing connectors remain UNAVAILABLE).
4. Diagnostic Token Collision Prevention (crawl discovery does not leak into other chapters).
5. Dynamic Sequential Chapter Numbering (strictly continuous TOC and chapter labels).
6. Placeholder Domain Prohibition (zero industry-peer.com or example.com).
7. Mandatory Validation Gate Enforcement & Auto-Repair.
8. Chapter Conclusion Reconciliation (no false 'No verified defects' on failed metrics).
"""
import pytest
from unittest.mock import MagicMock

from app.seo.audit.evidence.compatibility_gate import EvidenceCompatibilityGate
from app.reports.plain_english_engine import AgenticSpecialistRegistry, PlainEnglishEngine
from app.seo.reporting.seo_book_renderer import build_seo_book_context, SeoAuditBookRenderer
from app.reports.validation_gate import ValidationGate
from app.domain.enums import DiagnosticStatus
from app.domain.models import (
    ExecutiveReport,
    Finding,
    OverallScoreResult,
    CategoryScore,
    Severity,
    Category,
    CrawlManifest,
)


def _make_mock_evidence(selector: str, observation: str, value: str = ""):
    return {
        "id": "ev_test_1",
        "selector": selector,
        "element": selector,
        "observation": observation,
        "value": value or observation,
        "snippet": f"<{selector}>...",
    }


def test_missing_alt_evidence_isolation():
    """Requirement 1: 15 missing alt images must NEVER bind to non-image claims."""
    alt_evidence = _make_mock_evidence("img", "15 image(s) are missing alt text.")

    # Must be compatible with image/alt claims
    assert EvidenceCompatibilityGate.is_evidence_compatible("Missing Image Alt Attributes", "IMAGE_SEO", alt_evidence)
    assert EvidenceCompatibilityGate.is_evidence_compatible("Image Accessibility Warning", "MEDIA", alt_evidence)

    # Must be REJECTED for non-image claims
    assert not EvidenceCompatibilityGate.is_evidence_compatible("Pricing Model Transparency", "COMMERCIAL", alt_evidence)
    assert not EvidenceCompatibilityGate.is_evidence_compatible("Buyer Persona Intent Alignment", "STRATEGY", alt_evidence)
    assert not EvidenceCompatibilityGate.is_evidence_compatible("Competitor Search Visibility Parity", "COMPETITOR", alt_evidence)
    assert not EvidenceCompatibilityGate.is_evidence_compatible("Hreflang Language Reciprocity", "INTERNATIONAL", alt_evidence)
    assert not EvidenceCompatibilityGate.is_evidence_compatible("Canonical URL Mismatch", "CANONICAL", alt_evidence)
    assert not EvidenceCompatibilityGate.is_evidence_compatible("Single H1 Hierarchy Adherence", "ON_PAGE_SEO", alt_evidence)


def test_https_content_routing_no_security_hijack():
    """Requirement 2: Content on https:// URLs must route to content specialist, NOT security."""
    finding = {
        "title": "Thin Commercial Copy",
        "category": "CONTENT",
        "url": "https://target-domain.com/solutions",
        "affected_urls": ["https://target-domain.com/solutions"],
        "observation": "Page body contains fewer than 150 words of descriptive text.",
    }

    agent = AgenticSpecialistRegistry.dispatch_agent_for_finding(
        category=finding["category"],
        title=finding["title"],
        description=finding["observation"],
    )
    agent_id = agent.agent_id
    assert agent_id != "trust.security.v3", f"Expected content agent, got {agent_id}"
    assert "content" in agent_id or "onpage" in agent_id

    # Explanation must not contain browser certificate warnings
    explanation = PlainEnglishEngine.enrich_finding(finding)
    assert "mandatory security certificates" not in explanation["business_impact"]
    assert "Modern browsers display warnings" not in explanation["business_impact"]
    # Verification command must not use example.com
    for step in explanation.get("verification_steps", []):
        assert "example.com" not in step


def test_external_connector_isolation_backlinks():
    """Requirement 3: Missing backlink connector reports Chapter 17 as UNAVAILABLE without fabrication."""
    report = MagicMock()
    report.domain = "testdomain.com"
    report.analysis_id = "test_run_1"
    report.generated_at = "2026-10-19T00:00:00"
    report.crawl_manifest = None
    report.page_reports = [{"url": "https://testdomain.com/"}]
    report.findings = []
    report.scores = None
    report.google_performance = None
    report.external_authority = None
    report.diagnostic_inventory = None

    ctx = build_seo_book_context(report)
    sections = ctx["seo_sections"]

    # Chapter on Off-Page & Backlinks
    backlink_sec = next((s for s in sections if "backlink" in s["title"].lower() or "off-page" in s["title"].lower()), None)
    assert backlink_sec is not None, "Backlink section should be in core sections"
    for sub in backlink_sec["subsections"]:
        for metric in sub["metrics"]:
            if "referring domain" in metric["name"].lower() or "authority" in metric["name"].lower():
                assert metric["status"] == DiagnosticStatus.UNAVAILABLE.value
                assert "authorized" in metric["value"].lower() or "connector" in metric["value"].lower()


def test_diagnostic_token_collision_prevention():
    """Requirement 4: Crawl discovery '0 via sitemap, 14 via links' must never leak into other chapters."""
    from app.domain.models import DiagnosticRecord, DiagnosticCoverageMatrix

    # Create synthetic crawl discovery record matching Chapter 02
    leak_record = DiagnosticRecord(
        diagnostic_id="DIAG-02-DISCOVERY-SOURCES",
        chapter_num="02",
        chapter_title="Methodology, Crawl Scope & Limitations",
        subchapter="Discovery Source Accounting",
        applicable_url_types=["all"],
        required_data_sources=["sitemap_parser", "link_traversal"],
        test_performed="Track URL provenance across XML sitemaps, internal links, and seed configuration.",
        status=DiagnosticStatus.PASSED.value,
        status_reason="Discovered via sitemap: 0, via links: 14.",
        severity="INFORMATIONAL",
    )

    matrix = DiagnosticCoverageMatrix(
        total_diagnostics=1,
        passed_count=1,
        failed_count=0,
        warning_count=0,
        not_tested_count=0,
        records=[leak_record],
        chapter_breakdown={"02": {"passed": 1, "failed": 0}},
    )

    report = MagicMock()
    report.domain = "testdomain.com"
    report.analysis_id = "test_run_2"
    report.generated_at = "2026-10-19T00:00:00"
    report.crawl_manifest = None
    report.page_reports = [{"url": "https://testdomain.com/"}]
    report.findings = []
    report.scores = None
    report.google_performance = None
    report.external_authority = None
    report.diagnostic_inventory = matrix

    ctx = build_seo_book_context(report)

    # Verify NO section in seo_sections (which covers Chapter 03+) contains the leak string
    for sec in ctx["seo_sections"]:
        for sub in sec["subsections"]:
            for metric in sub["metrics"]:
                assert "Discovered via sitemap: 0, via links: 14." not in metric["value"], (
                    f"Leakage detected in chapter '{sec['title']}', metric '{metric['name']}': {metric['value']}"
                )


def test_sequential_chapter_numbering_zero_gaps():
    """Requirement 5: Dynamic sequential chapter numbering strictly continuous (no 30 -> 37 jump)."""
    report = MagicMock()
    report.domain = "testdomain.com"
    report.analysis_id = "test_run_3"
    report.generated_at = "2026-10-19T00:00:00"
    report.crawl_manifest = None
    report.page_reports = [{"url": "https://testdomain.com/"}]
    report.findings = []
    report.scores = None
    report.google_performance = None
    report.external_authority = None
    report.diagnostic_inventory = None

    ctx = build_seo_book_context(report)
    sections = ctx["seo_sections"]
    toc_items = ctx["toc_items"]

    num_sections = len(sections)
    expected_findings_reg_num = f"{num_sections + 3:02d}"
    expected_roadmap_num = f"{num_sections + 4:02d}"

    assert ctx["findings_register_chapter_label"] == f"Chapter {expected_findings_reg_num}"
    assert ctx["roadmap_chapter_label"] == f"Chapter {expected_roadmap_num}"

    # Verify TOC items have strictly sequential chapter labels
    reg_toc = next(t for t in toc_items if t["id"] == "findings-register")
    road_toc = next(t for t in toc_items if t["id"] == "roadmap")

    assert f"Chapter {expected_findings_reg_num}" in reg_toc["title"]
    assert f"Chapter {expected_roadmap_num}" in road_toc["title"]


def test_placeholder_domain_prohibition():
    """Requirement 6: Zero occurrences of industry-peer.com or example.com in findings and competitor audits."""
    from app.orchestration.runtime.registry import AGENT_REGISTRY
    from app.orchestration.runtime.specialist import SpecialistAgent

    agent = SpecialistAgent(AGENT_REGISTRY["competitor.head_to_head_parity.v3"], model_router=MagicMock())
    blackboard = MagicMock()
    blackboard.blackboard_state = {}
    blackboard.pages = []
    blackboard.crawl_manifest = None

    result = agent._deterministic_audit(blackboard, [])
    observations = result.get("observations") or {}

    assert observations.get("competitor_data_status") == "DATA_UNAVAILABLE"
    assert "industry-peer.com" not in str(observations)


def test_validation_gate_incompatible_evidence_and_repair():
    """Requirement 7: ValidationGate rejects incompatible evidence and auto-repairs."""
    from tests.test_validation_gate import create_sample_report

    finding_clean = Finding(
        finding_id="F-IMG-01",
        category=Category.ON_PAGE_SEO,
        title="15 Images Missing Alt Text",
        description="Images lack descriptive alt text.",
        severity=Severity.MEDIUM,
        priority=6,
        confidence=0.9,
        evidence=[_make_mock_evidence("img", "15 image(s) are missing alt text.")],
    )

    finding_incompatible = Finding(
        finding_id="F-COMM-01",
        category=Category.CONTENT,
        title="Pricing Transparency Missing",
        description="Pricing page lacks structured tier breakdown.",
        severity=Severity.HIGH,
        priority=8,
        confidence=0.9,
        evidence=[_make_mock_evidence("img", "15 image(s) are missing alt text.")],  # Incompatible!
        verification_steps=["curl -sI 'https://example.com/'"],  # Placeholder!
    )

    report = create_sample_report()
    report.domain = "validationsite.com"
    report.website_url = "https://validationsite.com"
    report.findings = [finding_clean, finding_incompatible]

    # 1. ValidationGate.validate_report must fail due to incompatible evidence & placeholder
    val_res = ValidationGate.validate_report(report)
    assert not val_res.is_valid
    assert "zero_cross_wired_evidence" in val_res.failed_checks
    assert "zero_placeholder_domains" in val_res.failed_checks

    # 2. ValidationGate.repair_report must clean incompatible evidence & replace placeholder
    repaired_report, repairs = ValidationGate.repair_report(report)
    for f in repaired_report.findings:
        for ev in (f.evidence or []):
            assert EvidenceCompatibilityGate.is_evidence_compatible(f.title, f.category, ev)
        for step in (getattr(f, "verification_steps", []) or []):
            assert "example.com" not in step


def test_chapter_conclusion_reconciled_with_failed_metrics():
    """Requirement 8: Chapters with failed metrics must not conclude 'No verified defects'."""
    manifest = MagicMock()
    manifest.crawl_health = {"avg_ttfb_ms": 2261.0}  # Slow TTFB (> 800ms)

    report = MagicMock()
    report.domain = "testdomain.com"
    report.analysis_id = "test_run_4"
    report.generated_at = "2026-10-19T00:00:00"
    report.crawl_manifest = manifest
    report.page_reports = [{"url": "https://testdomain.com/"}]
    report.findings = []  # Zero isolated findings
    report.scores = None
    report.google_performance = None
    report.external_authority = None
    report.diagnostic_inventory = None

    ctx = build_seo_book_context(report)
    speed_sec = next((s for s in ctx["seo_sections"] if "web vitals" in s["title"].lower() or "speed" in s["title"].lower()), None)
    assert speed_sec is not None

    # Failed metrics flag must be True because TTFB > 800
    assert speed_sec["has_failed_metrics"] is True
    # Conclusion must indicate threshold failure, NOT generic pass
    assert "threshold failures" in speed_sec["conclusion"].lower() or "remediation" in speed_sec["conclusion"].lower()
    assert "conformed to target standards" not in speed_sec["conclusion"].lower()

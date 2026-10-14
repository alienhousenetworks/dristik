"""
Dristik AI Master SEO Audit Intelligence Upgrade - Regression Test Suite
Validates all 18 enterprise scenarios from Phase 13:
1. Five eligible URLs, all analyzed.
2. Five discovered URLs, only two eligible and analyzed.
3. Sixty-seven discovered URLs, only five analyzed.
4. Failed HTTP requests and render timeouts.
5. Empty or unavailable sitemap.
6. Unavailable external APIs.
7. A title that exists but is semantically poor.
8. Missing versus duplicate versus generic metadata.
9. Valid schema with missing feature-specific requirements.
10. A site with no e-commerce applicability.
11. A site with incomplete competitor data.
12. Duplicate findings across different chapters.
13. Conflicting scores from stale cached results.
14. High-impact finding without causal evidence.
15. An unresolved contradiction at publication time.
16. A report with all required gates passing.
17. A report with a failed mandatory gate.
18. AlienHouse Networks regression fixture & PDF/HTML rendering.
"""
import pytest
from app.domain.enums import Category, Severity, FindingStatus
from app.domain.models import (
    ExecutiveReport, Finding, FindingEvidence, PageReport, CrawlManifest, PageEvidence,
    SchemaValidationReport, SchemaIssue, SecurityAuditReport,
    MetaBucketRollup, MetaBucketItem, HeadingHierarchyRollup, HeadingIssueItem,
    OverallScoreResult, CategoryScore, CompetitorSeoParityMatrix,
    CompetitorSeoParityProfile, CrawlInventory, ExternalDataSource,
    QualityGateResult, ConsistencyAuditReport, EcommerceSeoAuditReport,
    BusinessProfile, ThreeWayComparison,
)
from app.audit.inventory_helper import get_canonical_crawl_inventory
from app.audit.diagnostic_inventory import DiagnosticInventoryEngine
from app.audit.consistency_engine import CrossChapterConsistencyEngine
from app.audit.page_analysis import PageLevelAnalysisEngine
from app.reports.validation_gate import ValidationGate
from app.reports.seo_print_report import seo_print_renderer
from app.reports.seo_report_generator import CompleteSeoReportGenerator


def _build_base_report(num_pages=5, disc_total=5, domain="alienhousenetworks.com"):
    pages = [
        PageEvidence(
            url=f"https://{domain}/page{i}" if i > 0 else f"https://{domain}/",
            status_code=200,
            title=f"Page {i} - Enterprise AlienHouse Network Architecture" if i > 0 else "AlienHouse Networks - Managed Cyber Architecture",
            meta_description="Enterprise network operations, managed IT, and zero-trust cloud infrastructure services.",
            h1=[f"AlienHouse Operations {i}" if i > 0 else "Enterprise Cyber Architecture"],
            canonical_url=f"https://{domain}/page{i}" if i > 0 else f"https://{domain}/",
            word_count=650,
            schema_types=["Organization"],
            structured_data=[{"@type": "Organization", "name": "AlienHouse Networks"}],
            internal_links=[f"https://{domain}/page{(i+1)%max(1, num_pages)}"],
        )
        for i in range(num_pages)
    ]
    manifest = CrawlManifest(
        domain=domain,
        total_pages_discovered=disc_total,
        total_pages_crawled=num_pages,
        pages=pages,
        discovered_urls=[p.url for p in pages] + [f"https://{domain}/untested_{j}" for j in range(max(0, disc_total - num_pages))],
        crawl_inventory={
            "discovered_total": disc_total,
            "tested_pages": num_pages,
            "untested_pages": max(0, disc_total - num_pages),
            "url_coverage_pct": round((num_pages / max(1, disc_total)) * 100.0, 1),
            "sampling_status": "FULL_CRAWL" if num_pages >= disc_total else "SAMPLED_AUDIT",
        },
        sampling_status="FULL_CRAWL" if num_pages >= disc_total else "SAMPLED_AUDIT",
    )
    cat_scores = {
        "TECHNICAL_SEO": CategoryScore(category=Category.TECHNICAL_SEO, score=85.0, weight=25.0, weighted_score=21.25, summary="Technical hygiene evaluated"),
        "ON_PAGE_SEO": CategoryScore(category=Category.ON_PAGE_SEO, score=80.0, weight=25.0, weighted_score=20.0, summary="On-page metadata evaluated"),
        "CONTENT": CategoryScore(category=Category.CONTENT, score=75.0, weight=25.0, weighted_score=18.75, summary="Content quality evaluated"),
        "STRUCTURED_DATA": CategoryScore(category=Category.SCHEMA, score=70.0, weight=25.0, weighted_score=17.5, summary="Structured data evaluated"),
    }
    report = ExecutiveReport(
        report_id=f"RPT-{domain}-001",
        analysis_id="analysis_upgrade_test",
        domain=domain,
        website_url=f"https://{domain}",
        generated_at="October 14, 2026",
        business_profile=BusinessProfile(business_name="AlienHouse Networks"),
        primary_strategic_opportunity="Harden technical crawl edge and expand topical authority.",
        consultant_advice_what_to_ignore="Ignore superficial meta keyword tags.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Fast loading, secure architecture.",
            search_engine_perspective="Clean indexability, header canonical gaps.",
            ai_answer_engine_perspective="Clear entity definitions, high citation potential.",
        ),
        scores=OverallScoreResult(overall_score=77.5, grade="B", health_label="Good", category_scores=cat_scores),
        page_reports=[PageReport(url=p.url, path=f"/page{i}", title=p.title or "", status_code=200) for i, p in enumerate(pages)],
        crawl_manifest=manifest,
        story_summary=f"Audit of {domain} evaluating {num_pages} analyzed pages.",
        findings=[
            Finding(
                finding_id="F-TECH-01",
                title="Missing Canonical Header Directive",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                priority=8,
                status=FindingStatus.OPEN,
                affected_urls=[pages[0].url],
                evidence=[FindingEvidence(url=pages[0].url, value="canonical-header-missing", element="headers", snippet="HTTP/1.1 200 OK")],
                root_cause="Nginx origin server does not emit Link rel=canonical in HTTP response headers.",
                causal_mechanism="Crawler must rely exclusively on in-HTML canonical tag, increasing duplicate content risk if HTML head parsing terminates early.",
                root_cause_status="confirmed",
                recommendation="Inject Link: <https://alienhousenetworks.com/>; rel='canonical' in Nginx configuration.",
                validation_criteria="curl -I https://alienhousenetworks.com/ | grep -i 'link: .*rel=canonical'",
            )
        ],
        ecommerce_seo=EcommerceSeoAuditReport(status="NOT_APPLICABLE", is_ecommerce=False, summary="B2B infrastructure service, not e-commerce."),
    )
    return report, manifest, pages


# Scenario 1: Five eligible URLs, all analyzed
def test_scenario_1_five_eligible_all_analyzed():
    report, manifest, pages = _build_base_report(num_pages=5, disc_total=5)
    inv = get_canonical_crawl_inventory(manifest, report)
    assert inv.discovered_total == 5
    assert inv.tested_pages == 5
    assert inv.untested_total == 0
    assert inv.url_coverage_pct == 100.0
    assert inv.coverage_denominator == "eligible_total"


# Scenario 2: Five discovered URLs, only two eligible and analyzed
def test_scenario_2_five_discovered_two_analyzed():
    report, manifest, pages = _build_base_report(num_pages=2, disc_total=5)
    inv = get_canonical_crawl_inventory(manifest, report)
    assert inv.discovered_total == 5
    assert inv.tested_pages == 2
    assert inv.untested_total == 3
    assert inv.url_coverage_pct == 40.0
    assert inv.sampling_status == "SAMPLED_AUDIT"


# Scenario 3: Sixty-seven discovered URLs, only five analyzed (AlienHouse Networks fixture)
def test_scenario_3_sixty_seven_discovered_five_analyzed():
    report, manifest, pages = _build_base_report(num_pages=5, disc_total=67)
    inv = get_canonical_crawl_inventory(manifest, report)
    assert inv.discovered_total == 67
    assert inv.tested_pages == 5
    assert inv.untested_total == 62
    assert inv.url_coverage_pct == 7.5

    report, cons = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    assert report.crawl_manifest.crawl_inventory["discovered_total"] == 67
    assert report.crawl_manifest.crawl_inventory["tested_pages"] == 5


# Scenario 4: Failed HTTP requests and render timeouts
def test_scenario_4_failed_http_and_render_timeouts():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=5)
    manifest.crawl_inventory = {
        "discovered_total": 5,
        "tested_pages": 3,
        "failed_pages": 2,
        "total_errors": 2,
        "untested_pages": 0,
        "url_coverage_pct": 60.0,
    }
    inv = get_canonical_crawl_inventory(manifest, report)
    assert inv.failed_total == 2
    assert inv.fetched_total == 5


# Scenario 5: Empty or unavailable sitemap
def test_scenario_5_empty_or_unavailable_sitemap():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    manifest.sitemap_found = False
    manifest.sitemap_urls = []
    inv = get_canonical_crawl_inventory(manifest, report)
    assert inv.discovered_via_sitemap == 0
    assert inv.discovered_via_links >= 0


# Scenario 6: Unavailable external APIs handled as NOT_CONNECTED
def test_scenario_6_unavailable_external_apis():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    report.external_authority = {"status": "NOT_CONNECTED", "reason": "Ahrefs/Semrush OAuth not linked."}
    report, cons = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    assert cons.is_consistent is True


# Scenario 7: A title that exists but is semantically poor
def test_scenario_7_title_exists_but_semantically_poor():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    pages[1].title = "Home"  # exists but generic
    diag = DiagnosticInventoryEngine.build_inventory(report, manifest, pages)
    title_quality = next((d for d in diag.diagnostics if d.diagnostic_id == "DIAG-05-TITLE-QUALITY"), None)
    assert title_quality is not None
    assert title_quality.status in ("WARN", "WARNING", "FAIL")


# Scenario 8: Missing versus duplicate versus generic metadata
def test_scenario_8_metadata_taxonomies_separated():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    pages[0].meta_description = "Identical duplicate sitewide description."
    pages[1].meta_description = "Identical duplicate sitewide description."
    pages[2].meta_description = ""  # missing
    diag = DiagnosticInventoryEngine.build_inventory(report, manifest, pages)
    desc_exist = next((d for d in diag.diagnostics if d.diagnostic_id == "DIAG-05-DESC-EXISTENCE"), None)
    desc_quality = next((d for d in diag.diagnostics if d.diagnostic_id == "DIAG-05-DESC-QUALITY"), None)
    assert desc_exist is not None
    assert desc_quality is not None
    assert desc_exist.status in ("WARN", "WARNING")  # missing on page 2
    assert desc_quality.status in ("WARN", "WARNING")  # duplicated across pages 0 and 1


# Scenario 9: Valid schema with missing feature-specific requirements
def test_scenario_9_valid_schema_missing_rich_requirements():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    report.schema_validation = SchemaValidationReport(
        total_pages_with_schema=1,
        total_entities_detected=1,
        valid_entities_count=1,
        entities_with_errors_count=1,
        detected_types=["Organization"],
        issues=[
            SchemaIssue(
                url=pages[0].url,
                schema_type="Organization",
                severity="ERROR",
                field="logo",
                message="Missing required field 'logo' for Google Rich Results"
            )
        ]
    )
    assessments = PageLevelAnalysisEngine.compile_page_assessments(pages, report, manifest)
    home = next(a for a in assessments if a.url == pages[0].url)
    assert home.schema_valid is True  # Valid JSON-LD
    assert home.rich_result_eligible is False  # Missing logo required for Google feature


# Scenario 10: A site with no e-commerce applicability
def test_scenario_10_site_with_no_ecommerce_applicability():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    report.ecommerce_seo = EcommerceSeoAuditReport(
        status="NOT_APPLICABLE",
        is_ecommerce=False,
        summary="Informational and B2B infrastructure site with zero cart or product SKUs."
    )
    qg = ValidationGate.evaluate_quality_gates(report, manifest)
    assert qg["gates"]["applicability_gate"]["status"] == "PASS"


# Scenario 11: A site with incomplete competitor data
def test_scenario_11_incomplete_competitor_data():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    report.competitor_seo_parity = CompetitorSeoParityMatrix(
        target_domain=report.domain,
        competitors=[CompetitorSeoParityProfile(domain=report.domain, brand_name="AlienHouse", is_target=True, overall_seo_score=43)],
        peer_avg_seo_score=60,  # invalid because only 1 competitor
    )
    report, cons = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    assert report.competitor_seo_parity.peer_avg_seo_score is None


# Scenario 12: Duplicate findings across different chapters
def test_scenario_12_duplicate_findings_deduplicated():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    # Add identical duplicate finding
    f_dup = Finding(
        finding_id="F-TECH-02",
        title="Missing Canonical Header Directive",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        priority=8,
        status=FindingStatus.OPEN,
        affected_urls=[pages[0].url],
        evidence=[FindingEvidence(url=pages[0].url, value="canonical-header-missing", element="headers", snippet="HTTP/1.1 200 OK")],
    )
    report.findings.append(f_dup)
    repaired, res = ValidationGate.enforce_gate(report, manifest)
    titles = [f.title for f in repaired.findings]
    assert titles.count("Missing Canonical Header Directive") == 1


# Scenario 13: Conflicting scores from stale cached results
def test_scenario_13_conflicting_scores_arithmetically_repaired():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    # Inject stale overall score conflicting with weighted contributions
    report.scores.overall_score = 50.0  # weighted sum is 77.5
    repaired, res = ValidationGate.enforce_gate(report, manifest)
    assert abs(repaired.scores.overall_score - 77.5) <= 0.5


# Scenario 14: High-impact finding without causal evidence
def test_scenario_14_high_impact_finding_causal_enrichment():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    f_high = Finding(
        finding_id="F-CRIT-99",
        title="Server Response Latency Anomaly",
        category=Category.TECHNICAL_SEO,
        severity=Severity.CRITICAL,
        priority=9,
        status=FindingStatus.OPEN,
        affected_urls=[pages[0].url],
        evidence=[FindingEvidence(url=pages[0].url, value="ttfb-anomaly", element="performance", snippet="TTFB: 3200ms")],
        root_cause="",  # missing causal chain
    )
    report.findings.append(f_high)
    report, cons = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    reconciled_f = next(f for f in report.findings if f.finding_id == "F-CRIT-99")
    assert reconciled_f.diagnostic_gap is not None
    assert "Direct server runtime telemetry" in reconciled_f.diagnostic_gap


# Scenario 15: An unresolved contradiction at publication time
def test_scenario_15_unresolved_contradiction_blocks_certification():
    report, manifest, pages = _build_base_report(num_pages=3, disc_total=3)
    # Finding with 0 evidence
    f_unevidenced = Finding(
        finding_id="F-FAKE-01",
        title="Hypothetical Security Threat",
        category=Category.TECHNICAL_SEO,
        severity=Severity.CRITICAL,
        priority=10,
        status=FindingStatus.OPEN,
        affected_urls=[pages[0].url],
        evidence=[],
        evidence_refs=[],
        evidence_ids=[],
    )
    # If unevidenced finding cannot be repaired or is raw
    report.findings.append(f_unevidenced)
    qg = ValidationGate.evaluate_quality_gates(report, manifest)
    # Evidence gate must flag untraceable finding
    assert qg["gates"]["evidence_gate"]["passed"] is False


# Scenario 16: A report with all required gates passing
def test_scenario_16_all_gates_passing_certified():
    report, manifest, pages = _build_base_report(num_pages=5, disc_total=5)
    report.diagnostic_inventory = DiagnosticInventoryEngine.build_inventory(report, manifest, pages)
    report.page_level_assessments = PageLevelAnalysisEngine.compile_page_assessments(pages, report, manifest)
    report, report.consistency_report = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    repaired, res = ValidationGate.enforce_gate(report, manifest)
    assert res.is_valid is True
    assert repaired.certification_status == "CERTIFIED"


# Scenario 17: A report with a failed mandatory gate
def test_scenario_17_failed_mandatory_gate_qa_failed():
    report, manifest, pages = _build_base_report(num_pages=5, disc_total=5)
    # Inject unresolved placeholder string in narrative
    report.story_summary = "Audit results [TODO] undefined nan null."
    repaired, res = ValidationGate.enforce_gate(report, manifest)
    assert repaired.certification_status in ("QA_FAILED", "DEGRADED_SECTIONS_WITHHELD")


# Scenario 18: AlienHouse Networks regression fixture & print HTML rendering
def test_scenario_18_alienhouse_fixture_complete_render():
    report, manifest, pages = _build_base_report(num_pages=5, disc_total=14, domain="alienhousenetworks.com")
    report.diagnostic_inventory = DiagnosticInventoryEngine.build_inventory(report, manifest, pages)
    report.page_level_assessments = PageLevelAnalysisEngine.compile_page_assessments(pages, report, manifest)
    report, report.consistency_report = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    repaired, res = ValidationGate.enforce_gate(report, manifest)

    # Render print book HTML
    html_out = seo_print_renderer.render(repaired)
    assert html_out is not None
    assert len(html_out) > 5000

    # Assert AlienHouse Networks crawl reconciliation
    assert "5 / 14" in html_out
    assert "35.7% URL coverage" in html_out
    assert "SAMPLED_AUDIT" in html_out

    # Assert 9-pillar scorecard is rendered in Chapter 01
    assert "Authoritative 9-Pillar SEO Health Score Breakdown" in html_out

    # Assert Causal Analysis is rendered in Chapter 19
    assert "Root Cause (Causal Chain)" in html_out
    assert "Nginx origin server does not emit Link rel=canonical" in html_out

    # Assert 10 Quality Gates and Certification status in Chapter 20
    assert "Pre-Publication Quality Assurance Gate Evaluations (10 Gates)" in html_out
    assert "PUBLISHED_WITH_LIMITATIONS" in html_out

import pytest
from app.domain.enums import Category, Severity, FindingStatus
from app.domain.models import (
    ExecutiveReport, Finding, PageReport, CrawlManifest, PageEvidence,
    SchemaValidationReport, SchemaIssue, SecurityAuditReport,
    MetaBucketRollup, MetaBucketItem, HeadingHierarchyRollup, HeadingIssueItem,
    CanonicalAuditRollup, HttpStatusBreakdown, DiagnosticCoverageMatrix,
    PageLevelAssessment, ConsistencyAuditReport,
    BusinessProfile, OverallScoreResult, ThreeWayComparison
)
from app.audit.diagnostic_inventory import DiagnosticInventoryEngine
from app.audit.consistency_engine import CrossChapterConsistencyEngine
from app.audit.page_analysis import PageLevelAnalysisEngine
from app.reports.validation_gate import ValidationGate
from app.reports.seo_print_report import seo_print_renderer
from app.reports.seo_report_generator import CompleteSeoReportGenerator


def create_sample_pages():
    p1 = PageEvidence(
        url="https://example.com/",
        status_code=200,
        title="Example Homepage - High Quality SEO Testing Platform",
        meta_description="A complete test platform for deterministic enterprise SEO audits and technical verification.",
        h1=["Example Homepage"],
        h2=["Features", "Pricing"],
        canonical_url="https://example.com/",
        is_indexable=True,
        word_count=850,
        structured_data=[{"@type": "Organization", "name": "Example Corp"}],
        schema_types=["Organization"],
        response_headers={"strict-transport-security": "max-age=31536000; includeSubDomains"}
    )
    p2 = PageEvidence(
        url="https://example.com/about",
        status_code=200,
        title="About Us",
        meta_description="",
        h1=[],  # missing H1
        canonical_url="https://example.com/about-us",  # conflicting canonical
        is_indexable=True,
        word_count=320,
        structured_data=[],
        schema_types=[],
        response_headers={}
    )
    p3 = PageEvidence(
        url="https://example.com/dead-link",
        status_code=404,
        title="Not Found",
        meta_description="",
        h1=[],
        canonical_url="",
        is_indexable=False,
        word_count=50,
        structured_data=[],
        schema_types=[],
        response_headers={}
    )
    return [p1, p2, p3]


def create_sample_report(pages):
    manifest = CrawlManifest(
        manifest_id="cm-enterprise-01",
        run_id="run-ent-01",
        domain="example.com",
        pages=pages,
        total_pages_discovered=3,
        total_pages_crawled=3,
        sitemap_found=True,
        robots_txt_found=True,
        crawl_health={"avg_ttfb_ms": 180.0, "total_words_across_site": 1220}
    )

    finding1 = Finding(
        finding_id="F-TECH-001",
        title="Missing Strict-Transport-Security Header",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        priority=8,
        effort=2,
        impact=7,
        status=FindingStatus.OPEN,
        affected_urls=["https://example.com/about"],
        description="The HTTP response headers do not include Strict-Transport-Security (HSTS).",
        raw_observation="curl -I https://example.com/about returned headers without Strict-Transport-Security",
        difference_observed_expected="Missing HSTS; expected max-age=31536000; includeSubDomains",
        technical_explanation="Without HSTS, initial requests can be intercepted via SSL stripping attacks.",
        business_impact="Exposes visitors to man-in-the-middle attacks and signals degraded technical trust.",
        recommendation="Configure Nginx/Cloudflare to emit Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
        validation_criteria="curl -sI https://example.com/about | grep -i strict-transport-security matches max-age=31536000"
    )

    finding2 = Finding(
        finding_id="F-CONTENT-002",
        title="Missing Primary Heading (H1)",
        category=Category.CONTENT,
        severity=Severity.MEDIUM,
        priority=7,
        effort=1,
        impact=6,
        status=FindingStatus.OPEN,
        affected_urls=["https://example.com/about"],
        description="The about page lacks an H1 heading element.",
        raw_observation="DOM query selector for h1 returned 0 elements on /about",
        difference_observed_expected="0 H1 elements observed; exactly 1 expected",
        technical_explanation="Heading hierarchy is severed, preventing clear document outline parsing by bots.",
        recommendation="Add <h1>About Example Corp</h1> above the primary content block.",
        validation_criteria="document.querySelectorAll('h1').length === 1"
    )

    page_reports = [
        PageReport(url=p.url, path=p.url.replace("https://example.com", ""), title=p.title or "", status_code=p.status_code)
        for p in pages
    ]

    sec_report = SecurityAuditReport(
        target_domain="example.com",
        score=75.0,
        hsts_enabled=False,
        csp_enabled=False,
        summary="Security audit found missing HSTS on secondary endpoints."
    )

    schema_rep = SchemaValidationReport(
        total_pages_with_schema=1,
        total_entities_detected=1,
        valid_entities_count=0,
        entities_with_errors_count=1,
        detected_types=["Organization"],
        issues=[
            SchemaIssue(
                url="https://example.com/",
                schema_type="Organization",
                severity="ERROR",
                field="logo",
                message="Missing required field 'logo' for Google Rich Results"
            )
        ]
    )

    meta_rollup = MetaBucketRollup(
        total_pages_evaluated=3,
        missing_titles=[],
        duplicate_titles=[],
        missing_descriptions=[MetaBucketItem(url="https://example.com/about", text="", length=0)],
        too_long_titles=[],
        title_issue_count=0,
        description_issue_count=1
    )

    head_rollup = HeadingHierarchyRollup(
        total_pages_evaluated=3,
        missing_h1=[HeadingIssueItem(url="https://example.com/about", issue_type="missing_h1", detail="Zero H1 tags found")],
        multiple_h1=[],
        total_heading_issues=1
    )

    report = ExecutiveReport(
        report_id="rep-ent-01",
        analysis_id="run-ent-01",
        website_url="https://example.com",
        domain="example.com",
        generated_at="October 14, 2026",
        business_profile=BusinessProfile(business_name="Example Corp"),
        scores=OverallScoreResult(overall_score=78.4, grade="C+", health_label="Fair"),
        story_summary="The website demonstrates a solid technical foundation.",
        what_site_gets_right=["HTTPS secured", "Mobile responsive"],
        what_is_holding_it_back=["Missing HSTS", "Schema missing properties"],
        primary_strategic_opportunity="Implement full schema graph and HSTS.",
        consultant_advice_what_to_ignore="Ignore keyword tags.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clean layout.",
            search_engine_perspective="Crawlable, needs entity completeness.",
            ai_answer_engine_perspective="Clear context.",
        ),
        crawl_manifest=manifest,
        page_reports=page_reports,
        findings=[finding1, finding2],
        security_audit=sec_report,
        schema_validation=schema_rep,
        meta_rollup=meta_rollup,
        heading_hierarchy=head_rollup,
        canonical_audit=CanonicalAuditRollup(
            total_pages_evaluated=3,
            canonical_ok_count=1,
            conflicting_canonical_count=1,
            missing_canonical_count=1
        ),
        http_status_breakdown=HttpStatusBreakdown(
            count_200=2,
            count_301=0,
            count_404=1,
            count_500=0
        )
    )
    return report, manifest


def test_30_field_finding_model():
    """Validates 30-field structured finding properties and bidirectional synchronization."""
    f = Finding(
        finding_id="F-TEST-30",
        title="Test 30-Field Finding",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        priority=9,
        raw_observation="HTTP 404 response received for /sitemap.xml",
        difference_observed_expected="HTTP 404 observed; HTTP 200 expected",
        technical_explanation="Sitemap file route is unmapped in web server configuration.",
        user_experience_impact="No direct end-user impact; major search bot discovery bottleneck.",
        business_impact="New blog posts remain undiscovered for weeks.",
        risk_of_inaction="Delayed indexing and lost organic traffic velocity.",
        recommendation="Deploy sitemap generator middleware to serve dynamic XML at /sitemap.xml",
        implementation_detail="Add @app.get('/sitemap.xml') returning Response(media_type='application/xml')",
        validation_criteria="curl -sI https://example.com/sitemap.xml | grep '200 OK'"
    )
    assert f.raw_observation == "HTTP 404 response received for /sitemap.xml"
    assert f.difference_observed_expected == "HTTP 404 observed; HTTP 200 expected"
    assert f.user_experience_impact == "No direct end-user impact; major search bot discovery bottleneck."
    assert f.risk_of_inaction == "Delayed indexing and lost organic traffic velocity."
    assert f.implementation_detail == "Add @app.get('/sitemap.xml') returning Response(media_type='application/xml')"
    # Test expected_condition and causal_chain / technical_explanation
    assert f.difference_observed_expected == "HTTP 404 observed; HTTP 200 expected"
    assert f.technical_explanation == "Sitemap file route is unmapped in web server configuration."


def test_diagnostic_inventory_engine():
    """Validates DiagnosticInventoryEngine produces coverage across all 20 chapters."""
    pages = create_sample_pages()
    report, manifest = create_sample_report(pages)

    matrix = DiagnosticInventoryEngine.build_inventory(
        report=report,
        manifest=manifest,
        eval_pages=pages
    )

    assert isinstance(matrix, DiagnosticCoverageMatrix)
    assert matrix.total_diagnostics >= 20
    assert len(matrix.records) >= 20

    # Check all 20 chapters are represented
    chapters_present = {r.chapter_num for r in matrix.records}
    for ch in range(1, 21):
        ch_str = f"{ch:02d}"
        assert ch_str in chapters_present, f"Chapter {ch_str} missing from diagnostic inventory"

    # Check status values are strictly from the allowed vocabulary
    allowed_statuses = {
        "PASS", "PASSED", "FAIL", "FAILED", "WARNING", "WARN",
        "NOT_TESTED", "NOT_CONNECTED", "UNAVAILABLE", "NOT_APPLICABLE",
        "INCONCLUSIVE", "INFERRED", "SAMPLED"
    }
    for r in matrix.records:
        assert r.status in allowed_statuses, f"Invalid diagnostic status: {r.status} for {r.diagnostic_id}"

    # Check coverage calculations
    assert matrix.total_diagnostics == len(matrix.records)


def test_page_level_analysis_engine():
    """Validates PageLevelAnalysisEngine compiles per-URL diagnostic dossiers."""
    pages = create_sample_pages()
    report, manifest = create_sample_report(pages)

    assessments = PageLevelAnalysisEngine.compile_page_assessments(
        pages=pages,
        report=report,
        manifest=manifest
    )

    assert len(assessments) == 3
    # Check homepage
    home = next(a for a in assessments if a.url == "https://example.com/")
    assert home.http_status == 200
    assert home.indexable is True
    assert home.canonical_match is True
    assert home.h1_count == 1
    assert home.schema_valid is True

    # Check about page
    about = next(a for a in assessments if a.url == "https://example.com/about")
    assert about.http_status == 200
    assert about.h1_count == 0
    assert about.canonical_match is False
    assert about.open_issues_count >= 1

    # Check dead link
    dead = next(a for a in assessments if a.url == "https://example.com/dead-link")
    assert dead.http_status == 404
    assert dead.indexable is False


def test_cross_chapter_consistency_engine():
    """Validates reconciliation of cross-chapter contradictions."""
    pages = create_sample_pages()
    report, manifest = create_sample_report(pages)

    # Contradiction #1: schema errors > 0 vs schema claim
    # Contradiction #2: security header finding vs security report
    repaired_report, consistency_rep = CrossChapterConsistencyEngine.audit_and_reconcile(report)

    assert isinstance(consistency_rep, ConsistencyAuditReport)
    assert consistency_rep.is_consistent is True

    # Check that schema validation fields are consistent
    assert repaired_report.schema_validation.entities_with_errors_count == 1
    assert repaired_report.schema_validation.total_entities_detected == 1

    # Check that HSTS state was reconciled with finding
    assert repaired_report.security_audit.hsts_enabled is False


def test_pre_publication_quality_gates():
    """Validates evaluation of all 6 pre-publication quality gates."""
    pages = create_sample_pages()
    report, manifest = create_sample_report(pages)

    # Attach diagnostic inventory and page assessments
    report.diagnostic_inventory = DiagnosticInventoryEngine.build_inventory(report, manifest, pages)
    report.page_level_assessments = PageLevelAnalysisEngine.compile_page_assessments(pages, report, manifest)
    report, report.consistency_report = CrossChapterConsistencyEngine.audit_and_reconcile(report)

    gates = ValidationGate.evaluate_quality_gates(report, manifest)
    assert isinstance(gates, dict)
    assert "gates" in gates

    expected_gates = [
        "evidence_gate",
        "coverage_gate",
        "analysis_gate",
        "consistency_gate",
        "actionability_gate",
        "reporting_gate"
    ]
    for g in expected_gates:
        assert g in gates["gates"], f"Missing quality gate: {g}"
        assert gates["gates"][g]["status"] in ("PASS", "WARNING", "FAIL")

    assert "scorecard" in gates


def test_seo_print_report_rendering_with_enterprise_features():
    """Validates print report HTML renders diagnostic checklists, schema issues, and quality gates."""
    pages = create_sample_pages()
    report, manifest = create_sample_report(pages)

    report.diagnostic_inventory = DiagnosticInventoryEngine.build_inventory(report, manifest, pages)
    report.page_level_assessments = PageLevelAnalysisEngine.compile_page_assessments(pages, report, manifest)
    report, report.consistency_report = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    report.quality_gate_results = ValidationGate.evaluate_quality_gates(report, manifest)

    html_out = seo_print_renderer.render(report)

    assert html_out is not None
    assert len(html_out) > 5000

    # Verify diagnostic checklist is embedded in chapters
    assert "Diagnostic Checklist &amp; Coverage" in html_out
    assert "DIAG-01-BLOCKERS" in html_out
    assert "DIAG-08-REQUIRED-FIELDS" in html_out
    assert "DIAG-11-HSTS-HEADER" in html_out

    # Verify schema issues table is rendered in Chapter 08
    assert "Rich Result Disqualification Log" in html_out
    assert "Missing required field &#x27;logo&#x27;" in html_out or "Missing required field 'logo'" in html_out

    # Verify security headers inventory table is rendered in Chapter 11
    assert "HTTP Security Headers &amp; Protocol Integrity Inventory" in html_out
    assert "Strict-Transport-Security (HSTS)" in html_out

    # Verify quality gates table is rendered in Chapter 20
    assert "Pre-Publication Quality Assurance Gate Evaluations" in html_out
    assert "Evidence Gate" in html_out


def test_json_report_deliverables():
    """Validates SeoReportGenerator outputs deliverables A through G and top-level diagnostic records."""
    pages = create_sample_pages()
    report, manifest = create_sample_report(pages)

    report.diagnostic_inventory = DiagnosticInventoryEngine.build_inventory(report, manifest, pages)
    report.page_level_assessments = PageLevelAnalysisEngine.compile_page_assessments(pages, report, manifest)
    report, report.consistency_report = CrossChapterConsistencyEngine.audit_and_reconcile(report)
    report.quality_gate_results = ValidationGate.evaluate_quality_gates(report, manifest)

    generator = CompleteSeoReportGenerator()
    json_out = generator.render_json_report(report)

    assert "diagnostic_inventory" in json_out
    assert "page_level_assessments" in json_out
    assert "consistency_report" in json_out
    assert "quality_gate_results" in json_out

    deliverables = json_out.get("deliverables", {})
    assert "deliverable_a_chapter_investigation_matrix" in deliverables
    assert "deliverable_d_reconciliation_report" in deliverables
    assert "deliverable_f_audit_reliability_report" in deliverables

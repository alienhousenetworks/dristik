"""
Tests for Master SEO Pipeline, Rendering Disparity Engine, 14-Field Findings,
Master 12-Part Report Architecture, and Remediation Verification Rescan Loop.
"""
import pytest
from app.domain.models import (
    Finding,
    PageEvidence,
    ExecutiveReport,
    FindingStatus,
    VerificationStatus,
    EvidenceClass,
    CrawlManifest,
    BusinessProfile,
    OverallScoreResult,
    ThreeWayComparison,
)
from app.domain.enums import Category, Severity
from app.seo.analyzers.rendering_disparity import analyze_rendering_disparity, RenderingDisparityAnalyzer
from app.seo.reporting.seo_report_generator import CompleteSeoReportGenerator
from app.reports.adaptive_audit_book import render_adaptive_audit_book_html
from app.agents.runtime.specialist import SpecialistAgent
from app.agents.runtime.registry import AGENT_REGISTRY
from app.cognition.blackboard import CognitiveBlackboard
from app.verification.verification_loop import verification_loop_service


def test_rendering_disparity_empty_server_shell():
    """Validates that empty raw server shells with client hydration trigger PAGE_VERIFIED findings."""
    raw_html = "<html><head><title>App</title></head><body><div id='root'></div><script src='/app.js'></script></body></html>"
    rendered_dom = "<html><head><title>App</title></head><body><div id='root'><h1>Enterprise Cloud Analytics</h1><p>Our platform automates operational workflows across multi-cloud environments.</p><a href='/pricing'>Pricing</a><a href='/docs'>Documentation</a></div></body></html>"

    report_data, findings = analyze_rendering_disparity(raw_html, rendered_dom, "https://example.com/app")

    assert report_data["has_discrepancy"] is True
    assert report_data["empty_raw_shell"] is True
    assert report_data["raw_word_count"] <= 2
    assert report_data["rendered_word_count"] > 5
    assert len(report_data["client_only_internal_links"]) >= 2
    assert "/pricing" in report_data["client_only_internal_links"] or "https://example.com/pricing" in report_data["client_only_internal_links"]
    assert len(findings) >= 1

    finding = findings[0]
    assert finding.scope_classification == "PAGE_VERIFIED"
    assert finding.severity == Severity.HIGH or finding.severity == Severity.CRITICAL
    assert "Server-Side Rendering" in (finding.recommended_solution or "")
    assert finding.acceptance_criteria is not None
    assert finding.relevant_code_or_configuration_example is not None


def test_rendering_disparity_client_injected_h1():
    """Validates detection of client-injected H1 headings when raw HTML contains body text but no H1."""
    raw_html = "<html><head><title>Blog</title></head><body><div class='content'><p>Welcome to our detailed technical guide on search engine optimization.</p></div></body></html>"
    rendered_dom = "<html><head><title>Blog</title></head><body><div class='content'><h1>Complete Technical SEO Guide</h1><p>Welcome to our detailed technical guide on search engine optimization.</p></div></body></html>"

    report_data, findings = analyze_rendering_disparity(raw_html, rendered_dom, "https://example.com/blog")

    assert report_data["has_discrepancy"] is True
    assert report_data["empty_raw_shell"] is False
    assert report_data["client_injected_h1"] is True
    assert len(findings) >= 1
    h1_finding = [f for f in findings if "Rendering" in f.title or "H1" in f.description][0]
    assert h1_finding.scope_classification == "PAGE_VERIFIED"
    assert "client-side" in h1_finding.root_cause.lower() or "server" in h1_finding.recommended_solution.lower()


def test_rendering_disparity_clean_parity():
    """Validates that SSR or static sites with identical content produce zero discrepancy findings."""
    html_content = "<html><head><title>Home</title></head><body><h1>Welcome</h1><p>Static server content.</p><a href='/about'>About</a></body></html>"
    report_data, findings = analyze_rendering_disparity(html_content, html_content, "https://example.com/")

    assert report_data["has_discrepancy"] is False
    assert report_data.get("empty_raw_shell") is not True
    assert report_data.get("client_injected_h1") is not True
    assert len(findings) == 0


def test_14_field_finding_model_synchronization():
    """Validates that diagnostic finding fields automatically sync bidirectionally with legacy fields."""
    finding = Finding(
        finding_id="F-SEO-001",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        finding_title="Empty Server Shell Detected",
        concise_summary="Raw HTML contains zero textual copy.",
        detailed_diagnosis="Search crawler requests receive an empty <div id='root'> requiring JavaScript execution.",
        business_context="Search engines without immediate JS execution will index an empty page.",
        root_cause="SPA architecture without Server-Side Rendering (SSR).",
        recommended_solution="Enable Server-Side Rendering in Next.js/Nuxt.",
        implementation_steps=["Install SSR middleware", "Deploy Node server runtime", "Verify curl response"],
        acceptance_criteria="curl -s https://example.com/ returns non-empty <h1> and >200 words.",
        verification_method="Automated HTTP GET inspection of raw byte stream.",
        relevant_code_or_configuration_example="export async function getServerSideProps() { ... }",
        scope_classification="PAGE_VERIFIED",
        affected_sample_count=5,
    )

    # Legacy field synchronization check
    assert finding.title == "Empty Server Shell Detected"
    assert finding.description == "Raw HTML contains zero textual copy."
    assert finding.recommendation == "Enable Server-Side Rendering in Next.js/Nuxt."
    assert finding.scope == "PAGE_VERIFIED"
    assert finding.validation_criteria == "curl -s https://example.com/ returns non-empty <h1> and >200 words."
    assert finding.why_it_matters == "Search engines without immediate JS execution will index an empty page."
    assert finding.relevant_code_or_configuration_example is not None


def test_complete_seo_report_generator_html_diagnostic_fields():
    """Validates that CompleteSeoReportGenerator renders the 14-field card, disparity block, and external authority block."""
    f = Finding(
        finding_id="F-TEST-101",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Rendering Hydration Discrepancy",
        finding_title="Rendering Hydration Discrepancy",
        description="Core content rendered purely via client-side JavaScript.",
        detailed_diagnosis="Core content rendered purely via client-side JavaScript.",
        recommendation="Implement SSR or SSG prerendering.",
        recommended_solution="Implement SSR or SSG prerendering.",
        root_cause="Client-side React hydration dependency.",
        implementation_steps=["Configure SSR build", "Validate raw HTML curl"],
        acceptance_criteria="Raw HTTP GET returns complete HTML body.",
        verification_method="HTTP raw socket stream comparison.",
        relevant_code_or_configuration_example="const prerender = true;",
        scope_classification="PAGE_VERIFIED",
        affected_sample_count=3,
        affected_templates=["/product/:id"],
        data_limitations="Evaluated across 10 sampled URLs.",
    )

    manifest_page = PageEvidence(
        url="https://example.com/product/1",
        rendering_discrepancy={"has_discrepancy": True, "empty_raw_shell": True, "client_injected_h1": True},
    )
    manifest = CrawlManifest(
        domain="example.com",
        base_url="https://example.com",
        pages=[manifest_page],
    )

    report = ExecutiveReport(
        report_id="rep-test-001",
        analysis_id="run-test-001",
        domain="example.com",
        website_url="https://example.com",
        generated_at="2026-10-13T12:00:00Z",
        business_profile=BusinessProfile(business_name="Example Corp"),
        scores=OverallScoreResult(overall_score=85.0, grade="B", health_label="Good"),
        story_summary="Example Corp shows strong performance with opportunities in rendering parity.",
        primary_strategic_opportunity="Implement Server-Side Rendering to eliminate client hydration lag.",
        consultant_advice_what_to_ignore="Ignore minor unstyled tag warnings.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Fast experience.",
            search_engine_perspective="Disparity between raw and rendered DOM.",
            ai_answer_engine_perspective="Needs structured entities.",
        ),
        findings=[f],
        crawl_manifest=manifest,
        external_authority={"status": "NOT_CONNECTED", "coverage": {}},
    )

    generator = CompleteSeoReportGenerator()
    html_output = generator.render_html_report(report)

    # 1. 14 Diagnostic Fields rendered in HTML
    assert "F-TEST-101" in html_output
    assert "PAGE_VERIFIED" in html_output
    assert "Root Cause (Causal Chain)" in html_output
    assert "Client-side React hydration dependency." in html_output
    assert "Step-by-Step Remediation Guide" in html_output
    assert "Configure SSR build" in html_output
    assert "Production Code / Configuration Fix" in html_output
    assert "const prerender = true;" in html_output
    assert "Validation Acceptance Test" in html_output
    assert "Raw HTTP GET returns complete HTML body." in html_output
    assert "Verification Method" in html_output
    assert "HTTP raw socket stream comparison." in html_output
    assert "Affected Templates" in html_output
    assert "/product/:id" in html_output

    # 2. Section 03 Rendering Disparity Block
    assert "HYDRATION DISPARITY DETECTED" in html_output
    assert "Raw HTML vs Client Rendered DOM Disparity" in html_output

    # 3. Section 16 External Authority (Zero-Fake NOT_CONNECTED Disclosure)
    assert "NOT_CONNECTED / NOT_MEASURED" in html_output
    assert "Zero-Fake Evidence Governance" in html_output

    # 4. Print / PDF Export Button in Header
    assert "/api/v1/reports/run-test-001/seo-report?format=pdf" in html_output


def test_adaptive_audit_book_html_diagnostic_fields():
    """Validates that the typeset adaptive audit book renders finding cards with scope and acceptance criteria."""
    f = Finding(
        finding_id="F-BOOK-001",
        category=Category.TECHNICAL_SEO,
        severity=Severity.CRITICAL,
        title="Empty Raw Server Response",
        finding_title="Empty Raw Server Response",
        description="Server delivers blank shell div to crawlers.",
        detailed_diagnosis="Server delivers blank shell div to crawlers.",
        recommendation="Implement Server-Side Rendering.",
        root_cause="SPA hydration defect.",
        acceptance_criteria="Server HTTP 200 contains rendered H1 tag.",
        relevant_code_or_configuration_example="next build && next export",
        scope_classification="PAGE_VERIFIED",
    )

    report = ExecutiveReport(
        report_id="rep-book-001",
        analysis_id="run-book-001",
        domain="example.com",
        website_url="https://example.com",
        generated_at="2026-10-13T12:00:00Z",
        business_profile=BusinessProfile(business_name="Example Corp"),
        scores=OverallScoreResult(overall_score=85.0, grade="B", health_label="Good"),
        story_summary="Executive narrative for adaptive book.",
        primary_strategic_opportunity="Eliminate blank shell rendering.",
        consultant_advice_what_to_ignore="Ignore superficial items.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Visitor view.",
            search_engine_perspective="Search bot view.",
            ai_answer_engine_perspective="AI view.",
        ),
        findings=[f],
    )

    html_book = render_adaptive_audit_book_html(report, report_type="SEO")

    assert "F-BOOK-001" in html_book
    assert "PAGE_VERIFIED" in html_book
    assert "ROOT CAUSE:" in html_book
    assert "SPA hydration defect." in html_book
    assert "ACCEPTANCE CRITERIA:" in html_book
    assert "Server HTTP 200 contains rendered H1 tag." in html_book
    assert "next build" in html_book and "next export" in html_book


@pytest.mark.asyncio
async def test_remediation_verification_loop_rescan():
    """Validates that the verification loop deterministically checks findings on live content and returns clean status."""
    finding = Finding(
        finding_id="F-CANONICAL-001",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Missing Self-Referential Canonical Tag",
        finding="No rel=canonical found in DOM.",
        description="Missing canonical link tag.",
        recommendation="Add <link rel='canonical' href='https://example.com/page'>.",
    )

    # 1. Test against HTML containing proper canonical tag -> RESOLVED
    clean_html = "<html><head><title>Page</title><meta name='description' content='Valid descriptive page summary for search engine snippet generation.'><link rel='canonical' href='https://example.com/page'></head><body><h1>Content</h1></body></html>"
    rep_resolved = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="https://example.com/page",
        live_html=clean_html,
        live_status=200,
    )

    assert rep_resolved.status == "RESOLVED"
    assert rep_resolved.stage in ("CERTIFY", "CERTIFIED")
    assert len(rep_resolved.checks) >= 1
    assert all(c.passed for c in rep_resolved.checks)

    # 2. Test against HTML with mismatched canonical tag -> PARTIALLY_RESOLVED or FAILED_RECHECK
    broken_html = "<html><head><title>Page</title><link rel='canonical' href='https://other-domain.com/unrelated'></head><body><h1>Content</h1></body></html>"
    rep_broken = await verification_loop_service.verify_finding(
        finding=finding,
        website_url="https://example.com/page",
        live_html=broken_html,
        live_status=200,
    )

    assert rep_broken.status in ("FAILED_RECHECK", "PARTIALLY_RESOLVED")
    assert any(not c.passed for c in rep_broken.checks)


def test_specialist_agent_rendering_hydration_deterministic():
    """Validates that crawl.rendering_hydration.v3 inspects page rendering discrepancies deterministically."""
    agent_defn = AGENT_REGISTRY.get("crawl.rendering_hydration.v3")
    assert agent_defn is not None

    agent = SpecialistAgent(agent_defn, model_router=None)
    blackboard = CognitiveBlackboard("run-101", "https://example.com")

    # Add a page with rendering disparity
    page = PageEvidence(
        url="https://example.com/spa",
        rendering_discrepancy={
            "has_discrepancy": True,
            "empty_raw_shell": True,
            "client_injected_h1": True,
        },
    )
    blackboard.pages = [page]

    # Run deterministic audit
    res = agent._deterministic_audit(blackboard, [page])

    assert res.get("observations", {}).get("hydration_analysis_mode") == "RAW_VS_RENDERED_DOM"
    assert res.get("observations", {}).get("empty_shells_count") == 1

    # Should register claims
    assert len(blackboard.claims) >= 1
    hydration_claim = [c for c in blackboard.claims if "empty server shell" in c.statement.lower()][0]
    assert hydration_claim.severity == Severity.CRITICAL

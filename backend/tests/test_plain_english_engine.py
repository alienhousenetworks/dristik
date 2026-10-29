"""
Unit & Integration Tests for Dristik Plain-English Explanation Engine.
Verifies plain-English translations, executive business explanations,
11-point finding card rendering, zero-fabrication disclosures, and consistency engine integration.
"""
import pytest
from app.domain.models import (
    BusinessProfile,
    ExecutiveReport,
    Finding,
    OverallScoreResult,
    ThreeWayComparison,
)
from app.reports.plain_english_engine import (
    GLOSSARY_DEFINITIONS,
    PlainEnglishEngine,
    SectionBusinessExplanation,
    expand_acronyms_in_text,
    generate_section_explanation,
    render_plain_english_finding_card,
    render_section_business_callout,
)
from app.reports.section_exports import section_report_generator
from app.audit.consistency_engine import CrossChapterConsistencyEngine


def _make_report(findings=None) -> ExecutiveReport:
    return ExecutiveReport(
        report_id="rep_test_001",
        analysis_id="an_test_001",
        website_url="https://acme-tools.com",
        domain="acme-tools.com",
        generated_at="2026-10-15T12:00:00Z",
        business_profile=BusinessProfile(business_name="Acme Tools"),
        scores=OverallScoreResult(
            overall_score=82.0,
            overall_grade="A-",
            grade="A-",
            health_label="STRONG",
            seo_score=85,
            geo_score=78,
            aeo_score=80,
            cro_score=86,
        ),
        story_summary="Acme Tools demonstrates solid architecture with clear conversion opportunities.",
        primary_strategic_opportunity="Publish schema.org Organization and Service entities.",
        consultant_advice_what_to_ignore="Disregard non-indexed staging subdomains.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear value proposition on desktop.",
            search_engine_perspective="Clean 200 OK responses.",
            ai_answer_engine_perspective="Concise factual extracts verified.",
        ),
        findings=findings or [],
    )


def test_glossary_definitions():
    """Verify core acronyms are defined with plain-English business translations."""
    assert "SEO" in GLOSSARY_DEFINITIONS
    assert "GEO" in GLOSSARY_DEFINITIONS
    assert "AEO" in GLOSSARY_DEFINITIONS
    assert "CRO" in GLOSSARY_DEFINITIONS
    assert "TTFB" in GLOSSARY_DEFINITIONS
    assert "CLS" in GLOSSARY_DEFINITIONS
    assert "LCP" in GLOSSARY_DEFINITIONS
    assert "INP" in GLOSSARY_DEFINITIONS
    assert "JSON-LD" in GLOSSARY_DEFINITIONS
    assert "HSTS" in GLOSSARY_DEFINITIONS
    assert "CSP" in GLOSSARY_DEFINITIONS

    sample_text = "Missing HSTS and high TTFB affect SEO."
    expanded = expand_acronyms_in_text(sample_text)
    assert "HTTP Strict Transport Security" in expanded or "HSTS" in expanded


def test_plain_english_enrich_finding_legacy():
    """Verify that a legacy sparse Finding is properly enriched with all mandatory fields."""
    legacy_finding = Finding(
        finding_id="F-SEO-001",
        category="TECHNICAL_SEO",
        severity="HIGH",
        title="Missing Meta Description on Commercial Service Pages",
        description="Meta description tags are absent from 4 audited product pages.",
        recommendation="Add descriptive meta description tags to all service pages.",
        affected_urls=["https://example.com/services/consulting", "https://example.com/services/audit"],
    )

    enriched = PlainEnglishEngine.enrich_finding(legacy_finding)

    assert enriched["id"] == "F-SEO-001"
    assert enriched["title"] == "Missing Meta Description on Commercial Service Pages"
    assert enriched["severity"] == "HIGH"
    assert enriched["plain_english_summary"]
    assert enriched["what_was_checked"]
    assert enriched["observed_result"]
    assert enriched["who_affected"]
    assert enriched["business_impact"]
    assert enriched["recommended_action"]
    assert enriched["developer_instructions"]
    assert isinstance(enriched["verification_steps"], list)
    assert len(enriched["verification_steps"]) > 0
    assert enriched["expected_outcome"]
    assert "not a guarantee" in enriched["expected_outcome"].lower()


def test_render_plain_english_finding_card_all_11_points():
    """Verify that the rendered finding card contains all 11 numbered points and disclaimers."""
    finding_dict = {
        "id": "F-GEO-002",
        "finding_title": "Lack of Machine-Readable Executive Credentials in Schema",
        "title": "Lack of Machine-Readable Executive Credentials in Schema",
        "severity": "CRITICAL",
        "priority": "P0 (Immediate Blocker)",
        "lifecycle_status": "Open Defect",
        "scope_status": "Representative Sample (4 URLs)",
        "what_was_checked": "Evaluated Person and Organization schema tags in HTML head.",
        "observed_result": "No author or leadership schema detected on leadership bios.",
        "plain_english_summary": "AI search engines cannot verify who runs the company or wrote the advice.",
        "business_impact": "Causes Perplexity and ChatGPT to skip citing your brand as an authoritative voice.",
        "who_affected": "Prospective clients asking AI engines for verified vendor recommendations.",
        "affected_urls": ["https://example.com/about/team", "https://example.com/leadership"],
        "recommended_action": "Inject Schema.org Person markup linking to verified LinkedIn profiles.",
        "developer_instructions": 'Add <script type="application/ld+json">{"@context":"https://schema.org","@type":"Person"}</script>',
        "verification_steps": [
            "Deploy schema tags to staging server.",
            "Test URL with Google Rich Results validator.",
            "Verify 0 schema syntax errors and re-crawl in Dristik.",
        ],
        "evidence": [
            {
                "id": "EV-001",
                "source": "HTML DOM Parser",
                "observation": "Zero ld+json blocks found on /about/team",
                "scope": "Sampled URL",
            }
        ],
        "confidence": "HIGH (Empirical verification)",
        "limitations": "Tested on 2 leadership URLs; sitewide template pass assumed.",
        "expected_outcome": "Improved machine extractability for conversational AI search engines.",
    }

    card_html = render_plain_english_finding_card(finding_dict)

    # Verify all 11 numbered headings
    assert "1. What was found?" in card_html
    assert "2. What does this mean in simple English?" in card_html
    assert "plain-english-panel" in card_html
    assert "3. Why does this matter to your business?" in card_html
    assert "4. What did Dristik check?" in card_html
    assert "5. Which pages are affected?" in card_html
    assert "6. Recommended solution" in card_html
    assert "7. Technical implementation instructions (Developer details)" in card_html
    assert "8. How to verify the fix (Retest procedure)" in card_html
    assert "9. Supporting evidence" in card_html
    assert "10. Confidence and limitations" in card_html
    assert "11. Expected outcome" in card_html

    # Verify Who is affected and Commercial Disclaimer
    assert "Who is affected:" in card_html
    assert "Commercial Disclaimer:" in card_html
    assert "not a guarantee of improved rankings, traffic, leads, or revenue" in card_html

    # Verify developer instructions are inside code/pre blocks
    assert "code-block" in card_html
    assert "<pre" in card_html


def test_section_business_callout_defects_found():
    """Verify SectionBusinessExplanation when defects are present."""
    findings = [
        Finding(
            finding_id="F-01",
            category="TECHNICAL_SEO",
            severity="CRITICAL",
            title="Crawl Loop in Pagination",
        )
    ]
    exp = generate_section_explanation(
        section_id="ch_seo",
        section_title="Technical Search Engine Optimization (SEO)",
        findings=findings,
        pages_crawled=10,
        is_sample_audit=True,
    )
    assert exp.evidence_status == "DEFECTS_FOUND"
    assert "1 issue(s) identified" in exp.key_result
    assert exp.pages_affected == 1

    callout_html = render_section_business_callout(exp)
    assert "WHAT THIS MEANS FOR YOUR BUSINESS" in callout_html
    assert "ISSUES REQUIRING ATTENTION" in callout_html
    assert "Why this matters to your bottom line:" in callout_html


def test_section_business_callout_clean_sample():
    """Verify zero-fabrication sample pass disclosure: sample passed but uninspected pages are not guaranteed."""
    exp = generate_section_explanation(
        section_id="ch_seo",
        section_title="Technical Search Engine Optimization (SEO)",
        findings=[],
        pages_crawled=8,
        is_sample_audit=True,
    )
    assert exp.evidence_status == "SAMPLE_TESTED_CLEAN"
    assert "representative sample" in exp.evidence_status_note.lower()
    assert "does not guarantee" in exp.evidence_status_note.lower()

    callout_html = render_section_business_callout(exp)
    assert "SAMPLE PASSED // NO DEFECTS RECORDED" in callout_html
    assert "representative sample" in callout_html.lower()


def test_section_business_callout_untested_missing_connector():
    """Verify unmeasured sections are labeled NOT_TESTED with missing connector details, not false zeroes or passes."""
    exp = generate_section_explanation(
        section_id="ch_seo",
        section_title="Google Search Console Analytics",
        findings=None,
        pages_crawled=0,
        has_connector=False,
        connector_name="Google Search Console API",
    )
    assert exp.evidence_status == "NOT_TESTED"
    assert "Google Search Console API" in exp.key_result
    assert "is not connected" in exp.evidence_status_note
    assert "No speculative scores or assumptions were made" in exp.evidence_status_note

    callout_html = render_section_business_callout(exp)
    assert "NOT TESTED // INTEGRATION REQUIRED" in callout_html


def test_section_exports_contains_plain_english_and_callout():
    """Verify section exports HTML contains business callout and 11-point finding card."""
    finding = Finding(
        finding_id="F-CRAWL-001",
        category="TECHNICAL_SEO",
        severity="CRITICAL",
        title="Broken Internal Link Returning 404 Not Found",
        description="The main navigation links to /solutions which returns HTTP 404.",
        recommendation="Update navbar template href to point to /services.",
    )
    report = _make_report(findings=[finding])

    crawl_html = section_report_generator.render_section_html(report, "crawl")
    assert "WHAT THIS MEANS FOR YOUR BUSINESS" in crawl_html
    assert "1. What was found?" in crawl_html
    assert "2. What does this mean in simple English?" in crawl_html
    assert "plain-english-panel" in crawl_html
    assert "7. Technical implementation instructions (Developer details)" in crawl_html
    assert "Commercial Disclaimer:" in crawl_html


def test_consistency_engine_backfills_plain_english_fields():
    """Verify CrossChapterConsistencyEngine enriches findings missing plain-English fields."""
    raw_finding = Finding(
        finding_id="F-RAW-001",
        category="TECHNICAL_SEO",
        severity="HIGH",
        title="Missing H1 Heading on Homepage",
        description="No <h1> tag was found in the HTML source.",
        recommendation="Add a descriptive H1 heading summarizing the service.",
    )
    # Ensure plain_english_summary is unset
    raw_finding.plain_english_summary = None

    report = _make_report(findings=[raw_finding])

    reconciled_report, consistency_report = CrossChapterConsistencyEngine.audit_and_reconcile(report)

    f = reconciled_report.findings[0]
    assert f.plain_english_summary is not None
    assert len(f.plain_english_summary) > 0
    assert f.who_affected is not None
    assert f.observed_result is not None
    assert f.expected_outcome is not None

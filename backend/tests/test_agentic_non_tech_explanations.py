"""
Unit and integration tests for Agentic Non-Technical Explanations across Chapters and Findings.
Verifies that:
- synthesize_chapter_narrative_ai generates consultative non-technical answers for leadership.
- synthesize_chapter_narrative_ai sanitizes overclaims.
- Deterministic synthesize_narrative provides rich domain-specific consultative explanations.
- generate_section_explanation_ai generates non-technical section callouts.
- SpecialistAuditorAgent provides high-fidelity domain translations for non-technical questions.
- batch_enrich_report_agentic orchestrates report finding calibration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.enums import Category, Severity
from app.domain.models import Finding
from app.reports.agentic_chapter_synthesizer import (
    AIChapterExplanation,
    AgenticChapterSynthesizer,
)
from app.reports.plain_english_engine import (
    AgenticSpecialistRegistry,
    PlainEnglishEngine,
    generate_section_explanation,
    generate_section_explanation_ai,
    batch_enrich_report_agentic,
)


def _make_dummy_book(domain="example.com", pages=None, findings=None):
    b = MagicMock()
    b.domain = domain
    b.pages = pages or [MagicMock(url="https://example.com/"), MagicMock(url="https://example.com/about")]
    b.findings = findings or []
    b.report = MagicMock()
    return b


def _sample_finding(title="Missing Canonical Tag", severity="HIGH", category="TECHNICAL_SEO", **kwargs):
    base = {
        "finding_id": "F-TEST-001",
        "title": title,
        "description": "Technical DOM analysis observed absence of rel=canonical.",
        "severity": severity,
        "category": category,
        "affected_urls": ["https://example.com/duplicate"],
    }
    base.update(kwargs)
    return Finding(**base)


@pytest.mark.asyncio
async def test_chapter_narrative_ai_answers_non_tech_questions():
    """Verify that synthesize_chapter_narrative_ai answers the 5 non-tech questions for leadership."""
    finding = _sample_finding(
        title="Uncached Slow Server Response (TTFB > 1800ms)",
        severity="HIGH",
        category="TECHNICAL_SEO",
        why_it_matters="Slow server response increases mobile visitor drop-off.",
    )
    book = _make_dummy_book(findings=[finding])
    section = {"title": "HTTP & Server Reliability"}

    mock_client = MagicMock()
    mock_client.available = True
    mock_client.model = "gpt-4o-mini"
    mock_client.generate_chat_completion = AsyncMock(return_value={
        "text": '''
        {
            "executive_summary": "Dristik evaluated the hosting response times across key pages of example.com and detected significant server latency during peak initial connection requests.",
            "business_risk": "Prolonged server delays cause mobile visitors to abandon pages before viewing products, depressing lead generation and organic visibility.",
            "commercial_opportunity": "Accelerating server delivery through edge caching keeps visitors engaged and satisfies Google core performance criteria.",
            "why_reader_should_care": "Every second of avoidable server delay directly reduces buyer conversion rates.",
            "recommended_action": "Direct the DevOps engineering team to implement CDN page caching and optimize database response queries.",
            "priority_tier": "P1 (HIGH BUSINESS IMPACT)",
            "technical_mechanics": "Time to First Byte (TTFB) exceeded 1800ms across origin responses without a caching header.",
            "root_cause_analysis": "Origin web server executes uncached dynamic database queries on every incoming HTTP request.",
            "prescriptive_fix": "Configure reverse-proxy cache-control headers with max-age=3600 for public marketing endpoints.",
            "verification_protocol": "Execute 5 consecutive curl requests measuring time_starttransfer to confirm latency drops below 300ms."
        }
        '''
    })

    narrative = await AgenticChapterSynthesizer.synthesize_chapter_narrative_ai(
        book=book,
        number="14",
        section=section,
        findings=[finding],
        is_geo=False,
        client=mock_client,
    )

    # Verify non-technical questions answered
    assert "evaluated the hosting response times" in narrative["executive_summary"]
    assert "depressing lead generation" in narrative["business_risk"]
    assert "Accelerating server delivery" in narrative["commercial_opportunity"]
    assert "Every second of avoidable server delay" in narrative["why_reader_should_care"]
    assert "Direct the DevOps engineering team" in narrative["recommended_action"]
    assert narrative["priority_tier"] == "P1 (HIGH BUSINESS IMPACT)"
    assert "TTFB" in narrative["technical_mechanics"]


@pytest.mark.asyncio
async def test_chapter_narrative_ai_sanitizes_overclaims():
    """Verify that guarantees of traffic or revenue in chapter AI narratives are sanitized."""
    finding = _sample_finding(title="Missing HSTS Header", severity="HIGH")
    book = _make_dummy_book(findings=[finding])
    section = {"title": "HTTPS & Security Integrity"}

    mock_client = MagicMock()
    mock_client.available = True
    mock_client.model = "gpt-4o-mini"
    mock_client.generate_chat_completion = AsyncMock(return_value={
        "text": '''
        {
            "executive_summary": "Dristik inspected security directives across example.com.",
            "business_risk": "Until this defect is resolved, additional SEO or design work will not change buyer or citation outcomes.",
            "commercial_opportunity": "Resolving this fixes compliance.",
            "why_reader_should_care": "Security headers protect client sessions.",
            "recommended_action": "Deploy HSTS in reverse proxy.",
            "priority_tier": "P2 (TACTICAL OPTIMIZATION)",
            "technical_mechanics": "Missing Strict-Transport-Security header.",
            "root_cause_analysis": "Nginx config missing header directive.",
            "prescriptive_fix": "Add add_header Strict-Transport-Security.",
            "verification_protocol": "Curl -I to verify header."
        }
        '''
    })

    narrative = await AgenticChapterSynthesizer.synthesize_chapter_narrative_ai(
        book=book,
        number="18",
        section=section,
        findings=[finding],
        is_geo=False,
        client=mock_client,
    )

    # Overclaim must be sanitized
    assert "will not change buyer or citation outcomes" not in narrative["business_risk"]


def test_deterministic_chapter_narrative_consultative_answers():
    """Verify that deterministic fallback answers non-tech questions consultatively without robotic templates."""
    # 1. Security Chapter
    sec_finding = _sample_finding(title="Missing HSTS Header", severity="HIGH", category="TECHNICAL_SEO")
    book = _make_dummy_book(findings=[sec_finding])
    sec_narrative = AgenticChapterSynthesizer.synthesize_narrative(
        book=book,
        number="18",
        section={"title": "HTTPS & Security Integrity"},
        findings=[sec_finding],
    )
    assert "Missing security directives do not prevent search robots" in sec_narrative["business_risk"]
    assert "corporate buyer confidence" in sec_narrative["commercial_opportunity"].lower() or "transport encryption" in sec_narrative["commercial_opportunity"].lower()
    assert len(sec_narrative["why_reader_should_care"]) > 20
    assert len(sec_narrative["recommended_action"]) > 20

    # 2. Speed Chapter
    speed_finding = _sample_finding(title="High LCP on Mobile", severity="HIGH", category="TECHNICAL_SEO")
    speed_narrative = AgenticChapterSynthesizer.synthesize_narrative(
        book=book,
        number="16",
        section={"title": "Core Web Vitals & Page Speed"},
        findings=[speed_finding],
    )
    assert "server response times" in speed_narrative["business_risk"].lower() or "layout shifts" in speed_narrative["business_risk"].lower()

    # 3. CRO Chapter
    cro_finding = _sample_finding(title="No Primary CTA on Hero Viewport", severity="HIGH", category="CRO")
    cro_narrative = AgenticChapterSynthesizer.synthesize_narrative(
        book=book,
        number="50",
        section={"title": "Conversion Rate Optimization (CRO)"},
        findings=[cro_finding],
    )
    assert "calls-to-action" in cro_narrative["business_risk"].lower()
    assert "conversion velocity" in cro_narrative["commercial_opportunity"].lower()


@pytest.mark.asyncio
async def test_section_explanation_ai():
    """Verify that generate_section_explanation_ai answers executive non-tech questions."""
    finding = _sample_finding(title="Missing Structured Data", severity="MEDIUM")
    mock_client = MagicMock()
    mock_client.available = True
    mock_client.model = "gpt-4o-mini"
    mock_client.generate_chat_completion = AsyncMock(return_value={
        "text": '''
        {
            "plain_english_subject": "Evaluates machine-readable identity tags that help search engines understand your organization.",
            "key_result": "1 issue detected: Schema markup is missing on core commercial landing pages.",
            "why_reader_should_care": "Without structured markup, your business misses out on rich Google snippets and AI engine recognition.",
            "recommended_action": "Deploy JSON-LD Organization and Product schema across page templates."
        }
        '''
    })

    exp = await generate_section_explanation_ai(
        section_id="ch_seo",
        section_title="Structured Data & Knowledge Graph",
        findings=[finding],
        domain="example.com",
        client=mock_client,
    )

    assert "Evaluates machine-readable identity tags" in exp.plain_english_subject
    assert "misses out on rich Google snippets" in exp.why_reader_should_care
    assert "Deploy JSON-LD Organization" in exp.recommended_action
    assert exp.evidence_status == "DEFECTS_FOUND"


def test_specialist_auditor_agent_domain_intelligence():
    """Verify SpecialistAuditorAgent provides high-fidelity domain intelligence for non-technical questions."""
    agent = AgenticSpecialistRegistry.dispatch_agent_for_section("ch_seo", "Canonicalization")
    assert agent.domain == "CANONICAL"

    # 1. Plain English explanation
    exp = agent.explain("Canonical URL Mismatch", "", "CANONICAL")
    assert "Search engines require a single definitive URL address" in exp
    assert "diluting page search prominence" in exp

    # 2. Business impact
    impact = agent.business_impact("Canonical URL Mismatch", "", "HIGH")
    assert "Dilutes link equity across duplicate URLs" in impact

    # 3. Who is affected
    who = agent.who_is_affected("Canonical URL Mismatch", "")
    assert "Search Spiders" in who

    # 4. Recommended action
    rec = agent.recommended_action("Canonical URL Mismatch")
    assert "Ensure each canonical tag points to the single authoritative URL" in rec


@pytest.mark.asyncio
async def test_batch_enrich_report_agentic():
    """Verify batch_enrich_report_agentic calibrates and explains findings."""
    finding = _sample_finding(title="Broken Nav Link Returning 404", severity="HIGH")
    report = MagicMock()
    report.findings = [finding]

    mock_client = MagicMock()
    mock_client.available = True
    mock_client.model = "gpt-4o-mini"
    mock_client.generate_chat_completion = AsyncMock(return_value={
        "text": '''
        {
            "what_is_this": "A navigation link on your website leads to a missing 404 page.",
            "why_to_change": "Broken links frustrate buyers and waste search engine crawl resources.",
            "how_to_change": "Update the navigation link to point to the active page address.",
            "business_impact": "High",
            "is_blocking": false,
            "blocks": [],
            "blocking_reason": null,
            "affected_outcomes": ["buyer_experience", "crawl_hygiene"]
        }
        '''
    })

    enriched_report = await batch_enrich_report_agentic(report, domain="example.com", client=mock_client)
    f = enriched_report.findings[0]
    assert "missing 404 page" in f.description
    assert "frustrate buyers" in f.why_it_matters

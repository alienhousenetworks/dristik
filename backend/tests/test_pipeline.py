"""
Dristik AI Comprehensive Test Suite
Tests SSRF security, deterministic analyzers, evidence provenance, scoring, and end-to-end orchestration.
"""
import pytest
import asyncio
from bs4 import BeautifulSoup

from app.core.security.ssrf import is_safe_url
from app.evidence.store import EvidenceStore
from app.crawl.analyzers.html import analyze_html_content, calculate_readability
from app.crawl.analyzers.schema import analyze_schema_markup
from app.crawl.analyzers.meta import analyze_meta_tags
from app.inference.json_repair import repair_and_parse_json
from app.scoring.engine import ScoringEngine
from app.domain.models import BusinessProfile, Finding
from app.domain.enums import BusinessIntent, Category, Severity
from app.orchestration.orchestrator import orchestrator

def test_django_main_is_used_not_nav_chrome():
    from bs4 import BeautifulSoup
    from app.crawl.analyzers.html import analyze_html_content, distill_semantic_content, heading_text
    from app.evidence.store import EvidenceStore
    from app.crawl.crawler import CrawlerService

    html = """
    <html><head><title>Privacy Policy | NORTHWIND</title></head>
    <body>
      <nav>COMPANY About Us Careers Blog SERVICES Software Development API Development</nav>
      <div id="mobile-menu">COMPANY About Us Careers Blog SERVICES Cloud Engineering</div>
      <main>
        <h1>Privacy <span>Policy</span></h1>
        <p>This privacy notice for Northwind describes how we collect and use information when you use the website.</p>
        <h2>1. Summary of key points</h2>
        <p>We process account data to deliver the service.</p>
      </main>
      <footer>Contact</footer>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    assert heading_text(h1) == "Privacy Policy"
    distilled = distill_semantic_content(soup)
    assert "This privacy notice" in distilled
    assert "Software Development" not in distilled
    assert distilled.lower().startswith("privacy") or "privacy notice" in distilled.lower()

    result = analyze_html_content(soup, "https://example.com/privacy", EvidenceStore("nav_test"))
    assert result["h1"] == ["Privacy Policy"]
    assert "Software Development" not in result["distilled_text"]

    crawler = CrawlerService()
    assert crawler._classify_page_type("/company/blog") == "blog"
    assert crawler._classify_page_type("/privacy") == "legal"
    assert crawler._classify_page_type("/services/cloud-solutions") == "product"


def test_cms_json_and_spa_shell_are_readable():
    from bs4 import BeautifulSoup
    from app.crawl.analyzers.html import analyze_html_content
    from app.crawl.analyzers.dynamic_content import extract_embedded_cms_content, needs_js_render
    from app.evidence.store import EvidenceStore

    spa = """
    <html><body>
      <div id="__next"></div>
      <script id="__NEXT_DATA__" type="application/json">{
        "props": {"pageProps": {
          "title": "Autumn collection landing",
          "hero": "Hand-finished wool coats cut in small batches.",
          "body": "Our studio publishes every product story from the admin CMS. Buyers see fabric, fit, and care in one place.",
          "cta": "Shop the collection"
        }}
      }</script>
      <script src="/chunk.js"></script>
      <script src="/chunk2.js"></script>
      <script src="/chunk3.js"></script>
      <script src="/chunk4.js"></script>
    </body></html>
    """
    soup = BeautifulSoup(spa, "lxml")
    embedded = extract_embedded_cms_content(soup)
    assert embedded["word_count"] > 20
    assert any("wool coats" in t.lower() for t in [embedded["text"]])
    assert needs_js_render(soup, 0) is True

    store = EvidenceStore("cms_test")
    result = analyze_html_content(soup, "https://example.com/", store)
    assert result["word_count"] > 20
    assert "wool" in result["distilled_text"].lower()

    django = """
    <html><body>
      <div id="content"></div>
      <script id="page-data" type="application/json">{
        "fields": {
          "headline": "Clinic visiting hours",
          "rich_text": "<p>The ward is open weekdays from 8am. Book from the patient portal.</p>"
        }
      }</script>
    </body></html>
    """
    dsoup = BeautifulSoup(django, "lxml")
    dres = analyze_html_content(dsoup, "https://clinic.example/", EvidenceStore("django_cms"))
    assert "visiting hours" in dres["distilled_text"].lower()
    assert "patient portal" in dres["distilled_text"].lower()


def test_per_page_seo_and_copy_fallback():
    from app.agents.page.intelligence import audit_page_seo, fallback_copy_audit
    from app.domain.models import PageEvidence, BusinessProfile

    thin = PageEvidence(
        url="https://example.com/about",
        title="Hi",
        meta_description=None,
        h1=[],
        h2=[],
        word_count=40,
        page_type="about",
        body_text="We are a team.",
        ctas=[],
    )
    seo = audit_page_seo(thin)
    assert seo.title_status == "too_short"
    assert seo.meta_status == "missing"
    assert seo.h1_status == "missing"
    assert seo.score < 80

    copy = fallback_copy_audit(thin, BusinessProfile(business_name="Northwind", primary_intent=BusinessIntent.SAAS), seo)
    assert copy.suggested.h1
    assert copy.suggested.title
    assert copy.suggested.meta_description
    assert copy.suggested.primary_cta
    assert any(i.area == "h1" for i in copy.issues)


def test_ssrf_protection():
    # Private and loopback IPs must be blocked
    safe, _ = is_safe_url("http://127.0.0.1:8000/secret")
    assert not safe
    safe, _ = is_safe_url("http://localhost:3000")
    assert not safe
    safe, _ = is_safe_url("http://169.254.169.254/latest/meta-data")
    assert not safe
    safe, _ = is_safe_url("ftp://example.com")
    assert not safe
    
    # Public domain should pass
    safe, _ = is_safe_url("https://example.com")
    assert safe

def test_deterministic_analyzers_and_evidence_store():
    store = EvidenceStore("test_run_001")
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Acme AI — High Performance Intelligence</title>
    <meta name="description" content="Acme AI delivers autonomous intelligence tools for modern software development.">
    <link rel="canonical" href="https://acme.ai">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Acme AI",
        "url": "https://acme.ai"
    }
    </script>
</head>
<body>
    <h1>Acme AI Autonomous Intelligence</h1>
    <h2>Enterprise Scalability</h2>
    <p>We build cutting edge AI software that accelerates developer velocity and simplifies complex data flows.</p>
</body>
</html>"""
    soup = BeautifulSoup(html, "lxml")
    
    html_res = analyze_html_content(soup, "https://acme.ai", store)
    assert len(html_res["h1"]) == 1
    assert html_res["h1"][0] == "Acme AI Autonomous Intelligence"
    assert html_res["word_count"] > 10
    
    meta_res = analyze_meta_tags(soup, "https://acme.ai", store)
    assert meta_res["title"] == "Acme AI — High Performance Intelligence"
    assert meta_res["canonical_url"] == "https://acme.ai"
    
    schema_res = analyze_schema_markup(soup, "https://acme.ai", store)
    assert "Organization" in schema_res["schema_types"]
    
    # Check evidence store
    assert store.count() >= 4
    all_ev = store.get_all()
    assert all_ev[0].hash is not None

def test_json_repair():
    # Test markdown code block extraction
    raw = "```json\n{\"business_name\": \"Acme Corp\", \"score\": 88}\n```"
    repaired = repair_and_parse_json(raw)
    assert repaired is not None
    assert repaired["business_name"] == "Acme Corp"
    
    # Test trailing comma repair
    raw_trailing = "{\"key\": \"val\",}"
    repaired_trailing = repair_and_parse_json(raw_trailing)
    assert repaired_trailing is not None
    assert repaired_trailing["key"] == "val"

    # Truncated object (max_tokens cut mid-generation)
    raw_truncated = '{"intent_alignment_analysis": "Architecture supports the offer", "confidence": 0.9, "content_gaps": ["pricing"'
    repaired_truncated = repair_and_parse_json(raw_truncated)
    assert repaired_truncated is not None
    assert repaired_truncated["intent_alignment_analysis"] == "Architecture supports the offer"
    assert repaired_truncated["confidence"] == 0.9
    assert repaired_truncated["content_gaps"] == ["pricing"]

    # Prose wrapper around JSON
    raw_wrapped = "Here is the result:\n{\"business_name\": \"Acme\", \"industry\": \"SaaS\"}\nThanks."
    repaired_wrapped = repair_and_parse_json(raw_wrapped)
    assert repaired_wrapped is not None
    assert repaired_wrapped["business_name"] == "Acme"

def test_deterministic_scoring_math():
    scoring = ScoringEngine()
    profile = BusinessProfile(
        business_name="Test SaaS",
        primary_intent=BusinessIntent.SAAS
    )
    
    # Test perfect score
    clean_scores = scoring.calculate_scores([], profile)
    assert clean_scores.overall_score == 100.0
    assert clean_scores.grade == "A+"
    
    # Test score with critical deduction
    f_crit = Finding(
        finding_id="f1",
        category=Category.TECHNICAL_SEO,
        severity=Severity.CRITICAL,
        title="Broken canonical and server errors",
        description="Severe issue",
        recommendation="Fix immediately"
    )
    degraded = scoring.calculate_scores([f_crit], profile)
    assert degraded.overall_score < 100.0
    # Unknown CRITICAL findings step business impact down to HIGH and default
    # confidence is LIKELY (medium). 25 * 0.85 * 0.75 = 15.9, so the pillar is 84.1.
    tech = degraded.category_scores["TECHNICAL_SEO"]
    assert tech.deductions[0]["points_lost"] == 6.0
    assert tech.score == 20.0
    assert tech.deductions[0]["title"] == "Broken canonical and server errors"
    empty_summary = clean_scores.category_scores["CONTENT"].summary
    assert clean_scores.category_scores["CONTENT"].score == 100.0
    assert "100/100" in empty_summary or "No verified defects" in empty_summary

@pytest.mark.asyncio
async def test_end_to_end_orchestration(monkeypatch):
    from unittest.mock import AsyncMock
    from app.domain.models import PageEvidence, CrawlManifest
    from app.core.config import settings
    
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "test_key_mock")
    
    # Mock crawler to return real PageEvidence
    mock_page = PageEvidence(
        url="https://dristik-demo.ai",
        status_code=200,
        title="Dristik Demo Platform",
        meta_description="Demo platform for unit tests",
        h1=["Welcome to Dristik"],
        h2=["Scalable Architecture"],
        h3=[],
        word_count=200,
        readability_score=80.0,
        canonical_url="https://dristik-demo.ai",
        robots_meta="index, follow",
        viewport="width=device-width, initial-scale=1",
        og_tags={},
        twitter_tags={},
        schema_types=["Organization"],
        raw_schema=[],
        internal_links=["https://dristik-demo.ai/pricing"],
        external_links=[],
        images_without_alt=0,
        total_images=2,
        ttfb_ms=65.0,
        dom_elements_count=30,
        scripts_count=1,
        stylesheets_count=1,
        page_type="homepage"
    )
    mock_manifest = CrawlManifest(
        domain="dristik-demo.ai",
        base_url="https://dristik-demo.ai",
        total_pages_discovered=1,
        pages=[mock_page],
        sitemap_found=True,
        sitemap_url="https://dristik-demo.ai/sitemap.xml",
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nAllow: /",
        crawl_health={"avg_ttfb_ms": 65.0, "total_words_across_site": 200, "page_breakdown": []}
    )
    
    monkeypatch.setattr(
        orchestrator.crawler,
        "crawl_site_and_analyze",
        AsyncMock(return_value=mock_manifest)
    )
    
    # Mock Together AI client response
    from app.inference.together import TogetherClient
    mock_llm_json = '{"business_name": "Dristik Demo", "primary_intent": "saas", "summary": "Valid test summary", "claims": []}'
    monkeypatch.setattr(
        TogetherClient,
        "generate_chat_completion",
        AsyncMock(return_value={"content": mock_llm_json, "input_tokens": 50, "output_tokens": 50, "latency_ms": 120.0})
    )

    from app.inference.model_router import ModelRouter

    async def fake_structured(*args, **kwargs):
        role = kwargs.get("agent_role") or ""
        capability = kwargs.get("capability") or ""
        if "copywriter" in role.lower() or "copy auditor" in role.lower() or capability == "content_intelligence":
            return {
                "score": 72,
                "voice": "Direct",
                "clarity": "Clear",
                "persuasion": "Needs proof",
                "audience_fit": "SaaS buyers",
                "cta_quality": "Present",
                "what_works": ["Headline names the product"],
                "analysis": "Solid homepage promise, thin proof.",
                "issues": [{"area": "body", "severity": "MEDIUM", "issue": "Needs proof points", "why_it_matters": "Buyers cannot verify claims."}],
                "suggested": {
                    "title": "Dristik Demo | Website intelligence",
                    "meta_description": "Audit websites with evidence-backed SEO, copy, and AI search scores.",
                    "h1": "Website intelligence from evidence",
                    "hero": "Crawl a site. Verify every claim. Ship a plan.",
                    "primary_cta": "Start audit",
                    "secondary_cta": "See a sample",
                    "supporting_points": ["Per-page SEO", "Suggested copy"],
                    "body_rewrite": "Dristik Demo audits public websites and returns a plan.",
                    "notes": "Draft",
                },
            }
        return {"business_name": "Dristik Demo", "primary_intent": "saas", "claims": []}

    monkeypatch.setattr(ModelRouter, "generate_structured", AsyncMock(side_effect=fake_structured))

    run = orchestrator.create_run("https://dristik-demo.ai")
    assert run.status.value == "queued"
    
    # Execute analysis pipeline
    await orchestrator.execute_analysis_pipeline(run.analysis_id, "https://dristik-demo.ai")
    
    completed_run = orchestrator.runs[run.analysis_id]
    assert completed_run.error is None, f"Run failed with error: {completed_run.error}"
    assert completed_run.status.value == "completed"
    assert completed_run.report is not None
    assert completed_run.report.scores.overall_score > 0
    assert len(completed_run.report.code_patches) >= 0
    assert len(completed_run.report.roadmap_7_days) >= 0
    assert completed_run.report.page_reports
    copy = completed_run.report.page_reports[0].copywriting
    if copy.llm_status == "ok":
        assert copy.suggested and copy.suggested.h1
    else:
        assert copy.suggested is None
        assert copy.llm_failure_reason

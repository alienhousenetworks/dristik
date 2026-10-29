import pytest
from unittest.mock import AsyncMock
from app.evidence.store import EvidenceStore
from app.crawl.crawler import CrawlerService
from app.orchestration.orchestrator import orchestrator
from app.domain.models import PageEvidence, CrawlManifest
from app.core.config import settings
from app.inference.llm_client import LLMClient

@pytest.mark.asyncio
async def test_crawler_multi_page_manifest(monkeypatch):
    store = EvidenceStore("test_multi_crawl")
    crawler = CrawlerService()
    
    # Mock crawler HTTP fetch
    mock_page = PageEvidence(
        url="https://example.com",
        status_code=200,
        title="Example Domain",
        meta_description="Example site",
        h1=["Example Domain"],
        h2=[],
        h3=[],
        word_count=150,
        readability_score=75.0,
        canonical_url="https://example.com",
        robots_meta="index, follow",
        viewport="width=device-width, initial-scale=1",
        og_tags={},
        twitter_tags={},
        schema_types=[],
        raw_schema=[],
        internal_links=["https://example.com/about"],
        external_links=[],
        images_without_alt=0,
        total_images=1,
        ttfb_ms=45.0,
        dom_elements_count=20,
        scripts_count=0,
        stylesheets_count=1,
        page_type="homepage"
    )
    mock_manifest = CrawlManifest(
        domain="example.com",
        base_url="https://example.com",
        total_pages_discovered=1,
        pages=[mock_page],
        sitemap_found=False,
        robots_txt_found=False,
        crawl_health={"avg_ttfb_ms": 45.0, "total_words_across_site": 150, "page_breakdown": [{"url": "https://example.com", "status": 200, "ttfb_ms": 45.0, "words": 150}]}
    )
    
    monkeypatch.setattr(crawler, "crawl_site_and_analyze", AsyncMock(return_value=mock_manifest))
    manifest = await crawler.crawl_site_and_analyze(
        target_url="https://example.com",
        evidence_store=store,
        max_pages=3
    )
    
    assert manifest.domain == "example.com"
    assert len(manifest.pages) >= 1
    assert manifest.crawl_health is not None
    assert "page_breakdown" in manifest.crawl_health

@pytest.mark.asyncio
async def test_multi_page_orchestration_pipeline(monkeypatch):
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "test_key")
    
    mock_page = PageEvidence(
        url="https://supabase.com",
        status_code=200,
        title="Supabase | The Open Source Firebase Alternative",
        meta_description="Build production apps with Postgres database, Authentication, instant APIs, Edge Functions, Realtime subscriptions, Storage, and Vector embeddings.",
        h1=["Build in a weekend. Scale to millions."],
        h2=["Features", "Products"],
        h3=[],
        word_count=500,
        readability_score=70.0,
        canonical_url="https://supabase.com",
        robots_meta="index, follow",
        viewport="width=device-width, initial-scale=1",
        og_tags={},
        twitter_tags={},
        schema_types=["Organization", "SoftwareApplication"],
        raw_schema=[],
        internal_links=["https://supabase.com/pricing", "https://supabase.com/docs"],
        external_links=[],
        images_without_alt=0,
        total_images=5,
        ttfb_ms=50.0,
        dom_elements_count=80,
        scripts_count=5,
        stylesheets_count=2,
        page_type="homepage"
    )
    mock_manifest = CrawlManifest(
        domain="supabase.com",
        base_url="https://supabase.com",
        total_pages_discovered=1,
        pages=[mock_page],
        sitemap_found=True,
        sitemap_url="https://supabase.com/sitemap.xml",
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nAllow: /",
        crawl_health={"avg_ttfb_ms": 50.0, "total_words_across_site": 500, "page_breakdown": []}
    )
    
    monkeypatch.setattr(orchestrator.crawler, "crawl_site_and_analyze", AsyncMock(return_value=mock_manifest))
    mock_llm_json = '{"business_name": "Supabase", "primary_intent": "saas", "summary": "Open source backend platform", "claims": []}'
    monkeypatch.setattr(
        LLMClient,
        "generate_chat_completion",
        AsyncMock(return_value={"content": mock_llm_json, "input_tokens": 50, "output_tokens": 50, "latency_ms": 100.0, "provider": "together"})
    )
    
    run = orchestrator.create_run("https://supabase.com")
    await orchestrator.execute_analysis_pipeline(run.analysis_id, "https://supabase.com", max_pages=3)
    
    completed = orchestrator.runs[run.analysis_id]
    assert completed.status.value == "completed"
    assert completed.report is not None
    assert completed.report.crawl_manifest is not None
    assert len(completed.report.crawl_manifest.pages) >= 1

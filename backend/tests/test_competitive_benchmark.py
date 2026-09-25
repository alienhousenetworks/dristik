"""
Unit tests for Dristik AI Competitive Benchmarking Layer.
"""
import pytest
from unittest.mock import AsyncMock
from app.domain.models import PageEvidence, CrawlManifest
from app.intelligence.competitive.benchmark import (
    _clean_domain,
    _evaluate_page_to_pillar_scores,
    _extract_tech_specs,
    CompetitorBenchmarkEngine,
    CompetitorPillarScores,
)


def test_clean_domain_utility():
    assert _clean_domain("https://www.alienhousenetworks.com/features") == "alienhousenetworks.com"
    assert _clean_domain("http://tailscale.com:8080/pricing") == "tailscale.com"
    assert _clean_domain("cloudflare.com") == "cloudflare.com"


def test_evaluate_page_to_pillar_scores():
    # Good evidence
    ev_good = PageEvidence(
        url="https://example.com",
        status_code=200,
        title="Enterprise Zero-Trust Network & Mesh Routing Platform",
        meta_description="Secure your infrastructure with fast encrypted mesh VPN networks and automated zero-trust policies.",
        h1=["Modern Mesh Networking for Distributed Teams"],
        word_count=850,
        ttfb_ms=210.0,
        viewport="width=device-width, initial-scale=1.0",
        schema_types=["Organization", "SoftwareApplication", "FAQPage"],
        ctas=["Start Free Trial", "Schedule Architecture Demo"],
        dom_elements_count=850
    )

    scores = _evaluate_page_to_pillar_scores(ev_good, is_https=True)
    assert scores.search_seo >= 80
    assert scores.ai_search_geo >= 80
    assert scores.experience_sxo >= 90
    assert scores.conversion_cro >= 80
    assert scores.overall_score >= 80

    # Poor evidence
    ev_poor = PageEvidence(
        url="http://slow-site.com",
        status_code=404,
        title="Hi",
        meta_description="",
        h1=[],
        word_count=50,
        ttfb_ms=1800.0,
        viewport=None,
        schema_types=[],
        ctas=[],
        dom_elements_count=3200
    )

    scores_poor = _evaluate_page_to_pillar_scores(ev_poor, is_https=False)
    assert scores_poor.search_seo <= 40
    assert scores_poor.ai_search_geo <= 35
    assert scores_poor.experience_sxo <= 45
    assert scores_poor.overall_score <= 45


@pytest.mark.asyncio
async def test_3way_benchmark_engine():
    mock_crawler = AsyncMock()

    # Mock competitor 1 (Slow but rich content)
    comp1_ev = PageEvidence(
        url="https://rival1.com",
        status_code=200,
        title="Rival 1 Solutions - Enterprise Cloud Architecture",
        meta_description="Enterprise cloud infrastructure provider with high security.",
        h1=["Cloud Infrastructure Simplified"],
        word_count=1200,
        ttfb_ms=850.0,
        viewport="width=device-width",
        schema_types=["Organization"],
        ctas=["Request Quote"],
        dom_elements_count=1200
    )

    # Mock competitor 2 (Fast but minimal schema)
    comp2_ev = PageEvidence(
        url="https://rival2.com",
        status_code=200,
        title="Rival 2 Network Engine",
        meta_description="Lightweight routing for modern developer stacks.",
        h1=["Fast Routing Everywhere"],
        word_count=400,
        ttfb_ms=180.0,
        viewport="width=device-width",
        schema_types=[],
        ctas=["Sign Up", "Read Docs"],
        dom_elements_count=700
    )

    def side_effect_crawl(target_url, evidence_store, max_pages=1):
        manifest = CrawlManifest(website_url=target_url)
        if "rival1" in target_url:
            manifest.pages = [comp1_ev]
        else:
            manifest.pages = [comp2_ev]
        return manifest

    mock_crawler.crawl_site_and_analyze.side_effect = side_effect_crawl

    engine = CompetitorBenchmarkEngine(crawler=mock_crawler)

    target_ev = PageEvidence(
        url="https://target.com",
        status_code=200,
        title="Target Platform - High Performance Cloud Security",
        meta_description="Target provides ultra-low latency mesh networking with automated schema declarations.",
        h1=["Enterprise Mesh Security"],
        word_count=900,
        ttfb_ms=220.0,
        viewport="width=device-width",
        schema_types=["Organization", "SoftwareApplication", "FAQPage"],
        ctas=["Start Free", "Book Demo"],
        dom_elements_count=800
    )

    result = await engine.benchmark_two_competitors(
        target_domain="target.com",
        competitor_1_url="rival1.com",
        competitor_2_url="rival2.com",
        target_evidence=target_ev
    )

    assert result.target_domain == "target.com"
    assert len(result.peers) == 3
    # Target has rich schema and fast speed, should lead
    assert result.target_overall_rank == 1
    assert result.target_vs_peer_avg_delta > 0
    assert len(result.competitive_moats) > 0
    # Summary should mention rank #1
    assert "leads this 3-way peer cohort" in result.strategic_summary

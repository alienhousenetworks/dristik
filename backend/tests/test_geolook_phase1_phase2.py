"""
Unit tests for GeoLook -> Dristik Phase 1 & Phase 2 integrated modules:
- Unified RFC 9309 robots.txt parser (crawl/robots.py)
- Active WAF/CDN differential AI-UA probing (crawler_accessibility.py)
- 4-Layer GEO dependency chain with upstream-first `blocked_by` (dependency_chain.py)
- Universal draft fabrication-risk linter (draft_linter.py)
- Zero-key search demand miner with snapshot diffing (demand_miner.py)
"""
from __future__ import annotations

import pytest

from app.crawl.robots import check_ai_bots_robots, evaluate_robots, sitewide_disallow
from app.geo.demand_miner import (
    classify_intent_group,
    is_relevant_suggestion,
    mine_search_demand,
    to_natural_question,
)
from app.geo.dependency_chain import evaluate_dependency_chain
from app.geo.draft_linter import lint_draft
from app.geo.intelligence.crawler_accessibility import CrawlerAccessibilityEngine


# ============================================================================
# Phase 1.1: Unified RFC 9309 robots.txt parser
# ============================================================================

def test_rfc9309_shared_groups_and_specificity_override():
    robots = """
    User-agent: *
    Disallow: /

    User-agent: GPTBot
    User-agent: OAI-SearchBot
    Allow: /
    Disallow: /admin/
    """
    # Wildcard blocks ClaudeBot
    assert evaluate_robots(robots, "/", "ClaudeBot").allowed is False
    assert sitewide_disallow(robots, "ClaudeBot") is True

    # Shared specific group overrides '*' for BOTH GPTBot and OAI-SearchBot
    assert evaluate_robots(robots, "/", "GPTBot").allowed is True
    assert evaluate_robots(robots, "/pricing", "OAI-SearchBot").allowed is True
    assert evaluate_robots(robots, "/admin/settings", "GPTBot").allowed is False


def test_rfc9309_longest_match_wildcards_anchors_and_allow_tiebreak():
    robots = """
    User-agent: PerplexityBot
    Disallow: /docs/
    Allow: /docs/public/
    Disallow: /*?session=
    Disallow: /private$
    Allow: /tie
    Disallow: /tie
    """
    assert evaluate_robots(robots, "/docs/internal", "PerplexityBot").allowed is False
    assert evaluate_robots(robots, "/docs/public/guide", "PerplexityBot").allowed is True
    assert evaluate_robots(robots, "/blog?session=abc", "PerplexityBot").allowed is False
    assert evaluate_robots(robots, "/private", "PerplexityBot").allowed is False
    assert evaluate_robots(robots, "/private-info", "PerplexityBot").allowed is True
    # Equal-length tie -> Allow wins per RFC 9309
    assert evaluate_robots(robots, "/tie", "PerplexityBot").allowed is True


def test_check_ai_bots_partial_path_blocks():
    robots = """
    User-agent: GPTBot
    Disallow: /pricing
    """
    blocked, partial = check_ai_bots_robots(robots, sample_paths=["/", "/pricing", "/docs"])
    assert "GPTBot" not in blocked
    assert any(p["bot"] == "GPTBot" and "/pricing" in p["paths"] for p in partial)


# ============================================================================
# Phase 1.2: Active WAF/CDN differential AI-UA probing
# ============================================================================

def test_crawler_accessibility_flags_waf_differential_block():
    robots = "User-agent: *\nAllow: /"
    report = CrawlerAccessibilityEngine.evaluate_crawler_access(
        robots_txt=robots,
        ai_ua_probe={"GPTBot": 403, "PerplexityBot": 403, "ClaudeBot": 200},
    )
    assert report.cdn_waf_challenges_detected is True
    assert "PerplexityBot" in report.ai_ua_blocked
    assert report.search_retrieval_allowed is False
    assert any("WAF/CDN" in r for r in report.actionable_remediation)


# ============================================================================
# Phase 1.3: Four-layer dependency chain & index hygiene
# ============================================================================

def test_dependency_chain_blocks_downstream_when_access_fails():
    pages = [
        {
            "url": "https://example.com/",
            "status_code": 200,
            "title": "Example Home",
            "body_text": "word " * 200,
            "word_count": 200,
            "canonical_url": "https://example.com/",
            "schema_types": ["Organization"],
            "json_ld": [{"@type": "Organization", "name": "Example"}],
        }
    ]
    res = evaluate_dependency_chain(
        pages=pages,
        robots_txt="User-agent: *\nAllow: /",
        has_sitemap=True,
        has_llms_txt=True,
        ai_ua_blocked=["GPTBot"],
        quotability_score=85.0,
    )
    assert res.first_failing_layer == "access"
    by_key = {l.key: l for l in res.layers}
    assert by_key["access"].status == "fail"
    assert by_key["orient"].blocked_by == "access"
    assert by_key["quote"].status == "blocked"
    assert by_key["quote"].score is None


def test_dependency_chain_detects_hygiene_and_exempts_login_page():
    pages = [
        {
            "url": "https://example.com/login",
            "status_code": 200,
            "title": "Login",
            "body_text": "Sign in to your account",
            "word_count": 5,
            "canonical_url": "https://example.com/login",
            "schema_types": ["WebPage"],
            "json_ld": [{"@type": "WebPage"}],
        },
        {
            "url": "https://example.com/guide",
            "status_code": 200,
            "title": "Same Title",
            "body_text": "This is a detailed product guide. " * 20,
            "word_count": 140,
            "canonical_url": "https://example.com/guide",
            "schema_types": ["FAQPage", "Article"],
            "json_ld": [{"@type": "Article", "headline": "Guide"}],
        },
        {
            "url": "https://example.com/guide-copy",
            "status_code": 200,
            "title": "Same Title",
            "body_text": "This is a detailed product guide. " * 20,
            "word_count": 140,
            "canonical_url": "https://example.com/guide-copy",
            "schema_types": ["Article"],
            "json_ld": [{"@type": "Article", "headline": "Guide"}],
        },
    ]
    res = evaluate_dependency_chain(
        pages=pages,
        robots_txt="User-agent: *\nAllow: /",
        has_sitemap=True,
        sitemap_urls=["https://example.com/guide", "https://example.com/search?q=test"],
        has_llms_txt=True,
        quotability_score=75.0,
    )
    # /login is exempted from SPA shell false positive
    assert "https://example.com/login" not in res.spa_shell_urls
    assert res.duplicate_title_groups == 1
    assert res.near_duplicate_body_groups == 1
    assert "https://example.com/search?q=test" in res.sitemap_noisy_urls
    assert "https://example.com/guide" in res.schema_content_mismatches
    assert "https://example.com/guide" in res.missing_article_authors


# ============================================================================
# Phase 2.1: Universal draft fabrication-risk linter
# ============================================================================

def test_draft_linter_blocks_placeholders_unconfirmed_competitors_and_guarantees():
    bad_draft = (
        "Compared to Competitor A and ShadowRival, our platform offers a 30-day money-back guarantee "
        "and saves teams 47% in 2023."
    )
    rep = lint_draft(
        bad_draft,
        verified_numbers=["10%"],
        verified_facts_text="Pricing starts at $49/month.",
        unconfirmed_competitors=["ShadowRival"],
        current_year=2026,
    )
    assert rep.status == "rejected"
    types = {i.issue_type for i in rep.blocking_issues}
    assert "placeholder_entity" in types
    assert "unconfirmed_competitor" in types
    assert "unsupported_claim" in types
    warn_types = {i.issue_type for i in rep.warnings}
    assert "unverified_number" in warn_types
    assert "stale_year" in warn_types

    clean_draft = "Acme-free verified guide: Dristik pricing starts at $49/month in 2026."
    rep_ok = lint_draft(
        clean_draft.replace("Acme-free ", ""),
        verified_numbers=["$49"],
        verified_facts_text="Pricing starts at $49/month.",
        current_year=2026,
    )
    assert rep_ok.status == "passed"


# ============================================================================
# Phase 2.2: Search demand miner & snapshot diffing
# ============================================================================

@pytest.mark.asyncio
async def test_demand_miner_filters_noise_classifies_and_diffs_snapshots():
    async def fake_fetcher(query: str, market: str):
        if "dristik" in query.lower():
            return [
                "dristik login",  # navigational noise -> dropped
                "dristik vs semrush",  # compare
                "dristik pricing",  # pricing
                "unrelated toaster review",  # prefix drift -> dropped
            ]
        return []

    assert is_relevant_suggestion("dristik login", "Dristik") is False
    assert is_relevant_suggestion("dristik vs semrush", "Dristik") is True
    assert classify_intent_group("dristik vs semrush", "brand") == "COMPARE"
    assert to_natural_question("how does dristik work", "SCENARIO").endswith("?")

    snap = await mine_search_demand(
        brand_name="Dristik",
        market="global",
        previous_first_seen={"dristik pricing": "2026-10-01"},
        delay=0.0,
        fetcher=fake_fetcher,
    )
    terms = {c.term: c for c in snap.candidates}
    assert "dristik login" not in terms
    assert "unrelated toaster review" not in terms
    assert "dristik vs semrush" in terms and terms["dristik vs semrush"].is_new is True
    assert "dristik pricing" in terms and terms["dristik pricing"].is_new is False
    assert terms["dristik pricing"].first_seen == "2026-10-01"
    assert snap.new_count == 1

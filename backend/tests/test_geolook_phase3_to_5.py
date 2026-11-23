"""
Unit & Integration Tests for Phases 3, 4, and 5:
- Phase 3: Manual/browser sampling, provenance grades, negation guard, persistent overrides, visibility aggregation
- Phase 4: Declarative verification checkers + auto-reopen, live WordPress draft API, live GitHub branch+PR API, signed webhook + verification linker
- Phase 5: Delivery freshness guard, 2-round trend confirmation, competitor source-gap hit-list, offsite-only GEO readiness
"""
from __future__ import annotations

import json
import httpx
import pytest

from app.connectors.base.models import ConnectorCredentials
from app.connectors.github.client import GitHubClient
from app.connectors.github.remediation import GitHubRemediation
from app.connectors.outbound_webhook import (
    publish_signed_webhook,
    sign_webhook_payload,
    verify_published_asset,
)
from app.connectors.wordpress.client import WordPressClient
from app.connectors.wordpress.remediation import WordPressRemediation
from app.domain.enums import ConnectorType, PatchApprovalStatus, PatchOperation
from app.domain.models import RemediationPatch
from app.geo.offpage_network import compute_competitor_source_gap
from app.geo.readiness import evaluate_geo_readiness
from app.geo.reporting.freshness_guard import (
    check_delivery_freshness,
    evaluate_two_round_trend,
)
from app.geo.sampling_manual import (
    aggregate_manual_samples,
    analyze_manual_answer,
    apply_manual_override,
    export_sampling_sheet,
    import_sampling_sheet,
)
from app.geo.verification_engine import run_declarative_check


# ============================================================================
# Phase 3: Consumer / Manual Sampling, Provenance & Persistent Overrides
# ============================================================================

def test_phase3_manual_sheet_import_quarantine_and_override():
    sheet = export_sampling_sheet(
        brand_name="Dristik",
        platforms=["chatgpt_web"],
        questions=[
            {"id": "q001", "text": "What are the best GEO platforms for B2B teams?"},
            {"id": "q002", "text": "What is Dristik?"},
        ],
    )
    filled = sheet.replace(
        "### q001 · What are the best GEO platforms for B2B teams?\n\n```answer\n\n```",
        "### q001 · What are the best GEO platforms for B2B teams?\n\n```answer\n"
        "Top platforms include RivalOne (https://g2.com/rivalone) and Dristik (https://dristik.ai/geo). "
        "Note: some users mention Dristik is overpriced compared to free tools.\n```",
    ).replace(
        "### q002 · What is Dristik?\n\n```answer\n\n```",
        "### q002 · What is Dristik?\n\n```answer\nDristik is an enterprise SEO/GEO/AEO platform.\n```",
    )

    samples = import_sampling_sheet(
        filled,
        tenant_id="org_test",
        brand_name="Dristik",
        competitors={"RivalOne": ["Rival1"]},
        own_domain="https://dristik.ai",
        session_mode="personal",
    )
    assert len(samples) == 2
    s1, s2 = samples[0], samples[1]
    # Personal session auto-downgraded to Grade D
    assert s1.evidence_grade == "D_NEEDS_REVIEW"
    assert s1.needs_review is True
    assert "overpriced" in s1.automated_result.negative_cues
    assert s1.automated_result.brand_rank == 2  # RivalOne appeared first
    assert s2.brand_in_question is True  # Quarantined probe

    # Persistent human override preserves immutable automated_result
    apply_manual_override(
        s1,
        reviewer_id="analyst_1",
        brand_rank=1,
        review_note="RivalOne was only listed as legacy context.",
    )
    assert s1.automated_result.brand_rank == 2
    assert s1.effective_analysis().brand_rank == 1

    agg = aggregate_manual_samples(samples)
    plat_stats = agg["by_platform_surface"]["chatgpt_web:consumer_ui"]
    assert plat_stats["unprompted_samples"] == 1
    assert plat_stats["top1_rate"] == 1.0  # Reflects human override
    assert plat_stats["brand_probe"]["samples"] == 1
    assert plat_stats["brand_probe"]["recognized_rate"] == 1.0


def test_phase3_negation_guard_and_alias_boundaries():
    # 'AIGC' must not match 'AIGCLINK', and 'not Dristik' must flag needs_review
    res = analyze_manual_answer(
        answer_text="AIGCLINK is a different product. This tool is not Dristik.",
        brand_name="Dristik",
        brand_aliases=["AIGC"],
    )
    assert res.brand_mentioned is False
    assert res.needs_review is True


# ============================================================================
# Phase 4: Declarative Checkers + Live WordPress, GitHub & Signed Webhook
# ============================================================================

def test_phase4_declarative_checkers_and_auto_reopen():
    # Regression triggers auto_reopen_task=True
    reg = run_declarative_check(
        "site.no_ai_ua_block",
        audit_context={"site": {"ai_ua_blocked": ["GPTBot"]}},
        previous_passed=True,
    )
    assert reg.status == "REGRESSED"
    assert reg.auto_reopen_task is True

    # External domain citation check passes when target cited
    ext = run_declarative_check(
        "external.any:g2.com,capterra.com",
        audit_context={},
        metrics_context={"cited_domains": ["www.g2.com", "reddit.com"]},
    )
    assert ext.status == "PASS"
    assert ext.passed is True


@pytest.mark.asyncio
async def test_phase4_wordpress_live_draft_publish():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/wp-json/wp/v2/posts"
        body = json.loads(request.content.decode())
        assert body["status"] == "draft"
        return httpx.Response(201, json={"id": 42, "status": "draft", "link": "https://blog.example.com/?p=42"})

    creds = ConnectorCredentials(
        provider=ConnectorType.WORDPRESS,
        api_url="https://blog.example.com",
        username="editor",
        app_password="app-password-123",
    )
    rem = WordPressRemediation(WordPressClient(creds))
    patch = RemediationPatch(
        patch_id="PATCH-WP-1",
        finding_id="F-1",
        category="GEO",
        title="Add GEO Definition Block",
        explanation="Adds grounded definition block for citation readiness.",
        operation=PatchOperation.INSERT_BODY,
        target_url="https://blog.example.com/geo",
        after_snippet="<h2>What is Dristik?</h2><p>Verified copy.</p>",
        approval_status=PatchApprovalStatus.APPROVED,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_client:
        res = await rem.apply(patch, dry_run=False, http_client=mock_client)
    assert res.success is True
    assert res.execution_mode == "LIVE"
    assert res.diff_summary["wp_post_id"] == 42


@pytest.mark.asyncio
async def test_phase4_github_live_pr_publish():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "abc123"}})
        if request.method == "POST" and request.url.path.endswith("/git/refs"):
            return httpx.Response(201, json={"ref": "refs/heads/dristik/fix-patch-gh-1"})
        if request.method == "GET" and "/contents/" in request.url.path:
            return httpx.Response(404, json={"message": "Not Found"})
        if request.method == "PUT" and "/contents/" in request.url.path:
            return httpx.Response(201, json={"content": {"path": "docs/geo/llms.txt"}})
        if request.method == "POST" and request.url.path.endswith("/pulls"):
            return httpx.Response(201, json={"number": 17, "html_url": "https://github.com/acme/site/pull/17"})
        return httpx.Response(500)

    creds = ConnectorCredentials(
        provider=ConnectorType.GITHUB,
        repository="acme/site",
        github_token="ghp_testtoken",
        branch="main",
    )
    rem = GitHubRemediation(GitHubClient(creds))
    patch = RemediationPatch(
        patch_id="PATCH-GH-1",
        finding_id="F-2",
        category="GEO",
        title="Publish llms.txt",
        explanation="Publishes official llms.txt index to repository.",
        operation=PatchOperation.UPDATE_FILE,
        target_file="docs/geo/llms.txt",
        after_snippet="# Acme\n> Verified summary.",
        approval_status=PatchApprovalStatus.APPROVED,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_client:
        res = await rem.apply(patch, dry_run=False, http_client=mock_client)
    assert res.success is True
    assert res.execution_mode == "LIVE"
    assert res.pr_number == 17
    assert res.pr_url == "https://github.com/acme/site/pull/17"


@pytest.mark.asyncio
async def test_phase4_signed_webhook_and_post_publish_verification():
    secret = "whsec_supersecret"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            expected_sig = sign_webhook_payload(request.content, secret)
            assert request.headers["X-Dristik-Signature"] == expected_sig
            assert "X-Dristik-Idempotency-Key" in request.headers
            return httpx.Response(200, json={"url": "https://published.example.com/article-1"})
        if request.method == "GET" and str(request.url) == "https://published.example.com/article-1":
            return httpx.Response(200, text="<html><body>Live Article</body></html>")
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_client:
        rec = await publish_signed_webhook(
            webhook_url="https://hooks.example.com/publish",
            webhook_secret=secret,
            tenant_id="org_1",
            title="Verified GEO Guide",
            markdown="# Verified GEO Guide",
            approved_by="user_admin",
            http_client=mock_client,
        )
        assert rec.success is True
        assert rec.published_url == "https://published.example.com/article-1"
        verified = await verify_published_asset(rec, http_client=mock_client)
        assert verified.verification_status == "VERIFIED_LIVE"


# ============================================================================
# Phase 5: Freshness Guard, 2-Round Trend, Source-Gap & Offsite-Only Mode
# ============================================================================

def test_phase5_freshness_guard_and_two_round_trend():
    stale = check_delivery_freshness(audited_at="2026-11-23T10:00:00Z", verified_at="2026-11-15T10:00:00Z")
    assert stale.verification_stale is True
    assert stale.is_fresh is False

    fresh = check_delivery_freshness(audited_at="2026-11-23T10:00:00Z", verified_at="2026-11-23T12:00:00Z")
    assert fresh.is_fresh is True

    assert evaluate_two_round_trend([0.20, 0.35]).status == "OBSERVATIONAL_NOISE"
    assert evaluate_two_round_trend([0.20, 0.28, 0.36]).status == "CONFIRMED_UPWARD"
    assert evaluate_two_round_trend([0.40, 0.30, 0.20]).status == "CONFIRMED_DOWNWARD"


def test_phase5_competitor_source_gap_and_offsite_only_mode():
    sheet = """
## platform: perplexity_web
### q001 · Best GEO platform?
```answer
RivalX is widely reviewed on https://g2.com/rivalx and https://reddit.com/r/seo/1.
```
### q002 · GEO tool comparison?
```answer
RivalX appears on https://g2.com/compare and https://capterra.com/rivalx.
```
### q003 · Enterprise AEO tools?
```answer
Dristik is cited on https://capterra.com/dristik.
```
"""
    samples = import_sampling_sheet(
        sheet,
        tenant_id="org_1",
        brand_name="Dristik",
        competitors={"RivalX": []},
        own_domain="https://dristik.ai",
    )
    gap = compute_competitor_source_gap(samples, brand_name="Dristik", own_host="dristik.ai", min_hits=2)
    gap_domains = [item["domain"] for item in gap["source_gap_hitlist"]]
    # g2.com had 2 hits for RivalX and 0 for Dristik -> top hit-list; capterra.com was covered by Dristik -> excluded
    assert "g2.com" in gap_domains
    assert "capterra.com" not in gap_domains

    # Offsite-only mode (no website) marks own-site checks n/a instead of 0
    offsite = evaluate_geo_readiness(
        website_url="",
        pages=[],
        business_presence_mode="offsite_only",
        visibility_measured=True,
        visibility_score=64.0,
    )
    assert offsite.visibility_status == "MEASURED"
    assert offsite.extractability_score is None
    assert offsite.dimension_scores["retrieval_accessibility"].is_measured is False
    assert offsite.dimension_scores["live_ai_citations"].score == 64.0

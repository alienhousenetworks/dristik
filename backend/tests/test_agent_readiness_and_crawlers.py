"""Tests for Phase 7: path-level RFC 9309 robots.txt and /llms-full.txt checks."""
import pytest
from app.domain.models import CrawlManifest
from app.geo.agent_readiness import _robots_signal, evaluate_agent_readiness
from app.geo.intelligence.crawler_accessibility import CrawlerAccessibilityEngine


def test_robots_signal_evaluates_specific_page_path():
    robots = (
        "User-agent: OAI-SearchBot\n"
        "Disallow: /private/\n"
        "Allow: /private/public-guide$\n"
    )
    manifest = CrawlManifest(
        website_url="https://acme.com",
        robots_txt_found=True,
        robots_txt_content=robots,
    )
    # Root is allowed
    assert _robots_signal(manifest, page_path="/").status == "PRESENT"
    # /private/secret is blocked for OAI-SearchBot
    blocked = _robots_signal(manifest, page_path="/private/secret")
    assert blocked.status == "MISSING"
    assert "oai-searchbot" in blocked.summary.lower()
    # /private/public-guide matches longer Allow rule
    assert _robots_signal(manifest, page_path="/private/public-guide").status == "PRESENT"


def test_crawler_accessibility_path_level_and_new_bots():
    robots = "User-agent: Claude-SearchBot\nDisallow: /docs/\n"
    rep_root = CrawlerAccessibilityEngine.evaluate_crawler_access(robots_txt=robots, page_path="/")
    rep_docs = CrawlerAccessibilityEngine.evaluate_crawler_access(robots_txt=robots, page_path="/docs/api")

    root_by_bot = {c.bot_name: c for c in rep_root.crawlers_evaluated}
    docs_by_bot = {c.bot_name: c for c in rep_docs.crawlers_evaluated}

    assert "Claude-SearchBot" in root_by_bot
    assert "Claude-User" in root_by_bot
    assert "Perplexity-User" in root_by_bot
    assert root_by_bot["Claude-SearchBot"].is_allowed is True
    assert docs_by_bot["Claude-SearchBot"].is_allowed is False


@pytest.mark.asyncio
async def test_evaluate_agent_readiness_includes_llms_full_txt_signal(monkeypatch):
    async def _fake_llms(website_url: str, filename: str, signal_key: str):
        from app.geo.agent_readiness import _signal
        return _signal(signal_key, "PRESENT" if filename == "llms.txt" else "MISSING", f"mock {filename}")

    monkeypatch.setattr("app.geo.agent_readiness._llms_file_signal", _fake_llms)
    report = await evaluate_agent_readiness("https://acme.com/pricing", pages=[], manifest=None)
    keys = {s.key: s.status for s in report.signals}
    assert keys["llms_txt"] == "PRESENT"
    assert keys["llms_full_txt"] == "MISSING"

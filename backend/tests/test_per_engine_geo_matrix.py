"""
Unit tests for Per-Engine AI Scorecard, Information Gain, and AI Bot Directives.
"""
from app.domain.models import PageEvidence, BusinessProfile, CrawlManifest
from app.intelligence.geo.per_engine_evaluator import evaluate_per_engine_ai


def test_per_engine_evaluator_and_scorecard():
    pages = [
        PageEvidence(
            url="https://acme.com",
            title="Acme Platform — Enterprise Web Intelligence Solutions",
            h1=["Acme Enterprise Web Intelligence & Growth OS"],
            h2=["What is Acme?", "How Much Does Acme Cost?", "Methodology & Empirical Benchmarks"],
            body_text=(
                "Acme delivers verified web intelligence for enterprise engineering teams. "
                "Across a dataset of 1,200 domains, our platform eliminated 84% of crawl anomalies "
                "and lifted conversion rates by 23.5%. The standard plan starts at $49/mo. "
                "According to CTO Sarah Jenkins, our deterministic approach guarantees zero-fake telemetry."
            ),
            schema_types=["Organization", "WebSite", "FAQPage"],
        )
    ]
    manifest = CrawlManifest(
        domain="acme.com",
        base_url="https://acme.com",
        pages=pages,
        sitemap_found=True,
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nAllow: /\n",
    )
    profile = BusinessProfile(
        business_name="Acme",
        industry="Enterprise Software",
        products=["Web Intelligence OS"],
        target_audience="engineering leaders",
    )

    matrix = evaluate_per_engine_ai(
        pages=pages,
        manifest=manifest,
        profile=profile,
        website_url="https://acme.com",
    )

    # 1. Check all 4 engines are scored
    assert matrix.chatgpt.engine_name == "ChatGPT / SearchGPT"
    assert matrix.chatgpt.score >= 50.0

    assert matrix.perplexity.engine_name == "Perplexity"
    assert matrix.perplexity.score >= 50.0

    assert matrix.google_aio.engine_name == "Google AI Overviews"
    assert matrix.google_aio.score >= 60.0  # Boosted by Schema (FAQPage, Organization)

    assert matrix.claude_gemini.engine_name == "Claude / Gemini"
    assert matrix.claude_gemini.score >= 50.0

    # 2. Check Information Gain
    info_gain = matrix.information_gain
    assert info_gain.has_proprietary_statistics is True
    assert info_gain.has_methodology_section is True
    assert info_gain.has_executive_quotes is True
    assert info_gain.score >= 70.0
    assert len(info_gain.original_data_signals) >= 2

    # 3. Check AI Bot Directives & llms.txt
    directives = matrix.ai_bot_directives
    assert directives.gptbot_allowed is True
    assert directives.perplexitybot_allowed is True
    assert directives.claudebot_allowed is True
    assert directives.llms_txt_generated is not None
    assert "# Acme" in directives.llms_txt_generated
    assert "https://acme.com" in directives.llms_txt_generated


def test_fluff_penalizes_information_gain_and_claude_score():
    fluff_text = (
        "We empower organizations to unlock unprecedented, revolutionary growth "
        "with our cutting-edge, next-generation, world-class, hyper-advanced, "
        "game-changer seamless solutions."
    )
    pages = [
        PageEvidence(
            url="https://fluffy.com",
            title="The Future of Growth",
            h1=["Revolutionize Everything"],
            body_text=fluff_text,
        )
    ]
    matrix = evaluate_per_engine_ai(
        pages=pages,
        website_url="https://fluffy.com",
    )

    assert matrix.information_gain.score < 50.0
    assert matrix.information_gain.fluff_ratio_score > 30.0
    assert any("superlatives" in s.lower() for s in matrix.information_gain.commodity_fluff_signals)
    # Claude penalizes heavy fluff
    assert matrix.claude_gemini.score < matrix.chatgpt.score or matrix.claude_gemini.readiness_band in ("medium", "low")

"""
Tests for the 5 specialized copywriting agents and section-wise page copy intelligence.
"""
import pytest
from app.orchestration.runtime.registry import (
    COPYWRITING_AGENTS_V3,
    AGENT_REGISTRY,
    list_copywriting_specialists,
    get_agent_definition,
)
from app.orchestration.runtime.task_cards import ALL_TASK_CARDS, task_card_for
from app.domain.models import BusinessProfile, PageCopyAudit, PageEvidence, PageReport, PageSeoAudit, SuggestedCopy
from app.crawl.page_intelligence import fallback_copy_audit
from app.seo.reporting.seo_book_renderer import _specialist_copy, _url_key


def test_seo_book_dossier_keeps_specialist_title_across_trailing_slash():
    report = PageReport(
        url="https://acme-analytics.io",
        copywriting=PageCopyAudit(
            llm_status="ok",
            score=81,
            analysis="Name the product in the title.",
            suggested=SuggestedCopy(
                title="Acme Analytics | Unified Data",
                meta_description="Observability for engineering teams.",
                h1="Unified data for engineering teams",
                hero="One pipeline record for the teams who already run Acme.",
                hook_3sec="See pipeline cost before the quarter closes.",
            ),
        ),
    )
    payload = _specialist_copy(report)
    assert payload["has_specialist_copy"] is True
    assert payload["suggested_title"] == "Acme Analytics | Unified Data"
    assert payload["suggested_meta"].startswith("Observability")
    assert payload["hook"].startswith("See pipeline")
    assert "Official Enterprise" not in payload["suggested_title"]
    assert _url_key("https://acme-analytics.io/") == _url_key(report.url)


def test_5_copywriting_agents_registered():
    specialists = list_copywriting_specialists()
    assert len(specialists) == 5
    expected_ids = {
        "copywriting.seo.v3",
        "copywriting.geo.v3",
        "copywriting.cro.v3",
        "copywriting.clarity.v3",
        "copywriting.section.v3",
    }
    assert set(COPYWRITING_AGENTS_V3.keys()) == expected_ids
    for aid in expected_ids:
        defn = get_agent_definition(aid)
        assert defn is not None
        assert defn.domain == "COPYWRITING"
        assert defn.worker_type == "analyst_worker"
        assert len(defn.capabilities) >= 2
        assert len(defn.required_evidence) >= 2


def test_copywriting_task_cards_present():
    for aid in [
        "copywriting.seo.v3",
        "copywriting.geo.v3",
        "copywriting.cro.v3",
        "copywriting.clarity.v3",
        "copywriting.section.v3",
    ]:
        card = task_card_for(aid)
        assert card != "Audit only what the evidence pack contains. Cite [ev_xxx]. Invent nothing."
        assert len(card) > 50


def test_parse_copy_result_keeps_title_tag_and_top_level_rewrite():
    from app.crawl.page_intelligence import _parse_copy_result

    page = PageEvidence(url="https://acme-analytics.io/", title="Acme", word_count=40)
    profile = BusinessProfile(business_name="Acme Analytics")
    fallback = fallback_copy_audit(page, profile, PageSeoAudit())
    parsed = _parse_copy_result(
        {
            "score": 74,
            "analysis": "The title does not name the product.",
            "suggested": {
                "title_tag": "Acme Analytics | Unified Data",
                "description": "Observability for engineering teams that already run Acme.",
                "sections": [{"section_name": "Hero", "suggested_copy": "Unified data for the teams who already pay for Acme."}],
            },
        },
        fallback,
        brand_name="Acme Analytics",
    )
    assert parsed.llm_status == "ok"
    assert parsed.suggested is not None
    assert parsed.suggested.title == "Acme Analytics | Unified Data"
    assert parsed.suggested.meta_description.startswith("Observability")
    assert parsed.suggested.sections[0].suggested_copy.startswith("Unified data")
    assert "Official Enterprise" not in parsed.suggested.title

    top_level = _parse_copy_result(
        {
            "title_tag": "Acme Analytics pricing",
            "meta_description": "Pricing for the Acme observability plan.",
            "hook": "See pipeline cost before the quarter closes.",
        },
        fallback,
    )
    assert top_level.suggested is not None
    assert top_level.suggested.title == "Acme Analytics pricing"
    assert top_level.suggested.hook_3sec.startswith("See pipeline")


def test_template_sections_are_dropped_unless_the_page_has_them():
    from app.crawl.page_intelligence import _keep_page_section
    from app.domain.models import CopySection

    page = PageEvidence(
        url="https://acme-analytics.io/pricing",
        h1=["Plans"],
        h2=["Team", "Enterprise"],
    )
    canned = CopySection(
        section_name="Problem Agitation & Commercial Friction",
        suggested_copy="Many prospective clients struggle with fragmented processes.",
    )
    real = CopySection(
        section_name="Enterprise",
        suggested_copy="Enterprise is the plan for teams that already run Acme.",
    )
    assert _keep_page_section(canned, page) is False
    assert _keep_page_section(real, page) is True


def test_page_intelligence_generates_sections_and_faqs():
    page = PageEvidence(
        url="https://acme-analytics.io/",
        page_type="homepage",
        title="Acme Analytics — Unified Data Platform",
        meta_description="Acme Analytics provides enterprise data intelligence and real-time observability.",
        h1=["Unified Data Platform for Modern Engineering Teams"],
        h2=["Automated Data Pipelines", "Real-Time Observability", "Enterprise Governance"],
        ctas=["Start Free Trial", "Book a Demo"],
        word_count=320,
        readability_score=68.0,
    )
    profile = BusinessProfile(
        business_name="Acme Analytics",
        value_proposition="Real-time data intelligence and automated pipeline observability",
        target_audience="VP of Engineering & Data Platform Leads",
        primary_intent="saas",
    )
    seo = PageSeoAudit(score=82.0)

    audit = fallback_copy_audit(page, profile, seo)
    assert audit.score is None
    assert audit.geo_score is None
    assert audit.llm_status == "skipped"
    assert audit.suggested is None
    assert audit.issues == []
    assert "seo" in audit.specialist_insights
    assert "cro" in audit.specialist_insights
    assert "clarity" in audit.specialist_insights
    blob = (audit.analysis or "").lower()
    assert "acme-analytics.io" in blob
    assert "unified data platform" in blob
    assert "fragmented tooling" not in blob
    assert "under 15 minutes" not in blob
    assert "enterprise intelligence platform" not in blob
    assert "specialist" in blob



def test_copywriting_agents_receive_cross_domain_and_trend_policy():
    """All copy specialists must use evidence-backed trends and page-level change decisions."""
    for agent_id in COPYWRITING_AGENTS_V3:
        prompt = task_card_for(agent_id)
        assert "CROSS-DOMAIN CONTEXT AND KEYWORD FRESHNESS" in prompt
        assert "NO_CHANGE_NEEDED" in prompt
        assert "INSUFFICIENT_EVIDENCE" in prompt
        assert "never invent search volume" in prompt.lower()
        assert "page-by-page" in prompt.lower()


def test_non_copywriting_agents_do_not_receive_copywriting_policy():
    prompt = task_card_for("business.discovery.v3")
    assert "CROSS-DOMAIN CONTEXT AND KEYWORD FRESHNESS" not in prompt


@pytest.mark.asyncio
async def test_page_intelligence_agent_run_handles_none_overall_score():
    from unittest.mock import AsyncMock, MagicMock
    from app.crawl.page_intelligence import PageIntelligenceAgent
    from app.cognition.blackboard import CognitiveBlackboard
    from app.domain.models import PageEvidence, PageReport

    agent = PageIntelligenceAgent(model_router=MagicMock())
    page = PageEvidence(url="https://example.com/test", title="Test Page")
    blackboard = CognitiveBlackboard(run_id="run_test", website_url="https://example.com")
    blackboard.pages = [page]

    # Mock _analyze_page returning a PageReport with overall_score=None
    mock_report = PageReport(
        url=page.url,
        page_type="general",
        title=page.title,
        overall_score=None,
    )
    agent._analyze_page = AsyncMock(return_value=mock_report)

    result = await agent.run(blackboard)
    assert result == {"page_reports": 1}
    assert len(blackboard.page_reports) == 1
    assert blackboard.page_reports[0].overall_score is None
    last_step = blackboard.execution_trace[-1]
    assert last_step["details"]["avg_score"] == 0.0


"""Live visibility labeling, CRO analytics shape, and unmeasured competitor gaps."""
from app.agents.runtime.registry import get_agent_definition
from app.agents.runtime.specialist import SpecialistAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import PageEvidence
from app.integrations.google_report import map_analytics
from app.intelligence.geo.buyer_surfaces import surfaces_not_queried
from app.intelligence.search_demand import build_search_demand


def test_buyer_surfaces_stay_unqueried_for_model_apis():
    missing = surfaces_not_queried(["ChatGPT", "Perplexity", "Gemini"])
    assert missing == ["Google AI Overviews", "Google AI Mode", "Bing Copilot"]
    assert "Google AI Overviews" not in surfaces_not_queried(["Google AI Overviews", "ChatGPT"])
    assert "Bing Copilot" not in surfaces_not_queried(["Copilot"])


def test_search_demand_is_blank_without_provider_rows():
    demand = build_search_demand({"state": "NOT_CONNECTED"})
    assert demand["status"] == "NOT_CONNECTED"
    assert demand["queries"] == []
    assert "skipped" in demand["note"]


def test_search_demand_keeps_measured_search_console_rows():
    demand = build_search_demand({
        "state": "MEASURED",
        "queries": [{"query": "widget repair", "page": "/repair", "clicks": 4, "position": 6}],
    })
    assert demand["status"] == "MEASURED"
    assert demand["sources"] == ["google_search_console"]
    assert demand["queries"][0]["source"] == "google_search_console"
    assert demand["queries"][0]["query"] == "widget repair"


def test_ga4_landing_pages_and_key_events_are_passed_through():
    channel = map_analytics({
        "state": "PAYLOAD",
        "property_id": "123",
        "payload": {
            "dimensionHeaders": [{"name": "pagePath"}],
            "metricHeaders": [{"name": "sessions"}, {"name": "conversions"}],
            "rows": [
                {"dimensionValues": [{"value": "/"}], "metricValues": [{"value": "10"}, {"value": "2"}]},
                {"dimensionValues": [{"value": "/pricing"}], "metricValues": [{"value": "4"}, {"value": "1"}]},
            ],
        },
    })
    assert channel["state"] == "MEASURED"
    assert channel["sessions"] == 14
    assert channel["key_events"] == 3
    assert channel["landing_pages"][0]["page"] == "/"
    assert channel["landing_pages"][1]["key_events"] == 1


def test_duplicate_headings_are_not_called_keyword_cannibalization():
    definition = get_agent_definition("content.cannibalization.v3")
    agent = SpecialistAgent(definition, model_router=None)
    blackboard = CognitiveBlackboard(run_id="gap", website_url="https://example.com")
    blackboard.pages = [
        PageEvidence(url="https://example.com/a", title="Same", h1=["Same offer"]),
        PageEvidence(url="https://example.com/b", title="Same", h1=["Same offer"]),
    ]
    result = agent._deterministic_audit(blackboard, [])
    statements = []
    for claim in blackboard.claim_registry.get_all():
        statements.append(getattr(claim, "statement", "") or "")
    text = " ".join(statements).lower()
    assert "keyword cannibalization" not in text
    assert "potential topical overlap" in text
    assert result["observations"]["query_level_cannibalization"] == "NOT_MEASURED"
    assert result["observations"]["query_level_status"] == "NOT_CONNECTED"

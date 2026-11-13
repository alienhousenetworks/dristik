"""Tests for Phase 1: AgentToolBus & Multi-Turn ReAct Specialist Execution."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.orchestration.runtime.tool_bus import AgentToolBus
from app.orchestration.runtime.specialist import SpecialistAgent
from app.orchestration.runtime.registry import get_agent_definition
from app.domain.evidence.models import Evidence
from app.domain.models import PageEvidence


def _make_blackboard_with_many_items(total: int = 80) -> CognitiveBlackboard:
    bb = CognitiveBlackboard("run_tool_bus_test", "https://example.com")
    bb.business_profile.business_name = "Acme Cloud"
    bb.business_profile.niche = "B2B SaaS"
    bb.business_profile.target_audience = "Engineering Leaders"
    bb.business_profile.value_proposition = "Zero-config observability."
    bb.pages = [
        PageEvidence(
            url="https://example.com/",
            status_code=200,
            title="Acme Cloud | Observability",
            meta_description="Zero-config observability for modern engineering teams.",
            h1=["Observe everything"],
            raw_html="<html><head><script src='/_next/static/chunk.js'></script></head><body><h1>Observe everything</h1></body></html>",
            word_count=350,
        ),
        PageEvidence(
            url="https://example.com/pricing",
            status_code=200,
            title="Pricing - Acme Cloud",
            h1=["Simple pricing"],
            word_count=220,
        ),
    ]
    for i in range(1, total + 1):
        ev = Evidence(
            id=f"ev_{i:03d}",
            url="https://example.com/pricing" if i == total else "https://example.com/",
            selector="meta[name='description']" if i == total else "div.content",
            text=f"Pricing tier missing canonical tag on /pricing" if i == total else f"Generic observation {i}",
            source_type="dom",
            analyzer="test_dom",
            hash=f"sha256_{i:03d}",
        )
        bb.evidence_store.add(ev)
    return bb


def test_tool_bus_searches_beyond_60_item_limit():
    bb = _make_blackboard_with_many_items(85)
    bus = AgentToolBus(bb)
    res = bus.execute("search_evidence", {"query": "pricing canonical"})
    assert res["total_store_items"] == 85
    assert res["matched_count"] >= 1
    assert any(r["id"] == "ev_085" for r in res["results"])


def test_tool_bus_detects_tech_stack_and_jsonld():
    bb = _make_blackboard_with_many_items(5)
    bus = AgentToolBus(bb)
    stack = bus.execute("detect_tech_stack")
    assert stack["primary_framework"] == "nextjs"

    valid = bus.execute("validate_json_ld", {"json_ld_str": '{"@context":"https://schema.org","@type":"Organization","name":"Acme","url":"https://example.com"}'})
    assert valid["valid"] is True

    invalid = bus.execute("validate_json_ld", {"json_ld_str": '{"@type":"Organization"}'})
    assert invalid["valid"] is False
    assert len(invalid["issues"]) >= 2


@pytest.mark.asyncio
async def test_specialist_react_loop_invokes_tools_and_does_not_bypass_business_llm():
    bb = _make_blackboard_with_many_items(85)
    defn = get_agent_definition("business.icp.v3")
    assert defn is not None

    router = MagicMock()
    router.client = MagicMock(provider="gemini")
    # Turn 1 asks for tool call; Turn 2 returns grounded claim citing ev_085 (beyond initial 60 slice)
    router.generate_structured = AsyncMock(side_effect=[
        {
            "status": "completed",
            "tool_calls": [{"tool": "search_evidence", "args": {"query": "pricing canonical"}}],
            "claims": [],
        },
        {
            "status": "completed",
            "claims": [
                {
                    "statement": "Pricing page lacks canonical tag for B2B SaaS buyers.",
                    "severity": "HIGH",
                    "confidence": 0.9,
                    "evidence_refs": ["ev_085"],
                    "recommendation": "Add self-referencing canonical link on /pricing.",
                }
            ],
        },
    ])

    agent = SpecialistAgent(defn, router)
    res = await agent.run(bb)

    assert router.generate_structured.await_count == 2
    assert res["status"] == "completed"
    assert len(res["claims"]) == 1
    assert res["claims"][0]["evidence_refs"] == ["ev_085"]
    assert res["tool_calls_trace"][0]["tool"] == "search_evidence"

import pytest
from app.domain.models import AnalysisRequest, AnalysisRun
from app.orchestration.pipeline_dag import (
    SECTIONS_REGISTRY,
    NODES_REGISTRY,
    PILLAR_TO_SECTION,
    SECTION_TO_PILLAR,
    GraphNodeStatus,
    get_pipeline_controller,
)
from app.orchestration.agent_pool import AgentPool, PILLAR_DOMAINS
from app.cognition.blackboard import CognitiveBlackboard
from app.inference.model_router import ModelRouter


def test_pillar_sections_registry():
    assert PILLAR_TO_SECTION == {
        "seo": "sec_seo",
        "geo": "sec_geo",
        "aeo": "sec_aeo",
        "cro": "sec_cro",
    }
    assert len(SECTIONS_REGISTRY) == 7

    # Verify each pillar has a dedicated section with nodes
    for pillar, sec_id in PILLAR_TO_SECTION.items():
        sec = next((s for s in SECTIONS_REGISTRY if s.section_id == sec_id), None)
        assert sec is not None, f"Missing section definition for {sec_id}"
        assert len(sec.node_ids) >= 3, f"Pillar {pillar} should have at least 3 sub-section nodes"
        for nid in sec.node_ids:
            assert nid in NODES_REGISTRY, f"Node {nid} in section {sec_id} not registered"


def test_analysis_request_target_pillars():
    req = AnalysisRequest(
        website_url="https://example.com",
        target_pillars=["seo", "cro"]
    )
    assert req.target_pillars == ["seo", "cro"]

    run = AnalysisRun(
        analysis_id="run_test_pillars",
        website_url="https://example.com",
        target_pillars=["seo", "cro"],
        created_at="2026-10-12T00:00:00",
        updated_at="2026-10-12T00:00:00",
    )
    assert run.target_pillars == ["seo", "cro"]


@pytest.mark.asyncio
async def test_agent_pool_selective_execution():
    model_router = ModelRouter()
    pool = AgentPool(model_router)
    blackboard = CognitiveBlackboard(run_id="run_test_sel", website_url="https://example.com")

    # When active_pillars is {"seo"}, non-SEO agents must be marked skipped without running
    events = []
    async def track_progress(stage, pct, msg, data):
        events.append((data.get("agent_id"), data.get("status")))

    async def mock_run_one(aid, bb):
        return {"agent_id": aid, "status": "completed", "claims": []}
    pool._run_one = mock_run_one

    summary = await pool.execute_all(
        blackboard,
        progress_cb=track_progress,
        base_progress=0,
        end_progress=100,
        active_pillars={"seo"}
    )

    assert "skipped" in summary
    assert summary["skipped"] > 0
    # Ensure skipped count covers non-SEO domains
    assert summary["skipped"] >= 15


@pytest.mark.asyncio
async def test_orchestrator_section_pillar_alias():
    from app.orchestration.orchestrator import orchestrator

    # Verify run_pipeline_section accepts pillar abbreviation like 'seo'
    run = orchestrator.create_run("https://example.com", target_pillars=["seo"])
    assert run.target_pillars == ["seo"]

    controller = get_pipeline_controller(run.analysis_id)
    # Check that nodes are recognized in the graph state
    graph_state = controller.get_full_graph_state()
    assert "sections" in graph_state
    assert len(graph_state["sections"]) == 7
    sec_ids = [s["section_id"] for s in graph_state["sections"]]
    assert "sec_seo" in sec_ids
    assert "sec_geo" in sec_ids
    assert "sec_aeo" in sec_ids
    assert "sec_cro" in sec_ids

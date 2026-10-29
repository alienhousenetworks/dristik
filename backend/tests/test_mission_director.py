"""
Tests for Phase 1: MissionDirector, StateGraph Engine, and Dynamic Workforce.
"""
import pytest
from app.mission.director import MissionDirector
from app.mission.graph import StateGraph, START, END
from app.mission.state import MissionState
from app.domain.enums import AnalysisStage
from app.inference.model_router import ModelRouter
from app.orchestration.team_orchestrator import TeamOrchestrator

@pytest.mark.asyncio
async def test_mission_director_decomposition():
    director = MissionDirector()
    mission = director.create_mission(
        target_url="https://example.com",
        audit_type="deep_enterprise",
        industry="saas",
        max_pages=15
    )

    assert mission.mission_id.startswith("msn_")
    assert mission.target.domain == "example.com"
    assert mission.objective.depth == 3
    assert mission.budget.policy == "ENTERPRISE"
    assert mission.objective.max_pages == 15

    caps = director.select_capabilities_for_mission(mission, site_type="saas")
    assert len(caps["tier_1_deterministic"]) >= 10
    assert "16_competitive_differentiation" in caps["tier_2_business"]
    assert "26_ai_discoverability" in caps["tier_3_specialists"]
    assert "35_contradiction_resolution" in caps["tier_4_verification"]

@pytest.mark.asyncio
async def test_state_graph_execution_flow():
    graph = StateGraph()

    async def step_one(state: MissionState):
        state.status = AnalysisStage.INGESTING
        return {"current_node": "step_one"}

    async def step_two(state: MissionState):
        state.status = AnalysisStage.COMPLETED
        return {"current_node": "step_two"}

    graph.add_node("step_one", step_one)
    graph.add_node("step_two", step_two)
    graph.add_edge("step_one", "step_two")
    graph.add_edge("step_two", END)
    graph.set_entry_point("step_one")

    compiled = graph.compile()
    director = MissionDirector()
    initial_state = director.create_mission("https://test.com")

    final_state = await compiled.astream(initial_state)
    assert final_state.status == AnalysisStage.COMPLETED
    assert len(final_state.events) >= 4

@pytest.mark.asyncio
async def test_team_orchestrator_initialization():
    router = ModelRouter()
    team = TeamOrchestrator(router)
    assert team.worker_extractor is not None
    assert team.worker_strategist is not None
    assert team.worker_simulator is not None
    assert team.worker_remediation is not None

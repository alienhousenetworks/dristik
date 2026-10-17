"""The pillar registry and the specialist dependency order import cleanly."""
from app.orchestration.dependency_resolver import topological_waves
from app.orchestration.execution_manager import AnalysisOrchestrator, orchestrator
from app.pillars import list_pillars


def test_seven_pillars_and_execution_manager():
    assert len(list_pillars()) == 7
    assert isinstance(orchestrator, AnalysisOrchestrator)
    assert callable(topological_waves)

"""Pipeline orchestration, mission control, runtime agents, DAG planner, and cognitive reasoning engine."""
import sys
from app.orchestration import mission
from app.orchestration.mission import director, graph, policies, state, state_machine
from app.orchestration import cognition
from app.orchestration.cognition import (
    blackboard,
    causal,
    claims,
    confidence,
    consensus,
    context_manager,
    contradiction,
    contradiction_engine,
    decision_engine,
    finding_registry,
    finding_rubric,
    ground_truth,
    hypotheses,
    memory,
    report_critic,
)

sys.modules["app.mission"] = mission
sys.modules["app.mission.director"] = director
sys.modules["app.mission.graph"] = graph
sys.modules["app.mission.policies"] = policies
sys.modules["app.mission.state"] = state
sys.modules["app.mission.state_machine"] = state_machine

sys.modules["app.cognition"] = cognition
sys.modules["app.cognition.blackboard"] = blackboard
sys.modules["app.cognition.causal"] = causal
sys.modules["app.cognition.claims"] = claims
sys.modules["app.cognition.confidence"] = confidence
sys.modules["app.cognition.consensus"] = consensus
sys.modules["app.cognition.context_manager"] = context_manager
sys.modules["app.cognition.contradiction"] = contradiction
sys.modules["app.cognition.contradiction_engine"] = contradiction_engine
sys.modules["app.cognition.decision_engine"] = decision_engine
sys.modules["app.cognition.finding_registry"] = finding_registry
sys.modules["app.cognition.finding_rubric"] = finding_rubric
sys.modules["app.cognition.ground_truth"] = ground_truth
sys.modules["app.cognition.hypotheses"] = hypotheses
sys.modules["app.cognition.memory"] = memory
sys.modules["app.cognition.report_critic"] = report_critic

__all__ = ["mission", "cognition"]

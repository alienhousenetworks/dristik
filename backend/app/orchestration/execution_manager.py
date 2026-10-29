"""Execution entry point for a full analysis run."""
from app.orchestration.orchestrator import AnalysisOrchestrator, orchestrator

ExecutionManager = AnalysisOrchestrator

__all__ = ["AnalysisOrchestrator", "ExecutionManager", "orchestrator"]

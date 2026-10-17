"""Run context around the cognitive blackboard."""
from __future__ import annotations

from typing import Any, Dict

from app.orchestration.cognition.blackboard import CognitiveBlackboard


class ContextManager:
    def __init__(self, blackboard: CognitiveBlackboard):
        self.blackboard = blackboard

    @property
    def run_id(self) -> str:
        return self.blackboard.run_id

    @property
    def website_url(self) -> str:
        return self.blackboard.website_url

    def log(self, step_name: str, agent_id: str, details: Dict[str, Any] | None = None) -> None:
        self.blackboard.log_step(step_name, agent_id, details or {})

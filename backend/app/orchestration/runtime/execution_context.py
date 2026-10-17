"""Per-wave inputs shared by pillar execution.

The context points at the live blackboard. It does not copy findings or scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Set

from app.cognition.blackboard import CognitiveBlackboard


@dataclass
class ExecutionContext:
    run_id: str
    website_url: str
    blackboard: CognitiveBlackboard
    wave_index: int = 0
    active_agents: Set[str] = field(default_factory=set)
    model_router: Any = None

    @classmethod
    def from_blackboard(
        cls,
        blackboard: CognitiveBlackboard,
        *,
        wave_index: int = 0,
        active_agents: Optional[Set[str]] = None,
        model_router: Any = None,
    ) -> "ExecutionContext":
        return cls(
            run_id=blackboard.run_id,
            website_url=blackboard.website_url,
            blackboard=blackboard,
            wave_index=wave_index,
            active_agents=set(active_agents or ()),
            model_router=model_router,
        )

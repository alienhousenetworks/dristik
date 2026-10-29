"""Public pillar contracts.

The protocol and score result stay defined on app.domain.pillar. This module
is the import path for those contracts plus the execution request.
"""
from __future__ import annotations

from typing import List, Set

from pydantic import BaseModel, Field

from app.domain.pillar import DomainPillar, PillarId, PillarScoreResult

__all__ = [
    "DomainPillar",
    "PillarExecutionRequest",
    "PillarId",
    "PillarScoreResult",
]


class PillarExecutionRequest(BaseModel):
    pillar_id: PillarId
    wave_index: int = 0
    active_agents: List[str] = Field(default_factory=list)

    def active_agent_set(self) -> Set[str]:
        return set(self.active_agents)

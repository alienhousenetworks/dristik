"""
Dristik Domain Pillar Protocol and Registry Contracts.

Defines the formal contracts and protocols for domain pillars:
- Crawling & Discovery
- SEO (Technical, Structured Data, Content, Linking)
- GEO (Generative Engine Optimization, AI Citations, Share-of-Model)
- AEO (Answer Engine Optimization, Direct Answers, Entity Consensus)
- CRO (Conversion Rate Optimization, Visual UX, Friction)
- Remediation (Diffs, AST Patches, Rollback)
- Reporting (Audit Books, PDF/HTML generation)
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Set, TYPE_CHECKING, runtime_checkable
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.domain.models import Finding


class PillarId(str, Enum):
    CRAWLING = "crawling"
    SEO = "seo"
    GEO = "geo"
    AEO = "aeo"
    CRO = "cro"
    REMEDIATION = "remediation"
    REPORTING = "reporting"


class PillarScoreResult(BaseModel):
    pillar_id: PillarId
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    grade: str = Field(default="C")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    measured_findings_count: int = Field(default=0)
    metrics: Dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class DomainPillar(Protocol):
    """Protocol for modular domain pillars."""
    pillar_id: PillarId
    domains: Set[str]

    async def execute_wave(
        self,
        wave_index: int,
        blackboard: CognitiveBlackboard,
        active_agents: Set[str],
    ) -> List[Finding]:
        """Execute agents belonging to this pillar for a given DAG wave."""
        ...

    def calculate_pillar_score(
        self,
        findings: List[Finding],
        blackboard: Optional[CognitiveBlackboard] = None,
    ) -> PillarScoreResult:
        """Deterministic score calibration for this domain."""
        ...

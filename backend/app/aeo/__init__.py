"""
Dristik Modular Monolith: Answer Engine Optimization (AEO) Domain.
"""
from app.aeo.pillar import AeoPillar
from app.aeo.specialists import AEO_SPECIALISTS, build_aeo_agents
from app.aeo.agents import (
    DirectAnswerAgent,
    ConversationalIntentAgent,
    EntityConsensusAgent,
)
from app.aeo.contracts import (
    MeasurementMode,
    ClaimSupportStatus,
    NormalizedEvidenceRecord,
    SharedResultEnvelope,
    QuestionSuite,
    QuestionIntent,
    UnifiedQuestionDefinition,
    QuestionRegistry,
)
from app.aeo.analysis import (
    AssessedClaim,
    ClaimGroundingEvaluation,
    ClaimGroundingEvaluator,
    ApprovalStatus,
    VerificationStatus,
    RemediationProposal,
    RemediationPlanner,
)

__all__ = [
    "AeoPillar",
    "AEO_SPECIALISTS",
    "build_aeo_agents",
    "DirectAnswerAgent",
    "ConversationalIntentAgent",
    "EntityConsensusAgent",
    "MeasurementMode",
    "ClaimSupportStatus",
    "NormalizedEvidenceRecord",
    "SharedResultEnvelope",
    "QuestionSuite",
    "QuestionIntent",
    "UnifiedQuestionDefinition",
    "QuestionRegistry",
    "AssessedClaim",
    "ClaimGroundingEvaluation",
    "ClaimGroundingEvaluator",
    "ApprovalStatus",
    "VerificationStatus",
    "RemediationProposal",
    "RemediationPlanner",
]

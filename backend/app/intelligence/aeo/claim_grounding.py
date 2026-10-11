"""
Dristik AEO Claim Grounding & Verification.

Computes transparent, defensible claim support ratios:
  Claim Support Ratio = (Supported Claims / All Assessable Claims) * 100

Does not treat opaque LLM confidence as a grounding ratio.
Unassessable claims are reported separately.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.intelligence.aeo.measurement_contracts import ClaimSupportStatus
from app.intelligence.knowledge.primitives import KieAnswerRisk


class AssessedClaim(BaseModel):
    claim_text: str
    status: ClaimSupportStatus
    confidence: float = 0.0
    evidence_snippet: Optional[str] = None
    evidence_url: Optional[str] = None
    section_heading: Optional[str] = None
    is_assessable: bool = True
    assessment_notes: Optional[str] = None


class ClaimGroundingEvaluation(BaseModel):
    question_id: str
    total_claims: int = 0
    assessable_claims: int = 0
    supported_claims: int = 0
    partially_supported_claims: int = 0
    unsupported_claims: int = 0
    contradicted_claims: int = 0
    unassessable_claims: int = 0
    claim_support_ratio_pct: float = 0.0
    answer_risk: KieAnswerRisk = KieAnswerRisk.HIGH
    abstained: bool = False
    abstention_reason: Optional[str] = None
    claims: List[AssessedClaim] = Field(default_factory=list)


class ClaimGroundingEvaluator:
    """Evaluates synthesized candidate answers against verified evidence chunks."""

    @staticmethod
    def evaluate(
        question_id: str,
        claims: List[AssessedClaim],
        abstained: bool = False,
        abstention_reason: Optional[str] = None,
    ) -> ClaimGroundingEvaluation:
        if abstained or not claims:
            return ClaimGroundingEvaluation(
                question_id=question_id,
                total_claims=len(claims),
                assessable_claims=0,
                supported_claims=0,
                partially_supported_claims=0,
                unsupported_claims=0,
                contradicted_claims=0,
                unassessable_claims=len(claims),
                claim_support_ratio_pct=0.0,
                answer_risk=KieAnswerRisk.HIGH,
                abstained=True,
                abstention_reason=abstention_reason or "No first-party evidence discovered in crawled pages.",
                claims=claims,
            )

        assessable = [c for c in claims if c.is_assessable]
        unassessable_count = len(claims) - len(assessable)

        supported = sum(1 for c in assessable if c.status == ClaimSupportStatus.SUPPORTED)
        partial = sum(1 for c in assessable if c.status == ClaimSupportStatus.PARTIALLY_SUPPORTED)
        unsupported = sum(1 for c in assessable if c.status == ClaimSupportStatus.UNSUPPORTED)
        contradicted = sum(1 for c in assessable if c.status == ClaimSupportStatus.CONTRADICTED)

        denom = max(1, len(assessable))
        # Supported counts fully (1.0), partial counts as half (0.5)
        ratio = round(((supported + (0.5 * partial)) / denom) * 100.0, 1)

        # Answer risk classification
        if contradicted > 0 or unsupported >= 1 or ratio < 50.0:
            risk = KieAnswerRisk.HIGH
        elif partial > 0 or ratio < 75.0 or unassessable_count > 0:
            risk = KieAnswerRisk.MEDIUM
        else:
            risk = KieAnswerRisk.LOW

        return ClaimGroundingEvaluation(
            question_id=question_id,
            total_claims=len(claims),
            assessable_claims=len(assessable),
            supported_claims=supported,
            partially_supported_claims=partial,
            unsupported_claims=unsupported,
            contradicted_claims=contradicted,
            unassessable_claims=unassessable_count,
            claim_support_ratio_pct=ratio,
            answer_risk=risk,
            abstained=False,
            abstention_reason=None,
            claims=claims,
        )

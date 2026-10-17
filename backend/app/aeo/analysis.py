"""
Dristik Modular Monolith: AEO Claim Grounding & Evidence-Based Remediation.

Combines:
1. Transparent claim support ratio calculations and answer risk classification.
2. Evidence-grounded remediation proposals with strict anti-fabrication gates
   (business owner confirmation required for pricing, SLA, and compliance claims).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.aeo.contracts import ClaimSupportStatus
from app.crawl.knowledge.primitives import KieAnswerRisk


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


ApprovalStatus = Literal["PROPOSED", "APPROVED", "REJECTED", "IMPLEMENTED"]
VerificationStatus = Literal["UNVERIFIED", "VERIFIED_ON_PAGE", "VERIFIED_LIVE"]


class RemediationProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: f"REM-{uuid.uuid4().hex[:8].upper()}")
    question_id: str
    target_page: str
    target_section: str
    content_gap: str
    requires_owner_confirmation: bool = False
    owner_confirmation_brief: Optional[str] = None
    recommended_patch_text: str
    approval_status: ApprovalStatus = "PROPOSED"
    verification_status: VerificationStatus = "UNVERIFIED"
    observed_evidence_ids: List[str] = Field(default_factory=list)


class RemediationPlanner:
    """Generates remediation proposals with strict anti-fabrication gates."""

    @staticmethod
    def create_proposal(
        question_id: str,
        target_page: str,
        target_section: str,
        content_gap: str,
        intent: str,
        evidence_ids: Optional[List[str]] = None,
        observed_facts: Optional[List[str]] = None,
    ) -> RemediationProposal:
        # Facts requiring authoritative confirmation if absent
        sensitive_intents = {"COMMERCIAL", "COMPLIANCE", "TECHNICAL"}
        requires_confirmation = intent.upper() in sensitive_intents or any(
            kw in content_gap.lower() for kw in ["pricing", "cost", "soc 2", "iso 27001", "sla", "uptime", "refund"]
        )

        if requires_confirmation:
            brief = (
                f"Business owner must confirm authoritative values for '{content_gap}'. "
                "Do not publish placeholder prices, uncertified compliance badges, or unverified SLAs."
            )
            patch = (
                f"Publish verified {content_gap.lower()} on {target_page} under {target_section}. "
                "Include canonical documentation and structured table/FAQ markup once confirmed."
            )
        else:
            brief = None
            patch = (
                f"Update {target_page} under section '{target_section}': {content_gap}. "
                "Ensure factual, machine-extractable sentences without marketing fluff."
            )

        return RemediationProposal(
            question_id=question_id,
            target_page=target_page,
            target_section=target_section,
            content_gap=content_gap,
            requires_owner_confirmation=requires_confirmation,
            owner_confirmation_brief=brief,
            recommended_patch_text=patch,
            observed_evidence_ids=evidence_ids or [],
        )


__all__ = [
    "AssessedClaim",
    "ClaimGroundingEvaluation",
    "ClaimGroundingEvaluator",
    "ApprovalStatus",
    "VerificationStatus",
    "RemediationProposal",
    "RemediationPlanner",
]

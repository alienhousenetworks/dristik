"""
Dristik AEO Evidence-Based Remediation.

Generates actionable content proposals tied directly to verified evidence gaps.
Zero Fabricated Facts: Missing pricing, compliance certifications, SLAs, or technical specs
trigger an explicit owner confirmation request rather than inventing plausible values.
"""
from __future__ import annotations

import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


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

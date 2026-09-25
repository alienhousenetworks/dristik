"""
Dristik AI Orchestrator Integrity Gate (Zero-Fake Evidence Enforcement)
Validates all agent claims, evidence references, and live evaluation provenance
before scoring and executive synthesis.
"""
from typing import List, Dict, Any, Optional, Set
import logging
from pydantic import BaseModel, Field

from app.domain.models import Claim
from app.domain.enums import ClaimType, SourceIntegrityLabel, VerificationStatus
from app.evidence.store import EvidenceStore
from app.cognition.ground_truth import apply_ground_truth_feed

logger = logging.getLogger("dristik.orchestration.integrity_gate")

class IntegrityViolation(BaseModel):
    agent_id: str
    claim_id: Optional[str] = None
    violation_type: str
    description: str
    action_taken: str

class IntegrityValidationResult(BaseModel):
    is_valid: bool = True
    total_claims_inspected: int = 0
    claims_passed: int = 0
    claims_adjusted: int = 0
    dangling_refs_removed: int = 0
    violations: List[IntegrityViolation] = Field(default_factory=list)

class EvidenceIntegrityValidator:
    """
    Guarantees that no unsubstantiated, fabricated, or dangling claims
    pass through to decision synthesis or customer-facing reports.
    """

    def validate_claims_and_evidence(
        self,
        claims: List[Claim],
        evidence_store: EvidenceStore,
        claim_registry=None,
    ) -> IntegrityValidationResult:
        result = IntegrityValidationResult(
            total_claims_inspected=len(claims)
        )

        all_evidence_ids: Set[str] = set()
        if evidence_store:
            for ev in evidence_store.get_all():
                all_evidence_ids.add(ev.id)

        for claim in claims:
            adjusted = False

            # 1. Validate evidence_refs existence
            if claim.evidence_refs:
                valid_refs = []
                for ref in claim.evidence_refs:
                    if ref in all_evidence_ids:
                        valid_refs.append(ref)
                    else:
                        result.dangling_refs_removed += 1
                        result.violations.append(IntegrityViolation(
                            agent_id=claim.agent_id,
                            claim_id=claim.id,
                            violation_type="DANGLING_EVIDENCE_REFERENCE",
                            description=f"Claim referenced evidence id '{ref}' which does not exist in the EvidenceStore.",
                            action_taken="Removed dangling reference from claim."
                        ))
                        adjusted = True

                claim.evidence_refs = valid_refs

            # 2. Check claim type vs evidence backing
            if claim.claim_type == ClaimType.FACT and not claim.evidence_refs:
                # A factual claim with zero evidence backing cannot remain FACT with high confidence
                if claim.confidence and claim.confidence > 0.60:
                    claim.confidence = 0.50
                    result.violations.append(IntegrityViolation(
                        agent_id=claim.agent_id,
                        claim_id=claim.id,
                        violation_type="UNBACKED_FACTUAL_CLAIM",
                        description=f"Claim '{claim.statement[:60]}' marked FACT has 0 evidence references.",
                        action_taken="Downgraded confidence to 0.50."
                    ))
                    adjusted = True

            # 3. Check for banned mock/synthetic markers in claim statement or recommendation
            text_to_scan = f"{claim.statement} {claim.recommendation or ''}".lower()
            banned_markers = ["order_mock_", "mock_sig_", "pay_mock_", "fake_", "simulated real data"]
            for marker in banned_markers:
                if marker in text_to_scan:
                    result.violations.append(IntegrityViolation(
                        agent_id=claim.agent_id,
                        claim_id=claim.id,
                        violation_type="SYNTHETIC_MARKER_DETECTED",
                        description=f"Claim contains banned synthetic token '{marker}'.",
                        action_taken="Flagged integrity violation."
                    ))
                    result.is_valid = False

            if adjusted:
                result.claims_adjusted += 1
            else:
                result.claims_passed += 1

        # v4: bind ICP/pricing/performance/trust/authorship claims to ext_xxx
        apply_ground_truth_feed(claims, evidence_store, registry=claim_registry)
        for claim in claims:
            if claim.source_integrity_label == SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED:
                result.violations.append(IntegrityViolation(
                    agent_id=claim.agent_id,
                    claim_id=claim.id,
                    violation_type="SINGLE_SOURCE_UNVERIFIED",
                    description=f"Claim about {claim.claim_family.value if claim.claim_family else 'gated topic'} rests on DOM (ev_xxx) only; no usable ext_xxx.",
                    action_taken="Labeled SINGLE_SOURCE_UNVERIFIED; confidence capped at MEDIUM.",
                ))
                result.claims_adjusted += 1
            elif claim.source_integrity_label == SourceIntegrityLabel.CONTESTED:
                result.violations.append(IntegrityViolation(
                    agent_id=claim.agent_id,
                    claim_id=claim.id,
                    violation_type="FLAGGED_UNVERIFIED",
                    description=f"External feed contradicts DOM for {claim.claim_family.value if claim.claim_family else 'gated topic'}.",
                    action_taken="Status CONTESTED; cited ev_xxx and ext_xxx; routed to verification.contradiction.v3; winner not selected.",
                ))
                if claim.verification_status != VerificationStatus.CONTESTED:
                    claim.verification_status = VerificationStatus.CONTESTED
                result.claims_adjusted += 1

        if result.violations:
            logger.info(
                f"[IntegrityGate] Inspected {result.total_claims_inspected} claims: "
                f"{len(result.violations)} violations detected, "
                f"{result.dangling_refs_removed} dangling refs purged."
            )

        return result

integrity_gate = EvidenceIntegrityValidator()

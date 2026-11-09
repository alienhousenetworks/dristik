"""
Dristik AI Canonical Semantic Evidence Validator
Validates that claims, findings, and statements have genuine, traceable,
and semantically congruent supporting evidence. Enforces Audit 1 standards.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
import re
from datetime import datetime, timezone

from app.domain.models import Claim, Finding, PageEvidence
from app.domain.enums import (
    VerificationStatus,
    ClaimType,
    ClaimSourceType,
    Severity,
    ProvenanceType,
    CollectionStatus,
)
from app.domain.evidence.models import Evidence
from app.domain.evidence.store import EvidenceStore


@dataclass
class ClaimValidationResult:
    is_valid: bool
    claim_id: str
    status: VerificationStatus
    issues: List[str] = field(default_factory=list)
    downgraded_to_inferred: bool = False
    rejection_reason: Optional[str] = None
    valid_evidence_ids: List[str] = field(default_factory=list)


class SemanticEvidenceValidator:
    """
    Validates claim-level and finding-level evidence support.
    Enforces that evidence references actually substantiate the claim.
    """

    def __init__(self, run_id: str, store: EvidenceStore):
        self.run_id = run_id
        self.store = store

    def validate_claim(self, claim: Claim) -> ClaimValidationResult:
        claim_id = getattr(claim, "claim_id", None) or getattr(claim, "id", "CLM_UNKNOWN")
        statement = getattr(claim, "claim_text", None) or getattr(claim, "statement", "")
        raw_refs = getattr(claim, "evidence_refs", []) or []
        stmt_lower = statement.lower()

        issues: List[str] = []
        valid_refs: List[str] = []

        # 1. Existence and Cross-Run Reference Check
        cross_run_detected = False
        for ref_id in raw_refs:
            ev = self.store.get(ref_id) or self.store.get_observation(ref_id)
            if not ev:
                issues.append(f"Referenced evidence ID '{ref_id}' does not exist in store.")
                continue

            # Verify audit_run_id matches if present
            ev_run_id = getattr(ev, "audit_run_id", None)
            claim_run_id = getattr(claim, "audit_run_id", None) or self.run_id
            if ev_run_id and claim_run_id and ev_run_id != claim_run_id:
                issues.append(f"Evidence '{ref_id}' belongs to another audit run ({ev_run_id} != {claim_run_id}).")
                cross_run_detected = True
                continue

            valid_refs.append(ref_id)

        if cross_run_detected:
            return ClaimValidationResult(
                is_valid=False,
                claim_id=claim_id,
                status=VerificationStatus.REJECTED,
                issues=issues,
                downgraded_to_inferred=False,
                rejection_reason="Evidence belongs to another audit run.",
                valid_evidence_ids=[],
            )

        # 2. Evidence Requirement for Factual / Observed Claims
        claim_type_str = str(getattr(claim, "claim_type", "")).upper()
        is_factual = any(k in claim_type_str for k in ["OBSERVED", "MEASURED", "FACT"])

        if is_factual and not valid_refs:
            # Cannot assert direct empirical observation with zero backing evidence
            return ClaimValidationResult(
                is_valid=False,
                claim_id=claim_id,
                status=VerificationStatus.UNSUPPORTED,
                issues=["Factual/Observed claim has no valid supporting evidence."],
                downgraded_to_inferred=False,
                rejection_reason="Factual claim lacks traceable Layer 1 evidence.",
                valid_evidence_ids=[],
            )

        # 3. Semantic Grounding & Contradiction Check
        for ref_id in valid_refs:
            ev = self.store.get(ref_id) or self.store.get_observation(ref_id)
            if not ev:
                continue

            # Check collection status
            col_status = getattr(ev, "collection_status", CollectionStatus.SUCCESS)
            if col_status in (CollectionStatus.UNAVAILABLE, CollectionStatus.FAILED, CollectionStatus.NOT_TESTED):
                # An unavailable check cannot support a confirmed positive or negative factual claim
                if "confirmed" in stmt_lower or "is working" in stmt_lower or "failed" in stmt_lower:
                    issues.append(f"Evidence '{ref_id}' status is {col_status.value}; cannot assert confirmed outcome.")

            # Check numeric and technical token consistency
            # If claim asserts a specific HTTP code, evidence must match
            http_claim_match = re.search(r"\bhttp\s*(\d{3})\b", stmt_lower)
            if http_claim_match:
                claimed_code = int(http_claim_match.group(1))
                ev_status = getattr(ev, "response_status", None)
                if ev_status is None and hasattr(ev, "metadata") and isinstance(ev.metadata, dict):
                    ev_status = ev.metadata.get("response_status")
                if ev_status is None and str(getattr(ev, "attribute", "")) in ("status_code", "http_status"):
                    try:
                        ev_status = int(ev.value)
                    except (ValueError, TypeError):
                        pass
                if ev_status is None and getattr(ev, "analyzer", "") == "layer1_http":
                    try:
                        ev_status = int(ev.value)
                    except (ValueError, TypeError):
                        pass
                if ev_status is not None and ev_status != claimed_code:
                    issues.append(f"Claim asserts HTTP {claimed_code} but evidence '{ref_id}' records HTTP {ev_status}.")

            # If claim asserts site is down but evidence is 200 OK
            if any(k in stmt_lower for k in ["site is down", "completely unreachable", "100% down"]):
                ev_val = str(getattr(ev, "value", ""))
                ev_text = str(getattr(ev, "text", ""))
                if "200" in ev_val or "200" in ev_text:
                    issues.append(f"Claim asserts site down but evidence '{ref_id}' shows 200 OK.")

            # Scope check
            claim_scope = getattr(claim, "scope", None)
            ev_scope = getattr(ev, "scope", None) or getattr(ev, "url", None)
            if claim_scope and ev_scope and claim_scope.startswith("http") and ev_scope.startswith("http"):
                # URL level scope mismatch
                if claim_scope.rstrip("/") != ev_scope.rstrip("/"):
                    issues.append(f"Scope mismatch: claim scoped to {claim_scope} but evidence collected from {ev_scope}.")

        # 4. Result Formulation
        if issues:
            # Check if fatal
            fatal_errors = [i for i in issues if "another audit run" in i or "site down but evidence" in i or "HTTP" in i]
            if fatal_errors:
                return ClaimValidationResult(
                    is_valid=False,
                    claim_id=claim_id,
                    status=VerificationStatus.REJECTED,
                    issues=issues,
                    downgraded_to_inferred=False,
                    rejection_reason="; ".join(fatal_errors),
                    valid_evidence_ids=valid_refs,
                )
            else:
                # Downgrade to INFERRED
                return ClaimValidationResult(
                    is_valid=True,
                    claim_id=claim_id,
                    status=VerificationStatus.PARTIALLY_VERIFIED,
                    issues=issues,
                    downgraded_to_inferred=True,
                    rejection_reason=None,
                    valid_evidence_ids=valid_refs,
                )

        return ClaimValidationResult(
            is_valid=True,
            claim_id=claim_id,
            status=VerificationStatus.VERIFIED,
            issues=[],
            downgraded_to_inferred=False,
            rejection_reason=None,
            valid_evidence_ids=valid_refs,
        )

    def validate_finding(self, finding: Finding) -> Tuple[bool, List[str]]:
        """
        Validates that a finding is grounded in empirical evidence and not manufactured.
        """
        reasons: List[str] = []
        raw_refs = getattr(finding, "evidence_ids", None) or getattr(finding, "evidence_refs", None) or []
        
        if not raw_refs:
            reasons.append(f"Finding '{finding.title}' has no evidence_refs.")
            return False, reasons

        valid_refs = []
        for ref in raw_refs:
            ev = self.store.get(ref) or self.store.get_observation(ref)
            if not ev:
                reasons.append(f"Finding '{finding.title}' references nonexistent evidence '{ref}'.")
                continue
            ev_run_id = getattr(ev, "audit_run_id", None)
            if ev_run_id and self.run_id and ev_run_id != self.run_id:
                reasons.append(f"Finding '{finding.title}' references evidence '{ref}' from another audit ({ev_run_id}).")
                continue
            valid_refs.append(ref)

        if not valid_refs:
            reasons.append(f"Finding '{finding.title}' has zero surviving valid evidence records.")
            return False, reasons

        # Check that recommendation is grounded
        rec = getattr(finding, "recommendation", "") or ""
        if getattr(finding, "grounded_recommendation", None):
            rec = f"{rec} {finding.grounded_recommendation.what_to_change}"

        rec_lower = rec.lower()
        # Disallow irrelevant or hallucinated infrastructure recommendations
        for banned_phrase in [
            "install redis cluster",
            "upgrade to aws aurora",
            "configure kubernetes ingress",
            "purchase ahrefs subscription",
        ]:
            if banned_phrase in rec_lower:
                reasons.append(f"Finding contains irrelevant unevidenced infrastructure advice: '{banned_phrase}'.")

        return (len(reasons) == 0), reasons

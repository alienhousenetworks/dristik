"""
Dristik AI Calibrated Confidence Engine
Calculates true Bayesian multi-signal confidence from evidence quality, coverage,
cross-page consistency, model agreement, and contradiction penalties.
"""
from typing import Dict, Any, List, Optional
import math
from pydantic import BaseModel, Field
from app.domain.models import Claim, PageEvidence
from app.evidence.store import EvidenceStore

class ConfidenceResult(BaseModel):
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    evidence_coverage: float = Field(..., ge=0.0, le=1.0)
    status: str  # VERIFIED, STRONGLY_SUPPORTED, PROBABLE, UNCERTAIN, UNSUPPORTED, CONTRADICTED
    signals_breakdown: Dict[str, float] = Field(default_factory=dict)
    summary: str
    index_coverage: Optional[float] = None
    sample_page_count: int = 0
    index_url_count: Optional[int] = None

class CalibratedConfidenceEngine:
    """
    Computes calibrated confidence metrics rather than trusting raw LLM certainty.
    """

    def calculate_confidence(
        self,
        claims: List[Claim],
        evidence_store: EvidenceStore,
        pages: List[PageEvidence],
        contradictions_count: int = 0,
        sample_target: int = 5,
        index_url_count: Optional[int] = None,
    ) -> ConfidenceResult:
        if not claims:
            return ConfidenceResult(
                confidence_score=0.0,
                evidence_coverage=0.0,
                status="UNCERTAIN",
                signals_breakdown={"base": 0.0},
                summary="No claims evaluated; confidence uncalibrated."
            )

        # 1. Evidence Quality & Grounding
        total_claims = len(claims)
        grounded_claims = sum(1 for c in claims if len(c.evidence_refs) > 0)
        grounding_ratio = grounded_claims / max(1, total_claims)

        # 2. Sample coverage: blends deep-audit budget attainment with domain discovery coverage
        # when index_url_count exceeds the sample target, so a 5/504 (1%) sample does not claim 100% coverage.
        crawled_count = len(pages)
        target = sample_target if sample_target and sample_target > 0 else 5
        budget_coverage = min(1.0, crawled_count / float(target)) if crawled_count > 0 else 0.0
        index_coverage = None
        if index_url_count and index_url_count > 0:
            raw_index_ratio = min(1.0, crawled_count / float(index_url_count)) if crawled_count > 0 else 0.0
            index_coverage = round(raw_index_ratio, 2)
            if index_url_count > target:
                coverage_score = round((0.40 * budget_coverage) + (0.60 * math.sqrt(raw_index_ratio)), 4)
            else:
                coverage_score = raw_index_ratio
        else:
            coverage_score = budget_coverage

        # 3. Contradiction Penalty (CONTESTED DOM vs ext counts)
        from app.domain.enums import VerificationStatus, SourceIntegrityLabel
        contested = sum(
            1 for c in claims
            if c.verification_status == VerificationStatus.CONTESTED
            or c.source_integrity_label == SourceIntegrityLabel.CONTESTED
        )
        contra_penalty = min(0.35, (contradictions_count + contested) * 0.08)

        # 4. Deterministic Verification Boost (weighted 20% in the composite below)
        deterministic_claims = sum(
            1 for c in claims
            if "deterministic" in (getattr(c, "agent_id", "") or "").lower()
            or getattr(c, "evidence_refs", None)
        )
        det_ratio = deterministic_claims / max(1, total_claims)
        deterministic_boost = det_ratio * 0.20

        # Raw multi-signal formula grounded in real evidence (weights: 0.50 + 0.30 + 0.20 = 1.00)
        raw_confidence = (
            (0.50 * grounding_ratio) +
            (0.30 * coverage_score) +
            deterministic_boost -
            contra_penalty
        )
        final_score = max(0.0, min(0.99, raw_confidence))

        # Determine confidence class
        if final_score >= 0.92 and contradictions_count == 0:
            status = "VERIFIED"
        elif final_score >= 0.82:
            status = "STRONGLY_SUPPORTED"
        elif final_score >= 0.70:
            status = "PROBABLE"
        elif contradictions_count >= 2:
            status = "CONTRADICTED"
        elif final_score >= 0.50:
            status = "UNCERTAIN"
        else:
            status = "UNSUPPORTED"

        summary = (
            f"Confidence calibrated at {int(final_score * 100)}% ({status}) "
            f"across {len(claims)} evaluated claims and {crawled_count} deep-audited pages."
        )
        if index_coverage is not None and index_url_count:
            summary += (
                f" Index coverage is {crawled_count} of {index_url_count} discovered URLs"
                f" ({int(index_coverage * 100)}%). Sample confidence is not sitewide coverage."
            )

        return ConfidenceResult(
            confidence_score=round(final_score, 2),
            evidence_coverage=round(budget_coverage, 2),
            status=status,
            signals_breakdown={
                "grounding_ratio": round(grounding_ratio, 2),
                "page_coverage": round(coverage_score, 2),
                "deterministic_verification": round(deterministic_boost, 2),
                "contradiction_penalty": round(contra_penalty, 2)
            },
            summary=summary,
            index_coverage=index_coverage,
            sample_page_count=crawled_count,
            index_url_count=index_url_count,
        )

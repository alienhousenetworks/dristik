"""
Dristik AI GEO / Generative Engine Competition Metrics.
Calculates AI prompt overlap, citation frequency, answer mention rate,
and head-to-head answer readiness across AI engines (ChatGPT, Perplexity, Claude, Gemini).
Zero-fake policy: If AI prompt visibility has not been observed, emits status=UNMEASURED.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from app.seo.competitive.models import (
    CompetitorEvidenceItem,
    DimensionScore,
    EvidenceConfidence,
)


class GeoMetricsCalculator:
    """
    Evaluates generative engine optimization (GEO) competition dimensions.
    """

    def compute_geo_score(
        self,
        competitor_id: str,
        competitor_domain: str,
        total_prompts_tested: int,
        prompt_mentions: int = 0,
        citations_count: int = 0,
        bakeoff_wins: Optional[int] = None,
        bakeoff_total: Optional[int] = None,
        audit_id: Optional[str] = None,
    ) -> Tuple[DimensionScore, List[CompetitorEvidenceItem]]:
        evidence_items: List[CompetitorEvidenceItem] = []

        if total_prompts_tested <= 0:
            return (
                DimensionScore(
                    dimension="geo",
                    score=None,
                    confidence=EvidenceConfidence.UNMEASURED,
                    status="UNMEASURED",
                    evidence_count=0,
                    key_metrics={"reason": "Insufficient prompt coverage: No AI answer engine tests observed."},
                ),
                evidence_items,
            )

        prompt_overlap_pct = round((prompt_mentions / total_prompts_tested) * 100, 1)
        citation_freq_pct = round((citations_count / total_prompts_tested) * 100, 1)

        evidence_items.append(
            CompetitorEvidenceItem(
                id=f"{competitor_id}_geo_vis",
                competitor_id=competitor_id,
                evidence_type="geo",
                metric="geo_visibility",
                value=prompt_overlap_pct,
                unit="%",
                source_type="ai_simulator",
                confidence=EvidenceConfidence.HIGH,
                audit_id=audit_id,
                notes=f"Competitor mentioned in {prompt_mentions}/{total_prompts_tested} tested AI prompts.",
            )
        )

        evidence_items.append(
            CompetitorEvidenceItem(
                id=f"{competitor_id}_citation_freq",
                competitor_id=competitor_id,
                evidence_type="geo",
                metric="citation_frequency",
                value=citation_freq_pct,
                unit="%",
                source_type="ai_simulator",
                confidence=EvidenceConfidence.HIGH,
                audit_id=audit_id,
                notes=f"Competitor URL cited in {citations_count}/{total_prompts_tested} answer sources.",
            )
        )

        # Calculate composite GEO score
        # 50% prompt overlap, 50% citation frequency
        composite_score = int(round(0.5 * prompt_overlap_pct + 0.5 * citation_freq_pct))
        if composite_score > 100:
            composite_score = 100

        key_metrics: Dict[str, Any] = {
            "ai_prompt_overlap_pct": prompt_overlap_pct,
            "citation_frequency_pct": citation_freq_pct,
            "prompts_tested": total_prompts_tested,
            "citations_observed": citations_count,
        }

        if bakeoff_wins is not None and bakeoff_total and bakeoff_total > 0:
            key_metrics["commercial_bakeoff_win_rate"] = round((bakeoff_wins / bakeoff_total) * 100, 1)

        dim_score = DimensionScore(
            dimension="geo",
            score=composite_score,
            confidence=EvidenceConfidence.HIGH if total_prompts_tested >= 5 else EvidenceConfidence.MEDIUM,
            status="AVAILABLE",
            evidence_count=len(evidence_items),
            key_metrics=key_metrics,
        )

        return dim_score, evidence_items


geo_metrics_calculator = GeoMetricsCalculator()

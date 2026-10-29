"""
Dristik AI Search Competition Metrics.
Calculates keyword overlap, organic visibility index, commercial query coverage,
and SERP ownership from empirical search demand observations.
Zero-fake policy: If search overlap has not been measured, emits status=UNMEASURED.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from app.seo.competitive.models import (
    CompetitorEvidenceItem,
    DimensionScore,
    EvidenceConfidence,
)

# Canonical CTR by organic position (Industry standard CTR curve)
_CTR_BY_POSITION: Dict[int, float] = {
    1: 0.28,
    2: 0.15,
    3: 0.11,
    4: 0.07,
    5: 0.06,
    6: 0.04,
    7: 0.03,
    8: 0.03,
    9: 0.02,
    10: 0.02,
}


def calculate_organic_visibility_index(positions: List[int]) -> int:
    """
    Computes a normalized 0-100 Organic Visibility Index based on ranking positions.
    """
    if not positions:
        return 0
    total_ctr = sum(_CTR_BY_POSITION.get(p, 0.01 if p <= 20 else 0.002) for p in positions)
    # Scale to 0-100 (10 top-1 ranks = max score)
    scaled = min(100, int(round((total_ctr / 2.8) * 100)))
    return scaled


class SearchMetricsCalculator:
    """
    Evaluates search competition dimensions from observed query rankings.
    """

    def compute_search_score(
        self,
        competitor_id: str,
        target_queries: List[str],
        competitor_ranking_queries: Optional[Dict[str, int]] = None,
        target_ranking_queries: Optional[Dict[str, int]] = None,
        audit_id: Optional[str] = None,
    ) -> Tuple[DimensionScore, List[CompetitorEvidenceItem]]:
        """
        Calculates search dimension score and evidence items.
        target_queries: Universe of customer search queries.
        competitor_ranking_queries: dict of {query: rank_position} for competitor.
        target_ranking_queries: dict of {query: rank_position} for customer.
        """
        evidence_items: List[CompetitorEvidenceItem] = []

        if not competitor_ranking_queries:
            # Unmeasured competitor
            return (
                DimensionScore(
                    dimension="search",
                    score=None,
                    confidence=EvidenceConfidence.UNMEASURED,
                    status="UNMEASURED",
                    evidence_count=0,
                    key_metrics={"reason": "Competitor query rankings not yet queried or crawled."},
                ),
                evidence_items,
            )

        total_target_q = len(target_queries) if target_queries else len(target_ranking_queries or {})
        if total_target_q == 0:
            total_target_q = 1  # prevent div 0

        # Calculate Keyword Overlap
        target_q_set = set(q.lower().strip() for q in (target_queries or list((target_ranking_queries or {}).keys())))
        shared_queries = [q for q in competitor_ranking_queries.keys() if q.lower().strip() in target_q_set]
        overlap_pct = round((len(shared_queries) / total_target_q) * 100, 1)

        # Calculate Organic Visibility Index
        positions = list(competitor_ranking_queries.values())
        visibility_index = calculate_organic_visibility_index(positions)

        # Average Position
        avg_pos = round(sum(positions) / len(positions), 1) if positions else None

        # Build evidence items
        evidence_items.append(
            CompetitorEvidenceItem(
                id=f"{competitor_id}_kw_overlap",
                competitor_id=competitor_id,
                evidence_type="search",
                metric="keyword_overlap",
                value=overlap_pct,
                unit="%",
                source_type="serp_api",
                confidence=EvidenceConfidence.HIGH,
                audit_id=audit_id,
                notes=f"Competitor shares {len(shared_queries)}/{total_target_q} queries with target domain.",
            )
        )

        evidence_items.append(
            CompetitorEvidenceItem(
                id=f"{competitor_id}_org_vis",
                competitor_id=competitor_id,
                evidence_type="search",
                metric="organic_visibility",
                value=visibility_index,
                unit="score_0_100",
                source_type="serp_api",
                confidence=EvidenceConfidence.HIGH,
                audit_id=audit_id,
                notes=f"Derived from {len(positions)} observed SERP ranking positions.",
            )
        )

        # Overall Search Score composite (0-100)
        # 50% keyword overlap, 50% visibility index
        composite_score = int(round(0.5 * min(100, overlap_pct * 1.5) + 0.5 * visibility_index))

        dim_score = DimensionScore(
            dimension="search",
            score=composite_score,
            confidence=EvidenceConfidence.HIGH if len(positions) >= 5 else EvidenceConfidence.MEDIUM,
            status="AVAILABLE",
            evidence_count=len(evidence_items),
            key_metrics={
                "keyword_overlap_pct": overlap_pct,
                "organic_visibility_index": visibility_index,
                "average_rank_position": avg_pos,
                "shared_query_count": len(shared_queries),
                "total_queries_evaluated": total_target_q,
            },
        )

        return dim_score, evidence_items


search_metrics_calculator = SearchMetricsCalculator()

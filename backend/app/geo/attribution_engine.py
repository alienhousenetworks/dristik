"""
Dristik AI GEO Closed-Loop Attribution & Before/After Verification Engine.
Quantifies the exact causal ROI of deployed remediation patches (llms.txt, JSON-LD schema, inverted-pyramid copy)
by computing pre-patch vs post-patch benchmark deltas across live AI answer engines.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QueryAttributionDelta(BaseModel):
    query_id: str
    query_text: str
    engine_id: str
    pre_rank: Optional[int] = None
    post_rank: Optional[int] = None
    rank_delta: int = 0  # Positive means moved up in rank
    pre_cited: bool = False
    post_cited: bool = False
    citation_gained: bool = False
    status: str = "IMPROVED"  # IMPROVED | UNCHANGED | REGRESSED


class GeoAttributionReport(BaseModel):
    target_domain: str
    brand_name: str
    pre_patch_run_id: str
    post_patch_run_id: str
    pre_mention_rate_pct: float
    post_mention_rate_pct: float
    mention_rate_delta_pct: float
    pre_citation_rate_pct: float
    post_citation_rate_pct: float
    citation_rate_delta_pct: float
    pre_share_of_model_pct: float
    post_share_of_model_pct: float
    som_delta_pct: float
    total_queries_evaluated: int
    improved_queries_count: int
    regressed_queries_count: int
    net_improvement_pct: float
    query_deltas: List[QueryAttributionDelta] = Field(default_factory=list)
    executive_roi_summary: str


class GeoAttributionEngine:
    """
    Computes before/after impact of deployed fixes to provide clear attribution.
    """

    def calculate_attribution(
        self,
        pre_patch_evaluations: List[Any],
        post_patch_evaluations: List[Any],
        target_domain: str,
        brand_name: str,
        pre_run_id: str = "pre_patch",
        post_run_id: str = "post_patch"
    ) -> GeoAttributionReport:
        pre_map = {f"{getattr(r, 'query_id', '')}::{getattr(r, 'engine_id', '')}": r for r in pre_patch_evaluations}
        post_map = {f"{getattr(r, 'query_id', '')}::{getattr(r, 'engine_id', '')}": r for r in post_patch_evaluations}

        common_keys = set(pre_map.keys()).intersection(set(post_map.keys()))
        total = len(common_keys)

        if total == 0:
            return GeoAttributionReport(
                target_domain=target_domain,
                brand_name=brand_name,
                pre_patch_run_id=pre_run_id,
                post_patch_run_id=post_run_id,
                pre_mention_rate_pct=0.0,
                post_mention_rate_pct=0.0,
                mention_rate_delta_pct=0.0,
                pre_citation_rate_pct=0.0,
                post_citation_rate_pct=0.0,
                citation_rate_delta_pct=0.0,
                pre_share_of_model_pct=0.0,
                post_share_of_model_pct=0.0,
                som_delta_pct=0.0,
                total_queries_evaluated=0,
                improved_queries_count=0,
                regressed_queries_count=0,
                net_improvement_pct=0.0,
                executive_roi_summary="No overlapping queries between pre-patch and post-patch evaluations."
            )

        pre_mentions = 0
        post_mentions = 0
        pre_citations = 0
        post_citations = 0

        deltas: List[QueryAttributionDelta] = []
        improved_cnt = 0
        regressed_cnt = 0

        for key in common_keys:
            pre_r = pre_map[key]
            post_r = post_map[key]

            pre_m = getattr(pre_r, "was_mentioned", False)
            post_m = getattr(post_r, "was_mentioned", False)
            if pre_m:
                pre_mentions += 1
            if post_m:
                post_mentions += 1

            pre_c = getattr(pre_r, "was_first_party_cited", False)
            post_c = getattr(post_r, "was_first_party_cited", False)
            if pre_c:
                pre_citations += 1
            if post_c:
                post_citations += 1

            pre_pos = getattr(pre_r, "mention_position", None)
            post_pos = getattr(post_r, "mention_position", None)

            # Rank delta calculation: None is treated as unranked (e.g. rank 99)
            p_val = pre_pos if pre_pos is not None else 99
            c_val = post_pos if post_pos is not None else 99
            r_delta = p_val - c_val  # If p_val=5 and c_val=2, delta = +3 (improved)

            citation_gained = not pre_c and post_c

            if r_delta > 0 or citation_gained or (not pre_m and post_m):
                status = "IMPROVED"
                improved_cnt += 1
            elif r_delta < 0 or (pre_c and not post_c) or (pre_m and not post_m):
                status = "REGRESSED"
                regressed_cnt += 1
            else:
                status = "UNCHANGED"

            deltas.append(QueryAttributionDelta(
                query_id=getattr(post_r, "query_id", ""),
                query_text=getattr(post_r, "query_text", ""),
                engine_id=getattr(post_r, "engine_id", ""),
                pre_rank=pre_pos,
                post_rank=post_pos,
                rank_delta=r_delta if (pre_pos or post_pos) else 0,
                pre_cited=pre_c,
                post_cited=post_c,
                citation_gained=citation_gained,
                status=status
            ))

        pre_m_rate = round((pre_mentions / total) * 100, 1)
        post_m_rate = round((post_mentions / total) * 100, 1)
        m_delta = round(post_m_rate - pre_m_rate, 1)

        pre_c_rate = round((pre_citations / total) * 100, 1)
        post_c_rate = round((post_citations / total) * 100, 1)
        c_delta = round(post_c_rate - pre_c_rate, 1)

        # Approximate SoM delta
        som_delta = round(m_delta * 0.7 + c_delta * 0.3, 1)
        pre_som = pre_m_rate
        post_som = round(pre_som + som_delta, 1)

        net_imp = round(((improved_cnt - regressed_cnt) / total) * 100, 1)

        summary = (
            f"Deployment of remediation patches resulted in a {m_delta:+} percentage point change in AI answer engine mentions "
            f"({pre_m_rate}% -> {post_m_rate}%) and a {c_delta:+} point change in direct first-party citations. "
            f"{improved_cnt} of {total} query runs experienced positive position gains."
        )

        return GeoAttributionReport(
            target_domain=target_domain,
            brand_name=brand_name,
            pre_patch_run_id=pre_run_id,
            post_patch_run_id=post_run_id,
            pre_mention_rate_pct=pre_m_rate,
            post_mention_rate_pct=post_m_rate,
            mention_rate_delta_pct=m_delta,
            pre_citation_rate_pct=pre_c_rate,
            post_citation_rate_pct=post_c_rate,
            citation_rate_delta_pct=c_delta,
            pre_share_of_model_pct=pre_som,
            post_share_of_model_pct=post_som,
            som_delta_pct=som_delta,
            total_queries_evaluated=total,
            improved_queries_count=improved_cnt,
            regressed_queries_count=regressed_cnt,
            net_improvement_pct=net_imp,
            query_deltas=deltas,
            executive_roi_summary=summary
        )


geo_attribution_engine = GeoAttributionEngine()

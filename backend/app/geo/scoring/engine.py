"""Phase 12 — Canonical Dual-Scorecard & 7-Dimension GEO Scoring Engine.

Single source of truth consumed identically by backend, frontend, QA gate,
and PDF reports.

Strictly preserves TWO separate scorecards:
1. Observed GEO Performance (Measured AI visibility 20%, Citation visibility &
   quality 20%, Competitive positioning & coverage 10% -> 50% weight share)
2. GEO Readiness & Optimization (Brand entity consistency 15%, Content &
   information quality 15%, External reputation & source coverage 15%,
   Technical & retrieval readiness 5% -> 50% weight share)

Non-negotiable integrity rules:
- Missing AI provider credentials -> NOT_CONFIGURED (score=None), NEVER 0.
- Untested platform -> excluded from numerator and denominator.
- Readiness NEVER substitutes for Observed AI Performance.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.geo.models import (
    GEOAuditScope,
    GEOCitation,
    GEOCoverageMetadata,
    GEODataQualityState,
    GEODimensionScoreCard,
    GEODualScorecard,
    GEOPlatform,
    GEOPromptRun,
    GEOResponse,
    GEOSourceOwnership,
    GEOTestPrompt,
    GEO_METHODOLOGY_VERSION,
)

# Proposed 7-dimension product methodology weights (total = 100%)
SEVEN_DIMENSION_WEIGHTS = [
    ("measured_ai_visibility", "Measured AI visibility", "observed_performance", 20.0),
    ("citation_visibility_quality", "Citation visibility and quality", "observed_performance", 20.0),
    ("brand_entity_consistency", "Brand entity consistency", "readiness_optimization", 15.0),
    ("content_information_quality", "Content and information quality", "readiness_optimization", 15.0),
    ("external_reputation_coverage", "External reputation and source coverage", "readiness_optimization", 15.0),
    ("competitive_positioning_coverage", "Competitive positioning and coverage", "observed_performance", 10.0),
    ("technical_retrieval_readiness", "Technical and retrieval readiness", "readiness_optimization", 5.0),
]


def _grade(score: Optional[float]) -> str:
    if score is None:
        return "Unmeasured"
    if score >= 85.0:
        return "A"
    if score >= 70.0:
        return "B"
    if score >= 55.0:
        return "C"
    if score >= 40.0:
        return "D"
    return "F"


class EnterpriseGEOScoringEngine:
    """Computes canonical dual scorecards + 7-dimension methodology breakdown."""

    @classmethod
    def compute(
        cls,
        *,
        audit_id: str,
        scope: GEOAuditScope,
        prompts: List[GEOTestPrompt],
        runs: List[GEOPromptRun],
        responses: List[GEOResponse],
        citations: List[GEOCitation],
        platforms: List[GEOPlatform],
        dept_artifacts: Dict[str, Any],
    ) -> GEODualScorecard:
        ok_runs = [r for r in runs if r.status == GEODataQualityState.OBSERVED]
        failed_runs = [r for r in runs if r.status in (GEODataQualityState.FAILED, GEODataQualityState.UNAVAILABLE)]
        approved_prompts = [p for p in prompts if p.approval_status == "approved"]
        prompt_map = {p.prompt_id: p for p in prompts}

        branded_tested = len({r.prompt_id for r in ok_runs if prompt_map.get(r.prompt_id) and prompt_map[r.prompt_id].is_branded})
        non_branded_tested = len({r.prompt_id for r in ok_runs if prompt_map.get(r.prompt_id) and not prompt_map[r.prompt_id].is_branded})

        tested_platforms = sorted({r.platform_id for r in ok_runs})
        unconfigured_platforms = sorted({p.platform_id for p in platforms if p.data_quality_state == GEODataQualityState.NOT_CONFIGURED})

        vis_art = dept_artifacts.get("department_b") or {}
        cit_art = dept_artifacts.get("department_c") or {}
        ent_art = dept_artifacts.get("department_a") or {}
        cnt_art = dept_artifacts.get("department_d") or {}
        tech_art = dept_artifacts.get("department_e") or {}
        rep_art = dept_artifacts.get("department_f") or {}
        comp_art = dept_artifacts.get("department_g") or {}

        # ── Dimension 1: Measured AI visibility (20%) ────────────────────────
        d1_score: Optional[float] = None
        d1_status = GEODataQualityState.NOT_CONFIGURED if not tested_platforms else GEODataQualityState.NOT_TESTED
        d1_num: Optional[float] = None
        d1_den: Optional[float] = None
        if ok_runs:
            overall = vis_art.get("overall") or {}
            non_b = vis_art.get("non_branded") or {}
            m_rate = non_b.get("mention_rate_pct") if non_b.get("runs", 0) > 0 else overall.get("mention_rate_pct", 0.0)
            rec_rate = overall.get("recommendation_rate_pct") or 0.0
            sh_rate = overall.get("shortlist_rate_pct") or 0.0
            d1_score = round((float(m_rate or 0.0) * 0.45) + (float(rec_rate) * 0.35) + (float(sh_rate) * 0.20), 1)
            d1_status = GEODataQualityState.OBSERVED
            d1_num = float(overall.get("mentions", 0))
            d1_den = float(len(ok_runs))

        # ── Dimension 2: Citation visibility & quality (20%) ─────────────────
        d2_score: Optional[float] = None
        d2_status = GEODataQualityState.NOT_CONFIGURED if not tested_platforms else GEODataQualityState.UNAVAILABLE
        d2_num: Optional[float] = None
        d2_den: Optional[float] = None
        if ok_runs:
            c_summary = cit_art.get("summary") or {}
            total_c = int(c_summary.get("total_citations") or 0)
            owned_c = int(c_summary.get("owned_citations") or 0)
            indep_c = int(c_summary.get("independent_citations") or 0)
            # Only score citation visibility if search-grounded or citations were actually available
            has_citation_capable = any(
                (p.capabilities.citation_metadata == "Yes" or p.citation_count > 0) for p in platforms if p.platform_id in tested_platforms
            )
            if total_c > 0 or has_citation_capable:
                cited_resps = sum(1 for r in responses if r.brand_cited)
                cit_resp_rate = (cited_resps / len(ok_runs)) * 100.0
                indep_bonus = min(30.0, indep_c * 7.5)
                owned_share = (owned_c / total_c * 100.0) if total_c > 0 else 0.0
                d2_score = round(min(100.0, cit_resp_rate * 0.50 + owned_share * 0.20 + indep_bonus), 1)
                d2_status = GEODataQualityState.OBSERVED
                d2_num = float(owned_c)
                d2_den = float(max(total_c, len(ok_runs)))

        # ── Dimension 3: Brand entity consistency (15%) ──────────────────────
        d3_raw = ent_art.get("consistency_score")
        d3_score = round(float(d3_raw), 1) if isinstance(d3_raw, (int, float)) else None
        d3_status = GEODataQualityState.OBSERVED if d3_score is not None else GEODataQualityState.NOT_TESTED

        # ── Dimension 4: Content & information quality (15%) ─────────────────
        d4_raw = cnt_art.get("content_quality_score")
        d4_score = round(float(d4_raw), 1) if isinstance(d4_raw, (int, float)) else None
        d4_status = GEODataQualityState.OBSERVED if d4_score is not None else GEODataQualityState.NOT_TESTED

        # ── Dimension 5: External reputation & source coverage (15%) ─────────
        d5_raw = rep_art.get("reputation_score")
        d5_score = round(float(d5_raw), 1) if isinstance(d5_raw, (int, float)) else None
        d5_status = GEODataQualityState.OBSERVED if d5_score is not None else GEODataQualityState.NOT_TESTED

        # ── Dimension 6: Competitive positioning & coverage (10%) ────────────
        d6_raw = comp_art.get("competitive_score")
        d6_score = round(float(d6_raw), 1) if isinstance(d6_raw, (int, float)) else None
        d6_status = GEODataQualityState.OBSERVED if d6_score is not None else (
            GEODataQualityState.NOT_CONFIGURED if not tested_platforms else GEODataQualityState.NOT_TESTED
        )

        # ── Dimension 7: Technical & retrieval readiness (5%) ────────────────
        d7_raw = tech_art.get("technical_readiness_score")
        d7_score = round(float(d7_raw), 1) if isinstance(d7_raw, (int, float)) else None
        d7_status = GEODataQualityState.OBSERVED if d7_score is not None else GEODataQualityState.NOT_TESTED

        dim_values = {
            "measured_ai_visibility": (d1_score, d1_status, d1_num, d1_den, len(ok_runs), [r.response_id for r in responses[:3]]),
            "citation_visibility_quality": (d2_score, d2_status, d2_num, d2_den, len(citations), [c.citation_id for c in citations[:3]]),
            "brand_entity_consistency": (d3_score, d3_status, float(ent_art.get("confirmed_facts", 0)), float(max(ent_art.get("total_facts", 0), 1)), int(ent_art.get("total_facts", 0)), []),
            "content_information_quality": (d4_score, d4_status, None, float(cnt_art.get("pages_analyzed", 0)) or None, int(cnt_art.get("pages_analyzed", 0)), []),
            "external_reputation_coverage": (d5_score, d5_status, float(rep_art.get("independent_sources_with_brand", 0)), float(rep_art.get("independent_sources_total", 0)) or None, int(rep_art.get("independent_sources_total", 0)), []),
            "competitive_positioning_coverage": (d6_score, d6_status, None, float(len(ok_runs)) or None, len(ok_runs), []),
            "technical_retrieval_readiness": (d7_score, d7_status, None, None, len(tech_art.get("crawlers_evaluated") or []), []),
        }

        dimensions: List[GEODimensionScoreCard] = []
        for key, name, group, weight in SEVEN_DIMENSION_WEIGHTS:
            sc, st, num, den, sample, evs = dim_values[key]
            dimensions.append(
                GEODimensionScoreCard(
                    dimension_key=key,
                    dimension_name=name,
                    scorecard_group=group,
                    proposed_weight_pct=weight,
                    score=sc,
                    grade=_grade(sc),
                    status=st,
                    numerator=num,
                    denominator=den,
                    sample_size=sample,
                    evidence_ids=evs,
                    notes=[] if sc is not None else [f"Unmeasured ({st.value}); excluded from weighted numerator and denominator."],
                )
            )

        def _weighted_avg(group: str) -> tuple[Optional[float], float, GEODataQualityState]:
            subset = [d for d in dimensions if d.scorecard_group == group]
            measured = [d for d in subset if d.score is not None]
            if not measured:
                if group == "observed_performance" and not tested_platforms:
                    return None, 0.0, GEODataQualityState.NOT_CONFIGURED
                return None, 0.0, GEODataQualityState.NOT_TESTED
            w_sum = sum(d.proposed_weight_pct for d in measured)
            val = round(sum((d.score or 0.0) * d.proposed_weight_pct for d in measured) / w_sum, 1)
            st = GEODataQualityState.OBSERVED if len(measured) == len(subset) else GEODataQualityState.PARTIAL
            return val, w_sum, st

        obs_score, obs_w, obs_status = _weighted_avg("observed_performance")
        ready_score, ready_w, ready_status = _weighted_avg("readiness_optimization")

        # Only compute a combined methodology reference when BOTH scorecards have eligible measurements
        comp_score: Optional[float] = None
        active_weight = round(obs_w + ready_w, 1)
        if obs_score is not None and ready_score is not None and active_weight > 0:
            measured_all = [d for d in dimensions if d.score is not None]
            comp_score = round(sum((d.score or 0.0) * d.proposed_weight_pct for d in measured_all) / active_weight, 1)

        overall_vis = vis_art.get("overall") or {}
        non_b_vis = vis_art.get("non_branded") or {}
        branded_vis = vis_art.get("branded") or {}
        confidence = None
        if ok_runs and ready_score is not None:
            confidence = round(min(0.95, 0.55 + (len(tested_platforms) * 0.08) + min(0.16, len(ok_runs) / 100.0)), 2)
        elif ready_score is not None:
            confidence = 0.72

        coverage = GEOCoverageMetadata(
            tested_platforms=tested_platforms,
            unconfigured_platforms=unconfigured_platforms,
            successful_prompt_executions=len(ok_runs),
            failed_prompt_executions=len(failed_runs),
            total_planned_prompts=len(approved_prompts),
            branded_prompts_tested=branded_tested,
            non_branded_prompts_tested=non_branded_tested,
            repeat_test_count=scope.repetitions,
            markets_covered=list(scope.markets or []),
            languages_covered=list(scope.languages or []),
            connector_availability={p.platform_id: p.capabilities.auth_state for p in platforms},
            evidence_confidence=confidence,
            methodology_version=GEO_METHODOLOGY_VERSION,
        )

        return GEODualScorecard(
            audit_id=audit_id,
            methodology_version=GEO_METHODOLOGY_VERSION,
            observed_performance_score=obs_score,
            observed_performance_grade=_grade(obs_score),
            observed_performance_status=obs_status,
            observed_metrics={
                "brand_mention_rate_pct": overall_vis.get("mention_rate_pct"),
                "non_branded_mention_rate_pct": non_b_vis.get("mention_rate_pct"),
                "branded_mention_rate_pct": branded_vis.get("mention_rate_pct"),
                "recommendation_rate_pct": overall_vis.get("recommendation_rate_pct"),
                "shortlist_rate_pct": overall_vis.get("shortlist_rate_pct"),
                "citation_observation_rate_pct": overall_vis.get("citation_rate_pct"),
                "total_citations_observed": (cit_art.get("summary") or {}).get("total_citations", 0),
                "owned_citation_share_pct": (cit_art.get("summary") or {}).get("owned_share_pct"),
                "independent_citation_share_pct": (cit_art.get("summary") or {}).get("independent_share_pct"),
                "target_competitive_rank": comp_art.get("target_rank"),
                "target_mention_share_pct": comp_art.get("target_mention_share_pct"),
            },
            readiness_score=ready_score,
            readiness_grade=_grade(ready_score),
            readiness_status=ready_status,
            readiness_metrics={
                "entity_consistency_score": d3_score,
                "content_quality_score": d4_score,
                "external_reputation_score": d5_score,
                "technical_readiness_score": d7_score,
                "pages_analyzed": cnt_art.get("pages_analyzed", 0),
                "search_retrieval_allowed": tech_art.get("search_retrieval_allowed"),
            },
            methodology_composite_score=comp_score,
            methodology_composite_grade=_grade(comp_score),
            active_weight_pct=active_weight,
            dimensions=dimensions,
            coverage=coverage,
        )

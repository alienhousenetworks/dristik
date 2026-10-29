"""
Dristik AI Causal Competitive Gap & Advantage Reasoner.
Calculates objective dimensional gaps (Target vs Competitors) and derives
traceable, evidence-backed causal explanations explaining WHY competitors outperform
the target domain across search, GEO, and technical execution.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.seo.competitive.models import (
    CausalAdvantageExplanation,
    CompetitiveGapDimension,
    DimensionScore,
)


class CausalGapExplainer:
    """
    Synthesizes dimensional gaps and causal explainability proofs.
    """

    DIMENSION_NAMES = {
        "technical": "Technical SEO Health",
        "search": "Search Visibility & Rank Overlap",
        "geo": "GEO & AI Citation Visibility",
        "content": "Content Depth & Topic Coverage",
        "schema": "Structured Data & Entity Graph",
        "authority": "Authority & External Mentions",
    }

    def compute_dimensional_gaps(
        self,
        target_dimensions: Dict[str, DimensionScore],
        competitor_dimensions: Dict[str, Dict[str, DimensionScore]],  # comp_domain -> dim_key -> DimensionScore
    ) -> List[CompetitiveGapDimension]:
        gap_rows: List[CompetitiveGapDimension] = []

        all_keys = list(self.DIMENSION_NAMES.keys())

        for dim_key in all_keys:
            name = self.DIMENSION_NAMES.get(dim_key, dim_key.title())
            target_dim = target_dimensions.get(dim_key)
            t_score = target_dim.score if target_dim and target_dim.status == "AVAILABLE" else None

            comp_scores: Dict[str, Optional[int]] = {}
            deltas: Dict[str, Optional[int]] = {}

            for comp_domain, dims in competitor_dimensions.items():
                c_dim = dims.get(dim_key)
                c_score = c_dim.score if c_dim and c_dim.status == "AVAILABLE" else None
                comp_scores[comp_domain] = c_score
                if t_score is not None and c_score is not None:
                    deltas[comp_domain] = t_score - c_score
                else:
                    deltas[comp_domain] = None

            # Generate verdict string
            measured_deltas = [d for d in deltas.values() if d is not None]
            if not measured_deltas:
                verdict = f"{name}: Target score {t_score if t_score is not None else 'Unmeasured'}. Competitor data unmeasured."
            else:
                avg_delta = sum(measured_deltas) / len(measured_deltas)
                if avg_delta >= 10:
                    verdict = f"Target holds a clear competitive advantage (+{int(avg_delta)} pts ahead of peer average)."
                elif avg_delta <= -10:
                    verdict = f"Target trails competitors by {abs(int(avg_delta))} pts; critical optimization opportunity."
                else:
                    verdict = f"Target performs at competitive parity (within {abs(int(avg_delta))} pts of peers)."

            gap_rows.append(
                CompetitiveGapDimension(
                    dimension_name=name,
                    dimension_key=dim_key,
                    target_score=t_score,
                    competitor_scores=comp_scores,
                    deltas=deltas,
                    verdict=verdict,
                )
            )

        return gap_rows

    def explain_advantages(
        self,
        target_domain: str,
        target_brand: str,
        target_dimensions: Dict[str, DimensionScore],
        competitor_domain: str,
        competitor_name: str,
        competitor_dimensions: Dict[str, DimensionScore],
    ) -> CausalAdvantageExplanation:
        """
        Generates concrete bulleted reasons explaining why a competitor outperforms or lags target.
        """
        reasons_they_outperform: List[str] = []
        areas_target_wins: List[str] = []

        # 1. GEO / AI Visibility check
        t_geo = target_dimensions.get("geo")
        c_geo = competitor_dimensions.get("geo")
        if t_geo and c_geo and t_geo.status == "AVAILABLE" and c_geo.status == "AVAILABLE":
            t_score = t_geo.score or 0
            c_score = c_geo.score or 0
            t_prompts = (t_geo.key_metrics or {}).get("ai_prompt_overlap_pct", 0)
            c_prompts = (c_geo.key_metrics or {}).get("ai_prompt_overlap_pct", 0)

            if c_score > t_score + 10:
                reasons_they_outperform.append(
                    f"GEO Visibility: {competitor_name} appears in {c_prompts}% of tested AI prompts vs {t_prompts}% for {target_brand}."
                )
            elif t_score > c_score + 10:
                areas_target_wins.append(
                    f"GEO Visibility: {target_brand} captures {t_prompts}% AI prompt share vs {c_prompts}% for {competitor_name}."
                )

        # 2. Search / Keyword Overlap check
        t_search = target_dimensions.get("search")
        c_search = competitor_dimensions.get("search")
        if t_search and c_search and t_search.status == "AVAILABLE" and c_search.status == "AVAILABLE":
            c_km = c_search.key_metrics or {}
            overlap = c_km.get("keyword_overlap_pct", 0)
            vis = c_km.get("organic_visibility_index", 0)
            shared_q = c_km.get("shared_query_count", 0)

            if vis > 60:
                reasons_they_outperform.append(
                    f"Organic Search Ownership: {competitor_name} controls high-intent SERPs with {overlap}% keyword overlap across {shared_q} shared commercial queries."
                )

        # 3. Technical & Structured Data check
        t_tech = target_dimensions.get("technical")
        c_tech = competitor_dimensions.get("technical")
        if t_tech and c_tech and t_tech.status == "AVAILABLE" and c_tech.status == "AVAILABLE":
            t_km = t_tech.key_metrics or {}
            c_km = c_tech.key_metrics or {}

            t_ttfb = t_km.get("ttfb_ms", 0)
            c_ttfb = c_km.get("ttfb_ms", 0)
            t_schemas = t_km.get("schema_count", 0)
            c_schemas = c_km.get("schema_count", 0)

            # TTFB
            if c_ttfb > 0 and t_ttfb > c_ttfb + 250:
                reasons_they_outperform.append(
                    f"Server Latency: {competitor_name} loads substantially faster ({c_ttfb:.0f}ms TTFB vs {t_ttfb:.0f}ms on {target_brand})."
                )
            elif t_ttfb > 0 and c_ttfb > t_ttfb + 250:
                areas_target_wins.append(
                    f"Server Latency: {target_brand} responds {c_ttfb - t_ttfb:.0f}ms faster ({t_ttfb:.0f}ms vs {c_ttfb:.0f}ms)."
                )

            # Schema
            if c_schemas > t_schemas:
                schema_types = ", ".join(c_km.get("schema_types", [])[:3])
                reasons_they_outperform.append(
                    f"Structured Data: {competitor_name} implements {c_schemas} Schema.org types ({schema_types}) versus {t_schemas} types on {target_brand}."
                )
            elif t_schemas > c_schemas:
                areas_target_wins.append(
                    f"Structured Data: {target_brand} deploys richer Schema.org markup ({t_schemas} types vs {c_schemas})."
                )

        if not reasons_they_outperform:
            reasons_they_outperform.append(
                f"No major deficits observed: {competitor_name} performs at or below parity on measured metrics."
            )

        if not areas_target_wins:
            areas_target_wins.append(
                f"Closing the technical and GEO citation gap is required to establish dominance over {competitor_name}."
            )

        return CausalAdvantageExplanation(
            competitor_domain=competitor_domain,
            competitor_name=competitor_name,
            reasons_they_outperform=reasons_they_outperform,
            areas_target_wins=areas_target_wins,
        )


causal_gap_explainer = CausalGapExplainer()

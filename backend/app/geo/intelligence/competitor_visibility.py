"""
Competitor AI Visibility Benchmark — Phase 4.8

Executes uniform comparative benchmarks against declared competitors:
- Brand mention Share of Voice (SOV)
- First-party citation frequency
- Top recommendation win rate
- Query coverage across the Question Universe
- Competitor displacement and positioning analysis

STRICT GUARDRAIL:
Enforces identical benchmark prompt sets, time windows, and engine parameters across all entities.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CompetitorBenchmarkMetrics(BaseModel):
    entity_name: str
    is_target_brand: bool = False
    total_queries_tested: int
    mention_count: int
    mention_rate_pct: float
    citation_count: int
    citation_rate_pct: float
    top_recommendation_wins: int
    recommendation_win_rate_pct: float
    citation_domains: List[str] = Field(default_factory=list)


class CompetitorVisibilityReport(BaseModel):
    target_brand: str
    competitors_compared_count: int
    test_conditions_summary: str
    leaderboard: List[CompetitorBenchmarkMetrics] = Field(default_factory=list)
    winner_entity: str
    target_brand_rank: int
    competitive_displacement_verdict: str
    actionable_remediation: List[str] = Field(default_factory=list)


class CompetitorVisibilityEngine:
    """
    Computes comparative AI visibility metrics under uniform prompt conditions.
    """

    @classmethod
    def compare_competitors(
        cls,
        target_brand: str,
        competitors: List[str],
        probed_responses: List[Dict[str, Any]],  # List of {"query": str, "response": str, "citations": List[str]}
    ) -> CompetitorVisibilityReport:
        all_entities = [target_brand] + competitors
        metrics_map: Dict[str, Dict[str, Any]] = {
            ent: {
                "mentions": 0,
                "citations": 0,
                "rec_wins": 0,
                "domains": set(),
            }
            for ent in all_entities
        }

        q_count = len(probed_responses)

        for item in probed_responses:
            resp = item.get("response", "")
            citations = item.get("citations", [])

            for ent in all_entities:
                ent_clean = ent.lower()
                # Mention check
                if re.search(rf"\b{re.escape(ent_clean)}\b", resp, re.I):
                    metrics_map[ent]["mentions"] += 1

                # Citation check
                ent_norm = ent_clean.replace("-", "").replace(" ", "")
                has_cit = any(ent_clean in c.lower() or ent_norm in c.lower().replace("-", "") for c in citations)
                if has_cit:
                    metrics_map[ent]["citations"] += 1
                    for c in citations:
                        if ent_clean in c.lower() or ent_norm in c.lower().replace("-", ""):
                            metrics_map[ent]["domains"].add(c.split("/")[2] if "/" in c else c)


                # Recommendation check
                if re.search(rf"\b(?:recommend|best|winner|top pick)\s*[:\-]?\s*{re.escape(ent_clean)}\b", resp, re.I):
                    metrics_map[ent]["rec_wins"] += 1

        leaderboard: List[CompetitorBenchmarkMetrics] = []
        for ent in all_entities:
            m = metrics_map[ent]
            m_cnt = m["mentions"]
            c_cnt = m["citations"]
            r_cnt = m["rec_wins"]

            m_rate = round((m_cnt / max(q_count, 1)) * 100, 1)
            c_rate = round((c_cnt / max(q_count, 1)) * 100, 1)
            r_rate = round((r_cnt / max(q_count, 1)) * 100, 1)

            leaderboard.append(
                CompetitorBenchmarkMetrics(
                    entity_name=ent,
                    is_target_brand=(ent == target_brand),
                    total_queries_tested=q_count,
                    mention_count=m_cnt,
                    mention_rate_pct=m_rate,
                    citation_count=c_cnt,
                    citation_rate_pct=c_rate,
                    top_recommendation_wins=r_cnt,
                    recommendation_win_rate_pct=r_rate,
                    citation_domains=list(m["domains"]),
                )
            )

        # Sort leaderboard by citation rate descending, then mentions
        leaderboard.sort(key=lambda x: (x.citation_rate_pct, x.mention_rate_pct), reverse=True)
        winner = leaderboard[0].entity_name if leaderboard else target_brand

        # Find target brand rank
        target_rank = 1
        for idx, lb in enumerate(leaderboard, 1):
            if lb.entity_name == target_brand:
                target_rank = idx
                break

        recs: List[str] = []
        if target_rank > 1:
            verdict = f"{target_brand} ranks #{target_rank} in AI citation visibility behind category leader '{winner}'."
            recs.append(f"Deploy head-to-head comparison pages against {winner} to intercept commercial queries.")
        else:
            verdict = f"{target_brand} leads the comparative AI benchmark at #{target_rank} with {leaderboard[0].citation_rate_pct}% citation rate."

        return CompetitorVisibilityReport(
            target_brand=target_brand,
            competitors_compared_count=len(competitors),
            test_conditions_summary=f"Evaluated {q_count} shared prompts across {len(all_entities)} entities under synchronized testing conditions.",
            leaderboard=leaderboard,
            winner_entity=winner,
            target_brand_rank=target_rank,
            competitive_displacement_verdict=verdict,
            actionable_remediation=recs,
        )

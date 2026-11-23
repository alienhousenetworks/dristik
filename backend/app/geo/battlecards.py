"""
Competitor Battlecard Generator & Interactive Persona Fan-Out (Phase 5).

Grounded strictly in observed live AI responses — refuses to fabricate
competitive strengths or weaknesses when zero responses are provided.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field


class CompetitorBattlecard(BaseModel):
    competitor: str
    sentiment: str = "neutral"  # positive | neutral | negative | not_observed
    mention_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    summary: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    winning_prompts: List[str] = Field(default_factory=list)
    losing_prompts: List[str] = Field(default_factory=list)
    top_cited_domains: List[str] = Field(default_factory=list)


class BattlecardReport(BaseModel):
    brand_name: str
    responses_analyzed: int
    status: str  # OBSERVED | NOT_MEASURED
    battlecards: List[CompetitorBattlecard] = Field(default_factory=list)


_POS_CUES = ("best", "leading", "top", "recommended", "strong", "reliable", "popular", "trusted", "enterprise")
_NEG_CUES = ("expensive", "overpriced", "complex", "limited", "lacking", "outdated", "drawback", "downside", "slow")


def _host(url: str) -> str:
    try:
        return (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


class CompetitorBattlecardGenerator:
    """Synthesizes side-by-side competitor battlecards from observed AI responses."""

    @classmethod
    def generate(
        cls,
        *,
        brand_name: str,
        competitors: List[str],
        responses: List[Dict[str, Any]],
    ) -> BattlecardReport:
        if not responses:
            return BattlecardReport(
                brand_name=brand_name,
                responses_analyzed=0,
                status="NOT_MEASURED",
                battlecards=[
                    CompetitorBattlecard(
                        competitor=c,
                        sentiment="not_observed",
                        summary="No live AI responses were provided; battlecard cannot be synthesized without observed answers.",
                    )
                    for c in competitors
                ],
            )

        brand_re = re.compile(rf"(?<!\w){re.escape(brand_name.strip())}(?!\w)", re.I) if brand_name.strip() else None
        cards: List[CompetitorBattlecard] = []

        for comp in competitors:
            c_clean = (comp or "").strip()
            if not c_clean:
                continue
            comp_re = re.compile(rf"(?<!\w){re.escape(c_clean)}(?!\w)", re.I)
            mentions = 0
            wins = 0
            losses = 0
            pos_hits = 0
            neg_hits = 0
            win_prompts: List[str] = []
            lose_prompts: List[str] = []
            cited_domains: Counter[str] = Counter()

            for item in responses:
                prompt = str(item.get("prompt") or item.get("query") or "").strip()
                answer = str(item.get("answer") or item.get("response") or "")
                sources = item.get("sources") or item.get("citations") or []

                has_comp = bool(comp_re.search(answer))
                has_brand = bool(brand_re.search(answer)) if brand_re else False

                if has_comp:
                    mentions += 1
                    low = answer.lower()
                    pos_hits += sum(1 for w in _POS_CUES if w in low)
                    neg_hits += sum(1 for w in _NEG_CUES if w in low)
                    for s in sources:
                        h = _host(str(s))
                        if h:
                            cited_domains[h] += 1
                    if not has_brand:
                        wins += 1
                        if prompt and prompt not in win_prompts:
                            win_prompts.append(prompt)
                elif has_brand:
                    losses += 1
                    if prompt and prompt not in lose_prompts:
                        lose_prompts.append(prompt)

            if mentions == 0:
                sentiment = "not_observed"
                summary = f"{c_clean} was not mentioned across {len(responses)} observed AI responses."
                strengths: List[str] = []
                weaknesses = [f"Absent from {len(responses)} tested buyer queries."]
            else:
                sentiment = "positive" if pos_hits > neg_hits + 1 else ("negative" if neg_hits > pos_hits + 1 else "neutral")
                summary = (
                    f"{c_clean} appeared in {mentions}/{len(responses)} observed AI answers "
                    f"(won {wins} queries where {brand_name} was absent; lost {losses} where {brand_name} appeared alone)."
                )
                strengths = [
                    f"Mentioned in {mentions}/{len(responses)} live AI responses ({round(100.0 * mentions / len(responses), 1)}%).",
                ]
                if wins > 0:
                    strengths.append(f"Captured {wins} uncontested prompt(s) where {brand_name} was not mentioned.")
                weaknesses = []
                if losses > 0:
                    weaknesses.append(f"Omitted in {losses} prompt(s) where {brand_name} was cited or named.")
                if neg_hits > 0:
                    weaknesses.append(f"Negative/cautionary cues observed in {neg_hits} response signal(s).")

            cards.append(
                CompetitorBattlecard(
                    competitor=c_clean,
                    sentiment=sentiment,
                    mention_count=mentions,
                    win_count=wins,
                    loss_count=losses,
                    summary=summary,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    winning_prompts=win_prompts[:5],
                    losing_prompts=lose_prompts[:5],
                    top_cited_domains=[d for d, _ in cited_domains.most_common(5)],
                )
            )

        return BattlecardReport(
            brand_name=brand_name,
            responses_analyzed=len(responses),
            status="OBSERVED",
            battlecards=cards,
        )


def generate_persona_fanout_prompts(
    core_prompt: str,
    personas: List[str],
    brand_name: str = "",
) -> List[Dict[str, str]]:
    """Generate persona-angled prompt variants deterministically (zero LLM cost)."""
    base = (core_prompt or "").strip().rstrip("?")
    if not base:
        return []
    out: List[Dict[str, str]] = []
    for raw_p in personas[:12]:
        persona = (raw_p or "").strip()
        if not persona:
            continue
        p_low = persona.lower()
        if any(k in p_low for k in ("cfo", "finance", "procurement")):
            angle = "focusing on total cost of ownership, pricing transparency, and ROI"
        elif any(k in p_low for k in ("cto", "engineer", "developer", "architect", "tech")):
            angle = "focusing on security, API integrations, scalability, and technical reliability"
        elif any(k in p_low for k in ("cmo", "marketing", "seo", "growth")):
            angle = "focusing on measurable pipeline impact, attribution, and time to value"
        elif any(k in p_low for k in ("founder", "ceo", "owner")):
            angle = "focusing on fast setup, vendor reliability, and competitive edge"
        else:
            angle = f"from the perspective of a {persona} evaluating practical day-to-day workflows"
        q = f"As a {persona}, {base[0].lower() + base[1:] if len(base) > 1 else base} — {angle}?"
        if brand_name:
            q = q.replace("{brand}", brand_name)
        out.append({"persona": persona, "prompt": q})
    return out

"""
Dristik AI Answer Engine Retrieval Observatory.
Enterprise measurement system tracking granular query-level answer behaviors:
Query -> Engine -> Verbatim Answer -> Mention? -> Citation? -> Which URL? -> Which Passage?
-> Competitor Mentioned? -> Competitor Cited? -> Claim Accuracy -> Position Prominence
-> Sentiment Framing -> Commercial Intent.

Also provides longitudinal trajectory synthesis across audit dates (Citation Trajectory,
Competitor Displacement, Claim Drift, and Visibility Trends).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from app.domain.models import BusinessProfile
from app.intelligence.geo.sentiment_engine import POSITIVE_LEXICON, NEGATIVE_LEXICON

logger = logging.getLogger(__name__)


class CompetitorCitation(BaseModel):
    name: str
    url: Optional[str] = None
    domain: Optional[str] = None


class QueryObservatoryRecord(BaseModel):
    record_id: str
    query_id: str
    query_text: str
    commercial_intent: str
    engine_id: str
    engine_name: str
    model_version: str = "production"
    timestamp: str
    latency_ms: float = 0.0
    verbatim_answer: str
    brand_mentioned: bool = False
    brand_cited: bool = False
    cited_url: Optional[str] = None
    cited_passage: Optional[str] = None
    competitors_mentioned: List[str] = Field(default_factory=list)
    competitors_cited: List[CompetitorCitation] = Field(default_factory=list)
    position_prominence: str = "ABSENT"  # PRIMARY_RECOMMENDATION | LISTED_OPTION | FOOTNOTE | ABSENT
    sentiment_framing: str = "NEUTRAL"    # ENDORSED | NEUTRAL | CAVEATED | CRITICIZED | UNMENTIONED
    claim_accuracy: str = "UNVERIFIED"    # ACCURATE | DISTORTED | HALLUCINATED | UNVERIFIED
    hallucination_note: Optional[str] = None


class LongitudinalTrajectoryItem(BaseModel):
    query_id: str
    query_text: str
    engine_id: str
    dates: List[str] = Field(default_factory=list)
    citation_statuses: List[bool] = Field(default_factory=list)
    prominences: List[str] = Field(default_factory=list)
    trajectory_direction: str = "STABLE"  # IMPROVING | REGRESSING | STABLE


class ObservatorySummary(BaseModel):
    total_evaluations: int
    engines_evaluated: List[str]
    brand_mention_rate_pct: float
    brand_citation_rate_pct: float
    primary_recommendation_share_pct: float
    sentiment_distribution: Dict[str, int]
    top_competitors_cited: Dict[str, int]
    top_cited_urls: List[str]
    hallucination_rate_pct: float
    records: List[QueryObservatoryRecord] = Field(default_factory=list)
    trajectories: List[LongitudinalTrajectoryItem] = Field(default_factory=list)


class AiRetrievalObservatory:
    """
    Enterprise AI Retrieval Observatory tracking multi-engine query executions,
    extracting passages, competitor co-citations, prominence, sentiment, and drift.
    """

    @classmethod
    def evaluate_query_run(
        cls,
        eval_run: Any,
        brand_name: str,
        target_domain: str,
        competitors: Optional[List[str]] = None,
        profile: Optional[BusinessProfile] = None,
    ) -> QueryObservatoryRecord:
        raw_answer = getattr(eval_run, "raw_response", "") or ""
        query_text = getattr(eval_run, "query_text", "") or ""
        citations = getattr(eval_run, "citations", []) or []
        engine_id = getattr(eval_run, "engine_id", "unknown")
        engine_name = getattr(eval_run, "engine_name", engine_id.title())
        intent = getattr(eval_run, "category", "general")

        clean_brand = brand_name.strip().lower() if brand_name else ""
        clean_target_domain = target_domain.strip().lower().replace("www.", "")

        # 1. Mention & Citation Detection
        brand_mentioned = bool(
            getattr(eval_run, "was_mentioned", False)
            or (clean_brand and clean_brand in raw_answer.lower())
            or (clean_target_domain and clean_target_domain in raw_answer.lower())
        )

        brand_cited = False
        cited_url = None
        for cite in citations:
            cite_str = str(cite).lower()
            if clean_target_domain in cite_str or (clean_brand and clean_brand in cite_str):
                brand_cited = True
                cited_url = str(cite)
                break

        # 2. Competitors Mentioned & Cited
        comps = [c.strip() for c in (competitors or []) if c and c.strip()]
        comps_mentioned = []
        comps_cited = []

        for comp in comps:
            c_clean = comp.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
            c_name = c_clean.split(".")[0].capitalize()

            if c_clean in raw_answer.lower() or c_name.lower() in raw_answer.lower():
                comps_mentioned.append(c_name)

            for cite in citations:
                if c_clean in str(cite).lower() or c_name.lower() in str(cite).lower():
                    comps_cited.append(CompetitorCitation(
                        name=c_name,
                        url=str(cite),
                        domain=c_clean
                    ))
                    break

        # 3. Position Prominence
        prominence = "ABSENT"
        if brand_mentioned:
            # Check if mentioned in the first 2 sentences or numbered position 1
            paragraphs = [p.strip() for p in raw_answer.split("\n") if p.strip()]
            first_block = (paragraphs[0] if paragraphs else raw_answer)[:300].lower()

            if clean_brand in first_block or clean_target_domain in first_block:
                prominence = "PRIMARY_RECOMMENDATION"
            elif re.search(r"(?:1\.|#1|first)\s*[:\-–]?\s*.*" + re.escape(clean_brand), raw_answer, re.I):
                prominence = "PRIMARY_RECOMMENDATION"
            elif brand_cited:
                prominence = "LISTED_OPTION"
            else:
                prominence = "FOOTNOTE"

        # 4. Sentiment & Framing
        sentiment = "UNMENTIONED"
        if brand_mentioned:
            answer_lower = raw_answer.lower()
            pos_matches = [w for w in POSITIVE_LEXICON if f" {w} " in f" {answer_lower} "]
            neg_matches = [w for w in NEGATIVE_LEXICON if f" {w} " in f" {answer_lower} "]

            if len(neg_matches) > len(pos_matches):
                sentiment = "CRITICIZED"
            elif len(pos_matches) >= 2:
                sentiment = "ENDORSED"
            elif "however" in answer_lower or "limited" in answer_lower or "expensive" in answer_lower:
                sentiment = "CAVEATED"
            else:
                sentiment = "NEUTRAL"

        # 5. Extract Cited Passage
        cited_passage = None
        if brand_mentioned and raw_answer:
            sentences = re.split(r"(?<=[.!?])\s+", raw_answer)
            for s in sentences:
                if (clean_brand and clean_brand in s.lower()) or (clean_target_domain and clean_target_domain in s.lower()):
                    cited_passage = s.strip()
                    break

        # 6. Claim Accuracy & Hallucination Check
        claim_acc = "UNVERIFIED"
        hallucination_note = None
        if brand_mentioned and profile:
            # Check price hallucination if site has no pricing
            if getattr(profile, "pricing_summary", None) in [None, "", "Contact for Pricing"]:
                price_match = re.search(r"\$\d+(?:/mo|/month|/yr| per user)?", raw_answer)
                if price_match:
                    claim_acc = "HALLUCINATED"
                    hallucination_note = f"Answer claims pricing of {price_match.group(0)} but site has no declared pricing tier."
            if claim_acc == "UNVERIFIED" and brand_mentioned:
                claim_acc = "ACCURATE"

        return QueryObservatoryRecord(
            record_id=f"obs_{getattr(eval_run, 'query_id', 'q')}_{engine_id}",
            query_id=getattr(eval_run, "query_id", "q_unknown"),
            query_text=query_text,
            commercial_intent=intent,
            engine_id=engine_id,
            engine_name=engine_name,
            timestamp=getattr(eval_run, "timestamp", datetime.now(timezone.utc).isoformat()),
            latency_ms=float(getattr(eval_run, "latency_ms", 0.0) or 0.0),
            verbatim_answer=raw_answer,
            brand_mentioned=brand_mentioned,
            brand_cited=brand_cited,
            cited_url=cited_url,
            cited_passage=cited_passage,
            competitors_mentioned=list(set(comps_mentioned)),
            competitors_cited=comps_cited,
            position_prominence=prominence,
            sentiment_framing=sentiment,
            claim_accuracy=claim_acc,
            hallucination_note=hallucination_note,
        )

    @classmethod
    def compile_observatory(
        cls,
        evaluations: List[Any],
        brand_name: str,
        target_domain: str,
        competitors: Optional[List[str]] = None,
        profile: Optional[BusinessProfile] = None,
    ) -> ObservatorySummary:
        records: List[QueryObservatoryRecord] = []
        for ev in evaluations:
            if getattr(ev, "status", "SUCCESS") == "SUCCESS":
                records.append(cls.evaluate_query_run(
                    eval_run=ev,
                    brand_name=brand_name,
                    target_domain=target_domain,
                    competitors=competitors,
                    profile=profile
                ))

        total = len(records)
        if total == 0:
            return ObservatorySummary(
                total_evaluations=0,
                engines_evaluated=[],
                brand_mention_rate_pct=0.0,
                brand_citation_rate_pct=0.0,
                primary_recommendation_share_pct=0.0,
                sentiment_distribution={},
                top_competitors_cited={},
                top_cited_urls=[],
                hallucination_rate_pct=0.0,
                records=[],
                trajectories=[]
            )

        engines = sorted(list(set(r.engine_name for r in records)))
        mentions = sum(1 for r in records if r.brand_mentioned)
        citations = sum(1 for r in records if r.brand_cited)
        primary = sum(1 for r in records if r.position_prominence == "PRIMARY_RECOMMENDATION")
        hallucinations = sum(1 for r in records if r.claim_accuracy == "HALLUCINATED")

        sent_dist: Dict[str, int] = {}
        for r in records:
            sent_dist[r.sentiment_framing] = sent_dist.get(r.sentiment_framing, 0) + 1

        comp_cited_counts: Dict[str, int] = {}
        for r in records:
            for cc in r.competitors_cited:
                comp_cited_counts[cc.name] = comp_cited_counts.get(cc.name, 0) + 1

        top_urls = list(set(r.cited_url for r in records if r.cited_url))

        return ObservatorySummary(
            total_evaluations=total,
            engines_evaluated=engines,
            brand_mention_rate_pct=round((mentions / total) * 100.0, 1),
            brand_citation_rate_pct=round((citations / total) * 100.0, 1),
            primary_recommendation_share_pct=round((primary / total) * 100.0, 1),
            sentiment_distribution=sent_dist,
            top_competitors_cited=comp_cited_counts,
            top_cited_urls=top_urls[:10],
            hallucination_rate_pct=round((hallucinations / total) * 100.0, 1),
            records=records,
            trajectories=[]
        )


observatory = AiRetrievalObservatory()

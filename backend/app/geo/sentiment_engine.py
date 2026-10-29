"""
Dristik AI GEO Sentiment, Attribute Perception & Ground-Truth Hallucination Engine.
Analyzes verbatim responses from AI answer engines (ChatGPT, Perplexity, Gemini, Claude)
to evaluate brand sentiment polarity, extracted brand attribute perceptions, and
detect factual hallucinations / distortions against verified ground-truth business profiles.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.domain.models import BusinessProfile

logger = logging.getLogger(__name__)


class BrandPerceptionScore(BaseModel):
    brand_name: str
    sentiment: str = "NEUTRAL"  # POSITIVE | NEUTRAL | SKEPTICAL | NEGATIVE
    sentiment_score: float = 0.0  # -1.0 (most negative) to +1.0 (most positive)
    attributed_traits: List[str] = Field(default_factory=list)
    positive_signals: List[str] = Field(default_factory=list)
    negative_signals: List[str] = Field(default_factory=list)
    quote_snippets: List[str] = Field(default_factory=list)
    hallucination_detected: bool = False
    hallucination_details: Optional[str] = None
    confidence: float = 0.85


class HallucinationItem(BaseModel):
    hallucination_id: str
    query_id: Optional[str] = None
    engine_id: str
    claim_text: str
    ground_truth_fact: str
    category: str  # PRICING | ARCHITECTURE | FEATURE_ABSENCE | COMPLIANCE | ENTITY_IDENTITY
    severity: str = "HIGH"  # CRITICAL | HIGH | MEDIUM


class HallucinationAuditReport(BaseModel):
    total_evaluated: int
    clean_responses: int
    hallucinated_responses: int
    hallucination_rate_pct: float
    detected_distortions: List[HallucinationItem] = Field(default_factory=list)
    overall_sentiment_distribution: Dict[str, int] = Field(default_factory=dict)
    top_attributed_traits: Dict[str, int] = Field(default_factory=dict)


# Lexical sentiment indicators tailored to B2B/B2C software and services
POSITIVE_LEXICON = {
    "leading", "industry-standard", "best", "top-tier", "robust", "scalable",
    "intuitive", "seamless", "exceptional", "highly recommended", "preferred",
    "flexible", "reliable", "comprehensive", "powerful", "innovative", "modern",
    "advanced", "efficient", "cost-effective", "leader", "pioneer", "gold standard"
}

NEGATIVE_LEXICON = {
    "expensive", "costly", "complex", "clunky", "steep learning curve", "outdated",
    "legacy", "slow", "buggy", "limited", "lacks", "difficult to configure",
    "cumbersome", "inflexible", "poor support", "overpriced", "unreliable",
    "frustrating", "opaque pricing", "vendor lock-in", "security concerns"
}

TRAIT_DICTIONARY: Dict[str, List[str]] = {
    "Enterprise Ready": ["enterprise-grade", "large organizations", "fortune 500", "soc2", "compliance", "sso"],
    "Developer Friendly": ["api-first", "developer-centric", "sdk", "cli", "gitops", "code-first", "extensible"],
    "Budget Friendly / Accessible": ["affordable", "freemium", "free tier", "open-source", "transparent pricing", "low cost"],
    "High Learning Curve": ["steep learning curve", "complex setup", "requires training", "specialized knowledge"],
    "Premium / Expensive": ["expensive", "enterprise pricing only", "high cost", "custom quote required"],
    "Modern / Innovative": ["modern", "cutting-edge", "next-gen", "ai-powered", "state-of-the-art", "innovative"],
    "Turnkey / Easy Setup": ["plug-and-play", "intuitive", "easy setup", "no-code", "low friction", "out of the box"],
    "Niche Specialist": ["tailored for", "specialized in", "niche", "vertical-specific", "bespoke"]
}


class GeoSentimentEngine:
    """
    Evaluates how AI models represent a brand across queries.
    Detects brand sentiment, attributed characteristics, and verifies facts against crawl ground truth.
    """

    def analyze_response_sentiment(
        self,
        raw_response: str,
        brand_name: str,
        ground_truth_profile: Optional[BusinessProfile] = None,
        engine_id: str = "generic",
        query_id: Optional[str] = None
    ) -> BrandPerceptionScore:
        if not raw_response or not brand_name:
            return BrandPerceptionScore(brand_name=brand_name)

        brand_clean = brand_name.strip().lower()
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", raw_response) if s.strip()]

        # Filter sentences mentioning brand or immediate pronoun continuity
        mention_sentences: List[str] = []
        for i, s in enumerate(sentences):
            if brand_clean in s.lower():
                mention_sentences.append(s)
                # Check next sentence if it refers to the brand via pronoun or continuity
                if i + 1 < len(sentences):
                    next_s = sentences[i + 1]
                    next_low = next_s.lower()
                    if next_low.startswith(("it ", "they ", "this ", "the platform", "the company", "the tool", "the solution")):
                        mention_sentences.append(next_s)

        if not mention_sentences:
            return BrandPerceptionScore(
                brand_name=brand_name,
                sentiment="NEUTRAL",
                sentiment_score=0.0
            )

        pos_hits: List[str] = []
        neg_hits: List[str] = []
        traits: Set[str] = set()

        combined_mentions = " ".join(mention_sentences).lower()

        # Score positive and negative hits
        for pos_word in POSITIVE_LEXICON:
            if re.search(r"\b" + re.escape(pos_word) + r"\b", combined_mentions):
                pos_hits.append(pos_word)

        for neg_word in NEGATIVE_LEXICON:
            if re.search(r"\b" + re.escape(neg_word) + r"\b", combined_mentions):
                neg_hits.append(neg_word)

        # Detect traits
        for trait_name, keywords in TRAIT_DICTIONARY.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", combined_mentions):
                    traits.add(trait_name)
                    break

        # Calculate sentiment polarity (-1.0 to +1.0)
        pos_count = len(pos_hits)
        neg_count = len(neg_hits)
        total_hits = pos_count + neg_count

        if total_hits == 0:
            sentiment = "NEUTRAL"
            score = 0.0
        else:
            score = round((pos_count - neg_count) / max(1, total_hits), 2)
            if score >= 0.25:
                sentiment = "POSITIVE"
            elif score <= -0.25:
                sentiment = "NEGATIVE"
            elif neg_count > 0:
                sentiment = "SKEPTICAL"
            else:
                sentiment = "NEUTRAL"

        # Check hallucinations if profile is present
        hallucination_detected = False
        hallucination_details: Optional[str] = None

        if ground_truth_profile:
            distortions = self._check_hallucinations(
                text=combined_mentions,
                brand_name=brand_name,
                profile=ground_truth_profile,
                engine_id=engine_id,
                query_id=query_id
            )
            if distortions:
                hallucination_detected = True
                hallucination_details = "; ".join([d.claim_text + f" (Actual: {d.ground_truth_fact})" for d in distortions])

        return BrandPerceptionScore(
            brand_name=brand_name,
            sentiment=sentiment,
            sentiment_score=score,
            attributed_traits=sorted(list(traits)),
            positive_signals=pos_hits[:5],
            negative_signals=neg_hits[:5],
            quote_snippets=mention_sentences[:3],
            hallucination_detected=hallucination_detected,
            hallucination_details=hallucination_details,
            confidence=0.88
        )

    def _check_hallucinations(
        self,
        text: str,
        brand_name: str,
        profile: BusinessProfile,
        engine_id: str,
        query_id: Optional[str]
    ) -> List[HallucinationItem]:
        """
        Cross-checks model assertions against ground-truth profile.
        Detects contradictions in pricing, architecture (cloud vs on-prem), and core capabilities.
        """
        distortions: List[HallucinationItem] = []
        low_text = text.lower()

        # 1. Architecture Check (e.g. claiming SaaS is on-prem only or vice versa)
        if getattr(profile, "business_model", None):
            model_type = str(profile.business_model).lower()
            if "saas" in model_type or "cloud" in model_type:
                if re.search(r"\b(only\s+available\s+on-premise|self-hosted\s+only|no\s+cloud\s+offering)\b", low_text):
                    distortions.append(HallucinationItem(
                        hallucination_id=f"HAL-ARCH-{len(distortions)+1}",
                        query_id=query_id,
                        engine_id=engine_id,
                        claim_text="Stated product is self-hosted / on-premise only without cloud",
                        ground_truth_fact=f"Verified business model is {profile.business_model}",
                        category="ARCHITECTURE",
                        severity="CRITICAL"
                    ))

        # 2. Free Tier / Pricing Check
        if hasattr(profile, "pricing_transparency") and getattr(profile, "pricing_transparency", None) == "transparent":
            # If the model says pricing is completely unknown or unavailable
            if re.search(r"\b(pricing\s+is\s+not\s+public|unknown\s+cost|must\s+contact\s+sales\s+for\s+any\s+pricing)\b", low_text):
                distortions.append(HallucinationItem(
                    hallucination_id=f"HAL-PRICE-{len(distortions)+1}",
                    query_id=query_id,
                    engine_id=engine_id,
                    claim_text="Reported pricing is private or contact-sales only",
                    ground_truth_fact="Website features transparent public pricing plans",
                    category="PRICING",
                    severity="HIGH"
                ))

        # 3. Features Absence Hallucination (claiming product doesn't support X when site explicitly lists X)
        services = [str(s).lower() for s in (getattr(profile, "services", []) or [])]
        products = [str(p).lower() for p in (getattr(profile, "products", []) or [])]
        all_offerings = set(services + products)

        if "api" in all_offerings or any("api" in o for o in all_offerings):
            if re.search(r"\b(does\s+not\s+(offer|provide|have)\s+an\s+api|no\s+api\s+access)\b", low_text):
                distortions.append(HallucinationItem(
                    hallucination_id=f"HAL-FEAT-{len(distortions)+1}",
                    query_id=query_id,
                    engine_id=engine_id,
                    claim_text="Claimed product has no API access",
                    ground_truth_fact="Verified API access and developer endpoints are available",
                    category="FEATURE_ABSENCE",
                    severity="HIGH"
                ))

        return distortions

    def generate_audit_report(
        self,
        evaluations: List[Any],
        brand_name: str,
        ground_truth_profile: Optional[BusinessProfile] = None
    ) -> HallucinationAuditReport:
        """
        Aggregates sentiment, trait frequency, and hallucination counts across an entire benchmark run.
        """
        total = len(evaluations)
        if total == 0:
            return HallucinationAuditReport(
                total_evaluated=0,
                clean_responses=0,
                hallucinated_responses=0,
                hallucination_rate_pct=0.0
            )

        distortions: List[HallucinationItem] = []
        sentiment_dist: Dict[str, int] = {"POSITIVE": 0, "NEUTRAL": 0, "SKEPTICAL": 0, "NEGATIVE": 0}
        trait_counts: Dict[str, int] = {}
        hallucinated_runs = 0

        for run in evaluations:
            raw = getattr(run, "raw_response", "") or ""
            eng = getattr(run, "engine_id", "generic")
            qid = getattr(run, "query_id", None)
            
            res = self.analyze_response_sentiment(
                raw_response=raw,
                brand_name=brand_name,
                ground_truth_profile=ground_truth_profile,
                engine_id=eng,
                query_id=qid
            )

            sentiment_dist[res.sentiment] = sentiment_dist.get(res.sentiment, 0) + 1
            for trait in res.attributed_traits:
                trait_counts[trait] = trait_counts.get(trait, 0) + 1

            if res.hallucination_detected:
                hallucinated_runs += 1
                if ground_truth_profile:
                    distortions.extend(self._check_hallucinations(
                        text=raw,
                        brand_name=brand_name,
                        profile=ground_truth_profile,
                        engine_id=eng,
                        query_id=qid
                    ))

        clean_count = total - hallucinated_runs
        hallucination_pct = round((hallucinated_runs / max(1, total)) * 100, 1)

        return HallucinationAuditReport(
            total_evaluated=total,
            clean_responses=clean_count,
            hallucinated_responses=hallucinated_runs,
            hallucination_rate_pct=hallucination_pct,
            detected_distortions=distortions,
            overall_sentiment_distribution=sentiment_dist,
            top_attributed_traits=dict(sorted(trait_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        )


geo_sentiment_engine = GeoSentimentEngine()

"""
Search Intent & Demand Intelligence — Phase 3.5

Develops the Search Intent Agent covering 12 sub-phases:
1. Keyword extraction
2. Query classification
3. Intent classification (Commercial, Informational, Navigational, Transactional)
4. Commercial intent analysis
5. Informational intent analysis
6. Navigational intent analysis
7. Transactional intent analysis
8. Page-to-query mapping
9. Keyword cannibalization
10. Missing topic identification
11. Content gap analysis
12. Search journey mapping

STRICT GUARDRAIL:
With GSC connected, incorporates real queries, clicks, impressions, and CTR.
Without GSC, explicitly flags search demand as UNMEASURED and reports extracted on-page topics only.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SearchIntentType(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    COMMERCIAL = "COMMERCIAL"
    TRANSACTIONAL = "TRANSACTIONAL"
    NAVIGATIONAL = "NAVIGATIONAL"


class SearchDemandSource(str, Enum):
    GSC_VERIFIED = "GSC_VERIFIED"
    ON_PAGE_EXTRACTED = "ON_PAGE_EXTRACTED"
    UNMEASURED = "UNMEASURED"


class QueryIntentMapping(BaseModel):
    query: str
    intent: SearchIntentType
    primary_url_target: str
    confidence: float
    gsc_impressions: Optional[int] = None
    gsc_clicks: Optional[int] = None
    gsc_ctr: Optional[float] = None
    demand_source: SearchDemandSource = SearchDemandSource.ON_PAGE_EXTRACTED


class KeywordCannibalizationFinding(BaseModel):
    query: str
    competing_urls: List[str]
    intent: SearchIntentType
    recommended_canonical_url: str
    remediation_action: str


class SearchJourneyStage(BaseModel):
    stage_name: str  # Top-of-Funnel, Mid-Funnel, Bottom-of-Funnel
    intent_target: SearchIntentType
    pages_assigned: List[str]
    topic_coverage_status: str  # ADEQUATE, GAP_DETECTED


class SearchIntentReport(BaseModel):
    domain: str
    has_gsc_connected: bool
    demand_measurement_statement: str
    mapped_queries: List[QueryIntentMapping] = Field(default_factory=list)
    cannibalization_issues: List[KeywordCannibalizationFinding] = Field(default_factory=list)
    content_gaps: List[str] = Field(default_factory=list)
    search_journey: List[SearchJourneyStage] = Field(default_factory=list)


class SearchIntentAgent:
    """
    Classifies search intent, detects cannibalization, and maps queries to landing pages.
    """

    @classmethod
    def classify_intent(cls, text: str) -> SearchIntentType:
        low = text.lower()
        if any(w in low for w in ["buy", "order", "price", "cart", "checkout", "shop", "coupon", "discount"]):
            return SearchIntentType.TRANSACTIONAL
        elif any(w in low for w in ["best", "vs", "compare", "review", "top", "alternative", "rating"]):
            return SearchIntentType.COMMERCIAL
        elif any(w in low for w in ["login", "signin", "portal", "account", "support", "contact"]):
            return SearchIntentType.NAVIGATIONAL
        else:
            return SearchIntentType.INFORMATIONAL

    @classmethod
    def analyze_site_intent(
        cls,
        domain: str,
        pages: List[Dict[str, Any]],
        gsc_queries: Optional[List[Dict[str, Any]]] = None,
    ) -> SearchIntentReport:
        has_gsc = bool(gsc_queries)
        mapped: List[QueryIntentMapping] = []
        url_to_queries: Dict[str, List[str]] = {}
        query_to_urls: Dict[str, List[str]] = {}

        if has_gsc and gsc_queries:
            statement = "Search demand and click performance verified via connected Google Search Console data."
            for q in gsc_queries:
                q_text = q.get("query", "")
                url = q.get("page", f"https://{domain}/")
                intent = cls.classify_intent(q_text)
                mapped.append(
                    QueryIntentMapping(
                        query=q_text,
                        intent=intent,
                        primary_url_target=url,
                        confidence=0.95,
                        gsc_impressions=q.get("impressions"),
                        gsc_clicks=q.get("clicks"),
                        gsc_ctr=q.get("ctr"),
                        demand_source=SearchDemandSource.GSC_VERIFIED,
                    )
                )
                query_to_urls.setdefault(q_text.lower(), []).append(url)
        else:
            statement = "Google Search Console is not connected. Real search query volumes, impressions, and clicks are UNMEASURED. Intent is derived solely from on-page topics."
            for p in pages:
                url = p.get("url", "")
                title = p.get("title", "")
                clean_title = re.sub(r"[-|].*$", "", title).strip()
                if clean_title:
                    intent = cls.classify_intent(f"{url} {clean_title}")
                    mapped.append(
                        QueryIntentMapping(
                            query=clean_title.lower(),
                            intent=intent,
                            primary_url_target=url,
                            confidence=0.80,
                            demand_source=SearchDemandSource.ON_PAGE_EXTRACTED,
                        )
                    )
                    query_to_urls.setdefault(clean_title.lower(), []).append(url)

        # Detect Keyword Cannibalization
        cannibalization: List[KeywordCannibalizationFinding] = []
        for q, u_list in query_to_urls.items():
            unique_urls = list(set(u_list))
            if len(unique_urls) > 1 and len(q) > 4:
                # Rank shortest or category url as primary
                primary_url = sorted(unique_urls, key=lambda x: (len(x.split("/")), len(x)))[0]
                cannibalization.append(
                    KeywordCannibalizationFinding(
                        query=q,
                        competing_urls=unique_urls,
                        intent=cls.classify_intent(q),
                        recommended_canonical_url=primary_url,
                        remediation_action=f"Consolidate intent around {primary_url} by redirecting or adjusting internal link anchors from competing URLs.",
                    )
                )

        # Search Journey Mapping
        top_funnel = [m.primary_url_target for m in mapped if m.intent == SearchIntentType.INFORMATIONAL]
        mid_funnel = [m.primary_url_target for m in mapped if m.intent == SearchIntentType.COMMERCIAL]
        bot_funnel = [m.primary_url_target for m in mapped if m.intent == SearchIntentType.TRANSACTIONAL]

        journey = [
            SearchJourneyStage(
                stage_name="Top-of-Funnel (Awareness & Education)",
                intent_target=SearchIntentType.INFORMATIONAL,
                pages_assigned=list(set(top_funnel))[:10],
                topic_coverage_status="ADEQUATE" if top_funnel else "GAP_DETECTED",
            ),
            SearchJourneyStage(
                stage_name="Mid-Funnel (Evaluation & Comparison)",
                intent_target=SearchIntentType.COMMERCIAL,
                pages_assigned=list(set(mid_funnel))[:10],
                topic_coverage_status="ADEQUATE" if mid_funnel else "GAP_DETECTED",
            ),
            SearchJourneyStage(
                stage_name="Bottom-of-Funnel (Conversion & Purchase)",
                intent_target=SearchIntentType.TRANSACTIONAL,
                pages_assigned=list(set(bot_funnel))[:10],
                topic_coverage_status="ADEQUATE" if bot_funnel else "GAP_DETECTED",
            ),
        ]

        content_gaps = []
        if not mid_funnel:
            content_gaps.append("Missing Commercial Comparison Pages (Mid-funnel comparison and alternative guides).")
        if not top_funnel:
            content_gaps.append("Missing Authoritative Informational Hubs (Educational query coverage).")

        return SearchIntentReport(
            domain=domain,
            has_gsc_connected=has_gsc,
            demand_measurement_statement=statement,
            mapped_queries=mapped[:20],
            cannibalization_issues=cannibalization,
            content_gaps=content_gaps,
            search_journey=journey,
        )

"""
Dristik AI Competitor Multi-Signal Classifier.
Assigns multi-label classification to competitors based on observed demand overlap:
DIRECT, SEARCH, GEO, CONTENT, COMMERCIAL, LOCAL, INDIRECT, EMERGING.
A competitor can belong to multiple categories.
"""
from __future__ import annotations

from typing import List, Set, Optional, Dict, Any
from app.seo.competitive.models import CompetitorType


class CompetitorClassifier:
    """
    Classifies discovered competitor domains across Dristik's 8 competitive dimensions.
    """

    def classify_competitor(
        self,
        domain: str,
        overlap_signals: Dict[str, Any],
    ) -> List[CompetitorType]:
        """
        Determines the competitor types based on empirical overlap signals:
        - keyword_overlap_pct: float (0-100)
        - ai_prompt_overlap_pct: float (0-100)
        - shared_commercial_queries: int
        - shared_content_topics: int
        - is_direct_offer_match: bool
        - is_local_geo_match: bool
        - is_emerging_signal: bool
        """
        types: Set[CompetitorType] = set()

        kw_overlap = overlap_signals.get("keyword_overlap_pct", 0.0) or 0.0
        ai_overlap = overlap_signals.get("ai_prompt_overlap_pct", 0.0) or 0.0
        comm_queries = overlap_signals.get("shared_commercial_queries", 0) or 0
        topics = overlap_signals.get("shared_content_topics", 0) or 0
        direct_match = overlap_signals.get("is_direct_offer_match", False)
        local_match = overlap_signals.get("is_local_geo_match", False)
        emerging = overlap_signals.get("is_emerging_signal", False)

        # 1. Direct Competitor
        if direct_match or (kw_overlap >= 35.0 and ai_overlap >= 30.0):
            types.add(CompetitorType.DIRECT)

        # 2. Search Competitor
        if kw_overlap >= 15.0 or overlap_signals.get("serp_rank_overlap", False):
            types.add(CompetitorType.SEARCH)

        # 3. GEO Competitor
        if ai_overlap >= 20.0 or overlap_signals.get("cited_in_ai_prompts", False):
            types.add(CompetitorType.GEO)

        # 4. Commercial Competitor
        if comm_queries >= 1 or overlap_signals.get("competes_on_pricing_or_vs", False):
            types.add(CompetitorType.COMMERCIAL)

        # 5. Content Competitor
        if topics >= 2 or overlap_signals.get("competes_on_guides_or_faqs", False):
            types.add(CompetitorType.CONTENT)

        # 6. Local Competitor
        if local_match:
            types.add(CompetitorType.LOCAL)

        # 7. Emerging Competitor
        if emerging:
            types.add(CompetitorType.EMERGING)

        # 8. Indirect Competitor (fallback if adjacent but not direct)
        if not types:
            types.add(CompetitorType.INDIRECT)
        elif not direct_match and len(types) == 1 and CompetitorType.CONTENT in types:
            types.add(CompetitorType.INDIRECT)

        # Sort logically
        order = [
            CompetitorType.DIRECT,
            CompetitorType.SEARCH,
            CompetitorType.GEO,
            CompetitorType.COMMERCIAL,
            CompetitorType.CONTENT,
            CompetitorType.LOCAL,
            CompetitorType.EMERGING,
            CompetitorType.INDIRECT,
        ]
        return [t for t in order if t in types]


competitor_classifier = CompetitorClassifier()

"""
Dristik AI Dimension Similarity Scorer & Competitor Classifier
Calculates 5-dimension weighted similarity:
  - Offering Overlap (35%)
  - Buyer Persona Match (25%)
  - Scale Parity (20%)
  - Search / Query Overlap (15%)
  - Geography & Language (5%)
Classifies rivals into DIRECT, ASPIRATIONAL, INDIRECT, or SEARCH_ONLY.
Eliminates enterprise conglomerates for boutique targets via continuous mathematical distance.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from app.intelligence.competitive.models import CompetitorType

logger = logging.getLogger("dristik.similarity_scorer")


class SimilarityScorer:
    """
    Evaluates multi-dimensional similarity between target business and candidate rivals.
    """

    def compute_similarity(
        self,
        target_profile: Dict[str, Any],
        candidate_profile: Dict[str, Any],
        shared_queries: Optional[List[str]] = None,
    ) -> Tuple[float, Dict[str, float], CompetitorType, str]:
        """
        Computes overall similarity score (0.0 to 1.0), dimensional breakdown,
        competitor classification tier, and evidence-grounded explanation.
        """
        # 1. Scale Parity (20%)
        target_scale = float(target_profile.get("scale_score") or 0.25)
        cand_scale = float(candidate_profile.get("scale_score") or 0.25)
        scale_distance = abs(target_scale - cand_scale)
        scale_parity = max(0.0, round(1.0 - scale_distance, 3))

        # 2. Offering Overlap (35%)
        target_services = [s.lower() for s in target_profile.get("services") or []]
        cand_services = [s.lower() for s in candidate_profile.get("services") or []]
        target_niche = (target_profile.get("niche") or "").lower()
        cand_niche = (candidate_profile.get("niche") or "").lower()

        offer_hits = 0
        total_eval = max(1, len(target_services))
        for ts in target_services:
            if any(ts in cs or cs in ts for cs in cand_services):
                offer_hits += 1
            elif ts in cand_niche or cand_niche in ts:
                offer_hits += 0.5
        offer_overlap = min(1.0, max(0.40 if target_niche and (target_niche in cand_niche or cand_niche in target_niche) else 0.20, offer_hits / total_eval))

        # 3. Buyer & Persona Match (25%)
        target_buyer = (target_profile.get("target_buyer_persona") or "").lower()
        cand_buyer = (candidate_profile.get("target_buyer_persona") or "").lower()
        buyer_match = 0.50
        if target_buyer and cand_buyer:
            if any(w in cand_buyer for w in target_buyer.split() if len(w) > 4):
                buyer_match = 0.85
        elif scale_distance < 0.20:
            buyer_match = 0.75  # Comparable scale businesses usually serve comparable buyer tiers
        elif scale_distance > 0.50:
            buyer_match = 0.15  # Enterprise procurement vs SMB / boutique self-serve

        # 4. Search & Intent Overlap (15%)
        queries = shared_queries or []
        search_overlap = min(1.0, len(queries) * 0.3) if queries else 0.40

        # 5. Geography & Language (5%)
        target_geo = (target_profile.get("geography") or "global").lower()
        cand_geo = (candidate_profile.get("geography") or "global").lower()
        geo_match = 0.90 if target_geo in cand_geo or cand_geo in target_geo or "global" in (target_geo, cand_geo) else 0.50

        # Weighted aggregate similarity
        total_sim = round(
            (0.35 * offer_overlap)
            + (0.25 * buyer_match)
            + (0.20 * scale_parity)
            + (0.15 * search_overlap)
            + (0.05 * geo_match),
            3
        )

        breakdown = {
            "offering_overlap": round(offer_overlap, 2),
            "buyer_match": round(buyer_match, 2),
            "scale_parity": round(scale_parity, 2),
            "search_overlap": round(search_overlap, 2),
            "geography_match": round(geo_match, 2),
        }

        # Classification
        cand_domain = candidate_profile.get("domain", "")
        cand_brand = candidate_profile.get("brand_name") or cand_domain.split(".")[0].title()
        target_brand = target_profile.get("brand_name") or "Your brand"

        if cand_scale >= 0.70 and target_scale <= 0.35:
            comp_class = CompetitorType.ASPIRATIONAL
            explanation = (
                f"{cand_brand} operates in the same digital/technology domain, but at enterprise conglomerate scale "
                f"(Scale Score: {cand_scale} vs {target_brand}'s {target_scale}). Classified as an Aspirational Leader, "
                f"not a direct day-to-day bidding rival."
            )
        elif scale_distance <= 0.28 and total_sim >= 0.45:
            comp_class = CompetitorType.DIRECT
            explanation = (
                f"Direct peer match: {cand_brand} offers comparable core services to similar buyers at equivalent "
                f"market scale (Scale Score: {cand_scale} vs {target_brand}'s {target_scale}, {int(scale_parity*100)}% scale parity)."
            )
        elif search_overlap >= 0.70 and offer_overlap < 0.30:
            comp_class = CompetitorType.SEARCH_ONLY
            explanation = (
                f"{cand_brand} competes for shared search queries in this category but does not offer the same commercial services."
            )
        else:
            comp_class = CompetitorType.INDIRECT
            explanation = (
                f"{cand_brand} is an adjacent service provider addressing related customer needs with partial offering overlap."
            )

        return total_sim, breakdown, comp_class, explanation


similarity_scorer = SimilarityScorer()

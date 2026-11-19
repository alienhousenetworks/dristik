"""
Opportunity Gap Engine — Phase 7.7 (10/10 Transformation)

Synthesizes cross-discipline findings (SEO, GEO, AEO, CRO) into ranked,
actionable competitive opportunities across 5 canonical archetypes:
1. Competitors answer questions the target does not (UNANSWERED_QUESTION)
2. Competitors have stronger relevant authority signals (AUTHORITY_REPUTATION)
3. Competitors offer clearer commercial information (COMMERCIAL_CLARITY)
4. Competitors have stronger conversion journeys (CONVERSION_JOURNEY)
5. Competitors have pages covering unmet search intent (UNMET_SEARCH_INTENT)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.competitive.models import (
    CompetitiveAeoComparison,
    CompetitiveCroComparison,
    CompetitiveGeoComparison,
    CompetitiveSeoComparison,
    OpportunityGapItem,
    OpportunityGapReport,
    OpportunityGapType,
)
from app.seo.competitive.resolution.domain_normalizer import normalize_domain

logger = logging.getLogger("dristik.competitive.opportunity_gap")

EFFORT_DIVISORS = {"LOW": 1.0, "MEDIUM": 2.0, "HIGH": 3.0}


class OpportunityGapEngine:
    """
    Identifies and ranks evidence-backed competitive gaps.
    """

    def generate_opportunity_gaps(
        self,
        target_domain: str,
        seo_comparisons: List[CompetitiveSeoComparison],
        geo_comparisons: List[CompetitiveGeoComparison],
        aeo_comparisons: List[CompetitiveAeoComparison],
        cro_comparisons: List[CompetitiveCroComparison],
    ) -> OpportunityGapReport:
        clean_target = normalize_domain(target_domain)
        items: List[OpportunityGapItem] = []
        now = datetime.now(timezone.utc)

        # 1. Unanswered Questions Gap (from AEO)
        for aeo in aeo_comparisons:
            unanswered = aeo.unanswered_commercial_questions
            if unanswered:
                top_q = unanswered[0]
                item = OpportunityGapItem(
                    id=f"GAP_AEO_{aeo.competitor_domain[:8]}_01",
                    title=f"Unanswered High-Intent Question: '{top_q[:50]}...'",
                    gap_type=OpportunityGapType.UNANSWERED_QUESTION,
                    priority="P1",
                    impact_score=9,
                    effort="LOW",
                    ice_score=round((9 * 0.9) / EFFORT_DIVISORS["LOW"], 2),
                    competitor_domain=aeo.competitor_domain,
                    proof_url=f"https://{aeo.competitor_domain}/faq",
                    proof_observation_date=now,
                    description=f"{aeo.competitor_domain} provides direct answers to '{top_q}', which {clean_target} fails to address.",
                    actionable_playbook=(
                        f"Deploy an FAQ or direct answer component on {clean_target}'s primary landing page addressing '{top_q}' "
                        f"with 20-40 word self-contained extractable text and FAQPage JSON-LD schema."
                    ),
                )
                items.append(item)

        # 2. Authority & Reputation Gap (from GEO)
        for geo in geo_comparisons:
            c_tier1 = geo.source_credibility.get("competitor_tier1_citations", 0)
            t_tier1 = geo.source_credibility.get("target_tier1_citations", 0)
            if c_tier1 > t_tier1:
                item = OpportunityGapItem(
                    id=f"GAP_GEO_{geo.competitor_domain[:8]}_02",
                    title=f"Third-Party AI Citation Deficit vs {geo.competitor_domain}",
                    gap_type=OpportunityGapType.AUTHORITY_REPUTATION,
                    priority="P1",
                    impact_score=8,
                    effort="MEDIUM",
                    ice_score=round((8 * 0.8) / EFFORT_DIVISORS["MEDIUM"], 2),
                    competitor_domain=geo.competitor_domain,
                    proof_url=f"https://{geo.competitor_domain}/",
                    proof_observation_date=now,
                    description=(
                        f"{geo.competitor_domain} has {c_tier1} Tier-1 independent citations compared to {t_tier1} for {clean_target}, "
                        f"resulting in higher recommendation win rates across AI answer engines."
                    ),
                    actionable_playbook=(
                        "Target authoritative industry registries, category roundups, and co-citation partner pages "
                        "to build independent third-party credibility references that generative models recognize."
                    ),
                )
                items.append(item)

        # 3. Clearer Commercial Information Gap (from CRO)
        for cro in cro_comparisons:
            c_pricing = cro.pricing_visibility.get("competitor_public_pricing_page", False)
            t_pricing = cro.pricing_visibility.get("target_public_pricing_page", False)
            if c_pricing and not t_pricing:
                item = OpportunityGapItem(
                    id=f"GAP_CRO_{cro.competitor_domain[:8]}_03",
                    title=f"Missing Public Pricing Transparency vs {cro.competitor_domain}",
                    gap_type=OpportunityGapType.COMMERCIAL_CLARITY,
                    priority="P1",
                    impact_score=9,
                    effort="MEDIUM",
                    ice_score=round((9 * 0.85) / EFFORT_DIVISORS["MEDIUM"], 2),
                    competitor_domain=cro.competitor_domain,
                    proof_url=f"https://{cro.competitor_domain}/pricing",
                    proof_observation_date=now,
                    description=(
                        f"{cro.competitor_domain} publishes clear tiered pricing while {clean_target} requires demo booking, "
                        "introducing buyer evaluation drop-off."
                    ),
                    actionable_playbook=(
                        "Publish a dedicated /pricing page with transparent feature comparison matrix, starting price tiers, "
                        "and self-service trial entry points."
                    ),
                )
                items.append(item)

        # 4. Conversion Journey Gap (from CRO)
        for cro in cro_comparisons:
            c_ctas = cro.cta_placement.get("competitor_ctas_detected_count", 0)
            t_ctas = cro.cta_placement.get("target_ctas_detected_count", 0)
            if c_ctas > t_ctas + 2:
                item = OpportunityGapItem(
                    id=f"GAP_CRO_{cro.competitor_domain[:8]}_04",
                    title=f"Conversion CTA Density Gap vs {cro.competitor_domain}",
                    gap_type=OpportunityGapType.CONVERSION_JOURNEY,
                    priority="P2",
                    impact_score=7,
                    effort="LOW",
                    ice_score=round((7 * 0.9) / EFFORT_DIVISORS["LOW"], 2),
                    competitor_domain=cro.competitor_domain,
                    proof_url=f"https://{cro.competitor_domain}/",
                    proof_observation_date=now,
                    description=f"{cro.competitor_domain} provides persistent action triggers across templates, reducing funnel friction.",
                    actionable_playbook="Implement a sticky header CTA and secondary proof-reassurance action blocks at scroll midpoint.",
                )
                items.append(item)

        # 5. Unmet Search Intent Gap (from SEO)
        for seo in seo_comparisons:
            comp_exclusive = seo.keyword_coverage.get("competitor_exclusive_keywords_sample", [])
            if comp_exclusive:
                top_kw = comp_exclusive[0]
                item = OpportunityGapItem(
                    id=f"GAP_SEO_{seo.competitor_domain[:8]}_05",
                    title=f"Unmet Search Intent Keyword: '{top_kw}'",
                    gap_type=OpportunityGapType.UNMET_SEARCH_INTENT,
                    priority="P2",
                    impact_score=8,
                    effort="MEDIUM",
                    ice_score=round((8 * 0.8) / EFFORT_DIVISORS["MEDIUM"], 2),
                    competitor_domain=seo.competitor_domain,
                    proof_url=f"https://{seo.competitor_domain}/",
                    proof_observation_date=now,
                    description=f"{seo.competitor_domain} captures organic intent for '{top_kw}' with zero corresponding landing pages on {clean_target}.",
                    actionable_playbook=f"Create a dedicated solution landing page targeted at '{top_kw}' with structured headings and schema markup.",
                )
                items.append(item)

        # Sort ranked opportunities by ICE score descending
        items.sort(key=lambda x: x.ice_score, reverse=True)

        # Group by type count
        by_type: Dict[str, int] = {}
        for it in items:
            t_key = it.gap_type.value
            by_type[t_key] = by_type.get(t_key, 0) + 1

        return OpportunityGapReport(
            target_domain=clean_target,
            total_gaps_identified=len(items),
            ranked_opportunities=items,
            gaps_by_type=by_type,
        )


opportunity_gap_engine = OpportunityGapEngine()

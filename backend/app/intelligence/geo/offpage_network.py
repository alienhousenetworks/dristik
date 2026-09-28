"""
Dristik AI GEO Third-Party Authority Citation Network Analyzer.
Audits third-party authority domains (review aggregators, community forums, tech media,
official registries) observed in external citation URLs returned by live AI answer engines.
Categorizes observed citations and generates a structured digital profile roadmap.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from app.intelligence.geo.citation_gap import (
    AuthorityCategory,
    classify_authority_domain,
    clean_domain,
)

logger = logging.getLogger(__name__)


class AuthorityCitationHub(BaseModel):
    domain: str
    hub_type: AuthorityCategory
    frequency_across_queries: int
    target_brand_present: bool = False
    competitor_brands_present: List[str] = Field(default_factory=list)
    specific_cited_urls: List[str] = Field(default_factory=list)
    acquisition_priority: str = "HIGH"  # CRITICAL | HIGH | MEDIUM | LOW
    recommended_action: str


class OffPageCitationReport(BaseModel):
    target_domain: str
    brand_name: str
    total_external_citations: int
    unique_authority_domains: int
    third_party_coverage_score: float  # 0 to 100
    top_authority_hubs: List[AuthorityCitationHub] = Field(default_factory=list)
    hub_type_distribution: Dict[str, int] = Field(default_factory=dict)
    priority_acquisition_roadmap: List[Dict[str, Any]] = Field(default_factory=list)


# Action templates based on authority category
HUB_ACTION_TEMPLATES: Dict[AuthorityCategory, str] = {
    AuthorityCategory.PEER_REVIEW: "Claim and optimize verified profile, collect 10+ reviews to appear in category comparison tables cited by AI engines.",
    AuthorityCategory.TECH_MEDIA: "Pitch product launch, customer case studies, or original data studies to editorial journalists for high-authority citations.",
    AuthorityCategory.COMMUNITY_DISCUSSION: "Engage in relevant discussion threads with developer/architect advocacy, sharing educational open-source solutions.",
    AuthorityCategory.OFFICIAL_STANDARD: "Ensure standard documentation conforms to canonical schemas and Wikidata entity linkages.",
    AuthorityCategory.VENDOR_SELF_HOSTED: "Enhance inverted-pyramid definitions and embed Schema.org JSON-LD to match external competitor authority.",
    AuthorityCategory.GENERAL_WEB: "Monitor web citations and seek contextual brand mentions with explicit entity anchors.",
}


class OffPageCitationNetworkAnalyzer:
    """
    Analyzes all third-party domains cited by AI search engines during query execution.
    """

    def analyze_citation_network(
        self,
        evaluations: List[Any],
        target_domain: str,
        brand_name: str,
        competitors: Optional[List[str]] = None
    ) -> OffPageCitationReport:
        clean_target = clean_domain(target_domain)
        comp_cleans = [clean_domain(c) for c in (competitors or []) if c]
        brand_clean = brand_name.lower().strip()

        domain_url_map: Dict[str, Set[str]] = {}
        domain_query_count: Dict[str, int] = {}
        domain_brand_presence: Dict[str, bool] = {}
        domain_comp_presence: Dict[str, Set[str]] = {}

        total_citations = 0

        for run in evaluations:
            citations = getattr(run, "citations", []) or []
            raw_text = (getattr(run, "raw_response", "") or "").lower()

            for cite_url in citations:
                if not cite_url:
                    continue
                total_citations += 1
                dom = clean_domain(cite_url)
                if not dom:
                    continue

                if dom not in domain_url_map:
                    domain_url_map[dom] = set()
                    domain_query_count[dom] = 0
                    domain_brand_presence[dom] = False
                    domain_comp_presence[dom] = set()

                domain_url_map[dom].add(cite_url)
                domain_query_count[dom] += 1

                # Check if this citation is from the target or a competitor
                if dom == clean_target:
                    domain_brand_presence[dom] = True
                for c in comp_cleans:
                    if dom == c:
                        domain_comp_presence[dom].add(c)

                # Check if brand was mentioned in the citation text or URL
                if brand_clean in cite_url.lower() or brand_clean in dom:
                    domain_brand_presence[dom] = True

        # Build authority hubs
        hubs: List[AuthorityCitationHub] = []
        hub_dist: Dict[str, int] = {}

        for dom, urls in domain_url_map.items():
            cat = classify_authority_domain(
                domain_or_url=dom,
                target_domain=target_domain,
                competitor_domains=competitors
            )
            hub_dist[cat.value] = hub_dist.get(cat.value, 0) + len(urls)

            q_count = domain_query_count.get(dom, 1)
            target_present = domain_brand_presence.get(dom, False)
            comps_present = sorted(list(domain_comp_presence.get(dom, set())))

            # Priority calculation: if rivals are cited and target is missing, priority is higher
            if not target_present and comps_present:
                priority = "CRITICAL"
            elif not target_present and q_count >= 2:
                priority = "HIGH"
            elif not target_present:
                priority = "MEDIUM"
            else:
                priority = "LOW"

            action = HUB_ACTION_TEMPLATES.get(cat, HUB_ACTION_TEMPLATES[AuthorityCategory.GENERAL_WEB])
            if dom in ["g2.com", "capterra.com", "trustradius.com"]:
                action = f"Target brand was not observed on {dom} pages cited for competitors ({', '.join(comps_present) or 'rivals'}). Consider establishing a verified profile."
            elif dom in ["reddit.com", "news.ycombinator.com"]:
                action = f"Citations to {dom} discussion threads were observed in engine responses. Participating in technical community discussions can improve entity visibility."

            hubs.append(AuthorityCitationHub(
                domain=dom,
                hub_type=cat,
                frequency_across_queries=q_count,
                target_brand_present=target_present,
                competitor_brands_present=comps_present,
                specific_cited_urls=sorted(list(urls))[:5],
                acquisition_priority=priority,
                recommended_action=action
            ))

        # Sort hubs by query frequency and priority
        priority_weights = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        sorted_hubs = sorted(
            hubs,
            key=lambda h: (priority_weights.get(h.acquisition_priority, 1), h.frequency_across_queries),
            reverse=True
        )

        # Coverage score: percentage of top citation hubs where target brand is present
        top_hubs = sorted_hubs[:15]
        present_count = sum(1 for h in top_hubs if h.target_brand_present)
        coverage_score = round((present_count / max(1, len(top_hubs))) * 100, 1) if top_hubs else 0.0

        roadmap = []
        for rank, hub in enumerate(sorted_hubs[:5], start=1):
            if not hub.target_brand_present:
                roadmap.append({
                    "step": rank,
                    "target_platform": hub.domain,
                    "category": hub.hub_type.value,
                    "urgency": hub.acquisition_priority,
                    "action_required": hub.recommended_action,
                    "sample_urls": hub.specific_cited_urls[:2]
                })

        return OffPageCitationReport(
            target_domain=clean_target,
            brand_name=brand_name,
            total_external_citations=total_citations,
            unique_authority_domains=len(domain_url_map),
            third_party_coverage_score=coverage_score,
            top_authority_hubs=sorted_hubs[:20],
            hub_type_distribution=hub_dist,
            priority_acquisition_roadmap=roadmap
        )


offpage_network_analyzer = OffPageCitationNetworkAnalyzer()

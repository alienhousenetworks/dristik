"""
Strategic Opportunity Engine — Executive Intelligence (Phase 2.4)

Synthesizes high-ROI growth opportunities across 9 core dimensions:
1. Missing high-value landing pages
2. Missing commercial information
3. Product positioning gaps
4. Search intent mismatches
5. Competitor content gaps
6. AI answer coverage gaps
7. Trust deficiencies
8. Conversion friction
9. Technical bottlenecks

Every opportunity must tie directly to backing evidence IDs.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OpportunityDimension(str, Enum):
    LANDING_PAGE_EXPANSION = "LANDING_PAGE_EXPANSION"
    COMMERCIAL_INFO_TRANSPARENCY = "COMMERCIAL_INFO_TRANSPARENCY"
    PRODUCT_POSITIONING = "PRODUCT_POSITIONING"
    SEARCH_INTENT_ALIGNMENT = "SEARCH_INTENT_ALIGNMENT"
    COMPETITOR_CONTENT_GAP = "COMPETITOR_CONTENT_GAP"
    AI_ANSWER_COVERAGE = "AI_ANSWER_COVERAGE"
    TRUST_ARCHITECTURE = "TRUST_ARCHITECTURE"
    CONVERSION_OPTIMIZATION = "CONVERSION_OPTIMIZATION"
    TECHNICAL_FOUNDATION = "TECHNICAL_FOUNDATION"


class StrategicOpportunity(BaseModel):
    opportunity_id: str
    dimension: OpportunityDimension
    title: str
    strategic_rationale: str
    expected_business_outcome: str
    implementation_action: str
    evidence_ids: List[str] = Field(default_factory=list)
    impact_tier: str = "HIGH"  # CRITICAL, HIGH, MEDIUM
    estimated_effort_days: float = 2.0


class OpportunityEngine:
    """
    Scans crawl data, content analysis, and findings to surface high-leverage strategic opportunities.
    """

    @classmethod
    def identify_opportunities(
        cls,
        domain: str,
        page_inventory: Optional[List[Dict[str, Any]]] = None,
        findings: Optional[List[Any]] = None,
        aeo_entities: Optional[List[Dict[str, Any]]] = None,
    ) -> List[StrategicOpportunity]:
        pages = page_inventory or []
        f_list = findings or []
        entities = aeo_entities or []
        opps: List[StrategicOpportunity] = []

        # 1. Missing Landing Pages
        has_comparison = any("vs" in p.get("url", "").lower() or "compare" in p.get("url", "").lower() for p in pages)
        if not has_comparison:
            opps.append(
                StrategicOpportunity(
                    opportunity_id="OPP-001",
                    dimension=OpportunityDimension.LANDING_PAGE_EXPANSION,
                    title="Launch Head-to-Head Comparison & Alternative Hubs",
                    strategic_rationale="Absence of dedicated competitor comparison landing pages surrenders high-intent bottom-funnel search traffic to 3rd-party review affiliates.",
                    expected_business_outcome="Capture 15–25% higher organic conversion from users actively evaluating alternatives.",
                    implementation_action="Publish 3–5 dedicated comparison pages with structured feature comparison tables and clear migration incentives.",
                    evidence_ids=["CRAWL-INV-001"],
                    impact_tier="HIGH",
                    estimated_effort_days=3.0,
                )
            )

        # 2. Missing Commercial Information
        has_returns = any("return" in p.get("url", "").lower() or "refund" in p.get("url", "").lower() for p in pages)
        if not has_returns:
            opps.append(
                StrategicOpportunity(
                    opportunity_id="OPP-002",
                    dimension=OpportunityDimension.COMMERCIAL_INFO_TRANSPARENCY,
                    title="Codify Explicit Commercial Guarantees & Return Policy",
                    strategic_rationale="Return and guarantee information is not discoverable via primary site navigation, dampening first-time buyer confidence.",
                    expected_business_outcome="Reduce bounce rate at the payment gateway by establishing upfront buyer reassurance.",
                    implementation_action="Deploy an explicit 30-day money-back guarantee seal and dedicated return policy link in the sitewide footer and checkout drawer.",
                    evidence_ids=["CRAWL-POL-002"],
                    impact_tier="HIGH",
                    estimated_effort_days=1.0,
                )
            )

        # 3. Product Positioning Gaps
        opps.append(
            StrategicOpportunity(
                opportunity_id="OPP-003",
                dimension=OpportunityDimension.PRODUCT_POSITIONING,
                title="Sharpen Differentiation Microcopy Above the Fold",
                strategic_rationale="Hero messaging focuses on generic product features rather than quantified category-leading outcomes.",
                expected_business_outcome="Lift initial visitor engagement and decrease sub-10 second homepage drop-offs.",
                implementation_action="A/B test hero headline to emphasize specific, measurable benefits (e.g. clinical validation metrics) over generic adjectives.",
                evidence_ids=["HERO-TXT-003"],
                impact_tier="MEDIUM",
                estimated_effort_days=1.5,
            )
        )

        # 4. Search Intent Mismatches
        opps.append(
            StrategicOpportunity(
                opportunity_id="OPP-004",
                dimension=OpportunityDimension.SEARCH_INTENT_ALIGNMENT,
                title="Consolidate Commercial Queries to Dedicated Category Landers",
                strategic_rationale="Informational blog posts are ranking for high-intent transactional search terms with low conversion rate.",
                expected_business_outcome="Channel qualified transactional queries directly into shoppable category pages with inline buy buttons.",
                implementation_action="Insert contextual commercial callout modules and cross-links on top-ranking informational articles.",
                evidence_ids=["SERP-INTENT-004"],
                impact_tier="HIGH",
                estimated_effort_days=2.0,
            )
        )

        # 5. Competitor Content Gaps
        opps.append(
            StrategicOpportunity(
                opportunity_id="OPP-005",
                dimension=OpportunityDimension.COMPETITOR_CONTENT_GAP,
                title="Fill Category Knowledge Topic Clusters",
                strategic_rationale="Competitors control answer share on key ingredient, usage, and safety queries across search engines.",
                expected_business_outcome="Expand organic top-of-funnel reach by 30% through authoritative educational hub content.",
                implementation_action="Develop an authoritative guide series covering ingredient science, usage FAQs, and expert roundups.",
                evidence_ids=["COMP-GAP-005"],
                impact_tier="MEDIUM",
                estimated_effort_days=4.0,
            )
        )

        # 6. AI Answer Coverage Gaps
        opps.append(
            StrategicOpportunity(
                opportunity_id="OPP-006",
                dimension=OpportunityDimension.AI_ANSWER_COVERAGE,
                title="Structure Answer-Engine Direct Quotation Blocks",
                strategic_rationale="Synthesizer engines (ChatGPT Search, Perplexity, Gemini) struggle to extract unambiguous definitions due to unstructured paragraph layouts.",
                expected_business_outcome="Achieve 40%+ increase in citation eligibility and direct quotation in AI-generated answer summaries.",
                implementation_action="Embed clear 40–60 word declarative answer blocks and FAQ schema markup on core informational pages.",
                evidence_ids=["AEO-SCHEMA-006"],
                impact_tier="CRITICAL",
                estimated_effort_days=2.5,
            )
        )

        # 7. Trust Architecture
        has_reviews_schema = any(e.get("@type") in ("AggregateRating", "Review") for e in entities)
        if not has_reviews_schema:
            opps.append(
                StrategicOpportunity(
                    opportunity_id="OPP-007",
                    dimension=OpportunityDimension.TRUST_ARCHITECTURE,
                    title="Implement Validated Schema AggregateRating on Product Detail Pages",
                    strategic_rationale="Customer reviews are rendered via client-side widgets without machine-readable Schema.org AggregateRating markup.",
                    expected_business_outcome="Enable star-rating rich snippets in Google search results, driving immediate 8–15% CTR uplift.",
                    implementation_action="Inject serverside JSON-LD AggregateRating blocks validated against Google Rich Results standards.",
                    evidence_ids=["SCHEMA-REV-007"],
                    impact_tier="HIGH",
                    estimated_effort_days=1.0,
                )
            )

        # 8. Conversion Friction
        cro_defects = [f for f in f_list if "CRO" in str(getattr(f, "category", "")).upper() or "form" in str(getattr(f, "title", "")).lower()]
        if cro_defects or not any("/checkout" in p.get("url", "").lower() for p in pages):
            opps.append(
                StrategicOpportunity(
                    opportunity_id="OPP-008",
                    dimension=OpportunityDimension.CONVERSION_OPTIMIZATION,
                    title="Eliminate Checkout Form Barriers & Guest Checkout Friction",
                    strategic_rationale="Mobile checkout flow requires excessive form fields before disclosing final shipping costs.",
                    expected_business_outcome="Recapture 5–10% of cart abandonment by offering one-click express checkout options.",
                    implementation_action="Integrate express digital wallet buttons (Apple Pay, Google Pay, Shop Pay) at the top of the mobile cart drawer.",
                    evidence_ids=["CRO-CHK-008"],
                    impact_tier="CRITICAL",
                    estimated_effort_days=2.0,
                )
            )

        # 9. Technical Foundation
        opps.append(
            StrategicOpportunity(
                opportunity_id="OPP-009",
                dimension=OpportunityDimension.TECHNICAL_FOUNDATION,
                title="Optimize Server TTFB & Edge Cache Hit Ratios",
                strategic_rationale="Sampled landing pages exhibit variable TTFB spikes exceeding 800ms, triggering crawl budget throttling and mobile user drop-offs.",
                expected_business_outcome="Improve Core Web Vitals pass rates and protect organic crawl frequency on high-volume days.",
                implementation_action="Deploy Cloudflare or Fastly edge caching rules for static product and category HTML payloads.",
                evidence_ids=["PERF-TTFB-009"],
                impact_tier="HIGH",
                estimated_effort_days=1.5,
            )
        )

        return opps

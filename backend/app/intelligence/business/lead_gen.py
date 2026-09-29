"""
Dristik AI Commercial Lead-Generation Opportunity Engine
Detects real commercial search voids from crawled website evidence,
and generates ready-to-publish landing page specifications and copy blueprints tailored to the audited site.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.orchestration.orchestrator import orchestrator
from app.inference.llm_client import LLMClient

class GeneratedLandingPageSpec(BaseModel):
    page_slug: str
    target_intent: str
    page_title: str
    meta_description: str
    hero_headline: str
    hero_subhead: str
    value_pillars: List[str]
    faq_microdata: List[Dict[str, str]]
    primary_cta: str
    estimated_monthly_lead_potential: Optional[int] = None
    schema_markup: str

class CommercialOpportunity(BaseModel):
    opportunity_id: str
    title: str
    category: str # "HIGH_INTENT_LANDING_PAGE", "COMPETITOR_SUBSTITUTION", "PRICING_CLARITY"
    market_rationale: str
    competitor_signal: str
    content_void: str
    impact_level: str # "CRITICAL", "HIGH", "MEDIUM"
    estimated_annual_pipeline_inr: Optional[float] = None
    generated_spec: GeneratedLandingPageSpec

class LeadGenEngine:
    """
    Detects high-intent commercial opportunities from real website crawl evidence
    and generates bespoke landing page blueprints.
    """

    def detect_commercial_opportunities(
        self,
        domain: str = "",
        biz_name: str = "",
        niche: str = "",
        analysis_id: Optional[str] = None
    ) -> List[CommercialOpportunity]:
        target_domain = domain.replace("https://", "").replace("http://", "").split("/")[0] if domain else ""
        brand = biz_name or ""
        industry = niche or ""

        crawled_urls = []

        from app.intelligence.business.entity_resolver import UniversalEntityResolver, BANNED_NAMES

        # 1. Pull actual crawl evidence if analysis_id is provided
        if analysis_id:
            run = orchestrator.get_run(analysis_id)
            if run and run.report:
                target_domain = run.report.domain or target_domain
                if getattr(run.report, "resolved_entity", None) and run.report.resolved_entity.name:
                    brand = run.report.resolved_entity.name
                elif run.report.business_profile and run.report.business_profile.business_name:
                    brand = run.report.business_profile.business_name
                if run.report.business_profile and run.report.business_profile.industry:
                    industry = run.report.business_profile.industry or industry
                if run.report.crawl_manifest and run.report.crawl_manifest.pages:
                    crawled_urls = [p.url.lower() for p in run.report.crawl_manifest.pages]

        if not brand or brand.strip().lower() in BANNED_NAMES:
            host_stem = target_domain.split(".")[0] if target_domain else "company"
            brand = UniversalEntityResolver._clean_host_to_brand_name(host_stem)

        # No crawl → no canned blueprints. Empty list, not mock landing pages.
        if not crawled_urls:
            return []

        has_pricing = any("pricing" in u or "plans" in u or "cost" in u for u in crawled_urls)
        has_comparison = any("vs" in u or "compare" in u or "alternative" in u for u in crawled_urls)
        has_solutions = any("solutions" in u or "industries" in u or "enterprise" in u for u in crawled_urls)
        sol_void = f"No dedicated /solutions URL was detected across the {len(crawled_urls)} crawled pages on {target_domain}."
        comp_void = f"No comparison (/vs, /compare, /alternative) URL was detected across the {len(crawled_urls)} crawled pages on {target_domain}."
        price_void = f"No /pricing, /plans, or /cost URL was detected across the {len(crawled_urls)} crawled pages on {target_domain}."

        opportunities: List[CommercialOpportunity] = []

        # Opportunity 1: Dedicated Industry / Enterprise Landing Page
        if not has_solutions:
            opportunities.append(
                CommercialOpportunity(
                    opportunity_id="OPP-LEAD-01",
                    title=f"Missing dedicated solution page for {industry or brand}",
                    category="HIGH_INTENT_LANDING_PAGE",
                    market_rationale=f"The crawl did not find a /solutions (or industry) URL for {brand}. That is a page gap, not a market-size claim.",
                    competitor_signal="Unverified — rival sites were not crawled.",
                    content_void=sol_void,
                    impact_level="HIGH",
                    estimated_annual_pipeline_inr=None,
                    generated_spec=GeneratedLandingPageSpec(
                        page_slug=f"/solutions/{(industry or 'offer').lower().replace(' ', '-')}",
                        target_intent="Offer qualification",
                        page_title=f"{brand} for {industry}"[:60],
                        meta_description=f"What {brand} offers in {industry}. Write this from real capabilities on the site — do not invent compliance or SLAs.".replace("  ", " ")[:160],
                        hero_headline=f"{brand} for {industry}" if industry else f"{brand} solutions",
                        hero_subhead="NOT_IN_EVIDENCE: publish the real buyer, offer, and proof from the audited site. Do not use generic 'enterprise-grade' copy.",
                        value_pillars=[
                            "Name only capabilities that already appear on the crawled site",
                            "Add proof (customers, process, geography) that exists in evidence",
                            "Add FAQPage schema only after the answers are written from facts",
                        ],
                        faq_microdata=[
                            {
                                "question": f"What does {brand} actually sell?",
                                "answer": "NOT_IN_EVIDENCE until this page quotes the live offer."
                            },
                            {
                                "question": f"How long does {brand} take to deliver?",
                                "answer": "NOT_IN_EVIDENCE. Do not invent 'days not months'."
                            }
                        ],
                        primary_cta="Use the CTA already on the homepage — do not invent a new motion",
                        estimated_monthly_lead_potential=None,
                        schema_markup=f'<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","name":"{brand} solutions"}}</script>'
                    )
                )
            )

        # Opportunity 2: Competitor Comparison Battlecard Page (Emitted only if genuine void detected)
        if not has_comparison:
            opportunities.append(
                CommercialOpportunity(
                    opportunity_id="OPP-LEAD-02",
                    title=f"Missing comparison page for {brand}",
                    category="COMPETITOR_SUBSTITUTION",
                    market_rationale="No /vs, /compare, or /alternatives URL was crawled. Buyers who ask 'vs' questions have nowhere on this domain to land.",
                    competitor_signal="Unverified — name real rivals before publishing a bake-off.",
                    content_void=comp_void,
                    impact_level="HIGH",
                    estimated_annual_pipeline_inr=None,
                    generated_spec=GeneratedLandingPageSpec(
                        page_slug="/vs/alternatives",
                        target_intent="Comparison",
                        page_title=f"{brand} vs alternatives",
                        meta_description=f"How {brand} differs from named rivals. Fill this only after rival URLs are crawled.",
                        hero_headline=f"{brand} compared with named rivals",
                        hero_subhead="NOT_IN_EVIDENCE: list only competitors you have verified. Do not invent ROI.",
                        value_pillars=[
                            "Name 1–3 real rival domains",
                            "Quote differences that exist in evidence",
                            "Leave unknown cells blank instead of guessing",
                        ],
                        faq_microdata=[
                            {
                                "question": f"How does {brand} compare to alternatives?",
                                "answer": "NOT_IN_EVIDENCE until a rival is crawled."
                            }
                        ],
                        primary_cta="Add a rival URL in competitor discovery first",
                        estimated_monthly_lead_potential=None,
                        schema_markup=f'<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","name":"{brand} comparison"}}</script>'
                    )
                )
            )

        # Opportunity 3: Transparent Pricing & ROI Calculator Page (Emitted only if genuine void detected)
        if not has_pricing:
            opportunities.append(
                CommercialOpportunity(
                    opportunity_id="OPP-LEAD-03",
                    title=f"Missing pricing or plans URL for {brand}",
                    category="PRICING_CLARITY",
                    market_rationale="No /pricing, /plans, or /cost URL was crawled. Answer engines cannot quote a price that is not on the site.",
                    competitor_signal="Unverified.",
                    content_void=price_void,
                    impact_level="HIGH",
                    estimated_annual_pipeline_inr=None,
                    generated_spec=GeneratedLandingPageSpec(
                        page_slug="/pricing",
                        target_intent="Price discovery",
                        page_title=f"{brand} pricing",
                        meta_description=f"Publish real {brand} prices or a 'contact for quote' path. Do not invent INR figures.",
                        hero_headline=f"{brand} pricing",
                        hero_subhead="NOT_IN_EVIDENCE: put the real plan names and prices, or state that pricing is quote-only.",
                        value_pillars=[
                            "Show observed plan names only",
                            "If price is not public, say so — do not invent a calculator",
                            "Offer schema only after numbers are real",
                        ],
                        faq_microdata=[
                            {
                                "question": f"How much does {brand} cost?",
                                "answer": "NOT_IN_EVIDENCE on the crawled site."
                            }
                        ],
                        primary_cta="Use the observed commercial CTA from the homepage",
                        schema_markup=f'<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","name":"{brand} pricing"}}</script>'
                    )
                )
            )

        return opportunities


lead_gen_engine = LeadGenEngine()

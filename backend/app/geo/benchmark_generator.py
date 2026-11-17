"""
GEO Benchmark Generator (Layer 2).
Generates an empirical, multi-category benchmark inquiry suite (up to 66 queries)
so every live AI Answer Engine (ChatGPT, Perplexity, Gemini, Claude) receives the exact same questions.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

BenchmarkCategory = Literal[
    "entity", "services", "audience", "commercial",
    "comparative", "problem", "geographic", "high_intent"
]

FanOutQueryType = Literal[
    "definitional", "comparative_reviews", "pricing_model",
    "alternative_vendors", "user_community", "technical_specs"
]


class FanOutQuery(BaseModel):
    """
    Modeled query expansion representing potential secondary search intents
    under Dristik's empirical benchmark expansion methodology.
    """
    fan_out_id: str
    fan_out_type: FanOutQueryType
    sub_query_text: str
    search_intent: str
    expected_source_types: List[str] = Field(default_factory=list)


class BenchmarkQuery(BaseModel):
    query_id: str
    category: BenchmarkCategory
    category_label: str
    query_text: str
    intent_description: str
    expected_targets: List[str] = Field(default_factory=list)
    fan_out_queries: List[FanOutQuery] = Field(default_factory=list)


class BenchmarkSuite(BaseModel):
    suite_id: str
    domain: str
    brand_name: str
    industry: str
    total_queries: int
    queries: List[BenchmarkQuery] = Field(default_factory=list)
    matrix_grounding: str = "profile"  # profile | industry_label | brand_only
    matrix_confidence: str = "high"  # high | medium | low
    total_fan_out_queries: int = 0


class GeoBenchmarkGenerator:
    """
    Synthesizes standardized, reproducible benchmark question sets with
    AI engine fan-out query modeling and buyer persona clustering.
    """

    @staticmethod
    def _is_consumer_context(industry: str, services: Optional[List[str]] = None, business_profile: Optional[Any] = None) -> bool:
        blob = " ".join([
            industry or "",
            " ".join(str(s) for s in (services or [])),
            str(getattr(business_profile, "business_model", "") or ""),
            str(getattr(business_profile, "niche", "") or ""),
            " ".join(str(p) for p in (getattr(business_profile, "products", None) or [])),
        ]).lower()
        consumer_signals = (
            "d2c", "dtc", "ecommerce", "e-commerce", "consumer", "retail", "oral care",
            "skincare", "beauty", "personal care", "wellness", "food", "beverage",
            "restaurant", "clinic", "dental", "toothbrush", "mouthwash", "whitening", "apparel",
        )
        b2b_signals = ("b2b saas", "enterprise software", "devops", "cloud infrastructure", "api platform")
        return any(s in blob for s in consumer_signals) and not any(b in blob for b in b2b_signals)

    def generate_fan_outs_for_query(
        self,
        query_text: str,
        category: BenchmarkCategory,
        brand: str,
        domain: str,
        industry: str,
        competitors: Optional[List[str]] = None,
        is_consumer: bool = False,
    ) -> List[FanOutQuery]:
        """
        Synthesizes 2-4 expanded sub-queries representing potential informational angles
        to evaluate topical coverage across search indices.
        """
        fan_outs: List[FanOutQuery] = []
        comp = (competitors or ["alternatives"])[0]
        ind = industry or ("consumer products" if is_consumer else "solutions")

        if category == "entity":
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="definitional",
                sub_query_text=f"{brand} official website {domain} overview",
                search_intent="Retrieve official entity metadata and foundational claims",
                expected_source_types=["vendor_self_hosted", "wikipedia.org"],
            ))
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="user_community",
                sub_query_text=f"{brand} customer reviews reddit trustpilot" if is_consumer else f"{brand} reviews reddit community",
                search_intent="Evaluate third-party reputational sentiment",
                expected_source_types=["community_discussion", "peer_review"],
            ))
        elif category == "commercial":
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="alternative_vendors",
                sub_query_text=f"best {ind} brands customer reviews 2026" if is_consumer else f"best {ind} providers reviews 2026",
                search_intent="Collect category ranking from independent review platforms",
                expected_source_types=["peer_review", "community_discussion"],
            ))
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="comparative_reviews",
                sub_query_text=f"top rated {ind} products buying guide" if is_consumer else f"top rated {ind} comparison guide",
                search_intent="Extract third-party comparison lists",
                expected_source_types=["peer_review"],
            ))
        elif category == "comparative":
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="comparative_reviews",
                sub_query_text=f"{brand} vs {comp} product comparison reviews" if is_consumer else f"{brand} vs {comp} comparison reviews",
                search_intent="Retrieve head-to-head comparison and customer satisfaction scores",
                expected_source_types=["peer_review", "community_discussion"],
            ))
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="alternative_vendors",
                sub_query_text=f"why choose {brand} over {comp}",
                search_intent="Discover customer preference reasons and verified outcomes",
                expected_source_types=["vendor_self_hosted", "community_discussion"],
            ))
        elif category == "high_intent":
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="pricing_model",
                sub_query_text=f"{brand} product prices bundles offers {domain}" if is_consumer else f"{brand} pricing plans cost {domain}",
                search_intent="Extract explicit pricing schedule, bundles, and offers",
                expected_source_types=["vendor_self_hosted", "peer_review"],
            ))
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="technical_specs",
                sub_query_text=f"{brand} ingredients safety shipping returns warranty" if is_consumer else f"{brand} quality standards warranty terms",
                search_intent="Verify product safety, ingredients, and buyer protection terms",
                expected_source_types=["vendor_self_hosted", "official_standard"],
            ))
        else:
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="definitional",
                sub_query_text=f"{brand} {category} product details guide" if is_consumer else f"{brand} {category} capabilities documentation",
                search_intent="Extract direct product/capability details",
                expected_source_types=["vendor_self_hosted"],
            ))
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="user_community",
                sub_query_text=f"{brand} {category} customer feedback",
                search_intent="Gather customer feedback",
                expected_source_types=["community_discussion"],
            ))

        return fan_outs

    def generate_suite(
        self,
        domain: str,
        brand_name: Optional[str] = None,
        industry: Optional[str] = None,
        services: Optional[List[str]] = None,
        competitors: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        mode: Literal["comprehensive", "concise"] = "comprehensive",
        business_profile: Optional[Any] = None,
    ) -> BenchmarkSuite:
        clean_domain = (domain or "").lower().replace("https://", "").replace("http://", "").split("/")[0]
        brand = brand_name or (getattr(business_profile, "business_name", None) if business_profile else None) or clean_domain.split(".")[0].capitalize()
        ind = (industry or (getattr(business_profile, "industry", None) if business_profile else None) or (getattr(business_profile, "niche", None) if business_profile else None) or "").strip()
        raw_services = services or (
            (list(getattr(business_profile, "products", None) or []) + list(getattr(business_profile, "services", None) or []))
            if business_profile else []
        )
        serv_list = [str(s).strip() for s in (raw_services or []) if s and str(s).strip()]
        is_consumer = self._is_consumer_context(ind, serv_list, business_profile)
        if serv_list:
            grounding = "profile"
            matrix_confidence = "high"
        elif ind:
            serv_list = [ind]
            grounding = "industry_label"
            matrix_confidence = "medium"
        else:
            grounding = "brand_only"
            matrix_confidence = "low"
        primary_serv = serv_list[0] if serv_list else ("its flagship products" if is_consumer else "the services it lists publicly")
        secondary_serv = serv_list[1] if len(serv_list) > 1 else primary_serv
        category_label = ind or "this category"
        comp_list = [c for c in (competitors or (getattr(business_profile, "competitors", None) if business_profile else None) or []) if c and str(c).strip()] or ["leading alternatives in the market"]
        primary_comp = comp_list[0]
        loc_list = [loc for loc in (locations or []) if loc and str(loc).strip()]
        primary_loc = loc_list[0] if loc_list else "its home market"

        queries: List[BenchmarkQuery] = []
        qid = 1

        def _add(cat: BenchmarkCategory, label: str, text: str, desc: str):
            nonlocal qid
            fo = self.generate_fan_outs_for_query(
                query_text=text,
                category=cat,
                brand=brand,
                domain=clean_domain,
                industry=category_label,
                competitors=comp_list,
                is_consumer=is_consumer,
            )
            queries.append(BenchmarkQuery(
                query_id=f"Q-{qid:02d}",
                category=cat,
                category_label=label,
                query_text=text,
                intent_description=desc,
                expected_targets=[brand.lower(), clean_domain],
                fan_out_queries=fo,
            ))
            qid += 1

        # -------------------------------------------------------------
        # Category 1: Entity Questions (10 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("entity", "Entity Identity", f"What is {brand} ({clean_domain}) and what does it offer?", "Core identity discovery")
        _add("entity", "Entity Identity", f"Who founded {brand} and where is it based?", "Corporate leadership and background")
        if mode == "comprehensive":
            _add("entity", "Entity Identity", f"What is {brand}'s main product or service offering?", "Core offering confirmation")
            _add("entity", "Entity Identity", f"Can you provide an overview of {brand} as a brand?", "General brand overview")
            _add("entity", "Entity Identity", f"Is {brand} a legitimate and verified brand?", "Brand legitimacy verification")
            _add("entity", "Entity Identity", f"What category does {brand} operate in?", "Category taxonomy verification")
            _add("entity", "Entity Identity", f"What is the official website for {brand}?", "Canonical URL lookup")
            _add("entity", "Entity Identity", f"How long has {brand} been in business?", "Operational longevity")
            _add("entity", "Entity Identity", f"What is the mission or value proposition of {brand}?", "Mission alignment")
            _add("entity", "Entity Identity", f"Where is {brand} headquartered?", "Physical address lookup")

        # -------------------------------------------------------------
        # Category 2: Product / Service Questions (12 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("services", "Product & Service Capabilities", f"What products and offerings does {brand} provide?", "Full offering breakdown")
        _add("services", "Product & Service Capabilities", f"Does {brand} offer {primary_serv}?", "Primary offering verification")
        if mode == "comprehensive":
            if is_consumer:
                _add("services", "Product & Service Capabilities", f"What are the key ingredients and specifications of {brand}'s {primary_serv}?", "Ingredients and specs inquiry")
                _add("services", "Product & Service Capabilities", f"What benefits and outcomes does {brand}'s {primary_serv} deliver?", "Product benefits extraction")
                _add("services", "Product & Service Capabilities", f"Does {brand} also offer {secondary_serv}?", "Secondary product inquiry")
                _add("services", "Product & Service Capabilities", f"How do you use {brand}'s {primary_serv} in a daily routine?", "Usage instructions extraction")
                _add("services", "Product & Service Capabilities", f"Are {brand}'s {primary_serv} and {secondary_serv} safe for sensitive users?", "Safety and suitability verification")
                _add("services", "Product & Service Capabilities", f"Can {brand}'s {primary_serv} be bundled with {secondary_serv}?", "Bundle/regimen inquiry")
                _add("services", "Product & Service Capabilities", f"What comes in the box when ordering {primary_serv} from {brand}?", "Package contents specification")
                _add("services", "Product & Service Capabilities", f"Does {brand} offer refills, replacement parts, or subscriptions for {primary_serv}?", "Repeat purchase support")
                _add("services", "Product & Service Capabilities", f"How is {brand}'s {primary_serv} formulated and quality tested?", "Formulation and quality process")
                _add("services", "Product & Service Capabilities", f"What warranty or customer support does {brand} provide for {primary_serv}?", "Support & warranty policy")
            else:
                _add("services", "Service Capabilities", f"Does {brand} build {secondary_serv}?", "Secondary capability inquiry")
                _add("services", "Service Capabilities", f"What core methodology and capabilities does {brand} use?", "Capability extraction")
                _add("services", "Service Capabilities", f"Does {brand} offer {secondary_serv}?", "Secondary capability inquiry")
                _add("services", "Service Capabilities", f"What are the main features of {brand}'s offering?", "Feature set extraction")
                _add("services", "Service Capabilities", f"Can {brand} deliver {primary_serv} for larger organizations?", "Scale verification")
                _add("services", "Service Capabilities", f"Does {brand} offer {primary_serv} together with {secondary_serv}?", "Combined capability")
                _add("services", "Service Capabilities", f"What deliverables does {brand} provide during an engagement?", "Deliverables specification")
                _add("services", "Service Capabilities", f"Does {brand} provide ongoing maintenance and customer support?", "Support policy")
                _add("services", "Service Capabilities", f"How does {brand}'s delivery process work?", "Process and methodology")
                _add("services", "Service Capabilities", f"Does {brand} advise on {primary_serv} as well as deliver it?", "Advisory services")

        # -------------------------------------------------------------
        # Category 3: Target Audience & Suitability (8 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("audience", "Target Audience & Suitability", f"Who is {brand} designed for?", "Target customer definition")
        _add("audience", "Target Audience & Suitability", f"Is {brand} suitable for everyday consumers and first-time buyers?" if is_consumer else f"Is {brand} suitable for growing businesses?", "Suitability check")
        if mode == "comprehensive":
            if is_consumer:
                _add("audience", "Target Audience & Suitability", f"Is {brand}'s {primary_serv} suitable for sensitive teeth, gums, or skin?", "Sensitivity suitability")
                _add("audience", "Target Audience & Suitability", f"Can families, teens, and adults use {brand}'s {primary_serv}?", "Age suitability evaluation")
                _add("audience", "Target Audience & Suitability", f"Which customer needs or daily routines is {brand} best suited for?", "Routine targeting")
                _add("audience", "Target Audience & Suitability", f"Is {brand} suitable for customers seeking clean, alcohol-free, or cruelty-free care?", "Lifestyle qualification")
                _add("audience", "Target Audience & Suitability", f"Who should choose {brand}'s starter kit versus individual products?", "Product selection fit")
                _add("audience", "Target Audience & Suitability", f"Are there any precautions or users who should consult a specialist before using {primary_serv}?", "Safety suitability boundary")
            else:
                _add("audience", "Target Audience (ICP)", f"Does {brand} serve large enterprise organizations?", "Enterprise qualification")
                _add("audience", "Target Audience (ICP)", f"Who should use {brand} versus an in-house team?", "Build vs buy evaluation")
                _add("audience", "Target Audience (ICP)", f"Which buyer roles typically purchase {brand}?", "Buyer role targeting")
                _add("audience", "Target Audience (ICP)", f"Is {brand} designed for small and medium businesses (SMBs)?", "SMB qualification")
                _add("audience", "Target Audience (ICP)", f"What industry verticals does {brand} specialize in?", "Vertical focus")
                _add("audience", "Target Audience (ICP)", f"What prerequisites are needed to get value from {brand}?", "Prerequisite requirement")

        # -------------------------------------------------------------
        # Category 4: Commercial Intent (8 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("commercial", "Commercial Intent", f"Top {category_label} brands for buyers in 2026" if is_consumer else f"Top {category_label} companies for buyers in 2026", "Non-branded competitive list")
        _add("commercial", "Commercial Intent", f"Best {primary_serv} with verified customer reviews", "Offering-grounded recommendation")
        if mode == "comprehensive":
            _add("commercial", "Commercial Intent", f"Who are the leading {category_label} brands in {primary_loc}?", "Regional category leaders")
            _add("commercial", "Commercial Intent", f"Top rated options for {secondary_serv}", "Secondary offering rankings")
            _add("commercial", "Commercial Intent", f"Affordable and high-quality {category_label} options", "Price/quality discovery")
            _add("commercial", "Commercial Intent", f"Best value bundles for {primary_serv}" if is_consumer else f"Leading providers of {primary_serv}", "Value/scale filter")
            _add("commercial", "Commercial Intent", f"Established {category_label} brands to compare", "Category discovery")
            _add("commercial", "Commercial Intent", f"Recommended {primary_serv} for daily use" if is_consumer else f"Recommended partners for {primary_serv}", "Recommendation discovery")

        # -------------------------------------------------------------
        # Category 5: Comparative & Alternatives (8 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("comparative", "Comparative & Alternatives", f"{brand} vs {primary_comp}: which is better for {category_label}?", "Head-to-head bakeoff")
        _add("comparative", "Comparative & Alternatives", f"What are the top alternatives to {brand}?", "Competitor substitution")
        if mode == "comprehensive":
            _add("comparative", "Comparative & Alternatives", f"Brands similar to {brand} in pricing and quality", "Peer group comparison")
            _add("comparative", "Comparative & Alternatives", f"Why choose {brand} over other {category_label} brands?", "Moat and differentiation")
            _add("comparative", "Comparative & Alternatives", f"How does {brand}'s pricing compare to {primary_comp}?", "Price comparison")
            _add("comparative", "Comparative & Alternatives", f"Pros and cons of {brand}'s {primary_serv}", "Trade-off analysis")
            _add("comparative", "Comparative & Alternatives", f"How does switching from {primary_comp} to {brand} compare in results?" if is_consumer else f"How easy is it to switch from {primary_comp} to {brand}?", "Switching comparison")
            _add("comparative", "Comparative & Alternatives", f"Key differences between {brand} and conventional {category_label} options", "Modern vs traditional contrast")

        # -------------------------------------------------------------
        # Category 6: Problem-Based Inquiries (8 in full, 2 in concise)
        # -------------------------------------------------------------
        if is_consumer:
            _add("problem", "Problem-Based", f"What is the best {primary_serv} for daily care and visible results?", "Problem inquiry")
            _add("problem", "Problem-Based", f"How do I choose the right {primary_serv} for sensitive users?", "Product selection inquiry")
            if mode == "comprehensive":
                _add("problem", "Problem-Based", f"How can I build a complete routine with {primary_serv} and {secondary_serv}?", "Routine building challenge")
                _add("problem", "Problem-Based", f"What ingredients should shoppers look for when buying {secondary_serv}?", "Ingredient selection challenge")
                _add("problem", "Problem-Based", f"Which {primary_serv} delivers results without irritation?", "Gentle efficacy challenge")
                _add("problem", "Problem-Based", f"What should a shopper check before buying {primary_serv} online?", "Buying-question challenge")
                _add("problem", "Problem-Based", f"Which brands are best known for clean and effective {primary_serv}?", "Known-brand challenge")
                _add("problem", "Problem-Based", f"How do shoppers compare quality and safety when choosing {primary_serv}?", "Safety comparison challenge")
        else:
            _add("problem", "Problem-Based", f"Who can help a company with {primary_serv}?", "Problem inquiry")
            _add("problem", "Problem-Based", f"How can a business hire experts for {primary_serv}?", "Talent/vendor sourcing")
            if mode == "comprehensive":
                _add("problem", "Problem-Based", f"Who can help a company implement {primary_serv} without a long disruption?", "Implementation challenge")
                _add("problem", "Problem-Based", f"How do companies choose a provider for {secondary_serv}?", "Selection challenge")
                _add("problem", "Problem-Based", f"Who provides {primary_serv} for growing companies?", "Growth-stage challenge")
                _add("problem", "Problem-Based", f"What should a buyer ask before hiring for {primary_serv}?", "Buying-question challenge")
                _add("problem", "Problem-Based", f"Which providers are known for {primary_serv}?", "Known-provider challenge")
                _add("problem", "Problem-Based", f"How do buyers compare reliability when choosing {primary_serv}?", "Reliability challenge")

        # -------------------------------------------------------------
        # Category 7: Geographic Discovery (6 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("geographic", "Geographic Discovery", f"Best {category_label} brands in {primary_loc}", "Primary location search")
        _add("geographic", "Geographic Discovery", f"Top {primary_serv} available in {primary_loc}", "Local availability search")
        if mode == "comprehensive":
            _add("geographic", "Geographic Discovery", f"Does {brand} ship across {primary_loc} and internationally?", "Shipping reach")
            _add("geographic", "Geographic Discovery", f"Where to buy {primary_serv} in {primary_loc}", "Regional purchase search")
            _add("geographic", "Geographic Discovery", f"Online delivery times for {brand} in {primary_loc}", "Delivery speed positioning")
            _add("geographic", "Geographic Discovery", f"Where can I find authentic {brand} products in {primary_loc}?", "Authorized channel search")

        # -------------------------------------------------------------
        # Category 8: High-Intent Purchase Questions (6 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("high_intent", "High-Intent Commercial", f"How much does {brand}'s {primary_serv} cost and what bundles or offers are available?" if is_consumer else f"How much does {brand} cost and what are its pricing tiers?", "Exact pricing inquiry")
        _add("high_intent", "High-Intent Commercial", f"Does {brand} offer starter kits, discounts, or subscribe-and-save options?" if is_consumer else f"Does {brand} offer a free trial, free tier, or proof of concept?", "Offer/trial inquiry")
        if mode == "comprehensive":
            _add("high_intent", "High-Intent Commercial", f"What are {brand}'s shipping timelines and free delivery thresholds?" if is_consumer else f"How long does it take to get started with {brand}?", "Fulfilment / time-to-value inquiry")
            _add("high_intent", "High-Intent Commercial", f"What safety testing, ingredient disclosures, or customer reviews does {brand} publish?" if is_consumer else f"What trust, certification, or customer evidence does {brand} publish?", "Trust evidence inquiry")
            _add("high_intent", "High-Intent Commercial", f"How can I order from {brand} or contact customer support?" if is_consumer else f"How can I book a consultation or contact {brand}'s team?", "Direct purchase/contact inquiry")
            _add("high_intent", "High-Intent Commercial", f"What is {brand}'s return, replacement, warranty, and refund policy?", "Return & refund terms inquiry")

        suite_id = f"BMK-{uuid.uuid4().hex[:8].upper()}"
        total_fo = sum(len(q.fan_out_queries) for q in queries)
        return BenchmarkSuite(
            suite_id=suite_id,
            domain=clean_domain,
            brand_name=brand,
            industry=category_label,
            total_queries=len(queries),
            queries=queries,
            matrix_grounding=grounding,
            matrix_confidence=matrix_confidence,
            total_fan_out_queries=total_fo,
        )

    def generate_dynamic_cluster(
        self,
        domain: str,
        brand_name: Optional[str] = None,
        industry: Optional[str] = None,
        competitors: Optional[List[str]] = None,
        personas: Optional[List[str]] = None,
        target_size: int = 100,
        business_profile: Optional[Any] = None,
    ) -> BenchmarkSuite:
        """
        Dynamically clusters and generates synthetic buyer-persona inquiries (up to target_size),
        adapting personas to B2C/D2C/ecommerce vs B2B context.
        """
        clean_domain = (domain or "").lower().replace("https://", "").replace("http://", "").split("/")[0]
        brand = brand_name or (getattr(business_profile, "business_name", None) if business_profile else None) or clean_domain.split(".")[0].capitalize()
        category_label = industry or (getattr(business_profile, "industry", None) if business_profile else None) or "solutions"
        comp_list = [c for c in (competitors or []) if c and str(c).strip()] or ["leading alternatives"]
        is_consumer = self._is_consumer_context(category_label, None, business_profile)

        # Generate base comprehensive suite
        base_suite = self.generate_suite(
            domain=domain,
            brand_name=brand_name,
            industry=industry,
            competitors=competitors,
            mode="comprehensive",
            business_profile=business_profile,
        )

        all_queries: List[BenchmarkQuery] = list(base_suite.queries)
        qid = len(all_queries) + 1

        if is_consumer:
            active_personas = personas or [
                "First-Time Shopper",
                "Ingredient & Safety Conscious Buyer",
                "Value & Bundle Seeker",
                "Repeat Routine User",
            ]
            persona_templates = {
                "First-Time Shopper": [
                    ("Which {brand} starter kit is best for someone trying the brand for the first time?", "starter_recommendation", "high_intent"),
                    ("How quickly does {brand} ship orders and is free shipping available?", "shipping_speed", "high_intent"),
                    ("What do verified customers say about {brand}'s results?", "customer_reviews", "entity"),
                    ("What is {brand}'s return and refund policy if a product is not the right fit?", "returns_policy", "high_intent"),
                ],
                "Ingredient & Safety Conscious Buyer": [
                    ("What active ingredients are used in {brand}'s formulas and are they safe for daily use?", "ingredient_safety", "services"),
                    ("Are {brand} products suitable for sensitive teeth, gums, or skin?", "sensitivity_suitability", "audience"),
                    ("Are {brand} products free from harsh chemicals, SLS, parabens, and artificial dyes?", "clean_formulation", "services"),
                ],
                "Value & Bundle Seeker": [
                    ("How much do {brand}'s combo packs and bundles save compared to single items?", "bundle_value", "commercial"),
                    ("Does {brand} offer subscribe-and-save discounts or loyalty rewards?", "subscription_offers", "high_intent"),
                    ("How does {brand}'s price and quality compare to {comp}?", "price_quality_comparison", "comparative"),
                ],
                "Repeat Routine User": [
                    ("How often should replacement heads or refills for {brand} be ordered?", "refill_cadence", "services"),
                    ("What warranty coverage and replacement support does {brand} offer?", "warranty_support", "high_intent"),
                ],
            }
        else:
            active_personas = personas or [
                "Enterprise Architect",
                "CFO & Procurement",
                "Technical Lead & Developer",
                "Executive & Business Leader",
            ]
            persona_templates = {
                "Enterprise Architect": [
                    ("How does {brand} handle multi-region data residency and disaster recovery?", "security_resilience", "high_intent"),
                    ("What are the integration and automation offerings for {brand}?", "api_extensibility", "services"),
                    ("What access controls and governance features does {brand} support?", "identity_governance", "high_intent"),
                    ("What deployment environments are supported by {brand}?", "infrastructure_deployment", "services"),
                ],
                "CFO & Procurement": [
                    ("What is the typical 3-year Total Cost of Ownership (TCO) for {brand}?", "tco_analysis", "commercial"),
                    ("How is {brand}'s pricing structured across tiers?", "contract_structure", "high_intent"),
                    ("What is the average payback period or measured ROI for {brand} customers?", "roi_quantification", "commercial"),
                    ("Are there onboarding or implementation fees with {brand}?", "procurement_transparency", "high_intent"),
                ],
                "Technical Lead & Developer": [
                    ("How thorough and up-to-date is {brand}'s technical documentation?", "developer_experience", "services"),
                    ("Common implementation challenges or limitations reported by users of {brand}", "dev_limitations", "problem"),
                    ("How easily does {brand} integrate with existing workflows?", "integration_ecosystem", "services"),
                ],
                "Executive & Business Leader": [
                    ("What makes {brand} lower risk than legacy {comp}?", "risk_mitigation", "comparative"),
                    ("Customer retention rate and case studies for {brand}", "market_validation", "entity"),
                    ("Where does {brand} appear in independent industry comparisons?", "analyst_recognition", "commercial"),
                ],
            }

        for persona in active_personas:
            if len(all_queries) >= target_size:
                break
            templates = persona_templates.get(persona, [])
            for tmpl, intent, cat in templates:
                if len(all_queries) >= target_size:
                    break
                text = tmpl.format(brand=brand, comp=comp_list[0], domain=clean_domain)
                fo = self.generate_fan_outs_for_query(
                    query_text=text,
                    category=cat,  # type: ignore
                    brand=brand,
                    domain=clean_domain,
                    industry=category_label,
                    competitors=comp_list,
                    is_consumer=is_consumer,
                )
                all_queries.append(BenchmarkQuery(
                    query_id=f"Q-{qid:02d}",
                    category=cat,  # type: ignore
                    category_label=f"{persona}: {cat.capitalize()}",
                    query_text=text,
                    intent_description=f"[{persona}] {intent}",
                    expected_targets=[brand.lower(), clean_domain],
                    fan_out_queries=fo,
                ))
                qid += 1

        total_fo = sum(len(q.fan_out_queries) for q in all_queries)
        return BenchmarkSuite(
            suite_id=f"DYN-{uuid.uuid4().hex[:8].upper()}",
            domain=clean_domain,
            brand_name=brand,
            industry=category_label,
            total_queries=len(all_queries),
            queries=all_queries,
            matrix_grounding="dynamic_persona_expansion",
            matrix_confidence="high",
            total_fan_out_queries=total_fo,
        )


benchmark_generator = GeoBenchmarkGenerator()


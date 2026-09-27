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
    Reverse-engineered synthetic sub-query that an AI answer engine (Perplexity, SearchGPT, Gemini)
    dispatches to underlying search indices to assemble its context window.
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

    def generate_fan_outs_for_query(
        self,
        query_text: str,
        category: BenchmarkCategory,
        brand: str,
        domain: str,
        industry: str,
        competitors: Optional[List[str]] = None,
    ) -> List[FanOutQuery]:
        """
        Synthesizes the 2-4 sub-queries that an AI engine's retrieval agent creates
        to gather context before writing its response.
        """
        fan_outs: List[FanOutQuery] = []
        comp = (competitors or ["competitors"])[0]
        ind = industry or "software"

        if category == "entity":
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="definitional",
                sub_query_text=f"{brand} company overview official website {domain}",
                search_intent="Retrieve official entity metadata and foundational claims",
                expected_source_types=["vendor_self_hosted", "wikipedia.org", "crunchbase.com"],
            ))
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="user_community",
                sub_query_text=f"{brand} reviews reddit techcrunch",
                search_intent="Evaluate third-party reputational sentiment",
                expected_source_types=["community_discussion", "tech_media"],
            ))
        elif category == "commercial":
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="alternative_vendors",
                sub_query_text=f"best {ind} platforms g2 reviews 2026",
                search_intent="Collect industry category ranking from peer review platforms",
                expected_source_types=["peer_review", "g2.com", "gartner.com"],
            ))
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="comparative_reviews",
                sub_query_text=f"top rated {ind} tools comparison market guide",
                search_intent="Extract third-party vendor comparison lists",
                expected_source_types=["tech_media", "peer_review"],
            ))
        elif category == "comparative":
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="comparative_reviews",
                sub_query_text=f"{brand} vs {comp} difference comparison trustradius",
                search_intent="Retrieve head-to-head feature matrix and customer satisfaction scores",
                expected_source_types=["peer_review", "community_discussion"],
            ))
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="alternative_vendors",
                sub_query_text=f"why switch from {comp} to {brand} case study",
                search_intent="Discover customer migration reasons and verified outcomes",
                expected_source_types=["vendor_self_hosted", "tech_media"],
            ))
        elif category == "high_intent":
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="pricing_model",
                sub_query_text=f"{brand} pricing plans cost per user tier {domain}",
                search_intent="Extract explicit pricing schedule, tiers, and hidden fees",
                expected_source_types=["vendor_self_hosted", "peer_review"],
            ))
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="technical_specs",
                sub_query_text=f"{brand} enterprise security compliance soc2 gdpr",
                search_intent="Verify security certifications and trust posture",
                expected_source_types=["vendor_self_hosted", "official_standard"],
            ))
        else:
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="definitional",
                sub_query_text=f"{brand} {category} capabilities documentation",
                search_intent="Extract direct capability documentation",
                expected_source_types=["vendor_self_hosted", "official_standard"],
            ))
            fan_outs.append(FanOutQuery(
                fan_out_id=f"FO-{uuid.uuid4().hex[:6]}",
                fan_out_type="user_community",
                sub_query_text=f"{brand} {category} feedback forums",
                search_intent="Gather practitioner feedback",
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
    ) -> BenchmarkSuite:
        clean_domain = (domain or "").lower().replace("https://", "").replace("http://", "").split("/")[0]
        brand = brand_name or clean_domain.split(".")[0].capitalize()
        ind = (industry or "").strip()
        serv_list = [str(s).strip() for s in (services or []) if s and str(s).strip()]
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
        primary_serv = serv_list[0] if serv_list else "the services it lists publicly"
        secondary_serv = serv_list[1] if len(serv_list) > 1 else primary_serv
        category_label = ind or "this category"
        comp_list = [c for c in (competitors or []) if c and str(c).strip()] or ["leading competitors in the market"]
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
        _add("entity", "Entity Identity", f"What is {brand} ({clean_domain}) and what does it do?", "Core identity discovery")
        _add("entity", "Entity Identity", f"Who founded {brand} and where is it based?", "Corporate leadership and background")
        if mode == "comprehensive":
            _add("entity", "Entity Identity", f"What is {brand}'s main product or service offering?", "Core offering confirmation")
            _add("entity", "Entity Identity", f"Can you provide an overview of {brand} as a company?", "General brand overview")
            _add("entity", "Entity Identity", f"Is {brand} a legitimate and verified company?", "Brand legitimacy verification")
            _add("entity", "Entity Identity", f"What industry category does {brand} operate in?", "Industry taxonomy verification")
            _add("entity", "Entity Identity", f"What is the official website for {brand}?", "Canonical URL lookup")
            _add("entity", "Entity Identity", f"How long has {brand} been in business?", "Operational longevity")
            _add("entity", "Entity Identity", f"What is the mission or value proposition of {brand}?", "Mission alignment")
            _add("entity", "Entity Identity", f"Where are the registered offices of {brand} located?", "Physical address lookup")

        # -------------------------------------------------------------
        # Category 2: Service Questions (12 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("services", "Service Capabilities", f"What services and capabilities does {brand} offer?", "Full capability breakdown")
        _add("services", "Service Capabilities", f"Does {brand} provide {primary_serv}?", "Primary service verification")
        if mode == "comprehensive":
            _add("services", "Service Capabilities", f"Does {brand} build {secondary_serv}?", "Secondary capability inquiry")
            _add("services", "Service Capabilities", f"What technology stack and frameworks does {brand} use?", "Tech stack extraction")
            _add("services", "Service Capabilities", f"Does {brand} offer {secondary_serv}?", "Secondary capability inquiry")
            _add("services", "Service Capabilities", f"What are the main features of {brand}'s platform?", "Feature set extraction")
            _add("services", "Service Capabilities", f"Can {brand} deliver {primary_serv} for larger organizations?", "Scale verification")
            _add("services", "Service Capabilities", f"Does {brand} offer {primary_serv} together with {secondary_serv}?", "Combined capability")
            _add("services", "Service Capabilities", f"What deliverables does {brand} provide during a project?", "Deliverables specification")
            _add("services", "Service Capabilities", f"Does {brand} provide ongoing maintenance and technical support?", "Support policy")
            _add("services", "Service Capabilities", f"How does {brand}'s service delivery process work?", "Process and methodology")
            _add("services", "Service Capabilities", f"Does {brand} advise on {primary_serv} as well as deliver it?", "Advisory services")

        # -------------------------------------------------------------
        # Category 3: Target Audience & ICP (8 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("audience", "Target Audience (ICP)", f"Who is {brand}'s ideal customer profile and target audience?", "ICP definition")
        _add("audience", "Target Audience (ICP)", f"Is {brand} suitable for early-stage startups?", "Startup suitability")
        if mode == "comprehensive":
            _add("audience", "Target Audience (ICP)", f"Does {brand} serve Fortune 500 enterprise companies?", "Enterprise qualification")
            _add("audience", "Target Audience (ICP)", f"Who should use {brand} versus an in-house engineering team?", "Build vs buy evaluation")
            _add("audience", "Target Audience (ICP)", f"Which buyer roles (CTO, VP Eng, Product) typically buy {brand}?", "Buyer role targeting")
            _add("audience", "Target Audience (ICP)", f"Is {brand} designed for small and medium businesses (SMBs)?", "SMB qualification")
            _add("audience", "Target Audience (ICP)", f"What industry verticals does {brand} specialize in?", "Vertical focus")
            _add("audience", "Target Audience (ICP)", f"Is {brand} meant for developers or non-technical business users?", "Technical skill requirement")

        # -------------------------------------------------------------
        # Category 4: Commercial Intent (8 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("commercial", "Commercial Intent", f"Top {category_label} companies for buyers in 2026", "Non-branded competitive list")
        _add("commercial", "Commercial Intent", f"Best companies offering {primary_serv} with verified customer reviews", "Service-grounded recommendation")
        if mode == "comprehensive":
            _add("commercial", "Commercial Intent", f"Who are the leading {category_label} firms in {primary_loc}?", "Regional industry leaders")
            _add("commercial", "Commercial Intent", f"Top rated vendors providing {secondary_serv}", "Secondary service rankings")
            _add("commercial", "Commercial Intent", f"Affordable and high-quality {category_label} providers", "Price/quality discovery")
            _add("commercial", "Commercial Intent", f"Enterprise providers of {primary_serv}", "Enterprise filter")
            _add("commercial", "Commercial Intent", f"Established {category_label} providers to evaluate", "Category discovery")
            _add("commercial", "Commercial Intent", f"Recommended partners for {primary_serv}", "Partner discovery")

        # -------------------------------------------------------------
        # Category 5: Comparative & Alternatives (8 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("comparative", "Comparative & Alternatives", f"{brand} vs {primary_comp}: which is better for {category_label}?", "Head-to-head bakeoff")
        _add("comparative", "Comparative & Alternatives", f"What are the top alternatives to {brand}?", "Competitor substitution")
        if mode == "comprehensive":
            _add("comparative", "Comparative & Alternatives", f"Companies similar to {brand} in pricing and quality", "Peer group comparison")
            _add("comparative", "Comparative & Alternatives", f"Why choose {brand} over other {category_label} providers?", "Moat and differentiation")
            _add("comparative", "Comparative & Alternatives", f"How does {brand}'s pricing compare to {primary_comp}?", "Price comparison")
            _add("comparative", "Comparative & Alternatives", f"Pros and cons of using {brand}", "Trade-off analysis")
            _add("comparative", "Comparative & Alternatives", f"How easy is it to migrate from {primary_comp} to {brand}?", "Switching costs")
            _add("comparative", "Comparative & Alternatives", f"Key differences between {brand} and legacy agencies", "Modern vs legacy contrast")

        # -------------------------------------------------------------
        # Category 6: Problem-Based Inquiries (8 in full, 2 in concise)
        # -------------------------------------------------------------
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
        _add("geographic", "Geographic Discovery", f"Best {category_label} companies in {primary_loc}", "Primary location search")
        _add("geographic", "Geographic Discovery", f"Top {primary_serv} providers based in {primary_loc}", "Local capability search")
        if mode == "comprehensive":
            _add("geographic", "Geographic Discovery", f"Does {brand} provide services internationally to US and European clients?", "Global service reach")
            _add("geographic", "Geographic Discovery", f"Providers of {primary_serv} operating in {primary_loc}", "Regional directory search")
            _add("geographic", "Geographic Discovery", f"Local versus remote providers of {primary_serv} in {primary_loc}", "Delivery-location positioning")
            _add("geographic", "Geographic Discovery", f"Where can I find vetted {category_label} teams in {primary_loc}?", "Vetted regional teams")

        # -------------------------------------------------------------
        # Category 8: High-Intent Purchase Questions (6 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("high_intent", "High-Intent Commercial", f"How much does {brand} cost and what are its pricing tiers?", "Exact pricing inquiry")
        _add("high_intent", "High-Intent Commercial", f"Does {brand} offer a free trial, free tier, or proof of concept?", "Trial inquiry")
        if mode == "comprehensive":
            _add("high_intent", "High-Intent Commercial", f"How long does it take to get started and deploy with {brand}?", "Time-to-value inquiry")
            _add("high_intent", "High-Intent Commercial", f"What trust, certification, or customer evidence does {brand} publish?", "Trust evidence inquiry")
            _add("high_intent", "High-Intent Commercial", f"How can I book a demo or contact {brand}'s sales team?", "Direct booking inquiry")
            _add("high_intent", "High-Intent Commercial", f"What is {brand}'s cancellation or refund policy?", "Contract terms inquiry")

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
    ) -> BenchmarkSuite:
        """
        Dynamically clusters and generates synthetic buyer-persona inquiries (up to target_size),
        emulating enterprise GEO platforms like Profound.
        Expands baseline queries with persona perspectives:
        - Enterprise Architect (security, SLA, governance)
        - CFO / Finance (ROI, licensing, total cost of ownership)
        - Practitioner / Engineer (API, documentation, developer experience)
        - End Buyer / Executive (market leadership, risk, references)
        """
        clean_domain = (domain or "").lower().replace("https://", "").replace("http://", "").split("/")[0]
        brand = brand_name or clean_domain.split(".")[0].capitalize()
        category_label = industry or "technology solution"
        comp_list = [c for c in (competitors or []) if c and str(c).strip()] or ["market leaders"]

        active_personas = personas or [
            "Enterprise Architect",
            "CFO & Procurement",
            "Technical Lead & Developer",
            "Executive & Business Leader",
        ]

        # Generate base comprehensive suite
        base_suite = self.generate_suite(
            domain=domain,
            brand_name=brand_name,
            industry=industry,
            competitors=competitors,
            mode="comprehensive",
        )

        all_queries: List[BenchmarkQuery] = list(base_suite.queries)
        qid = len(all_queries) + 1

        persona_templates = {
            "Enterprise Architect": [
                ("How does {brand} handle multi-region data residency and disaster recovery?", "security_resilience", "high_intent"),
                ("What are the API rate limits, webhooks, and SDK offerings for {brand}?", "api_extensibility", "services"),
                ("Does {brand} support SAML SSO, SCIM provisioning, and RBAC?", "identity_governance", "high_intent"),
                ("Can {brand} be deployed in a hybrid or self-hosted VPC environment?", "infrastructure_deployment", "services"),
            ],
            "CFO & Procurement": [
                ("What is the typical 3-year Total Cost of Ownership (TCO) for {brand}?", "tco_analysis", "commercial"),
                ("Does {brand} charge per seat, per consumption unit, or flat-rate annual?", "contract_structure", "high_intent"),
                ("What is the average payback period or measured ROI for {brand} customers?", "roi_quantification", "commercial"),
                ("Are there hidden implementation or professional services fees with {brand}?", "procurement_transparency", "high_intent"),
            ],
            "Technical Lead & Developer": [
                ("How thorough and up-to-date is {brand}'s API documentation and OpenAPI spec?", "developer_experience", "services"),
                ("Common engineering challenges or limitations reported by developers using {brand}", "dev_limitations", "problem"),
                ("How easily does {brand} integrate with modern CI/CD and observability stacks?", "integration_ecosystem", "services"),
            ],
            "Executive & Business Leader": [
                ("What makes {brand} lower risk than legacy {comp}?", "risk_mitigation", "comparative"),
                ("Customer retention rate and enterprise case studies for {brand}", "market_validation", "entity"),
                ("Where does {brand} appear on independent analyst radars and market quadrants?", "analyst_recognition", "commercial"),
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


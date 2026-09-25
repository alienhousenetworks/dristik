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


class BenchmarkQuery(BaseModel):
    query_id: str
    category: BenchmarkCategory
    category_label: str
    query_text: str
    intent_description: str
    expected_targets: List[str] = Field(default_factory=list)


class BenchmarkSuite(BaseModel):
    suite_id: str
    domain: str
    brand_name: str
    industry: str
    total_queries: int
    queries: List[BenchmarkQuery] = Field(default_factory=list)


class GeoBenchmarkGenerator:
    """
    Synthesizes a standardized, reproducible benchmark question set tailored to any business.
    """

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
        ind = industry or "Software & Technology Services"
        serv_list = services or ["AI development", "custom software engineering", "cloud infrastructure"]
        primary_serv = serv_list[0] if serv_list else "custom software engineering"
        secondary_serv = serv_list[1] if len(serv_list) > 1 else "cloud architecture"
        comp_list = competitors or ["leading competitors in the market"]
        primary_comp = comp_list[0] if comp_list else "market alternatives"
        loc_list = locations or ["India", "United States", "global"]
        primary_loc = loc_list[0] if loc_list else "global"

        queries: List[BenchmarkQuery] = []
        qid = 1

        def _add(cat: BenchmarkCategory, label: str, text: str, desc: str):
            nonlocal qid
            queries.append(BenchmarkQuery(
                query_id=f"Q-{qid:02d}",
                category=cat,
                category_label=label,
                query_text=text,
                intent_description=desc,
                expected_targets=[brand.lower(), clean_domain],
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
            _add("services", "Service Capabilities", f"Does {brand} offer custom API development and integrations?", "API capability")
            _add("services", "Service Capabilities", f"What are the main features of {brand}'s platform?", "Feature set extraction")
            _add("services", "Service Capabilities", f"Can {brand} handle enterprise-scale workloads?", "Scalability verification")
            _add("services", "Service Capabilities", f"Does {brand} offer mobile and cloud application development?", "Multi-platform support")
            _add("services", "Service Capabilities", f"What deliverables does {brand} provide during a project?", "Deliverables specification")
            _add("services", "Service Capabilities", f"Does {brand} provide ongoing maintenance and technical support?", "Support policy")
            _add("services", "Service Capabilities", f"How does {brand}'s service delivery process work?", "Process and methodology")
            _add("services", "Service Capabilities", f"Does {brand} offer consulting and architecture design?", "Advisory services")

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
        _add("commercial", "Commercial Intent", f"Top {ind} companies for startups in 2026", "Non-branded competitive list")
        _add("commercial", "Commercial Intent", f"Best companies offering {primary_serv} with verified customer reviews", "Service-grounded recommendation")
        if mode == "comprehensive":
            _add("commercial", "Commercial Intent", f"Who are the leading {ind} firms in {primary_loc}?", "Regional industry leaders")
            _add("commercial", "Commercial Intent", f"Top rated vendors providing {secondary_serv}", "Secondary service rankings")
            _add("commercial", "Commercial Intent", f"Affordable and high-quality {ind} agencies", "Price/quality discovery")
            _add("commercial", "Commercial Intent", f"Enterprise {primary_serv} providers with SOC 2 compliance", "Enterprise filter")
            _add("commercial", "Commercial Intent", f"Fastest growing {ind} startups to watch", "Growth category search")
            _add("commercial", "Commercial Intent", f"Recommended development partners for building AI SaaS applications", "SaaS development partners")

        # -------------------------------------------------------------
        # Category 5: Comparative & Alternatives (8 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("comparative", "Comparative & Alternatives", f"{brand} vs {primary_comp}: which is better for {ind}?", "Head-to-head bakeoff")
        _add("comparative", "Comparative & Alternatives", f"What are the top alternatives to {brand}?", "Competitor substitution")
        if mode == "comprehensive":
            _add("comparative", "Comparative & Alternatives", f"Companies similar to {brand} in pricing and quality", "Peer group comparison")
            _add("comparative", "Comparative & Alternatives", f"Why choose {brand} over other {ind} providers?", "Moat and differentiation")
            _add("comparative", "Comparative & Alternatives", f"How does {brand}'s pricing compare to {primary_comp}?", "Price comparison")
            _add("comparative", "Comparative & Alternatives", f"Pros and cons of using {brand}", "Trade-off analysis")
            _add("comparative", "Comparative & Alternatives", f"How easy is it to migrate from {primary_comp} to {brand}?", "Switching costs")
            _add("comparative", "Comparative & Alternatives", f"Key differences between {brand} and legacy agencies", "Modern vs legacy contrast")

        # -------------------------------------------------------------
        # Category 6: Problem-Based Inquiries (8 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("problem", "Problem-Based", f"Which company can build a production-ready AI application with low latency?", "Technical problem inquiry")
        _add("problem", "Problem-Based", f"How can a business hire experts for {primary_serv}?", "Talent/vendor sourcing")
        if mode == "comprehensive":
            _add("problem", "Problem-Based", f"Who can migrate our infrastructure to modern cloud architectures?", "Migration challenge")
            _add("problem", "Problem-Based", f"How to automate backend workflows using generative AI safely?", "GenAI workflow challenge")
            _add("problem", "Problem-Based", f"Who provides turnkey development for Series A venture-backed SaaS?", "Venture startup challenge")
            _add("problem", "Problem-Based", f"What is the best way to develop custom LLM agents for enterprise?", "Agent development challenge")
            _add("problem", "Problem-Based", f"Which agencies build scalable FastAPI and PyTorch software?", "Stack-specific challenge")
            _add("problem", "Problem-Based", f"How to achieve 99.99% uptime for AI inference microservices?", "High availability challenge")

        # -------------------------------------------------------------
        # Category 7: Geographic Discovery (6 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("geographic", "Geographic Discovery", f"Best {ind} companies in {primary_loc}", "Primary location search")
        _add("geographic", "Geographic Discovery", f"Top {primary_serv} providers based in {primary_loc}", "Local capability search")
        if mode == "comprehensive":
            _add("geographic", "Geographic Discovery", f"Does {brand} provide services internationally to US and European clients?", "Global service reach")
            _add("geographic", "Geographic Discovery", f"Tech and software development agencies operating in {primary_loc}", "Regional directory search")
            _add("geographic", "Geographic Discovery", f"Offshore vs nearshore development in {primary_loc} for AI", "Offshore positioning")
            _add("geographic", "Geographic Discovery", f"Where can I find vetted {ind} engineering teams in {primary_loc}?", "Vetted regional teams")

        # -------------------------------------------------------------
        # Category 8: High-Intent Purchase Questions (6 in full, 2 in concise)
        # -------------------------------------------------------------
        _add("high_intent", "High-Intent Commercial", f"How much does {brand} cost and what are its pricing tiers?", "Exact pricing inquiry")
        _add("high_intent", "High-Intent Commercial", f"Does {brand} offer a free trial, free tier, or proof of concept?", "Trial inquiry")
        if mode == "comprehensive":
            _add("high_intent", "High-Intent Commercial", f"How long does it take to get started and deploy with {brand}?", "Time-to-value inquiry")
            _add("high_intent", "High-Intent Commercial", f"Is {brand} SOC 2, HIPAA, or ISO 27001 compliant?", "Compliance proof")
            _add("high_intent", "High-Intent Commercial", f"How can I book a demo or contact {brand}'s sales team?", "Direct booking inquiry")
            _add("high_intent", "High-Intent Commercial", f"What is {brand}'s cancellation or refund policy?", "Contract terms inquiry")

        suite_id = f"BMK-{uuid.uuid4().hex[:8].upper()}"
        return BenchmarkSuite(
            suite_id=suite_id,
            domain=clean_domain,
            brand_name=brand,
            industry=ind,
            total_queries=len(queries),
            queries=queries,
        )


benchmark_generator = GeoBenchmarkGenerator()

"""
Dristik AI 35-Capability Taxonomy Registry
Defines the 35 cognitive capabilities across 8 intelligence domains,
their execution tier (Deterministic, SLM, Reasoning, High-Reasoning),
and worker routing policies.
"""
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class CapabilityDomain(str, Enum):
    TECHNICAL = "TECHNICAL"
    STRUCTURED_DATA = "STRUCTURED_DATA"
    BUSINESS = "BUSINESS"
    CONTENT = "CONTENT"
    GEO = "GEO"
    AI_SEARCH = "AI_SEARCH"
    EXPERIENCE = "EXPERIENCE"
    VERIFICATION = "VERIFICATION"

class ExecutionTier(str, Enum):
    TIER_A_DETERMINISTIC = "TIER_A_DETERMINISTIC"  # $0 inference, fast, 100% auditable
    TIER_B_SLM = "TIER_B_SLM"                      # 8B SLM (fast extraction / classification)
    TIER_C_REASONING = "TIER_C_REASONING"          # 14B - 32B (deep domain reasoning / GEO)
    TIER_D_HIGH_REASONING = "TIER_D_HIGH_REASONING"# 70B+ (adversarial arbitration / executive synthesis)

class CapabilitySpec(BaseModel):
    id: str                                        # e.g., "01_discovery"
    name: str                                      # e.g., "Discovery & Crawl Health"
    domain: CapabilityDomain
    tier: ExecutionTier
    description: str
    required_evidence: List[str] = Field(default_factory=list)
    output_schema: str = "standard_finding"
    cost_weight: float = 1.0
    can_escalate: bool = True
    agent_id: Optional[str] = None                 # v3 specialist agent ID (e.g. "seo.crawl.v3")
    worker_type: Optional[str] = None              # Reusable worker type (e.g. "analyst_worker")

# Complete 35-Capability Taxonomy Registry Definition
CAPABILITY_REGISTRY: Dict[str, CapabilitySpec] = {
    # 1. Technical Intelligence
    "01_discovery": CapabilitySpec(
        id="01_discovery",
        name="Discovery & Crawlability",
        domain=CapabilityDomain.TECHNICAL,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Analyzes sitemap, robots.txt, HTTP status codes, crawl depth, and redirect loops.",
        required_evidence=["crawl_manifest", "sitemap_xml", "robots_txt"]
    ),
    "02_semantic_structure": CapabilitySpec(
        id="02_semantic_structure",
        name="Semantic DOM & Heading Architecture",
        domain=CapabilityDomain.TECHNICAL,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Validates H1-H6 heading hierarchy, landmark elements (nav/main/footer), and semantic markup.",
        required_evidence=["dom_elements", "headings_tree"]
    ),
    "03_indexability": CapabilitySpec(
        id="03_indexability",
        name="Indexability & Canonicalization",
        domain=CapabilityDomain.TECHNICAL,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Checks canonical URLs, meta robots tags, X-Robots-Tag headers, and duplicate content risks.",
        required_evidence=["canonical_url", "robots_meta", "status_code"]
    ),
    "04_link_architecture": CapabilitySpec(
        id="04_link_architecture",
        name="Link Graph & PageRank Distribution",
        domain=CapabilityDomain.TECHNICAL,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Inspects internal link topology, broken links, anchor text distribution, and orphan pages.",
        required_evidence=["internal_links", "external_links"]
    ),
    "05_performance": CapabilitySpec(
        id="05_performance",
        name="Core Web Vitals & Server Latency",
        domain=CapabilityDomain.TECHNICAL,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Measures TTFB, page weight, DOM complexity, script blocking, and Core Web Vitals indicators.",
        required_evidence=["ttfb_ms", "page_size", "script_count"]
    ),
    "06_security": CapabilitySpec(
        id="06_security",
        name="Security & Transport Layer Defense",
        domain=CapabilityDomain.TECHNICAL,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Audits HTTPS enforcement, TLS certificates, HSTS, CSP, X-Frame-Options, and mixed content.",
        required_evidence=["protocol", "security_headers"]
    ),
    "07_asset_optimization": CapabilitySpec(
        id="07_asset_optimization",
        name="Asset & Media Optimization",
        domain=CapabilityDomain.TECHNICAL,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Evaluates image alt attributes, WebP/AVIF adoption, script compression, and render blocking.",
        required_evidence=["image_stats", "stylesheets_count", "scripts_count"]
    ),
    "08_mobile_readiness": CapabilitySpec(
        id="08_mobile_readiness",
        name="Mobile Viewport & Responsiveness",
        domain=CapabilityDomain.TECHNICAL,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Checks viewport tags, tap target configurations, and mobile responsive layout cues.",
        required_evidence=["viewport", "dom_metrics"]
    ),

    # 2. Structured Data
    "09_schema_syntax": CapabilitySpec(
        id="09_schema_syntax",
        name="Schema.org JSON-LD Syntax & Coverage",
        domain=CapabilityDomain.STRUCTURED_DATA,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Validates JSON-LD schema presence, Schema.org conformance, and required properties.",
        required_evidence=["raw_schema", "schema_types"]
    ),
    "10_entity_graph": CapabilitySpec(
        id="10_entity_graph",
        name="Knowledge Graph & Entity Alignment",
        domain=CapabilityDomain.STRUCTURED_DATA,
        tier=ExecutionTier.TIER_B_SLM,
        description="Maps named entities across pages, validating sameAs properties, Organization and Product entities.",
        required_evidence=["schema_types", "headings", "body_text"]
    ),
    "11_opengraph_metadata": CapabilitySpec(
        id="11_opengraph_metadata",
        name="OpenGraph & Social Sharing Meta",
        domain=CapabilityDomain.STRUCTURED_DATA,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Audits og:title, og:description, og:image, twitter:card tags for complete social previews.",
        required_evidence=["og_tags", "twitter_tags"]
    ),

    # 3. Business Intelligence
    "12_positioning": CapabilitySpec(
        id="12_positioning",
        name="Strategic Positioning & Value Narrative",
        domain=CapabilityDomain.BUSINESS,
        tier=ExecutionTier.TIER_B_SLM,
        description="Evaluates clarity and uniqueness of the core commercial value proposition and market category.",
        required_evidence=["h1", "h2", "title", "body_text"]
    ),
    "13_icp_alignment": CapabilitySpec(
        id="13_icp_alignment",
        name="ICP & Target Audience Alignment",
        domain=CapabilityDomain.BUSINESS,
        tier=ExecutionTier.TIER_B_SLM,
        description="Identifies who the site is built for (Enterprise, SMB, Developer, B2C) and flags audience confusion.",
        required_evidence=["h1", "body_text", "ctas", "pricing_hints"]
    ),
    "14_value_prop_strength": CapabilitySpec(
        id="14_value_prop_strength",
        name="Value Proposition Directness",
        domain=CapabilityDomain.BUSINESS,
        tier=ExecutionTier.TIER_B_SLM,
        description="Measures how quickly a visitor understands 'What is this?', 'Who is it for?', and 'Why choose it?'.",
        required_evidence=["h1", "h2", "first_fold_text"]
    ),
    "15_commercial_clarity": CapabilitySpec(
        id="15_commercial_clarity",
        name="Pricing & Commercial Model Clarity",
        domain=CapabilityDomain.BUSINESS,
        tier=ExecutionTier.TIER_B_SLM,
        description="Evaluates pricing transparency, plan tiers, SLA guarantees, and enterprise sales contact paths.",
        required_evidence=["pricing_text", "ctas", "plan_features"]
    ),
    "16_competitive_differentiation": CapabilitySpec(
        id="16_competitive_differentiation",
        name="Competitive Moat & Differentiation",
        domain=CapabilityDomain.BUSINESS,
        tier=ExecutionTier.TIER_C_REASONING,
        description="Identifies defensible differentiators vs generic industry buzzwords and commodity phrasing.",
        required_evidence=["features", "value_props", "social_proof"]
    ),

    # 4. Content Intelligence
    "17_content_depth": CapabilitySpec(
        id="17_content_depth",
        name="Content Depth & Topical Density",
        domain=CapabilityDomain.CONTENT,
        tier=ExecutionTier.TIER_B_SLM,
        description="Assesses whether content provides thorough, authoritative coverage or thin surface text.",
        required_evidence=["word_count", "headings", "body_text"]
    ),
    "18_eeat_authority": CapabilitySpec(
        id="18_eeat_authority",
        name="E-E-A-T & Authoritativeness Signals",
        domain=CapabilityDomain.CONTENT,
        tier=ExecutionTier.TIER_B_SLM,
        description="Audits Experience, Expertise, Authoritativeness, and Trust signals (byline, citations, credentials).",
        required_evidence=["author_info", "citations", "about_page", "certifications"]
    ),
    "19_readability": CapabilitySpec(
        id="19_readability",
        name="Readability & Cognitive Fluency",
        domain=CapabilityDomain.CONTENT,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Calculates Flesch-Kincaid grade level, sentence complexity, and vocabulary density.",
        required_evidence=["readability_score", "word_count", "body_text"]
    ),
    "20_topic_coverage": CapabilitySpec(
        id="20_topic_coverage",
        name="Topical Breadth & Keyword Architecture",
        domain=CapabilityDomain.CONTENT,
        tier=ExecutionTier.TIER_B_SLM,
        description="Evaluates comprehensive semantic coverage of the domain and identifies topical content gaps.",
        required_evidence=["headings_across_pages", "titles_across_pages"]
    ),
    "21_cannibalization": CapabilitySpec(
        id="21_cannibalization",
        name="Multi-Page Intent Cannibalization",
        domain=CapabilityDomain.CONTENT,
        tier=ExecutionTier.TIER_A_DETERMINISTIC,
        description="Detects competing URLs targeting identical titles, H1s, or search intents across the crawl.",
        required_evidence=["duplicate_titles", "duplicate_descriptions", "duplicate_h1s"]
    ),

    # 5. GEO Intelligence (Generative Engine Optimization)
    "22_direct_extractability": CapabilitySpec(
        id="22_direct_extractability",
        name="Direct Answer Extractability",
        domain=CapabilityDomain.GEO,
        tier=ExecutionTier.TIER_B_SLM,
        description="Tests whether LLMs can easily parse clean 1-2 sentence definitions and direct answers from text.",
        required_evidence=["headings", "first_paragraphs", "bullet_lists"]
    ),
    "23_information_gain": CapabilitySpec(
        id="23_information_gain",
        name="Information Gain & Proprietary Data",
        domain=CapabilityDomain.GEO,
        tier=ExecutionTier.TIER_C_REASONING,
        description="Detects novel insights, proprietary benchmarks, or unique perspectives not found in baseline LLM training.",
        required_evidence=["data_tables", "statistics", "case_studies", "body_text"]
    ),
    "24_summarizability": CapabilitySpec(
        id="24_summarizability",
        name="LLM Summarizability & TL;DR Readiness",
        domain=CapabilityDomain.GEO,
        tier=ExecutionTier.TIER_B_SLM,
        description="Evaluates whether pages contain crisp summaries, structured key takeaways, and modular sections.",
        required_evidence=["headings", "summaries", "lists"]
    ),
    "25_citation_readiness": CapabilitySpec(
        id="25_citation_readiness",
        name="Citation & Attribution Readiness",
        domain=CapabilityDomain.GEO,
        tier=ExecutionTier.TIER_B_SLM,
        description="Checks if facts are phrased as quotable, attributable claims with explicit sources and anchor context.",
        required_evidence=["claims", "author_info", "schema_org"]
    ),

    # 6. AI Search Intelligence
    "26_ai_discoverability": CapabilitySpec(
        id="26_ai_discoverability",
        name="AI Discoverability Simulation Matrix",
        domain=CapabilityDomain.AI_SEARCH,
        tier=ExecutionTier.TIER_C_REASONING,
        description="Simulates how AI answer engines extract, synthesize, and judge the site across standard buyer queries.",
        required_evidence=["body_text", "business_profile", "schema_types"]
    ),
    "27_chatgpt_scenario": CapabilitySpec(
        id="27_chatgpt_scenario",
        name="ChatGPT Search Retrieval Scenario",
        domain=CapabilityDomain.AI_SEARCH,
        tier=ExecutionTier.TIER_B_SLM,
        description="Evaluates answer formulation when a user asks ChatGPT: 'What does [Brand] do and is it good for X?'.",
        required_evidence=["business_profile", "headings", "body_text"]
    ),
    "28_perplexity_scenario": CapabilitySpec(
        id="28_perplexity_scenario",
        name="Perplexity Factoid & Source Extraction",
        domain=CapabilityDomain.AI_SEARCH,
        tier=ExecutionTier.TIER_B_SLM,
        description="Evaluates whether Perplexity-style multi-source synthesis identifies this domain as the primary reference.",
        required_evidence=["citations", "schema_org", "pricing"]
    ),
    "29_gemini_scenario": CapabilitySpec(
        id="29_gemini_scenario",
        name="Google Gemini & AI Overviews Scenario",
        domain=CapabilityDomain.AI_SEARCH,
        tier=ExecutionTier.TIER_B_SLM,
        description="Evaluates eligibility for inclusion in Google AI Overviews based on structure, schema, and direct answers.",
        required_evidence=["schema_types", "headings", "lists", "tables"]
    ),
    "30_claude_scenario": CapabilitySpec(
        id="30_claude_scenario",
        name="Claude Deep Research Synthesis Scenario",
        domain=CapabilityDomain.AI_SEARCH,
        tier=ExecutionTier.TIER_B_SLM,
        description="Evaluates how Claude's analytical long-context evaluation judges the technical rigor of the site.",
        required_evidence=["content_depth", "readability", "case_studies"]
    ),

    # 7. Experience Intelligence
    "31_ux_friction": CapabilitySpec(
        id="31_ux_friction",
        name="UX Cognitive Friction & Navigation Clarity",
        domain=CapabilityDomain.EXPERIENCE,
        tier=ExecutionTier.TIER_B_SLM,
        description="Identifies clutter, confusing navigation paths, overwhelming walls of text, and unclear visual hierarchy.",
        required_evidence=["dom_elements_count", "headings", "ctas"]
    ),
    "32_trust_signals": CapabilitySpec(
        id="32_trust_signals",
        name="Trust Signals, Proof Elements & Compliance",
        domain=CapabilityDomain.EXPERIENCE,
        tier=ExecutionTier.TIER_B_SLM,
        description="Audits customer logos, testimonials, privacy policy, terms of service, and security certifications.",
        required_evidence=["trust_badges", "external_links", "footer_links"]
    ),
    "33_conversion_cro": CapabilitySpec(
        id="33_conversion_cro",
        name="Conversion Architecture & Call-To-Action Clarity",
        domain=CapabilityDomain.EXPERIENCE,
        tier=ExecutionTier.TIER_B_SLM,
        description="Audits CTA placement, action verb directness, form friction, and lead capture clarity.",
        required_evidence=["ctas", "first_fold_text", "links"]
    ),

    # 8. Verification & Arbitration
    "34_adversarial_verification": CapabilitySpec(
        id="34_adversarial_verification",
        name="Adversarial Verification & Evidence Falsification",
        domain=CapabilityDomain.VERIFICATION,
        tier=ExecutionTier.TIER_C_REASONING,
        description="Adversarially challenges every claim against raw extracted DOM evidence to eliminate hallucinations.",
        required_evidence=["claims", "evidence_store", "evidence_graph"]
    ),
    "35_contradiction_resolution": CapabilitySpec(
        id="35_contradiction_resolution",
        name="Cross-Page Contradiction Resolution & Arbitration",
        domain=CapabilityDomain.VERIFICATION,
        tier=ExecutionTier.TIER_D_HIGH_REASONING,
        description="Resolves conflicting claims across pages (e.g. homepage enterprise claim vs SMB pricing) via arbiter.",
        required_evidence=["contradictions", "evidence_graph", "claims"]
    )
}

def get_capability(cap_id: str) -> Optional[CapabilitySpec]:
    if cap_id in CAPABILITY_REGISTRY:
        return CAPABILITY_REGISTRY[cap_id]
    for cap in CAPABILITY_REGISTRY.values():
        if cap.agent_id == cap_id:
            return cap
    return None

def get_capabilities_by_domain(domain: CapabilityDomain) -> List[CapabilitySpec]:
    return [cap for cap in CAPABILITY_REGISTRY.values() if cap.domain == domain]

def get_capabilities_by_tier(tier: ExecutionTier) -> List[CapabilitySpec]:
    return [cap for cap in CAPABILITY_REGISTRY.values() if cap.tier == tier]

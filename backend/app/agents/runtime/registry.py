"""
Dristik AI Specialist Agent Registry v3
Maintains typed agent contracts, capabilities, allowed models, token budgets, risk levels,
and worker pool mappings across the 35 specialist agents.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AgentDefinition(BaseModel):
    agent_id: str
    agent_name: str
    version: str = "3.0.0"
    domain: str
    worker_type: str = "analyst_worker"
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    allowed_models: List[str] = Field(default_factory=list)
    token_budget: int = 4000
    risk_level: str = "low"
    timeout_sec: int = 20
    dependencies: List[str] = Field(default_factory=list)
    required_evidence: List[str] = Field(default_factory=list)
    forbidden_operations: List[str] = Field(default_factory=list)

# Complete 35 Specialist Agent Workforce
SPECIALIST_AGENTS_V3: Dict[str, AgentDefinition] = {
    # DOMAIN 1: BUSINESS INTELLIGENCE
    "business.discovery.v3": AgentDefinition(
        agent_id="business.discovery.v3",
        agent_name="Business Discovery Agent",
        domain="BUSINESS",
        worker_type="analyst_worker",
        description="Determines company name, products, services, industry, target customer, business model, and value proposition.",
        capabilities=["business_identity", "offering_extraction", "value_prop_detection"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4000,
        risk_level="low",
        timeout_sec=20,
        dependencies=[],
        required_evidence=["homepage_dom", "header_nav", "hero_text", "footer_text"],
        forbidden_operations=["inferring_unsupported_business_models", "guessing_pricing"]
    ),
    "business.icp.v3": AgentDefinition(
        agent_id="business.icp.v3",
        agent_name="ICP Intelligence Agent",
        version="4.0.0",
        domain="BUSINESS",
        worker_type="analyst_worker",
        description="Determines ideal customer profile, buyer type (B2B/B2C), company size, industry, buyer roles, and pain points.",
        capabilities=["icp_classification", "buyer_role_mapping", "customer_problem_analysis"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4000,
        risk_level="low",
        timeout_sec=20,
        dependencies=["business.discovery.v3"],
        required_evidence=["homepage_dom", "use_cases_page", "case_studies", "external_ground_truth"]
    ),
    "business.intent.v3": AgentDefinition(
        agent_id="business.intent.v3",
        agent_name="Search Intent Agent",
        domain="BUSINESS",
        worker_type="analyst_worker",
        description="Maps visitor search intents: Informational, Commercial Investigation, Transactional, Navigational, Comparison.",
        capabilities=["intent_classification", "journey_mapping", "funnel_stage_tagging"],
        allowed_models=["fast_slm", "reasoning_model"],
        token_budget=3500,
        risk_level="low",
        timeout_sec=15,
        dependencies=["business.discovery.v3"],
        required_evidence=["headings", "meta_descriptions", "urls"]
    ),
    "business.commercial.v3": AgentDefinition(
        agent_id="business.commercial.v3",
        agent_name="Commercial Intelligence Agent",
        version="4.0.0",
        domain="BUSINESS",
        worker_type="analyst_worker",
        description="Analyzes pricing models, packages, CTA friction, sales funnels, free trials, and commercial trust requirements.",
        capabilities=["pricing_analysis", "monetization_detection", "commercial_friction"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4500,
        risk_level="medium",
        timeout_sec=20,
        dependencies=["business.discovery.v3"],
        required_evidence=["pricing_table", "cta_elements", "terms_of_sale", "external_ground_truth"]
    ),
    "business.semantic_strategist.v3": AgentDefinition(
        agent_id="business.semantic_strategist.v3",
        agent_name="Semantic Business Strategist",
        domain="BUSINESS",
        worker_type="strategist_worker",
        description="Synthesizes business findings to detect identity, positioning, audience, product, or commercial conflicts.",
        capabilities=["identity_arbitration", "conflict_detection", "canonical_business_synthesis"],
        allowed_models=["judge_model", "reasoning_model"],
        token_budget=6000,
        risk_level="medium",
        timeout_sec=25,
        dependencies=["business.discovery.v3", "business.icp.v3", "business.intent.v3", "business.commercial.v3"],
        required_evidence=["claims"]
    ),

    # DOMAIN 2: TECHNICAL SEO
    "seo.crawl.v3": AgentDefinition(
        agent_id="seo.crawl.v3",
        agent_name="Crawl Intelligence Agent",
        domain="TECHNICAL_SEO",
        worker_type="extractor_worker",
        description="Deterministic analysis of robots.txt, sitemaps, crawl depth, status codes, redirects, and orphan pages.",
        capabilities=["crawlability_audit", "status_check", "redirect_loop_detection"],
        allowed_models=["deterministic"],
        token_budget=1000,
        risk_level="low",
        timeout_sec=15,
        required_evidence=["robots_txt", "sitemap_xml", "http_status_codes"]
    ),
    "seo.indexability.v3": AgentDefinition(
        agent_id="seo.indexability.v3",
        agent_name="Indexability Agent",
        domain="TECHNICAL_SEO",
        worker_type="analyst_worker",
        description="Audits noindex directives, canonical link tags, X-Robots-Tag, parameter duplicates, and indexation conflicts.",
        capabilities=["canonical_validation", "robots_meta_audit", "duplicate_risk_check"],
        allowed_models=["deterministic", "fast_slm"],
        token_budget=2000,
        risk_level="low",
        timeout_sec=15,
        required_evidence=["canonical_url", "meta_robots", "x_robots_tag"]
    ),
    "seo.html.v3": AgentDefinition(
        agent_id="seo.html.v3",
        agent_name="Technical HTML Agent",
        domain="TECHNICAL_SEO",
        worker_type="extractor_worker",
        description="Validates title tags, meta descriptions, H1-H6 hierarchy, semantic landmarks, and HTML5 conformance.",
        capabilities=["semantic_html_audit", "heading_tree_check", "meta_length_validation"],
        allowed_models=["deterministic"],
        token_budget=1500,
        risk_level="low",
        timeout_sec=15,
        required_evidence=["raw_dom", "headings_tree", "meta_tags"]
    ),
    "seo.internal_links.v3": AgentDefinition(
        agent_id="seo.internal_links.v3",
        agent_name="Internal Linking Agent",
        domain="TECHNICAL_SEO",
        worker_type="analyst_worker",
        description="Builds page-to-page link graph, detecting orphan pages, depth violations, weak anchor text, and link concentration.",
        capabilities=["link_graph_builder", "orphan_detection", "anchor_distribution"],
        allowed_models=["deterministic", "fast_slm"],
        token_budget=2500,
        risk_level="low",
        timeout_sec=20,
        required_evidence=["internal_link_graph", "anchor_texts"]
    ),
    "seo.performance.v3": AgentDefinition(
        agent_id="seo.performance.v3",
        agent_name="Performance Agent",
        version="4.0.0",
        domain="TECHNICAL_SEO",
        worker_type="analyst_worker",
        description="Analyzes TTFB, resource weights, render blocking, and CWV indicators. Never fabricates unmeasured metrics.",
        capabilities=["ttfb_analysis", "resource_weight_breakdown", "render_blocking_audit"],
        allowed_models=["deterministic"],
        token_budget=1500,
        risk_level="low",
        timeout_sec=15,
        required_evidence=["ttfb_ms", "resource_timings", "payload_size", "external_ground_truth"],
        forbidden_operations=["inventing_core_web_vitals", "guessing_real_user_lcp"]
    ),
    "seo.security.v3": AgentDefinition(
        agent_id="seo.security.v3",
        agent_name="Security & Infrastructure SEO Agent",
        domain="TECHNICAL_SEO",
        worker_type="extractor_worker",
        description="Checks HTTPS enforcement, TLS certificate validity, HSTS, CSP, X-Frame-Options, and mixed content.",
        capabilities=["security_header_audit", "ssl_tls_check", "mixed_content_detection"],
        allowed_models=["deterministic"],
        token_budget=1000,
        risk_level="low",
        timeout_sec=10,
        required_evidence=["response_headers", "protocol_scheme"]
    ),
    "seo.assets.v3": AgentDefinition(
        agent_id="seo.assets.v3",
        agent_name="Media & Asset Agent",
        domain="TECHNICAL_SEO",
        worker_type="extractor_worker",
        description="Checks image dimensions, alt text presence, modern formats (WebP/AVIF), lazy loading, and video metadata.",
        capabilities=["image_optimization_audit", "alt_text_coverage", "video_metadata_check"],
        allowed_models=["deterministic", "fast_slm"],
        token_budget=2000,
        risk_level="low",
        timeout_sec=15,
        required_evidence=["img_tags", "media_elements"]
    ),

    # DOMAIN 3: STRUCTURED DATA / ENTITY
    "schema.validation.v3": AgentDefinition(
        agent_id="schema.validation.v3",
        agent_name="Schema Intelligence Agent",
        domain="STRUCTURED_DATA",
        worker_type="analyst_worker",
        description="Validates JSON-LD, Microdata, RDFa, Schema.org types, required properties, and syntax errors.",
        capabilities=["jsonld_validation", "schema_property_check", "schema_syntax_audit"],
        allowed_models=["deterministic", "fast_slm"],
        token_budget=2500,
        risk_level="low",
        timeout_sec=15,
        required_evidence=["raw_schema_jsonld", "microdata_nodes"]
    ),
    "entity.graph.v3": AgentDefinition(
        agent_id="entity.graph.v3",
        agent_name="Entity Intelligence Agent",
        domain="STRUCTURED_DATA",
        worker_type="analyst_worker",
        description="Extracts Organization, Person, Product, Service, Location entities and establishes relational links.",
        capabilities=["entity_extraction", "entity_resolution", "relation_mapping"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4000,
        risk_level="medium",
        timeout_sec=20,
        required_evidence=["raw_schema_jsonld", "entity_text_spans"]
    ),
    "entity.knowledge_graph.v3": AgentDefinition(
        agent_id="entity.knowledge_graph.v3",
        agent_name="Knowledge Graph Agent",
        domain="STRUCTURED_DATA",
        worker_type="analyst_worker",
        description="Evaluates entity clarity, sameAs authority links, author identity, and external reference consistency.",
        capabilities=["knowledge_graph_readiness", "sameas_verification", "entity_disambiguation"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=3500,
        risk_level="low",
        timeout_sec=20,
        dependencies=["entity.graph.v3"],
        required_evidence=["entity_nodes", "sameas_urls"],
        forbidden_operations=["claiming_kg_inclusion_without_external_proof"]
    ),

    # DOMAIN 4: CONTENT INTELLIGENCE
    "content.depth.v3": AgentDefinition(
        agent_id="content.depth.v3",
        agent_name="Content Depth Agent",
        domain="CONTENT",
        worker_type="analyst_worker",
        description="Analyzes topical breadth, depth, missing subtopics, completeness, and content fluff vs substance.",
        capabilities=["topical_breadth", "semantic_depth", "content_completeness"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=5000,
        risk_level="medium",
        timeout_sec=25,
        required_evidence=["body_copy", "headings", "word_counts"]
    ),
    "content.eeat.v3": AgentDefinition(
        agent_id="content.eeat.v3",
        agent_name="E-E-A-T Agent",
        version="4.0.0",
        domain="CONTENT",
        worker_type="analyst_worker",
        description="Audits observable author identity, credentials, citations, editorial policies, and first-hand experience.",
        capabilities=["eeat_audit", "author_credentials_check", "experience_signal_detection"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4500,
        risk_level="medium",
        timeout_sec=20,
        required_evidence=["author_bios", "citations", "about_page", "editorial_policy", "external_ground_truth"]
    ),
    "content.quality.v3": AgentDefinition(
        agent_id="content.quality.v3",
        agent_name="Content Quality Agent",
        domain="CONTENT",
        worker_type="analyst_worker",
        description="Analyzes clarity, originality, utility, specificity, evidence backing, and repetition.",
        capabilities=["clarity_scoring", "fluff_detection", "utility_scoring"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4000,
        risk_level="medium",
        timeout_sec=20,
        required_evidence=["clean_text", "readability_metrics"]
    ),
    "content.topic_coverage.v3": AgentDefinition(
        agent_id="content.topic_coverage.v3",
        agent_name="Topic Coverage Agent",
        domain="CONTENT",
        worker_type="analyst_worker",
        description="Constructs hierarchical topic trees (Main Topic -> Subtopics) and identifies coverage gaps.",
        capabilities=["topic_tree_builder", "gap_identification", "subtopic_mapping"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4500,
        risk_level="medium",
        timeout_sec=25,
        required_evidence=["headings", "body_text"]
    ),
    "content.cannibalization.v3": AgentDefinition(
        agent_id="content.cannibalization.v3",
        agent_name="Cannibalization Agent",
        domain="CONTENT",
        worker_type="analyst_worker",
        description="Compares multi-page titles, intent keywords, and content for keyword cannibalization and conflicting canonicals.",
        capabilities=["cannibalization_detection", "intent_overlap_audit", "title_collision_check"],
        allowed_models=["fast_slm", "reasoning_model"],
        token_budget=3500,
        risk_level="low",
        timeout_sec=20,
        required_evidence=["page_manifest", "all_page_titles", "canonical_links"]
    ),

    # DOMAIN 5: GEO (GENERATIVE ENGINE OPTIMIZATION)
    "geo.extractability.v3": AgentDefinition(
        agent_id="geo.extractability.v3",
        agent_name="Answer Extractability Agent",
        domain="GEO",
        worker_type="analyst_worker",
        description="Measures direct answer clarity: definitions, bulleted lists, tables, concise summaries, and modular sections.",
        capabilities=["answer_extractability_score", "definition_finder", "table_list_density"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4500,
        risk_level="medium",
        timeout_sec=20,
        required_evidence=["dom_elements", "clean_text", "faqs"]
    ),
    "geo.information_gain.v3": AgentDefinition(
        agent_id="geo.information_gain.v3",
        agent_name="Information Gain Agent",
        domain="GEO",
        worker_type="analyst_worker",
        description="Detects original research, proprietary data, benchmarks, unique methodology, and first-party insights.",
        capabilities=["information_gain_score", "original_data_detection", "proprietary_insight_check"],
        allowed_models=["reasoning_model"],
        token_budget=5000,
        risk_level="high",
        timeout_sec=25,
        required_evidence=["clean_text", "data_tables", "stat_mentions"]
    ),
    "geo.citation_readiness.v3": AgentDefinition(
        agent_id="geo.citation_readiness.v3",
        agent_name="Citation Readiness Agent",
        domain="GEO",
        worker_type="analyst_worker",
        description="Maps claim -> evidence -> source -> attribution. Identifies easily citable claims vs unsupported assertions.",
        capabilities=["citation_readiness_score", "attributable_claims_mapping", "citation_friction"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4500,
        risk_level="medium",
        timeout_sec=25,
        dependencies=["business.semantic_strategist.v3", "entity.graph.v3", "content.quality.v3"],
        required_evidence=["claims", "clean_text"]
    ),
    "geo.structure.v3": AgentDefinition(
        agent_id="geo.structure.v3",
        agent_name="Generative Content Structure Agent",
        domain="GEO",
        worker_type="analyst_worker",
        description="Audits TL;DR blocks, answer-first framing, FAQ structures, definitions, and entity-dense snippets.",
        capabilities=["generative_structure_audit", "faq_schema_alignment", "tldr_validation"],
        allowed_models=["fast_slm", "reasoning_model"],
        token_budget=3500,
        risk_level="low",
        timeout_sec=20,
        required_evidence=["headings", "first_paragraph_texts", "faq_blocks"]
    ),

    # DOMAIN 6: AI SEARCH
    "ai_search.discoverability.v3": AgentDefinition(
        agent_id="ai_search.discoverability.v3",
        agent_name="AI Discoverability Agent",
        domain="AI_SEARCH",
        worker_type="research_worker",
        description="Generates an exhaustive synthetic prompt matrix ('Best X companies', 'X alternatives', 'X vs Y').",
        capabilities=["query_matrix_generation", "intent_simulation", "prompt_space_mapping"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4500,
        risk_level="low",
        timeout_sec=20,
        dependencies=["business.semantic_strategist.v3"],
        required_evidence=["business_profile", "offerings"]
    ),
    "ai_search.chatgpt.v3": AgentDefinition(
        agent_id="ai_search.chatgpt.v3",
        agent_name="ChatGPT Visibility Agent",
        domain="AI_SEARCH",
        worker_type="research_worker",
        description="Evaluates discoverability scenarios for ChatGPT. Strictly labels unverified runs as SIMULATION_ONLY.",
        capabilities=["chatgpt_simulation", "citation_likelihood_evaluation"],
        allowed_models=["reasoning_model"],
        token_budget=4000,
        risk_level="medium",
        timeout_sec=25,
        dependencies=["ai_search.discoverability.v3"],
        required_evidence=["query_matrix"],
        forbidden_operations=["fabricating_live_chatgpt_citations"]
    ),
    "ai_search.perplexity.v3": AgentDefinition(
        agent_id="ai_search.perplexity.v3",
        agent_name="Perplexity Visibility Agent",
        domain="AI_SEARCH",
        worker_type="research_worker",
        description="Evaluates citation eligibility for Perplexity Search. Strictly prohibits fabricated citations.",
        capabilities=["perplexity_simulation", "source_eligibility_check"],
        allowed_models=["reasoning_model"],
        token_budget=4000,
        risk_level="medium",
        timeout_sec=25,
        dependencies=["ai_search.discoverability.v3"],
        required_evidence=["query_matrix"],
        forbidden_operations=["fabricating_live_perplexity_citations"]
    ),
    "ai_search.google.v3": AgentDefinition(
        agent_id="ai_search.google.v3",
        agent_name="Google AI Search Agent",
        domain="AI_SEARCH",
        worker_type="research_worker",
        description="Audits readiness for Google AI Overviews and featured snippets. Separates OBSERVED from INFERRED.",
        capabilities=["ai_overview_readiness", "snippet_extractability"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4000,
        risk_level="medium",
        timeout_sec=20,
        dependencies=["ai_search.discoverability.v3"],
        required_evidence=["headings", "direct_answers", "query_matrix"]
    ),
    "ai_search.cross_engine.v3": AgentDefinition(
        agent_id="ai_search.cross_engine.v3",
        agent_name="Cross-Engine Search Agent",
        domain="AI_SEARCH",
        worker_type="research_worker",
        description="Compares simulated visibility across Google, ChatGPT, Perplexity, Gemini, and Claude.",
        capabilities=["cross_engine_matrix", "engine_consensus_analysis"],
        allowed_models=["reasoning_model"],
        token_budget=5000,
        risk_level="medium",
        timeout_sec=25,
        dependencies=["ai_search.chatgpt.v3", "ai_search.perplexity.v3", "ai_search.google.v3"],
        required_evidence=["engine_evaluations"]
    ),

    # DOMAIN 7: UX / CRO / TRUST
    "ux.experience.v3": AgentDefinition(
        agent_id="ux.experience.v3",
        agent_name="UX Intelligence Agent",
        domain="EXPERIENCE",
        worker_type="analyst_worker",
        description="Audits navigation hierarchy, readability, mobile ergonomics, information architecture, and interaction friction.",
        capabilities=["navigation_audit", "readability_check", "mobile_friction_detection"],
        allowed_models=["fast_slm", "deterministic"],
        token_budget=3000,
        risk_level="low",
        timeout_sec=15,
        required_evidence=["dom_elements", "nav_structure", "viewport"]
    ),
    "cro.conversion.v3": AgentDefinition(
        agent_id="cro.conversion.v3",
        agent_name="Conversion Intelligence Agent",
        domain="EXPERIENCE",
        worker_type="analyst_worker",
        description="Audits visitor-to-customer conversion paths: CTA copy, placement, form fields, and checkout friction.",
        capabilities=["cta_friction_audit", "conversion_funnel_check", "action_clarity"],
        allowed_models=["fast_slm", "reasoning_model"],
        token_budget=3500,
        risk_level="low",
        timeout_sec=15,
        required_evidence=["cta_elements", "form_fields", "hero_section"]
    ),
    "trust.authority.v3": AgentDefinition(
        agent_id="trust.authority.v3",
        agent_name="Trust Authority Agent",
        version="4.0.0",
        domain="EXPERIENCE",
        worker_type="analyst_worker",
        description="Audits testimonials, customer logos, security badges, contact info, privacy policies, and compliance proof.",
        capabilities=["trust_badge_audit", "social_proof_verification", "legal_compliance_check"],
        allowed_models=["fast_slm", "reasoning_model"],
        token_budget=3500,
        risk_level="low",
        timeout_sec=15,
        required_evidence=["footer_links", "trust_badges", "contact_info", "external_ground_truth"]
    ),

    # DOMAIN 8: VERIFICATION / INTELLIGENCE
    "verification.adversarial.v3": AgentDefinition(
        agent_id="verification.adversarial.v3",
        agent_name="Adversarial Verification Agent",
        domain="VERIFICATION",
        worker_type="critic_worker",
        description="Adversarially attempts to falsify every claim. Checks evidence presence, relevance, freshness, and over-extrapolation.",
        capabilities=["adversarial_falsification", "evidence_audit", "hallucination_purge"],
        allowed_models=["judge_model", "reasoning_model"],
        dependencies=[
            "business.icp.v3",
            "business.commercial.v3",
            "content.eeat.v3",
            "content.quality.v3",
            "trust.authority.v3",
            "seo.performance.v3",
            "geo.citation_readiness.v3",
            "ai_search.cross_engine.v3",
        ],
        required_evidence=["claims", "evidence_store", "evidence_graph"]
    ),
    "verification.contradiction.v3": AgentDefinition(
        agent_id="verification.contradiction.v3",
        agent_name="Contradiction & Causal Reasoning Agent",
        version="4.0.0",
        domain="VERIFICATION",
        worker_type="critic_worker",
        description="Detects cross-page and cross-agent contradictions (Page A says X, Page B says Y) and identifies root causes.",
        capabilities=["cross_page_arbitration", "causal_root_cause_analysis", "conflict_resolution"],
        allowed_models=["judge_model", "reasoning_model"],
        token_budget=6000,
        risk_level="high",
        timeout_sec=30,
        dependencies=[
            "verification.adversarial.v3",
            "business.icp.v3",
            "business.commercial.v3",
            "seo.performance.v3",
            "content.eeat.v3",
            "trust.authority.v3",
        ],
        required_evidence=["claims", "contradictions", "page_manifest", "external_ground_truth"],
        forbidden_operations=["picking_winner_between_dom_and_external"],
    ),
    "strategy.executive.v3": AgentDefinition(
        agent_id="strategy.executive.v3",
        agent_name="Executive Intelligence & Remediation Agent",
        domain="VERIFICATION",
        worker_type="synthesizer_worker",
        description="Consumes ONLY VERIFIED findings to build executive narrative, root-cause prioritization, and 7/30/90-day roadmaps.",
        capabilities=["executive_narrative", "roadmap_generation", "patch_plan_synthesis"],
        allowed_models=["judge_model", "reasoning_model"],
        token_budget=8000,
        risk_level="medium",
        timeout_sec=35,
        dependencies=["verification.contradiction.v3", "ai_search.cross_engine.v3"],
        required_evidence=["verified_findings", "scores"]
    )
}

# DOMAIN 9: SPECIALIZED COPYWRITING WORKFORCE (5 SPECIALISTS)
COPYWRITING_AGENTS_V3: Dict[str, AgentDefinition] = {
    "copywriting.seo.v3": AgentDefinition(
        agent_id="copywriting.seo.v3",
        agent_name="Search Intent & SERP Copywriting Specialist",
        domain="COPYWRITING",
        worker_type="analyst_worker",
        description="Crafts strict character-compliant titles (50-60 chars) and meta descriptions (140-160 chars) matching commercial search intent with zero SERP truncation.",
        capabilities=["serp_copywriting", "title_meta_optimization", "semantic_heading_alignment"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4000,
        risk_level="low",
        timeout_sec=20,
        required_evidence=["page_title", "meta_description", "h1", "h2", "primary_intent"],
    ),
    "copywriting.geo.v3": AgentDefinition(
        agent_id="copywriting.geo.v3",
        agent_name="Answer Engine & GEO Citation Copywriter",
        domain="COPYWRITING",
        worker_type="analyst_worker",
        description="Formulates extractable 40-60 word definition blocks and structured FAQ Q&As optimized for citation by ChatGPT, Perplexity, and Google AI Overviews.",
        capabilities=["geo_snippet_crafting", "faq_schema_copywriting", "extractable_definition_generation"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4500,
        risk_level="low",
        timeout_sec=20,
        required_evidence=["clean_text", "value_proposition", "offerings"],
    ),
    "copywriting.cro.v3": AgentDefinition(
        agent_id="copywriting.cro.v3",
        agent_name="Direct-Response Conversion & CRO Copywriter",
        domain="COPYWRITING",
        worker_type="analyst_worker",
        description="Audits the 3-second hook, value proposition clarity, objection handling, and crafts high-intent CTA button microcopy with active value verbs.",
        capabilities=["cro_microcopy", "hook_crafting", "cta_friction_removal"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=4000,
        risk_level="low",
        timeout_sec=20,
        required_evidence=["cta_elements", "hero_section", "target_audience"],
    ),
    "copywriting.clarity.v3": AgentDefinition(
        agent_id="copywriting.clarity.v3",
        agent_name="Brand Voice & Cognitive Clarity Copywriter",
        domain="COPYWRITING",
        worker_type="analyst_worker",
        description="Bans empty corporate buzzwords and fluff, calibrates readability to grade 7-9, and enforces sharp ICP-targeted audience callouts.",
        capabilities=["fluff_elimination", "readability_calibration", "audience_callout_crafting"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=3500,
        risk_level="low",
        timeout_sec=20,
        required_evidence=["clean_text", "readability_metrics", "brand_voice"],
    ),
    "copywriting.section.v3": AgentDefinition(
        agent_id="copywriting.section.v3",
        agent_name="Modular Section Architect & Page Copywriter",
        domain="COPYWRITING",
        worker_type="analyst_worker",
        description="Deconstructs pages into modular blocks (Hero, Problem, Solution, Features/Proof, GEO FAQ, Closing CTA) with status and complete production rewrites.",
        capabilities=["section_architecture", "full_page_modular_rewrite", "section_gap_diagnosis"],
        allowed_models=["reasoning_model", "fast_slm"],
        token_budget=5500,
        risk_level="low",
        timeout_sec=25,
        required_evidence=["page_sections", "headings", "body_text"],
    ),
}

# Backward Compatibility Alias Map
AGENT_REGISTRY: Dict[str, AgentDefinition] = {
    **SPECIALIST_AGENTS_V3,
    **COPYWRITING_AGENTS_V3,
    "copywriting_seo": COPYWRITING_AGENTS_V3["copywriting.seo.v3"],
    "copywriting_geo": COPYWRITING_AGENTS_V3["copywriting.geo.v3"],
    "copywriting_cro": COPYWRITING_AGENTS_V3["copywriting.cro.v3"],
    "copywriting_clarity": COPYWRITING_AGENTS_V3["copywriting.clarity.v3"],
    "copywriting_section": COPYWRITING_AGENTS_V3["copywriting.section.v3"],
    "discovery": SPECIALIST_AGENTS_V3["seo.crawl.v3"],
    "business": SPECIALIST_AGENTS_V3["business.discovery.v3"],
    "technical_seo": SPECIALIST_AGENTS_V3["seo.indexability.v3"],
    "content": SPECIALIST_AGENTS_V3["content.depth.v3"],
    "geo": SPECIALIST_AGENTS_V3["geo.extractability.v3"],
    "ai_search": SPECIALIST_AGENTS_V3["ai_search.discoverability.v3"],
    "ux_conversion": SPECIALIST_AGENTS_V3["ux.experience.v3"],
    "verifier": SPECIALIST_AGENTS_V3["verification.adversarial.v3"],
    "narrative": SPECIALIST_AGENTS_V3["strategy.executive.v3"]
}

# 1:1 capability → specialist agent. Every live capability routes to a real agent.
CAPABILITY_AGENT_MAP: Dict[str, str] = {
    "01_discovery": "seo.crawl.v3",
    "02_semantic_structure": "seo.html.v3",
    "03_indexability": "seo.indexability.v3",
    "04_link_architecture": "seo.internal_links.v3",
    "05_performance": "seo.performance.v3",
    "06_security": "seo.security.v3",
    "07_asset_optimization": "seo.assets.v3",
    "08_mobile_readiness": "ux.experience.v3",
    "09_schema_syntax": "schema.validation.v3",
    "10_entity_graph": "entity.graph.v3",
    "11_opengraph_metadata": "entity.knowledge_graph.v3",
    "12_positioning": "business.discovery.v3",
    "13_icp_alignment": "business.icp.v3",
    "14_value_prop_strength": "business.intent.v3",
    "15_commercial_clarity": "business.commercial.v3",
    "16_competitive_differentiation": "business.semantic_strategist.v3",
    "17_content_depth": "content.depth.v3",
    "18_eeat_authority": "content.eeat.v3",
    "19_readability": "content.quality.v3",
    "20_topic_coverage": "content.topic_coverage.v3",
    "21_cannibalization": "content.cannibalization.v3",
    "22_direct_extractability": "geo.extractability.v3",
    "23_information_gain": "geo.information_gain.v3",
    "24_summarizability": "geo.structure.v3",
    "25_citation_readiness": "geo.citation_readiness.v3",
    "26_ai_discoverability": "ai_search.discoverability.v3",
    "27_chatgpt_scenario": "ai_search.chatgpt.v3",
    "28_perplexity_scenario": "ai_search.perplexity.v3",
    "29_gemini_scenario": "ai_search.google.v3",
    "30_claude_scenario": "ai_search.cross_engine.v3",
    "31_ux_friction": "ux.experience.v3",
    "32_trust_signals": "trust.authority.v3",
    "33_conversion_cro": "cro.conversion.v3",
    "34_adversarial_verification": "verification.adversarial.v3",
    "35_contradiction_resolution": "verification.contradiction.v3",
}

DOMAIN_CATEGORY: Dict[str, str] = {
    "BUSINESS": "COMPETITIVE",
    "TECHNICAL_SEO": "TECHNICAL_SEO",
    "STRUCTURED_DATA": "SCHEMA",
    "CONTENT": "CONTENT",
    "GEO": "GEO",
    "AI_SEARCH": "AI_SEARCH",
    "EXPERIENCE": "UX_CONVERSION",
    "VERIFICATION": "CONTENT",
    "COPYWRITING": "CONTENT",
}

def get_agent_definition(agent_id: str) -> Optional[AgentDefinition]:
    """Retrieve agent definition by ID or legacy alias."""
    return AGENT_REGISTRY.get(agent_id)

def list_all_specialists() -> List[AgentDefinition]:
    """List all 35 canonical specialist agents."""
    return list(SPECIALIST_AGENTS_V3.values())

def list_copywriting_specialists() -> List[AgentDefinition]:
    """List all 5 specialized copywriting agents."""
    return list(COPYWRITING_AGENTS_V3.values())

def specialist_count() -> int:
    return len(SPECIALIST_AGENTS_V3)


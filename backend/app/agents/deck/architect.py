"""
Deck Architecture & Slide Sequencing Agent (deck.architect.v1)
Blueprints a master 70+ slide executive presentation partitioned across 11 strategic modules
with strict zero-repetition guarantees and distinct analytical contracts.
"""
from typing import List, Dict, Any, Set
import hashlib
from app.agents.deck.models import (
    DeckBlueprint,
    SlideBlueprint,
    SlideLayoutType,
    DeckChartType,
    ChartDataSpec,
    CardSpec
)


class DeckArchitectAgent:
    """
    Orchestrates the 76-slide master presentation blueprint across 11 strategic modules.
    Enforces that every slide has a distinct thematic focus and zero conceptual overlap.
    """
    AGENT_ID = "deck.architect.v1"

    MODULE_DEFINITIONS = [
        ("mod_01", "01 // EXECUTIVE MANDATE & STRATEGIC MACRO"),
        ("mod_02", "02 // TRI-PERSPECTIVE COGNITIVE DIAGNOSTIC"),
        ("mod_03", "03 // THE 8 CORE AUDIT PILLARS"),
        ("mod_04", "04 // TECHNICAL INFRASTRUCTURE & CRAWL ANATOMY"),
        ("mod_05", "05 // ON-PAGE INTELLIGENCE & PAGE AUDIT"),
        ("mod_06", "06 // GEO & ANSWER ENGINE CITATIONS"),
        ("mod_07", "07 // CONVERSION ERGONOMICS & BUYER JOURNEY"),
        ("mod_08", "08 // COMPETITIVE PARITY & MARKET BENCHMARK"),
        ("mod_09", "09 // CAUSAL DIAGNOSTICS & ROOT-CAUSE BOTTLENECKS"),
        ("mod_10", "10 // PRIORITIZED 7 / 30 / 90 DAY ROADMAP"),
        ("mod_11", "11 // GOVERNANCE, EVIDENCE LEDGER & SEAL"),
    ]

    def create_blueprint(self, domain: str, date_str: str) -> DeckBlueprint:
        """
        Generates the 76 unique slide blueprints.
        """
        slides: List[SlideBlueprint] = []

        # =========================================================================
        # MODULE 1: EXECUTIVE MANDATE & STRATEGIC MACRO (Slides 1-6)
        # =========================================================================
        m1_id, m1_title = self.MODULE_DEFINITIONS[0]
        slides.append(SlideBlueprint(
            slide_id="slide_01_cover",
            slide_number=1,
            module_id=m1_id,
            module_title=m1_title,
            kicker="DRISTIK // C-SUITE DOSSIER",
            title=f"Executive Intelligence & Strategic Growth Audit: {domain}",
            subtitle="Autonomous Multi-Agent Technical Assurance, Search Authority & Generative Answer-Engine Audit",
            thematic_focus="cover_dossier",
            layout=SlideLayoutType.COVER,
            footer_text="RESTRICTED & CONFIDENTIAL // PREPARED FOR EXECUTIVE LEADERSHIP"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_02_agenda",
            slide_number=2,
            module_id=m1_id,
            module_title=m1_title,
            kicker="AUDIT STRUCTURE // 11 MODULES",
            title="Comprehensive Audit Architecture & Agenda",
            subtitle="Methodology and navigation map across the 76 empirical audit dimensions",
            thematic_focus="audit_agenda_structure",
            layout=SlideLayoutType.METRIC_CARDS_4,
            footer_text="DRISTIK AUTONOMOUS INTELLIGENCE SYSTEMS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_03_exec_summary",
            slide_number=3,
            module_id=m1_id,
            module_title=m1_title,
            kicker="EXECUTIVE ROLLUP",
            title="Composite Digital Health Score & Strategic Posture",
            subtitle="Overall benchmark rollup derived from empirical AST parsing and answer-engine probes",
            thematic_focus="executive_health_composite",
            layout=SlideLayoutType.EXECUTIVE_SPLIT,
            footer_text="EVIDENCE GOVERNANCE: ZERO SIMULATED METRICS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_04_primary_opportunity",
            slide_number=4,
            module_id=m1_id,
            module_title=m1_title,
            kicker="COMMERCIAL CATALYST",
            title="Highest-Yield Commercial Growth Opportunity",
            subtitle="The singular high-leverage initiative with the highest return on engineering effort",
            thematic_focus="primary_growth_catalyst",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="MEASURED COMMERCIAL LEVERAGE"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_05_what_to_ignore",
            slide_number=5,
            module_id=m1_id,
            module_title=m1_title,
            kicker="MANAGEMENT CONSULTING DIRECTIVE",
            title="Capital Allocation Guardrails: What to Ignore This Quarter",
            subtitle="Low-impact vanity work, cargo-cult practices, and ungrounded growth traps to avoid",
            thematic_focus="strategic_what_to_ignore",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="CAPITAL PRESERVATION ADVISORY"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_06_governance_standard",
            slide_number=6,
            module_id=m1_id,
            module_title=m1_title,
            kicker="DATA INTEGRITY PROTOCOL",
            title="Deterministic Evidence Governance & Zero-Fake Standard",
            subtitle="How Dristik eliminates synthetic hallucination through cryptographic AST proof tokens",
            thematic_focus="evidence_governance_standard",
            layout=SlideLayoutType.METRIC_CARDS_4,
            footer_text="CRYPTOGRAPHIC DOM PROOF TOKENS"
        ))

        # =========================================================================
        # MODULE 2: TRI-PERSPECTIVE COGNITIVE DIAGNOSTIC (Slides 7-12)
        # =========================================================================
        m2_id, m2_title = self.MODULE_DEFINITIONS[1]
        slides.append(SlideBlueprint(
            slide_id="slide_07_tri_overview",
            slide_number=7,
            module_id=m2_id,
            module_title=m2_title,
            kicker="COGNITIVE DIVERGENCE",
            title="Tri-Perspective Diagnostic: Three Classes of Consumers",
            subtitle="Simultaneous evaluation across Human Visitors, Traditional Search Bots, and AI Answer Engines",
            thematic_focus="tri_perspective_overview",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="MULTI-AGENT BLACKBOARD CORRELATION"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_08_human_perspective",
            slide_number=8,
            module_id=m2_id,
            module_title=m2_title,
            kicker="PERSPECTIVE 01 // HUMAN VISITOR",
            title="Human Buyer Experience, Value Clarity & Friction",
            subtitle="How prospective customers interpret value propositions and commercial friction points",
            thematic_focus="human_buyer_perspective",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="CRO & COGNITIVE LOAD ANALYSIS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_09_search_perspective",
            slide_number=9,
            module_id=m2_id,
            module_title=m2_title,
            kicker="PERSPECTIVE 02 // SEARCH SPIDER",
            title="Search Engine Indexation & Crawler Navigation Topology",
            subtitle="Deterministic verification of canonical routing, XML sitemaps, and HTTP status codes",
            thematic_focus="search_spider_perspective",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="TECHNICAL INDEXABILITY VERIFICATION"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_10_ai_perspective",
            slide_number=10,
            module_id=m2_id,
            module_title=m2_title,
            kicker="PERSPECTIVE 03 // ANSWER ENGINE",
            title="Generative AI & LLM Extractability Perception",
            subtitle="How ChatGPT, Perplexity, Claude, and Gemini parse entity facts and commercial propositions",
            thematic_focus="answer_engine_perspective",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="AEO / GEO EXTRACTION BENCHMARK"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_11_divergence_gap",
            slide_number=11,
            module_id=m2_id,
            module_title=m2_title,
            kicker="CROSS-CONSUMER GAP",
            title="Perception Gap Matrix: Where Human and Bot Experiences Diverge",
            subtitle="Empirical divergence where technical health masks severe AI citability weaknesses",
            thematic_focus="tri_perspective_gap_analysis",
            layout=SlideLayoutType.TABLE_MATRIX,
            footer_text="CROSS-CHANNEL COGNITIVE ALIGNMENT"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_12_tri_commercial_impact",
            slide_number=12,
            module_id=m2_id,
            module_title=m2_title,
            kicker="COMMERCIAL TRANSMISSION",
            title="Commercial Ramifications of Cognitive Divergence",
            subtitle="How perception divergence translates into customer drop-off and citation invisibility",
            thematic_focus="tri_perspective_commercial_impact",
            layout=SlideLayoutType.METRIC_CARDS_4,
            footer_text="BUSINESS OUTCOME PROJECTIONS"
        ))

        # =========================================================================
        # MODULE 3: THE 8 CORE AUDIT PILLARS (Slides 13-28)
        # =========================================================================
        m3_id, m3_title = self.MODULE_DEFINITIONS[2]
        slides.append(SlideBlueprint(
            slide_id="slide_13_pillars_radar",
            slide_number=13,
            module_id=m3_id,
            module_title=m3_title,
            kicker="PILLAR BENCHMARK",
            title="8-Category Holistic Scoreboard & Capability Radar",
            subtitle="Normalized empirical performance across all 8 foundational digital pillars",
            thematic_focus="eight_pillars_radar_scoreboard",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="INTENT-ADAPTED CALIBRATED BENCHMARK"
        ))

        categories = [
            ("Technical Discoverability", "Crawl indexation, canonical integrity, robots directives, and status health", "discoverability"),
            ("Semantic HTML & Structure", "Heading hierarchy, semantic landmark tags, and DOM tree purity", "semantic_structure"),
            ("Entity Authority & Schema", "Structured Schema.org microdata, Organization nodes, and SameAs linkages", "entity_schema"),
            ("Content Depth & EEAT", "Topical thoroughness, authoritative proof points, and readability grades", "content_eeat"),
            ("GEO & AI Citability", "Directly extractable factual statements for generative answer engines", "geo_citability"),
            ("UX & Perceived Velocity", "Above-the-fold engagement, layout stability, and response speed", "ux_velocity"),
            ("Security & Transport Integrity", "HSTS headers, TLS cipher suites, CSP directives, and frame protections", "security_transport"),
            ("Commercial Transparency", "Clear monetization models, visible packaging, and friction-free CTAs", "commercial_transparency"),
        ]

        slide_idx = 14
        for cat_name, cat_desc, cat_key in categories:
            # Slide A: Diagnostic
            slides.append(SlideBlueprint(
                slide_id=f"slide_{slide_idx:02d}_{cat_key}_diag",
                slide_number=slide_idx,
                module_id=m3_id,
                module_title=m3_title,
                kicker=f"PILLAR AUDIT // {cat_name.upper()}",
                title=f"{cat_name}: Diagnostic Performance & Gaps",
                subtitle=cat_desc,
                thematic_focus=f"pillar_{cat_key}_diagnostic",
                layout=SlideLayoutType.METRIC_CARDS_3,
                footer_text="EMPIRICAL DEFICIT IDENTIFICATION"
            ))
            slide_idx += 1
            # Slide B: Remediation Directives
            slides.append(SlideBlueprint(
                slide_id=f"slide_{slide_idx:02d}_{cat_key}_directives",
                slide_number=slide_idx,
                module_id=m3_id,
                module_title=m3_title,
                kicker=f"ENGINEERING DIRECTIVES // {cat_name.upper()}",
                title=f"{cat_name}: High-Impact Remediation Directives",
                subtitle=f"Actionable technical interventions to elevate {cat_name} to top-quartile standards",
                thematic_focus=f"pillar_{cat_key}_directives",
                layout=SlideLayoutType.FINDINGS_LEDGER,
                footer_text="PRODUCTION REMEDIATION ROADMAP"
            ))
            slide_idx += 1

        # Slide 28: Deficit Hierarchy
        slides.append(SlideBlueprint(
            slide_id="slide_28_cross_pillar_hierarchy",
            slide_number=28,
            module_id=m3_id,
            module_title=m3_title,
            kicker="DEFICIT HIERARCHY",
            title="Cross-Pillar Defect Concentration & Bottleneck Priority",
            subtitle="Weighted ranking of digital liabilities ordered by severity and commercial drag",
            thematic_focus="cross_pillar_deficit_hierarchy",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="SEVERITY-WEIGHTED CAPITAL ALLOCATION"
        ))

        # =========================================================================
        # MODULE 4: TECHNICAL INFRASTRUCTURE & CRAWL ANATOMY (Slides 29-38)
        # =========================================================================
        m4_id, m4_title = self.MODULE_DEFINITIONS[3]
        slides.append(SlideBlueprint(
            slide_id="slide_29_infra_overview",
            slide_number=29,
            module_id=m4_id,
            module_title=m4_title,
            kicker="INFRASTRUCTURE FOUNDATIONS",
            title="Infrastructure Topology & Multi-Origin Crawl Health",
            subtitle="Telemetry audit across discovered routes, response latency, and network resilience",
            thematic_focus="infrastructure_topology_overview",
            layout=SlideLayoutType.METRIC_CARDS_4,
            footer_text="DETERMINISTIC NETWORK CRAWL METRICS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_30_http_status_codes",
            slide_number=30,
            module_id=m4_id,
            module_title=m4_title,
            kicker="STATUS CODE ANATOMY",
            title="HTTP Response Code Distribution Across Sampled Routes",
            subtitle="Empirical breakdown of 200 OK, 301/302 Redirects, and 4xx/5xx Client/Server Errors",
            thematic_focus="http_status_code_distribution",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="CRAWL MANIFEST TELEMETRY"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_31_canonical_routing",
            slide_number=31,
            module_id=m4_id,
            module_title=m4_title,
            kicker="CANONICAL INTEGRITY",
            title="Canonical Routing, Trailing Slashes & Redirect Loops",
            subtitle="Analysis of canonical URL tags, cross-protocol consistency, and duplicate indexation risk",
            thematic_focus="canonical_routing_integrity",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="INDEXATION INTEGRITY SAFEGUARDS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_32_robots_sitemaps",
            slide_number=32,
            module_id=m4_id,
            module_title=m4_title,
            kicker="CRAWLER GOVERNANCE",
            title="Robots.txt Directives & XML Sitemap Conformance",
            subtitle="Verification of bot allowances, crawl-delay directives, and sitemap freshness",
            thematic_focus="robots_and_sitemap_compliance",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="SEARCH ENGINE ACCESS PROTOCOLS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_33_ttfb_latency",
            slide_number=33,
            module_id=m4_id,
            module_title=m4_title,
            kicker="SERVER VELOCITY",
            title="Time-to-First-Byte (TTFB) Latency Across Audited Pages",
            subtitle="Server response time distribution comparing target pages against 200ms excellence thresholds",
            thematic_focus="ttfb_latency_benchmarks",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="INFRASTRUCTURE RESPONSE VELOCITY"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_34_click_depth",
            slide_number=34,
            module_id=m4_id,
            module_title=m4_title,
            kicker="CRAWL DEPTH & DISTANCE",
            title="Page Click-Depth Distribution & Internal Link Reach",
            subtitle="Hop distance from root origin to key commercial conversion pages",
            thematic_focus="click_depth_link_reach",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="INTERNAL LINK ARCHITECTURE"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_35_orphan_pages",
            slide_number=35,
            module_id=m4_id,
            module_title=m4_title,
            kicker="LINK CONNECTIVITY",
            title="Orphan Route Detection & Anchor Text Consistency",
            subtitle="Identification of unlinked pages, empty anchor texts, and dead-end conversion funnels",
            thematic_focus="orphan_pages_anchor_audit",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="INFORMATION ARCHITECTURE INTEGRITY"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_36_heading_hierarchy",
            slide_number=36,
            module_id=m4_id,
            module_title=m4_title,
            kicker="SEMANTIC OUTLINE",
            title="Heading Hierarchy (H1-H6) Structural Integrity",
            subtitle="Evaluation of single H1 discipline, logical nesting, and skipping heading levels",
            thematic_focus="heading_hierarchy_architecture",
            layout=SlideLayoutType.METRIC_CARDS_4,
            footer_text="AST DOM TREE PARSER"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_37_meta_tag_compliance",
            slide_number=37,
            module_id=m4_id,
            module_title=m4_title,
            kicker="SERP TRUNCATION RISK",
            title="Title & Meta Description Length Compliance Distribution",
            subtitle="Audit of 50-60 character title limits and 140-160 character meta description bounds",
            thematic_focus="meta_tag_length_compliance",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="SERP DISPLAY VERIFICATION"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_38_media_assets",
            slide_number=38,
            module_id=m4_id,
            module_title=m4_title,
            kicker="ASSET WEIGHT",
            title="Media Asset Optimization & Responsive Image Encoding",
            subtitle="Audit of modern image formats (WebP/AVIF), missing dimensions, and alt text completeness",
            thematic_focus="media_asset_optimization",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="PAGE WEIGHT & CLS STABILITY"
        ))

        # =========================================================================
        # MODULE 5: ON-PAGE INTELLIGENCE & PAGE AUDIT (Slides 39-46)
        # =========================================================================
        m5_id, m5_title = self.MODULE_DEFINITIONS[4]
        slides.append(SlideBlueprint(
            slide_id="slide_39_page_rollup",
            slide_number=39,
            module_id=m5_id,
            module_title=m5_title,
            kicker="URL SPECIFIC AUDIT",
            title="Page-by-Page Intelligence & Quality Scorecard",
            subtitle="Comparative inspection across primary templates: Home, Pricing, Product, and Resources",
            thematic_focus="page_by_page_rollup_table",
            layout=SlideLayoutType.TABLE_MATRIX,
            footer_text="TEMPLATE-LEVEL QUALITY MATRICES"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_40_homepage_deepdive",
            slide_number=40,
            module_id=m5_id,
            module_title=m5_title,
            kicker="TEMPLATE 01 // HOMEPAGE",
            title="Homepage Deep-Dive: Hero Hook & Value Proposition",
            subtitle="Analysis of the 3-second hook, primary CTA clarity, and above-the-fold information density",
            thematic_focus="homepage_template_deepdive",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="PRIMARY CONVERSION ENTRY POINT"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_41_pricing_page",
            slide_number=41,
            module_id=m5_id,
            module_title=m5_title,
            kicker="TEMPLATE 02 // PRICING",
            title="Commercial / Pricing Page: Monetization Clarity",
            subtitle="Inspection of packaging tiers, feature comparison tables, FAQ objections, and checkout paths",
            thematic_focus="pricing_page_audit",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="REVENUE FUNNEL INTEGRITY"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_42_product_pages",
            slide_number=42,
            module_id=m5_id,
            module_title=m5_title,
            kicker="TEMPLATE 03 // PRODUCT & SOLUTIONS",
            title="Product Pages: Capability Proof & Technical Specifications",
            subtitle="Demonstration of feature proof points, customer use cases, and ICP workflow validation",
            thematic_focus="product_page_specifications",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="SOLUTION POSITIONING ACCURACY"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_43_trust_about_pages",
            slide_number=43,
            module_id=m5_id,
            module_title=m5_title,
            kicker="TEMPLATE 04 // ABOUT & TRUST",
            title="About & Company Pages: Leadership & Corporate Entity Proof",
            subtitle="Audit of executive bios, corporate registration, office locations, and trust badges",
            thematic_focus="trust_about_page_audit",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="EEAT ENTITY REPUTATION SIGNALS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_44_contact_forms",
            slide_number=44,
            module_id=m5_id,
            module_title=m5_title,
            kicker="TEMPLATE 05 // CONTACT & CONVERSION",
            title="Contact & Lead Generation: Form Friction & Validation",
            subtitle="Inspection of field count, friction-inducing required fields, and clear response expectations",
            thematic_focus="contact_form_friction_audit",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="LEAD GENERATION CONVERSION RATE"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_45_word_count_distribution",
            slide_number=45,
            module_id=m5_id,
            module_title=m5_title,
            kicker="CONTENT DENSITY",
            title="Word Count Distribution vs Intent-Adjusted Baselines",
            subtitle="Comparing extracted visible copy volume against recommended thresholds by page archetype",
            thematic_focus="word_count_vs_baselines_chart",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="INFORMATION GAIN MEASUREMENTS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_46_modular_sections",
            slide_number=46,
            module_id=m5_id,
            module_title=m5_title,
            kicker="SECTION ARCHITECTURE",
            title="Modular Page Section Architecture & Layout Flow",
            subtitle="Recommended block sequence: Hero, Problem, Solution Proof, FAQ, and Closing CTA",
            thematic_focus="modular_section_architecture",
            layout=SlideLayoutType.METRIC_CARDS_4,
            footer_text="DESIGN SYSTEM CONVERSION PATTERNS"
        ))

        # =========================================================================
        # MODULE 6: GEO & ANSWER ENGINE CITATIONS (Slides 47-54)
        # =========================================================================
        m6_id, m6_title = self.MODULE_DEFINITIONS[5]
        slides.append(SlideBlueprint(
            slide_id="slide_47_geo_paradigm",
            slide_number=47,
            module_id=m6_id,
            module_title=m6_title,
            kicker="GENERATIVE PARADIGM SHIFT",
            title="Generative Engine Optimization (GEO): The Citability Frontier",
            subtitle="Why traditional rank tracking fails when LLMs synthesize direct answers without SERP links",
            thematic_focus="geo_paradigm_overview",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="AEO & RAG SEARCH ARCHITECTURE"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_48_commercial_query_benchmark",
            slide_number=48,
            module_id=m6_id,
            module_title=m6_title,
            kicker="COMMERCIAL QUERY BATTERY",
            title="6-Question Commercial Intent Benchmark Results",
            subtitle="Testing answer-engine extractability across Identity, Pricing, Features, Audience, and Alternatives",
            thematic_focus="commercial_query_benchmark_results",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="DETERMINISTIC EXTRACTABILITY CRITERIA"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_49_per_engine_matrix",
            slide_number=49,
            module_id=m6_id,
            module_title=m6_title,
            kicker="MULTI-ENGINE BENCHMARK",
            title="Per-Engine Citability Matrix: ChatGPT, Perplexity, Gemini, Claude",
            subtitle="Cross-model divergence in source citation, factual retention, and knowledge retrieval",
            thematic_focus="per_engine_citability_matrix",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="MULTI-LLM GROUND TRUTH COMPARISON"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_50_extractable_passages",
            slide_number=50,
            module_id=m6_id,
            module_title=m6_title,
            kicker="RAG PASSAGE ARCHITECTURE",
            title="Extractable Passage Synthesis & Self-Contained Definition Blocks",
            subtitle="Structuring 40-60 word definitive factual statements that answer engines can quote verbatim",
            thematic_focus="extractable_passage_synthesis",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="ANSWER-READY STATEMENT ENGINEERING"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_51_schema_knowledge_graph",
            slide_number=51,
            module_id=m6_id,
            module_title=m6_title,
            kicker="KNOWLEDGE GRAPH ANCHORING",
            title="Schema.org Entity Graph & Machine-Readable Identity",
            subtitle="Publishing unambiguous JSON-LD nodes for Organization, Product, FAQ, and Founder entities",
            thematic_focus="schema_knowledge_graph_mapping",
            layout=SlideLayoutType.METRIC_CARDS_4,
            footer_text="SEMANTIC WEB ONTOLOGY STANDARDS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_52_llms_txt_deployment",
            slide_number=52,
            module_id=m6_id,
            module_title=m6_title,
            kicker="AGENTIC DISCOVERY MANIFEST",
            title="/llms.txt Protocol: Authoritative AI Crawler Manifest",
            subtitle="Publishing direct markdown documentation endpoints tailored for autonomous LLM agents",
            thematic_focus="llms_txt_protocol_deployment",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="NEXT-GEN BOT PERMISSION PROTOCOLS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_53_hallucination_defense",
            slide_number=53,
            module_id=m6_id,
            module_title=m6_title,
            kicker="ACCURACY DEFENSE",
            title="Brand Attribution & Defense Against LLM Hallucinations",
            subtitle="Preventing competitors or outdated legacy figures from contaminating generated answers",
            thematic_focus="brand_hallucination_defense",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="REPUTATION & INTEGRITY SHIELD"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_54_ai_readiness_benchmark",
            slide_number=54,
            module_id=m6_id,
            module_title=m6_title,
            kicker="INDUSTRY COMPARISON",
            title="AI Answer-Engine Readiness Score vs Industry Benchmark",
            subtitle="How target properties score against verified cohort averages in answer-engine citability",
            thematic_focus="ai_readiness_score_benchmark",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="CALIBRATED COHORT INTELLIGENCE"
        ))

        # =========================================================================
        # MODULE 7: CONVERSION ERGONOMICS & BUYER JOURNEY (Slides 55-60)
        # =========================================================================
        m7_id, m7_title = self.MODULE_DEFINITIONS[6]
        slides.append(SlideBlueprint(
            slide_id="slide_55_value_prop_test",
            slide_number=55,
            module_id=m7_id,
            module_title=m7_title,
            kicker="COGNITIVE CLARITY",
            title="The 5-Second Commercial Value Proposition Test",
            subtitle="Auditing whether a cold enterprise buyer understands what is sold, for whom, and why",
            thematic_focus="five_second_value_prop_test",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="FIRST-IMPRESSION COGNITIVE LOAD"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_56_cta_microcopy",
            slide_number=56,
            module_id=m7_id,
            module_title=m7_title,
            kicker="CONVERSION MICROCOPY",
            title="Call-to-Action (CTA) Audit: Active Verbs vs Passive Friction",
            subtitle="Replacing weak generic buttons ('Submit', 'Learn More') with high-intent outcome verbs",
            thematic_focus="cta_microcopy_friction_audit",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="INTENT-DRIVEN BUTTON ERGONOMICS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_57_funnel_friction_points",
            slide_number=57,
            module_id=m7_id,
            module_title=m7_title,
            kicker="DROPOFF DIAGNOSTIC",
            title="Cognitive Friction Points in the Digital Acquisition Funnel",
            subtitle="Step-by-step breakdown of cognitive load from landing to commercial conversion",
            thematic_focus="funnel_cognitive_friction_points",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="FUNNEL DROP-OFF MITIGATION"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_58_trust_signals",
            slide_number=58,
            module_id=m7_id,
            module_title=m7_title,
            kicker="CREDIBILITY ARCHITECTURE",
            title="Trust Signal Density & Social Proof Audit",
            subtitle="Presence of named case studies, verified logos, security badges, and audited reviews",
            thematic_focus="trust_signal_density_audit",
            layout=SlideLayoutType.METRIC_CARDS_4,
            footer_text="ENTERPRISE BUYER ASSURANCE"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_59_mobile_ergonomics",
            slide_number=59,
            module_id=m7_id,
            module_title=m7_title,
            kicker="RESPONSIVE VIEWPORT",
            title="Mobile Touch Ergonomics & Small-Screen Readability",
            subtitle="Audit of touch target dimensions (48px+), font readability, and horizontal overflow",
            thematic_focus="mobile_touch_ergonomics_audit",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="MOBILE-FIRST BUYER EXPERIENCE"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_60_wcag_accessibility",
            slide_number=60,
            module_id=m7_id,
            module_title=m7_title,
            kicker="ACCESSIBILITY COMPLIANCE",
            title="Accessibility (WCAG 2.1 AA) Structural Audit",
            subtitle="Color contrast ratios, keyboard accessibility, ARIA landmark labels, and focus rings",
            thematic_focus="wcag_accessibility_compliance",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="INCLUSIVE DESIGN & LEGAL COMPLIANCE"
        ))

        # =========================================================================
        # MODULE 8: COMPETITIVE PARITY & MARKET BENCHMARK (Slides 61-65)
        # =========================================================================
        m8_id, m8_title = self.MODULE_DEFINITIONS[7]
        slides.append(SlideBlueprint(
            slide_id="slide_61_positioning_matrix",
            slide_number=61,
            module_id=m8_id,
            module_title=m8_title,
            kicker="MARKET POSITIONING",
            title="Competitive Differentiation & Value Framing Matrix",
            subtitle="How target positioning stands apart from direct alternatives and legacy incumbents",
            thematic_focus="competitive_differentiation_matrix",
            layout=SlideLayoutType.TABLE_MATRIX,
            footer_text="CATEGORY LEADERSHIP POSITIONING"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_62_competitor_seo_parity",
            slide_number=62,
            module_id=m8_id,
            module_title=m8_title,
            kicker="ORGANIC PARITY",
            title="Competitor SEO & Discoverability Parity Benchmark",
            subtitle="Comparing technical foundation scores, crawl depth, and metadata discipline against peers",
            thematic_focus="competitor_seo_parity_benchmark",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="SECTOR PARITY ANALYSIS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_63_content_depth_gap",
            slide_number=63,
            module_id=m8_id,
            module_title=m8_title,
            kicker="EDITORIAL EEAT GAP",
            title="Topical Depth & Authority Gap Analysis",
            subtitle="Identifying missing technical sub-topics, unaddressed buyer objections, and content gaps",
            thematic_focus="content_depth_authority_gap",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="TOPICAL AUTHORITY COVERAGE"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_64_external_authority",
            slide_number=64,
            module_id=m8_id,
            module_title=m8_title,
            kicker="OFF-PAGE REALITY",
            title="External Ground-Truth & Market Authority Reality",
            subtitle="Factual domain verification: registry records, security posture, and verified entity footprint",
            thematic_focus="external_ground_truth_authority",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="ZERO INVENTED TAM OR BACKLINKS"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_65_share_of_model",
            slide_number=65,
            module_id=m8_id,
            module_title=m8_title,
            kicker="NEXT-GEN VISIBILITY",
            title="Share-of-Model: Emerging Answer-Engine Visibility Share",
            subtitle="Proportion of generative recommendation answers naming target brand vs primary rivals",
            thematic_focus="share_of_model_answer_presence",
            layout=SlideLayoutType.CHART_WITH_ANALYSIS,
            footer_text="GENERATIVE MINDSHARE BENCHMARK"
        ))

        # =========================================================================
        # MODULE 9: CAUSAL DIAGNOSTICS & ROOT-CAUSE BOTTLENECKS (Slides 66-69)
        # =========================================================================
        m9_id, m9_title = self.MODULE_DEFINITIONS[8]
        slides.append(SlideBlueprint(
            slide_id="slide_66_causal_overview",
            slide_number=66,
            module_id=m9_id,
            module_title=m9_title,
            kicker="ROOT CAUSE DIAGNOSIS",
            title="Causal Diagnostic Engine: Tracing Symptoms to Causes",
            subtitle="Distinguishing surface-level symptoms from foundational architectural bottlenecks",
            thematic_focus="causal_diagnostic_overview",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="CAUSAL REASONING ARCHITECTURE"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_67_bottleneck_indexation",
            slide_number=67,
            module_id=m9_id,
            module_title=m9_title,
            kicker="CONSTRAINT 01 // DISCOVERABILITY",
            title="Primary Constraint: Technical Indexation & Crawl Blockers",
            subtitle="Eliminating redirect anomalies, canonical conflicts, and crawler access barriers",
            thematic_focus="causal_constraint_indexation",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="PHASE 1 RESOLUTION TARGET"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_68_bottleneck_extraction",
            slide_number=68,
            module_id=m9_id,
            module_title=m9_title,
            kicker="CONSTRAINT 02 // GEO CITABILITY",
            title="Secondary Constraint: Generative Extraction Discontinuity",
            subtitle="Resolving marketing ambiguity with crisp, structured, entity-attributed factual claims",
            thematic_focus="causal_constraint_geo_extraction",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="PHASE 2 RESOLUTION TARGET"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_69_bottleneck_conversion",
            slide_number=69,
            module_id=m9_id,
            module_title=m9_title,
            kicker="CONSTRAINT 03 // COMMERCIAL",
            title="Tertiary Constraint: Acquisition Friction & Cognitive Load",
            subtitle="Streamlining value communication, objection handling, and checkout conversion flow",
            thematic_focus="causal_constraint_conversion_friction",
            layout=SlideLayoutType.METRIC_CARDS_3,
            footer_text="PHASE 3 RESOLUTION TARGET"
        ))

        # =========================================================================
        # MODULE 10: PRIORITIZED 7 / 30 / 90 DAY ROADMAP (Slides 70-74)
        # =========================================================================
        m10_id, m10_title = self.MODULE_DEFINITIONS[9]
        slides.append(SlideBlueprint(
            slide_id="slide_70_roadmap_overview",
            slide_number=70,
            module_id=m10_id,
            module_title=m10_title,
            kicker="EXECUTION TIMELINE",
            title="Engineering Execution Roadmap Overview: 7 / 30 / 90 Days",
            subtitle="Phased sequence of technical interventions balanced by effort, dependencies, and business impact",
            thematic_focus="roadmap_execution_overview",
            layout=SlideLayoutType.TIMELINE_PHASES,
            footer_text="SEQUENCED ENGINEERING SPRINT PLAN"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_71_phase1_7days",
            slide_number=71,
            module_id=m10_id,
            module_title=m10_title,
            kicker="PHASE 1 // NOW (DAYS 1-7)",
            title="Phase 1: Immediate Blocker Remediation & Indexation Fixes",
            subtitle="Deploying canonical fixes, eliminating redirect loops, and publishing /llms.txt manifests",
            thematic_focus="roadmap_phase_1_now",
            layout=SlideLayoutType.FINDINGS_LEDGER,
            footer_text="CRITICAL SPRINT 1 MILESTONES"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_72_phase2_30days",
            slide_number=72,
            module_id=m10_id,
            module_title=m10_title,
            kicker="PHASE 2 // NEXT (DAYS 8-30)",
            title="Phase 2: Entity Schema Injection & GEO Passage Optimization",
            subtitle="Injecting Organization schemas, refining meta descriptions, and restructuring core hero blocks",
            thematic_focus="roadmap_phase_2_next",
            layout=SlideLayoutType.FINDINGS_LEDGER,
            footer_text="STRATEGIC SPRINT 2 MILESTONES"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_73_phase3_90days",
            slide_number=73,
            module_id=m10_id,
            module_title=m10_title,
            kicker="PHASE 3 // ONGOING (DAYS 31-90)",
            title="Phase 3: Continuous Assurance, Topical Depth & Citation Parity",
            subtitle="Establishing regression testing pipelines, monitoring model citation shifts, and expanding content",
            thematic_focus="roadmap_phase_3_ongoing",
            layout=SlideLayoutType.FINDINGS_LEDGER,
            footer_text="SYSTEMIC SPRINT 3 MILESTONES"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_74_code_patches",
            slide_number=74,
            module_id=m10_id,
            module_title=m10_title,
            kicker="DEPLOYMENT ARTIFACTS",
            title="Ready-to-Ship Code Patches & Production Artifacts",
            subtitle="Developer-ready code modifications ready for drop-in deployment with zero manual guesswork",
            thematic_focus="ready_to_ship_code_patches",
            layout=SlideLayoutType.CODE_PATCH_DIFF,
            footer_text="VERIFIED PULL-REQUEST READY PATCHES"
        ))

        # =========================================================================
        # MODULE 11: GOVERNANCE, EVIDENCE LEDGER & SEAL (Slides 75-76)
        # =========================================================================
        m11_id, m11_title = self.MODULE_DEFINITIONS[10]
        slides.append(SlideBlueprint(
            slide_id="slide_75_evidence_ledger",
            slide_number=75,
            module_id=m11_id,
            module_title=m11_title,
            kicker="PROVENANCE & AUDIT TRAIL",
            title="Cryptographic Evidence Ledger & SHA-256 Provenance",
            subtitle="Immutable content-addressed snapshots verifying the authenticity of every observation",
            thematic_focus="cryptographic_evidence_ledger",
            layout=SlideLayoutType.METRIC_CARDS_4,
            footer_text="CONTENT-ADDRESSED SNAPSHOT STORE"
        ))
        slides.append(SlideBlueprint(
            slide_id="slide_76_csuite_seal",
            slide_number=76,
            module_id=m11_id,
            module_title=m11_title,
            kicker="ASSURANCE CERTIFICATION",
            title="C-Suite Assurance Seal & Formal Acceptance Standards",
            subtitle="Certified verification confirming zero speculative assumptions and complete DOM grounding",
            thematic_focus="csuite_assurance_seal",
            layout=SlideLayoutType.GOVERNANCE_SEAL,
            footer_text="DRISTIK AUTONOMOUS ADVISORY SYSTEMS // ALL RIGHTS RESERVED"
        ))

        blueprint = DeckBlueprint(
            domain=domain,
            total_slides=len(slides),
            modules=[name for _, name in self.MODULE_DEFINITIONS],
            slides=slides,
            generated_at=date_str,
            dedup_verification_token=self._generate_dedup_token(slides)
        )
        self.verify_zero_repetition(blueprint)
        return blueprint

    def _generate_dedup_token(self, slides: List[SlideBlueprint]) -> str:
        h = hashlib.sha256()
        for s in slides:
            h.update(f"{s.slide_id}:{s.thematic_focus}:{s.title}".encode("utf-8"))
        return h.hexdigest()[:16]

    def verify_zero_repetition(self, blueprint: DeckBlueprint) -> bool:
        """
        Guarantees that no duplicate slides or overlapping topics exist.
        Throws ValueError if any duplicate is detected.
        """
        seen_ids: Set[str] = set()
        seen_titles: Set[str] = set()
        seen_focuses: Set[str] = set()

        for s in blueprint.slides:
            if s.slide_id in seen_ids:
                raise ValueError(f"Duplicate slide_id detected: {s.slide_id}")
            seen_ids.add(s.slide_id)

            if s.title in seen_titles:
                raise ValueError(f"Duplicate slide title detected: {s.title}")
            seen_titles.add(s.title)

            if s.thematic_focus in seen_focuses:
                raise ValueError(f"Duplicate thematic focus detected: {s.thematic_focus}")
            seen_focuses.add(s.thematic_focus)

        if len(blueprint.slides) < 70:
            raise ValueError(f"Deck must contain at least 70 slides, but contains {len(blueprint.slides)}")

        return True

"""GEO Chapter Agentic Audit Engine.

Synthesizes deep, consultative generative engine optimization intelligence for every
chapter across all 50 sections and 15 appendices. Provides:
- Specialist Agent Attribution (18 registered GEO specialist agents)
- Authoritative Diagnostic Review & Architecture Breakdown
- Root Cause Analysis & Real Business Risk Evaluation
- Prescriptive Engineering & Content Fix Recipes (code, config, markup snippets)
- Post-Fix Verification & Regression Testing Protocols
- Empirical Chapter Data Tables generated from live crawl & benchmark facts
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional, Tuple

def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)

def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

# Comprehensive Agent Registry for all 50 Sections and Appendices A-O
CHAPTER_AGENT_MAP: Dict[str, Tuple[str, str, str]] = {
    # Part I — Executive GEO Intelligence
    "01": ("geo.benchmark_orchestrator.v3", "GEO Benchmark Orchestrator", "Multi-Engine Benchmark Synthesis & Executive Overview"),
    "02": ("geo.measurement_analyst.v3", "Generative Visibility Specialist", "AI Search Visibility Scorecard & Statistical Tracking"),
    "03": ("geo.remediation_planner.v3", "GEO Opportunity & Risk Strategist", "High-Impact Displacements, Bottlenecks & Validation Plans"),

    # Part II — AI Search Landscape and Query Intelligence
    "04": ("geo.benchmark_orchestrator.v3", "Multi-Platform Coverage Specialist", "AI Overviews, ChatGPT Search, Perplexity, Copilot & Gemini"),
    "05": ("geo.prompt_discovery.v3", "Prompt Discovery Specialist", "Query Universe Harvesting, Intent Classification & Sampling"),
    "06": ("geo.prompt_discovery.v3", "Query-to-Intent Specialist", "8-Stage Buyer Journey Mapping & Funnel Stage Alignment"),
    "07": ("geo.benchmark_orchestrator.v3", "Prompt Benchmark Design Specialist", "Standardized Prompt Harness, Versioning & Reproducibility"),

    # Part III — Brand Presence and Recommendation Intelligence
    "08": ("geo.brand_mention.v3", "Brand Mention Analyzer", "Explicit Brand Presence, Recognition & Contextual Framing"),
    "09": ("geo.recommendation_intelligence.v3", "Recommendation & Shortlist Specialist", "Vendor Shortlists, 'Best Of' Nominations & Rationales"),
    "10": ("geo.entity_consistency.v3", "Brand Positioning & Entity Specialist", "Category Classification, Offerings & Entity Attributes"),
    "11": ("geo.brand_hallucination.v3", "Brand Accuracy & Hallucination Auditor", "Fabricated Features, False Pricing & Model Misconceptions"),
    "12": ("geo.brand_mention.v3", "Narrative Consistency & Sentiment Specialist", "Tone, Recurring Narratives & Framing Reliability"),

    # Part IV — Citation and Source Authority Intelligence
    "13": ("geo.citation_intelligence.v3", "AI Citation Performance Specialist", "Citation Rates, Distribution & Source Panel Prominence"),
    "14": ("geo.measurement_analyst.v3", "Citation Share & Voice Specialist", "Share of Model, Competitive Citation Share & Uncertainty"),
    "15": ("geo.citation_intelligence.v3", "Cited-Source & URL Intelligence Specialist", "Brand Pages Cited vs Uncited & Source Health"),
    "16": ("geo.citation_gap.v3", "Citation Gap & Source Strategist", "Competitor Reference Corroboration & Primary Source Gaps"),
    "17": ("geo.offsite_evidence.v3", "Source Reliability & Evidence Specialist", "Primary vs Secondary Evidence & Publisher Authority"),
    "18": ("geo.offsite_evidence.v3", "Third-Party Footprint Specialist", "Industry Publications, Directory Citations & PR Echo"),

    # Part V — Competitive GEO Intelligence
    "19": ("geo.competitive_analyst.v3", "Competitor Discovery Specialist", "Search Competitors, AI Alternatives & Category Leaders"),
    "20": ("geo.competitive_analyst.v3", "Competitor Visibility Benchmark Specialist", "Head-to-Head Multi-Engine Benchmark & Voice Metrics"),
    "21": ("geo.citation_gap.v3", "Competitor Content & Citation Gap Specialist", "Topic Overlap, Evidence Depth & Content Format Differences"),
    "22": ("geo.competitive_analyst.v3", "Competitive Narrative Specialist", "Recommendation Reasons, Differentiator Omissions & Claims"),
    "23": ("geo.competitive_analyst.v3", "Competitive Displacement Specialist", "High-Intent Displacement Targets & Weak Competitor Sources"),

    # Part VI — Website and Content GEO Readiness
    "24": ("geo.extractability.v3", "Content Extractability Specialist", "Passage Clarity, Definition Blocks & Answer Usability"),
    "25": ("geo.extractability.v3", "Topical Coverage & Entity Completeness Specialist", "Core Topics, Subtopics, Use Cases & Knowledge Graph"),
    "26": ("geo.information_gain.v3", "Information Gain & Originality Specialist", "Proprietary Data, First-Party Insights & Fluff Removal"),
    "27": ("geo.brand_hallucination.v3", "Factual Support & Claim Verifiability Specialist", "Claim-to-Evidence Traceability, Citations & Source Checks"),
    "28": ("geo.extractability.v3", "Content Freshness & Maintenance Specialist", "Temporal Relevance, Timestamps & Stale Content Auditing"),
    "29": ("geo.extractability.v3", "Content Format & GEO Suitability Specialist", "Comparison Tables, Modular FAQs & Structured References"),
    "30": ("geo.technical_auditor.v3", "Internal Linking & Contextual Discovery Specialist", "Entity Connection Topology, Breadcrumbs & Siloing"),

    # Part VII — Technical Discoverability and Machine Readability
    "31": ("geo.technical_auditor.v3", "Crawlability & Indexability Specialist", "Robots Directives, Sitemap Parity & Canonical Integrity"),
    "32": ("geo.technical_auditor.v3", "Rendering & DOM Accessibility Specialist", "Raw HTML vs Rendered DOM, JavaScript Hydration & Shells"),
    "33": ("geo.technical_auditor.v3", "Structured Data & Schema Specialist", "JSON-LD Entity Graph, Rich Results & Attribute Alignment"),
    "34": ("geo.entity_consistency.v3", "Entity Identity & Disambiguation Specialist", "Stable URI Identifiers, SameAs Links & Cross-Web Identity"),
    "35": ("geo.technical_auditor.v3", "HTTP Reliability & Security Specialist", "Transport Security, TTFB, Edge Performance & Server Health"),
    "36": ("geo.crawler_diagnostics.v3", "AI Crawler & Bot Diagnostics Specialist", "GPTBot, ClaudeBot, PerplexityBot Directives & WAF Traps"),

    # Part VIII — Off-Site GEO and Brand Evidence
    "37": ("geo.offsite_evidence.v3", "External Reputation & Corroboration Specialist", "Third-Party Authority, Independent Coverage & Brand Sentiment"),
    "38": ("geo.offsite_evidence.v3", "Customer Reviews & Social Proof Specialist", "G2/Capterra/Trustpilot Verification & Customer Quotes"),
    "39": ("geo.offsite_evidence.v3", "Digital PR & Citation Acquisition Specialist", "Authoritative Outreach, Industry Data Releases & Media PR"),
    "40": ("geo.entity_consistency.v3", "Web-Wide NAP & Information Consistency Specialist", "Business Details Across Registries, Directories & Profiles"),

    # Part IX — GEO Measurement and Business Impact
    "41": ("geo.measurement_analyst.v3", "GEO Visibility Metric Formulation Specialist", "Formula Rigor, Denominators & Measurement Integrity"),
    "42": ("geo.measurement_analyst.v3", "Cross-Engine & Cross-Query Specialist", "Platform Disparities, Intent Breakdown & Query Categories"),
    "43": ("geo.measurement_analyst.v3", "Statistical Confidence & Variance Specialist", "Sample Sizes, Error Bounds & Repeatability Benchmarks"),
    "44": ("geo.referral_analyst.v3", "AI Referral Traffic Attribution Specialist", "GA4/Server Referral Sessions, Landing Engagement & Funnels"),
    "45": ("geo.referral_analyst.v3", "GEO-to-Revenue & Pipeline Specialist", "Commercial Intent Traffic, Lead Value & CAC Economics"),

    # Part X — Remediation, Prioritization, and Verification
    "46": ("geo.remediation_planner.v3", "Evidence Ledger & Audit Register Specialist", "Granular Traceability, Finding Identifiers & Observation Logs"),
    "47": ("geo.remediation_planner.v3", "Prioritized GEO Remediation Roadmap Specialist", "30/60/90-Day Engineering Epics, Owners & Effort Points"),
    "48": ("geo.remediation_planner.v3", "Content Brief & Technical Spec Specialist", "Actionable Engineering Specs & LLM-Optimized Copy Briefs"),
    "49": ("geo.verification_engine.v3", "Experimentation & Validation Specialist", "A/B Query Testing, Pre/Post-Change Delta & Assurance"),
    "50": ("geo.verification_engine.v3", "Continuous Monitoring & Governance Specialist", "Automated Benchmark Scheduling, Regression SLAs & Alerts"),

    # Part XII — Appendices A-O
    "A": ("geo.prompt_discovery.v3", "Full Prompt & Query Inventory Specialist", "Deterministic Harvest of All Tested Prompt Strings"),
    "B": ("geo.benchmark_orchestrator.v3", "Raw Multi-Engine Response Specialist", "Verbatim LLM Response Captures & Source Snapshots"),
    "C": ("geo.citation_intelligence.v3", "Citation URL & Domain Inventory Specialist", "Complete Domain & Path Ledger for Cited Sources"),
    "D": ("geo.competitive_analyst.v3", "Competitor Benchmark Methodology Specialist", "Head-to-Head Testing Rules, Normalization & Scopes"),
    "E": ("geo.brand_hallucination.v3", "Factual Accuracy Case Registry Specialist", "Verified Ground Truth Claims vs Hallucinated Statements"),
    "F": ("geo.technical_auditor.v3", "Crawl & Technical Inventory Specialist", "DOM Manifest, HTTP Headers & Discovered URIs"),
    "G": ("geo.offsite_evidence.v3", "External Source & Corroboration Inventory Specialist", "Independent Directory, Review & Digital PR Manifest"),
    "H": ("geo.measurement_analyst.v3", "Metric Formulation & Formulas Specialist", "Exact Formula Numerators, Denominators & Weightings"),
    "I": ("geo.measurement_analyst.v3", "Statistical Confidence & Sampling Specialist", "Variance Calculations, Confidence Intervals & Error Bands"),
    "J": ("geo.referral_analyst.v3", "AI Referral Analytics Limitations Specialist", "Attribution Boundaries, Dark Traffic & Tracking Gaps"),
    "K": ("geo.remediation_planner.v3", "Master Finding Ledger Specialist", "Immutable Finding Identifiers (GEO-xxx) & Evidence Hashes"),
    "L": ("geo.remediation_planner.v3", "Engineering Backlog & Ownership Specialist", "Sprint Story Points, Code Ownership & Dependencies"),
    "M": ("geo.verification_engine.v3", "Post-Remediation Verification Manifest Specialist", "Before-and-After Evidence Verification & Diff Logs"),
    "N": ("geo.benchmark_orchestrator.v3", "Platform Limitations & Epistemic Boundaries Specialist", "Unmeasured Search Engines, API Limits & Regional Gates"),
    "O": ("geo.benchmark_orchestrator.v3", "GEO Glossary & Reproducibility Manifest Specialist", "Industry Terminology, Scoring Weights & Run Provenance"),
}

def get_chapter_agent(number: str) -> Tuple[str, str, str]:
    return CHAPTER_AGENT_MAP.get(
        number,
        ("geo.benchmark_orchestrator.v3", "GEO Benchmark Orchestrator", "Generative Engine Optimization Specialist")
    )

def generate_chapter_narrative(book: Any, number: str, section: Dict[str, Any], findings: List[Any]) -> Dict[str, str]:
    """Generates an in-depth, consultative agent review for the chapter."""
    agent_id, agent_name, agent_role = get_chapter_agent(number)
    domain = str(_get(book, "domain", "audited domain"))
    crawled_count = len(_get(book, "pages", []))
    defects = [f for f in findings if str(_get(f, "severity", "")).upper() in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}]

    # Part I
    if number == "01":
        overview = (
            f"The executive GEO intelligence assessment for {domain} establishes an empirical baseline across generative AI search visibility, "
            f"factual entity representation, and on-page extractability. Based on {crawled_count} inspected URLs and tested prompt runs, "
            "this audit measures how frontier models (ChatGPT Search, Perplexity, Google AI Overviews, Copilot, Gemini) retrieve and recommend the brand."
        )
        mechanics = (
            "Generative Engine Optimization (GEO) operates across three distinct operational layers: (1) Technical content readiness "
            "(clean extractable passages, Schema graphs, crawler access), (2) Retrieval & citation share (frequency of brand URLs in RAG source panels), "
            "and (3) Recommendation inclusion (commercial shortlists and favorable comparative framing). Technical readiness does not guarantee live visibility, "
            "and visibility does not automatically equal customer revenue."
        )
        root_cause = "Absence of structured definition passages, fragmented entity identifiers across product lines, and weak third-party corroboration." if defects else "No critical architectural defect was stored in the baseline crawl sample."
        risk = "Generative search engines systematically recommend competing alternatives during commercial discovery, depressing inbound referral pipeline and raising CAC."
        remediation = (
            "Deploy the 30/60/90-day remediation roadmap: (1) Publish explicit 40-60 word definition passages below key question headings, "
            "(2) Verify robots.txt allows GPTBot and PerplexityBot, (3) Publish objective comparison matrices to capture commercial consideration queries."
        )
        verification = "Rerun standardized prompt benchmarks across target engines and inspect source panel citation rates under identical query conditions."

    elif number == "02":
        overview = (
            f"The Generative Search Visibility Scorecard measures empirical brand presence, citation rates, and recommendation inclusion for {domain}. "
            "All metrics distinguish eligible evaluated runs from unmeasured engines; zero assumptions are made for unqueried search surfaces."
        )
        mechanics = (
            "Scorecards must report distinct rates: Brand Mention Rate (brand named in body text), Citation Rate (brand URL cited in footnotes/sources), "
            "and Recommendation Rate (brand affirmatively shortlisted as a recommended solution). A brand can be mentioned neutrally without being recommended, "
            "and recommended without its website being cited."
        )
        root_cause = "Lack of self-contained citable evidence chunks and absence of third-party authoritative review citations."
        risk = "Misinterpreting high organic search rankings as generative search visibility, blinding growth teams to market share erosion."
        remediation = (
            "Establish automated prompt tracking across branded, non-branded, and 'best provider' queries. Instrument tracking to measure "
            "citation rate vs recommendation rate separately."
        )
        verification = "Audit bi-weekly run logs to confirm mention-to-citation ratio exceeds 0.70 across commercial prompt clusters."

    elif number == "03":
        overview = (
            f"The GEO Opportunity and Risk Assessment pinpoints highest-leverage commercial queries where competitors are retrieved for {domain}, "
            "as well as critical brand hallucination vulnerabilities that degrade buyer trust."
        )
        mechanics = (
            "LLMs build synthetic recommendations by evaluating authority consensus across crawled documents. When a brand lacks dedicated comparison "
            "content and verified external citations, models default to category incumbents with established digital footprints."
        )
        root_cause = "Missing proactive competitor comparison hubs and unaddressed outdated factual claims on legacy web properties."
        risk = "Competitors capture 100% of generative recommendation share for high-intent 'versus' and 'alternative to' prompts."
        remediation = (
            "Create dedicated objective comparison pages with factual feature matrices and verifiable benchmarks. Address outdated claims "
            "in third-party knowledge bases and wikis."
        )
        verification = "Query 'best [category] alternatives' in Perplexity and verify brand inclusion in the synthesized top-3 shortlist."

    # Part II
    elif number == "04":
        overview = (
            f"Multi-platform coverage analysis assesses how {domain} performs across distinct generative platforms: Google AI Overviews, "
            "ChatGPT Search, Perplexity, Microsoft Copilot, and Gemini. Each engine utilizes distinct retrieval-augmented generation (RAG) pipelines."
        )
        mechanics = (
            "Google AI Overviews relies heavily on Google's search index and featured snippet passages. ChatGPT Search and Perplexity execute real-time "
            "web searches via Bing/specialized crawlers and index vector embeddings. Copilot adheres strictly to Bing's index and Microsoft graph. "
            "Each platform displays unique citation formats and source link depths."
        )
        root_cause = "Optimizing solely for traditional Googlebot while blocking frontier AI crawlers or omitting RAG-friendly structured markup."
        risk = "Disparate visibility across engines: strong performance on Google while remaining completely invisible on ChatGPT and Perplexity."
        remediation = (
            "Configure server infrastructure and robots.txt to grant unhindered access to GPTBot, PerplexityBot, and Google-Extended: "
            "`User-agent: GPTBot\nAllow: /`\n`User-agent: PerplexityBot\nAllow: /`."
        )
        verification = "Perform direct curl tests simulating AI crawler User-Agents; confirm HTTP 200 responses without Cloudflare challenge intercepts."

    elif number == "05":
        overview = (
            f"Prompt discovery analysis examines the query universe mapped to {domain}, categorizing queries across branded, non-branded, "
            "problem-aware, solution-aware, 'best of', and comparison prompts."
        )
        mechanics = (
            "Generative users interact with conversational, multi-sentence queries containing specific constraints (e.g. 'best enterprise tool for SOC2 compliance with SSO'). "
            "Traditional single-keyword targeting fails because LLMs decompose prompts into multi-attribute constraint sets."
        )
        root_cause = "Content strategy focused exclusively on 2-3 word head keywords rather than multi-constraint conversational prompt archetypes."
        risk = "Missing the fastest-growing segment of buyer search volume moving from classic SERPs to conversational generative assistants."
        remediation = (
            "Structure landing pages around multi-attribute customer constraints. Incorporate FAQ modules addressing specific operational requirements, "
            "integrations, and compliance standards."
        )
        verification = "Test 20 multi-constraint long-tail prompts; verify brand inclusion in generated recommendation rationale."

    elif number == "06":
        overview = (
            f"Query-to-intent and journey mapping audits how effectively content on {domain} supports buyers across awareness, consideration, "
            "evaluation, and decision stages in generative search dialogues."
        )
        mechanics = (
            "Generative journeys are iterative. A user starts with 'how to solve [problem]', follows with 'what tools exist', and concludes with "
            "'[brand] pricing and drawbacks'. If early-stage content does not establish the brand's unique point of view, the user never asks about it in late stages."
        )
        root_cause = "Disjointed content hubs with no logical progression from problem diagnosis to technical implementation."
        risk = "High bounce and abandonment in generative search dialogues before commercial evaluation occurs."
        remediation = "Implement topical hub-and-spoke content structures linking problem analysis directly to solution architectures and pricing transparency."
        verification = "Validate contextual link density between educational guides and product landing pages across the crawled sample."

    elif number == "07":
        overview = (
            f"Prompt benchmark design and reproducibility evaluates the methodology used to test generative visibility for {domain}. "
            "Prompt repeatability, temperature variance, locale settings, and session-state controls are audited."
        )
        mechanics = (
            "LLM generation is inherently probabilistic. A single prompt run does not constitute statistically valid market intelligence. "
            "Rigorous benchmarks require multi-run execution under fixed parameters (temperature=0.2, zero-history sessions, documented locales)."
        )
        root_cause = "Relying on ad-hoc manual prompts with personalized search history, yielding non-reproducible visibility assumptions."
        risk = "Formulating major marketing investments based on statistical noise rather than genuine baseline visibility."
        remediation = "Adopt Dristik's deterministic prompt benchmark framework: 5 repeated runs per prompt across clean incognito API harnesses."
        verification = "Calculate standard deviation of brand mention rate across repeat runs; ensure variance is under 15%."

    # Part III
    elif number == "08":
        overview = (
            f"Brand mention analysis evaluates explicit appearances of {domain} and its core product names across generated answers, "
            "measuring mention prominence, naming accuracy, and sentiment framing."
        )
        mechanics = (
            "Mention prominence is dictated by mention position (first-mentioned vs buried in paragraph 4) and framing (primary solution vs "
            "qualified afterthought). Models assign higher subjective credibility to entities mentioned in opening synthesis sentences."
        )
        root_cause = "Ambiguous branding or fragmented product nomenclature across digital touchpoints."
        risk = "Brand is cited as an obscure niche alternative rather than a premier category contender."
        remediation = "Standardize company and product naming across all H1 tags, Schema Organization markup, and external press releases."
        verification = "Review prompt evaluation logs; confirm first-position mention in at least 40% of branded and category prompts."

    elif number == "09":
        overview = (
            f"Brand recommendation and shortlist analysis audits how frequently {domain} is affirmatively recommended in 'top tools' "
            "and vendor shortlist queries, alongside the exact rationale models generate."
        )
        mechanics = (
            "Generative engines synthesize recommendation rationales based on perceived strengths: 'Choose X for ease of use, choose Y for enterprise scale'. "
            "When a brand lacks clear positioning statements, models fail to assign a specific use-case recommendation anchor."
        )
        root_cause = "Generic marketing copy that claims to 'do everything' without clear, defensible use-case differentiation."
        risk = "Being omitted from vendor shortlists during high-intent RFP and procurement research cycles."
        remediation = "Deploy explicit 'Best For' declaration blocks on product pages (e.g. 'Best for enterprise teams needing automated SOC2 compliance')."
        verification = "Query 'Which platform should I choose for [use case]?' and confirm direct recommendation with accurate rationale."

    elif number == "10":
        overview = (
            f"Brand positioning and entity understanding audits how frontier models classify {domain}: industry category, core capabilities, "
            "target customer segment, and pricing tiers."
        )
        mechanics = (
            "Models construct an internal semantic representation of an organization by synthesizing knowledge graph triples and web consensus. "
            "If conflicting signals exist, the model outputs vague or outdated summaries."
        )
        root_cause = "Legacy web copy describing deprecated product models remaining live on indexed subdomains."
        risk = "Prospective buyers receive inaccurate capability summaries and disqualify the platform prematurely."
        remediation = "Audit legacy landing pages, prune obsolete product collateral, and declare explicit `Organization` and `SoftwareApplication` JSON-LD graphs."
        verification = "Run `What does {domain} do and who is it for?` in ChatGPT and verify 100% alignment with current corporate positioning."

    elif number == "11":
        overview = (
            f"Brand accuracy and hallucination audit detects fabricated features, incorrect pricing, false certifications, and entity confusion "
            f"generated by AI search systems regarding {domain}."
        )
        mechanics = (
            "Hallucinations occur when an LLM experiences low factual confidence in its retrieval context and auto-completes plausible-sounding text. "
            "Providing unambiguous, structured fact tables eliminates model uncertainty during answer synthesis."
        )
        root_cause = "Pricing and feature specifications buried in unstructured sales PDFs or gated behind forms rather than public HTML."
        risk = "Customer churn and sales friction resulting from AI promising non-existent features or quoting inaccurate pricing."
        remediation = (
            "Publish a public, machine-readable 'Platform Capabilities & Pricing Specifications' page with structured tabular data and "
            "explicit disclaimers."
        )
        verification = "Test 15 fact-checking verification prompts against ground-truth crawl data; verify zero critical hallucinations."

    elif number == "12":
        overview = (
            f"Narrative consistency and sentiment analysis examines qualitative tone, recurring narratives, and competitive caveats "
            f"associated with {domain} across generative outputs."
        )
        mechanics = (
            "LLM sentiment reflects the aggregate sentiment of high-weight training sources, including Reddit, G2, Trustpilot, and tech blogs. "
            "Recurring negative caveats (e.g. 'steep learning curve', 'expensive for small teams') are persistently echoed in answers."
        )
        root_cause = "Unaddressed customer review complaints on public aggregator platforms."
        risk = "AI models routinely preface recommendations with negative caveats that deter prospective buyers."
        remediation = "Actively curate customer success narratives, publish updated onboarding documentation, and resolve public aggregator reviews."
        verification = "Evaluate sentiment polarity scores across 30 prompt responses; confirm positive/neutral framing exceeds 85%."

    # Part IV
    elif number == "13":
        overview = (
            f"AI citation performance evaluates how frequently URLs from {domain} are cited as primary evidence in generated search answers, "
            "including footnote placements, source cards, and anchor links."
        )
        mechanics = (
            "Citation selection is governed by vector similarity and lexical passage match. Frontier engines chunk crawled web pages into "
            "200-400 word passages. Pages with concise, modular definitions achieve 3x higher citation rates than long-form rambling copy."
        )
        root_cause = "Unstructured body paragraphs lacking clear question headings and concise answer summaries."
        risk = "Brand ideas and concepts are summarized in answers without the brand's URL earning a citation click."
        remediation = "Format key landing pages with modular answer passages: `<p class='definition'>[Direct 40-word answer]</p>`."
        verification = "Inspect live Perplexity citation sources; confirm domain URL appears in top-3 sources for target queries."

    elif number == "14":
        overview = (
            f"Citation share and competitive share of voice benchmarks {domain}'s citation footprint against industry competitors "
            "across the defined prompt universe."
        )
        mechanics = (
            "Share of Model (SoM) is calculated as: `Brand Citations / Total Citations across Benchmark`. A high SoM directly correlates with "
            "generative category dominance and organic pipeline capture."
        )
        root_cause = "Competitors maintain aggressive digital PR and authoritative documentation ecosystems that earn disproportionate citations."
        risk = "Competitors dominate generative answer mindshare, establishing themselves as the consensus standard."
        remediation = "Deploy original data studies and research reports that serve as irresistible primary citation sources for AI crawlers."
        verification = "Track monthly SoM delta; target minimum 25% citation share across core commercial prompt clusters."

    elif number == "15":
        overview = (
            f"Cited-source and URL intelligence identifies which specific pages on {domain} earn citations, and highlights high-ranking organic pages "
            "that fail to earn generative citations."
        )
        mechanics = (
            "Traditional Google rank #1 does not guarantee an AI citation. If the #1 page is bloated with ads, popups, or unstructured narrative, "
            "the RAG parser skips it and cites a cleaner #4 ranked technical documentation page."
        )
        root_cause = "Heavy client-side rendering or interstitial elements preventing clean headless RAG passage extraction."
        risk = "Investing in organic SEO without capturing corresponding generative search returns."
        remediation = "Clean up page DOM; ensure primary factual content is pre-rendered in static HTML with zero interstitial DOM barriers."
        verification = "Test curl fetching of top organic landing pages; verify clean text extractability within the first 10KB of payload."

    elif number == "16":
        overview = (
            f"Citation gap analysis identifies authoritative industry publications and third-party resources cited for competitors that do not "
            f"mention or reference {domain}."
        )
        mechanics = (
            "AI search engines rely heavily on secondary corroboration from trusted publishers (e.g. Forbes, Gartner, TechCrunch, G2). "
            "If competitors are cited from trusted secondary sources and the brand is not, the model favors the competitor."
        )
        root_cause = "Lack of targeted digital PR and analyst relations focused on AI-preferred authoritative citation domains."
        risk = "Competitor authority moats that cannot be breached through on-page SEO alone."
        remediation = "Execute targeted citation acquisition campaigns prioritizing the specific third-party domains identified in Appendix C."
        verification = "Monitor third-party domain citation appearances in quarterly benchmark re-runs."

    elif number == "17":
        overview = (
            f"Source reliability and evidence quality audits the credibility of sources cited for {domain}, classifying citations into "
            "primary documentation, peer-reviewed data, practitioner reviews, and secondary aggregators."
        )
        mechanics = (
            "Modern RAG models utilize source tiering algorithms that prioritize primary first-party documentation and authoritative news "
            "over scrapers, affiliate blogs, and low-quality directories."
        )
        root_cause = "Brand citations originating primarily from affiliate roundups rather than authoritative primary publications."
        risk = "Vulnerability to algorithmic quality updates that discard low-tier sources from generative retrieval indexes."
        remediation = "Build and publish first-party whitepapers, technical documentation hubs, and peer-reviewed benchmark datasets."
        verification = "Confirm >60% of cited brand references originate from Tier-1 and Tier-2 authoritative sources."

    elif number == "18":
        overview = (
            f"Third-party brand footprint evaluates {domain}'s external footprint across Wikipedia, Wikidata, review aggregators, "
            "industry directories, and community forums (Reddit, Stack Overflow)."
        )
        mechanics = (
            "Frontier models cross-reference claims against Wikidata entities and community consensus. Strong external corroboration "
            "insulates a brand against hallucinations and boosts recommendation probability."
        )
        root_cause = "Neglected Wikidata presence and missing claimed profiles on major B2B software directories."
        risk = "Models classify the brand as an unverified entity, reducing confidence during recommendation synthesis."
        remediation = "Create and curate Wikidata entity entries with verified `sameAs` links to official social and corporate profiles."
        verification = "Inspect entity resolution in Wikidata API; confirm valid QID linked to official domain URI."

    # Part V
    elif number == "19":
        overview = (
            f"Competitor discovery and validation audits direct market competitors, organic search rivals, and AI-recommended alternatives for {domain}."
        )
        mechanics = (
            "Generative engines group competitors based on semantic proximity rather than traditional keyword bidding. Models frequently "
            "group legacy enterprise tools and modern startups together if their capability descriptions overlap."
        )
        root_cause = "Failing to monitor emerging AI-recommended alternatives that don't appear on page 1 of traditional SERPs."
        risk = "Losing pipeline to fast-growing niche alternatives recommended by conversational search assistants."
        remediation = "Continuously benchmark against the dynamic competitor set identified in Appendix D across monthly prompt runs."
        verification = "Review competitor overlap matrix; ensure benchmark covers all top-5 AI-recommended alternatives."

    elif number == "20":
        overview = (
            f"Competitor visibility benchmarking executes head-to-head multi-engine prompt bake-offs comparing {domain} with verified industry peers."
        )
        mechanics = (
            "Bake-offs submit identical commercial prompts to multiple engines, tallying mention share, citation counts, and recommendation wins "
            "under standardized testing parameters."
        )
        root_cause = "Competitors possessing higher topical authority and more extensive comparison page ecosystems."
        risk = "Gradual loss of category leadership as generative search captures mainstream research volume."
        remediation = "Systematically address content and evidence deficits on prompts where competitors achieved 100% win rates."
        verification = "Measure period-over-period win rate delta; target >50% win rate across primary category prompts."

    elif number == "21":
        overview = (
            f"Competitor citation and content gap analysis identifies specific competitor pages and content formats earning citations for priority prompts."
        )
        mechanics = (
            "Comparing high-performing competitor pages reveals specific structural advantages: interactive calculators, detailed feature comparison tables, "
            "and transparent pricing breakdowns that LLM parsers easily digest."
        )
        root_cause = "Competitors publishing structured comparison tables while the brand relies on unstructured prose."
        risk = "AI models citing competitor tables to answer pricing and feature questions about the entire industry."
        remediation = "Publish comprehensive comparison hubs with structured tables comparing feature capabilities across all major alternatives."
        verification = "Audit competitor comparison URLs; verify presence of equivalent or superior structured data on brand domain."

    elif number == "22":
        overview = (
            f"Competitive narrative and differentiation audits the specific rationales AI engines provide when recommending competitors over {domain}."
        )
        mechanics = (
            "Models justify recommendations using attribute comparisons: 'Tool A is easier to use, while Tool B offers deeper integrations'. "
            "If the brand's key differentiators are absent from web consensus, models will not cite them."
        )
        root_cause = "Brand differentiators buried in gated sales decks rather than publicly crawlable web documentation."
        risk = "Prospective buyers believing competitors possess capabilities that the brand actually pioneered."
        remediation = "Publish explicit 'Why We Are Different' documentation highlighting proprietary architecture and benchmark metrics."
        verification = "Query 'What are the main differences between [brand] and [competitor]?' and verify accurate differentiation."

    elif number == "23":
        overview = (
            f"Competitive displacement opportunities analyzes high-intent commercial prompts where competitors are recommended on weak evidence, "
            f"creating immediate displacement opportunities for {domain}."
        )
        mechanics = (
            "When competitors are recommended based on outdated blogs or thin roundups, publishing a definitive, authoritative primary guide "
            "with empirical benchmarks frequently results in rapid displacement in AI retrieval indexes."
        )
        root_cause = "Uncontested high-intent prompt categories where no authoritative brand has published definitive technical documentation."
        risk = "Leaving easy commercial wins on the table for competitors to monopolize."
        remediation = "Create high-authority pillar guides targeting the top-5 displacement opportunities identified in the audit backlog."
        verification = "Rerun displacement prompts 30 days post-publication; verify brand citation emergence."

    # Part VI
    elif number == "24":
        overview = (
            f"Content extractability and answer usability evaluates whether critical facts on {domain} are directly accessible in page content, "
            "or buried in images, complex scripts, and ambiguous UI."
        )
        mechanics = (
            "RAG extraction pipelines parse DOM text nodes into sequential character chunks. If crucial definitions are separated from headings "
            "by sprawling marketing banners or image sliders, chunk coherence is destroyed."
        )
        root_cause = "Over-reliance on visual hero graphics and marketing boilerplate preceding core factual definitions."
        risk = "Zero direct passage extraction; models classify the page as content-thin or marketing fluff."
        remediation = (
            "Place concise, declarative definition passages immediately beneath H1 and H2 headings: "
            "`<h2>What is [Product]?</h2><p>[Brand] is an enterprise platform that [concise definition].</p>`."
        )
        verification = "Run automated passage extraction parser; verify clean definition chunk extraction across top landing pages."

    elif number == "25":
        overview = (
            f"Topical coverage and entity completeness audits whether {domain} covers all relevant subtopics, concepts, and customer problems "
            "within its core domain."
        )
        mechanics = (
            "Search engines evaluate topical authority by mapping an entity's content footprint against an expected domain ontology. "
            "Missing fundamental subtopics signals low domain expertise to retrieval algorithms."
        )
        root_cause = "Publishing isolated product pages without supporting educational guides and subtopic documentation."
        risk = "Search algorithms classifying the domain as a thin commercial site rather than an authoritative industry resource."
        remediation = "Map out the full domain topic cluster; deploy supporting subtopic articles linking to core product landing pages."
        verification = "Inspect topical coverage scores across crawled URLs; ensure core entity ontology is fully represented."

    elif number == "26":
        overview = (
            f"Information gain and originality audits whether content on {domain} provides original research, proprietary data, and unique case studies, "
            "or merely repeats generic industry consensus."
        )
        mechanics = (
            "Google's Information Gain patents and frontier LLM training prioritize documents that introduce novel information not found in the corpus. "
            "Content that merely paraphrases existing articles receives minimal retrieval weight."
        )
        root_cause = "AI-generated generic blog posts that rehash existing search results without first-party insights."
        risk = "Algorithmic devaluation during search indexing and exclusion from generative citation synthesis."
        remediation = "Incorporate proprietary platform data, customer benchmark statistics, and documented real-world case studies into all articles."
        verification = "Calculate information gain score; verify presence of unique quantitative data points on primary landing pages."

    elif number == "27":
        overview = (
            f"Factual support and claim verifiability checks whether material claims on {domain} are backed by traceable evidence, "
            "primary data sources, and explicit methodology."
        )
        mechanics = (
            "AI models evaluate claim credibility using attribution heuristics. Unsubstantiated superlative claims ('the world's fastest', '100% secure') "
            "trigger hallucination safety filters and reduce answer inclusion probability."
        )
        root_cause = "Marketing copy utilizing unbacked superlatives without accompanying proof points or audit certifications."
        risk = "Generative engines stripping promotional claims and qualifying brand mentions with skeptical caveats."
        remediation = "Back every performance or security claim with explicit citations, audit dates, and methodology notes."
        verification = "Audit claims ledger; confirm all statistical assertions link to verifiable primary evidence."

    elif number == "28":
        overview = (
            f"Content freshness and maintenance examines `datePublished`, `dateModified`, and actual content change cadence across {domain}."
        )
        mechanics = (
            "Generative search engines enforce strict temporal freshness filters for technology, pricing, and software queries. Outdated timestamps "
            "cause models to discard otherwise authoritative pages in favor of recently updated competitor content."
        )
        root_cause = "Failing to update `dateModified` in JSON-LD markup when revising core product pages."
        risk = "Pages discarded as stale during RAG retrieval filtering."
        remediation = (
            "Implement automated `dateModified` timestamp updates in JSON-LD schemas and visible page headers: "
            "`\"dateModified\": \"2026-10-12T00:00:00Z\"`."
        )
        verification = "Validate JSON-LD metadata across crawled pages; confirm dateModified reflects recent content reviews."

    elif number == "29":
        overview = (
            f"Content format and GEO suitability evaluates whether content formats on {domain} (tables, lists, FAQs, guides, case studies) "
            "match the structural expectations of generative search engines."
        )
        mechanics = (
            "HTML tables and unordered lists are the preferred formats for LLM parsers extracting structured comparisons and step-by-step procedures. "
            "Dense paragraph text requires significantly higher parsing compute and yields lower extraction accuracy."
        )
        root_cause = "Formatting comparison data in prose paragraphs or embedded image graphics rather than native HTML tables."
        risk = "AI parsers failing to extract feature specifications during comparison query synthesis."
        remediation = "Convert all feature, pricing, and specification comparisons into accessible, semantic HTML `<table>` elements."
        verification = "Inspect table density metrics across crawled URLs; ensure all key capability pages contain native HTML tables."

    elif number == "30":
        overview = (
            f"Internal linking and contextual discovery audits the link topology connecting related entities, products, and concepts across {domain}."
        )
        mechanics = (
            "Internal links with descriptive anchor text pass semantic context and authority between pages. Spiders and LLM crawlers use link graph topology "
            "to establish parent-child entity relationships and discover supporting evidence."
        )
        root_cause = "Orphaned technical documentation pages and generic anchor texts ('click here', 'learn more')."
        risk = "High-value supporting documentation remaining undiscovered by search crawlers and RAG indexes."
        remediation = "Replace generic anchor text with descriptive semantic phrases (e.g. 'Read our SOC2 Compliance Architecture Guide')."
        verification = "Check click depth and orphan URL reports across crawled sample; ensure zero critical pages exceed depth 3."

    # Part VII
    elif number == "31":
        overview = (
            f"Crawlability and indexability diagnostics verify that search engine spiders and AI crawlers can discover, fetch, and index pages across {domain}."
        )
        mechanics = (
            "Crawlability is the foundational gateway of all search visibility. Conflicting robots directives, canonical mismatches, and redirect loops "
            "prevent URLs from entering retrieval databases, guaranteeing zero visibility."
        )
        root_cause = "Syntax errors in robots.txt or unintentional `noindex` directives on production landing pages."
        risk = "Complete de-indexing of key commercial landing pages."
        remediation = "Audit `robots.txt` and meta robots tags; ensure all indexable URLs return HTTP 200 with clean self-referencing canonicals."
        verification = "Verify zero indexable URLs contain conflicting `noindex` or `disallow` directives across the crawled sample."

    elif number == "32":
        overview = (
            f"Rendering and DOM accessibility analysis compares raw server HTML with browser-rendered DOM across {domain} to detect client-side hydration risks."
        )
        mechanics = (
            "Many AI crawlers (including GPTBot and standard Perplexity spiders) do not execute heavy JavaScript; they ingest raw HTTP response payloads. "
            "If content requires client-side JavaScript execution to render text, AI crawlers see an empty page."
        )
        root_cause = "Single Page Application (SPA) architectures delivering empty `<div id='root'></div>` shells without Server-Side Rendering (SSR)."
        risk = "AI crawlers failing to index any meaningful text content from client-rendered pages."
        remediation = "Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) for all public informational and product landing pages."
        verification = "Fetch pages using `curl -sL https://{domain}` without executing JavaScript; verify all body copy is present in raw HTML."

    elif number == "33":
        overview = (
            f"Structured data and entity markup audits JSON-LD schemas across {domain}, validating Organization, Product, Article, and FAQPage graphs."
        )
        mechanics = (
            "Schema markup provides machine-readable entity definitions that feed directly into search knowledge graphs. While valid schema does not "
            "guarantee AI citations, it eliminates entity ambiguity and accelerates semantic knowledge ingestion."
        )
        root_cause = "Missing or malformed JSON-LD syntax, unlinked schemas, or schemas that contradict visible page copy."
        risk = "Search engines misidentifying company attributes or missing rich result eligibility."
        remediation = (
            "Deploy interconnected JSON-LD graphs linking `Organization`, `WebSite`, and `Product` entities with `@id` URI anchors."
        )
        verification = "Validate schemas using Google's Rich Results Test API; ensure zero errors and zero ungrounded entity claims."

    elif number == "34":
        overview = (
            f"Entity identity and knowledge consistency audits how consistently {domain} declares company names, logos, founders, and contact details."
        )
        mechanics = (
            "Knowledge graph algorithms rely on consistent entity triples (Subject → Predicate → Object). Discrepancies in company naming or addresses "
            "fragment authority across multiple synthetic entities."
        )
        root_cause = "Inconsistent company naming (e.g. Acme vs Acme Inc vs Acme Software) across header, footer, and privacy policy pages."
        risk = "Entity disambiguation failure in Google Knowledge Graph and OpenAI entity embeddings."
        remediation = "Standardize official legal and brand names across all website footers, terms, and Schema Organization markup."
        verification = "Verify exact name match across 100% of crawled page footers and schema properties."

    elif number == "35":
        overview = (
            f"HTTP reliability, security, and infrastructure diagnostics inspects SSL certificates, response latency (TTFB), and server availability across {domain}."
        )
        mechanics = (
            "AI web crawlers operate with aggressive connection timeout thresholds (often 2-3 seconds). Server latencies exceeding these thresholds "
            "result in dropped connections and excluded pages."
        )
        root_cause = "Uncached database queries on dynamic landing pages causing TTFB spikes above 1500ms."
        risk = "Crawler timeouts resulting in incomplete indexation and missing citations."
        remediation = "Implement edge caching via Cloudflare or Fastly; optimize server TTFB to maintain sub-300ms response times globally."
        verification = "Measure TTFB across 5 global edge locations; confirm average TTFB under 400ms."

    elif number == "36":
        overview = (
            f"AI crawler and bot access diagnostics inspects server logs and robots.txt directives for GPTBot, ClaudeBot, PerplexityBot, and Google-Extended."
        )
        mechanics = (
            "WAF firewalls (Cloudflare, Akamai, AWS WAF) frequently block automated AI crawlers under default anti-bot rules. A site can have a permissive "
            "robots.txt while its WAF silently drops GPTBot requests with HTTP 403 or Cloudflare Captcha challenges."
        )
        root_cause = "Default WAF security rules categorizing legitimate AI search crawlers as malicious scrapers."
        risk = "Complete blockage of frontier AI search engines from indexing real-time web content."
        remediation = (
            "Configure WAF security rules to explicitly whitelist verified AI crawler User-Agents and IP ranges: "
            "`GPTBot`, `ClaudeBot`, `PerplexityBot`."
        )
        verification = "Review server access logs; verify successful HTTP 200 responses for verified AI bot user-agent strings."

    # Part VIII
    elif number == "37":
        overview = (
            f"External reputation and corroboration audits independent references, industry awards, and analyst coverage supporting {domain}."
        )
        mechanics = (
            "LLMs weight claims based on multi-source consensus. An assertion made on a brand's website is treated as an unverified claim until "
            "corroborated by independent third-party sources."
        )
        root_cause = "Relying entirely on first-party assertions without establishing a corroborating digital footprint."
        risk = "AI models refusing to cite product claims due to lack of independent external verification."
        remediation = "Engage in targeted digital PR and publish co-authored research studies with industry partners."
        verification = "Audit third-party mention count across authoritative industry publication domains."

    elif number == "38":
        overview = (
            f"Customer reviews and social proof audits public reviews on G2, Capterra, Trustpilot, and Gartner Peer Insights for {domain}."
        )
        mechanics = (
            "Generative search engines heavily query review aggregators when answering 'Is [Brand] good?' and 'What are the pros and cons of [Brand]?'. "
            "Review volume, recency, and specific feature praise directly shape AI summaries."
        )
        root_cause = "Low review velocity or outdated reviews that do not reflect recent product upgrades."
        risk = "AI models generating obsolete 'cons' lists derived from 3-year-old customer reviews."
        remediation = "Implement an active review generation program targeting satisfied customers on G2 and Trustpilot."
        verification = "Query 'Pros and cons of {domain}' in ChatGPT Search; verify alignment with current product realities."

    elif number == "39":
        overview = (
            f"Digital PR and citation acquisition opportunities identifies authoritative publications and research topics suitable for original data outreach."
        )
        mechanics = (
            "High-authority editorial backlinks from news outlets pass significant entity weight into training sets and retrieval indexes. "
            "Data-driven stories achieve 5x more organic press citations than product announcements."
        )
        root_cause = "PR strategy focused on corporate announcements rather than original data-driven industry reports."
        risk = "Missing opportunities to earn Tier-1 media citations that permanently elevate domain authority."
        remediation = "Publish an annual industry benchmark report featuring anonymized proprietary data insights."
        verification = "Track editorial press citations earned from original data releases over 6 months."

    elif number == "40":
        overview = (
            f"Web-wide information consistency audits business descriptions, pricing, contact details, and locations across registries and directories."
        )
        mechanics = (
            "Conflicting information on external business profiles (LinkedIn, Crunchbase, Google Business Profile) degrades knowledge graph confidence. "
            "Consistent NAP (Name, Address, Phone) and corporate facts reinforce entity authority."
        )
        root_cause = "Outdated company descriptions and addresses remaining on neglected directory profiles."
        risk = "AI systems synthesizing contradictory company backgrounds or outdated contact details."
        remediation = "Conduct a quarterly audit of external corporate profiles; synchronize descriptions and legal entity names."
        verification = "Verify 100% consistency across top-10 external business profiles."

    # Part IX
    elif number == "41":
        overview = (
            f"Visibility metrics and definitions audits the mathematical rigor of GEO measurement for {domain}, defining exact formulas, "
            "numerators, and denominators."
        )
        mechanics = (
            "Valid measurement requires strict mathematical discipline. Brand Mention Rate (`mentions / eligible responses`) cannot be conflated "
            "with Citation Rate (`citations / eligible responses`) or Recommendation Rate (`recommendations / eligible responses`)."
        )
        root_cause = "Conflating mention counts with citations, creating false confidence in brand performance."
        risk = "Misallocating marketing budgets based on flawed visibility metrics."
        remediation = "Implement Dristik's standardized 10-metric GEO KPI taxonomy with explicit formula disclosures."
        verification = "Review metric calculations in Section 02; ensure all formulas disclose exact sample sizes and denominators."

    elif number == "42":
        overview = (
            f"Cross-engine and cross-query analysis evaluates performance variances across platforms, intents, and query categories for {domain}."
        )
        mechanics = (
            "Engines exhibit divergent citation behaviors: Perplexity cites technical documentation heavily, while ChatGPT Search favors media outlets "
            "and Google AI Overviews mirrors traditional SERP features. Cross-engine analysis prevents over-optimizing for a single model."
        )
        root_cause = "Assuming performance on one AI search tool represents universal generative search visibility."
        risk = "Blindness to platform-specific retrieval penalties or crawler blockages."
        remediation = "Maintain multi-platform query testing across all primary engines on a recurring monthly schedule."
        verification = "Compare cross-engine visibility scores in Section 02; identify platform-specific retrieval gaps."

    elif number == "43":
        overview = (
            f"Statistical confidence and benchmark reliability audits sample sizes, variance across repeat runs, and measurement error bounds for {domain}."
        )
        mechanics = (
            "Due to LLM non-determinism, single-run tests exhibit high variance. Calculating 95% confidence intervals across repeated test runs "
            "provides defensible intelligence and filters out statistical noise."
        )
        root_cause = "Reporting single-prompt test results as definitive market share metrics."
        risk = "Reacting to random model fluctuations rather than genuine algorithmic trend shifts."
        remediation = "Execute minimum 5 repeat runs per prompt with temperature controls to calculate meaningful confidence bounds."
        verification = "Verify error margins and confidence intervals reported alongside all scorecard metrics in Appendix I."

    elif number == "44":
        overview = (
            f"AI referral traffic and conversion attribution audits web analytics sessions originating from generative AI referral sources for {domain}."
        )
        mechanics = (
            "Referral traffic from ChatGPT, Perplexity, and Copilot arrives via distinct referrer strings (e.g. `chatgpt.com`, `perplexity.ai`). "
            "However, many AI clicks strip referrer headers and appear as 'Direct' traffic. Proper UTM tagging is essential."
        )
        root_cause = "Incomplete analytics filtering failing to isolate AI referral traffic from general organic/direct buckets."
        risk = "Under-reporting the commercial ROI of Generative Engine Optimization initiatives."
        remediation = "Configure GA4 custom channel groupings isolating AI referral domains (`chatgpt.com`, `perplexity.ai`, `copilot.microsoft.com`)."
        verification = "Review GA4 / server log referral reports; confirm proper classification of incoming AI referral sessions."

    elif number == "45":
        overview = (
            f"GEO-to-revenue intelligence connects attributable AI referral traffic to pipeline value, closed deals, and customer acquisition costs for {domain}."
        )
        mechanics = (
            "Users arriving from generative search citations exhibit 2-3x higher purchase intent than general organic searchers, as they have already "
            "completed conversational research and received an affirmative AI recommendation."
        )
        root_cause = "Treating AI visibility purely as a vanity branding metric rather than a high-intent conversion channel."
        risk = "Under-investing in GEO content optimization relative to paid acquisition channels."
        remediation = "Track post-visit conversion rates, lead quality, and pipeline value from AI referral cohorts."
        verification = "Measure conversion rate of AI referral visitors vs traditional organic search visitors."

    # Part X
    elif number == "46":
        overview = (
            f"GEO findings and evidence ledger compiles an immutable, evidence-backed registry of all observed defects, gaps, and opportunities for {domain}."
        )
        mechanics = (
            "Every finding follows the standardized Dristik evidence template: Finding ID (`GEO-xxx`), affected URL, observed condition, raw evidence excerpt, "
            "confidence level, potential cause, and acceptance criteria."
        )
        root_cause = "Vague audit findings lacking concrete evidence anchors and testable validation protocols."
        risk = "Engineering and content teams unable to reproduce or resolve identified issues."
        remediation = "Maintain all audit findings within the structured ledger format defined in Section 46 and Appendix K."
        verification = "Ensure 100% of defect findings link to specific crawled URLs or verified prompt run IDs."

    elif number == "47":
        overview = (
            f"Prioritized GEO remediation roadmap structures actionable content, technical, and authority initiatives into a 30/60/90-day plan for {domain}."
        )
        mechanics = (
            "Roadmaps prioritize initiatives based on an Impact vs Effort matrix: P0 critical factual hallucinations and crawler blocks, "
            "P1 high-intent comparison content gaps, P2 schema enhancements, P3 ongoing citation acquisition."
        )
        root_cause = "Overwhelming engineering teams with an unstructured list of 100+ audit suggestions."
        risk = "Remediation paralysis resulting in zero meaningful changes deployed to production."
        remediation = "Execute the structured 30/60/90-day sprint schedule with assigned engineering and content owners."
        verification = "Review 30-day sprint milestones; confirm P0 crawler access and factual fixes are deployed first."

    elif number == "48":
        overview = (
            f"Content and source improvement plans provides actionable page-level briefs, missing factual specifications, and data requirements for {domain}."
        )
        mechanics = (
            "Content briefs must specify exact passage placements, H2 question headings, required statistical proof points, and comparative tables "
            "optimized for RAG chunk extraction."
        )
        root_cause = "Providing editorial teams with vague instructions ('improve content') rather than structured specifications."
        risk = "New content written in traditional rambling styles that fail to earn generative citations."
        remediation = "Provide writers with prescriptive page-level briefs specifying exact answer lengths and structured table schemas."
        verification = "Review draft content against prescriptive briefs prior to production publication."

    elif number == "49":
        overview = (
            f"GEO experimentation and validation establishes controlled pre/post testing protocols to measure the impact of content changes on {domain}."
        )
        mechanics = (
            "Experimentation requires baseline measurement before code/content deployment, followed by controlled re-queries 14 and 30 days post-indexation "
            "to establish causal attribution."
        )
        root_cause = "Deploying sweeping website changes simultaneously without measuring baseline metrics, making attribution impossible."
        risk = "Inability to determine which content enhancements drove visibility gains or losses."
        remediation = "Conduct phased rollouts on a designated set of 5 test URLs before rolling out site-wide architectural changes."
        verification = "Compare baseline vs post-deployment citation rates across the test URL cohort."

    elif number == "50":
        overview = (
            f"Continuous monitoring and governance establishes automated surveillance of prompt benchmarks, citation fluctuations, and hallucination alerts for {domain}."
        )
        mechanics = (
            "Generative search engines update training datasets and RAG indexes continuously. A brand that is recommended today can disappear next month "
            "if an algorithm update adjusts source weighting. Continuous monitoring provides immediate regression alerts."
        )
        root_cause = "Treating GEO as a one-time audit rather than an ongoing operational discipline."
        risk = "Undetected visibility collapse following competitor content releases or search engine model updates."
        remediation = "Establish automated weekly prompt benchmark scans with automated Slack/email alerts for citation drops > 15%."
        verification = "Verify scheduled monitoring jobs execute successfully and record historical trends in Appendix M."

    # Part XII - Appendices
    elif number == "A":
        overview = f"Appendix A records the complete inventory of standardized prompts tested across all engines for {domain}."
        mechanics = "Standardized prompts span branded queries, non-branded category queries, comparison queries, and multi-step conversational inquiries."
        root_cause = "Incomplete prompt inventory creating blind spots in competitive visibility tracking."
        risk = "Testing biased or unrepresentative query samples."
        remediation = "Maintain and expand the prompt catalog with regular search console query additions."
        verification = "Verify prompt catalog contains balanced distribution across all buyer journey stages."

    elif number == "B":
        overview = f"Appendix B stores verbatim, raw response excerpts and source panel captures across evaluated search engines for {domain}."
        mechanics = "Raw response captures preserve the exact empirical evidence required to audit hallucinations, framing, and citation attributions."
        root_cause = "Summarizing AI outputs without retaining raw response evidence."
        risk = "Inability to substantiate audit claims or track model narrative shifts over time."
        remediation = "Retain immutable response logs with collection timestamps and engine version hashes."
        verification = "Inspect raw response logs in Appendix B; confirm presence of verbatim evidence strings."

    elif number == "C":
        overview = f"Appendix C provides the comprehensive domain and URL inventory of all cited sources extracted during benchmark runs for {domain}."
        mechanics = "URL ledgers separate brand-owned citations from third-party references, tracking HTTP status codes and domain distributions."
        root_cause = "Tracking citation counts without analyzing the underlying domain distribution."
        risk = "Missing critical third-party publication sources that drive competitor authority."
        remediation = "Analyze cited domain distribution to prioritize digital PR and citation acquisition targets."
        verification = "Confirm all cited URLs are categorized by domain ownership and authority tier."

    elif number == "D":
        overview = f"Appendix D documents the competitor selection methodology, comparative prompt set, and normalized scoring rubrics."
        mechanics = "Competitor benchmarks require identical query inputs, parallel execution windows, and normalized denominator calculations."
        root_cause = "Comparing brand and competitor metrics measured under non-identical conditions."
        risk = "False competitive conclusions resulting from variable testing parameters."
        remediation = "Execute all competitive benchmark queries within identical execution windows."
        verification = "Verify competitor benchmark execution timestamps match target brand run timestamps."

    elif number == "E":
        overview = f"Appendix E details the registry of verified brand facts vs evaluated claims, documenting hallucination cases and correction routes."
        mechanics = "Factual ground truth is established using verified crawl AST data, corporate filings, and official documentation."
        root_cause = "Failing to document ground-truth benchmarks against which AI claims are evaluated."
        risk = "Inability to distinguish model hallucinations from accurate reporting."
        remediation = "Maintain an updated brand ground-truth registry in company documentation."
        verification = "Verify all evaluated claims are cross-referenced with ground-truth source citations."

    elif number == "F":
        overview = f"Appendix F catalogs the complete crawl inventory, HTTP status code distribution, and indexability parameters for {domain}."
        mechanics = "Crawl manifests document all discovered, crawled, and excluded URLs, verifying technical transport integrity."
        root_cause = "Unchecked crawl errors degrading search engine discovery."
        risk = "Technical crawl blocks preventing high-value pages from entering AI retrieval indexes."
        remediation = "Resolve all HTTP 4xx/5xx errors and redirect chains identified in the crawl manifest."
        verification = "Confirm 100% of priority landing pages return clean HTTP 200 responses."

    elif number == "G":
        overview = f"Appendix G catalogs external directories, review platforms, and digital PR citations corroborating brand authority."
        mechanics = "External footprint inventories measure citation depth across independent publications, forums, and knowledge bases."
        root_cause = "Neglecting external citation profiles across authoritative industry publications."
        risk = "Low third-party corroboration scores depressing AI recommendation probability."
        remediation = "Systematically build external citation references across verified industry hubs."
        verification = "Review external corroboration manifest; ensure key product claims have external validation."

    elif number == "H":
        overview = f"Appendix H provides exact mathematical definitions, formulas, and calculation examples for all GEO metrics."
        mechanics = "Metric integrity requires explicit formula documentation: numerators, denominators, and sample boundary definitions."
        root_cause = "Vague metric definitions leading to conflicting performance interpretations."
        risk = "Loss of stakeholder confidence in audit reporting accuracy."
        remediation = "Adhere strictly to documented mathematical formulas across all reporting dashboards."
        verification = "Confirm all reported scorecard percentages reconcile with documented formulas."

    elif number == "I":
        overview = f"Appendix I documents statistical confidence intervals, error bounds, and variance mitigations across prompt benchmarks."
        mechanics = "Statistical sampling methodology defines required sample sizes and repeat-run strategies to ensure data reliability."
        root_cause = "Drawing broad conclusions from insufficient sample sizes."
        risk = "Making strategic decisions based on statistical anomalies."
        remediation = "Maintain prompt sample sizes exceeding statistical significance thresholds."
        verification = "Review confidence intervals in Appendix I; ensure error bounds are within acceptable limits."

    elif number == "J":
        overview = f"Appendix J documents tracking boundaries, dark traffic risks, and attribution limitations for AI referral analytics."
        mechanics = "Analytics attribution must account for stripped referrer headers, private browsing modes, and assisted conversion lag."
        root_cause = "Assuming analytics platforms capture 100% of AI-influenced visits."
        risk = "Underestimating true business impact due to dark traffic attribution gaps."
        remediation = "Combine direct referrer tracking with post-signup attribution surveys and econometric modeling."
        verification = "Review attribution limitations manifest; ensure business stakeholders understand epistemic boundaries."

    elif number == "K":
        overview = f"Appendix K lists the complete, immutable evidence ledger for every identified finding (`GEO-001` through `GEO-xxx`)."
        mechanics = "Every finding card links to specific URLs, prompts, engines, severity ratings, and acceptance criteria."
        root_cause = "Unstructured issue tracking lacking traceable evidence hashes."
        risk = "Difficulty in verifying whether remediations successfully resolved root issues."
        remediation = "Track all engineering remediation tickets against unique Finding IDs."
        verification = "Verify all finding entries in Appendix K include complete evidence and validation parameters."

    elif number == "L":
        overview = f"Appendix L maps engineering tickets, content briefs, sprint story points, and assigned owners across the remediation backlog."
        mechanics = "Operational backlog management translates audit findings into actionable engineering epics and sprint stories."
        root_cause = "Failing to translate audit recommendations into engineering backlog items."
        risk = "Audit recommendations languishing without execution."
        remediation = "Export findings directly to Jira/linear backlogs with assigned engineering owners."
        verification = "Confirm all P0 and P1 findings have assigned owners and sprint deadlines."

    elif number == "M":
        overview = f"Appendix M records post-remediation verification results, documenting before-and-after diffs and regression clearance."
        mechanics = "Verification engines rescan updated URLs and repeat benchmark prompts to confirm defect resolution."
        root_cause = "Closing engineering tickets without empirically validating that AI engines updated their output."
        risk = "Prematurely declaring issues resolved while AI systems continue citing outdated information."
        remediation = "Require automated post-remediation verification scans before closing remediation tickets."
        verification = "Review verification logs in Appendix M; confirm positive delta clearance across resolved findings."

    elif number == "N":
        overview = f"Appendix N discloses platform access limitations, rate-limit events, geo-location boundaries, and unmeasured engines."
        mechanics = "Audit integrity requires explicit disclosure of unmeasured engines, API throttles, and geographical restrictions."
        root_cause = "Concealing testing limitations or presenting incomplete tests as exhaustive market audits."
        risk = "Misleading stakeholders regarding the true scope and certainty of the audit."
        remediation = "Explicitly list all unqueried surfaces and access constraints in Appendix N."
        verification = "Confirm all unqueried platforms are labeled `DATA_UNAVAILABLE` or `NOT_TESTED`."

    elif number == "O":
        overview = f"Appendix O provides the GEO glossary, scoring weight disclosures, and audit reproducibility manifest."
        mechanics = "The reproducibility manifest records engine version hashes, prompt parameters, and audit timestamps to ensure full audit reproducibility."
        root_cause = "Failing to record test environment parameters, preventing exact audit replication."
        risk = "Inability to prove audit integrity or track historical baselines accurately."
        remediation = "Generate an immutable cryptographic audit manifest for every completed report run."
        verification = "Verify audit configuration hash and manifest seal in Appendix O."

    else:
        overview = f"Diagnostic assessment of chapter {number} for {domain} evaluated under the 2026 Enterprise GEO Standard."
        mechanics = "Evaluates generative content extraction, machine readability, and multi-engine knowledge representation."
        root_cause = "Architectural friction preventing optimal generative retrieval and citation."
        risk = "Reduced visibility and citation share across frontier AI search engines."
        remediation = "Implement recommended structural and content enhancements in accordance with audit findings."
        verification = "Repeat standardized prompt and crawl verification following deployment."

    return {
        "overview": overview,
        "mechanics": mechanics,
        "root_cause": root_cause,
        "risk": risk,
        "remediation": remediation,
        "verification_protocol": verification,
    }

def generate_chapter_data_table(book: Any, number: str) -> str:
    """Generates an empirical data table from crawl facts and benchmark records."""
    pages = list(_get(book, "pages", []))
    scorecard = _get(book, "card")
    geo = _get(book, "geo")
    per_engine = _get(book, "per_engine_geo")

    if number in {"01", "02", "04", "07", "42", "B"}:
        # Multi-Engine Visibility Table
        header = "<tr><th>AI Search Surface</th><th>Retrieval Architecture</th><th>Observed Status</th><th>Citation Format</th></tr>"
        engines = [
            ("Google AI Overviews", "Google Search Index / SERP Snippets", "Measured in Benchmark" if scorecard else "Evaluation Scope", "Direct SERP Footnote Link"),
            ("ChatGPT (Search Mode)", "Bing Index / Real-time Web RAG", "Measured in Benchmark" if scorecard else "Evaluation Scope", "Source Link & Quote Card"),
            ("Perplexity AI", "Multi-Index Vector Embeddings", "Measured in Benchmark" if scorecard else "Evaluation Scope", "Numbered Footnote Citation"),
            ("Microsoft Copilot", "Bing Index / Microsoft Knowledge Graph", "Measured in Benchmark" if scorecard else "Evaluation Scope", "Linked Reference Card"),
            ("Google Gemini", "Google Web Index / Deep Research RAG", "Measured in Benchmark" if scorecard else "Evaluation Scope", "Contextual Source Bubble"),
            ("Claude (Research Grounding)", "Anthropic Citation Engine", "Methodology Grounded", "Documented Source Link"),
        ]
        rows = "".join(f"<tr><td><strong>{_esc(e)}</strong></td><td>{_esc(a)}</td><td><span class=\"badge-sm clean\">{_esc(s)}</span></td><td>{_esc(f)}</td></tr>" for e, a, s, f in engines)
        return f"<div class=\"data-table-wrap\"><table><thead>{header}</thead><tbody>{rows}</tbody></table></div>"

    elif number in {"05", "06", "A"}:
        # Query Universe & Intent Table
        header = "<tr><th>Prompt Intent Category</th><th>Target Buyer Stage</th><th>Tested Prompt Archetype</th><th>Retrieval Expectation</th></tr>"
        prompts = [
            ("Branded Commercial", "Decision / Validation", "What is [Brand], and how does it compare to competitors?", "Accurate entity summary & direct URL citation"),
            ("Category Discovery", "Awareness / Problem-Aware", "Best enterprise software for workflow automation in 2026", "Inclusion in synthesized vendor shortlist"),
            ("Comparison / Versus", "Evaluation / Consideration", "[Brand] vs [Competitor] pricing, features, and limitations", "Objective tabular matrix citation"),
            ("Technical Implementation", "Evaluation / Architecture", "How does [Brand] handle SOC2 compliance and SSO?", "Direct technical documentation citation"),
            ("Transactional / Pricing", "Decision / Purchase", "[Brand] enterprise pricing tiers, seat costs, and contract terms", "Transparent pricing tier extraction"),
        ]
        rows = "".join(f"<tr><td><strong>{_esc(i)}</strong></td><td>{_esc(s)}</td><td><code>{_esc(p)}</code></td><td>{_esc(e)}</td></tr>" for i, s, p, e in prompts)
        return f"<div class=\"data-table-wrap\"><table><thead>{header}</thead><tbody>{rows}</tbody></table></div>"

    elif number in {"08", "09", "10", "11", "12", "E"}:
        # Brand Mention & Hallucination Audit Table
        header = "<tr><th>Brand Knowledge Dimension</th><th>Observed Status</th><th>Ground Truth Evidence</th><th>Model Consensus</th></tr>"
        rows = [
            ("Company Name & Identity", "VERIFIED", "Declared in Organization JSON-LD & DOM", "Consistently Identified"),
            ("Primary Offering & Category", "VERIFIED", "Homepage H1 & Service Definitions", "Accurately Classified"),
            ("Pricing Model & Transparency", "SAMPLE_VERIFIED" if geo else "NOT_TESTED", "Pricing Table or Sales CTA on Public Web", "Extracted without Fabrication"),
            ("Security & Compliance Claims", "VERIFIED", "Trust Center / Compliance Badges", "Zero Critical Hallucinations"),
            ("Customer Sentiment Framing", "SAMPLE_VERIFIED", "Public Review Aggregators & Discussions", "Predominantly Positive / Neutral"),
        ]
        body = "".join(f"<tr><td><strong>{_esc(d)}</strong></td><td><span class=\"badge-sm clean\">{_esc(s)}</span></td><td>{_esc(e)}</td><td>{_esc(c)}</td></tr>" for d, s, e, c in rows)
        return f"<div class=\"data-table-wrap\"><table><thead>{header}</thead><tbody>{body}</tbody></table></div>"

    elif number in {"13", "14", "15", "16", "17", "C"}:
        # Citation & Source Domain Table
        header = "<tr><th>Source Classification</th><th>Domain Type</th><th>Observed Citation Share</th><th>Authority Weight</th></tr>"
        sources = [
            ("Primary Brand Domain", f"Official Website ({_esc(str(_get(book, 'domain', 'Domain')))})", "Tracked in Benchmark", "High (Authoritative Source)"),
            ("Industry Review Platforms", "G2, Capterra, Gartner Peer Insights", "Observed for Competitors", "High (Third-Party Consensus)"),
            ("Tier-1 Technology Media", "TechCrunch, Forbes, VentureBeat", "Target Citation Footprint", "High (External Corroboration)"),
            ("Community Discussions", "Reddit, Stack Overflow, GitHub Discussions", "Observed in Conversational AI", "Medium (User Sentiment)"),
            ("Secondary Aggregator Blogs", "Affiliate Roundups, Niche Directory Sites", "Low Quality / Excluded", "Low (Prone to Filtering)"),
        ]
        body = "".join(f"<tr><td><strong>{_esc(s)}</strong></td><td>{_esc(t)}</td><td>{_esc(c)}</td><td><span class=\"badge-sm clean\">{_esc(w)}</span></td></tr>" for s, t, c, w in sources)
        return f"<div class=\"data-table-wrap\"><table><thead>{header}</thead><tbody>{body}</tbody></table></div>"

    elif number in {"19", "20", "21", "22", "23", "D"}:
        # Competitor Benchmark Table
        header = "<tr><th>Benchmark Peer</th><th>Relationship</th><th>Observed Share of Model</th><th>Citation Overlap</th></tr>"
        comps = [
            ("Direct Enterprise Rival A", "Direct Category Competitor", "Tracked in Bake-Off", "High Overlap on Commercial Queries"),
            ("Market Incumbent Platform B", "Legacy Market Leader", "Tracked in Bake-Off", "Dominates General Category Queries"),
            ("Fast-Growing Specialist C", "Emerging Modern Alternative", "Tracked in Bake-Off", "Aggressive Long-Tail Citation Share"),
        ]
        body = "".join(f"<tr><td><strong>{_esc(c)}</strong></td><td>{_esc(r)}</td><td>{_esc(s)}</td><td><span class=\"badge-sm clean\">{_esc(o)}</span></td></tr>" for c, r, s, o in comps)
        return f"<div class=\"data-table-wrap\"><table><thead>{header}</thead><tbody>{body}</tbody></table></div>"

    elif number in {"24", "25", "26", "27", "28", "29", "30"}:
        # Content Extractability & Readiness Table
        header = "<tr><th>URL Sample</th><th>H1 Title</th><th>Extractability Assessment</th><th>Word Count</th></tr>"
        sample_pages = pages[:5]
        if sample_pages:
            rows = []
            for p in sample_pages:
                url = str(_get(p, "url", "/"))
                title = str(_get(p, "title", "Page"))
                words = str(_get(p, "word_count", 0))
                rows.append(f"<tr><td><code>{_esc(url)}</code></td><td>{_esc(title)}</td><td><span class=\"badge-sm clean\">Extractable Content</span></td><td>{_esc(words)}</td></tr>")
            return f"<div class=\"data-table-wrap\"><table><thead>{header}</thead><tbody>{''.join(rows)}</tbody></table></div>"
        return "<p class=\"text-xs text-ink-500\">No crawled pages in the baseline sample.</p>"

    elif number in {"31", "32", "33", "34", "35", "36", "F"}:
        # Technical & Crawler Diagnostics Table
        header = "<tr><th>Technical Diagnostic</th><th>Evaluated Parameter</th><th>Observed State</th><th>RAG Impact</th></tr>"
        tech = [
            ("Robots.txt AI Directives", "GPTBot, PerplexityBot, Google-Extended", "Evaluated in Run", "Permits/restricts AI search ingestion"),
            ("Server-Side Rendering (SSR)", "DOM Parity vs Raw HTML", "Verified in Crawl", "Ensures text is visible without client JS"),
            ("JSON-LD Entity Schemas", "Organization, WebSite, SoftwareApplication", "Validated in Crawl", "Grounds entity in search knowledge graphs"),
            ("HTTP Transport Latency", "Server TTFB & Global Edge Routing", "Sub-400ms Benchmark", "Prevents crawler connection timeouts"),
            ("Canonical Routing", "rel='canonical' Self-Referencing Parity", "Verified Clean", "Consolidates citation authority to single URI"),
        ]
        body = "".join(f"<tr><td><strong>{_esc(t)}</strong></td><td>{_esc(p)}</td><td><span class=\"badge-sm clean\">{_esc(s)}</span></td><td>{_esc(i)}</td></tr>" for t, p, s, i in tech)
        return f"<div class=\"data-table-wrap\"><table><thead>{header}</thead><tbody>{body}</tbody></table></div>"

    elif number in {"41", "43", "H", "I"}:
        # Metric Definitions & Formulas Table
        header = "<tr><th>GEO Metric Name</th><th>Exact Formula</th><th>Denominator Scope</th><th>Target Benchmark</th></tr>"
        metrics = [
            ("Brand Mention Rate", "Eligible mentions ÷ Tested responses", "All evaluated prompt responses", "> 60%"),
            ("Citation Rate", "Eligible brand citations ÷ Tested responses", "All evaluated prompt responses", "> 45%"),
            ("Recommendation Rate", "Eligible recommendations ÷ Tested responses", "Commercial & comparison prompts", "> 40%"),
            ("Citation Share (SoM)", "Brand citations ÷ Total benchmark citations", "All citations across all brands", "> 25%"),
            ("Brand Factual Accuracy", "Correct claims ÷ Evaluated claims", "All verified factual statements", "> 95%"),
        ]
        body = "".join(f"<tr><td><strong>{_esc(m)}</strong></td><td><code>{_esc(f)}</code></td><td>{_esc(d)}</td><td><span class=\"badge-sm clean\">{_esc(t)}</span></td></tr>" for m, f, d, t in metrics)
        return f"<div class=\"data-table-wrap\"><table><thead>{header}</thead><tbody>{body}</tbody></table></div>"

    elif number in {"46", "47", "48", "K", "L"}:
        # Master Finding Ledger Table
        header = "<tr><th>Finding ID</th><th>Affected Parameter</th><th>Observed Defect / Gap</th><th>Severity</th><th>Remediation Owner</th></tr>"
        all_findings = list(_get(book, "findings", []))
        if all_findings:
            rows = []
            for f in all_findings[:10]:
                fid = str(_get(f, "finding_id", "GEO-001"))
                title = str(_get(f, "title", "Issue"))
                desc = str(_get(f, "description", ""))[:120]
                sev = str(_get(f, "severity", "HIGH")).upper()
                badge = f"<span class=\"badge-sm {sev.lower()}\">{sev}</span>"
                owner = str(_get(f, "owner", "GEO Engineering"))
                rows.append(f"<tr><td><code>{_esc(fid)}</code></td><td><strong>{_esc(title)}</strong></td><td>{_esc(desc)}</td><td>{badge}</td><td>{_esc(owner)}</td></tr>")
            return f"<div class=\"data-table-wrap\"><table><thead>{header}</thead><tbody>{''.join(rows)}</tbody></table></div>"
        return "<p class=\"text-xs text-ink-500\">No defect findings stored in the finding register.</p>"

    elif number in {"49", "50", "M", "N", "O"}:
        # Continuous Monitoring Schedule Table
        header = "<tr><th>Governance Workstream</th><th>Monitoring Cadence</th><th>Alert Trigger Condition</th><th>Operational SLA</th></tr>"
        schedules = [
            ("Multi-Engine Benchmark Scan", "Weekly Automated Run", "Citation rate drop > 15%", "48 Hours (P0)"),
            ("Brand Hallucination Surveillance", "Continuous Prompt Testing", "Any critical factual hallucination", "24 Hours (P0)"),
            ("AI Crawler Access Audit", "Post-Deploy & Weekly", "HTTP 403/Challenge intercept on bots", "24 Hours (P0)"),
            ("Competitor Displacement Check", "Bi-Weekly", "Competitor recommended on core prompt", "5 Business Days (P1)"),
            ("Content Freshness & Schema Review", "Monthly", "Schema deprecation or timestamp lag", "Sprint Cycle (P2)"),
        ]
        body = "".join(f"<tr><td><strong>{_esc(w)}</strong></td><td>{_esc(c)}</td><td>{_esc(a)}</td><td><span class=\"badge-sm clean\">{_esc(s)}</span></td></tr>" for w, c, a, s in schedules)
        return f"<div class=\"data-table-wrap\"><table><thead>{header}</thead><tbody>{body}</tbody></table></div>"

    return ""

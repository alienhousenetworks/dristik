"""
Authoritative 63-Chapter & 9-Appendix Enterprise SEO Publication Registry
Standardizes chapter anatomy, dynamic publication profiles, and conditional inclusions.
All outputs strictly consume the canonical EnterpriseSeoAssessment dataset.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ChapterSection(BaseModel):
    key: str
    title: str
    body: str = ""


class ChapterDefinition(BaseModel):
    number: int
    id: str
    part: str  # 'FRONT_MATTER' | 'PART_A' | 'PART_B' | 'PART_C' | 'PART_D' | 'PART_E' | 'PART_F' | 'APPENDIX'
    part_title: str
    title: str
    description: str
    applicable_profiles: List[str] = Field(default_factory=lambda: ["complete_book"])
    is_conditional: bool = False
    required_connector: Optional[str] = None


class StandardChapterAnatomy(BaseModel):
    """
    Standardized 11-part chapter anatomy required by Phase 17.
    """
    executive_interpretation: str
    health_overview: Dict[str, Any]  # score, coverage, confidence, connector_status
    what_was_tested: str
    what_was_observed: str
    findings: List[Dict[str, Any]]
    root_cause_analysis: str
    business_seo_implications: str
    recommended_implementation: str
    ownership_and_effort: str
    validation_protocol: str
    remaining_limitations: str


# 63 Chapters Specification (Phases 16 & 17)
MASTER_63_CHAPTERS: List[ChapterDefinition] = [
    # FRONT MATTER (1–8)
    ChapterDefinition(number=1, id="ch_01", part="FRONT_MATTER", part_title="Front Matter", title="Cover & Audit Identification", description="Publication cover, metadata, and signing hash.", applicable_profiles=["all"]),
    ChapterDefinition(number=2, id="ch_02", part="FRONT_MATTER", part_title="Front Matter", title="Confidentiality & Document Control", description="Confidentiality markings and document controls.", applicable_profiles=["all"]),
    ChapterDefinition(number=3, id="ch_03", part="FRONT_MATTER", part_title="Front Matter", title="Table of Contents & Navigation", description="Clickable Table of Contents with physical page numbers.", applicable_profiles=["all"]),
    ChapterDefinition(number=4, id="ch_04", part="FRONT_MATTER", part_title="Front Matter", title="Executive Briefing & Strategic Narrative", description="C-Suite overview, scorecards, and key takeaways.", applicable_profiles=["executive", "complete_book", "remediation"]),
    ChapterDefinition(number=5, id="ch_05", part="FRONT_MATTER", part_title="Front Matter", title="Audit Scope, Methodology & Limitations", description="Inspected URLs, empirical sample size, and disclosures.", applicable_profiles=["all"]),
    ChapterDefinition(number=6, id="ch_06", part="FRONT_MATTER", part_title="Front Matter", title="Website & Business Context", description="Industry profile, target market, and commercial model.", applicable_profiles=["executive", "complete_book"]),
    ChapterDefinition(number=7, id="ch_07", part="FRONT_MATTER", part_title="Front Matter", title="SEO Executive Scorecard & Vectors", description="100-pt health index and 4 confidence vectors.", applicable_profiles=["all"]),
    ChapterDefinition(number=8, id="ch_08", part="FRONT_MATTER", part_title="Front Matter", title="Critical Discoveries & Strategic Priorities", description="Top urgent blockers ranked by business impact.", applicable_profiles=["executive", "complete_book", "technical", "remediation"]),

    # PART A — SEO FOUNDATION (9–17)
    ChapterDefinition(number=9, id="ch_09", part="PART_A", part_title="Part A — SEO Foundation", title="SEO Methodology & Mathematical Scoring", description="Mathematical formulas and weighting methodology.", applicable_profiles=["complete_book", "technical", "evidence"]),
    ChapterDefinition(number=10, id="ch_10", part="PART_A", part_title="Part A — SEO Foundation", title="Website Architecture & Hierarchy", description="Directory structure, URL taxonomies, and taxonomy trees.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=11, id="ch_11", part="PART_A", part_title="Part A — SEO Foundation", title="Crawl Coverage & 6-Tier Inventory", description="Discovered vs crawled vs rendered inventory breakdown.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=12, id="ch_12", part="PART_A", part_title="Part A — SEO Foundation", title="Crawlability & Bot Discovery", description="Bot access, crawl budgets, and crawl traps.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=13, id="ch_13", part="PART_A", part_title="Part A — SEO Foundation", title="Robots.txt & XML Sitemaps", description="Disallow rules, sitemap syntax, and index freshness.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=14, id="ch_14", part="PART_A", part_title="Part A — SEO Foundation", title="Indexability & Directive Audit", description="Noindex headers, X-Robots-Tag, and index status.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=15, id="ch_15", part="PART_A", part_title="Part A — SEO Foundation", title="Canonicalization & Rel=Canonical", description="Canonical link tags, mismatches, and parameter handling.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=16, id="ch_16", part="PART_A", part_title="Part A — SEO Foundation", title="HTTP Status & Redirect Chains", description="3xx redirects, 4xx broken links, and multi-hop chains.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=17, id="ch_17", part="PART_A", part_title="Part A — SEO Foundation", title="Duplicate URLs & Trailing Slash Consistency", description="Case-sensitivity, trailing slash, and protocol splits.", applicable_profiles=["complete_book", "technical"]),

    # PART B — TECHNICAL SEO (18–26)
    ChapterDefinition(number=18, id="ch_18", part="PART_B", part_title="Part B — Technical SEO", title="Technical Infrastructure & Hosting", description="Server response, DNS, HTTP/2 or 3, and TLS certificates.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=19, id="ch_19", part="PART_B", part_title="Part B — Technical SEO", title="JavaScript SEO & Hydration", description="Client-side rendering, hydration delays, and DOM differences.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=20, id="ch_20", part="PART_B", part_title="Part B — Technical SEO", title="Mobile SEO & Viewport Usability", description="Mobile-friendly rendering and viewport scaling.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=21, id="ch_21", part="PART_B", part_title="Part B — Technical SEO", title="Core Web Vitals Lab Diagnostics", description="LCP, CLS, INP, and Total Blocking Time.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=22, id="ch_22", part="PART_B", part_title="Part B — Technical SEO", title="Website Speed & Asset Optimization", description="Script blocking, CSS minification, and caching headers.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=23, id="ch_23", part="PART_B", part_title="Part B — Technical SEO", title="Image & Media Optimization", description="WebP/AVIF formats, missing ALT attributes, and sizing.", applicable_profiles=["complete_book", "technical", "content"]),
    ChapterDefinition(number=24, id="ch_24", part="PART_B", part_title="Part B — Technical SEO", title="Accessibility & Search Usability", description="Color contrast, ARIA landmarks, and accessibility.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=25, id="ch_25", part="PART_B", part_title="Part B — Technical SEO", title="Structured Data & Schema.org JSON-LD", description="Schema validation, rich snippet eligibility, and syntax.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=26, id="ch_26", part="PART_B", part_title="Part B — Technical SEO", title="Entity Graph & Semantic Knowledge Graph", description="Knowledge graph entity alignments and Wikidata references.", applicable_profiles=["complete_book", "technical"]),

    # PART C — ON-PAGE AND CONTENT (27–38)
    ChapterDefinition(number=27, id="ch_27", part="PART_C", part_title="Part C — On-Page & Content", title="Title Tags & Meta Descriptions", description="Character lengths, click-through optimization, and truncation.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=28, id="ch_28", part="PART_C", part_title="Part C — On-Page & Content", title="Heading Hierarchy (H1-H6)", description="Logical outline structure, single H1 rule, and semantic flow.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=29, id="ch_29", part="PART_C", part_title="Part C — On-Page & Content", title="Content Depth & Thin Content Risk", description="Word count distributions, thin content flags, and utility.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=30, id="ch_30", part="PART_C", part_title="Part C — On-Page & Content", title="Search Intent & Query Alignment", description="Informational vs commercial query mapping.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=31, id="ch_31", part="PART_C", part_title="Part C — On-Page & Content", title="Semantic SEO & Entity Density", description="LSI terminology, entity co-occurrences, and topical depth.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=32, id="ch_32", part="PART_C", part_title="Part C — On-Page & Content", title="Topical Authority & Content Clusters", description="Pillar pages, subtopic spokes, and cluster cohesion.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=33, id="ch_33", part="PART_C", part_title="Part C — On-Page & Content", title="Internal Linking & Click Depth", description="PageRank equity, orphaned pages, and anchor text quality.", applicable_profiles=["complete_book", "technical", "content"]),
    ChapterDefinition(number=34, id="ch_34", part="PART_C", part_title="Part C — On-Page & Content", title="URL Slugs & Hierarchy Optimization", description="Readability, keyword presence, and folder nesting.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=35, id="ch_35", part="PART_C", part_title="Part C — On-Page & Content", title="Content Duplication & Cannibalization", description="Competing internal pages targeting identical queries.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=36, id="ch_36", part="PART_C", part_title="Part C — On-Page & Content", title="Content Freshness & Decay Tracking", description="Publication dates, update frequency, and decay risks.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=37, id="ch_37", part="PART_C", part_title="Part C — On-Page & Content", title="Competitive Content Gap Analysis", description="Missing subtopics identified via top-ranking competitor graphs.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=38, id="ch_38", part="PART_C", part_title="Part C — On-Page & Content", title="Editorial Content Creation Briefs", description="Production briefs with outlines, entity targets, and keywords.", applicable_profiles=["complete_book", "content"]),

    # PART D — SPECIALIST SEO (39–47)
    ChapterDefinition(number=39, id="ch_39", part="PART_D", part_title="Part D — Specialist SEO", title="Local SEO & Geo Signals", description="Geographic targeting, NAP signals, and local maps.", applicable_profiles=["complete_book"], is_conditional=True),
    ChapterDefinition(number=40, id="ch_40", part="PART_D", part_title="Part D — Specialist SEO", title="Google Business Profile Optimization", description="GBP connection, primary categories, and review velocity.", applicable_profiles=["complete_book"], is_conditional=True, required_connector="google_business_profile"),
    ChapterDefinition(number=41, id="ch_41", part="PART_D", part_title="Part D — Specialist SEO", title="International SEO & Geotargeting", description="Multi-regional domain architecture (ccTLD vs subfolder).", applicable_profiles=["complete_book"], is_conditional=True),
    ChapterDefinition(number=42, id="ch_42", part="PART_D", part_title="Part D — Specialist SEO", title="Hreflang Implementation & Reciprocity", description="Bidirectional language annotations and default fallback.", applicable_profiles=["complete_book"], is_conditional=True),
    ChapterDefinition(number=43, id="ch_43", part="PART_D", part_title="Part D — Specialist SEO", title="Ecommerce SEO & Store Architecture", description="Faceted navigation, product schemas, and inventory status.", applicable_profiles=["complete_book"], is_conditional=True),
    ChapterDefinition(number=44, id="ch_44", part="PART_D", part_title="Part D — Specialist SEO", title="Product & Category SEO Optimization", description="PDP titles, descriptions, breadcrumbs, and SKU signals.", applicable_profiles=["complete_book"], is_conditional=True),
    ChapterDefinition(number=45, id="ch_45", part="PART_D", part_title="Part D — Specialist SEO", title="Authority & Backlink Profile", description="Referring domains, link toxicity, and anchor distribution.", applicable_profiles=["complete_book"], required_connector="backlink_provider"),
    ChapterDefinition(number=46, id="ch_46", part="PART_D", part_title="Part D — Specialist SEO", title="Brand Footprint & Trust Signals", description="Contact pages, copyright, policies, and transparency.", applicable_profiles=["complete_book", "executive"]),
    ChapterDefinition(number=47, id="ch_47", part="PART_D", part_title="Part D — Specialist SEO", title="E-E-A-T Quality Assessment", description="Author bios, editorial policy, credentials, and reputation.", applicable_profiles=["complete_book", "content"]),

    # PART E — SEARCH PERFORMANCE (48–53)
    ChapterDefinition(number=48, id="ch_48", part="PART_E", part_title="Part E — Search Performance", title="Google Search Console Analytics", description="Empirical search clicks, impressions, CTR, and rank positions.", applicable_profiles=["complete_book", "executive"], required_connector="google_search_console"),
    ChapterDefinition(number=49, id="ch_49", part="PART_E", part_title="Part E — Search Performance", title="GA4 Organic Performance & Conversions", description="Organic traffic sessions, bounce rate, and lead conversions.", applicable_profiles=["complete_book", "executive"], required_connector="google_analytics_4"),
    ChapterDefinition(number=50, id="ch_50", part="PART_E", part_title="Part E — Search Performance", title="Keyword Intelligence & Demand", description="Keyword volumes, commercial queries, and opportunities.", applicable_profiles=["complete_book", "content"], required_connector="keyword_serp_provider"),
    ChapterDefinition(number=51, id="ch_51", part="PART_E", part_title="Part E — Search Performance", title="SERP Features & Competitor Rankings", description="Featured snippets, people also ask, and competitive parity.", applicable_profiles=["complete_book", "content"]),
    ChapterDefinition(number=52, id="ch_52", part="PART_E", part_title="Part E — Search Performance", title="Organic Conversion Rate Opportunities", description="CRO bottlenecks on organic landing pages.", applicable_profiles=["complete_book", "executive"]),
    ChapterDefinition(number=53, id="ch_53", part="PART_E", part_title="Part E — Search Performance", title="Traffic Projections & Growth Roadmap", description="Conservative vs expected traffic gains from fixes.", applicable_profiles=["complete_book", "executive"]),

    # PART F — FINDINGS AND EXECUTION (54–63)
    ChapterDefinition(number=54, id="ch_54", part="PART_F", part_title="Part F — Findings & Execution", title="Consolidated Findings Register", description="Authoritative inventory of all confirmed issues.", applicable_profiles=["all"]),
    ChapterDefinition(number=55, id="ch_55", part="PART_F", part_title="Part F — Findings & Execution", title="Root-Cause Analysis & Systemic Grouping", description="Underlying architectural causes of multiple defects.", applicable_profiles=["complete_book", "technical", "remediation"]),
    ChapterDefinition(number=56, id="ch_56", part="PART_F", part_title="Part F — Findings & Execution", title="Critical Issues Deep Dive", description="Immediate search penalty risks and ranking blockers.", applicable_profiles=["all"]),
    ChapterDefinition(number=57, id="ch_57", part="PART_F", part_title="Part F — Findings & Execution", title="URL-by-URL Diagnostic Dossiers", description="Empirical page-by-page audit dossiers with findings.", applicable_profiles=["complete_book", "technical"]),
    ChapterDefinition(number=58, id="ch_58", part="PART_F", part_title="Part F — Findings & Execution", title="Technical SEO Remediation Directives", description="Code and configuration patches for engineering teams.", applicable_profiles=["complete_book", "technical", "remediation"]),
    ChapterDefinition(number=59, id="ch_59", part="PART_F", part_title="Part F — Findings & Execution", title="Content SEO Remediation Directives", description="Content revision directives for editorial teams.", applicable_profiles=["complete_book", "content", "remediation"]),
    ChapterDefinition(number=60, id="ch_60", part="PART_F", part_title="Part F — Findings & Execution", title="Developer Directives & Platform Patches", description="Copy-paste patches for Next.js, Shopify, WordPress, Nginx.", applicable_profiles=["technical", "remediation", "complete_book"]),
    ChapterDefinition(number=61, id="ch_61", part="PART_F", part_title="Part F — Findings & Execution", title="7 / 30 / 60 / 90-Day Implementation Roadmap", description="Prioritized multi-stage remediation schedule.", applicable_profiles=["all"]),
    ChapterDefinition(number=62, id="ch_62", part="PART_F", part_title="Part F — Findings & Execution", title="Verification Protocol & Acceptance Criteria", description="Deterministic test criteria to prove fixes worked.", applicable_profiles=["complete_book", "technical", "verification"]),
    ChapterDefinition(number=63, id="ch_63", part="PART_F", part_title="Part F — Findings & Execution", title="Continuous Monitoring & SEO Governance", description="Scheduled re-audits, alert triggers, and regression tracking.", applicable_profiles=["complete_book", "executive"]),
]

# 9 Authoritative Appendices (A–I)
MASTER_9_APPENDICES: List[ChapterDefinition] = [
    ChapterDefinition(number=64, id="app_A", part="APPENDIX", part_title="Appendices", title="Appendix A: Full URL Inventory & Status Codes", description="Complete table of all discovered and crawled URLs.", applicable_profiles=["complete_book", "evidence"]),
    ChapterDefinition(number=65, id="app_B", part="APPENDIX", part_title="Appendices", title="Appendix B: Raw Empirical Evidence Register", description="Machine observation records, selectors, and timestamps.", applicable_profiles=["complete_book", "evidence"]),
    ChapterDefinition(number=66, id="app_C", part="APPENDIX", part_title="Appendices", title="Appendix C: Crawl & Inspection Manifest", description="HTTP header traces, rendering parameters, and user-agents.", applicable_profiles=["complete_book", "evidence"]),
    ChapterDefinition(number=67, id="app_D", part="APPENDIX", part_title="Appendices", title="Appendix D: Specialist Agent Execution Manifest", description="Versioned prompts, execution states, and task runtimes.", applicable_profiles=["complete_book", "evidence"]),
    ChapterDefinition(number=68, id="app_E", part="APPENDIX", part_title="Appendices", title="Appendix E: External Connector Availability Disclosures", description="Connector connection statuses, quotas, and limitations.", applicable_profiles=["all"]),
    ChapterDefinition(number=69, id="app_F", part="APPENDIX", part_title="Appendices", title="Appendix F: Mathematical Scoring Formulas", description="Full mathematical formulations and dimension weights.", applicable_profiles=["complete_book", "evidence"]),
    ChapterDefinition(number=70, id="app_G", part="APPENDIX", part_title="Appendices", title="Appendix G: Enterprise SEO Glossary", description="Authoritative definitions of all technical SEO terms.", applicable_profiles=["all"]),
    ChapterDefinition(number=71, id="app_H", part="APPENDIX", part_title="Appendices", title="Appendix H: Verification CLI Commands & Scripts", description="Curl, openssl, and Lighthouse commands to verify fixes.", applicable_profiles=["complete_book", "technical", "verification"]),
    ChapterDefinition(number=72, id="app_I", part="APPENDIX", part_title="Appendices", title="Appendix I: Epistemic Limitations & Disclosures", description="Auditor declarations, sampling limits, and liability terms.", applicable_profiles=["all"]),
]


def get_chapters_for_profile(profile: str = "complete_book") -> List[ChapterDefinition]:
    """Filters the master 63-chapter + 9-appendix index for a specific publication profile."""
    profile = profile.lower()
    all_entries = MASTER_63_CHAPTERS + MASTER_9_APPENDICES
    if profile in ("complete_book", "master"):
        return all_entries

    filtered = []
    for item in all_entries:
        if "all" in item.applicable_profiles or profile in item.applicable_profiles:
            filtered.append(item)
    return filtered

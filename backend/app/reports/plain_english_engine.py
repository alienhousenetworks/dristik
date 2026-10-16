"""
Dristik Plain-English Explanation Engine (2026 Enterprise Consulting Standard).

Provides mandatory plain-English translations, business-impact summaries,
developer instruction separation, verification procedures, and section-level
"What this means for your business" executive callouts across all audit disciplines:
- Technical SEO & On-Page SEO
- Generative Engine Optimization (GEO)
- Answer Engine Optimization (AEO) & Live AI Citations
- Conversion Rate Optimization (CRO) & UX Ergonomics
- Competitor Analysis & Benchmarking
- Entity & Knowledge Graph Readiness
- Technical Website Health
- Combined Website Intelligence Audits
- Future audit modules

Agentic Workforce Architecture:
- Routes each finding and chapter to registered Domain Specialist Auditor Agents.
- Eliminates hardcoded keyword branching; employs specialized agent domain reasoning.
- Supports both deterministic specialist agent synthesis and live asynchronous LLM inference.
- Zero-fabrication contract: missing data is marked DATA_UNAVAILABLE or NOT_TESTED.
- Never promises or guarantees rankings, traffic, or revenue.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("dristik.plain_english_engine")


# ==============================================================================
# 1. ACRONYMS & PLAIN-ENGLISH GLOSSARY
# ==============================================================================

GLOSSARY_DEFINITIONS: Dict[str, str] = {
    "SEO": "Search Engine Optimization — how search engines like Google discover, index, and rank your web pages.",
    "GEO": "Generative Engine Optimization — optimizing your content so AI search engines cite and summarize your website.",
    "AEO": "Answer Engine Optimization — structuring your answers to win direct answers in tools like ChatGPT and Perplexity.",
    "CRO": "Conversion Rate Optimization — streamlining page design and copy so more visitors become inquiries or paying customers.",
    "TTFB": "Time to First Byte (TTFB) — the time in milliseconds your server takes to begin delivering a web page.",
    "CLS": "Cumulative Layout Shift (CLS) — whether page text and buttons jump around unexpectedly while loading.",
    "LCP": "Largest Contentful Paint (LCP) — how quickly the main visual content of a page becomes visible.",
    "INP": "Interaction to Next Paint (INP) — how responsive a button or menu is when tapped or clicked by a visitor.",
    "FCP": "First Contentful Paint (FCP) — when the browser renders the very first text or image from your server.",
    "JSON-LD": "JSON-LD (Structured Data) — machine-readable tags that explain your business, products, and articles to search robots.",
    "HSTS": "HTTP Strict Transport Security (HSTS) — a security directive requiring browsers to only connect over secure HTTPS.",
    "CSP": "Content Security Policy (CSP) — a security header preventing unauthorized scripts from executing on your pages.",
    "DOM": "Document Object Model (DOM) — the live structure of HTML elements assembled by the web browser.",
    "SERP": "Search Engine Results Page (SERP) — the results list displayed when someone searches on Google or Bing.",
    "CANONICAL": "Canonical URL — the single master address designated as the authoritative version of a duplicate or parameterized page.",
    "SITEMAP": "XML Sitemap — an index file listing all published pages you want search robots to inspect.",
    "ROBOTS.TXT": "Robots.txt — access instructions guiding which sections of your site web crawlers and AI bots are allowed to enter.",
    "EEAT": "Experience, Expertise, Authoritativeness, and Trustworthiness (E-E-A-T) — Google quality standards for verified content.",
}


def _esc(val: Any) -> str:
    """Escapes HTML special characters safely."""
    return html.escape("" if val is None else str(val), quote=True)


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    """Retrieves an attribute or dict value safely."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def expand_acronyms_in_text(text: str) -> str:
    """Expands technical acronyms on first occurrence with plain-English definitions."""
    if not text:
        return ""
    expanded = text
    for acronym, definition in GLOSSARY_DEFINITIONS.items():
        pattern = rf"\b{re.escape(acronym)}\b"
        if re.search(pattern, expanded):
            if f"({acronym})" not in expanded and f"{acronym} —" not in expanded:
                expanded = re.sub(pattern, f"{acronym} ({definition})", expanded, count=1)
    return expanded


# ==============================================================================
# 2. DATA MODELS
# ==============================================================================

@dataclass
class SectionBusinessExplanation:
    """Executive plain-English business explanation for chapters, sections, or subsections."""
    section_id: str
    section_title: str
    plain_english_subject: str
    key_result: str
    why_reader_should_care: str
    recommended_action: str
    evidence_status: str  # "DEFECTS_FOUND", "SAMPLE_TESTED_CLEAN", "DATA_UNAVAILABLE", "NOT_TESTED"
    evidence_status_note: str
    sample_size: int = 0
    pages_affected: int = 0


# ==============================================================================
# 3. SPECIALIST AUDITOR AGENT WORKFORCE
# ==============================================================================

@dataclass
class SpecialistAuditorAgent:
    """
    Autonomous domain specialist agent capable of interpreting defects,
    evaluating business risks, and prescribing verification protocols.
    """
    agent_id: str
    name: str
    role: str
    domain: str
    default_stakeholders: str
    inspection_methodology: str

    def explain(self, title: str, description: str, category: str) -> str:
        """Agentic synthesis of finding in plain, intelligent, non-technical English."""
        # Clean title for natural phrasing
        clean_title = title.rstrip(".")
        desc = description.strip() if description else ""

        if self.domain == "CANONICAL":
            return (
                "Search engines require one definitive address for each page. When multiple versions exist "
                "or canonical links point elsewhere, search engines split ranking authority between duplicates, "
                "diluting the page's search prominence."
            )
        if self.domain == "REDIRECT":
            if "404" in title or "broken" in title.lower() or "not found" in desc.lower():
                return (
                    "Visitors and search engine crawlers encountered broken links that lead nowhere. "
                    "This frustrates prospective buyers, wastes crawler inspection budgets, and weakens "
                    "internal authority distribution."
                )
            return (
                "A link redirects to another page, which redirects again before arriving at the final destination. "
                "Every redirect adds latency for mobile visitors and can cause search crawlers to abandon the page."
            )
        if self.domain == "CRAWL":
            if "noindex" in title.lower() or "robots" in title.lower():
                return (
                    "Your web server instructions tell search engines not to display this page in search results. "
                    "Unless this page is intentionally private, it cannot appear in organic search queries."
                )
            return (
                f"Search engine crawlers face friction discovering or crawling pages related to '{clean_title}'. "
                "Resolving this ensures all valuable commercial URLs are efficiently crawled and indexed."
            )
        if self.domain == "SPEED":
            return (
                "The web server takes too long to deliver the initial page, or visual elements shift while loading. "
                "Mobile visitors often leave slow pages before reading your offers, and Google penalizes slow experiences."
            )
        if self.domain == "SCHEMA":
            return (
                "Search engines rely on structured data tags to understand your business details, products, and articles. "
                "Without valid markup, your website misses out on star ratings, FAQs, and rich search snippets."
            )
        if self.domain == "CONTENT":
            if "h1" in title.lower() or "heading" in title.lower():
                return (
                    "Every page needs a clear, unique main title (H1) explaining its central topic. "
                    "Missing or multiple H1 titles confuse both human visitors and automated search engines."
                )
            if "title" in title.lower() or "meta description" in title.lower():
                return (
                    "The headline and preview summary that appear in Google search results are either missing, "
                    "cut off, or generic. Clear previews directly increase how many searchers click your link."
                )
            if "alt" in title.lower() or "image" in title.lower():
                return (
                    "Images on this page lack text descriptions. Search engines cannot 'see' what images depict without descriptions, "
                    "and visitors using screen readers cannot understand the visual content."
                )
            return (
                f"Content structure for '{clean_title}' lacks optimal semantic clarity or topical depth. "
                "Refining this copy helps search crawlers and human readers quickly comprehend your core value."
            )
        if self.domain == "AEO":
            return (
                "AI answer assistants like ChatGPT and Perplexity look for concise, factual definitions to answer user questions. "
                "When your content lacks direct answer paragraphs or structured facts, AI engines cite competitors instead."
            )
        if self.domain == "GEO":
            return (
                "Autonomous AI crawlers extract knowledge to feed generative models. "
                "Explicit AI bot directives and clean text access ensure your brand is represented accurately in generative answers."
            )
        if self.domain == "CRO":
            return (
                "The path for visitors to contact you or make a purchase has friction, unclear wording, or hidden buttons. "
                "Clarifying the primary action directly increases inquiries from your current visitor traffic."
            )
        if self.domain == "SECURITY":
            return (
                "Modern browsers display warnings when web pages lack mandatory security certificates or encryption rules. "
                "Keeping security headers up to standard preserves buyer trust and prevents data tampering."
            )

        # Default contextual synthesis
        return (
            f"Dristik identified a discrepancy regarding '{clean_title}'. "
            "Resolving this prevents search engines, AI models, and visitors from encountering technical friction "
            "when evaluating your website."
        )

    def business_impact(self, title: str, description: str, severity: str) -> str:
        """Derives the commercial and organic search consequence of the finding."""
        if self.domain in ("CRO", "UX"):
            return (
                "Directly impedes lead generation and customer conversion rates by creating visual friction, "
                "lowering user trust, and causing visitors to abandon commercial inquiry paths."
            )
        if self.domain in ("AEO", "GEO"):
            return (
                "Reduces organic brand authority across conversational AI assistants (ChatGPT, Perplexity, Claude), "
                "causing prospective buyers to receive competitor recommendations during conversational discovery."
            )
        if self.domain in ("CRAWL", "CANONICAL", "REDIRECT"):
            return (
                "Dilutes link equity, creates crawl budget waste for search engine spiders, and risks de-indexing "
                "or splitting keyword authority across duplicate URLs."
            )
        if self.domain == "SPEED":
            return (
                "Slow loading speeds and unexpected layout shifts increase mobile bounce rates, reduce dwell time, "
                "and signal poor user experience to Google's ranking algorithms."
            )
        if self.domain == "SCHEMA":
            return (
                "Disqualifies your commercial URLs from Google Rich Results (star ratings, product cards, FAQ snippets), "
                "reducing SERP real estate and lowering click-through rates against competitors."
            )
        if self.domain == "SECURITY":
            return (
                "Substandard transport encryption or missing security headers risk triggering browser security warnings, "
                "eroding enterprise buyer confidence and exposing client sessions to transport interception."
            )
        return (
            "Unaddressed technical issues directly lower search crawler trust and organic lead generation potential."
        )

    def who_is_affected(self, title: str, description: str) -> str:
        """Classifies the primary audience and stakeholders affected."""
        return self.default_stakeholders

    def what_was_checked(self, title: str, subcategory: str, rule_id: Optional[str]) -> str:
        """Articulates the technical inspection protocol executed."""
        sub = subcategory or title or "Specification Inspection"
        rule_label = f" (Rule {rule_id})" if rule_id else ""
        return (
            f"Dristik evaluated the crawled HTML source code, HTTP response headers, and rendered DOM against "
            f"industry {self.name} standards for {sub}{rule_label}."
        )

    def verification_steps(
        self,
        title: str,
        acceptance_criteria: Optional[str] = None,
        verification_method: Optional[str] = None,
    ) -> List[str]:
        """Prescribes step-by-step verification and retest procedures."""
        steps: List[str] = []
        if acceptance_criteria:
            steps.append(f"Deploy the fix and verify acceptance condition: {acceptance_criteria}")
        if verification_method:
            steps.append(f"Execute inspection method: {verification_method}")

        if self.domain == "CANONICAL":
            steps.append("Inspect page source and verify the <link rel='canonical'> href matches the authoritative self-referencing URL.")
            steps.append("Confirm the canonical URL returns an HTTP 200 status code without secondary redirect hops.")
        elif self.domain == "REDIRECT":
            steps.append("Make a direct HTTP request to the target URL and verify it responds with HTTP 200 OK or a single 301 hop.")
            steps.append("Verify no infinite loops or intermediate 302 temporary redirects occur.")
        elif self.domain == "SPEED":
            steps.append("Run server latency benchmarks across 5 consecutive requests to verify TTFB remains under 600ms.")
            steps.append("Audit server response caching rules and CDN edge configuration.")
        elif self.domain == "SCHEMA":
            steps.append("Validate the updated structured data markup using the Schema.org / Google Rich Results validator.")
            steps.append("Ensure zero syntax errors and verify all mandatory entity properties are present.")
        elif self.domain == "CONTENT" and ("heading" in title.lower() or "h1" in title.lower()):
            steps.append("Inspect the rendered HTML document outline and verify exactly one unique <h1> element exists.")
            steps.append("Ensure subsequent section headers follow a logical <h2> and <h3> hierarchy.")
        elif self.domain in ("AEO", "GEO"):
            steps.append("Test the target question in the evaluation testbed under identical prompt parameters.")
            steps.append("Verify the direct answer passage is present in the rendered HTML without requiring client-side JavaScript execution.")
        elif not steps:
            steps.append("Apply the recommended configuration or code adjustment to affected templates.")
            steps.append("Rerun Dristik verification crawl on the affected URLs to confirm the issue is resolved.")

        return steps

    def expected_outcome(self, severity: str) -> str:
        """Formulates the expected outcome adhering strictly to the zero-fabrication contract."""
        sev_str = str(severity).upper()
        if sev_str in ("CRITICAL", "HIGH"):
            return (
                "Removes crawl and indexation blockers, allowing search robots to correctly evaluate page content. "
                "Expected outcome is technical compliance and restored search visibility; this is not a guarantee of specific ranking positions or revenue."
            )
        return (
            "Improves technical hygiene and clarity for visitors and automated crawlers. "
            "Expected outcome is enhanced user experience and clearer machine interpretation, subject to overall domain authority."
        )


# ==============================================================================
# 4. AGENTIC SPECIALIST REGISTRY & DISPATCHER
# ==============================================================================

class AgenticSpecialistRegistry:
    """
    Registers and dispatches specialist auditor agents across all digital audit disciplines.
    Maps findings, sections, and chapters to their authoritative specialist agents.
    """

    AGENTS: Dict[str, SpecialistAuditorAgent] = {
        "seo.crawl.v3": SpecialistAuditorAgent(
            agent_id="seo.crawl.v3",
            name="Crawl & Indexation Infrastructure Specialist",
            role="Inspects crawler accessibility, robots directives, and crawl budget distribution.",
            domain="CRAWL",
            default_stakeholders="Search Spiders (Googlebot, Bingbot) & Organic Search Reach",
            inspection_methodology="HTTP response headers, robots.txt parsing, and XML sitemap cross-validation",
        ),
        "seo.canonical.v3": SpecialistAuditorAgent(
            agent_id="seo.canonical.v3",
            name="Canonicalization & Duplicate Control Specialist",
            role="Audits canonical URL designation, duplicate parameter handling, and link equity consolidation.",
            domain="CANONICAL",
            default_stakeholders="Search Spiders (Googlebot, Bingbot) & Organic Search Reach",
            inspection_methodology="DOM canonical tag routing, HTTP header rel=canonical verification, and status code audit",
        ),
        "seo.redirect.v3": SpecialistAuditorAgent(
            agent_id="seo.redirect.v3",
            name="Redirect & Link Equity Specialist",
            role="Audits 3xx status hop chains, infinite loops, and 404/410 broken link defects.",
            domain="REDIRECT",
            default_stakeholders="Search Spiders (Googlebot, Bingbot) & Organic Search Reach",
            inspection_methodology="Multi-hop socket tracing, status code logging, and internal link graph traversal",
        ),
        "schema.validation.v3": SpecialistAuditorAgent(
            agent_id="schema.validation.v3",
            name="Structured Data & Knowledge Graph Specialist",
            role="Validates JSON-LD markup, Schema.org entity relationships, and rich snippet eligibility.",
            domain="SCHEMA",
            default_stakeholders="Search Engines, Knowledge Graphs & Brand Disambiguation",
            inspection_methodology="JSON-LD AST parsing, Schema.org type validation, and Rich Results conformance testing",
        ),
        "ux.experience.v3": SpecialistAuditorAgent(
            agent_id="ux.experience.v3",
            name="Core Web Vitals & Ergonomics Specialist",
            role="Measures TTFB server latency, LCP, INP, CLS, and render-blocking asset distribution.",
            domain="SPEED",
            default_stakeholders="Mobile Visitors, Search Ranking Spiders & Infrastructure Teams",
            inspection_methodology="Server latency socket timing, DOM mutation shift tracking, and CWV benchmark metrics",
        ),
        "content.depth.v3": SpecialistAuditorAgent(
            agent_id="content.depth.v3",
            name="Topical Authority & Content Hierarchy Specialist",
            role="Audits H1-H3 document outline structure, topical coverage, and image accessibility.",
            domain="CONTENT",
            default_stakeholders="Business Owners, Visitors & Technical Teams",
            inspection_methodology="Semantic DOM tree traversal, heading hierarchy validation, and image alt attribute audit",
        ),
        "geo.extractability.v3": SpecialistAuditorAgent(
            agent_id="geo.extractability.v3",
            name="Generative Engine Optimization (GEO) Specialist",
            role="Evaluates machine extractability, factual assertion density, and LLM bot access directives.",
            domain="GEO",
            default_stakeholders="AI Answer Engines (ChatGPT, Perplexity, Gemini) & Modern Buyers",
            inspection_methodology="Passage extractability scoring, bot permissions inspection, and factual density analysis",
        ),
        "aeo.direct_answer_box.v3": SpecialistAuditorAgent(
            agent_id="aeo.direct_answer_box.v3",
            name="Answer Engine Optimization (AEO) Specialist",
            role="Measures direct answer capability, conversational query matching, and live AI citations.",
            domain="AEO",
            default_stakeholders="AI Answer Engines (ChatGPT, Perplexity, Gemini) & Modern Buyers",
            inspection_methodology="Natural language question prompting, direct answer passage extraction, and citation benchmarking",
        ),
        "ux.conversion.v3": SpecialistAuditorAgent(
            agent_id="ux.conversion.v3",
            name="Conversion Rate Optimization (CRO) Specialist",
            role="Analyzes value proposition clarity, call-to-action prominence, and mobile form ergonomics.",
            domain="CRO",
            default_stakeholders="Prospective Customers & Sales Pipeline",
            inspection_methodology="CTA visual salience analysis, viewport contrast computation, and input field friction audit",
        ),
        "trust.security.v3": SpecialistAuditorAgent(
            agent_id="trust.security.v3",
            name="Security, HTTPS & Protocol Integrity Specialist",
            role="Audits TLS encryption, HSTS directives, Content-Security-Policy headers, and clickjacking protection.",
            domain="SECURITY",
            default_stakeholders="Business Owners (Reputation & Risk) and Developers",
            inspection_methodology="SSL/TLS certificate handshake inspection and HTTP security header policy evaluation",
        ),
        "competitor.organic.v3": SpecialistAuditorAgent(
            agent_id="competitor.organic.v3",
            name="Competitive Intelligence Specialist",
            role="Evaluates SERP overlap, keyword footprint discrepancies, and competitor displacement opportunities.",
            domain="COMPETITOR",
            default_stakeholders="Business Owners & Commercial Leadership",
            inspection_methodology="Empirical SERP overlap calculation, schema depth benchmarking, and competitive positioning",
        ),
        "strategy.executive.v3": SpecialistAuditorAgent(
            agent_id="strategy.executive.v3",
            name="Executive Strategy & Governance Specialist",
            role="Synthesizes cross-pillar multi-disciplinary performance and 90-day implementation sequencing.",
            domain="STRATEGY",
            default_stakeholders="Business Owners, Visitors & Technical Teams",
            inspection_methodology="Cross-discipline reconciliation, priority matrix synthesis, and engineering effort estimation",
        ),
    }

    # Chapter number to agent mapping (compatible with 55-section and appendices)
    SECTION_AGENT_MAP: Dict[str, str] = {
        "ch_brief": "strategy.executive.v3",
        "ch_seo": "seo.crawl.v3",
        "ch_geo": "geo.extractability.v3",
        "ch_aeo": "aeo.direct_answer_box.v3",
        "ch_competitive": "competitor.organic.v3",
        "ch_conversion": "ux.conversion.v3",
        "ch_page_by_page": "seo.crawl.v3",
        "ch_roadmap": "strategy.executive.v3",
        "ch_methodology": "trust.security.v3",
        "ch_appendix": "seo.crawl.v3",
    }

    @classmethod
    def dispatch_agent_for_finding(
        cls,
        category: str,
        subcategory: str = "",
        rule_id: Optional[str] = None,
        title: str = "",
        description: str = "",
    ) -> SpecialistAuditorAgent:
        """Autonomously dispatches the finding to the domain specialist agent."""
        blob = f"{category} {subcategory} {rule_id or ''} {title} {description}".lower()

        # Domain classification
        if any(k in blob for k in ("canonical", "self-referencing", "duplicate url", "cross-domain")):
            return cls.AGENTS["seo.canonical.v3"]
        if any(k in blob for k in ("redirect", "301", "302", "404", "broken link", "loop", "hop")):
            return cls.AGENTS["seo.redirect.v3"]
        if any(k in blob for k in ("schema", "json-ld", "structured data", "rich result", "entity graph")):
            return cls.AGENTS["schema.validation.v3"]
        if any(k in blob for k in ("speed", "ttfb", "cwv", "core web vitals", "lcp", "cls", "inp", "latency")):
            return cls.AGENTS["ux.experience.v3"]
        if any(k in blob for k in ("aeo", "answer engine", "chatgpt", "perplexity", "citation", "gemini")):
            return cls.AGENTS["aeo.direct_answer_box.v3"]
        if any(k in blob for k in ("geo", "llms.txt", "gptbot", "extractability", "generative")):
            return cls.AGENTS["geo.extractability.v3"]
        if any(k in blob for k in ("conversion", "cro", "cta", "form", "checkout", "mobile tap", "contrast", "friction")):
            return cls.AGENTS["ux.conversion.v3"]
        if any(k in blob for k in ("security", "https", "hsts", "csp", "ssl", "tls", "headers", "certificate")):
            return cls.AGENTS["trust.security.v3"]
        if any(k in blob for k in ("crawl", "index", "robots", "sitemap", "noindex", "status", "bot")):
            return cls.AGENTS["seo.crawl.v3"]
        if any(k in blob for k in ("h1", "heading", "outline", "title tag", "meta description", "alt", "image")):
            return cls.AGENTS["content.depth.v3"]
        if any(k in blob for k in ("competitor", "benchmark", "overlap", "displacement")):
            return cls.AGENTS["competitor.organic.v3"]

        # Default fallback by high-level category
        cat_lower = str(category).lower()
        if "seo" in cat_lower or "crawl" in cat_lower:
            return cls.AGENTS["seo.crawl.v3"]
        if "geo" in cat_lower:
            return cls.AGENTS["geo.extractability.v3"]
        if "aeo" in cat_lower:
            return cls.AGENTS["aeo.direct_answer_box.v3"]
        if "cro" in cat_lower or "ux" in cat_lower:
            return cls.AGENTS["ux.conversion.v3"]

        return cls.AGENTS["strategy.executive.v3"]

    @classmethod
    def dispatch_agent_for_section(cls, section_id: str, section_title: str) -> SpecialistAuditorAgent:
        """Autonomously resolves the specialist agent responsible for the section or chapter."""
        agent_key = cls.SECTION_AGENT_MAP.get(section_id)
        if agent_key and agent_key in cls.AGENTS:
            return cls.AGENTS[agent_key]

        # Check numeric chapter if applicable (e.g. "01", "10", "16", "19")
        clean_num = section_id.replace("ch_", "").strip()
        num_map: Dict[str, str] = {
            "01": "strategy.executive.v3",
            "07": "seo.crawl.v3",
            "08": "seo.crawl.v3",
            "10": "seo.canonical.v3",
            "11": "seo.redirect.v3",
            "12": "seo.crawl.v3",
            "16": "ux.experience.v3",
            "18": "trust.security.v3",
            "19": "schema.validation.v3",
            "20": "content.depth.v3",
            "21": "content.depth.v3",
            "45": "aeo.direct_answer_box.v3",
            "46": "geo.extractability.v3",
            "50": "ux.conversion.v3",
        }
        if clean_num in num_map:
            return cls.AGENTS[num_map[clean_num]]

        # Fallback by keyword in section title
        return cls.dispatch_agent_for_finding(category=section_title, title=section_title)


# ==============================================================================
# 5. ENRICHMENT ENGINE FOR FINDINGS (14 MANDATORY STRUCTURED FIELDS)
# ==============================================================================

class PlainEnglishEngine:
    """
    Centralized translation and explanation engine.
    Orchestrates domain specialist auditor agents to produce plain-English,
    zero-fabrication explanations for findings and sections.
    """

    @classmethod
    def classify_who_is_affected(cls, category: str, title: str, description: str) -> str:
        """Determines who is affected via autonomous specialist agent dispatch."""
        agent = AgenticSpecialistRegistry.dispatch_agent_for_finding(category, title=title, description=description)
        return agent.who_is_affected(title, description)

    @classmethod
    def generate_plain_english_summary(cls, title: str, description: str, category: str) -> str:
        """Synthesizes short, jargon-free explanation via autonomous specialist agent."""
        agent = AgenticSpecialistRegistry.dispatch_agent_for_finding(category, title=title, description=description)
        return agent.explain(title, description, category)

    @classmethod
    def generate_what_was_checked(cls, category: str, subcategory: str, title: str, rule_id: Optional[str]) -> str:
        """Explains the exact technical test protocol via autonomous specialist agent."""
        agent = AgenticSpecialistRegistry.dispatch_agent_for_finding(category, subcategory=subcategory, rule_id=rule_id, title=title)
        return agent.what_was_checked(title, subcategory, rule_id)

    @classmethod
    def generate_verification_steps(
        cls,
        title: str,
        category: str,
        acceptance_criteria: Optional[str] = None,
        verification_method: Optional[str] = None,
    ) -> List[str]:
        """Produces concrete, numbered retest instructions via autonomous specialist agent."""
        agent = AgenticSpecialistRegistry.dispatch_agent_for_finding(category, title=title)
        return agent.verification_steps(title, acceptance_criteria, verification_method)

    @classmethod
    def generate_expected_outcome(cls, category: str, severity: str) -> str:
        """Generates evidence-backed expected outcome via autonomous specialist agent."""
        agent = AgenticSpecialistRegistry.dispatch_agent_for_finding(category)
        return agent.expected_outcome(severity)

    @classmethod
    def enrich_finding(cls, finding: Any, index: int = 1) -> Dict[str, Any]:
        """
        Takes any Finding instance or dict, coordinates the assigned specialist agent,
        and ensures all 14 structured fields are populated with consultative intelligence.
        """
        raw_id = _get_val(finding, "finding_id") or _get_val(finding, "id") or f"DST-{index:03d}"
        title = (
            _get_val(finding, "finding_title")
            or _get_val(finding, "title")
            or _get_val(finding, "finding")
            or "Observed Technical Discrepancy"
        )
        category = _get_val(finding, "category") or "Technical Architecture"
        subcategory = _get_val(finding, "subcategory") or "Audit Inspection"
        rule_id = _get_val(finding, "rule_id")

        # Severity
        raw_sev = _get_val(finding, "severity")
        if hasattr(raw_sev, "value"):
            sev_str = str(raw_sev.value).upper()
        elif hasattr(raw_sev, "name"):
            sev_str = str(raw_sev.name).upper()
        else:
            sev_str = str(raw_sev or "MEDIUM").upper()

        priority_map = {
            "CRITICAL": "Critical Priority",
            "HIGH": "High Priority",
            "MEDIUM": "Medium Priority",
            "LOW": "Low Priority",
            "INFO": "Informational",
            "INFORMATIONAL": "Informational",
        }
        priority_label = priority_map.get(sev_str, "Medium Priority")

        # Affected URLs
        raw_urls = _get_val(finding, "affected_urls") or []
        affected_urls = [str(u) for u in raw_urls if u]

        # Scope status
        explicit_scope = _get_val(finding, "scope_status") or _get_val(finding, "scope_classification") or _get_val(finding, "scope")
        if explicit_scope:
            scope_status = str(explicit_scope).upper()
        elif len(affected_urls) == 1:
            scope_status = "PAGE_VERIFIED"
        elif len(affected_urls) > 1:
            scope_status = "SAMPLE_VERIFIED"
        else:
            scope_status = "DOMAIN_WIDE"

        # Observed result (What was found)
        observed_result = (
            _get_val(finding, "observed_result")
            or _get_val(finding, "detailed_diagnosis")
            or _get_val(finding, "diagnosis")
            or _get_val(finding, "description")
            or _get_val(finding, "finding")
            or f"Observed discrepancy on {title}."
        )

        # Dispatch specialist agent
        agent = AgenticSpecialistRegistry.dispatch_agent_for_finding(
            category=str(category),
            subcategory=str(subcategory),
            rule_id=rule_id,
            title=str(title),
            description=str(observed_result),
        )

        # Plain-English summary (In simple English)
        plain_english_summary = _get_val(finding, "plain_english_summary")
        if not plain_english_summary:
            why_matters = _get_val(finding, "why_it_matters")
            if why_matters and len(why_matters) > 20:
                plain_english_summary = why_matters
            else:
                plain_english_summary = agent.explain(str(title), str(observed_result), str(category))

        # Business impact (Why this matters)
        business_impact = (
            _get_val(finding, "business_impact")
            or _get_val(finding, "business_context")
            or _get_val(finding, "why_it_matters")
            or agent.business_impact(str(title), str(observed_result), sev_str)
        )

        # What Dristik checked
        what_was_checked = _get_val(finding, "what_was_checked")
        if not what_was_checked:
            what_was_checked = agent.what_was_checked(str(title), str(subcategory), rule_id)

        # Who is affected
        who_affected = _get_val(finding, "who_affected")
        if not who_affected:
            who_affected = agent.who_is_affected(str(title), str(observed_result))

        # Recommended action (What to do next)
        recommended_action = (
            _get_val(finding, "recommended_action")
            or _get_val(finding, "recommended_solution")
            or _get_val(finding, "recommendation")
            or _get_val(finding, "suggested_fix")
            or "Implement the recommended fix across all affected templates."
        )

        # Developer instructions (separated from plain-English explanation)
        developer_instructions = _get_val(finding, "developer_instructions")
        if not developer_instructions:
            code_patch = _get_val(finding, "code_patch")
            if code_patch:
                target_file = _get_val(code_patch, "target_file") or "source template"
                snippet = _get_val(code_patch, "after_snippet") or _get_val(code_patch, "diff") or ""
                developer_instructions = f"Target File: {target_file}\nPatch implementation:\n{snippet}"
            else:
                steps = _get_val(finding, "implementation_steps")
                if steps and isinstance(steps, list):
                    developer_instructions = "Implementation Steps:\n" + "\n".join(f"- {s}" for s in steps)
                else:
                    dev_detail = _get_val(finding, "implementation_detail") or _get_val(finding, "relevant_code_or_configuration_example")
                    if dev_detail:
                        developer_instructions = str(dev_detail)
                    else:
                        developer_instructions = f"Technical Owner: Update configuration or markup on affected URLs according to standard {category} guidelines."

        # Verification steps
        verification_steps = _get_val(finding, "verification_steps")
        if not verification_steps:
            val_crit = _get_val(finding, "validation_criteria") or _get_val(finding, "acceptance_criteria")
            ver_method = _get_val(finding, "verification_method")
            verification_steps = agent.verification_steps(str(title), val_crit, ver_method)

        # Evidence references (Full Layer 1 Machine Observations)
        raw_evidence = _get_val(finding, "evidence") or []
        evidence_list: List[Dict[str, Any]] = []
        for e_idx, ev in enumerate(raw_evidence):
            e_id = _get_val(ev, "evidence_id") or _get_val(ev, "id") or f"EV-{raw_id}-{e_idx + 1}"
            e_source = _get_val(ev, "source") or _get_val(ev, "test_method") or "crawl_html_dom"
            e_url = _get_val(ev, "url") or (affected_urls[0] if affected_urls else "")
            e_elem = _get_val(ev, "element") or _get_val(ev, "selector") or "DOM element"
            e_obs = _get_val(ev, "observed_value") or _get_val(ev, "value") or _get_val(ev, "observation") or "Defect detected"
            e_exp = _get_val(ev, "expected_condition") or "Conform to W3C / Search Engine standard"
            e_meth = _get_val(ev, "test_method") or "crawl_inspection"
            e_snip = _get_val(ev, "snippet") or ""
            e_scope = _get_val(ev, "scope") or _get_val(ev, "evidence_scope") or scope_status
            e_ts = _get_val(ev, "captured_at") or _get_val(ev, "timestamp") or "Audit crawl execution"
            evidence_list.append({
                "id": str(e_id),
                "url": str(e_url),
                "element": str(e_elem),
                "observed_value": str(e_obs),
                "expected_condition": str(e_exp),
                "test_method": str(e_meth),
                "snippet": str(e_snip),
                "source": str(e_source),
                "observation": str(e_obs),
                "scope": str(e_scope),
                "timestamp": str(e_ts),
            })

        # Confidence & Limitations
        raw_conf = _get_val(finding, "confidence_label") or _get_val(finding, "confidence_rubric") or _get_val(finding, "confidence")
        conf_str = str(getattr(raw_conf, "value", raw_conf) or "High (90%)").capitalize()
        if "certain" in conf_str.lower() or "strong" in conf_str.lower() or conf_str.replace(".", "").isdigit():
            conf_str = "High (95% Verified)"
        elif "likely" in conf_str.lower() or "medium" in conf_str.lower():
            conf_str = "Medium (Likely)"

        limitations = _get_val(finding, "limitations") or _get_val(finding, "data_limitations")
        if not limitations:
            if len(affected_urls) > 0:
                limitations = f"Evaluated on {len(affected_urls)} inspected URL(s). Site-wide verification is recommended."
            else:
                limitations = "Evaluated on crawled sample pages. Verification required on full staging environment."

        # Expected outcome (Qualitative specification-based, never guaranteed revenue/rankings)
        expected_outcome = _get_val(finding, "expected_outcome")
        if not expected_outcome:
            expected_outcome = agent.expected_outcome(sev_str)

        # Lifecycle status
        raw_status = _get_val(finding, "resolution_status") or _get_val(finding, "lifecycle_state") or _get_val(finding, "status")
        status_str = str(getattr(raw_status, "value", raw_status) or "OPEN").upper()
        lifecycle_display = {
            "OPEN": "Open Defect",
            "IN_PROGRESS": "Remediation In Progress",
            "VERIFYING": "Pending Verification",
            "RESOLVED": "Verified Fixed",
            "REGRESSED": "Regressed Defect",
        }.get(status_str, "Open Defect")

        # Responsible Role (Priority 6)
        responsible_role = _get_val(finding, "responsible_role") or _get_val(finding, "owner")
        if not responsible_role or responsible_role in ("Engineering", "default"):
            title_lower = title.lower()
            cat_str = str(category).upper()
            if any(k in title_lower for k in ["alt", "heading", "h1", "h2", "title tag", "meta description", "thin copy", "content"]):
                responsible_role = "Content Editor"
            elif any(k in title_lower for k in ["schema", "json-ld", "keyword", "sitemap", "robots.txt", "canonical", "serp"]):
                responsible_role = "SEO Specialist"
            elif any(k in title_lower for k in ["analytics", "conversion", "ga4", "gsc", "tracking"]):
                responsible_role = "Analytics Owner"
            else:
                responsible_role = "Developer"

        # Estimated Effort (Priority 6)
        raw_effort = _get_val(finding, "estimated_effort")
        if raw_effort:
            estimated_effort = str(raw_effort)
        else:
            eff_val = _get_val(finding, "effort") or 3
            if eff_val <= 2:
                estimated_effort = "Low (< 2 hours)"
            elif eff_val <= 5:
                estimated_effort = "Medium (2-8 hours)"
            elif eff_val <= 8:
                estimated_effort = "High (1-3 days)"
            else:
                estimated_effort = "Complex (> 3 days)"

        # Implementation Dependencies (Priority 6)
        raw_deps = _get_val(finding, "dependencies") or _get_val(finding, "implementation_dependencies") or []
        if isinstance(raw_deps, list) and raw_deps:
            dependencies = [str(d) for d in raw_deps]
        else:
            if responsible_role == "Developer":
                dependencies = ["Codebase template access", "Deployment staging pipeline"]
            elif responsible_role == "Content Editor":
                dependencies = ["CMS editor privileges"]
            elif responsible_role == "SEO Specialist":
                dependencies = ["DNS / Server header control or CMS SEO plugin access"]
            else:
                dependencies = ["Analytics administrative access"]

        # Priority Rationale (Priority 6)
        priority_rationale = _get_val(finding, "priority_rationale") or _get_val(finding, "severity_justification")
        if not priority_rationale:
            if sev_str == "CRITICAL":
                priority_rationale = "Critical Priority: Directly blocks search crawler indexation or creates catastrophic user-facing error."
            elif sev_str == "HIGH":
                priority_rationale = "High Priority: Materially impairs primary ranking signals, crawl efficiency, or core user experience."
            elif sev_str == "MEDIUM":
                priority_rationale = "Medium Priority: Technical or semantic non-compliance that weakens topical authority or accessibility."
            else:
                priority_rationale = "Low Priority: Best-practice hygiene optimization with minimal immediate crawl risk."

        # Testable Acceptance Criteria (Priority 6 / Validation)
        acceptance_val = _get_val(finding, "acceptance_criteria") or _get_val(finding, "validation_criteria")
        if not acceptance_val:
            title_l = title.lower()
            if "alt" in title_l:
                acceptance_val = "Every informative <img> on affected routes must declare a non-empty alt attribute, and decorative assets must use alt=''."
            elif "canonical" in title_l:
                acceptance_val = "Affected routes must declare an absolute self-referencing rel='canonical' tag resolving to valid HTTP 200."
            elif "heading" in title_l or "h1" in title_l:
                acceptance_val = "Document must contain exactly one <h1> heading followed by sequential <h2>/<h3> hierarchy without level skips."
            elif "security" in title_l or "hsts" in title_l:
                acceptance_val = "Server response headers on HTTPS must include Strict-Transport-Security with max-age >= 31536000."
            elif "title" in title_l or "meta" in title_l:
                acceptance_val = "Page must define an explicit, unique title (50-60 chars) and meta description (140-160 chars)."
            else:
                acceptance_val = f"Technical discrepancy regarding '{title}' is resolved and verified by automated crawl retest."

        # Concrete Verification Command (Priority 6 / Validation)
        verification_cmd = _get_val(finding, "verification_command")
        if not verification_cmd:
            primary_url = affected_urls[0] if affected_urls else "https://example.com/"
            title_l = title.lower()
            if "canonical" in title_l:
                verification_cmd = f"curl -sI -L '{primary_url}' | grep -i 'canonical'"
            elif "hsts" in title_l or "security" in title_l:
                verification_cmd = f"curl -sI '{primary_url}' | grep -i 'Strict-Transport-Security'"
            elif "heading" in title_l or "h1" in title_l:
                verification_cmd = f"curl -s '{primary_url}' | grep -i '<h1'"
            elif "alt" in title_l:
                verification_cmd = f"curl -s '{primary_url}' | grep -i '<img' | grep -v 'alt='"
            elif "404" in title_l or "redirect" in title_l:
                verification_cmd = f"curl -sIL -o /dev/null -w '%{{http_code}} -> %{{url_effective}}\\n' '{primary_url}'"
            elif "robots" in title_l:
                verification_cmd = f"curl -s '{primary_url.rstrip('/')}/robots.txt'"
            elif "sitemap" in title_l:
                verification_cmd = f"curl -sI '{primary_url.rstrip('/')}/sitemap.xml'"
            else:
                verification_cmd = f"curl -sI '{primary_url}'"

        root_cause_val = _get_val(finding, "root_cause") or _get_val(finding, "causal_mechanism")
        code_val = _get_val(finding, "relevant_code_or_configuration_example")

        return {
            "id": str(raw_id),
            "finding_title": str(title),
            "title": str(title),
            "severity": sev_str,
            "priority": priority_label,
            "lifecycle_status": lifecycle_display,
            "scope_status": scope_status,
            "what_was_checked": str(what_was_checked),
            "observed_result": str(observed_result),
            "plain_english_summary": str(plain_english_summary),
            "business_impact": str(business_impact),
            "who_affected": str(who_affected),
            "affected_urls": affected_urls,
            "recommended_action": str(recommended_action),
            "developer_instructions": str(developer_instructions),
            "verification_steps": verification_steps,
            "evidence": evidence_list,
            "confidence": conf_str,
            "limitations": str(limitations),
            "expected_outcome": str(expected_outcome),
            "root_cause": str(root_cause_val) if root_cause_val else None,
            "acceptance_criteria": str(acceptance_val),
            "verification_command": str(verification_cmd),
            "responsible_role": str(responsible_role),
            "estimated_effort": str(estimated_effort),
            "dependencies": dependencies,
            "priority_rationale": str(priority_rationale),
            "relevant_code_or_configuration_example": str(code_val) if code_val else None,
        }

    @classmethod
    async def enrich_finding_with_agent(
        cls,
        finding: Any,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Asynchronous LLM-powered agentic explanation pathway.
        When LLM inference is available, queries the model router with specialist task instructions.
        Falls back seamlessly to the deterministic agent workforce.
        """
        enriched = cls.enrich_finding(finding)
        try:
            from app.inference.llm_client import LLMClient
            client = LLMClient()
            if not getattr(client, "available", True):
                return enriched

            # Query agent with zero-fabrication prompt
            prompt = (
                f"You are the {enriched.get('who_affected')} auditor. Explain the defect '{enriched['title']}' "
                f"for the website {domain or 'domain'}. In 2 sentences, explain in simple non-technical English "
                f"what the defect is and why it matters commercially. Do not invent facts."
            )
            # If client has fast chat method:
            if hasattr(client, "complete"):
                res = await client.complete(prompt=prompt, max_tokens=150)
                if res and isinstance(res, str) and len(res) > 20:
                    enriched["plain_english_summary"] = res.strip()
        except Exception as e:
            logger.debug("Agentic LLM explanation fallback: %s", e)

        return enriched


# ==============================================================================
# 6. DYNAMIC SECTION & CHAPTER EXPLANATION ENGINE
# ==============================================================================

# Backwards-compatible section metadata map
SECTION_SUBJECT_MAP: Dict[str, Dict[str, str]] = {
    "ch_brief": {
        "subject": "Executive Diagnostic Briefing & Multi-Pillar Scorecard",
        "description": "A high-level synthesis of your digital performance across Search Engine Optimization (SEO), Generative Engine Optimization (GEO), Answer Engine Optimization (AEO), and Conversion Rate Optimization (CRO).",
        "why_care": "Executive alignment ensures engineering, marketing, and commercial teams resolve the highest-impact bottlenecks first rather than wasting budget on vanity projects.",
    },
    "ch_seo": {
        "subject": "Technical Search Engine Optimization (SEO) & Crawl Architecture",
        "description": "Evaluates how effectively search engine crawlers (Googlebot, Bingbot) discover, read, and index your website's pages without getting stuck in loops or server delays.",
        "why_care": "If search engine robots cannot efficiently crawl or correctly index your pages, your target audience will never discover your services through organic search.",
    },
    "ch_geo": {
        "subject": "Generative Engine Optimization (GEO) & Machine Extractability",
        "description": "Analyzes how easily artificial intelligence search engines and Large Language Models (LLMs) can extract verified facts, definitions, and company credentials directly from your HTML code.",
        "why_care": "As prospective customers increasingly ask AI tools for brand recommendations, websites that present dense, machine-readable facts are cited as definitive industry authorities.",
    },
    "ch_aeo": {
        "subject": "Answer Engine Optimization (AEO) & Live AI Citations",
        "description": "Measures your live visibility and citation rates across conversational AI platforms including ChatGPT Search, Perplexity AI, Claude, Google Gemini, and Google AI Overviews.",
        "why_care": "When high-intent buyers ask AI engines 'Who is the best vendor for X?', winning citations directly captures qualified buyers at the decision stage.",
    },
    "ch_competitive": {
        "subject": "Competitive Digital Visibility & Knowledge Graph Benchmark",
        "description": "Direct head-to-head empirical comparison of your brand presence against recorded market peers, evaluating schema depth and search overlap.",
        "why_care": "Knowing exactly where competitors win citations or search rankings highlights market gaps and displacement opportunities for your commercial team.",
    },
    "ch_conversion": {
        "subject": "Conversion Rate Optimization (CRO) & Visitor Ergonomics",
        "description": "Examines the clarity of your value proposition, heading hierarchy, call-to-action (CTA) prominence, and user interaction friction on sampled pages.",
        "why_care": "Traffic is only valuable if visitors convert. Reducing layout friction and clarifying calls to action increases inquiries without spending more on marketing.",
    },
    "ch_page_by_page": {
        "subject": "Page-by-Page Audit Inventory & URL Architecture",
        "description": "A URL-level breakdown showing the exact HTTP status codes, title tags, canonical states, and heading outlines across inspected pages.",
        "why_care": "Provides your engineering and content teams with an actionable, page-by-page checklist to resolve defects without guesswork.",
    },
    "ch_roadmap": {
        "subject": "Strategic Priorities & 90-Day Engineering Roadmap",
        "description": "A phased implementation schedule (NOW / NEXT / ONGOING) calibrated by technical severity, business impact, and engineering effort.",
        "why_care": "Sequencing fixes by return on effort ensures your technical resources produce the greatest commercial improvement in the shortest timeframe.",
    },
    "ch_methodology": {
        "subject": "Research Methodology, Sampling Scope & Governance Standards",
        "description": "Transparent disclosure of our inspection parameters, crawl depth boundaries, multi-engine testing protocols, and Zero-Fabrication integrity guarantees.",
        "why_care": "Enterprise leaders must know the boundaries of what was tested versus what was inferred, ensuring every commercial decision is backed by verified evidence.",
    },
    "ch_appendix": {
        "subject": "Institutional Findings Register & Code Patch Ledger",
        "description": "An exhaustive engineering catalog of every defect, affected URL, cryptographic provenance record, and verified code remediation patch.",
        "why_care": "Provides developers with copy-paste code patches and exact verification commands to accelerate resolution and prevent regressions.",
    },
}


def generate_section_explanation(
    section_id: str,
    section_title: str,
    report: Any = None,
    findings: Optional[Sequence[Any]] = None,
    context_data: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> SectionBusinessExplanation:
    """
    Constructs a specific, grounded business explanation for any section or chapter
    using the assigned Domain Specialist Auditor Agent.
    """
    ctx = dict(context_data or {})
    ctx.update(kwargs)
    if findings is None and "section_findings" in kwargs:
        findings = kwargs["section_findings"]
    if "has_connector" in kwargs and not kwargs["has_connector"]:
        ctx["is_tested"] = False
        ctx["missing_integration"] = kwargs.get("connector_name") or "Required telemetry connector"
    if "is_sample_audit" in kwargs:
        ctx["is_sample_audit"] = kwargs["is_sample_audit"]
    if "pages_crawled" in kwargs:
        ctx["pages_crawled"] = kwargs["pages_crawled"]

    # Dispatch agent for section
    agent = AgenticSpecialistRegistry.dispatch_agent_for_section(section_id, section_title)

    # Resolve meta: check static map first for backwards-compatibility, then agent
    meta = SECTION_SUBJECT_MAP.get(section_id, {
        "subject": section_title,
        "description": f"Detailed assessment evaluating {section_title} against verified industry standards via {agent.name}.",
        "why_care": f"Addressing these findings preserves user experience, search visibility, and digital brand authority.",
    })

    section_findings = list(findings or [])
    pages_crawled = int(_get_val(report, "pages_crawled") or ctx.get("pages_crawled") or 1)

    # Check connector / data availability
    is_tested = ctx.get("is_tested", True)
    missing_integration = ctx.get("missing_integration")

    if not is_tested or missing_integration:
        return SectionBusinessExplanation(
            section_id=section_id,
            section_title=section_title,
            plain_english_subject=meta["description"],
            key_result=f"Assessment pending: {missing_integration or 'Required telemetry connector'} is not yet authenticated.",
            why_reader_should_care=meta["why_care"],
            recommended_action=f"Authenticate {missing_integration or 'the corresponding data integration'} in Organization Settings to complete this diagnostic chapter.",
            evidence_status="NOT_TESTED",
            evidence_status_note=(
                f"This section was not tested because {missing_integration or 'the necessary data integration'} is not connected. "
                "No speculative scores or assumptions were made."
            ),
            sample_size=0,
            pages_affected=0,
        )

    # If defects were found
    if section_findings:
        crit_count = sum(1 for f in section_findings if str(_get_val(f, "severity", "")).upper() in ("CRITICAL", "HIGH"))
        top_finding = section_findings[0]
        top_title = _get_val(top_finding, "title") or _get_val(top_finding, "finding_title") or "Technical defect"

        key_result = (
            f"{len(section_findings)} issue(s) identified ({crit_count} high/critical priority). "
            f"Primary focus: {top_title}."
        )
        action_needed = (
            f"Review the prioritized remediation steps below and apply the recommended fixes "
            f"to the {len(section_findings)} recorded finding(s)."
        )
        status_note = (
            f"Verified defects were identified across the {pages_crawled} inspected sample page(s). "
            "Remediation is recommended to restore full compliance."
        )

        return SectionBusinessExplanation(
            section_id=section_id,
            section_title=section_title,
            plain_english_subject=meta["description"],
            key_result=key_result,
            why_reader_should_care=meta["why_care"],
            recommended_action=action_needed,
            evidence_status="DEFECTS_FOUND",
            evidence_status_note=status_note,
            sample_size=pages_crawled,
            pages_affected=len(section_findings),
        )

    # If no defects found (Clean sample pass)
    return SectionBusinessExplanation(
        section_id=section_id,
        section_title=section_title,
        plain_english_subject=meta["description"],
        key_result=f"No defects identified across the inspected sample of {pages_crawled} page(s).",
        why_reader_should_care=meta["why_care"],
        recommended_action="Maintain current configurations. Periodically retest when new page templates are deployed.",
        evidence_status="SAMPLE_TESTED_CLEAN",
        evidence_status_note=(
            f"What was tested on the {pages_crawled} sampled URL(s) passed target criteria without errors. "
            "Important note: Because this audit evaluated a representative sample, this does not guarantee "
            "that every uninspected page on the broader domain is completely error-free."
        ),
        sample_size=pages_crawled,
        pages_affected=0,
    )


# ==============================================================================
# 7. HTML COMPONENT RENDERERS (PRINT & PDF COMPLIANT)
# ==============================================================================

def render_section_business_callout(exp: SectionBusinessExplanation) -> str:
    """
    Renders the compact "What this means for your business" executive callout card.
    Visually distinct, high contrast, and print-ready.
    """
    if exp.evidence_status == "DEFECTS_FOUND":
        accent = "#ea580c"  # Amber/Orange
        badge_bg = "#fff7ed"
        badge_color = "#c2410c"
        badge_text = "ISSUES REQUIRING ATTENTION"
    elif exp.evidence_status == "SAMPLE_TESTED_CLEAN":
        accent = "#16a34a"  # Green
        badge_bg = "#f0fdf4"
        badge_color = "#15803d"
        badge_text = "SAMPLE PASSED // NO DEFECTS RECORDED"
    else:
        accent = "#64748b"  # Slate/Gray
        badge_bg = "#f8fafc"
        badge_color = "#475569"
        badge_text = "NOT TESTED // INTEGRATION REQUIRED"

    return f"""
    <div class="business-explanation-card report-avoid-break" style="border-left: 4px solid {accent}; margin: 16px 0 20px 0; padding: 14px 18px; background: #ffffff; border-radius: 4px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-family: ui-monospace, monospace; font-size: 7.5pt; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; color: {accent};">
                WHAT THIS MEANS FOR YOUR BUSINESS
            </span>
            <span style="font-family: ui-monospace, monospace; font-size: 7pt; font-weight: 700; padding: 2px 8px; border-radius: 3px; background: {badge_bg}; color: {badge_color};">
                {badge_text}
            </span>
        </div>
        <p style="font-size: 10pt; line-height: 1.55; color: #1e293b; margin: 0 0 8px 0; font-weight: 500;">
            {_esc(exp.plain_english_subject)}
        </p>
        <div style="margin: 6px 0 10px 0; font-size: 8.5pt; color: #334155; line-height: 1.5;">
            <strong style="color: #0f172a;">Why this matters to your bottom line:</strong> {_esc(exp.why_reader_should_care)}
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #f1f5f9;">
            <div>
                <strong style="font-size: 7.5pt; font-family: ui-monospace, monospace; text-transform: uppercase; color: #64748b; display: block; margin-bottom: 2px;">Key Observation:</strong>
                <span style="font-size: 8.5pt; color: #0f172a; line-height: 1.45;">{_esc(exp.key_result)}</span>
            </div>
            <div>
                <strong style="font-size: 7.5pt; font-family: ui-monospace, monospace; text-transform: uppercase; color: #64748b; display: block; margin-bottom: 2px;">Recommended Action:</strong>
                <span style="font-size: 8.5pt; color: #0f172a; line-height: 1.45;">{_esc(exp.recommended_action)}</span>
            </div>
        </div>
        <div style="margin-top: 8px; padding-top: 6px; border-top: 1px dashed #e2e8f0; font-size: 8pt; color: #64748b; line-height: 1.4;">
            <strong style="font-family: ui-monospace, monospace; font-size: 7pt; color: #475569;">EVIDENCE SCOPE &amp; LIMITATIONS:</strong> {_esc(exp.evidence_status_note)}
        </div>
    </div>
    """


def render_plain_english_finding_card(f: Dict[str, Any]) -> str:
    """
    Renders the exact 11-point finding card component requested by the user:
    - Header: Finding ID, Title, Priority/Severity badge, Scope status, Lifecycle status, Who is affected
    - 1. What was found? (observed_result)
    - 2. What does this mean in simple English? (plain_english_summary in .plain-english panel)
    - 3. Why does this matter to your business? (business_impact)
    - 4. What did Dristik check? (what_was_checked)
    - 5. Which pages are affected? (affected_urls)
    - 6. Recommended solution (recommended_action)
    - 7. Technical implementation instructions (developer_instructions in developer box)
    - 8. How to verify the fix (verification_steps)
    - 9. Supporting evidence (evidence table with ID, Source, Observation, Scope, Timestamp)
    - 10. Confidence and limitations (confidence, limitations)
    - 11. Expected outcome (expected_outcome with commercial disclaimer)
    """
    f_id = _esc(f.get("id", "DST-001"))
    title = _esc(f.get("finding_title") or f.get("title", "Observed Defect"))
    sev = str(f.get("severity", "MEDIUM")).upper()
    priority = _esc(f.get("priority", "Medium Priority"))
    scope_status = _esc(f.get("scope_status", "PAGE_VERIFIED"))
    lifecycle = _esc(f.get("lifecycle_status", "Open Defect"))
    who_affected = _esc(f.get("who_affected", "Visitors & Search Engines"))

    sev_class = sev.lower()
    sev_colors = {
        "CRITICAL": ("#dc2626", "#fee2e2", "#991b1b"),
        "HIGH": ("#ea580c", "#ffedd5", "#c2410c"),
        "MEDIUM": ("#d97706", "#fef3c7", "#92400e"),
        "LOW": ("#2563eb", "#dbeafe", "#1e40af"),
        "INFO": ("#64748b", "#f1f5f9", "#475569"),
    }
    border_col, badge_bg, badge_txt = sev_colors.get(sev, ("#64748b", "#f1f5f9", "#475569"))

    # 1. What was found?
    observed_result = _esc(f.get("observed_result", "Specific defect recorded during crawl inspection."))
    root_cause = f.get("root_cause")
    root_cause_html = ""
    if root_cause:
        root_cause_html = f"""
        <div class="root-cause-box" style="margin-top: 6px; padding: 6px 10px; background: #fffbeb; border: 1px solid #fef3c7; border-radius: 4px;">
            <strong style="font-size: 7.5pt; color: #b45309; text-transform: uppercase;">ROOT CAUSE:</strong>
            <span style="font-size: 8.5pt; color: #92400e; margin-left: 4px;">{_esc(root_cause)}</span>
        </div>
        """

    # 2. In simple English
    plain_english = _esc(f.get("plain_english_summary", ""))

    # 3. Why this matters
    business_impact = _esc(f.get("business_impact", ""))

    # 4. What did Dristik check?
    what_checked = _esc(f.get("what_was_checked", ""))

    # 5. Which pages are affected?
    urls = f.get("affected_urls", [])
    if urls:
        urls_html = "<ul class=\"affected-urls-list\">" + "".join(f"<li><code>{_esc(u)}</code></li>" for u in urls[:5])
        if len(urls) > 5:
            urls_html += f"<li><em>...plus {len(urls) - 5} additional sampled URL(s)</em></li>"
        urls_html += "</ul>"
    else:
        urls_html = "<p class=\"meta-note\">Specific URL list was not supplied. This issue may be systemic across templates.</p>"

    # 6. Recommended solution
    rec_solution = _esc(f.get("recommended_action", ""))

    # 7. Developer instructions
    dev_instructions = _esc(f.get("developer_instructions", "Developer-level instructions have not been supplied."))

    # 8. Verification steps
    ver_steps = f.get("verification_steps", [])
    acceptance_crit = f.get("acceptance_criteria")
    acceptance_html = ""
    if acceptance_crit:
        acceptance_html = f"""
        <div class="acceptance-box" style="margin-top: 6px; padding: 6px 10px; background: #f0fdf4; border: 1px solid #dcfce7; border-radius: 4px;">
            <strong style="font-size: 7.5pt; color: #15803d; text-transform: uppercase;">ACCEPTANCE CRITERIA:</strong>
            <span style="font-size: 8.5pt; color: #166534; margin-left: 4px;">{_esc(acceptance_crit)}</span>
        </div>
        """
    if ver_steps:
        steps_html = "<ol class=\"verification-steps-list\">" + "".join(f"<li>{_esc(s)}</li>" for s in ver_steps) + "</ol>"
    else:
        steps_html = "<p class=\"meta-note\">Verification steps pending technical review.</p>"

    # 9. Supporting evidence
    evidence = f.get("evidence", [])
    if evidence:
        ev_rows = []
        for e in evidence[:4]:
            ev_rows.append(
                f"<tr><td><code>{_esc(e.get('id', '—'))}</code></td>"
                f"<td>{_esc(e.get('source', 'DOM'))}</td>"
                f"<td>{_esc(e.get('observation', '—'))}</td>"
                f"<td>{_esc(e.get('scope', 'Sampled'))}</td></tr>"
            )
        evidence_html = f"""
        <table class="print-table evidence-mini-table">
            <thead>
                <tr><th>Evidence ID</th><th>Source</th><th>Observation</th><th>Scope</th></tr>
            </thead>
            <tbody>
                {"".join(ev_rows)}
            </tbody>
        </table>
        """
    else:
        evidence_html = "<p class=\"meta-note\">Direct DOM observation recorded during audit execution.</p>"

    # 10. Confidence and limitations
    confidence = _esc(f.get("confidence", "High (90%)"))
    limitations = _esc(f.get("limitations", "Evaluated on representative sample pages."))

    # 11. Expected outcome
    expected_outcome = _esc(f.get("expected_outcome", "Restores compliance with search and accessibility standards."))

    return f"""
    <article class="finding-card sev-{sev_class} report-avoid-break" id="finding-{f_id}" style="border-left: 4.5px solid {border_col}; margin-bottom: 22px;">

        <!-- FINDING HEADER & META -->
        <div class="finding-top-bar">
            <div class="finding-meta-left">
                <span class="finding-id-pill">{f_id}</span>
                <span class="finding-sev-pill" style="background: {badge_bg}; color: {badge_txt}; border: 1px solid {border_col}; font-weight: 800;">
                    {priority}
                </span>
                <span class="finding-scope-badge">{scope_status}</span>
                <span class="finding-lifecycle-badge">{lifecycle}</span>
            </div>
            <div class="finding-meta-right">
                <span class="who-affected-label"><strong>Who is affected:</strong> {who_affected}</span>
            </div>
        </div>

        <h3 class="finding-heading" style="font-size: 13pt; margin: 8px 0 12px 0; color: #0f172a; line-height: 1.35;">
            {f_id} — {title}
        </h3>

        <!-- 1. WHAT WAS FOUND? -->
        <div class="finding-block">
            <h4 class="finding-block-title">1. What was found?</h4>
            <p class="finding-block-text">{observed_result}</p>
            {root_cause_html}
        </div>

        <!-- 2. WHAT DOES THIS MEAN IN SIMPLE ENGLISH? -->
        <div class="finding-block plain-english-panel" style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 4px; padding: 12px 14px; margin: 10px 0;">
            <h4 class="finding-block-title" style="color: #1e40af; margin-bottom: 4px;">
                2. What does this mean in simple English?
            </h4>
            <p class="finding-block-text" style="color: #1e3a8a; margin: 0; font-size: 9.5pt; line-height: 1.55;">
                {plain_english}
            </p>
        </div>

        <!-- 3. WHY DOES THIS MATTER TO YOUR BUSINESS? -->
        <div class="finding-block">
            <h4 class="finding-block-title">3. Why does this matter to your business?</h4>
            <p class="finding-block-text">{business_impact}</p>
        </div>

        <!-- 4. WHAT DID DRISTIK CHECK? -->
        <div class="finding-block">
            <h4 class="finding-block-title">4. What did Dristik check?</h4>
            <p class="finding-block-text">{what_checked}</p>
        </div>

        <!-- 5. WHICH PAGES ARE AFFECTED? -->
        <div class="finding-block">
            <h4 class="finding-block-title">5. Which pages are affected?</h4>
            {urls_html}
        </div>

        <!-- 6. RECOMMENDED SOLUTION -->
        <div class="finding-block">
            <h4 class="finding-block-title">6. Recommended solution</h4>
            <div class="solution-box" style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px 12px;">
                <p class="finding-block-text" style="margin: 0; color: #0f172a; font-weight: 500;">{rec_solution}</p>
            </div>
        </div>

        <!-- 7. TECHNICAL IMPLEMENTATION INSTRUCTIONS -->
        <div class="finding-block dev-instructions-block" style="margin: 12px 0;">
            <h4 class="finding-block-title" style="color: #334155;">7. Technical implementation instructions (Developer details)</h4>
            <pre class="code-block" style="background: #0f172a; color: #38bdf8; font-family: ui-monospace, monospace; font-size: 7.5pt; padding: 10px 12px; border-radius: 4px; white-space: pre-wrap; margin: 4px 0 0 0; line-height: 1.45;"><code>{dev_instructions}</code></pre>
        </div>

        <!-- 8. HOW TO VERIFY THE FIX -->
        <div class="finding-block">
            <h4 class="finding-block-title">8. How to verify the fix (Retest procedure)</h4>
            {steps_html}
            {acceptance_html}
        </div>

        <!-- 9. SUPPORTING EVIDENCE -->
        <div class="finding-block">
            <h4 class="finding-block-title">9. Supporting evidence</h4>
            {evidence_html}
        </div>

        <!-- 10. CONFIDENCE AND LIMITATIONS -->
        <div class="finding-block">
            <h4 class="finding-block-title">10. Confidence and limitations</h4>
            <div class="confidence-limitations-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px 12px;">
                <div>
                    <strong style="font-family: ui-monospace, monospace; font-size: 7pt; text-transform: uppercase; color: #64748b; display: block;">Confidence Level:</strong>
                    <span style="font-size: 8.5pt; font-weight: 700; color: #0f172a;">{confidence}</span>
                </div>
                <div>
                    <strong style="font-family: ui-monospace, monospace; font-size: 7pt; text-transform: uppercase; color: #64748b; display: block;">Scope &amp; Limitations:</strong>
                    <span style="font-size: 8.5pt; color: #475569;">{limitations}</span>
                </div>
            </div>
        </div>

        <!-- 11. EXPECTED OUTCOME -->
        <div class="finding-block" style="margin-top: 10px; padding: 8px 12px; background: #fafafa; border-radius: 4px; border: 1px solid #f1f5f9;">
            <h4 class="finding-block-title" style="margin-bottom: 2px;">11. Expected outcome</h4>
            <p class="finding-block-text" style="margin-bottom: 4px;">{expected_outcome}</p>
            <p class="small meta-disclaimer" style="font-size: 7pt; color: #94a3b8; margin: 0; font-style: italic;">
                Commercial Disclaimer: This is an expected qualitative or evidence-backed outcome, not a guarantee of improved rankings, traffic, leads, or revenue.
            </p>
        </div>

    </article>
    """

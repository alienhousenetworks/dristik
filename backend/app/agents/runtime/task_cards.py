"""
Per-specialist task contracts for the 35-agent workforce.
Each card is a single-task instruction. Shared anti-hallucination rules live in
inference/prompts/specialist_system.txt and GLOBAL_POLICY.
"""
from typing import Dict

SPECIALIST_OUTPUT_SCHEMA = """{
  "status": "completed | unavailable",
  "unavailable_reason": "string or null",
  "mode": "OBSERVED | SIMULATION_ONLY | DETERMINISTIC",
  "claims": [
    {
      "statement": "string grounded in evidence",
      "category": "TECHNICAL_SEO | ON_PAGE_SEO | CONTENT | GEO | AI_SEARCH | SCHEMA | UX_CONVERSION | TRUST_AUTHORITY | COMPETITIVE",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW | INFO",
      "confidence": 0.0,
      "evidence_refs": ["ev_xxx", "ext_xxx"],
      "evidence_status": "supported | not_in_evidence",
      "source_integrity_label": "CORROBORATED | CONTESTED | SINGLE_SOURCE_UNVERIFIED | NOT_APPLICABLE",
      "confidence_band": "HIGH | MEDIUM | LOW",
      "finding": "plain-language claim",
      "evidence": ["ev_xxx", "ext_xxx"],
      "confidence_rubric": "CERTAIN | LIKELY | GUESSING",
      "confidence_basis": "one sentence: why this level, not the one above it",
      "materiality": "CRITICAL | MAJOR | MINOR",
      "source_agreement": 0,
      "recommendation": "string or empty",
      "impact": 5,
      "effort": 3
    }
  ],
  "observations": {}
}"""

TASK_CARDS: Dict[str, str] = {
    "business.discovery.v3": (
        "Extract only what the page writes: legal/brand name, offerings, industry phrases, "
        "stated audience, stated business model, primary CTA text. Industry/niche must be specific "
        "(who + offer), never 'Technology' or 'Software' when a sharper label exists. "
        "If a field is not on the page, omit it. Do not guess pricing, competitors, or market size."
    ),
    "business.icp.v3": (
        "From stated copy, list buyer roles, company-size phrases, industries named, and disqualifiers. "
        "BEFORE finalizing, check the External Ground-Truth feed (ext_xxx: LinkedIn/Clearbit/Crunchbase). "
        "If an ext token CONFIRMS the DOM ICP: cite both ev_xxx and ext_xxx, confidence HIGH. "
        "If it CONTRADICTS: status=CONTESTED, cite both, do not pick a winner, route to verification.contradiction.v3. "
        "If no usable ext_xxx exists: confidence MEDIUM at best, source_integrity_label=SINGLE_SOURCE_UNVERIFIED. "
        "If the site says 'everyone' or names no ICP, report AMBIGUOUS with evidence_refs. Do not invent personas."
    ),
    "business.intent.v3": (
        "Classify page intents from titles, H1s, URLs, and meta: informational, commercial, transactional, "
        "navigational, comparison. Tag each crawled URL with one intent. Do not invent URLs. "
        "A services firm with 'Get a quote' is lead generation, not ecommerce."
    ),
    "business.commercial.v3": (
        "Report only observed pricing tables, plan names, 'contact sales', trial CTAs, and checkout paths. "
        "BEFORE finalizing, check ext_xxx for published price/currency. "
        "CONFIRMS → cite ev_xxx + ext_xxx, confidence HIGH. CONTRADICTS → CONTESTED, cite both, route to verification.contradiction.v3. "
        "No usable ext_xxx → MEDIUM at best, SINGLE_SOURCE_UNVERIFIED. "
        "If no price appears in evidence, say pricing is NOT_IN_EVIDENCE. Never invent a number or TAM."
    ),
    "business.semantic_strategist.v3": (
        "Using prior business claims on the blackboard, detect conflicts (e.g. homepage says enterprise, "
        "pricing page says hobby). Do not add new facts. Only reconcile existing evidence-backed claims."
    ),
    "seo.crawl.v3": (
        "Audit robots.txt presence, sitemap presence, HTTP status codes, and crawl depth from the crawl manifest. "
        "Only state what the crawler recorded. Missing robots is MEDIUM unless the site also returns errors."
    ),
    "seo.indexability.v3": (
        "Audit canonical tags, meta robots, noindex, and X-Robots-Tag from extracted meta evidence. "
        "Do not assume indexability if tags are missing — report MISSING. noindex on the homepage is CRITICAL."
    ),
    "seo.html.v3": (
        "Audit title, meta description, H1–H6 hierarchy, and landmark elements from the DOM evidence. "
        "Quote lengths and counts. Do not invent missing headings. Duplicate H1s are MEDIUM, missing H1 is HIGH."
    ),
    "seo.internal_links.v3": (
        "Describe the observed internal link graph: orphan candidates, thin in-degree, generic anchors. "
        "Use only crawled URLs and recorded anchors."
    ),
    "seo.performance.v3": (
        "Use measured TTFB and payload size only. Never invent LCP, CLS, INP, or CrUX values. "
        "BEFORE finalizing any CWV/performance claim, check ext_xxx from CrUX field data. "
        "CONFIRMS → cite ev_xxx + ext_xxx, HIGH. CONTRADICTS → CONTESTED, cite both, route to verification.contradiction.v3. "
        "No usable CrUX ext_xxx → MEDIUM at best, SINGLE_SOURCE_UNVERIFIED. Lab Lighthouse is not a substitute. "
        "If a vital was not measured, status=unavailable for that metric."
    ),
    "seo.security.v3": (
        "Report HTTPS vs HTTP, HSTS, CSP, X-Frame-Options from response headers. "
        "If a header is absent, say absent. Do not assume HTTPS is true. HTTP homepage is CRITICAL."
    ),
    "seo.assets.v3": (
        "Count images, missing alt, and any observed format hints from the DOM. Do not invent file weights. "
        "Decorative missing alt is LOW; missing alt on a product/hero image is MEDIUM."
    ),
    "schema.validation.v3": (
        "List Schema.org types actually parsed from JSON-LD/microdata. Name missing required types only as MISSING, "
        "not as a fake Knowledge Graph failure. Do not invent sameAs URLs."
    ),
    "entity.graph.v3": (
        "Extract Organization, Person, Product, Service, Place entities that appear in schema or visible text. "
        "Do not add Wikidata/Wikipedia links that were not observed."
    ),
    "entity.knowledge_graph.v3": (
        "Evaluate sameAs URLs and entity clarity from observed schema only. "
        "Forbidden: claiming Knowledge Graph inclusion or Google panel presence."
    ),
    "content.depth.v3": (
        "Use measured word counts, heading trees, and body excerpts. Flag thin pages with the actual word count. "
        "Do not assume 300 words when count is missing — report not_measured."
    ),
    "content.eeat.v3": (
        "Record observed author names, credentials, citations, about/policy links. If none, E-E-A-T is NOT_IN_EVIDENCE. "
        "BEFORE finalizing authorship/credential claims, check ext_xxx (LinkedIn/Crunchbase). "
        "CONFIRMS → cite ev_xxx + ext_xxx, HIGH. CONTRADICTS → CONTESTED, cite both, route to verification.contradiction.v3. "
        "No usable ext_xxx → MEDIUM at best, SINGLE_SOURCE_UNVERIFIED."
    ),
    "content.quality.v3": (
        "Judge clarity and specificity of quoted passages. Do not score originality against the open web "
        "(we have no crawl of the web). Stay inside this site's text. Slogan-only heroes score weak."
    ),
    "content.topic_coverage.v3": (
        "Build a topic tree from H1/H2/H3 only. Gaps are topics implied by existing headings with no child section — "
        "not invented keyword lists."
    ),
    "content.cannibalization.v3": (
        "Compare crawled titles, H1s, and canonicals for collisions. Requires at least two pages; otherwise unavailable."
    ),
    "geo.extractability.v3": (
        "Find definition sentences, lists, tables, and FAQ blocks in the DOM. Score extractability only from those structures. "
        "Do not invent a 0–100 score that is not computed in code. Do not invent live citation rates."
    ),
    "geo.information_gain.v3": (
        "Flag original data only when the page contains numbers, tables, or methodology the evidence actually shows. "
        "No '35% citation lift' or similar."
    ),
    "geo.citation_readiness.v3": (
        "Map on-page claims to supporting sentences. Unsupported marketing adjectives are gaps. "
        "Do not predict live citation rate."
    ),
    "geo.structure.v3": (
        "Check for TL;DR, answer-first openings, FAQ markup, and entity-dense first paragraphs. Quote what exists."
    ),
    "ai_search.discoverability.v3": (
        "From the business profile and offerings IN EVIDENCE, list buyer queries the site could be asked. "
        "Queries are hypotheses, labeled SIMULATION_ONLY. Do not attach search volumes."
    ),
    "ai_search.chatgpt.v3": (
        "SIMULATION_ONLY. Using site evidence, say whether a model could answer each discoverability query from this DOM. "
        "Forbidden: fabricating a live ChatGPT citation, position, or screenshot."
    ),
    "ai_search.perplexity.v3": (
        "SIMULATION_ONLY. Same as ChatGPT agent for Perplexity-style citation eligibility from on-page facts only. "
        "Forbidden: fabricating live Perplexity citations or source lists."
    ),
    "ai_search.google.v3": (
        "Evaluate AI Overview / featured-snippet readiness from observed schema, lists, and definition blocks. "
        "Label INFERRED vs OBSERVED. Do not claim the site appears in AI Overviews."
    ),
    "ai_search.cross_engine.v3": (
        "Compare SIMULATION_ONLY results from ChatGPT, Perplexity, and Google agents already on the blackboard. "
        "If those results are missing, status=unavailable. Do not invent engine scores."
    ),
    "ux.experience.v3": (
        "Audit nav structure, viewport, heading scanability, and interaction labels from the DOM. "
        "Mobile readiness uses the viewport tag and observed layout cues only."
    ),
    "cro.conversion.v3": (
        "List observed CTAs, form fields, and hero actions with their exact text. If no CTA evidence, say MISSING. "
        "Primary CTA missing on homepage is HIGH. Weak verbs (Submit, Learn More) are MEDIUM with a rewrite."
    ),
    "trust.authority.v3": (
        "List observed testimonials, logos, badges, contact details, privacy/terms links. "
        "BEFORE finalizing trust/review/authority claims, check ext_xxx (G2/Capterra/Trustpilot/GBP/AmbitionBox). "
        "CONFIRMS → cite ev_xxx + ext_xxx, HIGH. CONTRADICTS → CONTESTED, cite both, route to verification.contradiction.v3. "
        "No usable ext_xxx → MEDIUM at best, SINGLE_SOURCE_UNVERIFIED. "
        "Do not invent customers, SOC2, or ISO unless those strings appear in evidence."
    ),
    "verification.adversarial.v3": (
        "Falsify prior claims: drop any claim whose evidence_refs are missing or whose statement is not entailed by the cited text. "
        "Do not add new commercial claims. Lower inflated severity."
    ),
    "verification.contradiction.v3": (
        "Find cross-page, cross-agent, and DOM-vs-external (ev_xxx vs ext_xxx) contradictions. "
        "If a claim is already CONTESTED, do not pick a winner between DOM and external evidence — leave status=CONTESTED and record both tokens. "
        "If none, return claims=[] and status=completed."
    ),
    "strategy.executive.v3": (
        "Using ONLY verified/supported claims that are CERTAIN or LIKELY, write a short executive story, what to ignore, and 7/30/90 actions. "
        "GUESSING findings inform the roadmap only and must not be presented with the same authority. "
        "A GUESSING + CRITICAL claim must already have passed verification.adversarial.v3; if it is still held, ignore it. "
        "Name the business, the offer, the buyer, and the constraint. "
        "No 3x citation promises, no rupee forecasts, no invented competitors, no TAM."
    ),
}

COPYWRITING_TASK_CARDS: Dict[str, str] = {
    "copywriting.seo.v3": (
        "Craft production-ready search-intent copy: Title strictly 50-60 characters (brand included, zero truncation risk), "
        "meta description strictly 140-160 characters (with active click trigger and primary value hook), and semantic H1/H2 header tree "
        "matching visitor search intent. Ban keyword stuffing. AFTER may not add facts absent from evidence."
    ),
    "copywriting.geo.v3": (
        "Formulate extractable, citation-ready content for AI Answer Engines (ChatGPT, Perplexity, Claude, Google SGE): "
        "40-60 word citable definitions, factual data hooks, structured Q&A / FAQ pairs, and entity-dense statements that answer engines can directly quote. "
        "No invented statistics."
    ),
    "copywriting.cro.v3": (
        "Audit 3-second hook clarity, high-converting value proposition framing, objection handling, and formulate high-intent "
        "CTA button microcopy with active value verbs (replacing weak 'Submit' or 'Click Here' with a verb + outcome grounded in the offer)."
    ),
    "copywriting.clarity.v3": (
        "Enforce brand voice consistency, radical elimination of buzzwords and empty consulting fluff (ban 'seamless', 'cutting-edge', "
        "'game-changing'), readability level (Flesch-Kincaid grade 7-9), and crisp ICP audience callouts when the page names an ICP."
    ),
    "copywriting.section.v3": (
        "Deconstruct page into modular, production-ready sections that need updating: Hero Header, Problem/Pain Agitation, Solution Architecture, "
        "Features/Value Drivers, AI Search FAQ Block, and Final Conversion Banner. For each section, provide concrete current vs proposed copy, "
        "purpose, and update urgency. BEFORE must match evidence."
    ),
}

ALL_TASK_CARDS: Dict[str, str] = {**TASK_CARDS, **COPYWRITING_TASK_CARDS}


def task_card_for(agent_id: str) -> str:
    return ALL_TASK_CARDS.get(agent_id, TASK_CARDS.get(agent_id, "Audit only what the evidence pack contains. Cite [ev_xxx]. Invent nothing."))

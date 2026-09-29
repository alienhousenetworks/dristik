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
        "Audit robots.txt presence and AI bot directives (GPTBot, ClaudeBot, PerplexityBot, Google-Extended), "
        "XML sitemap presence, HTTP status codes (4xx/5xx errors), redirect hops, and crawl depth from crawl manifest evidence. "
        "Emit distinct claims for missing robots.txt, missing XML sitemap, crawler blocking rules, or HTTP anomalies."
    ),
    "seo.indexability.v3": (
        "Audit canonical tags, self-referential canonical consistency, meta robots directives (noindex/nofollow), "
        "and X-Robots-Tag across all crawled URLs in evidence. "
        "Emit distinct findings for missing canonical, canonical mismatches, or unintended noindex directives."
    ),
    "seo.html.v3": (
        "Audit title tag length (<35 chars or >65 chars), meta description length (<70 chars, >160 chars, or absent), "
        "missing H1, multiple H1s, non-hierarchical heading skips (e.g. H1 to H3), empty heading tags, and landmark elements from DOM evidence. "
        "Quote exact strings and character counts. Emit distinct claims for each separate defect found across the crawled pages."
    ),
    "seo.internal_links.v3": (
        "Describe the observed internal link graph: orphan candidates, thin in-degree, generic anchors. "
        "Use only crawled URLs and recorded anchors."
    ),
    "seo.performance.v3": (
        "Audit server TTFB, render-blocking JS/CSS, payload weights by type, third-party scripts, and compression from crawl lab evidence. "
        "Never invent LCP, CLS, INP, or CrUX values. "
        "BEFORE finalizing any field CWV claim, verify ext_xxx from CrUX field data. "
        "CONFIRMS → cite ev_xxx + ext_xxx, HIGH. CONTRADICTS → CONTESTED, cite both, route to verification.contradiction.v3. "
        "No usable CrUX ext_xxx → state field telemetry is unmeasured. Deterministic lab measurements are evaluated independently. "
        "If a vital was not measured in CrUX, status=unavailable for that metric."
    ),
    "seo.security.v3": (
        "Audit HTTPS protocol, HSTS header (Strict-Transport-Security), Content-Security-Policy (CSP), "
        "X-Frame-Options (clickjacking protection), and X-Content-Type-Options (MIME sniffing) from response headers. "
        "Emit separate findings for each missing security header with its specific threat model and remediation directive."
    ),
    "seo.assets.v3": (
        "Audit every image in DOM evidence for missing alt attributes, empty alt attributes on informative images, "
        "and missing width/height attributes (causing CLS). Quote specific img src or selectors. "
        "Emit distinct findings for informative hero/product images lacking alt text."
    ),
    "schema.validation.v3": (
        "Audit structured data across JSON-LD and microdata. Check presence and completeness of Organization, "
        "WebSite, Service/Product, BreadcrumbList, and FAQPage. "
        "Flag missing required schema, missing sameAs entity links, and unlinked schema nodes with concrete JSON-LD fixes."
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
        "Evaluate the 8-dimension GEO rubric: definition sentence clarity, tabular data presence, FAQ block markup, "
        "entity disambiguation, statistics quotation readiness, and machine-parsable bullet lists. "
        "Flag low extractability and lack of structured answer passages with concrete DOM remediation."
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
        "Audit nav structure, mobile viewport configuration, heading scanability, button touch targets, and interaction labels from the DOM. "
        "Flag unlabelled form controls, missing aria-labels on interactive elements, or navigation hierarchies exceeding 3 levels."
    ),
    "cro.conversion.v3": (
        "Audit value proposition clarity, 3-second first impression hook, form fields and input accessibility, "
        "and primary CTA button microcopy. Flag generic or passive verbs ('Submit', 'Learn More', 'Click Here') with high-intent rewrites, "
        "and report form input fields lacking associated WCAG label elements as conversion friction barriers."
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
        "Review every crawled passage, not a sample of eight. Rewrite each one that is weak or only partly citable: "
        "we/our/you/your, a missing company name, or empty adjectives (seamless, cutting-edge, next-gen, world-class, robust). "
        "The rewrite must change the sentence: company as subject, third-person verbs, empty adjectives deleted, every original offer, place, and number kept. "
        "Do not paste the brand on the front of an unchanged sentence. Do not add customers, prices, certifications, or metrics that were not on the page. "
        "Leave a passage alone when it already names the company and states a concrete offer. No invented statistics."
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

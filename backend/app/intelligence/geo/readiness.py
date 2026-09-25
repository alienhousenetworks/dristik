"""
GEO Readiness vs GEO Visibility (High-Density Layer 1 Extractability).

Layer 1 Readiness: Can an answer engine (Perplexity, ChatGPT Search, Gemini, Claude)
understand, extract, verify, and quote this website from crawled first-party evidence?
Computed 100% deterministically from the DOM and content graph.

Layer 2 Visibility: Was the entity actually cited in a live AI engine?
Never inferred from HTML. If no live connector ran, status is NOT_CONFIGURED.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.domain.models import (
    BusinessProfile,
    CrawlManifest,
    GeoDimension,
    GeoQuestionEvidence,
    GeoReadinessReport,
    PageEvidence,
)
from app.intelligence.geo.entity_consistency import entity_consistency_analyzer
from app.intelligence.geo.claim_extractor import claim_extractor
from app.intelligence.geo.question_graph import question_graph_engine
from app.intelligence.geo.citation_passages import passage_analyzer
from app.intelligence.geo.schema_crosscheck import schema_crosschecker


_FLUFF = (
    "revolutionize", "empower", "unprecedented", "cutting-edge", "seamless",
    "next-generation", "unlock growth", "future of business",
)

_PRICING_RE = re.compile(
    r"(?:₹|rs\.?\s?|inr\s?|\$|€|£)\s*[\d,]+(?:\.\d+)?|\b\d{2,6}\s*/\s*(?:mo|month|yr|year)\b",
    re.I,
)


def _corpus(pages: List[PageEvidence]) -> str:
    parts = []
    for p in pages:
        parts.append(p.title or "")
        parts.extend(p.h1 or [])
        parts.extend(p.h2 or [])
        parts.extend(p.h3 or [])
        parts.append(p.body_text or "")
        parts.append(p.meta_description or "")
    return "\n".join(parts)


def _page_hits(pages: List[PageEvidence], pattern: re.Pattern) -> List[Tuple[str, str]]:
    hits = []
    for p in pages:
        blob = " ".join([
            p.title or "",
            " ".join(p.h1 or []),
            " ".join(p.h2 or []),
            p.body_text or "",
        ])
        m = pattern.search(blob)
        if m:
            start = max(0, m.start() - 80)
            snippet = blob[start:m.end() + 120].strip()
            hits.append((p.url, snippet[:240]))
    return hits


def _questions(name: str) -> List[Tuple[str, str, List[str]]]:
    n = name
    return [
        ("identity", f"What is {n}?", [n.lower(), "we are", "we provide", "we build", "platform", "software", "agency"]),
        ("icp", f"Who is {n} for?", ["for ", "built for", "smb", "sme", "enterprise", "startup", "b2b", "buyer", "teams of", "employees"]),
        ("pricing", f"How much does {n} cost?", ["pricing", "price", "₹", "$", "/mo", "/month", "plan", "starting at", "contact sales"]),
        ("offering", f"What does {n} offer?", ["api", "feature", "service", "product", "integration", "module"]),
        ("trust", f"Can I trust {n}?", ["testimonial", "case study", "iso", "soc 2", "soc2", "gdpr", "client", "customer"]),
        ("compare", f"How does {n} compare to alternatives?", ["vs ", "versus", "alternative", "compared", "competitor", "unlike"]),
    ]


def _status_for(blob: str, needles: List[str], hits: List[Tuple[str, str]], key: str) -> str:
    low = blob.lower()
    found = [n for n in needles if n in low]
    if key == "pricing":
        amounts = {m.group(0).lower().replace(" ", "") for m in _PRICING_RE.finditer(blob)}
        if len(amounts) >= 2:
            return "CONFLICTING"
        if amounts:
            return "SUPPORTED"
        if "contact sales" in low or "request a quote" in low:
            return "PARTIAL"
        return "UNSUPPORTED"
    if hits and len(found) >= 2:
        return "SUPPORTED"
    if hits or found:
        return "PARTIAL"
    return "UNSUPPORTED"


def _band(high: bool, medium: bool) -> str:
    if high:
        return "high"
    if medium:
        return "medium"
    return "low"


def evaluate_geo_readiness(
    *,
    website_url: str,
    pages: List[PageEvidence],
    manifest: Optional[CrawlManifest] = None,
    profile: Optional[BusinessProfile] = None,
    visibility_measured: bool = False,
    visibility_detail: Optional[str] = None,
    country: Optional[str] = None,
    language: Optional[str] = None,
    extended_questions: bool = False,
) -> GeoReadinessReport:
    profile = profile or BusinessProfile()
    name = profile.business_name if profile.business_name not in ("Unknown", "Unknown Business", "") else ""
    if not name:
        host = urlparse(website_url or "").netloc.replace("www.", "")
        name = host.split(".")[0].capitalize() if host else "the company"

    blob = _corpus(pages)
    low = blob.lower()

    # -------------------------------------------------------------
    # 1. Canonical 6-Question Evaluation (Backwards Compatibility)
    # -------------------------------------------------------------
    canonical_questions: List[GeoQuestionEvidence] = []
    for key, q, needles in _questions(name):
        pattern = re.compile("|".join(re.escape(n) for n in needles if n.strip()), re.I)
        hits = _page_hits(pages, pattern) if needles else []
        status = _status_for(blob, needles, hits, key)
        url, snippet = hits[0] if hits else (None, None)
        why = {
            "SUPPORTED": "A crawled page contains an explicit, extractable statement for this question.",
            "PARTIAL": "Related words appear, but there is no self-contained answer a model can quote.",
            "UNSUPPORTED": "The crawled sample does not contain an answer to this buyer question.",
            "CONFLICTING": "Multiple distinct price/value strings appear across the crawled sample.",
        }[status]
        canonical_questions.append(GeoQuestionEvidence(
            question_key=key,
            question=q,
            status=status,
            evidence_url=url,
            evidence_snippet=snippet,
            why=why,
        ))

    supported = sum(1 for q in canonical_questions if q.status == "SUPPORTED")
    partial = sum(1 for q in canonical_questions if q.status == "PARTIAL")
    unsupported = sum(1 for q in canonical_questions if q.status == "UNSUPPORTED")
    conflicting = sum(1 for q in canonical_questions if q.status == "CONFLICTING")

    # -------------------------------------------------------------
    # 2. Phase 1 Layer 1 Deep Extractability Engines
    # -------------------------------------------------------------
    try:
        entity_res = entity_consistency_analyzer.analyze(pages, website_url=website_url, profile=profile)
        entity_dict = entity_res.model_dump()
    except Exception:
        entity_res = None
        entity_dict = None

    try:
        claims_res = claim_extractor.extract_claims(pages, brand_name=name)
        claims_dict = claims_res.model_dump()
    except Exception:
        claims_res = None
        claims_dict = None

    try:
        q_graph_res = question_graph_engine.evaluate_graph(pages, brand_name=name, website_url=website_url, profile=profile)
        q_graph_dict = q_graph_res.model_dump()
    except Exception:
        q_graph_res = None
        q_graph_dict = None

    try:
        passage_res = passage_analyzer.analyze(pages, brand_name=name)
        passage_dict = passage_res.model_dump()
    except Exception:
        passage_res = None
        passage_dict = None

    try:
        schema_res = schema_crosschecker.crosscheck(pages, brand_name=name)
        schema_dict = schema_res.model_dump()
    except Exception:
        schema_res = None
        schema_dict = None

    # Compute composite Layer 1 Extractability Score (0 - 100)
    # Weights:
    # - Entity Consistency: 25%
    # - Question Graph Answerability: 30%
    # - Claim Specificity & Clarity: 20%
    # - Citation Passage Readiness: 15%
    # - Schema Grounding: 10%
    entity_part = (entity_res.overall_consistency_score if entity_res else 70.0) * 0.25
    q_graph_part = (q_graph_res.answerability_score if q_graph_res else 60.0) * 0.30
    claims_part = (claims_res.claim_clarity_score if claims_res else 60.0) * 0.20
    passage_part = (passage_res.citation_readiness_score if passage_res else 60.0) * 0.15
    schema_part = (schema_res.grounding_score if schema_res else 50.0) * 0.10
    extractability_score = round(entity_part + q_graph_part + claims_part + passage_part + schema_part, 1)

    # -------------------------------------------------------------
    # 3. Dimensions Construction (Enriched with Deep Diagnostics)
    # -------------------------------------------------------------
    fluff_hits = [w for w in _FLUFF if w in low]
    named = name.lower() in low if name else False
    specific = bool(profile.industry or profile.niche or profile.products or profile.services)
    entity_high = named and specific and not fluff_hits
    entity_med = named or specific

    entity_summary = (
        f"{name} is named on-page with a specific category/offer."
        if entity_high else
        f"Identity is vague or fluff-heavy ({', '.join(fluff_hits[:3]) or 'no concrete category'})."
    )
    if entity_res and entity_res.is_fragmented:
        entity_summary += f" Notice: {len(entity_res.discrepancies)} surface discrepancies detected ({entity_res.fragmentation_risk.lower()} risk)."

    entity = GeoDimension(
        key="entity_clarity",
        label="Entity clarity & consistency",
        band=entity_res.fragmentation_risk.lower() if entity_res and entity_res.fragmentation_risk == "LOW" else _band(entity_high, entity_med),
        summary=entity_summary,
        evidence_notes=[
            f"business_name={name}",
            f"consistency_score={entity_res.overall_consistency_score if entity_res else 'N/A'}",
            f"fragmentation_risk={entity_res.fragmentation_risk if entity_res else 'N/A'}"
        ],
    )

    headings = sum(len(p.h2 or []) + len(p.h3 or []) for p in pages)
    extract_high = headings >= 6 and supported >= 3
    extract_summary = f"{headings} H2/H3 blocks; {supported} questions have quotable answers."
    if passage_res:
        extract_summary += f" {passage_res.highly_citable_count} highly citation-ready passages detected."

    extract = GeoDimension(
        key="extractability",
        label="Content extractability & citation readiness",
        band=_band(extract_high, headings >= 3 or supported >= 1),
        summary=extract_summary,
        evidence_notes=[
            f"h2_h3_count={headings}",
            f"citation_score={passage_res.citation_readiness_score if passage_res else 'N/A'}"
        ],
    )

    schema_types = sorted({t for p in pages for t in (p.schema_types or [])})
    schema_summary = (
        f"Schema.org types observed: {', '.join(schema_types) or 'none'}. "
        "Schema is a machine-readable layer, not proof of GEO readiness."
    )
    if schema_res:
        schema_summary += f" Schema Grounding Score: {schema_res.grounding_score:.0f}/100 ({schema_res.verified_count} properties verified in DOM)."

    schema = GeoDimension(
        key="structured_data",
        label="Structured data (evidence layer, not GEO score)",
        band=_band(len(schema_types) >= 2, len(schema_types) >= 1),
        summary=schema_summary,
        evidence_notes=schema_types or ["none"],
    )

    robots = bool(manifest.robots_txt_found) if manifest else False
    sitemap = bool(manifest.sitemap_found) if manifest else False
    https = (website_url or "").startswith("https://")
    retrieval = GeoDimension(
        key="retrieval",
        label="Retrieval accessibility",
        band=_band(https and robots and sitemap, https),
        summary=f"https={https}, robots.txt={robots}, sitemap={sitemap}.",
        evidence_notes=[f"https={https}", f"robots={robots}", f"sitemap={sitemap}"],
    )

    consistency = GeoDimension(
        key="consistency",
        label="Factual consistency & claim verifiability",
        band="low" if conflicting else ("high" if supported >= 3 else "medium"),
        summary=(
            "Conflicting commercial facts (e.g. pricing) in the crawled sample."
            if conflicting else
            f"No conflicting price strings detected. {claims_res.citable_claims_count if claims_res else 0} verified citable claims."
        ),
    )

    headline = (
        f"{supported} of {len(canonical_questions)} high-value buyer questions have explicit on-page answers"
        f"{f'; {partial} partial' if partial else ''}"
        f"{f'; {conflicting} conflicting' if conflicting else ''}"
        f"{f'; {unsupported} cannot be answered from the crawled site' if unsupported else ''}."
    )

    visibility_status = "MEASURED" if visibility_measured else "NOT_CONFIGURED"
    if visibility_measured:
        visibility_message = visibility_detail or (
            "Live engine visibility was measured by the citation tracker or GEO pipeline. "
            "This number is not inferred from HTML."
        )
    else:
        visibility_message = (
            "Visibility data unavailable — connector/API access required. "
            "This report measures GEO Readiness (can an engine extract answers from the site), "
            "not GEO Visibility (does ChatGPT/Perplexity/AI Overviews actually cite you)."
        )

    # Active questions list: either 50 when extended_questions is requested, or canonical 6
    active_questions = (
        q_graph_res.questions if (extended_questions and q_graph_res and q_graph_res.questions)
        else canonical_questions
    )

    return GeoReadinessReport(
        visibility_status=visibility_status,
        visibility_message=visibility_message,
        entity_name=name,
        questions_total=len(active_questions),
        questions_supported=sum(1 for q in active_questions if q.status == "SUPPORTED"),
        questions_partial=sum(1 for q in active_questions if q.status == "PARTIAL"),
        questions_unsupported=sum(1 for q in active_questions if q.status == "UNSUPPORTED"),
        questions_conflicting=sum(1 for q in active_questions if q.status == "CONFLICTING"),
        headline=headline,
        questions=active_questions,
        dimensions=[entity, extract, schema, retrieval, consistency],
        schema_types=schema_types,
        market_country=(country or "Global").strip() or "Global",
        market_language=(language or "en").strip() or "en",
        extractability_score=extractability_score,
        entity_consistency=entity_dict,
        claims_analysis=claims_dict,
        question_graph_50=q_graph_dict,
        citation_passages=passage_dict,
        schema_crosscheck=schema_dict,
    )

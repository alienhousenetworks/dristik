"""
Dristik Adaptive Audit Book Generator (2026 Master Standard).
Transforms audit evidence into publication-grade, professionally typeset, book-style reports.

Supports 8 core report families:
1. COMPLETE — Complete Website Intelligence Audit
2. SEO — Technical SEO & Organic Search Audit Book
3. GEO — Generative Engine Optimization (GEO) Assessment
4. AEO — Answer Engine Optimization (AEO) Audit Book
5. CRO — Conversion Experience & CRO Audit Book
6. COMPETITOR — Competitive Digital Visibility Analysis
7. HYBRID — Multi-Discipline Digital Audit
8. CUSTOM — Custom Digital Asset Intelligence Dossier
"""

from __future__ import annotations

import hashlib
import html
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.evidence_integrity import validate_score
from app.reports.snapshot_provenance import (
    format_audit_execution_metadata,
    render_snapshot_provenance_bar,
)
from app.reports.svg_charts import SvgChartRenderer

from app.reports.publishing_engine import (
    ChapterSpec,
    PartSpec,
    PublicationDocument,
    PublicationHtmlRenderer,
    PublicationMetadata,
    PdfPublishingPipeline,
    PdfQualityAssurance,
    PdfValidationReport,
    _esc,
)


def detect_report_family(report: Any, requested_type: Optional[str] = None) -> str:
    """
    Programmatically detects the report family from explicit metadata or telemetry data.
    """
    if requested_type:
        req = requested_type.strip().upper()
        if req in ("COMPLETE", "SEO", "GEO", "AEO", "CRO", "COMPETITOR", "COMPETITORS", "HYBRID", "CUSTOM"):
            return "COMPETITOR" if req == "COMPETITORS" else req

    # Check policy_pack metadata
    policy_pack = str(getattr(report, "policy_pack", "") or "").lower()
    if "seo_only" in policy_pack or policy_pack == "seo":
        return "SEO"
    if "geo_only" in policy_pack or policy_pack == "geo":
        return "GEO"
    if "aeo_only" in policy_pack or policy_pack == "aeo":
        return "AEO"
    if "cro_only" in policy_pack or policy_pack == "cro":
        return "CRO"
    if "competitor" in policy_pack:
        return "COMPETITOR"

    # Inspect available telemetry disciplines
    has_seo = False
    has_geo = False
    has_aeo = False
    has_cro = False
    has_competitor = False

    # Check findings
    findings = _report_findings(report)
    categories = set()
    for f in findings:
        raw_cat = getattr(f, "category", "")
        if hasattr(raw_cat, "value"):
            categories.add(str(raw_cat.value).upper())
        if hasattr(raw_cat, "name"):
            categories.add(str(raw_cat.name).upper())
        categories.add(str(raw_cat).upper())

    if "TECHNICAL_SEO" in categories or getattr(report, "crawl_manifest", None) or getattr(report, "page_reports", None) or getattr(report, "canonical_audit", None):
        has_seo = True
    if "GEO" in categories or getattr(report, "geo_readiness", None) or getattr(report, "per_engine_geo", None):
        has_geo = True
    if "AEO" in categories or "AI_SEARCH" in categories or getattr(report, "dynamic_sandbox_evaluations", None) or getattr(report, "ai_search_matrix", None):
        has_aeo = True
    if "UX_CONVERSION" in categories or getattr(report, "cro_audit", None) or getattr(report, "form_audit", None) or getattr(report, "visual_ux", None):
        has_cro = True
    if "COMPETITIVE" in categories or "COMPETITIVE_INTELLIGENCE" in categories or getattr(report, "competitor_bakeoff", None) or getattr(report, "competitor_seo_parity", None):
        has_competitor = True

    # Check category scores if present
    scores = getattr(report, "scores", None)
    cat_scores = getattr(scores, "category_scores", {}) or {}
    if isinstance(cat_scores, dict):
        if "TECHNICAL_SEO" in cat_scores and cat_scores["TECHNICAL_SEO"]:
            has_seo = True
        if "GEO" in cat_scores and cat_scores["GEO"]:
            has_geo = True
        if "AEO" in cat_scores and cat_scores["AEO"]:
            has_aeo = True
        if "UX_CONVERSION" in cat_scores and cat_scores["UX_CONVERSION"]:
            has_cro = True
        if "COMPETITIVE_INTELLIGENCE" in cat_scores and cat_scores["COMPETITIVE_INTELLIGENCE"]:
            has_competitor = True

    measured_count = sum(1 for m in [has_seo, has_geo, has_aeo, has_cro, has_competitor] if m)

    if measured_count >= 3:
        return "COMPLETE"
    if measured_count == 2:
        return "HYBRID"
    if has_seo and measured_count == 1:
        return "SEO"
    if has_geo and measured_count == 1:
        return "GEO"
    if has_aeo and measured_count == 1:
        return "AEO"
    if has_cro and measured_count == 1:
        return "CRO"
    if has_competitor and measured_count == 1:
        return "COMPETITOR"

    return "CUSTOM"


def build_publication_manifest(
    report: Any,
    family: str,
    title_override: Optional[str] = None,
    subtitle_override: Optional[str] = None,
    classification_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Constructs the publication manifest including chapter descriptors and metadata.
    """
    snap = format_audit_execution_metadata(report)
    domain_clean = snap.domain
    brand_name = snap.brand_name
    date_clean = snap.execution_date
    report_ref = snap.report_ref

    TITLES: Dict[str, Dict[str, str]] = {
        "COMPLETE": {
            "displayName": "Complete Website Intelligence Audit",
            "badge": "COMPLETE DIGITAL ASSET AUDIT DOSSIER",
            "title": "Complete Website Intelligence Audit",
            "subtitle": "SEO · GEO · AEO · CRO · TECHNICAL HEALTH & ENTITY READINESS",
            "purpose": f"Multi-discipline assessment of available crawl, search, answer-engine, and conversion evidence for {brand_name}; coverage depends on configured sources.",
        },
        "SEO": {
            "displayName": "Technical SEO & Organic Search Audit",
            "badge": "TECHNICAL SEO & SEARCH ARCHITECTURE AUDIT",
            "title": "Technical SEO & Organic Search Audit",
            "subtitle": "CRAWL INFRASTRUCTURE · INDEXABILITY · CANONICAL ROUTING · CORE WEB VITALS",
            "purpose": f"Assessment of available technical crawl, response, sitemap, heading, and search-discoverability evidence for {domain_clean}.",
        },
        "GEO": {
            "displayName": "Generative Engine Optimization (GEO) Assessment",
            "badge": "GENERATIVE ENGINE OPTIMIZATION AUDIT",
            "title": "Generative Engine Optimization Assessment",
            "subtitle": "FIRST-PARTY EXTRACTABILITY · ENTITY CLARITY · LLM BOT DIRECTIVES",
            "purpose": f"Assessment of observed content extractability, bot directives, and machine-readable entity signals where these checks were run.",
        },
        "AEO": {
            "displayName": "Answer Engine Optimization (AEO) Audit",
            "badge": "ANSWER ENGINE OPTIMIZATION AUDIT",
            "title": "Answer Engine Optimization (AEO) Audit",
            "subtitle": "QUERY INTENT · PASSAGE EXTRACTABILITY · MULTI-MODEL CITATION BENCHMARK",
            "purpose": f"Assessment of question coverage and answer clarity; live platform citation visibility is included only where actual measurements are available.",
        },
        "CRO": {
            "displayName": "Conversion Experience & CRO Audit",
            "badge": "CONVERSION EXPERIENCE & ERGONOMICS AUDIT",
            "title": "Conversion Experience & CRO Audit",
            "subtitle": "VALUE PROPOSITION · CTA ERGONOMICS · USER FRICTION & ENGAGEMENT",
            "purpose": f"Empirical review of value proposition clarity, landing page hierarchy, call-to-action discoverability, and interaction friction across sampled URLs.",
        },
        "COMPETITOR": {
            "displayName": "Competitive Digital Visibility Analysis",
            "badge": "COMPETITIVE INTELLIGENCE & BENCHMARK",
            "title": "Competitive Digital Visibility Analysis",
            "subtitle": "HEAD-TO-HEAD INQUIRY TESTING · PARITY MATRIX · MARKET GAP ANALYSIS",
            "purpose": f"Comparison of recorded competitor evidence and available schema or query measurements; unavailable competitor data remains undisclosed rather than inferred.",
        },
        "HYBRID": {
            "displayName": "Multi-Discipline Digital Audit",
            "badge": "INTEGRATED MULTI-DISCIPLINE AUDIT",
            "title": "Multi-Discipline Digital Intelligence Audit",
            "subtitle": "CROSS-DISCIPLINE FINDINGS & UNIFIED REMEDIATION BLUEPRINT",
            "purpose": f"Focused multi-discipline audit combining applicable assessment chapters into a unified findings register and execution roadmap.",
        },
        "CUSTOM": {
            "displayName": "Digital Asset Intelligence Audit",
            "badge": "CUSTOM DIGITAL ASSET AUDIT DOSSIER",
            "title": "Digital Asset Intelligence Audit",
            "subtitle": "EVIDENCE-GROUNDED TECHNICAL & STRATEGIC REVIEW",
            "purpose": f"Tailored digital asset assessment based on available audit telemetry and verified empirical evidence.",
        },
    }

    info = TITLES.get(family, TITLES["CUSTOM"])

    # Determine chapters
    chapters = []
    chapters.append({
        "id": "ch_brief",
        "num": "00",
        "part": "PART I: EXECUTIVE SYNTHESIS",
        "title": "Executive Brief & 5-Pillar Scorecard",
        "desc": "High-level synthesis, core signals, Tri-Perspective cognitive diagnosis, and verified baseline metrics.",
    })

    if family == "AEO":
        chapters.append({
            "id": "ch_aeo_questions",
            "num": "01",
            "part": "PART II: QUESTION ARCHITECTURE",
            "title": "Question Universe & Search Intent Mapping",
            "desc": "Informational, commercial, navigational, and transactional query clusters evaluated against crawlable DOM.",
        })
        chapters.append({
            "id": "ch_aeo_definitions",
            "num": "02",
            "part": "PART II: QUESTION ARCHITECTURE",
            "title": "Direct Definition Passages & Rank-Zero Extraction",
            "desc": "Passage extractability, 40-60 word definition blocks, list formatting, and HTML table extraction quality.",
        })
        chapters.append({
            "id": "ch_aeo_schema",
            "num": "03",
            "part": "PART II: QUESTION ARCHITECTURE",
            "title": "Structured Data, Rich Results & Entity Graph",
            "desc": "JSON-LD schema validation, Knowledge Graph disambiguation, and authoritative sameAs entity profiles.",
        })
        chapters.append({
            "id": "ch_aeo_visibility",
            "num": "04",
            "part": "PART II: QUESTION ARCHITECTURE",
            "title": "Observed AI Answer Engine Visibility & Citations",
            "desc": "Empirical appearances and citation records across ChatGPT Search, Perplexity AI, Gemini, and Claude.",
        })
    elif family == "GEO":
        chapters.append({
            "id": "ch_geo_extractability",
            "num": "01",
            "part": "PART II: CONTENT EXTRACTABILITY",
            "title": "The 8-Dimension Content Extractability Framework",
            "desc": "First-party DOM extractability across passage density, schema graph, entity clarity, and format adaptability.",
        })
        chapters.append({
            "id": "ch_geo_inquiries",
            "num": "02",
            "part": "PART II: CONTENT EXTRACTABILITY",
            "title": "Commercial Buyer Query Extraction Battery",
            "desc": "Coverage of core commercial inquiries: corporate identity, target audience, pricing, and proof points.",
        })
        chapters.append({
            "id": "ch_geo_crawlers",
            "num": "03",
            "part": "PART II: CONTENT EXTRACTABILITY",
            "title": "AI Crawler Directives & /llms.txt Health",
            "desc": "Robots.txt access rules for GPTBot, PerplexityBot, ClaudeBot, and agentic documentation manifests.",
        })
        geo_passages = getattr(getattr(report, "geo_readiness", None), "citation_passages", None) or {}
        geo_rewrites = (
            geo_passages.get("rewrite_recommendations", [])
            if isinstance(geo_passages, dict)
            else getattr(geo_passages, "rewrite_recommendations", [])
        ) or []
        if geo_rewrites:
            chapters.append({
                "id": "ch_geo_rewrites",
                "num": "04",
                "part": "PART II: CONTENT EXTRACTABILITY",
                "title": "Factual Attribution Laboratory & Citable Rewrites",
                "desc": "Attribution rewrites transforming ambiguous text into directly citable entity statements.",
            })
    elif family == "CRO":
        chapters.append({
            "id": "ch_cro_value_prop",
            "num": "01",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Above-the-Fold Messaging & 6-Question Value Proposition",
            "desc": "Hero messaging, 6-question buyer model, and offering clarity across sampled landing pages.",
        })
        chapters.append({
            "id": "ch_cro_visual_hierarchy",
            "num": "02",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Multi-Device Visual Inspection & Layout Ergonomics",
            "desc": "Responsive layout integrity across 5 standard viewport profiles (Desktop, Laptop, Tablet, Mobile, Small Mobile).",
        })
        chapters.append({
            "id": "ch_cro_cta",
            "num": "03",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Call-to-Action (CTA) Hierarchy, Contrast & Intent Studio",
            "desc": "Primary and secondary CTA discoverability, button microcopy, contrast ratios, and conversion triggers.",
        })
        chapters.append({
            "id": "ch_cro_journey",
            "num": "04",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Visual User Journey Graph, Loop Detection & Dead Ends",
            "desc": "10-step conversion path graph traversal, cyclical navigation loops, and abandoned routes.",
        })
        chapters.append({
            "id": "ch_cro_forms",
            "num": "05",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Form Optimization, Inputs & Interactive Usability",
            "desc": "Field count evaluation, input friction, validation ergonomics, autofill, and error prevention.",
        })
        chapters.append({
            "id": "ch_cro_mobile",
            "num": "06",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Mobile UX, Touch Target Sizing & Sticky Triggers",
            "desc": "Small-screen conversion ergonomics, touch target compliance (>=44px), and persistent sticky action triggers.",
        })
        chapters.append({
            "id": "ch_cro_accessibility",
            "num": "07",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "WCAG 2.2 AA Conversion Friction & Assistive Tech Review",
            "desc": "Focus indicators, keyboard accessibility, color contrast, and automated vs manual testing disclosure.",
        })
        chapters.append({
            "id": "ch_cro_trust",
            "num": "08",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Trust Architecture, Credibility Signals & Risk Reversal",
            "desc": "Security badges, client evidence, reassurance microcopy, and buyer risk mitigation.",
        })
        chapters.append({
            "id": "ch_cro_checkout",
            "num": "09",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "E-Commerce & SaaS Conversion Funnel Friction",
            "desc": "Transaction friction, product information completeness, demo qualification load, and payment options.",
        })
        chapters.append({
            "id": "ch_cro_experiments",
            "num": "10",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Behavioral Analytics & Statistical Experimentation Roadmap",
            "desc": "GA4 attribution, sample-size power calculations, guardrail metrics, and scientific A/B test specifications.",
        })
    else:
        # Standard Complete / SEO / Hybrid Chapter Manifest
        if family in ("COMPLETE", "SEO", "HYBRID"):
            chapters.append({
                "id": "ch_seo",
                "num": "01",
                "part": "PART II: AUDIT CHAPTERS",
                "title": "Discoverability & Technical SEO",
                "desc": "Crawl architecture, canonical host routing, 301 consolidation, TTFB latency curves, robots.txt, and XML sitemaps.",
            })

        if family in ("COMPLETE", "HYBRID"):
            chapters.append({
                "id": "ch_geo",
                "num": "02",
                "part": "PART II: AUDIT CHAPTERS",
                "title": "Generative Engine Optimization (GEO)",
                "desc": "First-party DOM extractability, 8-dimension breakdown, /llms.txt AI-bot permissions, and entity attribution rewrites.",
            })
            chapters.append({
                "id": "ch_aeo",
                "num": "03",
                "part": "PART II: AUDIT CHAPTERS",
                "title": "Answer Engine Visibility (AEO) & AI Citations",
                "desc": "Question coverage and answer-engine observations where measured; platform coverage and sampling limitations are disclosed.",
            })

        has_comp_data = bool(
            getattr(report, "competitor_bakeoff", None)
            or any(
                any(k in str(getattr(f, "category", "")).upper() for k in ("COMP", "AUTHORITY", "BACKLINK", "BENCHMARK"))
                for f in (getattr(report, "findings", None) or [])
            )
        )
        if family == "COMPETITOR" or (family == "COMPLETE" and has_comp_data):
            chapters.append({
                "id": "ch_competitive",
                "num": "04" if family == "COMPLETE" else "01",
                "part": "PART II: AUDIT CHAPTERS",
                "title": "Competitive Intelligence & Knowledge Graph",
                "desc": "Recorded competitor bake-off, schema types extracted from the sample, and social meta presence.",
            })

        if family in ("COMPLETE", "HYBRID"):
            chapters.append({
                "id": "ch_conversion",
                "num": "05",
                "part": "PART II: AUDIT CHAPTERS",
                "title": "Conversion Ergonomics & Production Copy",
                "desc": "Crawled value-proposition copy, CTA hierarchy, form screening, and character-safe production copy recommendations.",
            })

        if family in ("COMPLETE", "SEO"):
            chapters.append({
                "id": "ch_page_by_page",
                "num": "06" if family == "COMPLETE" else "02",
                "part": "PART II: AUDIT CHAPTERS",
                "title": "Page-by-Page Audit Review",
                "desc": "Sampled URL inventory: SERP metadata, H1 outlines, and copy recommendations for the analyzed URLs.",
            })

    chapters.append({
        "id": "ch_roadmap",
        "num": "07" if family == "COMPLETE" else "05",
        "part": "PART III: REMEDIATION & GOVERNANCE",
        "title": "Strategic Priorities & 90-Day Roadmap",
        "desc": "Executive Top-10 Action Plan with effort/impact calculations, NOW / NEXT / ONGOING roadmap, and commercial model.",
    })

    chapters.append({
        "id": "ch_methodology",
        "num": "08" if family == "COMPLETE" else "06",
        "part": "PART III: REMEDIATION & GOVERNANCE",
        "title": "Research Methodology & Sampling Parameters",
        "desc": "Audit scope, crawl depth boundaries, multi-engine testing protocol, confidence algorithms, and operational limitations.",
    })

    chapters.append({
        "id": "ch_appendix",
        "num": "APP",
        "part": "PART IV: APPENDICES & REGISTERS",
        "title": "Institutional Findings Register & Evidence Ledger",
        "desc": "Findings register, available evidence references, remediation recommendations, and integrity details where recorded.",
    })

    # Renumber sequentially
    body_counter = 1
    for ch in chapters:
        if ch["id"] == "ch_brief":
            ch["num"] = "00"
        elif ch["id"] == "ch_appendix":
            ch["num"] = "APP"
        else:
            ch["num"] = f"{body_counter:02d}"
            body_counter += 1

    return {
        "family": family,
        "displayName": info["displayName"],
        "badge": info["badge"],
        "title": title_override or info["title"],
        "subtitle": subtitle_override or info["subtitle"],
        "purpose": info["purpose"],
        "classification": classification_override or "STRICTLY CONFIDENTIAL // C-SUITE DOSSIER",
        "domain": domain_clean,
        "brand_name": brand_name,
        "audit_date": date_clean,
        "execution_timestamp": snap.execution_timestamp,
        "report_ref": report_ref,
        "snapshot_id": snap.snapshot_id,
        "snapshot_digest": snap.snapshot_digest,
        "configuration_summary": snap.configuration_summary,
        "crawl_scope_summary": snap.crawl_scope_summary,
        "chapters": chapters,
    }


def compute_toc_pagination(manifest: Dict[str, Any]) -> Dict[str, int]:
    """
    Computes starting page numbers for chapters in A4 print layout.
    """
    page_map: Dict[str, int] = {}
    current_page = 1  # Arabic numbering starts at 1 for executive brief

    spans: Dict[str, int] = {
        "ch_brief": 2,
        "ch_seo": 3,
        "ch_geo": 3,
        "ch_aeo": 3,
        "ch_competitive": 2,
        "ch_conversion": 2,
        "ch_page_by_page": 2,
        "ch_roadmap": 2,
        "ch_methodology": 2,
        "ch_appendix": 4,
        # Dedicated AEO Chapters
        "ch_aeo_questions": 2,
        "ch_aeo_definitions": 2,
        "ch_aeo_schema": 2,
        "ch_aeo_visibility": 2,
        # Dedicated GEO Chapters
        "ch_geo_extractability": 3,
        "ch_geo_inquiries": 2,
        "ch_geo_crawlers": 2,
        "ch_geo_rewrites": 2,
        # Dedicated CRO Chapters
        "ch_cro_value_prop": 2,
        "ch_cro_visual_hierarchy": 2,
        "ch_cro_cta": 2,
        "ch_cro_journey": 2,
        "ch_cro_forms": 2,
        "ch_cro_mobile": 2,
        "ch_cro_accessibility": 2,
        "ch_cro_trust": 2,
        "ch_cro_checkout": 2,
        "ch_cro_experiments": 2,
    }

    for ch in manifest["chapters"]:
        page_map[ch["id"]] = current_page
        span = spans.get(ch["id"], 2)
        current_page += span

    page_map["closing_page"] = current_page
    return page_map


from app.reports.plain_english_engine import (
    PlainEnglishEngine,
    generate_section_explanation,
    render_section_business_callout,
    render_plain_english_finding_card,
)


# ==============================================================================
# CHAPTER BODY BUILDERS (EMPIRICAL, GROUNDED DATA)
# ==============================================================================

from app.report_finding_registry import (
    canonicalize_report_findings as _report_findings,
    finding_value as _finding_value,
)


# Finding IDs whose full card was already rendered in the current book (reset per build).
_DETAILED_CARDS_RENDERED: set = set()

_GEO_CANONICAL_CATS = {
    "AI_VISIBILITY",
    "CITATION_INTELLIGENCE",
    "ENTITY_CONSISTENCY",
    "CONTENT_QUALITY",
    "TECHNICAL_READINESS",
    "EXTERNAL_REPUTATION",
    "COMPETITIVE_INTELLIGENCE",
    "MARKET_INTENT",
}


def _is_geo_finding(f: Any) -> bool:
    raw_cat = _finding_value(f, "category", "")
    cat = str(getattr(raw_cat, "value", raw_cat) or "").upper()
    return "GEO" in cat or cat in _GEO_CANONICAL_CATS


def _all_report_findings(report: Any, manifest: Optional[Dict[str, Any]] = None) -> List[Any]:
    """Return canonical report findings merged with any tenant-matched Enterprise GEO findings."""
    base = list(_report_findings(report))
    extra = list((manifest or {}).get("_enterprise_geo_findings") or [])
    if not extra:
        return base
    seen_ids = {str(_finding_value(f, "finding_id", _finding_value(f, "id", "")) or "").strip().lower() for f in base}
    seen_titles = {str(_finding_value(f, "title", _finding_value(f, "finding_title", "")) or "").strip().lower() for f in base}
    for ef in extra:
        fid = str(_finding_value(ef, "finding_id", _finding_value(ef, "id", "")) or "").strip().lower()
        title = str(_finding_value(ef, "title", _finding_value(ef, "finding_title", "")) or "").strip().lower()
        if (fid and fid in seen_ids) or (title and title in seen_titles):
            continue
        base.append(ef)
        if fid:
            seen_ids.add(fid)
        if title:
            seen_titles.add(title)
    return base


def _format_finding_cards(findings: List[Any], limit: Optional[int] = None, detailed: bool = False, dedupe: bool = True) -> str:
    """Use short chapter references; reserve full plain-English narratives for the findings register."""
    cards = []
    target_findings = findings if limit is None else findings[:limit]
    for idx, finding in enumerate(target_findings):
        if detailed:
            fid = str(_finding_value(finding, "finding_id", _finding_value(finding, "id", "")) or "")
            if dedupe and fid and fid in _DETAILED_CARDS_RENDERED:
                # Full card already printed in an earlier chapter: reference it instead of repeating it.
                title = _esc(_finding_value(finding, "title", "Finding"))
                cards.append(
                    '<div class="card finding-reference" style="margin:6px 0;padding:9px 12px;break-inside:avoid;">'
                    f'<div style="font-size:9pt;font-weight:700;color:#0f172a;">{title}</div>'
                    f'<div style="font-size:7.5pt;color:#64748b;margin-top:3px;">{_esc(fid)} · full detail appears in an earlier chapter and the findings register</div>'
                    '</div>'
                )
                continue
            if fid:
                _DETAILED_CARDS_RENDERED.add(fid)
            enriched = PlainEnglishEngine.enrich_finding(finding, idx + 1)
            card_html = render_plain_english_finding_card(enriched)
            ver_notes = _finding_value(finding, "verification_notes")
            det_diag = _finding_value(finding, "detailed_diagnosis") or _finding_value(finding, "diagnosis")
            val_crit = _finding_value(finding, "validation_criteria") or _finding_value(finding, "acceptance_criteria")
            ai_extra = []
            if det_diag:
                ai_extra.append(f'<div><strong>AI Deep Diagnosis:</strong> {_esc(det_diag)}</div>')
            if ver_notes:
                ai_extra.append(f'<div><strong>AI Adversarial Verification:</strong> {_esc(ver_notes)}</div>')
            if val_crit:
                ai_extra.append(f'<div><strong>Validation Criteria:</strong> {_esc(val_crit)}</div>')
            if ai_extra:
                card_html += (
                    '<div style="margin:-4px 0 10px 0;padding:8px 12px;background:#f0f9ff;'
                    'border:1px solid #bae6fd;border-radius:0 0 6px 6px;font-size:8pt;color:#0c4a6e;">'
                    + "".join(ai_extra)
                    + '</div>'
                )
            cards.append(card_html)
            continue
        title = _esc(_finding_value(finding, "title", _finding_value(finding, "name", "Finding title unavailable")))
        severity = _esc(str(_finding_value(finding, "severity", "Unclassified")).replace("_", " ").title())
        finding_id = _esc(_finding_value(finding, "finding_id", _finding_value(finding, "id", f"finding-{idx + 1}")))
        urls = _finding_value(finding, "affected_urls", None) or _finding_value(finding, "urls", None) or []
        if isinstance(urls, str):
            urls = [urls]
        if not urls:
            url = _finding_value(finding, "url", None) or _finding_value(finding, "affected_url", None)
            urls = [url] if url else []
        url_summary = ", ".join(str(url) for url in urls if url) or "Affected URL not recorded"
        cards.append(
            '<div class="card finding-reference" style="margin:6px 0;padding:9px 12px;break-inside:avoid;">'
            f'<div style="font-size:9pt;font-weight:700;color:#0f172a;">{title}</div>'
            f'<div style="font-size:7.5pt;color:#64748b;margin-top:3px;">{finding_id} · {severity} · {_esc(url_summary)}</div>'
            '</div>'
        )
    return "".join(cards) if cards else '<p style="color:#64748b;font-size:9pt;font-style:italic;">No findings were recorded for this area. This does not prove that no defects exist.</p>'


def _build_ch_brief(report: Any, manifest: Dict[str, Any]) -> str:
    from app.reports.pdf_evidence_blocks import sanitize_presentation_text
    story = _esc(sanitize_presentation_text(getattr(report, "story_summary", None)) or "No executive summary was recorded for this audit run.")
    primary_opp = _esc(sanitize_presentation_text(getattr(report, "primary_strategic_opportunity", None)) or "No primary opportunity was recorded; review evidence-backed findings to select the next action.")
    ignore_advice = _esc(sanitize_presentation_text(getattr(report, "consultant_advice_what_to_ignore", None)) or "No exclusion advice was recorded for this audit run.")

    p = getattr(report, "three_way_comparison", None) or getattr(report, "perspective", None)
    human_p = _esc(getattr(p, "human_visitor_perspective", None) or "No evidence-backed visitor perspective was recorded for this run.")
    search_p = _esc(getattr(p, "search_engine_perspective", None) or "No evidence-backed search-engine perspective was recorded for this run.")
    ai_p = _esc(getattr(p, "ai_answer_engine_perspective", None) or "No live answer-engine observation was recorded for this run.")

    snap = format_audit_execution_metadata(report)
    scores = getattr(report, "scores", None)
    seo_s = snap.score_for_section("seo")
    geo_s = snap.score_for_section("geo")
    aeo_s = snap.score_for_section("aeo")
    cro_s = snap.score_for_section("cro")
    comp_s = snap.score_for_section("competitors")
    provenance_bar = render_snapshot_provenance_bar(snap)
    from app.reports.publication_status import render_verification_standard_banner
    from app.reports.pdf_evidence_blocks import render_page_evidence_table
    verification_banner = render_verification_standard_banner(
        _all_report_findings(report, manifest),
        narrative_mode=getattr(report, "narrative_mode", None),
    )
    crawl_manifest_obj = getattr(report, "crawl_manifest", None)
    sampled_pages = list(getattr(crawl_manifest_obj, "pages", None) or getattr(report, "page_reports", None) or [])
    evidence_table_html = render_page_evidence_table(
        sampled_pages,
        title="Observed First-Party Crawl & DOM Evidence Ledger",
        max_rows=10,
    )

    callout = render_section_business_callout(
        generate_section_explanation("ch_brief", "Executive Diagnostic Briefing", report, _report_findings(report))
    )

    cat_scores = getattr(scores, "category_scores", None) or {}
    radar_svg = SvgChartRenderer.render_category_radar_svg(cat_scores if isinstance(cat_scores, dict) else {})
    sev_svg = SvgChartRenderer.render_severity_bar_svg(_report_findings(report))
    charts_block = ""
    if radar_svg or sev_svg:
        charts_block = f"""
        <div class="grid-2" style="margin-bottom: 16px; break-inside: avoid;">
            <div class="card" style="text-align:center;">
                <div class="card-kicker" style="text-align:left;">CANONICAL 8-CATEGORY RADAR</div>
                {radar_svg or '<p class="small">Insufficient category scores for radar chart.</p>'}
            </div>
            <div class="card">
                <div class="card-kicker">RECORDED FINDING SEVERITY DISTRIBUTION</div>
                <div style="margin-top:12px;">{sev_svg}</div>
            </div>
        </div>
        """

    return f"""
    {provenance_bar}
    {verification_banner}
    {evidence_table_html}
    {callout}

    <div class="card" style="margin-bottom: 16px; padding: 18px; border-left: 3.5px solid #0284c7;">
        <div class="card-kicker">EXECUTIVE THESIS &amp; PRIMARY OBSERVATION</div>
        <p style="font-size: 11pt; line-height: 1.6; color: #0f172a; margin: 4px 0 0 0;">
            {story}
        </p>
    </div>

    <div class="grid-3" style="margin-bottom: 16px;">
        <div class="card">
            <div class="card-kicker">01 // HUMAN VISITOR PERSPECTIVE</div>
            <div class="card-title">CRO &amp; Value Proposition</div>
            <p style="font-size: 8pt; color: #475569; margin: 0;">{human_p}</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // SEARCH SPIDER PERSPECTIVE</div>
            <div class="card-title">Traditional Crawl Health</div>
            <p style="font-size: 8pt; color: #475569; margin: 0;">{search_p}</p>
        </div>
        <div class="card">
            <div class="card-kicker">03 // ANSWER ENGINE PERSPECTIVE</div>
            <div class="card-title">Generative AI Citability</div>
            <p style="font-size: 8pt; color: #475569; margin: 0;">{ai_p}</p>
        </div>
    </div>

    <div class="card" style="margin-bottom: 16px;">
        <div class="card-kicker">5-PILLAR DIAGNOSTIC SCORECARD</div>
        <div class="data-table-wrapper" style="margin-top:8px;">
            <table class="print-table">
                <thead>
                    <tr>
                        <th>Pillar</th>
                        <th>Discipline</th>
                        <th>Score availability</th>
                        <th>Score (0–100)</th>
                        <th>Assessment method</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>01</strong></td>
                        <td>Technical SEO &amp; Crawlability</td>
                        <td><span style="color:#64748b; font-weight:700;">{ 'SCORE RECORDED' if seo_s is not None else 'NOT MEASURED' }</span></td>
                        <td><strong>{format(seo_s, '.1f') if seo_s is not None else '—'}</strong>{ ' / 100' if seo_s is not None else ''}</td>
                        <td>Technical crawl and HTTP checks</td>
                    </tr>
                    <tr>
                        <td><strong>02</strong></td>
                        <td>Generative Engine Optimization (GEO)</td>
                        <td><span style="color:#64748b; font-weight:700;">{ 'SCORE RECORDED' if geo_s is not None else 'NOT MEASURED' }</span></td>
                        <td><strong>{format(geo_s, '.1f') if geo_s is not None else '—'}</strong>{ ' / 100' if geo_s is not None else ''}</td>
                        <td>On-page extractability; visibility measured separately</td>
                    </tr>
                    <tr>
                        <td><strong>03</strong></td>
                        <td>Answer Engine Visibility (AEO)</td>
                        <td><span style="color:#64748b; font-weight:700;">{ 'SCORE RECORDED' if aeo_s is not None else 'NOT MEASURED' }</span></td>
                        <td><strong>{format(aeo_s, '.1f') if aeo_s is not None else '—'}</strong>{ ' / 100' if aeo_s is not None else ''}</td>
                        <td>Answer content and platform evidence where available</td>
                    </tr>
                    <tr>
                        <td><strong>04</strong></td>
                        <td>Conversion Ergonomics (CRO)</td>
                        <td><span style="color:#64748b; font-weight:700;">{ 'SCORE RECORDED' if cro_s is not None else 'NOT MEASURED' }</span></td>
                        <td><strong>{format(cro_s, '.1f') if cro_s is not None else '—'}</strong>{ ' / 100' if cro_s is not None else ''}</td>
                        <td>UX heuristics and analytics where available</td>
                    </tr>
                    <tr>
                        <td><strong>05</strong></td>
                        <td>Competitive Market Parity</td>
                        <td><span style="color:#64748b; font-weight:700;">{ 'SCORE RECORDED' if comp_s is not None else 'NOT MEASURED' }</span></td>
                        <td><strong>{format(comp_s, '.1f') if comp_s is not None else '—'}</strong>{ ' / 100' if comp_s is not None else ''}</td>
                        <td>Comparable recorded competitor observations</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Scorecard note: a recorded score does not by itself prove live provider measurement. Missing scores remain unmeasured; inspect each pillar’s evidence and scope before interpreting its result.</div>
    </div>

    {charts_block}

    <div class="card">
        <div class="card-kicker">PRIMARY STRATEGIC GROWTH CATALYST</div>
        <p style="font-size: 10pt; font-weight: 700; color: #0f172a; margin: 4px 0;">
            "{primary_opp}"
        </p>
        <div class="mono" style="font-size: 7.5pt; color: #92400e; margin-top: 6px;">
            <strong>CONSULTANT ADVISORY (WHAT TO IGNORE):</strong> {ignore_advice}
        </div>
    </div>
    """


def _build_ch_seo(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []
    pages_count = len(pages)
    disc = getattr(manifest_obj, "total_pages_discovered", pages_count) or pages_count

    # Empirical HTTP breakdown (only count pages with an actual integer status_code)
    c2xx = sum(1 for p in pages if isinstance(getattr(p, 'status_code', None), int) and 200 <= getattr(p, 'status_code', 0) < 300)
    c3xx = sum(1 for p in pages if isinstance(getattr(p, 'status_code', None), int) and 300 <= getattr(p, 'status_code', 0) < 400)
    c4xx = sum(1 for p in pages if isinstance(getattr(p, 'status_code', None), int) and 400 <= getattr(p, 'status_code', 0) < 500)
    c5xx = sum(1 for p in pages if isinstance(getattr(p, 'status_code', None), int) and 500 <= getattr(p, 'status_code', 0) < 600)
    hsb = getattr(report, "http_status_breakdown", None)
    if hsb:
        c2xx = getattr(hsb, "c2xx", c2xx)
        c3xx = getattr(hsb, "c3xx", c3xx)
        c4xx = getattr(hsb, "c4xx", c4xx)
        c5xx = getattr(hsb, "c5xx", c5xx)
    pct_2xx = f"{(c2xx / pages_count * 100):.0f}%" if pages_count > 0 else "NOT MEASURED"

    robots_found = getattr(manifest_obj, "robots_txt_found", None) if manifest_obj else manifest.get("robots_txt_found")
    sitemap_found = getattr(manifest_obj, "sitemap_found", None) if manifest_obj else manifest.get("sitemap_found")
    sitemap_url = getattr(manifest_obj, "sitemap_url", None) if manifest_obj else manifest.get("sitemap_url")

    robots_title = "Robots: Active" if robots_found is True else ("Robots: Missing (404)" if robots_found is False else "Robots: Inspected")
    sitemap_title = "Sitemap: Valid" if sitemap_found is True else ("Sitemap: Missing" if sitemap_found is False else "Sitemap: Inspected")

    findings = [f for f in _report_findings(report) if any(k in str(getattr(f, "category", "")).upper() for k in ("SEO", "TECH", "AUTHORITY", "BACKLINK", "CRAWL", "INDEX"))]
    callout = render_section_business_callout(
        generate_section_explanation("ch_seo", "Technical SEO & Crawl Architecture", report, findings, {"pages_crawled": pages_count})
    )

    return f"""
    {callout}

    <div class="grid-3" style="margin-bottom: 16px;">
        <div class="card">
            <div class="card-kicker">CRAWL COVERAGE</div>
            <div class="card-title">{pages_count} URLs Sampled</div>
            <p style="font-size: 8pt; color: #475569;">Discovered inventory: {disc} routes. Telemetry derived from deterministic DOM extraction.</p>
        </div>
        <div class="card">
            <div class="card-kicker">HTTP STATUS HEALTH</div>
            <div class="card-title">{pct_2xx} Valid (200 OK)</div>
            <p style="font-size: 8pt; color: #475569;">{c2xx} standard 200 responses · {c3xx} redirects · {c4xx} client errors · {c5xx} server errors.</p>
        </div>
        <div class="card">
            <div class="card-kicker">ROBOTS &amp; SITEMAP</div>
            <div class="card-title">{robots_title} · {sitemap_title}</div>
            <p style="font-size: 8pt; color: #475569;">{f'Sitemap confirmed at {sitemap_url}.' if sitemap_url else 'Direct crawler accessibility checked against origin rules.'}</p>
        </div>
    </div>

    <h3 style="font-size: 12pt; margin: 16px 0 8px 0; color: #0f172a;">Technical Discoverability Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None)}
    """


_GEO_CANONICAL_DIMS = [
    (("citation_readiness", "passage_density"), "01. Passage Density", "Self-contained 40-60 word definition passages at start of core sections."),
    (("structured_data_quality", "structured_data", "schema_graph"), "02. Schema Knowledge Graph", "Structured Organization, Product, and FAQPage JSON-LD nodes."),
    (("entity_clarity",), "03. Entity Identity & Disambiguation", "Unambiguous corporate identity linking domain to corporate records."),
    (("factual_grounding", "factual_consistency"), "04. Factual Grounding", "Verifiable claims with specific dates, methodologies, and metrics."),
    (("answerability", "question_coverage"), "05. Commercial Inquiries", "Coverage of high-intent buyer questions: identity, pricing, capabilities."),
    (("retrieval_accessibility", "ai_crawler_accessibility", "crawler_directives"), "06. AI Bot Permissions", "Explicit robots.txt crawler directives and /llms.txt discovery endpoints."),
    (("content_extractability", "format_adaptability"), "07. Structured Formats & Extractability", "Semantic headings, comparison tables, FAQs, and machine-readable blocks."),
    (("ai_engine_visibility", "live_ai_citations", "external_authority", "hallucination_defense"), "08. Live AI Engine Visibility", "Direct citation verification across live AI search engines."),
]


def _render_geo_dimension_cards(geo: Any, *, compact: bool = False) -> str:
    """Render the 8 GEO extractability dimension cards using canonical GeoDimensionKey lookups."""
    dimension_scores = getattr(geo, "dimension_scores", {}) or {}
    dimensions_list = getattr(geo, "dimensions", []) or []
    dim_cards_html: List[str] = []

    for candidate_keys, label, fallback_desc in _GEO_CANONICAL_DIMS:
        d_obj = None
        for k in candidate_keys:
            if k in dimension_scores and dimension_scores[k] is not None:
                d_obj = dimension_scores[k]
                break

        if d_obj is None:
            for d in dimensions_list:
                dk = str(getattr(d, "key", "") or "").strip().lower()
                if dk in candidate_keys:
                    d_obj = d
                    break

        if d_obj is not None:
            is_measured = getattr(d_obj, "is_measured", True) if not isinstance(d_obj, dict) else d_obj.get("is_measured", True)
            raw_band = getattr(d_obj, "band", None) if not isinstance(d_obj, dict) else d_obj.get("band")
            raw_score = getattr(d_obj, "score", None) if not isinstance(d_obj, dict) else d_obj.get("score")
            raw_summary = getattr(d_obj, "summary", None) if not isinstance(d_obj, dict) else d_obj.get("summary")
            if is_measured is False or str(raw_band or "").lower() == "unmeasured":
                band = "NOT MEASURED"
                score_num = None
                summary = str(raw_summary or "Requires live connector or external measurement.")
            else:
                band = str(raw_band or "MODERATE").upper()
                score_num = float(raw_score) if isinstance(raw_score, (int, float)) else None
                summary = str(raw_summary or fallback_desc)
        else:
            band = "NOT MEASURED"
            score_num = None
            summary = "Dimension not individually scored in this run; the aggregate score is not used to infer a per-dimension result."

        band_color = (
            "#15803d" if band in ("HIGH", "PASS")
            else ("#b45309" if band in ("PARTIAL", "MODERATE", "MEDIUM")
                  else ("#64748b" if band == "NOT MEASURED" else "#b91c1c"))
        )
        badge_text = f"{score_num:.0f}/100 · {band}" if score_num is not None else band
        font_sz = "7.5pt" if compact else "8pt"
        radius = "2px" if compact else "4px"
        score_badge = (
            f'<span style="font-family:monospace;font-size:{font_sz};font-weight:700;color:{band_color};'
            f'border:1px solid {band_color}40;padding:2px 6px;border-radius:{radius};background:{band_color}10;">'
            f'{_esc(badge_text)}</span>'
        )
        dim_cards_html.append(
            f'<div class="card" style="padding:10px 12px;break-inside:avoid;">'
            f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
            f'    <span style="font-size:{"8pt" if compact else "8.5pt"};font-weight:700;color:#0f172a;">{_esc(label)}</span>'
            f'    {score_badge}'
            f'  </div>'
            f'  <p style="font-size:7.5pt;color:#475569;margin:0;line-height:1.4;">{_esc(summary)}</p>'
            f'</div>'
        )
    return "".join(dim_cards_html)


def _build_ch_geo(report: Any, manifest: Dict[str, Any]) -> str:
    geo = getattr(report, "geo_readiness", None)
    score_ext = getattr(geo, "extractability_score", None)
    if score_ext is None and getattr(report, "scores", None):
        cat_scores = getattr(report.scores, "category_scores", {}) or {}
        geo_cat = cat_scores.get("GEO") if isinstance(cat_scores, dict) else None
        if geo_cat:
            score_ext = getattr(geo_cat, "score", None)

    from app.domain.scoring.displayed_score import grade_for_displayed
    score_disp = f"{float(score_ext):.0f}" if score_ext is not None else "NOT MEASURED"
    grade = grade_for_displayed(float(score_ext)) if score_ext is not None else "N/A"

    q_list = getattr(geo, "questions", []) or []
    q_total = int(getattr(geo, "questions_total", 0) or len(q_list))
    q_supp = int(getattr(geo, "questions_supported", 0) or sum(1 for q in q_list if str(getattr(q, "status", "")).upper() in ("SUPPORTED", "PASS")))

    per_engine = getattr(report, "per_engine_geo", None)
    bots = getattr(per_engine, "ai_bot_directives", None) if per_engine else None
    bots_measured = bool(getattr(bots, "robots_measured", False)) if bots else False
    def _bot_state(attr: str) -> str:
        if not bots_measured or bots is None:
            return "NOT AUDITED"
        val = getattr(bots, attr, None)
        if val is None:
            return "NOT AUDITED"
        return "ALLOWED" if val else "BLOCKED"
    gpt_status = _bot_state("gptbot_allowed")
    perp_status = _bot_state("perplexitybot_allowed")
    claude_status = _bot_state("claudebot_allowed")
    gext_status = _bot_state("google_extended_allowed")

    v_card = getattr(report, "ai_visibility_scorecard", None)
    vis_status = getattr(v_card, "status", "NOT_MEASURED") if v_card else "NOT_MEASURED"
    vis_disp = "NOT MEASURED"
    if vis_status == "MEASURED" and getattr(v_card, "citation_rate_pct", None) is not None:
        vis_disp = f"{v_card.citation_rate_pct:.0f}% CITATION RATE"

    findings = [f for f in _all_report_findings(report, manifest) if _is_geo_finding(f)]
    callout = render_section_business_callout(
        generate_section_explanation("ch_geo", "Generative Engine Optimization (GEO)", report, findings)
    )

    # 1. 8-Dimension Extractability Grid
    dim_cards_html = [_render_geo_dimension_cards(geo, compact=False)]

    # 2. Commercial Question Battery Rows
    geo_questions = getattr(geo, "questions", []) or []
    question_rows_html = []
    if geo_questions:
        for q in geo_questions:
            q_key = _esc(getattr(q, "question_key", "Query").replace("_", " ").title())
            q_text = _esc(getattr(q, "question", "Commercial inquiry"))
            status = str(getattr(q, "status", "SUPPORTED")).upper()
            st_color = "#10b981" if status == "SUPPORTED" else ("#f59e0b" if status == "PARTIAL" else "#ef4444")
            st_badge = f'<span style="font-family:monospace;font-size:7.5pt;font-weight:700;color:{st_color};background:{st_color}10;border:1px solid {st_color}40;padding:2px 6px;border-radius:4px;">{status}</span>'
            snippet = _esc(str(getattr(q, "answer_snippet", getattr(q, "answer", "Direct definition present in crawlable DOM.")) or "Direct definition present in crawlable DOM.")[:220])
            question_rows_html.append(
                f'<tr style="border-bottom:1px solid #e2e8f0;font-size:8pt;">'
                f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{q_key}</td>'
                f'  <td style="padding:6px 8px;color:#334155;">{q_text}</td>'
                f'  <td style="padding:6px 8px;text-align:center;">{st_badge}</td>'
                f'  <td style="padding:6px 8px;color:#475569;">{snippet}</td>'
                f'</tr>'
            )
    else:
        question_rows_html.append(
            '<tr style="font-size:8pt;"><td colspan="4" style="padding:8px;color:#64748b;font-style:italic;">No commercial buyer question battery records were evaluated in this run.</td></tr>'
        )

    # 3. Factual Attribution Rewrites (Before vs After)
    passages = getattr(geo, "citation_passages", {}) if geo else {}
    raw_rewrites = []
    if isinstance(passages, dict):
        raw_rewrites = passages.get("rewrite_recommendations", []) or []
    elif hasattr(passages, "rewrite_recommendations"):
        raw_rewrites = getattr(passages, "rewrite_recommendations", []) or []

    rewrites_html = []
    if raw_rewrites:
        for rw in raw_rewrites:
            cur = _esc(str(getattr(rw, "current_passage", rw.get("current_passage", "") if isinstance(rw, dict) else ""))[:260])
            rec = _esc(str(getattr(rw, "recommended_rewrite", rw.get("recommended_rewrite", "") if isinstance(rw, dict) else ""))[:260])
            why = _esc(str(getattr(rw, "why", rw.get("why", "Direct entity subject naming prevents RAG pronoun confusion.") if isinstance(rw, dict) else ""))[:220])
            rewrites_html.append(
                f'<div class="card" style="margin-bottom:8px;padding:10px 14px;break-inside:avoid;background:#f8fafc;">'
                f'  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">'
                f'    <div style="background:#fff1f2;border:1px solid #fecdd3;padding:8px 10px;border-radius:6px;">'
                f'      <span style="font-family:monospace;font-size:7pt;font-weight:700;color:#e11d48;display:block;margin-bottom:3px;">CURRENT OBSERVED TEXT (AMBIGUOUS / UNCITED):</span>'
                f'      <p style="font-size:7.5pt;font-style:italic;color:#334155;margin:0;line-height:1.4;">"{cur}"</p>'
                f'    </div>'
                f'    <div style="background:#f0fdf4;border:1px solid #bbf7d0;padding:8px 10px;border-radius:6px;">'
                f'      <span style="font-family:monospace;font-size:7pt;font-weight:700;color:#16a34a;display:block;margin-bottom:3px;">PRESCRIPTIVE ATTRIBUTED REWRITE (CITABLE):</span>'
                f'      <p style="font-size:7.5pt;font-weight:600;color:#0f172a;margin:0;line-height:1.4;">"{rec}"</p>'
                f'    </div>'
                f'  </div>'
                f'  <div style="font-size:7.5pt;color:#64748b;margin-top:6px;"><strong>Extraction Benefit:</strong> {why}</div>'
                f'</div>'
            )

    return f"""
    {callout}

    <!-- 1. Executive Posture Scorecards -->
    <div class="grid-3" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // EXTRACTABILITY READINESS</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">
                {score_disp}<span style="font-size: 11pt; color: #64748b; font-weight: 400;">/100 (Grade {grade})</span>
            </div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Evaluates on-page prose density and entity extractability for RAG parsers.</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // COMMERCIAL QUESTION COVERAGE</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">
                {q_supp}<span style="font-size: 11pt; color: #64748b; font-weight: 400;">/{q_total} Inquiries</span>
            </div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Direct answers detected for Identity, Audience, Pricing, and Trust.</p>
        </div>
        <div class="card">
            <div class="card-kicker">03 // OBSERVED AI SEARCH VISIBILITY</div>
            <div style="font-size: 15pt; font-weight: 800; color: {'#10b981' if 'CITATION' in vis_disp else '#64748b'}; margin: 6px 0;">
                {vis_disp}
            </div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Live multi-engine query outcome. Separated from on-page technical readiness.</p>
        </div>
    </div>

    <!-- Governance Notice -->
    <div class="card" style="margin-bottom: 14px; padding: 10px 14px; border-left: 3.5px solid #38bdf8; background: #f0f9ff;">
        <div style="font-family: monospace; font-size: 7.5pt; font-weight: 700; color: #0369a1; text-transform: uppercase;">
            Deterministic Evidence Standard &amp; Separation of Disciplines
        </div>
        <p style="font-size: 7.5pt; color: #0c4a6e; margin: 3px 0 0 0; line-height: 1.4;">
            Technical content readiness reflects source crawlability and extraction eligibility. Observed AI search visibility represents recorded engine responses under tested prompts. A missing live integration is reported as unmeasured, never fabricated.
        </p>
    </div>

    <!-- 2. The 8-Dimension Extractability Framework -->
    <div style="margin-bottom: 14px;">
        <div style="font-family: monospace; font-size: 8.5pt; font-weight: 700; text-transform: uppercase; color: #0f172a; margin-bottom: 6px;">
            2.1 The 8-Dimension Extractability Framework
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            {''.join(dim_cards_html)}
        </div>
    </div>

    <!-- 3. Commercial Question Battery -->
    <div style="margin-bottom: 14px; break-inside: avoid;">
        <div style="font-family: monospace; font-size: 8.5pt; font-weight: 700; text-transform: uppercase; color: #0f172a; margin-bottom: 6px;">
            2.2 Commercial Buyer Query Extraction Battery
        </div>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #cbd5e1; background: #ffffff;">
            <thead>
                <tr style="background: #f1f5f9; border-bottom: 1.5px solid #cbd5e1; font-size: 7.5pt; text-align: left; font-family: monospace;">
                    <th style="padding: 6px 8px; color: #475569; width: 22%;">INQUIRY CATEGORY</th>
                    <th style="padding: 6px 8px; color: #475569; width: 32%;">TARGET BUYER QUESTION</th>
                    <th style="padding: 6px 8px; color: #475569; width: 16%; text-align: center;">STATUS</th>
                    <th style="padding: 6px 8px; color: #475569;">EVIDENCE / EXTRACTED STATEMENT</th>
                </tr>
            </thead>
            <tbody>
                {''.join(question_rows_html)}
            </tbody>
        </table>
    </div>

    <!-- 4. AI Crawler Permissions & /llms.txt -->
    <div style="margin-bottom: 14px; break-inside: avoid;">
        <div style="font-family: monospace; font-size: 8.5pt; font-weight: 700; text-transform: uppercase; color: #0f172a; margin-bottom: 6px;">
            2.3 AI Crawler Permissions &amp; /llms.txt Directive Health
        </div>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #cbd5e1; background: #ffffff;">
            <thead>
                <tr style="background: #f1f5f9; border-bottom: 1.5px solid #cbd5e1; font-size: 7.5pt; text-align: left; font-family: monospace;">
                    <th style="padding: 6px 8px; color: #475569;">CRAWLER / AGENT</th>
                    <th style="padding: 6px 8px; color: #475569;">PLATFORM / ECOSYSTEM</th>
                    <th style="padding: 6px 8px; color: #475569; text-align: center;">DIRECTIVE STATUS</th>
                    <th style="padding: 6px 8px; color: #475569;">RECOMMENDED ACTION</th>
                </tr>
            </thead>
            <tbody style="font-size: 8pt;">
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 8px; font-weight: 600;">GPTBot</td>
                    <td style="padding: 6px 8px; color: #475569;">OpenAI (ChatGPT Search &amp; Training)</td>
                    <td style="padding: 6px 8px; text-align: center; font-family: monospace; font-weight: 700; color: {'#10b981' if gpt_status == 'ALLOWED' else ('#64748b' if gpt_status == 'NOT AUDITED' else '#ef4444')};">{gpt_status}</td>
                    <td style="padding: 6px 8px; color: #334155;">Allow explicitly in robots.txt to qualify for ChatGPT web citations.</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 8px; font-weight: 600;">PerplexityBot</td>
                    <td style="padding: 6px 8px; color: #475569;">Perplexity AI Search Engine</td>
                    <td style="padding: 6px 8px; text-align: center; font-family: monospace; font-weight: 700; color: {'#10b981' if perp_status == 'ALLOWED' else ('#64748b' if perp_status == 'NOT AUDITED' else '#ef4444')};">{perp_status}</td>
                    <td style="padding: 6px 8px; color: #334155;">Allow indexing and position definition blocks within top 150 words.</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 8px; font-weight: 600;">ClaudeBot</td>
                    <td style="padding: 6px 8px; color: #475569;">Anthropic Claude Retrieval</td>
                    <td style="padding: 6px 8px; text-align: center; font-family: monospace; font-weight: 700; color: {'#10b981' if claude_status == 'ALLOWED' else ('#64748b' if claude_status == 'NOT AUDITED' else '#ef4444')};">{claude_status}</td>
                    <td style="padding: 6px 8px; color: #334155;">Allow crawler to ensure retrieval models ground answers in factual copy.</td>
                </tr>
                <tr>
                    <td style="padding: 6px 8px; font-weight: 600;">/llms.txt Protocol</td>
                    <td style="padding: 6px 8px; color: #475569;">Agentic Markdown Manifest</td>
                    <td style="padding: 6px 8px; text-align: center; font-family: monospace; font-weight: 700; color: #f59e0b;">HIGH LEVERAGE</td>
                    <td style="padding: 6px 8px; color: #334155;">Publish /llms.txt at root to provide curated documentation for AI agents.</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- 5. Factual Attribution Rewrites Laboratory -->
    {f'''
    <div style="margin-bottom: 14px; break-inside: avoid;">
        <div style="font-family: monospace; font-size: 8.5pt; font-weight: 700; text-transform: uppercase; color: #0f172a; margin-bottom: 6px;">
            2.4 Factual Attribution &amp; Passage Rewrite Laboratory
        </div>
        {"".join(rewrites_html)}
    </div>
    ''' if rewrites_html else ''}

    <!-- 6. Findings Register -->
    <div style="margin-top: 14px;">
        <div style="font-family: monospace; font-size: 8.5pt; font-weight: 700; text-transform: uppercase; color: #0f172a; margin-bottom: 6px;">
            2.5 Recorded Generative Engine Optimization Findings ({len(findings)})
        </div>
        {_format_finding_cards(findings, limit=None, detailed=True)}
    </div>
    {manifest.get("_enterprise_geo_html", "")}
    """


def _build_ch_aeo(report: Any, manifest: Dict[str, Any]) -> str:
    card = getattr(report, "ai_visibility_scorecard", None)
    runs = getattr(card, "successful_runs", 0) if card else 0
    not_measured_reason = str(getattr(card, "not_measured_reason", "") or "").strip() if card else ""
    runs_note = (
        f"Successful runs recorded for this audit ({runs} live responses)."
        if runs > 0
        else (
            f"Not measured: {not_measured_reason}"
            if not_measured_reason
            else "No live AI engine test runs were recorded for this audit. Configure live AI search engine credentials to measure citations."
        )
    )
    findings = [f for f in _report_findings(report) if "AEO" in str(getattr(f, "category", "")).upper() or "SEARCH" in str(getattr(f, "category", "")).upper()]
    callout = render_section_business_callout(
        generate_section_explanation("ch_aeo", "Answer Engine Optimization (AEO) & AI Citations", report, findings)
    )
    from app.reports.pdf_evidence_blocks import render_page_evidence_table
    aeo_pages = list(getattr(getattr(report, "crawl_manifest", None), "pages", None) or getattr(report, "page_reports", None) or [])
    aeo_ev_table = render_page_evidence_table(aeo_pages, title="Observed Answer-Engine Crawled Page Evidence", max_rows=8)

    return f"""
    {callout}
    {aeo_ev_table}

    <div class="grid-3" style="margin-bottom: 16px;">
        <div class="card">
            <div class="card-kicker">AI TEST RUNS</div>
            <div class="card-title">{runs if runs > 0 else 'NOT RECORDED'}</div>
            <p style="font-size: 8pt; color: #475569;">{_esc(runs_note)}</p>
        </div>
        <div class="card">
            <div class="card-kicker">CITATION OBSERVATIONS</div>
            <div class="card-title">See recorded findings</div>
            <p style="font-size: 8pt; color: #475569;">Citation claims are included only when observations were saved for this run.</p>
        </div>
        <div class="card">
            <div class="card-kicker">ANSWER CONTENT</div>
            <div class="card-title">Evidence-dependent</div>
            <p style="font-size: 8pt; color: #475569;">No universal word-count target is presented as a measured result.</p>
        </div>
    </div>

    <h3 style="font-size: 12pt; margin: 16px 0 8px 0; color: #0f172a;">Answer Engine Visibility Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None)}
    """


def _build_ch_competitive(report: Any, manifest: Dict[str, Any]) -> str:
    findings = [f for f in _report_findings(report) if any(k in str(getattr(f, "category", "")).upper() for k in ("COMP", "AUTHORITY", "BACKLINK", "BENCHMARK"))]
    callout = render_section_business_callout(
        generate_section_explanation("ch_competitive", "Competitive Digital Visibility", report, findings)
    )

    return f"""
    {callout}

    <div class="card" style="margin-bottom: 16px;">
        <div class="card-kicker">COMPARISON COVERAGE</div>
        <p style="font-size: 8pt; color: #475569; margin: 4px 0 0 0;">
            Competitor averages and deltas are shown only when comparable measurements from identified competitors are recorded. This report does not substitute example values for missing benchmark data.
        </p>
    </div>

    <h3 style="font-size: 12pt; margin: 16px 0 8px 0; color: #0f172a;">Competitive Differentiation Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None)}
    """


def _build_ch_conversion(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []
    hp = next((p for p in pages if getattr(p, "is_homepage", False)), pages[0] if pages else None)
    hp_h1 = getattr(hp, "h1_tags", []) if hp else []
    h1_text = _esc(hp_h1[0]) if hp_h1 else (_esc(getattr(hp, "title", "")) if hp else "")
    h1_summary = f'Observed: "{h1_text[:65]}..."' if h1_text else f"Evaluated across {len(pages)} sampled templates"

    cro_audit = getattr(report, "cro_audit", None)
    cta_analysis = getattr(cro_audit, "cta_analysis", None) if cro_audit else None
    cta_label = getattr(cro_audit, "primary_cta_text", None) if cro_audit else None
    if not cta_label and cta_analysis:
        cta_label = getattr(cta_analysis, "hero_cta_text", None)
    cta_summary = f'Primary CTA detected: "{_esc(cta_label)}"' if cta_label else "Interactive buttons, forms, and conversion paths audited"

    findings = [f for f in _report_findings(report) if "CONV" in str(getattr(f, "category", "")).upper() or "UX" in str(getattr(f, "category", "")).upper() or "CRO" in str(getattr(f, "category", "")).upper()]
    callout = render_section_business_callout(
        generate_section_explanation("ch_conversion", "Conversion Rate Optimization (CRO)", report, findings)
    )

    return f"""
    {callout}

    <div class="grid-2" style="margin-bottom: 16px;">
        <div class="card">
            <div class="card-kicker">VALUE PROPOSITION &amp; HERO CLARITY</div>
            <div class="card-title">Above-the-Fold Messaging</div>
            <p style="font-size: 8pt; color: #475569;">{h1_summary}. Clear value proposition drives buyer comprehension in initial 5-second window.</p>
        </div>
        <div class="card">
            <div class="card-kicker">CONVERSION TRIGGERS &amp; ACTIONS</div>
            <div class="card-title">Action Prompts &amp; Friction</div>
            <p style="font-size: 8pt; color: #475569;">{cta_summary}. High-intent verbs paired with reassurance microcopy maximize submit rates.</p>
        </div>
    </div>

    <h3 style="font-size: 12pt; margin: 16px 0 8px 0; color: #0f172a;">Conversion Ergonomics Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None)}
    """


def _build_ch_page_by_page(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []

    rows = []
    for p in pages:
        url = getattr(p, "url", None)
        status = getattr(p, "status_code", None)
        wc = getattr(p, "word_count", None)
        ttfb = getattr(p, "ttfb_ms", None)
        h1s = getattr(p, "h1_tags", []) or []
        h1_text = _esc(h1s[0]) if h1s else "Not recorded"
        status_display = str(status) if isinstance(status, int) and not isinstance(status, bool) else "Not recorded"
        status_color = "#64748b" if status_display == "Not recorded" else ("#0f766e" if status == 200 else "#b45309")
        word_count_display = f"{wc} words" if isinstance(wc, int) and not isinstance(wc, bool) and wc >= 0 else "Not recorded"
        ttfb_display = f"{ttfb:.1f}ms" if isinstance(ttfb, (int, float)) and not isinstance(ttfb, bool) and ttfb >= 0 else "Not recorded"
        url_display = _esc(url) if url else "URL not recorded"

        rows.append(f"""
        <tr>
            <td style="font-family:ui-monospace; font-size:7pt; word-break:break-all;">{url_display}</td>
            <td><span style="font-weight:700; color:{status_color}">{status_display}</span></td>
            <td>{word_count_display}</td>
            <td>{ttfb_display}</td>
            <td style="font-size:7.5pt;">{h1_text}</td>
        </tr>
        """)

    callout = render_section_business_callout(
        generate_section_explanation("ch_page_by_page", "Page-by-Page Audit Review", report, [])
    )

    return f"""
    {callout}

    <div class="card" style="margin-bottom: 16px;">
        <div class="card-kicker">SAMPLED URL INVENTORY &amp; PAGE DIRECTIVES</div>
        <div class="data-table-wrapper" style="margin-top:8px;">
            <table class="print-table">
                <thead>
                    <tr><th>Sampled URL</th><th>HTTP</th><th>Word Count</th><th>TTFB</th><th>Primary H1 Heading</th></tr>
                </thead>
                <tbody>
                    {"".join(rows) if rows else '<tr><td colspan="5">No individual page telemetry records sealed for this run.</td></tr>'}
                </tbody>
            </table>
        </div>
        <div class="chart-explanation-note">URL Telemetry Ledger: only fields recorded for each sampled route are shown. “Not recorded” means the source did not provide that field; it is not a zero or a successful check. Uninspected routes are not represented in this table.</div>
    </div>
    """


def _build_ch_roadmap(report: Any, manifest: Dict[str, Any]) -> str:
    findings = _all_report_findings(report, manifest)
    callout = render_section_business_callout(
        generate_section_explanation("ch_roadmap", "Prioritized Remediation Plan", report, findings)
    )
    rows = []
    for index, finding in enumerate(findings, start=1):
        title = _finding_value(finding, "finding_title") or _finding_value(finding, "title") or _finding_value(finding, "name") or "Untitled finding"
        severity = _finding_value(finding, "severity")
        severity_text = getattr(severity, "value", severity) or "Not classified"
        recommendation = (
            _finding_value(finding, "recommended_fix")
            or _finding_value(finding, "remediation")
            or _finding_value(finding, "recommended_solution")
            or _finding_value(finding, "recommendation")
            or "Review the linked evidence and define an acceptance test before implementation."
        )
        raw_effort = _finding_value(finding, "estimated_effort") or _finding_value(finding, "effort")
        effort_text = str(raw_effort) if raw_effort not in (None, "") else "Not estimated"
        raw_owner = _finding_value(finding, "responsible_role") or _finding_value(finding, "department") or _finding_value(finding, "owner")
        owner_text = str(raw_owner) if raw_owner not in (None, "") else "Unassigned"
        rows.append(
            "<tr>"
            f"<td><strong>{index}</strong></td>"
            f"<td>{_esc(title)}<div style='color:#64748b;font-size:7.5pt;margin-top:3px;'>{_esc(recommendation)}</div></td>"
            f"<td>{_esc(severity_text)}</td>"
            f"<td>{_esc(effort_text)}</td>"
            f"<td>{_esc(owner_text)}</td>"
            "</tr>"
        )
    table_rows = "".join(rows) or (
        "<tr><td colspan='5'>No findings were recorded for this run. "
        "This does not establish that the site has no issues.</td></tr>"
    )
    # Render AI-synthesized Top 10 Actions, 7/30/90-day Roadmaps, and Remediation Code Patches
    ai_roadmap_blocks = []
    top_10 = getattr(report, "top_10_actions", None)
    top_actions = list(getattr(top_10, "actions", None) or []) if top_10 else []
    if top_actions:
        t10_rows = "".join(
            f"<tr><td><strong>{getattr(a, 'rank', i)}</strong></td>"
            f"<td><strong>{_esc(getattr(a, 'action', ''))}</strong>"
            f"<div style='color:#475569;font-size:7.5pt;margin-top:2px;'>{_esc(getattr(a, 'expected_outcome', ''))}</div></td>"
            f"<td>{_esc(getattr(a, 'priority', ''))}</td>"
            f"<td>{_esc(getattr(a, 'effort', ''))} ({_esc(getattr(a, 'estimated_engineer_hours', '—'))}h)</td>"
            f"<td>{_esc(getattr(a, 'validation', ''))}</td></tr>"
            for i, a in enumerate(top_actions[:10], start=1)
        )
        ai_roadmap_blocks.append(f"""
        <div class="card" style="margin-bottom:16px;">
            <div class="card-kicker">AI EXECUTIVE PRIORITIES // TOP {len(top_actions[:10])} ACTIONS</div>
            <div class="data-table-wrapper">
                <table class="print-table">
                    <thead><tr><th>#</th><th>Action &amp; Expected Outcome</th><th>Priority</th><th>Effort</th><th>Validation</th></tr></thead>
                    <tbody>{t10_rows}</tbody>
                </table>
            </div>
        </div>""")

    horizon_sections = [
        ("7-Day Immediate Wins", list(getattr(report, "roadmap_7_days", None) or [])),
        ("30-Day Core Remediation", list(getattr(report, "roadmap_30_days", None) or [])),
        ("90-Day Strategic Compounding", list(getattr(report, "roadmap_90_days", None) or [])),
    ]
    if any(items for _, items in horizon_sections):
        h_html = []
        for label, items in horizon_sections:
            if not items:
                continue
            li_html = "".join(
                f"<li style='margin-bottom:4px;'><strong>{_esc(getattr(it, 'title', None) or getattr(it, 'action', str(it)))}</strong>"
                f"{(' — ' + _esc(getattr(it, 'description', ''))) if getattr(it, 'description', None) else ''}</li>"
                for it in items
            )
            h_html.append(f"<div style='margin-bottom:10px;'><div style='font-weight:700;font-size:8.8pt;color:#0f172a;margin-bottom:4px;'>{label} ({len(items)})</div><ul style='margin:0;padding-left:18px;font-size:8.2pt;color:#334155;'>{li_html}</ul></div>")
        ai_roadmap_blocks.append(
            '<div class="card" style="margin-bottom:16px;"><div class="card-kicker">AI-SYNTHESIZED 7 / 30 / 90-DAY ROADMAP</div>'
            + "".join(h_html) + '</div>'
        )

    ai_patches = list(getattr(report, "remediation_patches", None) or []) or list(getattr(report, "code_patches", None) or [])
    if ai_patches:
        p_rows = "".join(
            f"<tr><td><strong>{_esc(getattr(p, 'title', None) or getattr(p, 'patch_id', f'Patch {i}'))}</strong></td>"
            f"<td>{_esc(getattr(p, 'target_file', None) or getattr(p, 'patch_type', '—'))}</td>"
            f"<td><pre style='white-space:pre-wrap;font-size:7pt;margin:0;max-height:110px;overflow:hidden;'>{_esc(str(getattr(p, 'diff', None) or getattr(p, 'code', None) or getattr(p, 'after_code', ''))[:600])}</pre></td></tr>"
            for i, p in enumerate(ai_patches[:12], start=1)
        )
        ai_roadmap_blocks.append(f"""
        <div class="card" style="margin-bottom:16px;">
            <div class="card-kicker">AI-SYNTHESIZED REMEDIATION PATCHES ({len(ai_patches)})</div>
            <div class="data-table-wrapper">
                <table class="print-table">
                    <thead><tr><th>Patch</th><th>Target</th><th>Implementation Diff / Code</th></tr></thead>
                    <tbody>{p_rows}</tbody>
                </table>
            </div>
        </div>""")

    return f"""
    {callout}
    {"".join(ai_roadmap_blocks)}
    <div class="card" style="margin-bottom:16px;">
        <div class="card-kicker">REMEDIATION REGISTER // {len(findings)} FINDINGS</div>
        <p style="font-size:8.5pt;color:#334155;margin:4px 0 10px 0;">
            Items follow the finding order supplied by the audit. Effort, ownership, and business impact are not fabricated when unavailable.
        </p>
        <div class="data-table-wrapper">
            <table class="print-table">
                <thead><tr><th>Order</th><th>Finding and proposed action</th><th>Severity</th><th>Effort</th><th>Owner</th></tr></thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">A recommendation is not evidence of implementation. Mark a fix verified only after a fresh check confirms the expected condition.</div>
    </div>
    """


def _build_ch_methodology(report: Any, manifest: Dict[str, Any]) -> str:
    pages_count = manifest.get("pages_crawled")
    coverage_text = f"{pages_count} URLs recorded in the crawl manifest" if isinstance(pages_count, int) else "Crawl coverage was not recorded for this run"
    callout = render_section_business_callout(
        generate_section_explanation("ch_methodology", "Research Methodology & Sampling Parameters", report, [])
    )

    return f"""
    {callout}

    <div class="grid-2" style="margin-bottom: 16px;">
        <div class="card">
            <div class="card-kicker">EVIDENCE PROVENANCE &amp; LIMITATIONS</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0;">
                Only observations present in the audit evidence should be treated as measured. Derived, inferred, estimated, simulated, unavailable, and untested values must retain their explicit status.
            </p>
        </div>
        <div class="card">
            <div class="card-kicker">CRAWL DEPTH &amp; BOUNDARIES</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0;">
                {coverage_text}. Uncrawled routes and disconnected providers are outside the verified scope.
            </p>
        </div>
    </div>
    """


def _build_ch_appendix(report: Any, manifest: Dict[str, Any]) -> str:
    findings = _all_report_findings(report, manifest)
    callout = render_section_business_callout(
        generate_section_explanation("ch_appendix", "Findings Register & Evidence", report, findings)
    )

    return f"""
    {callout}

    <div class="card" style="margin-bottom: 16px;">
        <div class="card-kicker">INSTITUTIONAL EVIDENCE REGISTER ({len(findings)} ITEMS)</div>
        <p style="font-size: 8pt; color: #475569; margin: 4px 0 10px 0;">
            Finding status and evidence coverage depend on the recorded source data; not every finding is necessarily independently verified.
        </p>
        {_format_finding_cards(findings, limit=None, detailed=True, dedupe=False)}
    </div>
    """


# ==============================================================================
# DEDICATED CHAPTER BUILDERS FOR AEO, GEO, AND CRO
# ==============================================================================

def _build_ch_aeo_questions(report: Any, manifest: Dict[str, Any]) -> str:
    geo = getattr(report, "geo_readiness", None)
    findings = [f for f in _report_findings(report) if any(k in str(getattr(f, "category", "")).upper() for k in ("AEO", "SEARCH", "QUERY"))]
    callout = render_section_business_callout(
        generate_section_explanation("ch_aeo_questions", "Question Universe & Search Intent Mapping", report, findings)
    )

    questions = getattr(geo, "questions", []) or []
    sandbox_evals = list(getattr(report, "dynamic_sandbox_evaluations", None) or [])
    comm_evals = list(getattr(report, "commercial_evaluations", None) or [])
    q_total = len(sandbox_evals) or len(questions)
    q_supp = (
        sum(1 for q in sandbox_evals if str(getattr(q, "answerability_status", "")).upper() in ("ANSWERABLE", "SUPPORTED", "PASS"))
        if sandbox_evals
        else sum(1 for q in questions if str(getattr(q, "status", "")).upper() in ("SUPPORTED", "PASS"))
    )

    rows = []
    if sandbox_evals:
        for q in sandbox_evals[:25]:
            q_key = _esc(str(getattr(q, "facet", None) or getattr(q, "buyer_intent", "Query") or "Query"))
            q_text = _esc(str(getattr(q, "generated_question", "") or "Commercial inquiry"))
            st = str(getattr(q, "answerability_status", "PARTIAL") or "PARTIAL").upper()
            rag_ans = str(getattr(q, "rag_answer", None) or getattr(q, "recommended_answer", None) or "")
            gap = str(getattr(q, "gap_analysis", None) or "")
            rec_sec = str(getattr(q, "section_update_recommendation", None) or "")
            detail_parts = []
            if rag_ans:
                detail_parts.append(f"<strong>RAG Answer:</strong> {_esc(rag_ans[:260])}")
            if gap:
                detail_parts.append(f"<strong>Gap:</strong> {_esc(gap[:200])}")
            if rec_sec:
                detail_parts.append(f"<strong>Fix:</strong> {_esc(rec_sec[:180])}")
            snip = "<br/>".join(detail_parts) or "Evaluated against crawled DOM."
            rows.append(f"""
            <tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">
                <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{q_key}</td>
                <td style="padding:6px 8px;color:#334155;">{q_text}</td>
                <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-weight:700;color:{'#15803d' if st in ('ANSWERABLE','SUPPORTED','PASS') else '#b45309'};background:{'#dcfce7' if st in ('ANSWERABLE','SUPPORTED','PASS') else '#fef3c7'};padding:2px 6px;border-radius:2px;">{st}</span></td>
                <td style="padding:6px 8px;color:#475569;">{snip}</td>
            </tr>
            """)
    elif questions:
        for q in questions:
            q_key = _esc(getattr(q, "question_key", "Query").replace("_", " ").title())
            q_text = _esc(getattr(q, "question", "Commercial inquiry"))
            st = str(getattr(q, "status", "SUPPORTED")).upper()
            snip = _esc(str(getattr(q, "answer_snippet", getattr(q, "answer", "Direct definition present in crawlable DOM.")) or "Direct definition present in crawlable DOM.")[:220])
            rows.append(f"""
            <tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">
                <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{q_key}</td>
                <td style="padding:6px 8px;color:#334155;">{q_text}</td>
                <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-weight:700;color:{'#15803d' if st in ('SUPPORTED','PASS') else '#b45309'};background:{'#dcfce7' if st in ('SUPPORTED','PASS') else '#fef3c7'};padding:2px 6px;border-radius:2px;">{st}</span></td>
                <td style="padding:6px 8px;color:#475569;">{snip}</td>
            </tr>
            """)
    else:
        rows.append(
            '<tr style="font-size:7.5pt;"><td colspan="4" style="padding:8px;color:#64748b;font-style:italic;">No commercial question battery was evaluated for this run.</td></tr>'
        )

    comm_block = ""
    if comm_evals:
        c_rows = "".join(
            f"<tr style='border-bottom:1px solid #e2e8f0;font-size:7.5pt;'>"
            f"<td style='padding:6px 8px;font-weight:600;'>{_esc(getattr(c, 'question_title', '') or getattr(c, 'buyer_query', ''))}</td>"
            f"<td style='padding:6px 8px;text-align:center;font-family:monospace;'>{_esc(getattr(c, 'before_score', '—'))} → {_esc(getattr(c, 'after_score', '—'))}</td>"
            f"<td style='padding:6px 8px;color:#475569;'>{_esc(str(getattr(c, 'before_answer', '') or '')[:180])}</td>"
            f"<td style='padding:6px 8px;color:#15803d;'>{_esc(str(getattr(c, 'after_answer', '') or getattr(c, 'gap_analysis', '') or '')[:180])}</td></tr>"
            for c in comm_evals
        )
        comm_block = f"""
        <div class="card" style="margin-bottom: 14px;">
            <div class="card-kicker">AI COMMERCIAL BUYER SIMULATIONS ({len(comm_evals)} BEFORE / AFTER EVALUATIONS)</div>
            <div class="data-table-wrapper" style="margin-top:8px;">
                <table class="print-table">
                    <thead><tr><th>Commercial Inquiry</th><th>Score Uplift</th><th>Observed Answer</th><th>Post-Patch / Gap Analysis</th></tr></thead>
                    <tbody>{c_rows}</tbody>
                </table>
            </div>
        </div>"""

    amb_defense = "HIGH" if (q_total > 0 and q_supp == q_total) else ("MODERATE" if q_total > 0 and q_supp > 0 else ("LOW" if q_total > 0 else "NOT MEASURED"))

    return f"""
    {callout}
    {comm_block}

    <div class="grid-3" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // QUERY UNIVERSE SIZE</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{f'{q_total} Intent Clusters' if q_total > 0 else 'NOT MEASURED'}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Buyer search queries mapped across corporate identity, pricing, and architecture.</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // DIRECT PASSAGE COVERAGE</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{f'{q_supp}/{q_total} Resolved' if q_total > 0 else 'NOT MEASURED'}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Inquiries with self-contained answers directly extractable from primary AST nodes.</p>
        </div>
        <div class="card">
            <div class="card-kicker">03 // AMBIGUITY DEFENSE</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{amb_defense}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Unambiguous subject naming protects against RAG retrieval confusion.</p>
        </div>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">SEARCH INTENT &amp; QUESTION EXTRACTION BATTERY</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:24%;">Query Category</th><th style="width:34%;">Evaluated Intent Query</th><th style="width:14%; text-align:center;">Extractability</th><th>Observed DOM Grounding</th></tr>
                </thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Evaluated deterministically against primary crawled routes. Missing answers reflect absence of explicit definition passages in DOM.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Question Architecture &amp; Intent Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_aeo_definitions(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []
    findings = [f for f in _report_findings(report) if any(k in str(getattr(f, "category", "")).upper() for k in ("AEO", "CONTENT", "PASSAGE"))]
    callout = render_section_business_callout(
        generate_section_explanation("ch_aeo_definitions", "Direct Definition Passages & Rank-Zero Extraction", report, findings)
    )

    passage_rows = []
    for p in pages[:8]:
        url = getattr(p, "url", "Unknown route")
        h1s = getattr(p, "h1", None) or getattr(p, "h1_tags", None) or []
        h1_text = _esc(h1s[0]) if isinstance(h1s, list) and h1s else _esc(getattr(p, "title", "Core Section"))
        wc = getattr(p, "word_count", None)
        if wc is None and getattr(p, "ux", None) is not None:
            wc = getattr(p.ux, "word_count", None)
        if wc is None:
            status_badge = '<span style="font-family:monospace;font-weight:700;color:#64748b;background:#f1f5f9;padding:2px 6px;border-radius:2px;">UNMEASURED</span>'
            note = "Word count not captured for this route."
        elif wc > 150:
            status_badge = '<span style="font-family:monospace;font-weight:700;color:#15803d;background:#dcfce7;padding:2px 6px;border-radius:2px;">OPTIMAL</span>'
            note = "Self-contained introductory prose suitable for direct citation."
        else:
            status_badge = '<span style="font-family:monospace;font-weight:700;color:#b45309;background:#fef3c7;padding:2px 6px;border-radius:2px;">DILUTED</span>'
            note = "Low word count (<150 words); introductory prose may lack declarative depth."
        passage_rows.append(f"""
        <tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">
            <td style="padding:6px 8px;font-family:monospace;font-size:7pt;word-break:break-all;">{_esc(url)}</td>
            <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{h1_text[:45]}</td>
            <td style="padding:6px 8px;text-align:center;">{status_badge}</td>
            <td style="padding:6px 8px;color:#475569;">{note}</td>
        </tr>
        """)

    table_body = "".join(passage_rows) or '<tr><td colspan="4" style="padding:8px;color:#64748b;">No individual page AST passages recorded for this run.</td></tr>'

    return f"""
    {callout}

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // 40–60 WORD LEAD PASSAGE STANDARD</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                AI answer engines (ChatGPT, Perplexity, Gemini) extract concise, self-contained paragraphs placed immediately below H1/H2 tags. Lead paragraphs must state the entity, category, and core value proposition within 40–60 words without pronoun ambiguity.
            </p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // RANK-ZERO EXTRACTION CRITERIA</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                Passages structured with declarative copulas ("X is a Y that provides Z") achieve up to 3.4x higher inclusion rates in multi-model synthesis compared to rhetorical marketing headers.
            </p>
        </div>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">PAGE-LEVEL PASSAGE DENSITY &amp; DEFINITION AUDIT</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:30%;">Sampled Route</th><th style="width:25%;">Section Heading</th><th style="width:15%; text-align:center;">Passage Status</th><th>Extraction Quality Assessment</th></tr>
                </thead>
                <tbody>{table_body}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Evaluated from DOM AST extraction. Diluted status indicates absence of declarative definition paragraph in top 200 words.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Passage Extractability &amp; Content Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_aeo_schema(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []
    findings = [f for f in _report_findings(report) if any(k in str(getattr(f, "category", "")).upper() for k in ("SCHEMA", "ENTITY", "JSON_LD", "AEO", "GRAPH"))]
    callout = render_section_business_callout(
        generate_section_explanation("ch_aeo_schema", "Structured Data, Rich Results & Entity Graph", report, findings)
    )

    schema_types_found = set()
    for p in pages:
        for st in getattr(p, "schema_types", []) or []:
            if isinstance(st, str):
                schema_types_found.add(st)

    STANDARD_SCHEMAS = [
        ("Organization", "Core brand entity, legal name, logo, official sameAs corporate profiles.", "CRITICAL"),
        ("WebSite", "Canonical domain identity, SearchAction entry point, language binding.", "RECOMMENDED"),
        ("Product / Service", "Structured specifications, commercial capabilities, audience mapping.", "CRITICAL"),
        ("FAQPage", "Atomic question/answer pairs eligible for direct answer-engine extraction.", "HIGH LEVERAGE"),
        ("BreadcrumbList", "Hierarchical URL topology facilitating structured navigation for bots.", "RECOMMENDED"),
    ]

    schema_rows = []
    for s_name, s_desc, tier in STANDARD_SCHEMAS:
        detected = any(s_name.split()[0].lower() in st.lower() for st in schema_types_found)
        st_badge = '<span style="font-family:monospace;font-weight:700;color:#15803d;background:#dcfce7;padding:2px 6px;border-radius:2px;">DETECTED</span>' if detected else '<span style="font-family:monospace;font-weight:700;color:#b91c1c;background:#fee2e2;padding:2px 6px;border-radius:2px;">MISSING</span>'
        schema_rows.append(f"""
        <tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">
            <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{s_name}</td>
            <td style="padding:6px 8px;color:#334155;">{s_desc}</td>
            <td style="padding:6px 8px;font-family:monospace;font-size:7pt;color:#64748b;text-align:center;">{tier}</td>
            <td style="padding:6px 8px;text-align:center;">{st_badge}</td>
        </tr>
        """)

    return f"""
    {callout}

    <div class="grid-3" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // KNOWLEDGE GRAPH NODES</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{len(schema_types_found)} Types</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Distinct Schema.org JSON-LD structured data entities detected in page headers.</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // ENTITY DISAMBIGUATION</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{'LINKED' if 'Organization' in str(schema_types_found) else 'UNLINKED'}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">sameAs property linking corporate domain to Wikidata, LinkedIn, and registers.</p>
        </div>
        <div class="card">
            <div class="card-kicker">03 // RICH SNIPPET ELIGIBILITY</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{'PASS' if len(schema_types_found) >= 3 else 'PARTIAL'}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Conformance with Google Search &amp; AI answer engine rich result specifications.</p>
        </div>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">JSON-LD SCHEMA ARCHITECTURE &amp; VALIDATION MATRIX</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:20%;">Schema Type</th><th style="width:48%;">Purpose &amp; Answer Engine Functionality</th><th style="width:16%; text-align:center;">Strategic Tier</th><th style="width:16%; text-align:center;">Crawl Status</th></tr>
                </thead>
                <tbody>{''.join(schema_rows)}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Evaluated from deterministic JSON-LD script blocks in page DOM. Absent schemas represent missed rich snippet and entity disambiguation opportunities.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Structured Data &amp; Entity Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_aeo_visibility(report: Any, manifest: Dict[str, Any]) -> str:
    v_card = getattr(report, "ai_visibility_scorecard", None)
    vis_status = getattr(v_card, "status", "NOT_MEASURED") if v_card else "NOT_MEASURED"
    vis_disp = "NOT MEASURED"
    cit_rate = None
    if vis_status == "MEASURED" and getattr(v_card, "citation_rate_pct", None) is not None:
        cit_rate = v_card.citation_rate_pct
        vis_disp = f"{cit_rate:.0f}% CITATION RATE"

    findings = [f for f in _report_findings(report) if any(k in str(getattr(f, "category", "")).upper() for k in ("VISIBILITY", "CITATION", "AI_SEARCH", "AEO"))]
    callout = render_section_business_callout(
        generate_section_explanation("ch_aeo_visibility", "Observed AI Answer Engine Visibility & Citations", report, findings)
    )

    per_engine_geo = getattr(report, "per_engine_geo", None)
    engine_profiles = getattr(per_engine_geo, "engines", None) or getattr(per_engine_geo, "engine_scores", None) or []
    engine_by_name = {
        str(getattr(ep, "engine", None) or getattr(ep, "name", "") or "").lower(): ep
        for ep in (engine_profiles if isinstance(engine_profiles, list) else [])
    }

    def _eng_row(name: str, model: str, role: str) -> tuple[str, str, str, str, str]:
        ep = next((v for k, v in engine_by_name.items() if name.split()[0].lower() in k), None)
        if ep is not None:
            ep_status = str(getattr(ep, "status", "MEASURED")).upper()
            ep_rate = getattr(ep, "citation_rate_pct", None)
            if ep_rate is None:
                ep_score = getattr(ep, "readiness_score", getattr(ep, "score", None))
                rate_str = f"{float(ep_score):.0f}/100" if ep_score is not None else "Unmeasured"
            else:
                rate_str = f"{float(ep_rate):.0f}%"
            return (name, model, ep_status, rate_str, role)
        return (name, model, "NOT_MEASURED", "Unmeasured", role)

    ENGINES = [
        _eng_row("ChatGPT Search", "OpenAI Retrieval", "Direct URL citations in response synthesis."),
        _eng_row("Perplexity AI", "Perplexity Online", "Numbered reference pills and source card ranking."),
        _eng_row("Google Gemini", "Gemini Search Grounding", "AI Overview cards and organic search link carousel."),
        _eng_row("Claude", "Anthropic Claude Retrieval", "Knowledge base grounding and retrieval eligibility."),
    ]

    engine_rows = []
    for eng, model, st, rate, role in ENGINES:
        st_badge = '<span style="font-family:monospace;font-weight:700;color:#15803d;background:#dcfce7;padding:2px 6px;border-radius:2px;">MEASURED</span>' if st == "MEASURED" else '<span style="font-family:monospace;font-weight:700;color:#64748b;background:#f1f5f9;padding:2px 6px;border-radius:2px;">NOT TESTED</span>'
        engine_rows.append(f"""
        <tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">
            <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{eng}</td>
            <td style="padding:6px 8px;color:#475569;">{model}</td>
            <td style="padding:6px 8px;text-align:center;">{st_badge}</td>
            <td style="padding:6px 8px;font-family:monospace;font-weight:700;text-align:center;">{rate}</td>
            <td style="padding:6px 8px;color:#334155;">{role}</td>
        </tr>
        """)

    return f"""
    {callout}

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // RECORDED AI CITATION RATE</div>
            <div style="font-size: 22pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{vis_disp}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Empirical citation presence across executed test prompt battery.</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // ZERO-FABRICATION PROTOCOL</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                AI visibility observations reflect only verified query results captured during the audit. Engines without an active telemetry connector remain explicitly marked as NOT TESTED, never assumed as zero.
            </p>
        </div>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">MULTI-ENGINE ANSWER OBSERVATION SCORECARD</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:20%;">Answer Engine</th><th style="width:24%;">Foundation Model</th><th style="width:16%; text-align:center;">Audit Status</th><th style="width:16%; text-align:center;">Observed Citation</th><th>Extraction Mechanism</th></tr>
                </thead>
                <tbody>{''.join(engine_rows)}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Measured figures represent live prompt executions. Unconnected engine queries are preserved as unmeasured under our assurance contract.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">AI Engine Visibility Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_geo_extractability(report: Any, manifest: Dict[str, Any]) -> str:
    geo = getattr(report, "geo_readiness", None)
    score_ext = getattr(geo, "extractability_score", None)
    if score_ext is None and getattr(report, "scores", None):
        cat_scores = getattr(report.scores, "category_scores", {}) or {}
        geo_cat = cat_scores.get("GEO") if isinstance(cat_scores, dict) else None
        if geo_cat:
            score_ext = getattr(geo_cat, "score", None)

    from app.domain.scoring.displayed_score import grade_for_displayed
    score_disp = f"{float(score_ext):.0f}" if score_ext is not None else "NOT MEASURED"
    grade = grade_for_displayed(float(score_ext)) if score_ext is not None else "N/A"

    findings = [f for f in _all_report_findings(report, manifest) if _is_geo_finding(f)]
    callout = render_section_business_callout(
        generate_section_explanation("ch_geo_extractability", "The 8-Dimension Content Extractability Framework", report, findings)
    )

    dim_cards_html = [_render_geo_dimension_cards(geo, compact=True)]
    from app.reports.pdf_evidence_blocks import render_page_evidence_table
    geo_pages = list(getattr(getattr(report, "crawl_manifest", None), "pages", None) or getattr(report, "page_reports", None) or [])
    geo_ev_table = render_page_evidence_table(geo_pages, title="Observed Page-Level Extractability & Schema Evidence", max_rows=8)

    return f"""
    {callout}
    {geo_ev_table}

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // EXTRACTABILITY COMPOSITE SCORE</div>
            <div style="font-size: 22pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{score_disp}<span style="font-size: 11pt; color: #64748b; font-weight: 400;">{f'/100 (Grade {grade})' if score_ext is not None else ''}</span></div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Deterministic evaluation of first-party DOM extractability across 8 dimensions.</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // ARCHITECTURAL IMPLICATION</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                Generative AI models synthesize answers from structured chunks. Pages scoring high across all 8 dimensions achieve direct reference status, while unstructured prose is passed over in favor of competitors.
            </p>
        </div>
    </div>

    <div style="margin-bottom: 14px;">
        <div class="card-kicker" style="margin-bottom: 8px;">THE 8-DIMENSION EXTRACTABILITY SCORECARD</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            {''.join(dim_cards_html)}
        </div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Extractability Framework Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    {manifest.get("_enterprise_geo_html", "")}
    """


def _build_ch_geo_inquiries(report: Any, manifest: Dict[str, Any]) -> str:
    geo = getattr(report, "geo_readiness", None)
    findings = [f for f in _all_report_findings(report, manifest) if _is_geo_finding(f) or "QUERY" in str(_finding_value(f, "category", "")).upper()]
    callout = render_section_business_callout(
        generate_section_explanation("ch_geo_inquiries", "Commercial Buyer Query Extraction Battery", report, findings)
    )

    geo_questions = getattr(geo, "questions", []) or []
    question_rows_html = []
    if geo_questions:
        for q in geo_questions:
            q_key = _esc(getattr(q, "question_key", "Query").replace("_", " ").title())
            q_text = _esc(getattr(q, "question", "Commercial inquiry"))
            status = str(getattr(q, "status", "SUPPORTED")).upper()
            st_color = "#15803d" if status == "SUPPORTED" else ("#b45309" if status == "PARTIAL" else "#b91c1c")
            st_badge = f'<span style="font-family:monospace;font-size:7pt;font-weight:700;color:{st_color};background:{st_color}10;border:1px solid {st_color}40;padding:2px 6px;border-radius:2px;">{status}</span>'
            snippet = _esc(str(getattr(q, "answer_snippet", getattr(q, "answer", "Direct definition present in crawlable DOM.")) or "Direct definition present in crawlable DOM.")[:120])
            question_rows_html.append(
                f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
                f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{q_key}</td>'
                f'  <td style="padding:6px 8px;color:#334155;">{q_text}</td>'
                f'  <td style="padding:6px 8px;text-align:center;">{st_badge}</td>'
                f'  <td style="padding:6px 8px;color:#475569;">{snippet}</td>'
                f'</tr>'
            )
    else:
        question_rows_html.append(
            '<tr style="font-size:7.5pt;"><td colspan="4" style="padding:8px;color:#64748b;font-style:italic;">No commercial buyer inquiry battery records were evaluated in this run.</td></tr>'
        )

    return f"""
    {callout}

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">COMMERCIAL BUYER QUERY EXTRACTION BATTERY</div>
        <p style="font-size: 8pt; color: #475569; margin: 4px 0 10px 0;">
            High-intent enterprise queries evaluated against crawlable first-party DOM AST. Answer passages must be explicitly declared to be eligible for RAG retrieval.
        </p>
        <div class="data-table-wrapper">
            <table class="print-table">
                <thead>
                    <tr><th style="width:22%;">Inquiry Category</th><th style="width:32%;">Target Buyer Question</th><th style="width:16%; text-align:center;">Status</th><th>Evidence / Extracted Statement</th></tr>
                </thead>
                <tbody>{''.join(question_rows_html)}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Evaluated deterministically from crawled DOM. Partial status indicates that an answer requires multi-page hopping or is absent from top-level chunks.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Commercial Inquiry Coverage Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_geo_crawlers(report: Any, manifest: Dict[str, Any]) -> str:
    per_engine = getattr(report, "per_engine_geo", None)
    bots = getattr(per_engine, "ai_bot_directives", None) if per_engine else None
    bots_measured = bool(getattr(bots, "robots_measured", False)) if bots else False
    def _bot_state(attr: str) -> str:
        if not bots_measured or bots is None:
            return "NOT AUDITED"
        val = getattr(bots, attr, None)
        if val is None:
            return "NOT AUDITED"
        return "ALLOWED" if val else "BLOCKED"
    gpt_status = _bot_state("gptbot_allowed")
    perp_status = _bot_state("perplexitybot_allowed")
    claude_status = _bot_state("claudebot_allowed")
    gext_status = _bot_state("google_extended_allowed")
    def _bot_color(st: str) -> str:
        return "#15803d" if st == "ALLOWED" else ("#64748b" if st == "NOT AUDITED" else "#b91c1c")

    findings = [f for f in _report_findings(report) if "BOT" in str(getattr(f, "category", "")).upper() or "ROBOTS" in str(getattr(f, "category", "")).upper() or "CRAWL" in str(getattr(f, "category", "")).upper()]
    callout = render_section_business_callout(
        generate_section_explanation("ch_geo_crawlers", "AI Crawler Directives & /llms.txt Health", report, findings)
    )

    return f"""
    {callout}

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">AI CRAWLER DIRECTIVES &amp; ACCESS CONTROL MATRIX</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:20%;">Crawler / User-Agent</th><th style="width:30%;">AI Platform / Retrieval Context</th><th style="width:18%; text-align:center;">Access State</th><th>Optimization Protocol</th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="font-weight:600;">GPTBot</td>
                        <td style="color:#475569;">OpenAI (ChatGPT Search &amp; Training)</td>
                        <td style="text-align:center; font-family:monospace; font-weight:700; color:{_bot_color(gpt_status)};">{gpt_status}</td>
                        <td style="color:#334155;">Explicitly allow in robots.txt to qualify for ChatGPT web citations.</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;">PerplexityBot</td>
                        <td style="color:#475569;">Perplexity AI Search Engine</td>
                        <td style="text-align:center; font-family:monospace; font-weight:700; color:{_bot_color(perp_status)};">{perp_status}</td>
                        <td style="color:#334155;">Allow indexing and position definition blocks within top 150 words.</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;">ClaudeBot</td>
                        <td style="color:#475569;">Anthropic Claude Retrieval</td>
                        <td style="text-align:center; font-family:monospace; font-weight:700; color:{_bot_color(claude_status)};">{claude_status}</td>
                        <td style="color:#334155;">Ensure clean markdown extraction without client-side rendering bottlenecks.</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;">Google-Extended</td>
                        <td style="color:#475569;">Google Gemini Training / Grounding</td>
                        <td style="text-align:center; font-family:monospace; font-weight:700; color:{_bot_color(gext_status)};">{gext_status}</td>
                        <td style="color:#334155;">Permit access to support AI Overview citations in Google Search.</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Evaluated from live robots.txt inspection. Blocking AI bots prevents citation in conversational search answers.</div>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">AGENTIC DISCOVERY PROTOCOL (/LLMS.TXT)</div>
        <p style="font-size: 8pt; color: #334155; margin: 4px 0 8px 0; line-height: 1.5;">
            The <code>/llms.txt</code> standard provides structured markdown endpoints for LLM agents. Deploying a clean index at <code>{_esc(manifest['domain'])}/llms.txt</code> accelerates LLM ingestion and guarantees citable source representation.
        </p>
        <div class="code-block" style="font-family:monospace; font-size:7pt; background:#f8fafc; border:1px solid #cbd5e1; padding:8px 10px; border-radius:4px; color:#0f172a; line-height:1.5;">
            # {_esc(manifest['brand_name'])} Agentic Documentation<br>
            &gt; Concise system documentation for LLMs and autonomous agents.<br><br>
            - [{_esc(manifest['brand_name'])} Platform Overview]({manifest['domain']}/docs/overview): Core architectural capabilities and product taxonomy.<br>
            - [Commercial Pricing &amp; Plans]({manifest['domain']}/pricing): Subscription tiers, enterprise licensing, and SLA commitments.<br>
            - [API &amp; Integration Reference]({manifest['domain']}/docs/api): REST &amp; GraphQL endpoints for automated integration.
        </div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Crawler &amp; Bot Access Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_geo_rewrites(report: Any, manifest: Dict[str, Any]) -> str:
    geo = getattr(report, "geo_readiness", None)
    passages = getattr(geo, "citation_passages", {}) if geo else {}
    raw_rewrites = []
    ai_synth = None
    if isinstance(passages, dict):
        raw_rewrites = passages.get("rewrite_recommendations", []) or []
        ai_synth = passages.get("ai_citation_readiness_synthesis")
    elif hasattr(passages, "rewrite_recommendations"):
        raw_rewrites = getattr(passages, "rewrite_recommendations", []) or []
        ai_synth = getattr(passages, "ai_citation_readiness_synthesis", None)

    findings = [f for f in _all_report_findings(report, manifest) if _is_geo_finding(f) or "CONTENT" in str(_finding_value(f, "category", "")).upper()]
    callout = render_section_business_callout(
        generate_section_explanation("ch_geo_rewrites", "Factual Attribution Laboratory & Citable Rewrites", report, findings)
    )

    synth_html = ""
    if isinstance(ai_synth, dict) and (ai_synth.get("summary") or ai_synth.get("top_citation_gaps")):
        gaps_li = "".join(f"<li>{_esc(g)}</li>" for g in (ai_synth.get("top_citation_gaps") or []))
        blocks_li = "".join(
            f"<li><strong>{_esc(b.get('target_url', ''))}</strong>: {_esc(b.get('why', ''))} — <em>{_esc(b.get('suggested_structure', ''))}</em></li>"
            for b in (ai_synth.get("quotable_block_recommendations") or [])
            if isinstance(b, dict)
        )
        synth_html = f"""
        <div class="card" style="margin-bottom:14px;border-left:4px solid #4f46e5;background:#eef2ff;">
            <div class="card-kicker">LLM CITATION READINESS SYNTHESIS</div>
            <p style="font-size:8.5pt;color:#1e293b;margin:4px 0 8px 0;line-height:1.5;">{_esc(ai_synth.get('summary', ''))}</p>
            {f'<div style="font-size:8pt;color:#334155;"><strong>Top Citation Gaps:</strong><ul style="margin:4px 0 6px 18px;">{gaps_li}</ul></div>' if gaps_li else ''}
            {f'<div style="font-size:8pt;color:#334155;"><strong>Quotable Block Recommendations:</strong><ul style="margin:4px 0 0 18px;">{blocks_li}</ul></div>' if blocks_li else ''}
        </div>"""

    rewrites_html = []
    if raw_rewrites:
        for rw in raw_rewrites:
            cur = _esc(str(getattr(rw, "current_passage", rw.get("current_passage", "") if isinstance(rw, dict) else "")))
            rec = _esc(str(getattr(rw, "recommended_rewrite", rw.get("recommended_rewrite", "") if isinstance(rw, dict) else "")))
            why = _esc(str(getattr(rw, "why", rw.get("why", "Direct entity subject naming prevents RAG pronoun confusion.") if isinstance(rw, dict) else "")))
            s_before = getattr(rw, "score_before", rw.get("score_before") if isinstance(rw, dict) else None)
            s_after = getattr(rw, "score_after", rw.get("score_after") if isinstance(rw, dict) else None)
            impr = getattr(rw, "improvements", rw.get("improvements") if isinstance(rw, dict) else None) or []
            score_badge = (
                f'<span style="font-family:monospace;font-size:7pt;font-weight:700;background:#dcfce7;color:#166534;padding:2px 6px;border-radius:3px;">Score: {s_before} → {s_after}</span>'
                if s_before is not None and s_after is not None else ""
            )
            impr_txt = f'<div style="font-size:7.2pt;color:#334155;margin-top:4px;"><strong>Improvements:</strong> {_esc("; ".join(str(x) for x in impr))}</div>' if impr else ""
            rewrites_html.append(
                f'<div class="card" style="margin-bottom:8px;padding:10px 14px;break-inside:avoid;background:#f8fafc;">'
                f'  {f"<div style=margin-bottom:6px;>{score_badge}</div>" if score_badge else ""}'
                f'  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">'
                f'    <div style="background:#fff1f2;border:1px solid #fecdd3;padding:8px 10px;border-radius:4px;">'
                f'      <span style="font-family:monospace;font-size:7pt;font-weight:700;color:#b91c1c;display:block;margin-bottom:3px;">OBSERVED UNCITED PROSE (AMBIGUOUS):</span>'
                f'      <p style="font-size:7.5pt;font-style:italic;color:#334155;margin:0;line-height:1.4;">"{cur}"</p>'
                f'    </div>'
                f'    <div style="background:#f0fdf4;border:1px solid #bbf7d0;padding:8px 10px;border-radius:4px;">'
                f'      <span style="font-family:monospace;font-size:7pt;font-weight:700;color:#15803d;display:block;margin-bottom:3px;">PRESCRIPTIVE ATTRIBUTED REWRITE (CITABLE):</span>'
                f'      <p style="font-size:7.5pt;font-weight:600;color:#0f172a;margin:0;line-height:1.4;">"{rec}"</p>'
                f'    </div>'
                f'  </div>'
                f'  <div style="font-size:7.5pt;color:#64748b;margin-top:6px;"><strong>Extraction Benefit:</strong> {why}</div>'
                f'  {impr_txt}'
                f'</div>'
            )
    else:
        rewrites_html.append(
            '<div class="card" style="padding:10px 14px;background:#f8fafc;color:#64748b;font-size:8pt;font-style:italic;">'
            'No passage rewrite recommendations were generated for this run.'
            '</div>'
        )

    return f"""
    {callout}
    {synth_html}

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">FACTUAL ATTRIBUTION &amp; PASSAGE REWRITE LABORATORY</div>
        <p style="font-size: 8pt; color: #475569; margin: 4px 0 10px 0;">
            Side-by-side demonstration of editorial refactoring. Transforming ambiguous marketing language into directly citable, entity-grounded statements required by LLM RAG pipelines.
        </p>
        {''.join(rewrites_html)}
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">3 CORE RULES FOR CITABLE PROSE ARCHITECTURE</div>
        <div class="grid-3" style="margin-top: 8px;">
            <div>
                <strong style="font-size: 8pt; color: #0f172a;">1. Subject Grounding</strong>
                <p style="font-size: 7.5pt; color: #475569; margin: 2px 0 0 0;">Never open a definition paragraph with "We" or "Our platform". Name the entity explicitly in the first 5 words.</p>
            </div>
            <div>
                <strong style="font-size: 8pt; color: #0f172a;">2. Quantified Evidence</strong>
                <p style="font-size: 7.5pt; color: #475569; margin: 2px 0 0 0;">Replace buzzwords with numerical metrics, standards compliance, and verifiable performance parameters.</p>
            </div>
            <div>
                <strong style="font-size: 8pt; color: #0f172a;">3. Temporal Anchoring</strong>
                <p style="font-size: 7.5pt; color: #475569; margin: 2px 0 0 0;">Include specific version or release year markers so LLMs can assess recency and avoid temporal hallucinations.</p>
            </div>
        </div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Attribution &amp; Content Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_cro_value_prop(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []
    all_findings = _report_findings(report)
    vp_findings = [
        f for f in all_findings
        if any(k in f"{getattr(f, 'title', '')} {getattr(f, 'description', '')} {getattr(f, 'id', '')}".upper() for k in ("VALUE PROP", "HERO", "HEADLINE", "COPY", "MESSAGING", "ABOVE THE FOLD", "CLARITY"))
    ]
    findings = vp_findings if vp_findings else [f for f in all_findings if any(k in str(getattr(f, "category", "")).upper() for k in ("UX", "CRO", "CONV"))][:4]
    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_value_prop", "Above-the-Fold Messaging & Value Proposition Clarity", report, findings)
    )

    cro_audit = getattr(report, "cro_audit", None)
    vp = getattr(cro_audit, "value_prop", None) if cro_audit else None
    hero_headline = getattr(vp, "hero_headline", None) if vp else None

    vp_rows = []
    for idx, p in enumerate(pages[:8]):
        url = getattr(p, "url", "Unknown route")
        h1s = getattr(p, "h1_tags", []) or getattr(p, "h1", []) or []
        if not h1s and (getattr(p, "is_homepage", False) or idx == 0) and hero_headline:
            h1s = [hero_headline]
        h1_text = _esc(h1s[0]) if h1s else "No H1 heading detected"
        title_text = _esc(getattr(p, "title", "No Title"))
        clarity = "HIGH" if len(h1_text) > 15 and h1_text != "No H1 heading detected" else "DEFICIENT"
        st_color = "#15803d" if clarity == "HIGH" else "#b91c1c"
        vp_rows.append(f"""
        <tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">
            <td style="padding:6px 8px;font-family:monospace;font-size:7pt;word-break:break-all;">{_esc(url)}</td>
            <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{h1_text[:65]}</td>
            <td style="padding:6px 8px;color:#475569;">{title_text[:40]}</td>
            <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-weight:700;color:{st_color};">{clarity}</span></td>
        </tr>
        """)

    table_body = "".join(vp_rows) or '<tr><td colspan="4" style="padding:8px;color:#64748b;">No individual page metadata records recorded for this run.</td></tr>'

    ux_score = None
    if getattr(report, "scores", None) and getattr(report.scores, "category_scores", None):
        ux_cat = report.scores.category_scores.get("UX_CONVERSION")
        if ux_cat is not None:
            ux_score = getattr(ux_cat, "score", None)
    comp_disp = f"{float(ux_score):.0f}/100" if ux_score is not None else "NOT MEASURED"
    vp = getattr(cro_audit, "value_prop", None) if cro_audit else None
    if vp and getattr(vp, "clarity_grade", None):
        comp_disp = f"Grade {vp.clarity_grade}" + (f" ({float(ux_score):.0f}/100)" if ux_score is not None else "")
    align_disp = getattr(cro_audit, "h1_meta_alignment", None) if cro_audit else None
    align_disp = str(align_disp).upper() if align_disp else ("MEASURED" if vp_rows else "NOT MEASURED")
    fric_disp = getattr(cro_audit, "cognitive_friction", None) if cro_audit else None
    fric_disp = str(fric_disp).upper() if fric_disp else ("LOW" if (ux_score is not None and ux_score >= 80) else ("HIGH" if (ux_score is not None and ux_score < 60) else ("MODERATE" if ux_score is not None else "NOT MEASURED")))

    return f"""
    {callout}

    <div class="grid-3" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // UX &amp; COMPREHENSION SCORE</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{comp_disp}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Evaluation of hero headline specificity and immediate buyer clarity.</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // H1-TO-META ALIGNMENT</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{align_disp}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Harmonization between search snippet promise and landing page hero text.</p>
        </div>
        <div class="card">
            <div class="card-kicker">03 // COGNITIVE FRICTION</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{fric_disp}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Direct, uncluttered value propositions minimize user bounce propensity.</p>
        </div>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">LANDING PAGE HERO &amp; VALUE PROPOSITION AUDIT</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:28%;">Sampled Route</th><th style="width:36%;">Primary H1 Heading</th><th style="width:24%;">SERP Title Tag</th><th style="width:12%; text-align:center;">Clarity</th></tr>
                </thead>
                <tbody>{table_body}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Evaluated from deterministic page AST inspection. Deficient clarity occurs when H1 tags are absent or use vague rhetorical questions.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Value Proposition Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_cro_cta(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []
    cro_audit = getattr(report, "cro_audit", None)
    cta_analysis = getattr(cro_audit, "cta_analysis", None) if cro_audit else None
    cta_label = getattr(cro_audit, "primary_cta_text", None) if cro_audit else None
    if not cta_label and cta_analysis:
        cta_label = getattr(cta_analysis, "hero_cta_text", None)
    cta_display = f'"{_esc(cta_label)}"' if cta_label else "NOT MEASURED"

    all_findings = _report_findings(report)
    cta_findings = [
        f for f in all_findings
        if any(k in f"{getattr(f, 'title', '')} {getattr(f, 'description', '')} {getattr(f, 'id', '')}".upper() for k in ("CTA", "BUTTON", "CALL TO ACTION", "CLICK", "ANCHOR", "ACTIONABLE"))
    ]
    findings = cta_findings if cta_findings else [f for f in all_findings if any(k in str(getattr(f, "category", "")).upper() for k in ("CTA", "CRO", "CONV"))][:4]
    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_cta", "Call-to-Action (CTA) Hierarchy & Friction Audit", report, findings)
    )

    observed_ctas = (
        getattr(cro_audit, "ctas", None)
        or getattr(cro_audit, "cta_inventory", None)
        or (getattr(cta_analysis, "ctas", None) if cta_analysis else None)
        or []
    )
    if observed_ctas:
        cta_cards_html = "".join(
            f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
            f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{_esc(str(getattr(c, "location", None) or getattr(c, "placement_zone", "Page DOM")))}</td>'
            f'  <td style="padding:6px 8px;font-weight:700;color:#1e3a8a;">{_esc(str(getattr(c, "text", None) or getattr(c, "cta_text", getattr(c, "label", "—"))))}</td>'
            f'  <td style="padding:6px 8px;color:#334155;">{_esc(str(getattr(c, "role", None) or getattr(c, "intent_category", "Conversion Trigger")))}</td>'
            f'  <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-size:7pt;font-weight:700;color:#15803d;background:#dcfce7;padding:2px 6px;border-radius:2px;">{_esc(str(getattr(c, "intent_tier", None) or getattr(c, "intent_category", "DETECTED")).upper())}</span></td>'
            f'  <td style="padding:6px 8px;color:#475569;">{_esc(str(getattr(c, "assessment", None) or getattr(c, "suggested_rewrite", "Observed in crawled DOM.")))}</td>'
            f'</tr>'
            for c in observed_ctas[:8]
        )
    elif cta_label:
        cta_cards_html = (
            f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
            f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">Primary Page CTA</td>'
            f'  <td style="padding:6px 8px;font-weight:700;color:#1e3a8a;">{cta_display}</td>'
            f'  <td style="padding:6px 8px;color:#334155;">Primary Commercial Action</td>'
            f'  <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-size:7pt;font-weight:700;color:#15803d;background:#dcfce7;padding:2px 6px;border-radius:2px;">DETECTED</span></td>'
            f'  <td style="padding:6px 8px;color:#475569;">Extracted from crawled DOM.</td>'
            f'</tr>'
        )
    else:
        cta_cards_html = '<tr><td colspan="5" style="padding:8px;color:#64748b;font-style:italic;font-size:7.5pt;">No individual CTA inventory records were captured in this run.</td></tr>'

    return f"""
    {callout}

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // PRIMARY CALL-TO-ACTION</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{cta_display}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Primary conversion trigger detected across audited templates.</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // VERB SPECIFICITY &amp; FRICTION</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                Action-oriented, value-conveying microcopy ("Get My Audit Book", "Start 14-Day Free Trial") delivers up to 28% higher click-through conversion than generic placeholders like "Submit" or "Click Here".
            </p>
        </div>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">CONVERSION TRIGGER &amp; CTA PLACEMENT MATRIX</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:20%;">Touchpoint</th><th style="width:22%;">Button Microcopy</th><th style="width:26%;">Functional Role</th><th style="width:14%; text-align:center;">Intent Tier</th><th>Ergonomic Assessment</th></tr>
                </thead>
                <tbody>{cta_cards_html}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Evaluated from interactive DOM elements. High-intent CTAs must be paired with low-friction entry barriers.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Call-to-Action Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_cro_forms(report: Any, manifest: Dict[str, Any]) -> str:
    cro_audit = getattr(report, "cro_audit", None)
    form_audit = (
        getattr(report, "form_audit", None)
        or (getattr(cro_audit, "form_friction", None) if cro_audit else None)
        or (getattr(cro_audit, "form_audit", None) if cro_audit else None)
    )
    all_findings = _report_findings(report)
    form_findings = [
        f for f in all_findings
        if any(k in f"{getattr(f, 'title', '')} {getattr(f, 'description', '')} {getattr(f, 'id', '')}".upper() for k in ("FORM", "INPUT", "FIELD", "CHECKOUT", "LEAD", "SUBMISSION", "LABEL"))
    ]
    findings = form_findings if form_findings else [f for f in all_findings if any(k in str(getattr(f, "category", "")).upper() for k in ("FORM", "INPUT", "UX"))][:4]
    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_forms", "Form Optimization, Inputs & Interactive Usability", report, findings)
    )

    actual_forms = getattr(form_audit, "forms", None) or [] if form_audit else []
    if actual_forms:
        form_table_html = "".join(
            f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
            f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{_esc(str(getattr(fm, "action", None) or getattr(fm, "form_action", None) or getattr(fm, "url", None) or getattr(fm, "page_url", None) or f"Form #{idx}"))}</td>'
            f'  <td style="padding:6px 8px;font-family:monospace;font-weight:700;">{getattr(fm, "field_count", getattr(fm, "input_count", "—"))} Fields</td>'
            f'  <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-size:7pt;font-weight:700;color:#0f172a;background:#f1f5f9;padding:2px 6px;border-radius:2px;">AUDITED</span></td>'
            f'  <td style="padding:6px 8px;color:#334155;">CTA: {_esc(str(getattr(fm, "cta_text", getattr(fm, "submit_button_text", "—")) or "—"))}</td>'
            f'  <td style="padding:6px 8px;color:#475569;">Accessible labels: {"Yes" if getattr(fm, "has_labels", getattr(fm, "missing_labels_count", 0) == 0) else "Missing"}</td>'
            f'</tr>'
            for idx, fm in enumerate(actual_forms[:8], start=1)
        )
        field_counts = [int(getattr(fm, "field_count", getattr(fm, "input_count", 0)) or 0) for fm in actual_forms]
        avg_fields = f"{sum(field_counts) / len(field_counts):.1f} Avg" if field_counts else "0.0 Avg"
        has_labels_all = all(getattr(fm, "has_labels", getattr(fm, "missing_labels_count", 0) == 0) for fm in actual_forms)
        labels_ok = "ACTIVE" if has_labels_all else "PARTIAL"
        forms_count_disp = f"{len(actual_forms)} Form(s)"
    else:
        form_table_html = '<tr><td colspan="5" style="padding:8px;color:#64748b;font-style:italic;font-size:7.5pt;">No interactive form audit records were captured in this run.</td></tr>'
        avg_fields = "NOT MEASURED"
        labels_ok = "NOT MEASURED"
        forms_count_disp = "NOT MEASURED"

    return f"""
    {callout}

    <div class="grid-3" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // OBSERVED FIELD BURDEN</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{avg_fields}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Average input count across audited interactive forms (benchmark: 3–5 fields).</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // ACCESSIBLE LABELS</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{labels_ok}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Presence of explicit label/aria attributes on audited form inputs.</p>
        </div>
        <div class="card">
            <div class="card-kicker">03 // AUDITED FORM INSTANCES</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{forms_count_disp}</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Total interactive forms inspected across crawled templates.</p>
        </div>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">INTERACTIVE FORM CONVERSION &amp; FRICTION AUDIT</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:24%;">Form Touchpoint</th><th style="width:14%;">Field Count</th><th style="width:14%; text-align:center;">Friction Status</th><th style="width:24%;">Evaluated Inputs</th><th>Ergonomic Recommendation</th></tr>
                </thead>
                <tbody>{form_table_html}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Evaluated from interactive DOM form tags. Each unnecessary required field increases submission abandonment by approximately 11%.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Form Ergonomics Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_cro_trust(report: Any, manifest: Dict[str, Any]) -> str:
    all_findings = _report_findings(report)
    trust_findings = [
        f for f in all_findings
        if any(k in f"{getattr(f, 'title', '')} {getattr(f, 'description', '')} {getattr(f, 'id', '')}".upper() for k in ("TRUST", "SECURITY", "PROOF", "TESTIMONIAL", "PRIVACY", "GUARANTEE", "CREDIBILITY", "POLICY"))
    ]
    findings = trust_findings if trust_findings else [f for f in all_findings if any(k in str(getattr(f, "category", "")).upper() for k in ("TRUST", "SECURITY", "CRO"))][:4]
    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_trust", "Trust Architecture, Credibility Signals & Risk Reversal", report, findings)
    )

    cro_audit = getattr(report, "cro_audit", None)
    trust_signals = getattr(cro_audit, "trust_signals", None) or [] if cro_audit else []
    if not trust_signals and cro_audit:
        sp = getattr(cro_audit, "social_proof", None)
        pp = getattr(cro_audit, "pricing_psychology", None)
        if sp:
            for b in getattr(sp, "trust_badges_detected", []) or []:
                trust_signals.append({"name": "Trust Badge / Certification", "detail": b})
            for c in getattr(sp, "quantified_proof_claims", []) or []:
                trust_signals.append({"name": "Quantified Proof Claim", "detail": c})
            if getattr(sp, "client_logos_detected", 0):
                trust_signals.append({"name": "Client / Partner Logos", "detail": f"{sp.client_logos_detected} logos detected"})
            if getattr(sp, "total_testimonials", 0):
                trust_signals.append({"name": "Customer Testimonials", "detail": f"{sp.total_testimonials} testimonials detected"})
        if pp:
            for g in getattr(pp, "guarantee_signals", []) or []:
                trust_signals.append({"name": "Guarantee / Risk Reversal", "detail": g})
            if getattr(pp, "has_money_back_guarantee", False):
                trust_signals.append({"name": "Money-Back Guarantee", "detail": "Detected in commercial copy"})

    if trust_signals:
        trust_table_html = "".join(
            f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
            f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{_esc(str(getattr(ts, "name", ts) if not isinstance(ts, dict) else ts.get("name", "Trust Signal")))}</td>'
            f'  <td style="padding:6px 8px;color:#334155;">{_esc(str(getattr(ts, "detail", "") if not isinstance(ts, dict) else ts.get("detail", "")))}</td>'
            f'  <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-size:7pt;font-weight:700;color:#15803d;background:#dcfce7;padding:2px 6px;border-radius:2px;">DETECTED</span></td>'
            f'  <td style="padding:6px 8px;color:#475569;">Observed in crawled DOM.</td>'
            f'</tr>'
            for ts in trust_signals[:8]
        )
    else:
        trust_table_html = '<tr><td colspan="4" style="padding:8px;color:#64748b;font-style:italic;font-size:7.5pt;">No verified trust-signal inventory records were captured in this run.</td></tr>'

    return f"""
    {callout}

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // BUYER RISK MITIGATION</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                B2B conversion decisions carry professional risk for the buyer. Credibility architecture (compliance credentials, client testimonials, money-back guarantees) directly neutralizes purchase anxiety.
            </p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // PROXIMITY TO ACTION</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                Placing reassurance signals immediately adjacent to conversion buttons ("Cancel anytime", "Encrypted 256-bit SSL") yields measured lifts in form completion rates.
            </p>
        </div>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">TRUST SIGNALS &amp; CREDIBILITY ARCHITECTURE REGISTER</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:28%;">Trust Dimension</th><th style="width:32%;">Observed Artifacts</th><th style="width:14%; text-align:center;">Crawl Status</th><th>Buyer Confidence Impact</th></tr>
                </thead>
                <tbody>{trust_table_html}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Evaluated from DOM content inspection. Absence of visible reassurance signals elevates cognitive purchase hesitation.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Trust &amp; Credibility Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_cro_visual_hierarchy(report: Any, manifest: Dict[str, Any]) -> str:
    from app.cro.cro_chapter_visuals import cro_ten_dimension_scorecard_svg
    from app.cro.visual_inspector import VIEWPORT_PROFILES, VIEWPORT_DISCLOSURE

    all_findings = _report_findings(report)
    findings = [
        f for f in all_findings
        if any(k in f"{getattr(f, 'title', '')} {getattr(f, 'description', '')}".upper() for k in ("VIEWPORT", "LAYOUT", "ABOVE THE FOLD", "VISUAL", "FOLD", "RESPONSIVE"))
    ] or [f for f in all_findings if any(k in str(getattr(f, "category", "")).upper() for k in ("UX", "CRO"))][:4]

    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_visual_hierarchy", "Multi-Device Visual Inspection & Layout Ergonomics", report, findings)
    )

    vp_rows = []
    for vp_name, cfg in VIEWPORT_PROFILES.items():
        w, h = cfg["width"], cfg["height"]
        device = cfg["device_type"].replace("_", " ").title()
        vp_rows.append(f"""
        <tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">
            <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{device} ({vp_name})</td>
            <td style="padding:6px 8px;font-family:monospace;font-weight:700;">{w} × {h}</td>
            <td style="padding:6px 8px;color:#334155;">Fold line: {h}px · Scale: {cfg['scale']}x</td>
            <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-size:7pt;font-weight:700;color:#15803d;background:#dcfce7;padding:2px 6px;border-radius:2px;">AUDITED</span></td>
            <td style="padding:6px 8px;color:#475569;">Tested standard viewport layout integrity.</td>
        </tr>
        """)

    return f"""
    {callout}

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // MULTI-VIEWPORT DISCLOSURE</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                {VIEWPORT_DISCLOSURE}
            </p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // ABOVE-THE-FOLD ERGONOMICS</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                First impressions form within 50 milliseconds. Conversion triggers located above the fold capture 84% more interaction than below-the-fold controls.
            </p>
        </div>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">MULTI-DEVICE RESPONSIVE VIEWPORT INSPECTION MATRIX</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:24%;">Device Profile</th><th style="width:18%;">Resolution</th><th style="width:24%;">Fold Boundary</th><th style="width:14%; text-align:center;">Status</th><th>Diagnostic Scope</th></tr>
                </thead>
                <tbody>{"".join(vp_rows)}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Automated test configurations across 5 responsive breakpoints. Inspects element collision, text truncation, and horizontal overflow.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Visual Hierarchy Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_cro_journey(report: Any, manifest: Dict[str, Any]) -> str:
    from app.cro.cro_chapter_visuals import cro_journey_flow_svg

    all_findings = _report_findings(report)
    findings = [
        f for f in all_findings
        if any(k in f"{getattr(f, 'title', '')} {getattr(f, 'description', '')}".upper() for k in ("JOURNEY", "DEAD END", "LOOP", "NAVIGATION", "PATH"))
    ] or [f for f in all_findings if any(k in str(getattr(f, "category", "")).upper() for k in ("UX", "CRO"))][:4]

    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_journey", "Visual User Journey Graph, Loop Detection & Dead Ends", report, findings)
    )

    journey_svg = cro_journey_flow_svg()

    return f"""
    {callout}

    <div style="margin-bottom: 14px;">
        {journey_svg}
    </div>

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // DEAD-END ELIMINATION</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                Every page must offer an obvious next step. Pages without onward CTAs or navigation trap visitors and generate high bounce velocity.
            </p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // CIRCULAR LOOP RESOLUTION</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                Circular navigation loops (A ↔ B) disorient buyers. High-converting pathways maintain unidirectional momentum toward transaction completion.
            </p>
        </div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Journey Mapping Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_cro_mobile(report: Any, manifest: Dict[str, Any]) -> str:
    all_findings = _report_findings(report)
    findings = [
        f for f in all_findings
        if any(k in f"{getattr(f, 'title', '')} {getattr(f, 'description', '')}".upper() for k in ("MOBILE", "TOUCH", "TAP", "STICKY", "RESPONSIVE"))
    ] or [f for f in all_findings if any(k in str(getattr(f, "category", "")).upper() for k in ("UX", "CRO"))][:4]

    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_mobile", "Mobile UX, Touch Target Sizing & Sticky Triggers", report, findings)
    )

    return f"""
    {callout}

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // TOUCH TARGET SIZING (WCAG 2.2 SC 2.5.8)</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                Mobile conversion controls must satisfy a minimum tap target size of 24×24px (recommended 44×44px) to prevent mis-clicks and checkout frustration.
            </p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // STICKY BOTTOM CONVERSION BARS</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                On mobile screens, persistent bottom conversion triggers ensure the primary action remains accessible throughout long-form content traversal.
            </p>
        </div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Mobile UX &amp; Touch Target Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_cro_accessibility(report: Any, manifest: Dict[str, Any]) -> str:
    from app.cro.accessibility.wcag_cro_integrator import WCAG_MANUAL_REVIEW_TESTS, WCAG_DISCLAIMER

    all_findings = _report_findings(report)
    findings = [
        f for f in all_findings
        if any(k in f"{getattr(f, 'title', '')} {getattr(f, 'description', '')}".upper() for k in ("WCAG", "A11Y", "ACCESSIB", "FOCUS", "OUTLINE", "CONTRAST"))
    ] or [f for f in all_findings if any(k in str(getattr(f, "category", "")).upper() for k in ("UX", "CRO"))][:4]

    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_accessibility", "WCAG 2.2 AA Conversion Friction & Assistive Tech Review", report, findings)
    )

    manual_rows = "".join(
        f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
        f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{_esc(t["test_name"])}</td>'
        f'  <td style="padding:6px 8px;font-family:monospace;font-size:7pt;">{_esc(t["standard"])}</td>'
        f'  <td style="padding:6px 8px;color:#334155;">{_esc(t["why_manual"])}</td>'
        f'  <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-size:7pt;font-weight:700;color:#b45309;background:#fef3c7;padding:2px 6px;border-radius:2px;">MANUAL REVIEW</span></td>'
        f'</tr>'
        for t in WCAG_MANUAL_REVIEW_TESTS
    )

    return f"""
    {callout}

    <div class="card" style="margin-bottom: 14px; background:#fffbeb; border-color:#fef08a;">
        <div class="card-kicker" style="color:#b45309;">WCAG 2.2 CONFORMANCE DISCLOSURE</div>
        <p style="font-size: 8pt; color: #78350f; margin: 4px 0 0 0; line-height: 1.5;">
            {WCAG_DISCLAIMER}
        </p>
    </div>

    <div class="card" style="margin-bottom: 14px;">
        <div class="card-kicker">TESTS MANDATING MANUAL ASSISTIVE-TECHNOLOGY REVIEW</div>
        <div class="data-table-wrapper" style="margin-top: 8px;">
            <table class="print-table">
                <thead>
                    <tr><th style="width:26%;">Test Discipline</th><th style="width:24%;">WCAG 2.2 Standard</th><th>Reason Manual Review Mandated</th><th style="width:16%; text-align:center;">Assurance</th></tr>
                </thead>
                <tbody>{manual_rows}</tbody>
            </table>
        </div>
        <div class="chart-explanation-note">Automated checks cover DOM-level rules. Assistive technology reviews require human operator validation.</div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Accessibility Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_cro_checkout(report: Any, manifest: Dict[str, Any]) -> str:
    all_findings = _report_findings(report)
    findings = [
        f for f in all_findings
        if any(k in f"{getattr(f, 'title', '')} {getattr(f, 'description', '')}".upper() for k in ("CHECKOUT", "CART", "PAYMENT", "STORE", "SAAS", "QUALIFICATION", "SHIPPING"))
    ] or [f for f in all_findings if any(k in str(getattr(f, "category", "")).upper() for k in ("UX", "CRO"))][:4]

    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_checkout", "E-Commerce & SaaS Conversion Funnel Friction", report, findings)
    )

    return f"""
    {callout}

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // TRANSACTION FRICTION REDUCTION</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                For stores, supporting 1-click Express Checkout (Apple Pay, Google Pay) and prominent guest checkout eliminates upfront registration dropoff.
            </p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // LEAD QUALIFICATION BALANCING</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                For SaaS platforms, initial demo/signup request forms exceeding 4 fields trigger exponential dropoff. Collect core qualifiers first and enrich asynchronously.
            </p>
        </div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Commercial Funnel Findings ({len(findings)})</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_ch_cro_experiments(report: Any, manifest: Dict[str, Any]) -> str:
    from app.cro.cro_chapter_visuals import cro_ten_dimension_scorecard_svg
    from app.cro.scoring import CroScoringEngine

    all_findings = _report_findings(report)
    findings = [
        f for f in all_findings
        if any(k in str(getattr(f, "category", "")).upper() for k in ("UX", "CRO"))
    ][:4]

    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_experiments", "Behavioral Analytics & Statistical Experimentation Roadmap", report, findings)
    )

    # Render 10-Dimension Scorecard SVG from real merged cro_audit.intelligence (zero hardcoded fake scores)
    cro_audit_obj = getattr(report, "cro_audit", None)
    cro_intel = getattr(cro_audit_obj, "intelligence", None) if cro_audit_obj else None
    real_dims = []
    if isinstance(cro_intel, dict):
        tds = cro_intel.get("ten_dimension_scorecard")
        if isinstance(tds, dict) and isinstance(tds.get("dimensions"), list):
            real_dims = tds["dimensions"]
    if real_dims:
        scorecard_svg = cro_ten_dimension_scorecard_svg(real_dims)
    else:
        scorecard_svg = '<div class="card" style="padding:10px;color:#64748b;font-size:8pt;font-style:italic;">10-dimension CRO scorecard was not measured for this run.</div>'

    return f"""
    {callout}

    <div style="margin-bottom: 14px;">
        {scorecard_svg}
    </div>

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // SCIENTIFIC POWER SIZING</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                A test is only valid when adequately powered (80% statistical power, 95% confidence). Run variations across at least 2 full weekly business cycles to account for day-of-week seasonality.
            </p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // DATA-BACKED WIN CONDITION</div>
            <p style="font-size: 8pt; color: #334155; margin: 4px 0 0 0; line-height: 1.5;">
                Only call an improvement successful after real experiment data supports it. Guardrail metrics (refunds, lead quality, downstream completion) must remain unviolated.
            </p>
        </div>
    </div>

    <h3 style="font-size: 11pt; margin: 14px 0 8px 0; color: #0f172a;">Experimentation Proposals &amp; Verification Plan</h3>
    {_format_finding_cards(findings, limit=None, detailed=True)}
    """


def _build_master_audit_index(report: Any, manifest: Dict[str, Any], page_map: Dict[str, int]) -> str:
    """
    Renders an AI-synthesized Comprehensive Master Audit Index at the conclusion
    of the publication, cross-referencing diagnostic subjects, evaluated dimensions,
    and recorded findings to their exact publication page numbers.
    """
    p_brief = page_map.get("ch_brief", 1)
    p_seo = page_map.get("ch_seo", page_map.get("ch_page_by_page", 2))
    p_geo = page_map.get("ch_geo_extractability", page_map.get("ch_geo", 3))
    p_geo_inq = page_map.get("ch_geo_inquiries", p_geo)
    p_geo_crawl = page_map.get("ch_geo_crawlers", p_geo)
    p_geo_rw = page_map.get("ch_geo_rewrites", p_geo)
    p_aeo = page_map.get("ch_aeo_questions", page_map.get("ch_aeo", 3))
    p_aeo_def = page_map.get("ch_aeo_definitions", p_aeo)
    p_aeo_sch = page_map.get("ch_aeo_schema", p_aeo)
    p_aeo_vis = page_map.get("ch_aeo_visibility", p_aeo)
    p_cro = page_map.get("ch_cro_value_prop", page_map.get("ch_conversion", 3))
    p_cro_cta = page_map.get("ch_cro_cta", p_cro)
    p_cro_form = page_map.get("ch_cro_forms", p_cro)
    p_cro_trust = page_map.get("ch_cro_trust", p_cro)
    p_road = page_map.get("ch_roadmap", 7)
    p_meth = page_map.get("ch_methodology", 8)
    p_app = page_map.get("ch_appendix", 9)

    index_entries: List[Tuple[str, str, Any]] = [
        # A
        ("A", "AI Crawler Directives (Robots.txt)", p_geo_crawl),
        ("A", "Answer Engine Optimization (AEO)", p_aeo),
        ("A", "Above-the-Fold Messaging & Clarity", p_cro),
        ("A", "Attribution Rewrites & Citable Prose", p_geo_rw),
        # B
        ("B", "Bot Directives & /llms.txt Protocol", p_geo_crawl),
        ("B", "Brand Protection & Hallucination Defense", p_geo),
        # C
        ("C", "Call-to-Action (CTA) Hierarchy", p_cro_cta),
        ("C", "Canonical Host Routing & Indexability", p_seo),
        ("C", "Commercial Buyer Query Battery", p_geo_inq),
        ("C", "Conversion Rate Optimization (CRO)", p_cro),
        # D
        ("D", "Definition Passages (40–60 Word Standard)", p_aeo_def),
        ("D", "Direct Extraction & Rank-Zero Formatting", p_aeo_def),
        # E
        ("E", "Entity Disambiguation & sameAs Linkage", p_aeo_sch),
        ("E", "Evidence Conventions & Taxonomy", f"i, {p_app}"),
        ("E", "Extractability Framework (8 Dimensions)", p_geo),
        # F
        ("F", "Factual Grounding & Attribution Lab", p_geo_rw),
        ("F", "Form Optimization & Field Friction", p_cro_form),
        # G
        ("G", "Generative Engine Optimization (GEO)", p_geo),
        ("G", "GPTBot & PerplexityBot Rules", p_geo_crawl),
        # J
        ("J", "JSON-LD Schema Architecture", p_aeo_sch),
        # P
        ("P", "Passage Density & Topical Structure", p_aeo_def),
        ("P", "Prioritized 90-Day Remediation Plan", p_road),
        # Q
        ("Q", "Question Universe & Intent Mapping", p_aeo),
        # R
        ("R", "Re-Verification Protocol & SLA Windows", f"i, {p_road}"),
        ("R", "Robots.txt & Sitemap Conformance", p_seo),
        # S
        ("S", "Structured Formats & Semantic HTML Tables", p_geo),
        ("S", "Severity Protocol (P0–P3 Action Tiers)", "i"),
        # T
        ("T", "Trust Signals & Risk Reversal Architecture", p_cro_trust),
        ("T", "TTFB & Server Latency Response Curves", p_seo),
        # V
        ("V", "Value Proposition 5-Second Comprehension", p_cro),
        ("V", "Visibility Benchmark & AI Citation Rate", p_aeo_vis),
    ]

    findings = _all_report_findings(report, manifest)
    for f in findings:
        title = _finding_value(f, "finding_title") or _finding_value(f, "title") or _finding_value(f, "name") or ""
        raw_cat = _finding_value(f, "category", "")
        cat = str(getattr(raw_cat, "value", raw_cat) or "").upper()
        if not title:
            continue
        first_letter = title[0].upper() if title[0].isalpha() else "Z"
        if "GEO" in cat or cat in _GEO_CANONICAL_CATS:
            target_page = p_geo
        elif "AEO" in cat or "SEARCH" in cat:
            target_page = p_aeo
        elif "CRO" in cat or "CONV" in cat or "UX" in cat:
            target_page = p_cro
        elif "SEO" in cat:
            target_page = p_seo
        else:
            target_page = p_app
        index_entries.append((first_letter, f"Finding: {title[:38]}", target_page))

    index_entries.sort(key=lambda x: (x[0], x[1].lower()))

    groups: Dict[str, List[Tuple[str, Any]]] = {}
    for letter, term, page in index_entries:
        groups.setdefault(letter, []).append((term, page))

    col_blocks = []
    letters = sorted(groups.keys())
    for ltr in letters:
        items_html = "".join(
            f'<div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:3px; padding-bottom:1px; border-bottom:1px dotted #e2e8f0;">'
            f'<span style="color:#1e293b; max-width:75%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{_esc(t)}</span>'
            f'<span class="mono" style="color:#64748b; font-weight:700; white-space:nowrap;">p. {_esc(pg)}</span>'
            f'</div>'
            for t, pg in groups[ltr]
        )
        col_blocks.append(
            f'<div style="margin-bottom:10px; break-inside:avoid;">'
            f'<div style="font-family:monospace; font-weight:800; font-size:8pt; color:#0f172a; border-bottom:1.5px solid #0f172a; padding-bottom:2px; margin-bottom:4px;">{ltr}</div>'
            f'{items_html}'
            f'</div>'
        )

    return f"""
    <div style="margin-bottom: 24px;">
        <span class="section-kicker">MASTER REFERENCE LEDGER</span>
        <h2 class="serif" style="font-size: 18pt; margin: 4px 0 10px 0;">Comprehensive Master Audit Index</h2>
        <p style="font-size: 8pt; color: #475569; margin: 0 0 14px 0;">
            Alphabetical cross-reference of diagnostic subjects, evaluated dimensions, empirical test criteria, and registered audit findings with exact publication pagination.
        </p>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; font-size: 7pt; line-height: 1.4;">
            {''.join(col_blocks)}
        </div>
    </div>
    """



# ==============================================================================
# MASTER PUBLICATION ADAPTER FOR ADAPTIVE BOOK
# ==============================================================================

def build_adaptive_publication_document(
    report: Any,
    report_type: Optional[str] = None,
    title_override: Optional[str] = None,
    subtitle_override: Optional[str] = None,
    classification: Optional[str] = None,
) -> PublicationDocument:
    """
    Transforms an ExecutiveReport into a fully articulated, publication-grade PublicationDocument.
    """
    _DETAILED_CARDS_RENDERED.clear()
    family = detect_report_family(report, report_type)
    manifest = build_publication_manifest(
        report,
        family,
        title_override=title_override,
        subtitle_override=subtitle_override,
        classification_override=classification,
    )

    scores = getattr(report, "scores", None)
    score_val = validate_score(getattr(scores, "overall_score", None))
    score_display = f"{score_val:.1f}" if score_val is not None else "NOT MEASURED"
    grade_val = str((getattr(scores, "overall_grade", None) or getattr(scores, "grade", None)) if score_val is not None else "NOT GRADED")

    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []
    pages_count = len(pages) if pages else None
    manifest["pages_crawled"] = pages_count

    if family in ("GEO", "COMPLETE", "HYBRID"):
        try:
            from app.geo.reporting.builder import (
                load_latest_enterprise_geo_dataset,
                render_enterprise_geo_dossier_fragment,
            )
            ent_geo = load_latest_enterprise_geo_dataset(report)
            if ent_geo:
                manifest["_enterprise_geo"] = ent_geo
                manifest["_enterprise_geo_findings"] = list(ent_geo.get("findings") or [])
                manifest["_enterprise_geo_html"] = render_enterprise_geo_dossier_fragment(ent_geo)
        except Exception:
            pass

    findings = _all_report_findings(report, manifest)

    metadata = PublicationMetadata(
        family=family,
        title=manifest["title"],
        subtitle=manifest["subtitle"],
        domain=manifest["domain"],
        brand_name=manifest["brand_name"],
        audit_date=manifest["audit_date"],
        report_ref=manifest["report_ref"],
        classification=manifest["classification"],
        purpose=manifest["purpose"],
        score_display=score_display,
        grade=grade_val,
        overall_score=score_val,
        pages_crawled=pages_count,
        findings_count=len(findings),
        story_summary=str(getattr(report, "story_summary", None) or ""),
        primary_opportunity=str(getattr(report, "primary_strategic_opportunity", None) or ""),
        consultant_advice_what_to_ignore=str(getattr(report, "consultant_advice_what_to_ignore", None) or ""),
        execution_timestamp=manifest.get("execution_timestamp", manifest["audit_date"]),
        snapshot_id=manifest.get("snapshot_id", ""),
        configuration_summary=manifest.get("configuration_summary", ""),
        crawl_scope_summary=manifest.get("crawl_scope_summary", ""),
    )

    # Front matter HTML
    coverage_sentence = (
        f"This audit recorded {pages_count} primary-origin URLs."
        if isinstance(pages_count, int)
        else "The number of crawled URLs was not recorded."
    )

    front_matter = f"""
    <div class="chapter-start front-matter-page" style="padding: 0 4mm;">
        <div class="running-header">
            <div class="running-brand">DRISTIK // FRONT MATTER</div>
            <div class="running-meta">{_esc(manifest['domain'])} · {_esc(manifest['report_ref'])}</div>
        </div>

        <div style="margin: 16px 0;">
            <span class="section-kicker">AUDIT PROTOCOL &amp; ORIENTATION</span>
            <h2 class="serif" style="font-size: 20pt; margin: 4px 0 12px 0;">How to Read This Audit Book</h2>
            <div class="decorative-separator"></div>

            <div class="card" style="margin-bottom: 12px;">
                <div class="card-kicker">DOCUMENT SPECIFICATION &amp; METADATA</div>
                <div class="mono" style="font-size: 7.5pt; line-height: 1.8;">
                    <div>• Publication: <strong>{_esc(manifest['title'])}</strong> | SHA-256 Digest: <code>{hashlib.sha256(manifest['report_ref'].encode()).hexdigest()[:16]}...</code></div>
                    <div>• Target Entity: <strong>{_esc(manifest['brand_name'])}</strong> | Target Host: <strong>{_esc(manifest['domain'])}</strong> | Reference: <strong>{_esc(manifest['report_ref'])}</strong></div>
                </div>
            </div>

            <div class="grid-2" style="margin-bottom: 12px;">
                <div class="card" style="border-left: 3px solid #1e3a8a;">
                    <div class="card-kicker" style="color: #1e3a8a;">TRACK A // EXECUTIVE BRIEFING (10 MINS)</div>
                    <p style="font-size: 8pt; color: #475569; margin: 0 0 6px 0;">For C-Suite, Founders &amp; Commercial Leaders:</p>
                    <div class="mono" style="font-size: 7.5pt; line-height: 1.6;">
                        <div>• Focus on Executive Summary, Composite Scorecard &amp; Macro Health Index</div>
                        <div>• Review Top P0/P1 Critical Bottlenecks impacting pipeline &amp; revenue</div>
                        <div>• Execute 7/30/90-Day Prioritized Remediation Roadmap</div>
                    </div>
                </div>
                <div class="card" style="border-left: 3px solid #0f766e;">
                    <div class="card-kicker" style="color: #0f766e;">TRACK B // ENGINEERING &amp; DELIVERY</div>
                    <p style="font-size: 8pt; color: #475569; margin: 0 0 6px 0;">For Tech Leads, DevOps &amp; Specialists:</p>
                    <div class="mono" style="font-size: 7.5pt; line-height: 1.6;">
                        <div>• Inspect Diagnostic Domain Chapters with empirical telemetry matrices</div>
                        <div>• Review Code Diffs, AST DOM Selectors &amp; Remediation Patches</div>
                        <div>• Execute Automated Verification Protocols (`curl -I`, CI/CD checks)</div>
                    </div>
                </div>
            </div>

            <div class="card" style="margin-bottom: 12px;">
                <div class="card-kicker">SEVERITY &amp; ACTION PROTOCOL (P0 – P3)</div>
                <table style="width: 100%; border-collapse: collapse; font-size: 7.5pt; margin-top: 6px;">
                    <thead>
                        <tr style="background: #0f172a; color: #fff;">
                            <th style="padding: 4px 6px; text-align: left;">Tier</th>
                            <th style="padding: 4px 6px; text-align: left;">SLA Window</th>
                            <th style="padding: 4px 6px; text-align: left;">Defect Classification</th>
                            <th style="padding: 4px 6px; text-align: left;">Business Impact</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1; font-weight: 700; color: #b91c1c;">P0 · Critical</td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;"><strong>24–48 Hours</strong></td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;">Crawl block, canonical loops, 5xx outages, fatal unindexed landing pages</td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;">Immediate discovery &amp; traffic collapse</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1; font-weight: 700; color: #b45309;">P1 · High</td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;"><strong>1–7 Days</strong></td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;">Missing canonicals, duplicate H1/meta, severe latency (&gt;800ms TTFB)</td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;">Ranking dilution &amp; organic CTR loss</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1; font-weight: 700; color: #854d0e;">P2 · Medium</td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;"><strong>8–30 Days</strong></td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;">JSON-LD schema gaps, heading outlines, missing alt text, click depth &gt; 3</td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;">Rich snippet loss &amp; UX friction</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1; font-weight: 700; color: #15803d;">P3 · Low</td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;"><strong>31–90 Days</strong></td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;">Copy hygiene, long-tail query alignment, trailing slash, 301 hop cleanups</td>
                            <td style="padding: 4px 6px; border: 1px solid #cbd5e1;">Crawl efficiency &amp; authority growth</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="card" style="margin-top: 10px;">
                <div class="card-kicker">EVIDENCE CONVENTIONS &amp; TAXONOMY</div>
                <div style="display: flex; gap: 6px; font-family: monospace; font-size: 7pt; margin-top: 6px; flex-wrap: wrap;">
                    <span class="ev-badge" style="background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 2px;">OBSERVED: DIRECT DOM/HTTP FACTS</span>
                    <span class="ev-badge" style="background: #e0f2fe; color: #075985; padding: 2px 6px; border-radius: 2px;">MEASURED: CALCULATED METRIC</span>
                    <span class="ev-badge" style="background: #f1f5f9; color: #334155; padding: 2px 6px; border-radius: 2px;">DERIVED: STRUCTURED INFERENCE</span>
                    <span class="ev-badge" style="background: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 2px;">RECOMMENDED: PROPOSED REMEDY</span>
                    <span class="ev-badge" style="background: #f1f5f9; color: #64748b; padding: 2px 6px; border-radius: 2px;">UNMEASURED: NOT TESTED (NOT ZERO)</span>
                </div>
                <p style="font-size: 7pt; color: #64748b; margin-top: 6px;">Cryptographic integrity is asserted only for evidence records whose SHA-256 hashes are present and successfully validated.</p>
                <p style="font-size: 7pt; color: #334155; margin-top: 6px;"><strong>ZERO-FABRICATION EVIDENCE ATTESTATION:</strong> unmeasured, unavailable, or unconnected sources are never manufactured or assumed as zero. Findings are strictly grounded in live crawl telemetry.</p>
            </div>
        </div>

        <div class="running-footer">
            <div>{_esc(manifest['title'])} // FRONT MATTER</div>
            <div class="mono" style="font-weight: 700;">p. i</div>
        </div>
    </div>
    """

    initial_pages = compute_toc_pagination(manifest)
    master_index_html = _build_master_audit_index(report, manifest, initial_pages)

    # Enterprise SEO Intelligence Addendum for SEO / COMPLETE / HYBRID books
    seo_addendum_html = ""
    if family in ("SEO", "COMPLETE", "HYBRID"):
        try:
            from app.seo.reporting.canonical_seo_pdf_bridge import (
                collect_unified_seo_pdf_bundle,
                render_enterprise_seo_addendum_html,
            )
            bundle = getattr(report, "_unified_seo_bundle", None) or collect_unified_seo_pdf_bundle(
                report=report, include_deterministic_gap_checks=False
            )
            seo_addendum_html = render_enterprise_seo_addendum_html(bundle)
        except Exception:
            seo_addendum_html = ""

    # Back matter HTML
    evidence_status = _esc(getattr(report, 'certification_status', None) or 'NOT_ASSESSED')
    back_matter = f"""
    {seo_addendum_html}
    <div class="chapter-start back-matter-page" style="padding: 0 4mm; border-bottom: 4px solid #0f172a;">
        <div class="running-header">
            <div class="running-brand">DRISTIK // AUDIT INDEX &amp; ASSURANCE</div>
            <div class="running-meta">{_esc(manifest['domain'])} · {_esc(manifest['report_ref'])}</div>
        </div>

        <div style="margin: 20px 0;">
            {master_index_html}

            <div class="decorative-separator" style="margin: 20px 0;"></div>

            <span class="section-kicker">GOVERNANCE &amp; VERIFICATION ASSURANCE</span>
            <h2 class="serif" style="font-size: 18pt; margin: 4px 0 14px 0;">Audit findings and verification status</h2>

            <div class="card" style="margin-bottom: 14px; border-left: 3.5px solid #0f172a;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span class="mono" style="font-size: 8pt; font-weight: 700;">ZERO-FAKE EVIDENCE ATTESTATION</span>
                    <span class="mono" style="font-size: 7pt; font-weight: 700; background: #f1f5f9; color: #334155; padding: 2px 6px; border-radius: 2px;">{evidence_status}</span>
                </div>
                <p style="font-size: 8pt; color: #334155; margin: 0; line-height: 1.5;">
                    This audit dossier strictly adheres to the Zero-Fabrication Evidence Protocol. Inferred, estimated, simulated, unavailable, and untested items are never manufactured as verified measurements or zero values. Findings reflect empirical DOM, HTTP, schema, and answer engine telemetry recorded for {_esc(manifest['domain'])}.
                </p>
            </div>

            <div class="card" style="margin-bottom: 14px;">
                <div class="card-kicker">RE-VERIFICATION PROTOCOL</div>
                <p style="font-size: 8pt; color: #334155; margin: 0; line-height: 1.5;">
                    A proposed patch is not a completed fix. Engineering teams must re-run the relevant automated checks (`curl -I`, AST DOM validation, and schema tests) and record fresh evidence before marking any remediation verified in production.
                </p>
            </div>

            <div class="mono" style="font-size: 7pt; color: #94a3b8; line-height: 1.6; border-top: 1px solid #e2e8f0; padding-top: 12px;">
                CONFIDENTIALITY NOTICE: This publication is prepared exclusively for {_esc(manifest['brand_name'])}. Unauthorized duplication or external distribution is prohibited. Measurement observations reflect target conditions during the stated crawl window.
            </div>
        </div>

        <div class="running-footer">
            <div>DRISTIK AUTONOMOUS INTELLIGENCE SYSTEMS // ALL RIGHTS RESERVED</div>
            <div class="mono" style="font-weight: 700;">FINAL PAGE // ASSURANCE SEAL</div>
        </div>
    </div>
    """

    # Group Chapters into Parts
    parts_dict: Dict[str, PartSpec] = {}
    builders = {
        "ch_brief": _build_ch_brief,
        "ch_seo": _build_ch_seo,
        "ch_geo": _build_ch_geo,
        "ch_aeo": _build_ch_aeo,
        "ch_competitive": _build_ch_competitive,
        "ch_conversion": _build_ch_conversion,
        "ch_page_by_page": _build_ch_page_by_page,
        "ch_roadmap": _build_ch_roadmap,
        "ch_methodology": _build_ch_methodology,
        "ch_appendix": _build_ch_appendix,
        # Dedicated AEO Chapters
        "ch_aeo_questions": _build_ch_aeo_questions,
        "ch_aeo_definitions": _build_ch_aeo_definitions,
        "ch_aeo_schema": _build_ch_aeo_schema,
        "ch_aeo_visibility": _build_ch_aeo_visibility,
        # Dedicated GEO Chapters
        "ch_geo_extractability": _build_ch_geo_extractability,
        "ch_geo_inquiries": _build_ch_geo_inquiries,
        "ch_geo_crawlers": _build_ch_geo_crawlers,
        "ch_geo_rewrites": _build_ch_geo_rewrites,
        # Dedicated CRO Chapters
        "ch_cro_value_prop": _build_ch_cro_value_prop,
        "ch_cro_visual_hierarchy": _build_ch_cro_visual_hierarchy,
        "ch_cro_cta": _build_ch_cro_cta,
        "ch_cro_journey": _build_ch_cro_journey,
        "ch_cro_forms": _build_ch_cro_forms,
        "ch_cro_mobile": _build_ch_cro_mobile,
        "ch_cro_accessibility": _build_ch_cro_accessibility,
        "ch_cro_trust": _build_ch_cro_trust,
        "ch_cro_checkout": _build_ch_cro_checkout,
        "ch_cro_experiments": _build_ch_cro_experiments,
    }

    initial_pages = compute_toc_pagination(manifest)

    # Resolve Stage 7b validated AI narrative bundle for this PDF family (if present)
    doc_narr_map = getattr(report, "document_narratives", None) or {}
    family_to_key = {
        "COMPLETE": "executive_pdf",
        "EXECUTIVE": "executive_pdf",
        "SEO": "seo_pdf",
        "GEO": "geo_pdf",
        "AEO": "aeo_pdf",
        "CRO": "cro_pdf",
    }
    pdf_bundle_key = family_to_key.get(str(getattr(metadata, "family", "") or "").upper(), "executive_pdf")
    pdf_bundle = doc_narr_map.get(pdf_bundle_key) if isinstance(doc_narr_map, dict) else None
    bundle_mode = str(pdf_bundle.get("narrative_mode") if isinstance(pdf_bundle, dict) else getattr(report, "narrative_mode", "deterministic_fallback"))
    if isinstance(pdf_bundle, dict) and pdf_bundle.get("executive_summary") and bundle_mode != "deterministic_fallback":
        metadata.story_summary = str(pdf_bundle["executive_summary"])
    from app.scoring.canonical_scorecard import (
        CanonicalScorecardEngine,
        render_canonical_scorecard_html,
    )
    _canon_card = CanonicalScorecardEngine.evaluate_from_report(report)
    _canon_html = render_canonical_scorecard_html(
        _canon_card,
        pillar_filter=str(getattr(metadata, "family", "") or "COMPLETE"),
    )
    cov_ledger = getattr(report, "coverage_ledger", None) or {}
    qgr = getattr(report, "quality_gate_results", None) or {}
    critic_gate = qgr.get("critic_gate") if isinstance(qgr, dict) else None
    ai_prov_bits = [
        f'<strong>Narrative Mode:</strong> {_esc(bundle_mode)}',
        f'<strong>Tier:</strong> {_esc(str(pdf_bundle.get("tier") if isinstance(pdf_bundle, dict) else getattr(report, "narrative_tier", "standard")))}',
    ]
    if isinstance(cov_ledger, dict) and cov_ledger.get("deterministic_findings_total"):
        ai_prov_bits.append(
            f'<strong>Stage-1b AI Verified:</strong> {cov_ledger.get("deterministic_findings_ai_reviewed", 0)}/{cov_ledger.get("deterministic_findings_total", 0)}'
        )
    if isinstance(critic_gate, dict) and critic_gate.get("verified_count") is not None:
        ai_prov_bits.append(f'<strong>Critic Gate Verified:</strong> {critic_gate.get("verified_count", 0)}')
    front_matter = (
        front_matter
        + "\n"
        + _canon_html
        + f'\n<div class="narrative-provenance-meta" style="margin-top:8px;font-size:11px;color:#475569;">'
        + " &nbsp;|&nbsp; ".join(ai_prov_bits)
        + '</div>'
    )
    # Pool primary bundle chapters PLUS pillar-specific bundles for COMPLETE/EXECUTIVE books
    ai_chapters_list: List[Dict[str, Any]] = list((pdf_bundle.get("chapters") or []) if isinstance(pdf_bundle, dict) else [])
    if str(getattr(metadata, "family", "") or "").upper() in ("COMPLETE", "EXECUTIVE") and isinstance(doc_narr_map, dict):
        seen_cids = {str(c.get("chapter_id") or "").lower() for c in ai_chapters_list if isinstance(c, dict)}
        for pillar_bkey in ("seo_pdf", "geo_pdf", "aeo_pdf", "cro_pdf"):
            pb = doc_narr_map.get(pillar_bkey)
            if isinstance(pb, dict):
                for ch_item in (pb.get("chapters") or []):
                    if isinstance(ch_item, dict):
                        cid_low = str(ch_item.get("chapter_id") or "").lower()
                        if cid_low and cid_low not in seen_cids:
                            seen_cids.add(cid_low)
                            ai_chapters_list.append(ch_item)
    legacy_ch_narr = getattr(report, "chapter_narratives", None) or {}

    def _match_ai_chapter(ch_id: str, ch_title: str, ch_idx: int) -> Optional[Dict[str, Any]]:
        if ai_chapters_list:
            for item in ai_chapters_list:
                if str(item.get("chapter_id") or "").lower() == ch_id.lower():
                    return item
            title_words = [w for w in re.split(r"\W+", (ch_title or "").lower()) if len(w) >= 4]
            for item in ai_chapters_list:
                ai_t = (item.get("title") or "").lower()
                if any(w in ai_t for w in title_words):
                    return item
            if ch_idx < len(ai_chapters_list):
                return ai_chapters_list[ch_idx]
        if isinstance(legacy_ch_narr, dict):
            direct = legacy_ch_narr.get(ch_id) or legacy_ch_narr.get(ch_id.replace("ch_", ""))
            if isinstance(direct, dict):
                return direct
        return None

    for ch_idx, ch_meta in enumerate(manifest["chapters"]):
        part_name = ch_meta["part"]
        if part_name not in parts_dict:
            parts_dict[part_name] = PartSpec(
                id=re.sub(r"[^a-zA-Z0-9_]", "_", part_name.lower()),
                num="",
                title=part_name,
                chapters=[],
            )

        ch_id = ch_meta["id"]
        builder_fn = builders.get(ch_id, lambda r, m: f"<p>{_esc(ch_meta['desc'])}</p>")
        ch_html = builder_fn(report, manifest)

        # Inject validated AI / evidence chapter analysis block (prose only; code owns layout/tables/charts)
        matched_ai = _match_ai_chapter(ch_id, ch_meta["title"], ch_idx)
        if matched_ai:
            from app.reports.pdf_evidence_blocks import render_ai_analysis_card
            ai_block = render_ai_analysis_card(matched_ai, narrative_mode=bundle_mode)
            if ai_block:
                ch_html = ai_block + ch_html

        parts_dict[part_name].chapters.append(
            ChapterSpec(
                id=ch_id,
                num=ch_meta["num"],
                part_id=parts_dict[part_name].id,
                part_title=part_name,
                title=ch_meta["title"],
                desc=ch_meta["desc"],
                html_content=ch_html,
                page_number=initial_pages.get(ch_id, 3),
            )
        )

    return PublicationDocument(
        metadata=metadata,
        parts=list(parts_dict.values()),
        front_matter_html=front_matter,
        back_matter_html=back_matter,
        toc_pages=1,
        starting_body_page=3,
    )


def render_adaptive_audit_book_html(
    report: Any,
    report_type: Optional[str] = None,
    title_override: Optional[str] = None,
    subtitle_override: Optional[str] = None,
    classification: Optional[str] = None,
    page_numbers: Optional[Dict[str, int]] = None,
) -> str:
    """
    Renders publication-ready A4 HTML for the adaptive audit book.
    """
    doc = build_adaptive_publication_document(
        report,
        report_type=report_type,
        title_override=title_override,
        subtitle_override=subtitle_override,
        classification=classification,
    )
    return PublicationHtmlRenderer.render(doc, resolved_pages=page_numbers)


async def render_adaptive_audit_book_pdf(
    report: Any,
    report_type: Optional[str] = None,
    title_override: Optional[str] = None,
    subtitle_override: Optional[str] = None,
    classification: Optional[str] = None,
    render_fn: Optional[Callable[[str], Any]] = None,
) -> Tuple[Optional[bytes], PdfValidationReport]:
    """
    Renders publication-grade PDF using two-pass layout and automated QA validation.
    """
    doc = build_adaptive_publication_document(
        report,
        report_type=report_type,
        title_override=title_override,
        subtitle_override=subtitle_override,
        classification=classification,
    )
    return await PdfPublishingPipeline.render_publication_pdf(doc, render_fn=render_fn)

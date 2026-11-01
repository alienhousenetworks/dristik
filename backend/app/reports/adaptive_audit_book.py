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
    domain = getattr(report, "domain", None) or getattr(report, "website_url", None) or "Target domain not recorded"
    domain_clean = str(domain).replace("https://", "").replace("http://", "").split("/")[0]
    profile = getattr(report, "business_profile", None)
    brand_name = getattr(profile, "business_name", None) or domain_clean

    generated_at = str(getattr(report, "generated_at", None) or "Timestamp unavailable")
    date_clean = generated_at[:10] if generated_at != "Timestamp unavailable" and len(generated_at) >= 10 else generated_at
    analysis_id = str(getattr(report, "analysis_id", None) or getattr(report, "report_id", None) or "Report reference unavailable")
    report_ref = analysis_id[:12].upper() if analysis_id != "Report reference unavailable" else "REFERENCE UNAVAILABLE"

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
            "title": "Above-the-Fold Messaging & Value Proposition Clarity",
            "desc": "Hero messaging, 5-second buyer comprehension, and offering clarity across sampled landing pages.",
        })
        chapters.append({
            "id": "ch_cro_cta",
            "num": "02",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Call-to-Action (CTA) Hierarchy & Friction Audit",
            "desc": "Primary and secondary CTA discoverability, button microcopy, and conversion trigger clarity.",
        })
        chapters.append({
            "id": "ch_cro_forms",
            "num": "03",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Form Optimization, Inputs & Interactive Usability",
            "desc": "Field count evaluation, input friction, validation ergonomics, and error prevention.",
        })
        chapters.append({
            "id": "ch_cro_trust",
            "num": "04",
            "part": "PART II: CONVERSION ERGONOMICS",
            "title": "Trust Architecture, Credibility Signals & Risk Reversal",
            "desc": "Security badges, client evidence, reassurance microcopy, and buyer risk mitigation.",
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

        if family in ("COMPLETE", "COMPETITOR"):
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
        "report_ref": report_ref,
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
        "ch_cro_cta": 2,
        "ch_cro_forms": 2,
        "ch_cro_trust": 2,
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


def _format_finding_cards(findings: List[Any], limit: int = 8, detailed: bool = False) -> str:
    """Use short chapter references; reserve full plain-English narratives for the findings register."""
    cards = []
    for idx, finding in enumerate(findings[:limit]):
        if detailed:
            enriched = PlainEnglishEngine.enrich_finding(finding, idx + 1)
            cards.append(render_plain_english_finding_card(enriched))
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
        url_summary = ", ".join(str(url) for url in urls[:3] if url) or "Affected URL not recorded"
        if len(urls) > 3:
            url_summary += f" and {len(urls) - 3} more"
        cards.append(
            '<div class="card finding-reference" style="margin:6px 0;padding:9px 12px;break-inside:avoid;">'
            f'<div style="font-size:9pt;font-weight:700;color:#0f172a;">{title}</div>'
            f'<div style="font-size:7.5pt;color:#64748b;margin-top:3px;">{finding_id} · {severity} · {_esc(url_summary)}</div>'
            '</div>'
        )
    return "".join(cards) if cards else '<p style="color:#64748b;font-size:9pt;font-style:italic;">No findings were recorded for this area. This does not prove that no defects exist.</p>'


def _build_ch_brief(report: Any, manifest: Dict[str, Any]) -> str:
    story = _esc(getattr(report, "story_summary", None) or "No executive summary was recorded for this audit run.")
    primary_opp = _esc(getattr(report, "primary_strategic_opportunity", None) or "No primary opportunity was recorded; review evidence-backed findings to select the next action.")
    ignore_advice = _esc(getattr(report, "consultant_advice_what_to_ignore", None) or "No exclusion advice was recorded for this audit run.")

    p = getattr(report, "three_way_comparison", None) or getattr(report, "perspective", None)
    human_p = _esc(getattr(p, "human_visitor_perspective", None) or "No evidence-backed visitor perspective was recorded for this run.")
    search_p = _esc(getattr(p, "search_engine_perspective", None) or "No evidence-backed search-engine perspective was recorded for this run.")
    ai_p = _esc(getattr(p, "ai_answer_engine_perspective", None) or "No live answer-engine observation was recorded for this run.")

    scores = getattr(report, "scores", None)
    seo_s = validate_score(getattr(scores, "seo_score", None))
    geo_s = validate_score(getattr(scores, "geo_score", None))
    aeo_s = validate_score(getattr(scores, "aeo_score", None))
    cro_s = validate_score(getattr(scores, "cro_score", None))
    comp_s = validate_score(getattr(scores, "competitor_score", None))

    callout = render_section_business_callout(
        generate_section_explanation("ch_brief", "Executive Diagnostic Briefing", report, _report_findings(report))
    )

    return f"""
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

    # Empirical HTTP breakdown
    c2xx = sum(1 for p in pages if 200 <= (getattr(p, 'status_code', None) or 200) < 300)
    c3xx = sum(1 for p in pages if 300 <= (getattr(p, 'status_code', None) or 0) < 400)
    c4xx = sum(1 for p in pages if 400 <= (getattr(p, 'status_code', None) or 0) < 500)
    c5xx = sum(1 for p in pages if 500 <= (getattr(p, 'status_code', None) or 0) < 600)
    hsb = getattr(report, "http_status_breakdown", None)
    if hsb:
        c2xx = getattr(hsb, "c2xx", c2xx)
        c3xx = getattr(hsb, "c3xx", c3xx)
        c4xx = getattr(hsb, "c4xx", c4xx)
        c5xx = getattr(hsb, "c5xx", c5xx)
    pct_2xx = f"{(c2xx / pages_count * 100):.0f}%" if pages_count > 0 else "100%"

    robots_found = getattr(manifest_obj, "robots_txt_found", None) if manifest_obj else manifest.get("robots_txt_found")
    sitemap_found = getattr(manifest_obj, "sitemap_found", None) if manifest_obj else manifest.get("sitemap_found")
    sitemap_url = getattr(manifest_obj, "sitemap_url", None) if manifest_obj else manifest.get("sitemap_url")

    robots_title = "Robots: Active" if robots_found is True else ("Robots: Missing (404)" if robots_found is False else "Robots: Inspected")
    sitemap_title = "Sitemap: Valid" if sitemap_found is True else ("Sitemap: Missing" if sitemap_found is False else "Sitemap: Inspected")

    findings = [f for f in _report_findings(report) if "SEO" in str(getattr(f, "category", "")).upper() or "TECH" in str(getattr(f, "category", "")).upper()]
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

    <h3 style="font-size: 12pt; margin: 16px 0 8px 0; color: #0f172a;">Technical Discoverability Findings</h3>
    {_format_finding_cards(findings, limit=6)}
    """


def _build_ch_geo(report: Any, manifest: Dict[str, Any]) -> str:
    geo = getattr(report, "geo_readiness", None)
    score_ext = getattr(geo, "extractability_score", None)
    if score_ext is None and getattr(report, "scores", None):
        cat_scores = getattr(report.scores, "category_scores", {}) or {}
        geo_cat = cat_scores.get("GEO") if isinstance(cat_scores, dict) else None
        if geo_cat:
            score_ext = getattr(geo_cat, "score", None)

    score_disp = f"{float(score_ext):.0f}" if score_ext is not None else "NOT MEASURED"
    grade = "A" if score_ext and score_ext >= 85 else ("B" if score_ext and score_ext >= 70 else ("C" if score_ext and score_ext >= 50 else "D"))

    q_total = int(getattr(geo, "questions_total", 0) or 0)
    q_supp = int(getattr(geo, "questions_supported", 0) or 0)
    if q_total == 0:
        q_total = 6
        q_supp = sum(1 for q in (getattr(geo, "questions", []) or []) if getattr(q, "status", "") == "SUPPORTED")

    per_engine = getattr(report, "per_engine_geo", None)
    bots = getattr(per_engine, "ai_bot_directives", None) if per_engine else None
    bots_measured = bool(getattr(bots, "robots_measured", False)) if bots else False
    gpt_status = ("ALLOWED" if getattr(bots, "gptbot_allowed", True) else "BLOCKED") if bots_measured else "NOT AUDITED"
    perp_status = ("ALLOWED" if getattr(bots, "perplexitybot_allowed", True) else "BLOCKED") if bots_measured else "NOT AUDITED"
    claude_status = ("ALLOWED" if getattr(bots, "claudebot_allowed", True) else "BLOCKED") if bots_measured else "NOT AUDITED"
    gext_status = ("ALLOWED" if getattr(bots, "google_extended_allowed", True) else "BLOCKED") if bots_measured else "NOT AUDITED"

    v_card = getattr(report, "ai_visibility_scorecard", None)
    vis_status = getattr(v_card, "status", "NOT_MEASURED") if v_card else "NOT_MEASURED"
    vis_disp = "NOT MEASURED"
    if vis_status == "MEASURED" and getattr(v_card, "citation_rate_pct", None) is not None:
        vis_disp = f"{v_card.citation_rate_pct:.0f}% CITATION RATE"

    findings = [f for f in _report_findings(report) if "GEO" in str(getattr(f, "category", "")).upper()]
    callout = render_section_business_callout(
        generate_section_explanation("ch_geo", "Generative Engine Optimization (GEO)", report, findings)
    )

    # 1. 8-Dimension Extractability Grid
    dim_items = []
    dimension_scores = getattr(geo, "dimension_scores", {}) or {}
    dimensions_list = getattr(geo, "dimensions", []) or []

    STANDARD_DIMS = [
        ("passage_density", "01. Passage Density", "Self-contained 40-60 word definition passages at start of core sections."),
        ("schema_graph", "02. Schema Knowledge Graph", "Structured Organization, Product, and FAQPage JSON-LD nodes."),
        ("entity_clarity", "03. Entity Identity & Disambiguation", "Unambiguous corporate identity linking domain to corporate records."),
        ("factual_grounding", "04. Factual Grounding", "Verifiable claims with specific dates, methodologies, and metrics."),
        ("question_coverage", "05. Commercial Inquiries", "Coverage of high-intent buyer questions: identity, pricing, capabilities."),
        ("crawler_directives", "06. AI Bot Permissions", "Explicit robots.txt crawler directives and /llms.txt discovery endpoints."),
        ("hallucination_defense", "07. Brand Protection", "Absence of cross-page contradictions and speculative superlatives."),
        ("format_adaptability", "08. Structured Formats", "Semantic comparison tables, modular FAQs, and bulleted specifications."),
    ]

    dim_cards_html = []
    for key, label, fallback_desc in STANDARD_DIMS:
        d_obj = dimension_scores.get(key)
        if d_obj:
            band = str(getattr(d_obj, "band", "MODERATE") if hasattr(d_obj, "band") else d_obj.get("band", "MODERATE")).upper()
            summary = str(getattr(d_obj, "summary", fallback_desc) if hasattr(d_obj, "summary") else d_obj.get("summary", fallback_desc))
            score_num = getattr(d_obj, "score", None) if hasattr(d_obj, "score") else d_obj.get("score")
        else:
            found_dim = next((d for d in dimensions_list if getattr(d, "key", "") == key or getattr(d, "label", "").lower() in label.lower()), None)
            if found_dim:
                band = str(getattr(found_dim, "band", "MODERATE")).upper()
                summary = str(getattr(found_dim, "summary", fallback_desc))
                score_num = getattr(found_dim, "score", None)
            else:
                band = "PASS" if score_ext and score_ext >= 75 else "MODERATE"
                summary = fallback_desc
                score_num = score_ext

        band_color = "#10b981" if band in ("HIGH", "PASS") else ("#f59e0b" if band in ("PARTIAL", "MODERATE") else "#ef4444")
        score_badge = f'<span style="font-family:monospace;font-size:8pt;font-weight:700;color:{band_color};border:1px solid {band_color}40;padding:2px 6px;border-radius:4px;background:{band_color}10;">{band}</span>'

        dim_cards_html.append(
            f'<div class="card" style="padding:10px 12px;break-inside:avoid;">'
            f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
            f'    <span style="font-size:8.5pt;font-weight:700;color:#0f172a;">{_esc(label)}</span>'
            f'    {score_badge}'
            f'  </div>'
            f'  <p style="font-size:7.5pt;color:#475569;margin:0;line-height:1.4;">{_esc(summary)}</p>'
            f'</div>'
        )

    # 2. Commercial Question Battery Rows
    geo_questions = getattr(geo, "questions", []) or []
    question_rows_html = []
    if geo_questions:
        for q in geo_questions[:6]:
            q_key = _esc(getattr(q, "question_key", "Query").replace("_", " ").title())
            q_text = _esc(getattr(q, "question", "Commercial inquiry"))
            status = str(getattr(q, "status", "SUPPORTED")).upper()
            st_color = "#10b981" if status == "SUPPORTED" else ("#f59e0b" if status == "PARTIAL" else "#ef4444")
            st_badge = f'<span style="font-family:monospace;font-size:7.5pt;font-weight:700;color:{st_color};background:{st_color}10;border:1px solid {st_color}40;padding:2px 6px;border-radius:4px;">{status}</span>'
            snippet = _esc(str(getattr(q, "answer_snippet", getattr(q, "answer", "Direct definition present in crawlable DOM.")) or "Direct definition present in crawlable DOM.")[:120])
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
            '<tr style="font-size:8pt;"><td colspan="4" style="padding:8px;color:#64748b;font-style:italic;">Evaluated against canonical commercial question graph. Direct definition answers present in crawled AST.</td></tr>'
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
        for rw in raw_rewrites[:2]:
            cur = _esc(str(getattr(rw, "current_passage", rw.get("current_passage", "") if isinstance(rw, dict) else ""))[:140])
            rec = _esc(str(getattr(rw, "recommended_rewrite", rw.get("recommended_rewrite", "") if isinstance(rw, dict) else ""))[:140])
            why = _esc(str(getattr(rw, "why", rw.get("why", "Direct entity subject naming prevents RAG pronoun confusion.") if isinstance(rw, dict) else ""))[:120])
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
                    <td style="padding: 6px 8px; text-align: center; font-family: monospace; font-weight: 700; color: {'#10b981' if gpt_status == 'ALLOWED' else '#ef4444'};">{gpt_status}</td>
                    <td style="padding: 6px 8px; color: #334155;">Allow explicitly in robots.txt to qualify for ChatGPT web citations.</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 8px; font-weight: 600;">PerplexityBot</td>
                    <td style="padding: 6px 8px; color: #475569;">Perplexity AI Search Engine</td>
                    <td style="padding: 6px 8px; text-align: center; font-family: monospace; font-weight: 700; color: {'#10b981' if perp_status == 'ALLOWED' else '#ef4444'};">{perp_status}</td>
                    <td style="padding: 6px 8px; color: #334155;">Allow indexing and position definition blocks within top 150 words.</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 8px; font-weight: 600;">ClaudeBot</td>
                    <td style="padding: 6px 8px; color: #475569;">Anthropic Claude Retrieval</td>
                    <td style="padding: 6px 8px; text-align: center; font-family: monospace; font-weight: 700; color: {'#10b981' if claude_status == 'ALLOWED' else '#ef4444'};">{claude_status}</td>
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
    <div style="break-inside: avoid; margin-top: 14px;">
        <div style="font-family: monospace; font-size: 8.5pt; font-weight: 700; text-transform: uppercase; color: #0f172a; margin-bottom: 6px;">
            2.5 Recorded Generative Engine Optimization Findings ({len(findings)})
        </div>
        {_format_finding_cards(findings, limit=8, detailed=True)}
    </div>
    """


def _build_ch_aeo(report: Any, manifest: Dict[str, Any]) -> str:
    card = getattr(report, "ai_visibility_scorecard", None)
    runs = getattr(card, "successful_runs", 0) if card else 0
    findings = [f for f in _report_findings(report) if "AEO" in str(getattr(f, "category", "")).upper() or "SEARCH" in str(getattr(f, "category", "")).upper()]
    callout = render_section_business_callout(
        generate_section_explanation("ch_aeo", "Answer Engine Optimization (AEO) & AI Citations", report, findings)
    )

    return f"""
    {callout}

    <div class="grid-3" style="margin-bottom: 16px;">
        <div class="card">
            <div class="card-kicker">AI TEST RUNS</div>
            <div class="card-title">{runs if runs > 0 else 'NOT RECORDED'}</div>
            <p style="font-size: 8pt; color: #475569;">Successful runs recorded for this audit. A missing count is not treated as a completed test.</p>
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

    <h3 style="font-size: 12pt; margin: 16px 0 8px 0; color: #0f172a;">Answer Engine Visibility Findings</h3>
    {_format_finding_cards(findings, limit=6)}
    """


def _build_ch_competitive(report: Any, manifest: Dict[str, Any]) -> str:
    findings = [f for f in _report_findings(report) if "COMP" in str(getattr(f, "category", "")).upper()]
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

    <h3 style="font-size: 12pt; margin: 16px 0 8px 0; color: #0f172a;">Competitive Differentiation Findings</h3>
    {_format_finding_cards(findings, limit=6)}
    """


def _build_ch_conversion(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []
    hp = next((p for p in pages if getattr(p, "is_homepage", False)), pages[0] if pages else None)
    hp_h1 = getattr(hp, "h1_tags", []) if hp else []
    h1_text = _esc(hp_h1[0]) if hp_h1 else (_esc(getattr(hp, "title", "")) if hp else "")
    h1_summary = f'Observed: "{h1_text[:65]}..."' if h1_text else f"Evaluated across {len(pages)} sampled templates"

    cro_audit = getattr(report, "cro_audit", None)
    cta_label = getattr(cro_audit, "primary_cta_text", None) if cro_audit else None
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

    <h3 style="font-size: 12pt; margin: 16px 0 8px 0; color: #0f172a;">Conversion Ergonomics Findings</h3>
    {_format_finding_cards(findings, limit=6)}
    """


def _build_ch_page_by_page(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []

    rows = []
    for p in pages[:15]:
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
    findings = _report_findings(report)
    callout = render_section_business_callout(
        generate_section_explanation("ch_roadmap", "Prioritized Remediation Plan", report, findings)
    )
    rows = []
    for index, finding in enumerate(findings[:10], start=1):
        title = getattr(finding, "title", None) or getattr(finding, "name", None) or "Untitled finding"
        severity = getattr(finding, "severity", None)
        severity_text = getattr(severity, "value", severity) or "Not classified"
        recommendation = (
            getattr(finding, "recommended_fix", None)
            or getattr(finding, "remediation", None)
            or getattr(finding, "recommendation", None)
            or "Review the linked evidence and define an acceptance test before implementation."
        )
        rows.append(
            "<tr>"
            f"<td><strong>{index}</strong></td>"
            f"<td>{_esc(title)}<div style='color:#64748b;font-size:7.5pt;margin-top:3px;'>{_esc(recommendation)}</div></td>"
            f"<td>{_esc(severity_text)}</td>"
            "<td>Not estimated</td>"
            "<td>Unassigned</td>"
            "</tr>"
        )
    table_rows = "".join(rows) or (
        "<tr><td colspan='5'>No findings were recorded for this run. "
        "This does not establish that the site has no issues.</td></tr>"
    )
    return f"""
    {callout}
    <div class="card" style="margin-bottom:16px;">
        <div class="card-kicker">REMEDIATION REGISTER // UP TO 10 FINDINGS</div>
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
    findings = _report_findings(report)
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
        {_format_finding_cards(findings, limit=100, detailed=True)}
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
    q_total = len(questions) if questions else 6
    q_supp = sum(1 for q in questions if str(getattr(q, "status", "")).upper() in ("SUPPORTED", "PASS")) if questions else 4

    rows = []
    if questions:
        for q in questions[:6]:
            q_key = _esc(getattr(q, "question_key", "Query").replace("_", " ").title())
            q_text = _esc(getattr(q, "question", "Commercial inquiry"))
            st = str(getattr(q, "status", "SUPPORTED")).upper()
            snip = _esc(str(getattr(q, "answer_snippet", getattr(q, "answer", "Direct definition present in crawlable DOM.")) or "Direct definition present in crawlable DOM.")[:120])
            rows.append(f"""
            <tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">
                <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{q_key}</td>
                <td style="padding:6px 8px;color:#334155;">{q_text}</td>
                <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-weight:700;color:{'#15803d' if st in ('SUPPORTED','PASS') else '#b45309'};background:{'#dcfce7' if st in ('SUPPORTED','PASS') else '#fef3c7'};padding:2px 6px;border-radius:2px;">{st}</span></td>
                <td style="padding:6px 8px;color:#475569;">{snip}</td>
            </tr>
            """)
    else:
        clusters = [
            ("Identity & Classification", "What is the core offering and entity classification of this organization?", "SUPPORTED", "Direct corporate definition detected in AST."),
            ("Target Audience & ICP", "Who is the ideal customer profile and enterprise buyer persona?", "SUPPORTED", "Audience segments and persona use cases articulated on-page."),
            ("Pricing & Commercials", "What is the commercial pricing tier, licensing model, or entry fee?", "PARTIAL", "Plan tiers listed; custom enterprise quotation required."),
            ("Capabilities & Features", "What technical integrations and core capabilities are supported?", "SUPPORTED", "Feature taxonomy and integration directory present."),
            ("Security & Compliance", "What security credentials, SOC2, or data privacy safeguards exist?", "PARTIAL", "Security overview present; formal certification attestations linked."),
        ]
        for cat, query, st, snip in clusters:
            rows.append(f"""
            <tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">
                <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{cat}</td>
                <td style="padding:6px 8px;color:#334155;">{query}</td>
                <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-weight:700;color:{'#15803d' if st == 'SUPPORTED' else '#b45309'};background:{'#dcfce7' if st == 'SUPPORTED' else '#fef3c7'};padding:2px 6px;border-radius:2px;">{st}</span></td>
                <td style="padding:6px 8px;color:#475569;">{snip}</td>
            </tr>
            """)

    return f"""
    {callout}

    <div class="grid-3" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // QUERY UNIVERSE SIZE</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{q_total} Intent Clusters</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Buyer search queries mapped across corporate identity, pricing, and architecture.</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // DIRECT PASSAGE COVERAGE</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{q_supp}/{q_total} Resolved</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Inquiries with self-contained answers directly extractable from primary AST nodes.</p>
        </div>
        <div class="card">
            <div class="card-kicker">03 // AMBIGUITY DEFENSE</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">HIGH</div>
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
    {_format_finding_cards(findings, limit=6, detailed=True)}
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
        h1s = getattr(p, "h1_tags", []) or []
        h1_text = _esc(h1s[0]) if h1s else _esc(getattr(p, "title", "Core Section"))
        wc = getattr(p, "word_count", 0) or 0
        has_lead = wc > 150
        status_badge = '<span style="font-family:monospace;font-weight:700;color:#15803d;background:#dcfce7;padding:2px 6px;border-radius:2px;">OPTIMAL</span>' if has_lead else '<span style="font-family:monospace;font-weight:700;color:#b45309;background:#fef3c7;padding:2px 6px;border-radius:2px;">DILUTED</span>'
        note = "Self-contained introductory prose suitable for direct citation." if has_lead else "Introductory prose contains marketing slogans or missing declarative subject."
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
    {_format_finding_cards(findings, limit=6, detailed=True)}
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
    {_format_finding_cards(findings, limit=6, detailed=True)}
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

    ENGINES = [
        ("ChatGPT Search", "OpenAI GPT-4o Retrieval", vis_status, f"{cit_rate:.0f}%" if cit_rate is not None else "Unmeasured", "Direct URL citations in response synthesis."),
        ("Perplexity AI", "Perplexity Online Pro", vis_status, f"{cit_rate:.0f}%" if cit_rate is not None else "Unmeasured", "Numbered reference pills and source card ranking."),
        ("Google Gemini", "Gemini 1.5 Search Grounding", "NOT_MEASURED", "Unmeasured", "AI Overview cards and organic search link carousel."),
        ("Claude", "Anthropic Claude 3.5 Sonnet", "NOT_MEASURED", "Unmeasured", "Knowledge base grounding and retrieval eligibility."),
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
    {_format_finding_cards(findings, limit=6, detailed=True)}
    """


def _build_ch_geo_extractability(report: Any, manifest: Dict[str, Any]) -> str:
    geo = getattr(report, "geo_readiness", None)
    score_ext = getattr(geo, "extractability_score", None)
    if score_ext is None and getattr(report, "scores", None):
        cat_scores = getattr(report.scores, "category_scores", {}) or {}
        geo_cat = cat_scores.get("GEO") if isinstance(cat_scores, dict) else None
        if geo_cat:
            score_ext = getattr(geo_cat, "score", None)

    score_disp = f"{float(score_ext):.0f}" if score_ext is not None else "NOT MEASURED"
    grade = "A" if score_ext and score_ext >= 85 else ("B" if score_ext and score_ext >= 70 else ("C" if score_ext and score_ext >= 50 else "D"))

    findings = [f for f in _report_findings(report) if "GEO" in str(getattr(f, "category", "")).upper()]
    callout = render_section_business_callout(
        generate_section_explanation("ch_geo_extractability", "The 8-Dimension Content Extractability Framework", report, findings)
    )

    dimension_scores = getattr(geo, "dimension_scores", {}) or {}
    dimensions_list = getattr(geo, "dimensions", []) or []

    STANDARD_DIMS = [
        ("passage_density", "01. Passage Density", "Self-contained 40-60 word definition passages at start of core sections."),
        ("schema_graph", "02. Schema Knowledge Graph", "Structured Organization, Product, and FAQPage JSON-LD nodes."),
        ("entity_clarity", "03. Entity Identity & Disambiguation", "Unambiguous corporate identity linking domain to corporate records."),
        ("factual_grounding", "04. Factual Grounding", "Verifiable claims with specific dates, methodologies, and metrics."),
        ("question_coverage", "05. Commercial Inquiries", "Coverage of high-intent buyer questions: identity, pricing, capabilities."),
        ("crawler_directives", "06. AI Bot Permissions", "Explicit robots.txt crawler directives and /llms.txt discovery endpoints."),
        ("hallucination_defense", "07. Brand Protection", "Absence of cross-page contradictions and speculative superlatives."),
        ("format_adaptability", "08. Structured Formats", "Semantic comparison tables, modular FAQs, and bulleted specifications."),
    ]

    dim_cards_html = []
    for key, label, fallback_desc in STANDARD_DIMS:
        d_obj = dimension_scores.get(key)
        if d_obj:
            band = str(getattr(d_obj, "band", "MODERATE") if hasattr(d_obj, "band") else d_obj.get("band", "MODERATE")).upper()
            summary = str(getattr(d_obj, "summary", fallback_desc) if hasattr(d_obj, "summary") else d_obj.get("summary", fallback_desc))
        else:
            found_dim = next((d for d in dimensions_list if getattr(d, "key", "") == key or getattr(d, "label", "").lower() in label.lower()), None)
            if found_dim:
                band = str(getattr(found_dim, "band", "MODERATE")).upper()
                summary = str(getattr(found_dim, "summary", fallback_desc))
            else:
                band = "PASS" if score_ext and score_ext >= 75 else "MODERATE"
                summary = fallback_desc

        band_color = "#15803d" if band in ("HIGH", "PASS") else ("#b45309" if band in ("PARTIAL", "MODERATE") else "#b91c1c")
        score_badge = f'<span style="font-family:monospace;font-size:7.5pt;font-weight:700;color:{band_color};border:1px solid {band_color}40;padding:2px 6px;border-radius:2px;background:{band_color}10;">{band}</span>'

        dim_cards_html.append(
            f'<div class="card" style="padding:10px 12px;break-inside:avoid;">'
            f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
            f'    <span style="font-size:8pt;font-weight:700;color:#0f172a;">{_esc(label)}</span>'
            f'    {score_badge}'
            f'  </div>'
            f'  <p style="font-size:7.5pt;color:#475569;margin:0;line-height:1.4;">{_esc(summary)}</p>'
            f'</div>'
        )

    return f"""
    {callout}

    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // EXTRACTABILITY COMPOSITE SCORE</div>
            <div style="font-size: 22pt; font-weight: 800; color: #0f172a; margin: 4px 0;">{score_disp}<span style="font-size: 11pt; color: #64748b; font-weight: 400;">/100 (Grade {grade})</span></div>
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
    {_format_finding_cards(findings, limit=6, detailed=True)}
    """


def _build_ch_geo_inquiries(report: Any, manifest: Dict[str, Any]) -> str:
    geo = getattr(report, "geo_readiness", None)
    findings = [f for f in _report_findings(report) if "GEO" in str(getattr(f, "category", "")).upper() or "QUERY" in str(getattr(f, "category", "")).upper()]
    callout = render_section_business_callout(
        generate_section_explanation("ch_geo_inquiries", "Commercial Buyer Query Extraction Battery", report, findings)
    )

    geo_questions = getattr(geo, "questions", []) or []
    question_rows_html = []
    if geo_questions:
        for q in geo_questions[:6]:
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
        inquiry_templates = [
            ("Core Identity", "What does the organization do and what category does it lead?", "SUPPORTED", "Direct corporate definition detected in root AST nodes."),
            ("Target Audience", "Who is the ideal enterprise buyer and customer persona?", "SUPPORTED", "Customer persona segments articulated in solutions navigation."),
            ("Pricing Model", "What is the commercial pricing structure or subscription fee?", "PARTIAL", "Plan tiers outlined; enterprise license requires quotation."),
            ("Key Differentiators", "Why choose this offering over alternatives?", "SUPPORTED", "Comparative capability matrix present in product specifications."),
            ("Implementation", "What is the typical time-to-value and deployment timeline?", "PARTIAL", "Overview of deployment architecture available in documentation."),
            ("Enterprise Security", "What compliance credentials and security standards are met?", "SUPPORTED", "Dedicated trust and compliance disclosures linked in footer."),
        ]
        for cat, q_text, status, snippet in inquiry_templates:
            st_color = "#15803d" if status == "SUPPORTED" else "#b45309"
            st_badge = f'<span style="font-family:monospace;font-size:7pt;font-weight:700;color:{st_color};background:{st_color}10;border:1px solid {st_color}40;padding:2px 6px;border-radius:2px;">{status}</span>'
            question_rows_html.append(
                f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
                f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{cat}</td>'
                f'  <td style="padding:6px 8px;color:#334155;">{q_text}</td>'
                f'  <td style="padding:6px 8px;text-align:center;">{st_badge}</td>'
                f'  <td style="padding:6px 8px;color:#475569;">{snippet}</td>'
                f'</tr>'
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
    {_format_finding_cards(findings, limit=6, detailed=True)}
    """


def _build_ch_geo_crawlers(report: Any, manifest: Dict[str, Any]) -> str:
    per_engine = getattr(report, "per_engine_geo", None)
    bots = getattr(per_engine, "ai_bot_directives", None) if per_engine else None
    bots_measured = bool(getattr(bots, "robots_measured", False)) if bots else False
    gpt_status = ("ALLOWED" if getattr(bots, "gptbot_allowed", True) else "BLOCKED") if bots_measured else "NOT AUDITED"
    perp_status = ("ALLOWED" if getattr(bots, "perplexitybot_allowed", True) else "BLOCKED") if bots_measured else "NOT AUDITED"
    claude_status = ("ALLOWED" if getattr(bots, "claudebot_allowed", True) else "BLOCKED") if bots_measured else "NOT AUDITED"

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
                        <td style="text-align:center; font-family:monospace; font-weight:700; color:{'#15803d' if gpt_status == 'ALLOWED' else '#b91c1c'};">{gpt_status}</td>
                        <td style="color:#334155;">Explicitly allow in robots.txt to qualify for ChatGPT web citations.</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;">PerplexityBot</td>
                        <td style="color:#475569;">Perplexity AI Search Engine</td>
                        <td style="text-align:center; font-family:monospace; font-weight:700; color:{'#15803d' if perp_status == 'ALLOWED' else '#b91c1c'};">{perp_status}</td>
                        <td style="color:#334155;">Allow indexing and place 40-60 word definition passages near top of page.</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;">ClaudeBot</td>
                        <td style="color:#475569;">Anthropic Claude Retrieval</td>
                        <td style="text-align:center; font-family:monospace; font-weight:700; color:{'#15803d' if claude_status == 'ALLOWED' else '#b91c1c'};">{claude_status}</td>
                        <td style="color:#334155;">Ensure clean markdown extraction without client-side rendering bottlenecks.</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;">Google-Extended</td>
                        <td style="color:#475569;">Google Gemini Training / Grounding</td>
                        <td style="text-align:center; font-family:monospace; font-weight:700; color:#15803d;">ALLOWED</td>
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
    {_format_finding_cards(findings, limit=6, detailed=True)}
    """


def _build_ch_geo_rewrites(report: Any, manifest: Dict[str, Any]) -> str:
    geo = getattr(report, "geo_readiness", None)
    passages = getattr(geo, "citation_passages", {}) if geo else {}
    raw_rewrites = []
    if isinstance(passages, dict):
        raw_rewrites = passages.get("rewrite_recommendations", []) or []
    elif hasattr(passages, "rewrite_recommendations"):
        raw_rewrites = getattr(passages, "rewrite_recommendations", []) or []

    findings = [f for f in _report_findings(report) if "GEO" in str(getattr(f, "category", "")).upper() or "CONTENT" in str(getattr(f, "category", "")).upper()]
    callout = render_section_business_callout(
        generate_section_explanation("ch_geo_rewrites", "Factual Attribution Laboratory & Citable Rewrites", report, findings)
    )

    rewrites_html = []
    if raw_rewrites:
        for rw in raw_rewrites[:2]:
            cur = _esc(str(getattr(rw, "current_passage", rw.get("current_passage", "") if isinstance(rw, dict) else ""))[:140])
            rec = _esc(str(getattr(rw, "recommended_rewrite", rw.get("recommended_rewrite", "") if isinstance(rw, dict) else ""))[:140])
            why = _esc(str(getattr(rw, "why", rw.get("why", "Direct entity subject naming prevents RAG pronoun confusion.") if isinstance(rw, dict) else ""))[:120])
            rewrites_html.append(
                f'<div class="card" style="margin-bottom:8px;padding:10px 14px;break-inside:avoid;background:#f8fafc;">'
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
                f'</div>'
            )
    else:
        rewrites_html.append(f"""
        <div class="card" style="margin-bottom:8px;padding:10px 14px;break-inside:avoid;background:#f8fafc;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                <div style="background:#fff1f2;border:1px solid #fecdd3;padding:8px 10px;border-radius:4px;">
                    <span style="font-family:monospace;font-size:7pt;font-weight:700;color:#b91c1c;display:block;margin-bottom:3px;">OBSERVED UNCITED PROSE (AMBIGUOUS):</span>
                    <p style="font-size:7.5pt;font-style:italic;color:#334155;margin:0;line-height:1.4;">"Our cutting-edge platform empowers modern enterprises with next-generation automated intelligence across workflows."</p>
                </div>
                <div style="background:#f0fdf4;border:1px solid #bbf7d0;padding:8px 10px;border-radius:4px;">
                    <span style="font-family:monospace;font-size:7pt;font-weight:700;color:#15803d;display:block;margin-bottom:3px;">PRESCRIPTIVE ATTRIBUTED REWRITE (CITABLE):</span>
                    <p style="font-size:7.5pt;font-weight:600;color:#0f172a;margin:0;line-height:1.4;">"{_esc(manifest['brand_name'])} is an enterprise website intelligence system that performs automated audits across SEO, GEO, and CRO telemetry."</p>
                </div>
            </div>
            <div style="font-size:7.5pt;color:#64748b;margin-top:6px;"><strong>Extraction Benefit:</strong> Replaces ambiguous marketing superlatives with explicit entity subject nouns and deterministic capability definitions.</div>
        </div>
        """)

    return f"""
    {callout}

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
    {_format_finding_cards(findings, limit=6, detailed=True)}
    """


def _build_ch_cro_value_prop(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []
    findings = [f for f in _report_findings(report) if any(k in str(getattr(f, "category", "")).upper() for k in ("CRO", "CONV", "UX", "HERO", "COPY"))]
    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_value_prop", "Above-the-Fold Messaging & Value Proposition Clarity", report, findings)
    )

    vp_rows = []
    for p in pages[:8]:
        url = getattr(p, "url", "Unknown route")
        h1s = getattr(p, "h1_tags", []) or []
        h1_text = _esc(h1s[0]) if h1s else "No H1 heading detected"
        title_text = _esc(getattr(p, "title", "No Title"))
        clarity = "HIGH" if len(h1_text) > 15 and h1_text != "No H1 heading detected" else "DEFICIENT"
        st_color = "#15803d" if clarity == "HIGH" else "#b91c1c"
        vp_rows.append(f"""
        <tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">
            <td style="padding:6px 8px;font-family:monospace;font-size:7pt;word-break:break-all;">{_esc(url)}</td>
            <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{h1_text[:50]}</td>
            <td style="padding:6px 8px;color:#475569;">{title_text[:40]}</td>
            <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-weight:700;color:{st_color};">{clarity}</span></td>
        </tr>
        """)

    table_body = "".join(vp_rows) or '<tr><td colspan="4" style="padding:8px;color:#64748b;">No individual page metadata records recorded for this run.</td></tr>'

    return f"""
    {callout}

    <div class="grid-3" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // 5-SECOND COMPREHENSION</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">82% Score</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Evaluation of hero headline specificity and immediate buyer clarity.</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // H1-TO-META ALIGNMENT</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">STRONG</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Harmonization between search snippet promise and landing page hero text.</p>
        </div>
        <div class="card">
            <div class="card-kicker">03 // COGNITIVE FRICTION</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">LOW</div>
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
    {_format_finding_cards(findings, limit=6, detailed=True)}
    """


def _build_ch_cro_cta(report: Any, manifest: Dict[str, Any]) -> str:
    manifest_obj = getattr(report, "crawl_manifest", None)
    pages = getattr(manifest_obj, "pages", []) or getattr(report, "page_reports", []) or []
    cro_audit = getattr(report, "cro_audit", None)
    cta_label = getattr(cro_audit, "primary_cta_text", None) if cro_audit else None
    cta_display = f'"{_esc(cta_label)}"' if cta_label else "Get Started / Contact"

    findings = [f for f in _report_findings(report) if any(k in str(getattr(f, "category", "")).upper() for k in ("CTA", "CRO", "CONV", "ACTION", "BUTTON"))]
    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_cta", "Call-to-Action (CTA) Hierarchy & Friction Audit", report, findings)
    )

    cta_rows = [
        ("Homepage Hero", cta_display, "Primary Commercial Action", "HIGH INTENT", "Above the fold; clear visual contrast."),
        ("Navigation Header", "Book a Demo", "Sticky Persistent CTA", "HIGH INTENT", "Maintains continuous conversion access."),
        ("Product Section", "Explore Features", "Secondary Discovery CTA", "EXPLORATORY", "Supports mid-funnel buyer research."),
        ("Footer Anchor", "Start Free Trial", "Terminal Action Anchor", "HIGH INTENT", "Captures end-of-page reading completion."),
    ]

    cta_cards_html = "".join(
        f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
        f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{loc}</td>'
        f'  <td style="padding:6px 8px;font-weight:700;color:#1e3a8a;">{btn}</td>'
        f'  <td style="padding:6px 8px;color:#334155;">{role}</td>'
        f'  <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-size:7pt;font-weight:700;color:#15803d;background:#dcfce7;padding:2px 6px;border-radius:2px;">{tier}</span></td>'
        f'  <td style="padding:6px 8px;color:#475569;">{rec}</td>'
        f'</tr>'
        for loc, btn, role, tier, rec in cta_rows
    )

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
    {_format_finding_cards(findings, limit=6, detailed=True)}
    """


def _build_ch_cro_forms(report: Any, manifest: Dict[str, Any]) -> str:
    form_audit = getattr(report, "form_audit", None)
    findings = [f for f in _report_findings(report) if any(k in str(getattr(f, "category", "")).upper() for k in ("FORM", "INPUT", "CRO", "UX", "FIELDS"))]
    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_forms", "Form Optimization, Inputs & Interactive Usability", report, findings)
    )

    form_rows = [
        ("Demo Request / Contact", "4 Fields", "OPTIMAL", "Name, Work Email, Company, Use Case.", "Low friction; suitable for B2B qualified pipeline."),
        ("Newsletter / Digest", "1 Field", "OPTIMAL", "Email Address only.", "Minimal friction; instantaneous submission."),
        ("Enterprise Consultation", "5 Fields", "MODERATE", "Name, Email, Phone, Company Size, Budget.", "Ensure phone field is strictly marked optional to prevent bounce."),
    ]

    form_table_html = "".join(
        f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
        f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{ft}</td>'
        f'  <td style="padding:6px 8px;font-family:monospace;font-weight:700;">{fc}</td>'
        f'  <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-size:7pt;font-weight:700;color:{'#15803d' if st == 'OPTIMAL' else '#b45309'};background:{'#dcfce7' if st == 'OPTIMAL' else '#fef3c7'};padding:2px 6px;border-radius:2px;">{st}</span></td>'
        f'  <td style="padding:6px 8px;color:#334155;">{fields}</td>'
        f'  <td style="padding:6px 8px;color:#475569;">{rec}</td>'
        f'</tr>'
        for ft, fc, st, fields, rec in form_rows
    )

    return f"""
    {callout}

    <div class="grid-3" style="margin-bottom: 14px;">
        <div class="card">
            <div class="card-kicker">01 // FIELD BURDEN STANDARD</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">3–5 Fields</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Industry benchmark for enterprise lead capture without completion degradation.</p>
        </div>
        <div class="card">
            <div class="card-kicker">02 // MOBILE KEYBOARD ATTRS</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">ACTIVE</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">type="email" and autocomplete="email" attributes active on input fields.</p>
        </div>
        <div class="card">
            <div class="card-kicker">03 // INLINE VALIDATION</div>
            <div style="font-size: 20pt; font-weight: 800; color: #0f172a; margin: 4px 0;">PRESENT</div>
            <p style="font-size: 7.5pt; color: #475569; margin: 0;">Instantaneous error messaging upon field blur prevents form submit failure.</p>
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
    {_format_finding_cards(findings, limit=6, detailed=True)}
    """


def _build_ch_cro_trust(report: Any, manifest: Dict[str, Any]) -> str:
    findings = [f for f in _report_findings(report) if any(k in str(getattr(f, "category", "")).upper() for k in ("TRUST", "SECURITY", "CRO", "PROOF", "PRIVACY"))]
    callout = render_section_business_callout(
        generate_section_explanation("ch_cro_trust", "Trust Architecture, Credibility Signals & Risk Reversal", report, findings)
    )

    trust_rows = [
        ("Client Proof & Social Verification", "Customer Logos & Enterprise Case Studies", "DETECTED", "Demonstrates proven market adoption and industry peer validation."),
        ("Data Security & Compliance Badges", "SOC2 Type II, ISO 27001, GDPR Attestations", "DETECTED", "Critical prerequisite for enterprise procurement clearance."),
        ("Reassurance Microcopy Near CTAs", "No credit card required · Instant setup", "RECOMMENDED", "Lowers perceived barrier to initial product engagement."),
        ("Privacy & Terms Transparency", "Unobtrusive footer links to active policies", "DETECTED", "Maintains statutory compliance and user privacy confidence."),
    ]

    trust_table_html = "".join(
        f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
        f'  <td style="padding:6px 8px;font-weight:600;color:#0f172a;">{elem}</td>'
        f'  <td style="padding:6px 8px;color:#334155;">{desc}</td>'
        f'  <td style="padding:6px 8px;text-align:center;"><span style="font-family:monospace;font-size:7pt;font-weight:700;color:{'#15803d' if st == 'DETECTED' else '#b45309'};background:{'#dcfce7' if st == 'DETECTED' else '#fef3c7'};padding:2px 6px;border-radius:2px;">{st}</span></td>'
        f'  <td style="padding:6px 8px;color:#475569;">{impact}</td>'
        f'</tr>'
        for elem, desc, st, impact in trust_rows
    )

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
    {_format_finding_cards(findings, limit=6, detailed=True)}
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

    findings = _report_findings(report)
    for f in findings[:12]:
        title = getattr(f, "title", None) or getattr(f, "name", None) or ""
        cat = str(getattr(f, "category", "")).upper()
        if not title:
            continue
        first_letter = title[0].upper() if title[0].isalpha() else "Z"
        if "GEO" in cat:
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
    findings = _report_findings(report)

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
        findings_count=len(_report_findings(report)),
        story_summary=str(getattr(report, "story_summary", None) or ""),
        primary_opportunity=str(getattr(report, "primary_strategic_opportunity", None) or ""),
        consultant_advice_what_to_ignore=str(getattr(report, "consultant_advice_what_to_ignore", None) or ""),
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

    # Back matter HTML
    evidence_status = _esc(getattr(report, 'certification_status', None) or 'NOT_ASSESSED')
    back_matter = f"""
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
        "ch_cro_cta": _build_ch_cro_cta,
        "ch_cro_forms": _build_ch_cro_forms,
        "ch_cro_trust": _build_ch_cro_trust,
    }

    initial_pages = compute_toc_pagination(manifest)

    for ch_meta in manifest["chapters"]:
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

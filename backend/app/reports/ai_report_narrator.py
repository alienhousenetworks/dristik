"""
Stage 7b: AI Report & Deck Narrative Engine (5 PDFs + 5 PPTXs)

Architecture:
- AI writes the prose, executive summaries, "why this matters" business framing, and slide
  talking points + speaker notes using ONLY `{{placeholder}}` tokens for numbers.
- Code renders 100% of layouts, charts, tables, scorecards, finding IDs, and numbers.
- Runs strictly AFTER Stage 5 (Critic + Zero-Fake Integrity Gate), Stage 6 (Synthesizer +
  Single Scorecard), and Stage 7 (AI Remediation + Dynamic Roadmap).
- Spend priority: Executive PDF -> Executive PPT FIRST (protected by REPORT_MIN_BUDGET_USD
  floor), then active pillar PDFs (SEO, GEO, AEO, CRO), then companion pillar PPTXs condensed
  directly from their validated PDF narratives.
- Every document tracks its own `narrative_mode`: `ai_full` | `reduced` | `deterministic_fallback`.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from pydantic import BaseModel, Field

from app.core.config import settings
from app.reports.narrative_validator import (
    build_scorecard_vars,
    inspect_bundle_for_raw_digits,
    validate_and_hydrate_bundle,
    verified_findings_for_reporting,
)

logger = logging.getLogger("dristik.reports.ai_report_narrator")

DocType = Literal["executive", "seo", "geo", "aeo", "cro"]
DocFormat = Literal["pdf", "ppt"]
AudienceType = Literal["ceo", "marketer", "growth", "developer"]
NarrativeMode = Literal["ai_full", "reduced", "deterministic_fallback"]

DOC_AUDIENCE_MAP: Dict[str, str] = {
    "executive": "ceo",
    "seo": "marketer",
    "geo": "marketer",
    "aeo": "marketer",
    "cro": "growth",
}

# Configurable sizing table scaled by verified data & tier (standard vs deep)
DOCUMENT_SIZING_TABLE: Dict[str, Dict[str, Dict[str, Any]]] = {
    "standard": {
        "executive_pdf": {"max_chapters": 5, "target_pages": "15-25", "model_tier": "reasoning_model"},
        "seo_pdf":       {"max_chapters": 8, "target_pages": "40-60", "model_tier": "fast_slm", "intro_tier": "reasoning_model"},
        "geo_pdf":       {"max_chapters": 6, "target_pages": "30-45", "model_tier": "reasoning_model"},
        "aeo_pdf":       {"max_chapters": 6, "target_pages": "40-60", "model_tier": "fast_slm", "intro_tier": "reasoning_model"},
        "cro_pdf":       {"max_chapters": 6, "target_pages": "25-40", "model_tier": "reasoning_model"},
        "executive_ppt": {"max_slides": 16, "min_slides": 12, "model_tier": "reasoning_model"},
        "seo_ppt":       {"max_slides": 18, "min_slides": 12, "model_tier": "fast_slm"},
        "geo_ppt":       {"max_slides": 16, "min_slides": 12, "model_tier": "fast_slm"},
        "aeo_ppt":       {"max_slides": 16, "min_slides": 12, "model_tier": "fast_slm"},
        "cro_ppt":       {"max_slides": 16, "min_slides": 12, "model_tier": "fast_slm"},
    },
    "deep": {
        "executive_pdf": {"max_chapters": 7, "target_pages": "25-40", "model_tier": "reasoning_model"},
        "seo_pdf":       {"max_chapters": 12, "target_pages": "80-120", "model_tier": "fast_slm", "intro_tier": "reasoning_model"},
        "geo_pdf":       {"max_chapters": 9, "target_pages": "60-90", "model_tier": "reasoning_model"},
        "aeo_pdf":       {"max_chapters": 8, "target_pages": "80-120", "model_tier": "fast_slm", "intro_tier": "reasoning_model"},
        "cro_pdf":       {"max_chapters": 8, "target_pages": "50-80", "model_tier": "reasoning_model"},
        "executive_ppt": {"max_slides": 30, "min_slides": 20, "model_tier": "reasoning_model"},
        "seo_ppt":       {"max_slides": 36, "min_slides": 25, "model_tier": "fast_slm"},
        "geo_ppt":       {"max_slides": 30, "min_slides": 25, "model_tier": "fast_slm"},
        "aeo_ppt":       {"max_slides": 30, "min_slides": 25, "model_tier": "fast_slm"},
        "cro_ppt":       {"max_slides": 30, "min_slides": 25, "model_tier": "fast_slm"},
    },
}

_DOC_CHAPTER_BLUEPRINTS: Dict[str, List[Tuple[str, str, str]]] = {
    "executive": [
        ("ch_exec_summary", "Executive Posture & Digital Health", "ceo"),
        ("ch_exec_blockers", "Critical Growth & Visibility Blockers", "ceo"),
        ("ch_exec_ai_search", "AI Search & Generative Citation Readiness", "ceo"),
        ("ch_exec_conversion", "Conversion & Buyer Friction Priorities", "ceo"),
        ("ch_exec_roadmap", "Prioritized Execution Roadmap & Engineering Plan", "developer"),
        ("ch_exec_governance", "Evidence Governance & Measurement Boundaries", "ceo"),
        ("ch_exec_competitive", "Competitive Parity & Strategic Opportunity", "ceo"),
    ],
    "seo": [
        ("ch_seo_crawl", "Crawl Infrastructure & Indexability", "developer"),
        ("ch_seo_arch", "Site Architecture, Canonicals & Internal Links", "developer"),
        ("ch_seo_onpage", "On-Page Metadata & Semantic Headings", "marketer"),
        ("ch_seo_content", "Content Depth & Topical Authority", "marketer"),
        ("ch_seo_schema", "Structured Data & Schema.org Validation", "developer"),
        ("ch_seo_perf", "Performance, Security & Core Web Vitals", "developer"),
        ("ch_seo_remediation", "Verified SEO Remediation Blueprint", "developer"),
        ("ch_seo_roadmap", "SEO Sprint Sequencing & Retest Criteria", "marketer"),
        ("ch_seo_media", "Media Assets & Accessibility Hygiene", "marketer"),
        ("ch_seo_local_intl", "Local, International & SERP Appearance", "marketer"),
        ("ch_seo_competitive", "Organic Competitive Parity", "marketer"),
        ("ch_seo_governance", "SEO Measurement Scope & Verification", "developer"),
    ],
    "geo": [
        ("ch_geo_extractability", "On-Page GEO Extractability & Entity Clarity", "marketer"),
        ("ch_geo_citations", "Live AI Citation Visibility vs Readiness", "marketer"),
        ("ch_geo_passages", "Quotable Passage Density & Answer Structure", "marketer"),
        ("ch_geo_entity_graph", "Entity Consistency & Knowledge Graph Signals", "developer"),
        ("ch_geo_crawlers", "AI Crawler Access, llms.txt & Agent Readiness", "developer"),
        ("ch_geo_remediation", "GEO Content & Schema Remediation Plan", "developer"),
        ("ch_geo_engines", "Per-Engine Citation Readiness Breakdown", "marketer"),
        ("ch_geo_competitive", "Share-of-Model & Competitive Positioning", "marketer"),
        ("ch_geo_governance", "GEO Epistemic Boundaries & Telemetry", "marketer"),
    ],
    "aeo": [
        ("ch_aeo_questions", "Buyer Question Matrix & Coverage Clusters", "marketer"),
        ("ch_aeo_gaps", "High-Risk Evidence Gaps & Hallucination Defense", "marketer"),
        ("ch_aeo_definitions", "Direct Answer Blocks & FAQ Structure", "marketer"),
        ("ch_aeo_schema", "FAQPage, QAPage & Entity Markup", "developer"),
        ("ch_aeo_copy", "Page-by-Page Copy Upgrades for Answer Engines", "marketer"),
        ("ch_aeo_remediation", "AEO Patch Pack & Verification Plan", "developer"),
        ("ch_aeo_grounding", "Hybrid RAG Grounding & Claim Audit", "developer"),
        ("ch_aeo_governance", "Owner Confirmation & Zero-Fabrication Guardrails", "marketer"),
    ],
    "cro": [
        ("ch_cro_value_prop", "Hero Value Proposition & 5-Second Clarity", "growth"),
        ("ch_cro_cta", "Primary CTA Hierarchy & Conversion Pathways", "growth"),
        ("ch_cro_forms", "Form Ergonomics & Lead-Capture Friction", "developer"),
        ("ch_cro_trust", "Pricing Transparency & Buyer Trust Signals", "growth"),
        ("ch_cro_ux_mobile", "Visual Ergonomics, Scannability & Accessibility", "developer"),
        ("ch_cro_experiments", "Prioritized CRO Fixes & GA4 Measurement Plan", "growth"),
        ("ch_cro_journey", "Buyer Journey Friction & Dropoff Risks", "growth"),
        ("ch_cro_remediation", "Frontend UX & Copy Remediation Blueprint", "developer"),
    ],
}


class NarrativeChapter(BaseModel):
    chapter_id: str
    title: str
    audience: str = "ceo"
    executive_takeaway: str = ""
    body_md: str = ""
    why_it_matters: str = ""
    cited_finding_ids: List[str] = Field(default_factory=list)
    epistemic_labels: List[str] = Field(default_factory=list)


class NarrativeSlide(BaseModel):
    slide_id: str
    title: str
    kicker: str = ""
    bullets: List[str] = Field(default_factory=list)
    speaker_notes: str = ""
    visual_ref: Optional[str] = None
    cited_finding_ids: List[str] = Field(default_factory=list)


class NarrativeBundle(BaseModel):
    doc_type: DocType
    format: DocFormat
    audience: str
    tier: str = "standard"
    narrative_mode: NarrativeMode = "deterministic_fallback"
    executive_summary: str = ""
    chapters: List[NarrativeChapter] = Field(default_factory=list)
    slides: List[NarrativeSlide] = Field(default_factory=list)
    validation_summary: Dict[str, Any] = Field(default_factory=dict)
    critic_summary: Dict[str, Any] = Field(default_factory=dict)
    cost_usd: float = 0.0
    cost_inr_est: float = 0.0
    writer_provider: str = ""
    critic_provider: str = ""


def resolve_reporting_tier(pages_count: int, findings_count: int) -> str:
    mode = (getattr(settings, "REPORT_SIZING_MODE", "auto") or "auto").strip().lower()
    if mode in ("standard", "deep"):
        return mode
    min_pages = int(getattr(settings, "REPORT_DEEP_MIN_PAGES", 50) or 50)
    min_findings = int(getattr(settings, "REPORT_DEEP_MIN_FINDINGS", 60) or 60)
    return "deep" if (pages_count > min_pages or findings_count > min_findings) else "standard"


def compute_reporting_budget_cap_usd(audit_budget_usd: float) -> float:
    """Apply 15% budget share with a minimum USD floor so small-site Executive docs are never squeezed."""
    share = float(getattr(settings, "REPORT_BUDGET_SHARE_PCT", 0.15) or 0.15)
    floor_usd = float(getattr(settings, "REPORT_MIN_BUDGET_USD", 0.35) or 0.35)
    computed = max(floor_usd, float(audit_budget_usd or 0.0) * share)
    # Never exceed total audit budget if audit budget itself is smaller than floor
    if audit_budget_usd > 0:
        return round(min(computed, float(audit_budget_usd)), 4)
    return round(floor_usd, 4)


def _filter_findings_for_doc(doc_type: str, findings: List[Any]) -> List[Any]:
    if doc_type == "executive":
        return findings[:25]
    cat_keywords = {
        "seo": ("TECHNICAL", "ON_PAGE", "SCHEMA", "CONTENT", "SEO", "CRAWL"),
        "geo": ("GEO", "ENTITY", "CITATION"),
        "aeo": ("AI_SEARCH", "AEO", "SCHEMA", "CONTENT"),
        "cro": ("UX", "CONVERSION", "CRO", "TRUST", "FORM"),
    }
    keys = cat_keywords.get(doc_type, ())
    matched = [
        f for f in findings
        if any(k in str(getattr(getattr(f, "category", ""), "value", getattr(f, "category", ""))).upper() for k in keys)
    ]
    return (matched or findings)[:20]


def _serialize_findings_brief(findings: List[Any]) -> List[Dict[str, Any]]:
    rows = []
    for f in findings[:20]:
        rows.append({
            "finding_id": f.finding_id,
            "category": f.category.value if hasattr(f.category, "value") else str(f.category),
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "title": (getattr(f, "title", "") or getattr(f, "finding", "") or "")[:180],
            "why_it_matters": (getattr(f, "why_it_matters", "") or getattr(f, "business_impact", "") or getattr(f, "description", "") or "")[:240],
            "recommendation": (getattr(f, "recommendation", "") or "")[:220],
            "affected_urls": (getattr(f, "affected_urls", None) or [])[:3],
        })
    return rows


def _deterministic_fallback_bundle(
    *,
    doc_type: DocType,
    doc_format: DocFormat,
    audience: str,
    tier: str,
    findings: List[Any],
    scorecard_vars: Dict[str, str],
    narrative_mode: NarrativeMode = "deterministic_fallback",
) -> NarrativeBundle:
    """Honest deterministic fallback using ONLY verified findings & canonical scorecard vars."""
    brand = scorecard_vars.get("brand.name", "Website")
    overall = scorecard_vars.get("score.overall", "NOT_MEASURED")
    pillar_score = scorecard_vars.get(f"score.{doc_type}", overall)
    top_ids = [f.finding_id for f in findings[:5]]

    summary = (
        f"Deterministic fallback summary for {brand} ({doc_type.upper()}): "
        f"canonical score {pillar_score} across {scorecard_vars.get('count.pages_crawled', '0')} crawled page(s) "
        f"with {scorecard_vars.get('count.total_findings', '0')} verified finding(s). "
        f"Unmeasured analytics remain {scorecard_vars.get('label.analytics', 'UNKNOWN (Requires GA4)')}."
    )
    if doc_format == "pdf":
        chapters: List[NarrativeChapter] = []
        max_ch = int(DOCUMENT_SIZING_TABLE[tier][f"{doc_type}_pdf"]["max_chapters"])
        for idx, (ch_id, ch_title, ch_aud) in enumerate(_DOC_CHAPTER_BLUEPRINTS.get(doc_type, [])[:max_ch]):
            chunk = findings[idx : idx + 3] or findings[:2]
            cids = [f.finding_id for f in chunk]
            body = (
                " ".join(
                    f"{(f.title or f.finding or f.finding_id).strip()}."
                    for f in chunk
                )
                or f"No verified defects were recorded for {ch_title}."
            )
            chapters.append(
                NarrativeChapter(
                    chapter_id=ch_id,
                    title=ch_title,
                    audience=ch_aud,
                    executive_takeaway=f"Deterministic rollup for {ch_title}.",
                    body_md=body,
                    why_it_matters="Grounded strictly in verified audit findings without LLM prose.",
                    cited_finding_ids=cids,
                )
            )
        return NarrativeBundle(
            doc_type=doc_type,
            format="pdf",
            audience=audience,
            tier=tier,
            narrative_mode=narrative_mode,
            executive_summary=summary,
            chapters=chapters,
        )

    slides: List[NarrativeSlide] = []
    max_sl = int(DOCUMENT_SIZING_TABLE[tier][f"{doc_type}_ppt"]["max_slides"])
    for idx, f in enumerate(findings[: max(1, min(max_sl, 8))], start=1):
        title_clean = (f.title or f.finding or f.finding_id).strip()[:100]
        rec_clean = (f.recommendation or "Apply verified technical fix.").strip()
        slides.append(
            NarrativeSlide(
                slide_id=f"{doc_type}_sl_{idx:02d}",
                title=title_clean,
                kicker=f"{doc_type.upper()} // VERIFIED FINDING",
                bullets=[rec_clean[:100]],
                speaker_notes=f"Discuss verified finding {f.finding_id}: {title_clean}.",
                cited_finding_ids=[f.finding_id],
            )
        )
    if not slides:
        slides.append(
            NarrativeSlide(
                slide_id=f"{doc_type}_sl_01",
                title=f"{brand} — {doc_type.upper()} Overview",
                kicker=f"{doc_type.upper()} // OVERVIEW",
                bullets=[f"Canonical score: {pillar_score}"],
                speaker_notes=summary,
                cited_finding_ids=top_ids,
            )
        )
    return NarrativeBundle(
        doc_type=doc_type,
        format="ppt",
        audience=audience,
        tier=tier,
        narrative_mode=narrative_mode,
        executive_summary=summary,
        slides=slides,
    )


def _current_spent_usd(model_router: Any) -> float:
    td = getattr(getattr(model_router, "telemetry", None), "telemetry", None)
    return float(getattr(td, "estimated_cost_usd", 0.0) or 0.0) if td else 0.0


def _active_writer_provider(model_router: Any) -> str:
    prov = getattr(getattr(model_router, "client", None), "provider", None)
    if prov:
        return str(prov).strip().lower()
    return str(settings.get_active_provider() or "").strip().lower()


def _resolve_critic_provider(writer_provider: str) -> Optional[str]:
    override = getattr(settings, "CRITIC_PROVIDER_OVERRIDE", None)
    if not override or not str(override).strip():
        return None
    clean = str(override).strip().lower()
    if clean != writer_provider:
        return clean
    return clean


async def _run_narrative_critic(
    *,
    bundle_dict: Dict[str, Any],
    findings_brief: List[Dict[str, Any]],
    model_router: Any,
    writer_provider: str,
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    Run adversarial critic over validated narrative paragraphs/slides.
    Uses `CRITIC_PROVIDER_OVERRIDE` when set so the critic runs on a distinct provider from the writer.
    Drops any chapter/slide marked `unsupported` or `contradicted`.
    """
    critic_provider = _resolve_critic_provider(writer_provider)
    items_to_audit = []
    is_ppt = bundle_dict.get("format") == "ppt"
    if is_ppt:
        for sl in (bundle_dict.get("slides") or []):
            items_to_audit.append({
                "item_id": sl.get("slide_id"),
                "text": " ".join(sl.get("bullets") or []) + " " + (sl.get("speaker_notes") or ""),
                "cited_finding_ids": sl.get("cited_finding_ids") or [],
            })
    else:
        for ch in (bundle_dict.get("chapters") or []):
            items_to_audit.append({
                "item_id": ch.get("chapter_id"),
                "text": f"{ch.get('executive_takeaway', '')} {ch.get('body_md', '')} {ch.get('why_it_matters', '')}".strip()[:1200],
                "cited_finding_ids": ch.get("cited_finding_ids") or [],
            })

    if not items_to_audit:
        return bundle_dict, {"status": "skipped_empty", "dropped_ids": []}, critic_provider or writer_provider

    contract = (
        "You are an Independent Narrative Critic auditing report prose strictly against verified findings.\n"
        f"VERIFIED FINDINGS REGISTRY:\n{json.dumps(findings_brief, ensure_ascii=False)}\n\n"
        f"NARRATIVE ITEMS TO AUDIT:\n{json.dumps(items_to_audit, ensure_ascii=False)}\n\n"
        "For EVERY item_id, decide: `supported` | `unsupported` | `contradicted`.\n"
        "Mark `unsupported` or `contradicted` if the item makes claims not backed by its cited_finding_ids, "
        "invents outcomes/guarantees, or contradicts a verified finding."
    )
    try:
        res = await model_router.generate_structured(
            capability="critic",
            agent_role="Independent Report Narrative Critic",
            task_contract=contract,
            evidence_list=[],
            output_schema_desc='{"verdicts":[{"item_id":"string","decision":"supported|unsupported|contradicted","reason":"string"}]}',
            max_claims=len(items_to_audit),
            allow_fallback=False,
            model_tier="judge_model",
            provider_override=critic_provider,
        )
    except Exception as exc:
        logger.warning("Narrative critic failed: %s", exc)
        return bundle_dict, {"status": "unavailable", "dropped_ids": []}, critic_provider or writer_provider

    if not isinstance(res, dict) or str(res.get("status") or "").lower() in ("unavailable", "budget_exceeded"):
        return bundle_dict, {"status": "unavailable", "dropped_ids": []}, critic_provider or writer_provider

    dropped_ids: Set[str] = set()
    for v in (res.get("verdicts") or []):
        if not isinstance(v, dict):
            continue
        dec = str(v.get("decision") or "").strip().lower()
        iid = str(v.get("item_id") or "").strip()
        if iid and dec in ("unsupported", "contradicted"):
            dropped_ids.add(iid)

    updated = dict(bundle_dict)
    if dropped_ids:
        if is_ppt:
            updated["slides"] = [s for s in (updated.get("slides") or []) if s.get("slide_id") not in dropped_ids]
        else:
            updated["chapters"] = [c for c in (updated.get("chapters") or []) if c.get("chapter_id") not in dropped_ids]

    return (
        updated,
        {
            "status": "completed",
            "audited_count": len(items_to_audit),
            "dropped_count": len(dropped_ids),
            "dropped_ids": sorted(dropped_ids),
            "critic_provider": critic_provider or writer_provider,
        },
        critic_provider or writer_provider,
    )


async def narrate_document(
    *,
    doc_type: DocType,
    doc_format: DocFormat,
    audience: str,
    tier: str,
    findings: List[Any],
    scorecard_vars: Dict[str, str],
    roadmap_summary: Dict[str, Any],
    model_router: Any,
    source_pdf_bundle: Optional[NarrativeBundle] = None,
    run_critic: bool = True,
    all_verified_finding_ids: Optional[Set[str]] = None,
) -> NarrativeBundle:
    """
    Generate, validate, critic-verify, and hydrate a single PDF or PPTX NarrativeBundle.
    Never returns unhydrated `{{placeholders}}` or raw ungrounded numbers.
    """
    verified_ids = set(all_verified_finding_ids) if all_verified_finding_ids is not None else {
        f.finding_id for f in findings if getattr(f, "finding_id", None)
    }
    doc_key = f"{doc_type}_{doc_format}"
    sizing = DOCUMENT_SIZING_TABLE[tier][doc_key]
    writer_provider = _active_writer_provider(model_router)

    if not model_router or not hasattr(model_router, "generate_structured"):
        return _deterministic_fallback_bundle(
            doc_type=doc_type,
            doc_format=doc_format,
            audience=audience,
            tier=tier,
            findings=findings,
            scorecard_vars=scorecard_vars,
            narrative_mode="deterministic_fallback",
        )

    t0_spent = _current_spent_usd(model_router)
    findings_brief = _serialize_findings_brief(findings)
    placeholder_keys = sorted(scorecard_vars.keys())

    strict_rules = (
        "STRICT ZERO-FABRICATION RULES:\n"
        "1. NEVER write ANY raw digits, percentages, currency amounts, or counts in prose. "
        f"Use ONLY these exact placeholder tokens for numbers: {', '.join('{{' + k + '}}' for k in placeholder_keys)}.\n"
        "2. Every chapter/slide MUST include `cited_finding_ids` containing ONLY real finding IDs from VERIFIED FINDINGS.\n"
        "3. Preserve exact epistemic labels verbatim where applicable: `UNKNOWN (Requires GA4)`, `NOT_MEASURED`, `AI_INTERPRETATION`. "
        "NEVER convert unmeasured metrics into numbers.\n"
        "4. Write plain prose/markdown only — NEVER output HTML layout tags or chart JSON."
    )

    if doc_format == "pdf":
        max_chapters = int(sizing["max_chapters"])
        chapter_plan = _DOC_CHAPTER_BLUEPRINTS.get(doc_type, [])[:max_chapters]
        schema_desc = (
            '{"executive_summary":"string (using {{placeholders}} only, zero raw digits)",'
            '"chapters":[{"chapter_id":"string","title":"string","audience":"ceo|marketer|growth|developer",'
            '"executive_takeaway":"string","body_md":"string (2-3 crisp paragraphs using {{placeholders}} only)",'
            '"why_it_matters":"string (business impact for this audience)","cited_finding_ids":["find_001"],'
            '"epistemic_labels":["UNKNOWN (Requires GA4)"]}]}'
        )
        base_contract = (
            f"DOCUMENT: {doc_type.upper()} Audit Book PDF (Tier: {tier}, Target length: {sizing['target_pages']} pages)\n"
            f"PRIMARY AUDIENCE: {audience.upper()}\n"
            f"CHAPTER PLAN: {json.dumps([{'chapter_id': c[0], 'title': c[1], 'audience': c[2]} for c in chapter_plan])}\n\n"
            f"VERIFIED FINDINGS (Post-Critic Only):\n{json.dumps(findings_brief, ensure_ascii=False)}\n\n"
            f"ROADMAP CONTEXT:\n{json.dumps(roadmap_summary, ensure_ascii=False)[:1500]}\n\n"
            f"{strict_rules}"
        )
    else:
        max_slides = int(sizing["max_slides"])
        min_slides = int(sizing["min_slides"])
        schema_desc = (
            '{"executive_summary":"string (1-2 sentences using {{placeholders}} only)",'
            '"slides":[{"slide_id":"string","title":"string (concise action headline)","kicker":"string",'
            '"bullets":["<= 4 bullets, each <= 15 words, ZERO raw digits"],"speaker_notes":"string (presenter talking points)",'
            '"visual_ref":"string (optional chart/table key)","cited_finding_ids":["find_001"]}]}'
        )
        pdf_context = ""
        if source_pdf_bundle and source_pdf_bundle.chapters:
            pdf_digest = [
                {
                    "chapter_id": c.chapter_id,
                    "title": c.title,
                    "takeaway": c.executive_takeaway,
                    "why_it_matters": c.why_it_matters,
                    "cited_finding_ids": c.cited_finding_ids,
                }
                for c in source_pdf_bundle.chapters
            ]
            pdf_context = (
                "SOURCE PDF NARRATIVE TO CONDENSE (DO NOT PASTE — distill into boardroom slide bullets):\n"
                f"{json.dumps(pdf_digest, ensure_ascii=False)[:4500]}\n\n"
            )
        base_contract = (
            f"DOCUMENT: {doc_type.upper()} Presentation Deck PPTX (Tier: {tier}, Target: {min_slides}-{max_slides} slides, MAX {max_slides})\n"
            f"PRIMARY AUDIENCE: {audience.upper()}\n"
            f"{pdf_context}"
            f"VERIFIED FINDINGS:\n{json.dumps(findings_brief, ensure_ascii=False)[:3500]}\n\n"
            "SLIDE RULES: Maximum 4 bullets per slide, each bullet <= 15 words. Put nuance in speaker_notes.\n"
            f"{strict_rules}"
        )

    model_tier = sizing.get("model_tier", "reasoning_model")
    raw_resp: Optional[Dict[str, Any]] = None

    # Attempt 1 + single retry if raw ungrounded digits are detected outside {{placeholders}}
    for attempt in range(2):
        contract = base_contract
        if attempt == 1:
            contract += (
                "\n\nRETRY CORRECTION: Your previous draft contained raw digits/numbers outside {{placeholder}} tokens. "
                "Rewrite cleanly with ZERO raw digits — replace every number with a valid {{placeholder}} token."
            )
        try:
            res = await model_router.generate_structured(
                capability="report_narrative",
                agent_role=f"Executive {doc_type.upper()} {doc_format.upper()} Narrative Writer ({audience})",
                task_contract=contract,
                evidence_list=[],
                output_schema_desc=schema_desc,
                max_claims=int(sizing.get("max_chapters") or sizing.get("max_slides") or 12),
                allow_fallback=False,
                model_tier=model_tier,
            )
        except Exception as exc:
            logger.warning("Stage 7b narrative generation failed for %s: %s", doc_key, exc)
            res = None

        if not isinstance(res, dict) or str(res.get("status") or "").lower() in ("unavailable", "budget_exceeded"):
            return _deterministic_fallback_bundle(
                doc_type=doc_type,
                doc_format=doc_format,
                audience=audience,
                tier=tier,
                findings=findings,
                scorecard_vars=scorecard_vars,
                narrative_mode="deterministic_fallback",
            )

        raw_resp = res
        raw_digits = inspect_bundle_for_raw_digits(res)
        if not raw_digits:
            break
        logger.info("Stage 7b %s attempt %d contained raw digits %s; retrying once", doc_key, attempt + 1, raw_digits[:5])

    if not raw_resp:
        return _deterministic_fallback_bundle(
            doc_type=doc_type,
            doc_format=doc_format,
            audience=audience,
            tier=tier,
            findings=findings,
            scorecard_vars=scorecard_vars,
            narrative_mode="deterministic_fallback",
        )

    payload = {
        "doc_type": doc_type,
        "format": doc_format,
        "audience": audience,
        "tier": tier,
        "executive_summary": raw_resp.get("executive_summary") or "",
        "chapters": raw_resp.get("chapters") or [],
        "slides": raw_resp.get("slides") or [],
    }

    # Step 1: Deterministic validator (whole-sentence removal on bad digits/placeholders + finding ID check + hydration)
    max_slides_cap = int(sizing.get("max_slides", 20))
    hydrated_dict, val_rep = validate_and_hydrate_bundle(
        payload,
        verified_finding_ids=verified_ids,
        scorecard_vars=scorecard_vars,
        max_slides=max_slides_cap,
    )

    # Step 2: Narrative Critic pass AFTER deterministic validator (cross-provider when CRITIC_PROVIDER_OVERRIDE is set)
    critic_summary: Dict[str, Any] = {"status": "skipped"}
    critic_provider_used = writer_provider
    if run_critic and (hydrated_dict.get("chapters") or hydrated_dict.get("slides")):
        hydrated_dict, critic_summary, critic_provider_used = await _run_narrative_critic(
            bundle_dict=hydrated_dict,
            findings_brief=findings_brief,
            model_router=model_router,
            writer_provider=writer_provider,
        )

    # If validation/critic dropped everything, fall back cleanly & honestly
    has_content = bool(hydrated_dict.get("chapters") if doc_format == "pdf" else hydrated_dict.get("slides"))
    spent_delta = max(0.0, _current_spent_usd(model_router) - t0_spent)
    inr_rate = float(getattr(settings, "USD_TO_INR_RATE", 85.0) or 85.0)

    if not has_content:
        fb = _deterministic_fallback_bundle(
            doc_type=doc_type,
            doc_format=doc_format,
            audience=audience,
            tier=tier,
            findings=findings,
            scorecard_vars=scorecard_vars,
            narrative_mode="deterministic_fallback",
        )
        fb.validation_summary = val_rep.model_dump()
        fb.critic_summary = critic_summary
        fb.cost_usd = round(spent_delta, 6)
        fb.cost_inr_est = round(spent_delta * inr_rate, 2)
        fb.writer_provider = writer_provider
        fb.critic_provider = critic_provider_used
        return fb

    return NarrativeBundle(
        doc_type=doc_type,
        format=doc_format,
        audience=audience,
        tier=tier,
        narrative_mode="ai_full",
        executive_summary=hydrated_dict.get("executive_summary") or "",
        chapters=[NarrativeChapter.model_validate(c) for c in (hydrated_dict.get("chapters") or [])],
        slides=[NarrativeSlide.model_validate(s) for s in (hydrated_dict.get("slides") or [])],
        validation_summary=val_rep.model_dump(),
        critic_summary=critic_summary,
        cost_usd=round(spent_delta, 6),
        cost_inr_est=round(spent_delta * inr_rate, 2),
        writer_provider=writer_provider,
        critic_provider=critic_provider_used,
    )


async def narrate_all_documents(
    *,
    report: Any,
    model_router: Any,
    active_pillars: Optional[Set[str]] = None,
    audit_budget_usd: Optional[float] = None,
) -> Tuple[Dict[str, Any], str, str]:
    """
    Stage 7b Orchestrator Entrypoint:
    Narrates all 5 PDFs + 5 PPTXs (Executive, SEO, GEO, AEO, CRO) with strict priority:
      1. Executive PDF -> Executive PPT (ALWAYS first, protected by REPORT_MIN_BUDGET_USD floor)
      2. Active pillar PDFs (SEO, GEO, AEO, CRO)
      3. Companion pillar PPTXs condensed from their own validated PDF narratives
    Tracks per-document `narrative_mode` (`ai_full` | `reduced` | `deterministic_fallback`) and
    stage `"reporting"` spend.
    """
    if hasattr(model_router, "set_active_stage"):
        model_router.set_active_stage("reporting", "AI Report & Deck Narrative Synthesis")

    findings = verified_findings_for_reporting(report)
    scorecard_vars = build_scorecard_vars(report)
    pages_count = int(scorecard_vars.get("count.pages_crawled") or 0)
    tier = resolve_reporting_tier(pages_count=pages_count, findings_count=len(findings))

    roadmap_summary = {
        "roadmap_7_days": [getattr(r, "title", str(r)) for r in (getattr(report, "roadmap_7_days", None) or [])[:5]],
        "roadmap_30_days": [getattr(r, "title", str(r)) for r in (getattr(report, "roadmap_30_days", None) or [])[:5]],
        "roadmap_90_days": [getattr(r, "title", str(r)) for r in (getattr(report, "roadmap_90_days", None) or [])[:5]],
    }

    router_max_budget = float(getattr(getattr(model_router, "budget_manager", None), "max_budget_usd", 2.50) or 2.50)
    eff_audit_budget = float(audit_budget_usd if audit_budget_usd is not None else router_max_budget)
    reporting_cap_usd = compute_reporting_budget_cap_usd(eff_audit_budget)
    reporting_start_usd = _current_spent_usd(model_router)

    enabled = bool(getattr(settings, "ENABLE_AI_REPORT_NARRATIVES", True))
    pillars_ordered: List[DocType] = ["seo", "geo", "aeo", "cro"]
    if active_pillars:
        pillars_ordered = [p for p in pillars_ordered if p in active_pillars]

    bundles: Dict[str, NarrativeBundle] = {}

    def _cap_reached() -> bool:
        if not enabled:
            return True
        if not getattr(settings, "ENFORCE_HARD_BUDGET_CAP", True):
            return False
        return (_current_spent_usd(model_router) - reporting_start_usd) >= reporting_cap_usd

    all_verified_ids = {f.finding_id for f in findings if getattr(f, "finding_id", None)}

    async def _run_or_reduce(
        doc_type: DocType,
        doc_format: DocFormat,
        source_pdf: Optional[NarrativeBundle] = None,
        run_critic: bool = True,
    ) -> NarrativeBundle:
        aud = DOC_AUDIENCE_MAP[doc_type]
        doc_findings = _filter_findings_for_doc(doc_type, findings)
        if not enabled:
            return _deterministic_fallback_bundle(
                doc_type=doc_type,
                doc_format=doc_format,
                audience=aud,
                tier=tier,
                findings=doc_findings,
                scorecard_vars=scorecard_vars,
                narrative_mode="deterministic_fallback",
            )
        if _cap_reached():
            return _deterministic_fallback_bundle(
                doc_type=doc_type,
                doc_format=doc_format,
                audience=aud,
                tier=tier,
                findings=doc_findings,
                scorecard_vars=scorecard_vars,
                narrative_mode="reduced",
            )
        return await narrate_document(
            doc_type=doc_type,
            doc_format=doc_format,
            audience=aud,
            tier=tier,
            findings=doc_findings,
            scorecard_vars=scorecard_vars,
            roadmap_summary=roadmap_summary,
            model_router=model_router,
            source_pdf_bundle=source_pdf,
            run_critic=run_critic,
            all_verified_finding_ids=all_verified_ids,
        )

    # Priority 1: Executive PDF -> Executive PPT FIRST (buyer-facing priority)
    bundles["executive_pdf"] = await _run_or_reduce("executive", "pdf", run_critic=True)
    bundles["executive_ppt"] = await _run_or_reduce(
        "executive", "ppt", source_pdf=bundles["executive_pdf"], run_critic=True
    )

    # Priority 2: Pillar PDFs (parallel semaphore=2 so budget cap checks stay responsive)
    sample_low_risk = bool(getattr(settings, "REPORT_CRITIC_SAMPLE_LOW_RISK", True))
    sem = asyncio.Semaphore(2)

    async def _gen_pillar_pdf(pillar: DocType) -> Tuple[str, NarrativeBundle]:
        async with sem:
            # Always critic 100% of GEO/CRO (judgment-heavy); critic SEO/AEO unless sampling flag skips low-risk
            should_critic = (pillar in ("geo", "cro")) or (not sample_low_risk) or bool(
                any(str(getattr(getattr(f, "severity", ""), "value", "")).upper() in ("CRITICAL", "HIGH") for f in _filter_findings_for_doc(pillar, findings))
            )
            b = await _run_or_reduce(pillar, "pdf", run_critic=should_critic)
            return f"{pillar}_pdf", b

    for key, b in await asyncio.gather(*[_gen_pillar_pdf(p) for p in pillars_ordered]):
        bundles[key] = b

    # Priority 3: Pillar PPTXs condensed directly from their validated PDF narratives
    async def _gen_pillar_ppt(pillar: DocType) -> Tuple[str, NarrativeBundle]:
        async with sem:
            src_pdf = bundles.get(f"{pillar}_pdf")
            b = await _run_or_reduce(pillar, "ppt", source_pdf=src_pdf, run_critic=(pillar in ("geo", "cro")))
            return f"{pillar}_ppt", b

    for key, b in await asyncio.gather(*[_gen_pillar_ppt(p) for p in pillars_ordered]):
        bundles[key] = b

    # Assemble per-document dict + rollup summary (each document keeps its OWN narrative_mode)
    per_doc_modes = {k: b.narrative_mode for k, b in bundles.items()}
    mode_vals = set(per_doc_modes.values())
    if mode_vals == {"ai_full"}:
        overall_mode = "ai_full"
    elif "ai_full" in mode_vals:
        overall_mode = "reduced"
    else:
        overall_mode = "deterministic_fallback"

    total_rep_usd = round(max(0.0, _current_spent_usd(model_router) - reporting_start_usd), 6)
    inr_rate = float(getattr(settings, "USD_TO_INR_RATE", 85.0) or 85.0)

    serialized: Dict[str, Any] = {k: b.model_dump() for k, b in bundles.items()}
    serialized["_summary"] = {
        "tier": tier,
        "overall_narrative_mode": overall_mode,
        "reporting_budget_cap_usd": reporting_cap_usd,
        "reporting_spent_usd": total_rep_usd,
        "reporting_spent_inr_est": round(total_rep_usd * inr_rate, 2),
        "per_document_modes": per_doc_modes,
        "scorecard_snapshot": {
            "overall": scorecard_vars["score.overall"],
            "seo": scorecard_vars["score.seo"],
            "geo_readiness": scorecard_vars["score.geo_readiness"],
            "aeo": scorecard_vars["score.aeo"],
            "cro": scorecard_vars["score.cro"],
        },
    }
    return serialized, overall_mode, tier


def sync_seo_chapter_narratives_map(
    seo_pdf_bundle: Optional[Dict[str, Any]],
    existing_map: Dict[str, Dict[str, Any]],
    core_chapters: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Safely enrich `chapter_narratives` from `seo_pdf` NarrativeBundle WITHOUT losing
    any chapter ID or numeric key expected by SeoAuditBookRenderer (`CORE_CHAPTERS`).
    """
    merged = dict(existing_map or {})
    if not isinstance(seo_pdf_bundle, dict) or seo_pdf_bundle.get("narrative_mode") != "ai_full":
        return merged

    ai_chapters = seo_pdf_bundle.get("chapters") or []
    if not ai_chapters:
        return merged

    # Match AI chapters by keyword overlap against CORE_CHAPTERS while preserving every existing chapter key
    for ch_idx, ch in enumerate(core_chapters):
        ch_id = ch["id"]
        ch_num = f"{ch_idx + 3:02d}"
        ch_title_low = (ch.get("title") or "").lower()
        base = dict(merged.get(ch_id) or merged.get(ch_num) or {})
        matched = None
        for ai_ch in ai_chapters:
            ai_t = (ai_ch.get("title") or "").lower()
            ai_id = (ai_ch.get("chapter_id") or "").lower()
            if ch_id.lower() in ai_id or any(w in ai_t for w in ch_title_low.split() if len(w) >= 4):
                matched = ai_ch
                break
        if matched:
            base["executive_summary"] = matched.get("executive_takeaway") or matched.get("body_md") or base.get("executive_summary", "")
            base["why_reader_should_care"] = matched.get("why_it_matters") or base.get("why_reader_should_care", "")
            base["ai_body_md"] = matched.get("body_md") or ""
            base["cited_finding_ids"] = matched.get("cited_finding_ids") or []
            base["narrative_mode"] = "ai_full"
            merged[ch_id] = base
            merged[ch_num] = base
    return merged

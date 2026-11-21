"""
Enterprise SEO Audit Book PDF & Publishing Engine (Phases 15–18).
Consumes EXCLUSIVELY the canonical SEO audit dataset (EnterpriseSeoAssessment +
SeoScorecardReport + RemediationTask[] + ConnectorStatus[] + QaCertificationReport).
Supports:
- 7 dynamic publication profiles (Executive Brief, Complete Book, Technical, Content, Remediation, Verification, Evidence)
- 63 standardized chapters (11-part StandardChapterAnatomy per chapter) + 9 empirical Appendices (A–I)
- Clickable Table of Contents, vector SVG gauges, detailed finding cards, and landscape tables
- Dynamic chapter/tone/URL filtering that strictly preserves limitation disclosures
- Fail-closed SeoQaValidator enforcement & SHA-256 publication integrity seal
- Real PDF compilation via BrowserRenderService.render_pdf()
"""
from __future__ import annotations

import datetime
import hashlib
import html
import math
from typing import Any, Dict, List, Optional, Tuple

from app.seo.audit.qa.seo_qa_validator import QaCertificationReport, SeoQaValidator
from app.seo.reporting.canonical_seo_pdf_bridge import (
    LEGACY_REPORT_SECTION_KEYS,
    merge_evidence_preserving_all,
    merge_findings_preserving_all,
)
from app.seo.reporting.seo_chapter_registry import (
    ChapterDefinition,
    MASTER_63_CHAPTERS,
    MASTER_9_APPENDICES,
    StandardChapterAnatomy,
    get_chapters_for_profile,
)


def _esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _svg_score_gauge(score: Optional[float], size: int = 128) -> str:
    val = int(round(score)) if isinstance(score, (int, float)) else 0
    display = f"{val}" if isinstance(score, (int, float)) else "N/A"
    color = "#94a3b8" if score is None else ("#10b981" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444")
    stroke = 10
    r = (size - stroke) // 2
    circ = 2 * math.pi * r
    pct = min(100.0, max(0.0, float(score))) / 100.0 if isinstance(score, (int, float)) else 0.0
    offset = circ * (1.0 - pct)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" aria-label="SEO Health Score {display}">'
        f'<circle cx="{size // 2}" cy="{size // 2}" r="{r}" fill="none" stroke="#e2e8f0" stroke-width="{stroke}" />'
        f'<circle cx="{size // 2}" cy="{size // 2}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}" '
        f'stroke-dasharray="{circ:.2f}" stroke-dashoffset="{offset:.2f}" stroke-linecap="round" '
        f'transform="rotate(-90 {size // 2} {size // 2})" />'
        f'<text x="50%" y="46%" text-anchor="middle" dominant-baseline="middle" font-size="28" font-weight="800" fill="#0f172a">{display}</text>'
        f'<text x="50%" y="65%" text-anchor="middle" dominant-baseline="middle" font-size="10" font-weight="600" fill="#64748b">/ 100</text>'
        f"</svg>"
    )


def _svg_donut_chart(segments: List[Tuple[str, int, str]], title: str = "", size: int = 120) -> str:
    total = sum(v for _, v, _ in segments if v > 0)
    if total <= 0:
        return ""
    stroke = 18
    r = (size - stroke) // 2
    circ = 2 * math.pi * r
    arcs: List[str] = []
    angle = -90.0
    legend: List[str] = []
    for label, val, color in segments:
        if val <= 0:
            continue
        pct = val / total
        dash = pct * circ
        gap = circ - dash
        offset = -(angle + 90.0) / 360.0 * circ
        arcs.append(
            f'<circle cx="{size // 2}" cy="{size // 2}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-dasharray="{dash:.2f} {gap:.2f}" stroke-dashoffset="{offset:.2f}" />'
        )
        legend.append(
            f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:10px;font-size:7.5pt;">'
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:{color};"></span>'
            f'{_esc(label)}: <strong>{val}</strong></span>'
        )
        angle += pct * 360.0
    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" aria-label="{_esc(title)}">'
        f'<circle cx="{size // 2}" cy="{size // 2}" r="{r}" fill="none" stroke="#e2e8f0" stroke-width="{stroke}" />'
        f'{"".join(arcs)}'
        f'<text x="50%" y="48%" text-anchor="middle" dominant-baseline="middle" font-size="18" font-weight="800" fill="#0f172a">{total}</text>'
        f'<text x="50%" y="65%" text-anchor="middle" dominant-baseline="middle" font-size="8" fill="#64748b">Total</text>'
        f"</svg>"
    )
    return (
        f'<div style="display:flex;align-items:center;gap:14px;margin:6px 0;padding:8px;border:1px solid #e2e8f0;border-radius:6px;background:#f8fafc;">'
        f"{svg}<div><div style='font-size:8pt;font-weight:700;margin-bottom:4px;'>{_esc(title)}</div><div>{''.join(legend)}</div></div></div>"
    )


def _svg_bar_chart(rows: List[Tuple[str, float]], title: str, unit: str = "") -> str:
    clean = [(lbl, float(v)) for lbl, v in rows if v is not None and v >= 0][:10]
    if not clean:
        return ""
    peak = max(v for _, v in clean) or 1.0
    bar_rows = []
    for idx, (lbl, val) in enumerate(clean):
        y = 8 + idx * 22
        w = max(2.0, (val / peak) * 320.0)
        bar_rows.append(
            f'<text x="0" y="{y + 12}" font-size="8.5" fill="#334155">{_esc(lbl[:30])}</text>'
            f'<rect x="175" y="{y + 2}" width="{w:.1f}" height="12" rx="2" fill="#0284c7" />'
            f'<text x="{182 + w:.1f}" y="{y + 12}" font-size="8.5" font-weight="700" fill="#0f172a">{val:.0f}{_esc(unit)}</text>'
        )
    height = 16 + len(clean) * 22
    return (
        f'<div style="margin:6px 0;padding:8px;border:1px solid #e2e8f0;border-radius:6px;background:#f8fafc;">'
        f'<div style="font-size:8pt;font-weight:700;margin-bottom:4px;">{_esc(title)}</div>'
        f'<svg viewBox="0 0 560 {height}" width="100%" height="auto" role="img" aria-label="{_esc(title)}">{"".join(bar_rows)}</svg></div>'
    )


def _map_finding_to_chapter_numbers(f: Dict[str, Any]) -> List[int]:
    blob = (
        f"{f.get('rule_id', '')} {f.get('category', '')} {f.get('subcategory', '')} "
        f"{f.get('finding_title', '')} {f.get('title', '')}"
    ).lower()
    if any(k in blob for k in ("sitemap", "robots")):
        return [13, 14]
    if any(k in blob for k in ("noindex", "indexab")):
        return [14]
    if "canonical" in blob:
        return [15]
    if any(k in blob for k in ("http", "status", "redirect", "404", "5xx")):
        return [16]
    if any(k in blob for k in ("https", "tls", "ssl", "hsts", "security", "csp", "header")):
        return [18, 46]
    if any(k in blob for k in ("render", "hydrat", "javascript")):
        return [19]
    if any(k in blob for k in ("mobile", "viewport", "tap target", "responsive")):
        return [20]
    if any(k in blob for k in ("cwv", "lcp", "cls", "inp", "ttfb", "speed", "perf", "core_web_vitals")):
        return [21, 22]
    if any(k in blob for k in ("image", "alt", "media", "webp", "avif")):
        return [23]
    if any(k in blob for k in ("accessib", "wcag", "aria", "contrast")):
        return [24]
    if any(k in blob for k in ("schema", "json-ld", "json_ld", "rich", "structured")):
        return [25, 26]
    if any(k in blob for k in ("geo", "aeo", "ai_search", "answer engine", "citation", "extractab")):
        return [26, 51]
    if any(k in blob for k in ("title", "meta")):
        return [27]
    if any(k in blob for k in ("h1", "h2", "heading")):
        return [28]
    if any(k in blob for k in ("thin", "word_count", "content", "copywriting")):
        return [29, 38]
    if "intent" in blob:
        return [30]
    if any(k in blob for k in ("topical", "cluster", "semantic")):
        return [31, 32]
    if any(k in blob for k in ("link", "orphan", "depth", "anchor", "pagerank")):
        return [33]
    if "url" in blob or "query" in blob or "slug" in blob:
        return [34]
    if any(k in blob for k in ("cannibal", "duplicate")):
        return [35]
    if any(k in blob for k in ("freshness", "decay")):
        return [36]
    if any(k in blob for k in ("competit", "parity", "benchmark")):
        return [37, 51]
    if any(k in blob for k in ("local", "nap", "gbp")):
        return [39, 40]
    if "hreflang" in blob or "international" in blob:
        return [41, 42]
    if any(k in blob for k in ("ecommerce", "e-commerce", "product", "facet", "sku")):
        return [43, 44]
    if any(k in blob for k in ("backlink", "referring domain", "authority")):
        return [45]
    if any(k in blob for k in ("trust", "eeat", "e-e-a-t", "author", "brand")):
        return [46, 47]
    if any(k in blob for k in ("gsc", "search console", "ga4", "analytics")):
        return [48, 49]
    if any(k in blob for k in ("cro", "ux_conversion", "conversion", "cta", "form", "checkout")):
        return [52]
    return [18]


def _chapter_dimension_id(ch_num: int) -> str:
    if ch_num in (10, 11, 12, 16, 17, 18, 19):
        return "technical_crawlability"
    if ch_num in (13, 14, 15):
        return "indexation_canonicalization"
    if ch_num in (20, 21, 22, 24):
        return "performance_mobile"
    if ch_num in (23, 27, 28, 34):
        return "on_page_seo"
    if ch_num in (25, 26):
        return "structured_data_entities"
    if ch_num in (29, 30, 31, 32, 35, 36, 37, 38):
        return "content_quality_intent"
    if ch_num == 33:
        return "internal_linking_architecture"
    if ch_num in (39, 40, 41, 42, 43, 44):
        return "specialist_applicability"
    return "trust_authority_signals"


class EnterprisePdfEngine:
    """
    Single-source-of-truth HTML/PDF publisher for all 7 SEO publication profiles.
    """

    SUPPORTED_PROFILES = {
        "executive": "Executive SEO Brief",
        "complete_book": "Complete SEO Audit Book (Enterprise Edition)",
        "technical": "Technical SEO & Architecture Report",
        "content": "Content Strategy & Keyword Intelligence Report",
        "remediation": "SEO Remediation & Developer Directives Plan",
        "verification": "Independent SEO Verification & QA Report",
        "evidence": "SEO Evidence Register & Audit Appendix",
    }

    def _extract_canonical(self, assessment: Any, report_data: Dict[str, Any]) -> Dict[str, Any]:
        cov = _get(assessment, "coverage") or report_data.get("coverage") or {}
        manifest = report_data.get("crawl_manifest") or {}
        pages = list(_get(manifest, "pages") or report_data.get("page_reports") or [])
        pages = [p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in pages if p is not None]

        from app.report_finding_registry import canonicalize_report_findings

        assess_findings = list(
            _get(assessment, "canonical_findings")
            or _get(assessment, "findings")
            or []
        )
        rep_findings = list(
            canonicalize_report_findings(report_data)
            or report_data.get("findings")
            or []
        )
        findings = merge_findings_preserving_all(assess_findings, rep_findings)

        assess_ev = list(
            _get(assessment, "canonical_evidence")
            or _get(assessment, "evidence")
            or []
        )
        rep_ev = list(report_data.get("evidence") or [])
        evidence = merge_evidence_preserving_all(assess_ev, rep_ev, findings)

        scorecard = (
            _get(assessment, "mathematical_scorecard")
            or report_data.get("mathematical_scorecard")
            or {}
        )
        if hasattr(scorecard, "model_dump"):
            scorecard = scorecard.model_dump()

        tasks = (
            _get(assessment, "remediation_tasks")
            or report_data.get("remediation_tasks")
            or []
        )
        tasks = [t.model_dump() if hasattr(t, "model_dump") else dict(t) for t in tasks]

        verification_runs = list(
            _get(assessment, "verification_runs")
            or report_data.get("verification_runs")
            or []
        )
        verification_runs = [v.model_dump() if hasattr(v, "model_dump") else dict(v) for v in verification_runs]

        connectors = (
            _get(assessment, "connectors")
            or report_data.get("connectors")
            or []
        )
        connectors = [c.model_dump() if hasattr(c, "model_dump") else dict(c) for c in connectors]

        agent_execs = (
            _get(assessment, "agent_executions")
            or _get(assessment, "agents")
            or report_data.get("agent_executions")
            or []
        )
        agent_execs = [a.model_dump() if hasattr(a, "model_dump") else dict(a) for a in agent_execs]

        link_graph = (
            _get(assessment, "internal_link_graph")
            or report_data.get("internal_link_graph")
            or None
        )

        # Preserve ALL rich legacy ExecutiveReport sections intact for chapter telemetry rendering
        legacy_sections: Dict[str, Any] = dict(report_data.get("legacy_sections") or {})
        for key in LEGACY_REPORT_SECTION_KEYS:
            val = report_data.get(key)
            if val not in (None, "", [], {}) and key not in legacy_sections:
                legacy_sections[key] = val.model_dump() if hasattr(val, "model_dump") else val

        crawled = _get(cov, "urls_crawled")
        if crawled is None:
            crawled = len(pages)
        discovered = _get(cov, "urls_discovered")
        if discovered is None:
            discovered = max(int(_get(manifest, "total_pages_discovered") or 0), int(crawled))
        rendered = _get(cov, "urls_rendered")
        if rendered is None:
            rendered = crawled
        inspected = _get(cov, "urls_deeply_inspected")
        if inspected is None:
            inspected = crawled
        defects_urls = _get(cov, "urls_with_verified_findings")
        if defects_urls is None:
            defects_urls = len({u for f in findings for u in (f.get("affected_urls") or []) if u})
        sampling_status = str(_get(cov, "sampling_status") or _get(manifest, "sampling_status") or "SAMPLED_AUDIT")

        return {
            "domain": str(report_data.get("domain") or _get(assessment, "domain") or "unknown"),
            "audit_id": str(report_data.get("analysis_id") or report_data.get("report_id") or _get(assessment, "audit_run_id") or "UNSCOPED"),
            "pages": pages,
            "findings": findings,
            "evidence": evidence,
            "scorecard": scorecard,
            "tasks": tasks,
            "verification_runs": verification_runs,
            "link_graph": link_graph,
            "connectors": connectors,
            "agents": agent_execs,
            "legacy": legacy_sections,
            "coverage": {
                "urls_discovered": int(discovered),
                "urls_crawled": int(crawled),
                "urls_rendered": int(rendered),
                "urls_deeply_inspected": int(inspected),
                "urls_with_verified_findings": int(defects_urls),
                "sampling_status": sampling_status,
                "urls_tested_by_specialist": _get(cov, "urls_tested_by_specialist") or {},
            },
            "limitations": list(_get(assessment, "limitations") or report_data.get("limitations") or []),
            "qa": _get(assessment, "qa_certification") or report_data.get("qa_certification"),
        }

    def _build_chapter_anatomy(
        self,
        ch: ChapterDefinition,
        ctx: Dict[str, Any],
        tone: str = "executive",
    ) -> StandardChapterAnatomy:
        conn_map = {str(c.get("provider_id") or c.get("connector_type")): c for c in ctx["connectors"]}
        scorecard = ctx["scorecard"] or {}
        dims_by_id = {d.get("dimension_id"): d for d in (scorecard.get("dimensions") or [])}
        dim_id = _chapter_dimension_id(ch.number)
        dim_data = dims_by_id.get(dim_id) or {}

        # Connector availability gate
        req_conn = ch.required_connector
        conn_obj = conn_map.get(req_conn) if req_conn else None
        conn_connected = bool(conn_obj and str(conn_obj.get("status", "")).upper() == "CONNECTED")

        ch_findings = [f for f in ctx["findings"] if ch.number in _map_finding_to_chapter_numbers(f)]
        if ch.number == 54:
            ch_findings = list(ctx["findings"])
        elif ch.number == 56:
            ch_findings = [f for f in ctx["findings"] if str(f.get("severity", "")).upper() in ("CRITICAL", "HIGH")]

        tasks_by_finding = {t.get("finding_id"): t for t in ctx["tasks"]}
        cov = ctx["coverage"]
        crawled = cov["urls_crawled"]
        discovered = cov["urls_discovered"]

        if req_conn and not conn_connected:
            health = {
                "status": "DATA_UNAVAILABLE",
                "score": None,
                "coverage_pct": 0.0,
                "confidence": "Unavailable",
                "connector_status": f"{req_conn}: NOT_CONFIGURED",
            }
            tested = f"Checked connector availability for {req_conn}. Connector is not configured; zero synthetic data was invented."
            observed = f"External source '{req_conn}' is disconnected. No live metrics were fabricated for {ctx['domain']}."
            root_cause = "External API or OAuth integration has not yet been authorized for this workspace."
            implications = "Without live first-party or provider telemetry, performance/authority claims cannot be verified."
            rec_impl = f"Authorize {req_conn} in Dristik Connectors & Data and re-run the audit."
            owner_effort = "Owner: SEO Lead / Workspace Admin · Effort: 10 minutes"
            validation = f"Confirm GET /api/v1/seo/connectors/{req_conn} returns status='CONNECTED' and non-null last_sync_timestamp."
            limitations = f"Entire chapter is unmeasured until {req_conn} is connected. Excluded from scoring denominator without penalty."
        else:
            dim_score = dim_data.get("score")
            is_measured = bool(dim_data.get("is_measured")) if dim_data else (crawled > 0)
            is_applicable = bool(dim_data.get("is_applicable", True)) if dim_data else True
            if ch.is_conditional and not is_applicable and not ch_findings:
                status_label = "NOT_APPLICABLE"
            elif not is_measured and not ch_findings and crawled == 0:
                status_label = "NOT TESTED"
            elif ch_findings:
                status_label = "ISSUE_VERIFIED"
            else:
                status_label = "NO_ISSUE_IN_SAMPLE"

            health = {
                "status": status_label,
                "score": dim_score,
                "coverage_pct": scorecard.get("confidence_vectors", {}).get("audit_coverage_pct", round((crawled / max(discovered, 1)) * 100, 1)),
                "confidence": f"{scorecard.get('confidence_vectors', {}).get('evidence_confidence_pct', 100.0)}% verified",
                "connector_status": f"{req_conn}: CONNECTED" if req_conn else "First-party crawl & DOM",
            }
            tested = (
                f"Evaluated {crawled} crawled/rendered URL(s) out of {discovered} discovered URL(s) "
                f"(sampling_status={cov['sampling_status']}) using deterministic analyzers for {ch.title}."
            )
            if ch_findings:
                obs_bits = [f"{f.get('finding_id')}: {f.get('title')} ({f.get('severity')}, {len(f.get('affected_urls') or [])} URL(s))" for f in ch_findings[:6]]
                observed = "; ".join(obs_bits)
            else:
                observed = (
                    f"No confirmed defects were raised for {ch.title} within the {crawled} inspected URL(s)."
                    if status_label != "NOT_APPLICABLE"
                    else f"{ch.title} signals were not present on the inspected pages; marked NOT_APPLICABLE without penalty."
                )

            rc_ids = sorted({str(f.get("root_cause_id")) for f in ch_findings if f.get("root_cause_id")})
            root_cause = (
                f"Grouped under {len(rc_ids)} systemic root-cause cluster(s): {', '.join(rc_ids)}."
                if rc_ids
                else "No systemic template defect observed in the evaluated sample."
            )
            implications = (
                f"Confirmed findings ({len(ch_findings)}) directly affect {ch.description.lower()} Potential site-wide impact beyond the {crawled}-URL sample requires expanded crawl verification."
                if ch_findings
                else f"Maintaining clean signals in {ch.title} preserves crawl efficiency and indexing stability."
            )
            if ch_findings:
                first_task = tasks_by_finding.get(ch_findings[0].get("finding_id"))
                if first_task:
                    impl = first_task.get("implementation") or {}
                    rec_impl = (
                        f"[{impl.get('platform', 'GENERIC_HTML')} · {impl.get('stack_confidence', 'GENERIC_FALLBACK')}] "
                        f"{first_task.get('recommended_fix')} | Target: {impl.get('target_file_pattern')}\n"
                        f"{impl.get('code_diff_snippet', '')}"
                    )
                    owner_effort = f"Owner: {first_task.get('owner', 'Engineering')} ({first_task.get('department', 'Engineering')}) · Effort: {first_task.get('effort', 'TBD')}"
                    validation = f"Acceptance: {first_task.get('acceptance_criteria')} | Protocol: {first_task.get('verification_protocol')}"
                else:
                    rec_impl = "; ".join(str(f.get("recommendation") or "") for f in ch_findings[:3] if f.get("recommendation")) or "Resolve listed findings at template layer."
                    owner_effort = "Owner: Engineering / SEO Lead · Effort: Based on affected template scope"
                    validation = "Re-crawl affected URLs via POST /api/v1/seo/tasks/{task_id}/verify and assert 0 regressions."
            else:
                rec_impl = "No corrective patch required from current sample; include in continuous regression monitoring."
                owner_effort = "Owner: SEO Governance · Effort: Ongoing monitoring"
                validation = "Retain automated check in scheduled continuous audit runs."

            uninspected = max(0, discovered - crawled)
            limitations = (
                f"{uninspected} discovered URL(s) were outside the {crawled}-URL crawl sample."
                if uninspected > 0
                else "All discovered URLs within configured crawl scope were inspected; external unconfigured connectors remain disclosed."
            )

        exec_interp = (
            f"For {ctx['domain']}, {ch.title} evaluates {ch.description.lower()} "
            + (
                "Executive focus: prioritize verified blockers by commercial scope and effort."
                if tone == "executive"
                else "Engineering focus: apply deterministic template fixes and pass automated re-crawl acceptance tests."
            )
        )

        return StandardChapterAnatomy(
            executive_interpretation=exec_interp,
            health_overview=health,
            what_was_tested=tested,
            what_was_observed=observed,
            findings=ch_findings,
            root_cause_analysis=root_cause,
            business_seo_implications=implications,
            recommended_implementation=rec_impl,
            ownership_and_effort=owner_effort,
            validation_protocol=validation,
            remaining_limitations=limitations,
        )

    def _render_finding_card_html(self, f: Dict[str, Any], task: Optional[Dict[str, Any]]) -> str:
        sev = str(f.get("severity") or "MEDIUM").upper()
        badge_cls = "badge-critical" if sev == "CRITICAL" else "badge-high" if sev == "HIGH" else "badge-neutral"
        title = f.get("finding_title") or f.get("title") or "SEO Finding"
        cat = f.get("subcategory") or f.get("category") or "SEO"
        urls = f.get("affected_urls") or []
        templates = f.get("affected_templates") or []
        ev_ids = list(
            dict.fromkeys(
                str(x)
                for x in (
                    list(f.get("evidence_ids") or [])
                    + list(f.get("evidence_refs") or [])
                    + list(f.get("evidence_references") or [])
                )
                if x
            )
        )
        diagnosis = f.get("detailed_diagnosis") or f.get("concise_summary") or f.get("description") or f.get("observed_condition") or "Verified defect"
        plain_eng = f.get("plain_english_summary") or ""
        expected = f.get("expected_or_reference_behavior") or f.get("expected_condition") or ""
        why_impact = f.get("business_context") or f.get("why_it_matters") or f.get("business_impact") or ""
        root_cause = f.get("root_cause") or f.get("root_cause_id") or (task.get("root_cause") if task else None) or "Isolated defect"
        rec = f.get("recommended_solution") or f.get("recommendation") or (task.get("recommended_fix") if task else "Apply template correction")
        dev_inst = f.get("developer_instructions") or ""
        acceptance = f.get("acceptance_criteria") or f.get("validation_criteria") or (task.get("acceptance_criteria") if task else "")
        verif_proto = f.get("verification_method") or (task.get("verification_protocol") if task else "")
        verif_steps = f.get("verification_steps") or []
        verif_cmd = f.get("verification_command") or ""
        owner = f.get("responsible_role") or f.get("owner") or (task.get("owner") if task else "")
        effort = f.get("estimated_effort") or f.get("effort") or (task.get("effort") if task else "")
        data_limits = f.get("limitations") or f.get("data_limitations") or ""
        if isinstance(data_limits, list):
            data_limits = "; ".join(str(x) for x in data_limits if x)
        impl_snippet = ""
        stack_note = ""
        if task and isinstance(task.get("implementation"), dict):
            impl_snippet = str(task["implementation"].get("code_diff_snippet") or "")
            stack_note = f"{task['implementation'].get('platform', 'GENERIC_HTML')} ({task['implementation'].get('stack_confidence', 'GENERIC_FALLBACK')}) · {task['implementation'].get('target_file_pattern', 'Template')}"
        if not impl_snippet and f.get("relevant_code_or_configuration_example"):
            impl_snippet = str(f["relevant_code_or_configuration_example"])
        if not impl_snippet and isinstance(f.get("code_patch"), dict):
            impl_snippet = str(f["code_patch"].get("diff") or f["code_patch"].get("after_snippet") or "")

        extra_bits: List[str] = []
        if plain_eng:
            extra_bits.append(f"<p><strong>Plain English:</strong> {_esc(plain_eng)}</p>")
        if expected:
            extra_bits.append(f"<p><strong>Expected Standard:</strong> {_esc(expected)}</p>")
        if why_impact:
            extra_bits.append(f"<p><strong>Business &amp; SEO Impact:</strong> {_esc(why_impact)}</p>")
        if dev_inst:
            extra_bits.append(f"<p><strong>Developer Instructions:</strong> {_esc(dev_inst)}</p>")
        if templates:
            extra_bits.append(f"<p><strong>Affected Templates:</strong> {_esc(', '.join(str(t) for t in templates))}</p>")
        if acceptance or verif_proto:
            acc_str = "; ".join(str(x) for x in acceptance) if isinstance(acceptance, list) else str(acceptance)
            extra_bits.append(
                f"<p><strong>Acceptance &amp; Verification:</strong> {_esc(acc_str)}"
                f"{f' · Protocol: {_esc(verif_proto)}' if verif_proto else ''}</p>"
            )
        if verif_steps:
            extra_bits.append(f"<p><strong>Verification Steps:</strong> {_esc(' | '.join(str(s) for s in verif_steps))}</p>")
        if verif_cmd:
            extra_bits.append(f"<p><strong>Verification Command:</strong> <code>{_esc(verif_cmd)}</code></p>")
        if owner or effort or stack_note:
            extra_bits.append(
                f"<p><strong>Ownership &amp; Target:</strong> {_esc(owner or 'Engineering')}"
                f"{f' · Effort: {_esc(effort)}' if effort else ''}"
                f"{f' · Stack: <code>{_esc(stack_note)}</code>' if stack_note else ''}</p>"
            )
        if data_limits:
            extra_bits.append(f"<p><strong>Limitations:</strong> {_esc(data_limits)}</p>")

        return f"""
        <div class="finding-card">
          <div class="finding-card-head">
            <span><strong>{_esc(f.get('finding_id'))}</strong> · {_esc(title)} <span style="color:#64748b;font-size:7.5pt;">({_esc(cat)})</span></span>
            <span class="badge {badge_cls}">{_esc(sev)}</span>
          </div>
          <p><strong>Diagnosis / Observed:</strong> {_esc(diagnosis)}</p>
          <p><strong>Affected Scope:</strong> {len(urls)} URL(s) confirmed ({_esc(', '.join(str(u) for u in urls)) if urls else 'Site-wide'})</p>
          <p><strong>Root Cause:</strong> {_esc(root_cause)} · <strong>Recommended Fix:</strong> {_esc(rec)}</p>
          {''.join(extra_bits)}
          {f'<pre class="code-snippet">{_esc(impl_snippet)}</pre>' if impl_snippet else ''}
          <p class="meta-line">Evidence: {_esc(', '.join(ev_ids) or 'None')} · Status: {_esc(f.get('status') or f.get('verification_status') or 'VERIFIED')} · Fix Verification: {_esc(task.get('verification_status') if task else (f.get('verification_status') or 'UNVERIFIED'))}</p>
        </div>
        """

    def _render_chapter_telemetry_html(self, ch: ChapterDefinition, ctx: Dict[str, Any]) -> str:
        """
        Renders rich legacy ExecutiveReport sections, SVG charts, internal link graph metrics,
        copywriting rewrites, SERP snippets, developer patches, 7/30/60/90 roadmaps, and live
        verification before/after tables right inside the matching chapter.
        """
        leg = ctx.get("legacy") or {}
        blocks: List[str] = []

        def _kv_table(title: str, data: Any) -> str:
            if not isinstance(data, dict) or not data:
                return ""
            rows = []
            for k, v in list(data.items())[:18]:
                if v in (None, "", [], {}):
                    continue
                if isinstance(v, (dict, list)):
                    val_s = f"{len(v)} item(s)" if isinstance(v, list) else f"{len(v)} field(s)"
                else:
                    val_s = str(v)
                rows.append(f"<tr><td><strong>{_esc(k.replace('_', ' ').title())}</strong></td><td>{_esc(val_s[:240])}</td></tr>")
            if not rows:
                return ""
            return f'<h4>{_esc(title)}</h4><table class="data-table"><thead><tr><th>Signal</th><th>Observed Value</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'

        if ch.number == 4:
            # Executive Briefing: narrative + severity donut
            story = leg.get("story_summary")
            opp = leg.get("primary_strategic_opportunity")
            rights = leg.get("what_site_gets_right")
            backs = leg.get("what_is_holding_it_back")
            if story:
                blocks.append(f"<p><strong>Executive Narrative:</strong> {_esc(story)}</p>")
            if opp:
                blocks.append(f"<p><strong>Primary Strategic Opportunity:</strong> {_esc(opp)}</p>")
            if isinstance(rights, list) and rights:
                blocks.append("<p><strong>Verified Strengths:</strong></p><ul>" + "".join(f"<li>{_esc(x)}</li>" for x in rights[:6]) + "</ul>")
            elif isinstance(rights, str) and rights:
                blocks.append(f"<p><strong>Verified Strengths:</strong> {_esc(rights)}</p>")
            if isinstance(backs, list) and backs:
                blocks.append("<p><strong>Primary Constraints:</strong></p><ul>" + "".join(f"<li>{_esc(x)}</li>" for x in backs[:6]) + "</ul>")
            elif isinstance(backs, str) and backs:
                blocks.append(f"<p><strong>Primary Constraints:</strong> {_esc(backs)}</p>")
            sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for f in ctx["findings"]:
                s = str(f.get("severity") or "MEDIUM").upper()
                sev_counts[s] = sev_counts.get(s, 0) + 1
            donut = _svg_donut_chart(
                [("Critical", sev_counts["CRITICAL"], "#dc2626"), ("High", sev_counts["HIGH"], "#d97706"), ("Medium", sev_counts["MEDIUM"], "#0284c7"), ("Low", sev_counts["LOW"], "#16a34a")],
                title="Canonical Finding Severity Mix",
            )
            if donut:
                blocks.append(donut)

        elif ch.number == 6 and leg.get("business_profile"):
            blocks.append(_kv_table("Website & Business Context Profile", leg["business_profile"]))

        elif ch.number in (11, 16):
            http_b = leg.get("http_status_breakdown")
            if isinstance(http_b, dict):
                donut = _svg_donut_chart(
                    [
                        ("2xx OK", int(http_b.get("count_2xx") or 0), "#16a34a"),
                        ("3xx Redirect", int(http_b.get("count_3xx") or 0), "#0284c7"),
                        ("4xx Client Error", int(http_b.get("count_4xx") or 0), "#d97706"),
                        ("5xx Server Error", int(http_b.get("count_5xx") or 0), "#dc2626"),
                    ],
                    title="Observed HTTP Response Status Breakdown",
                )
                if donut:
                    blocks.append(donut)
                blocks.append(_kv_table("HTTP Status Telemetry", http_b))
            if ch.number == 16 and leg.get("host_and_redirects"):
                blocks.append(_kv_table("Host & Redirect Chain Audit", leg["host_and_redirects"]))

        elif ch.number in (13, 14) and leg.get("indexation_intelligence"):
            blocks.append(_kv_table("Indexation & Robots Telemetry", leg["indexation_intelligence"]))

        elif ch.number == 15 and leg.get("canonical_audit"):
            blocks.append(_kv_table("Canonicalization Telemetry", leg["canonical_audit"]))

        elif ch.number == 18 and leg.get("security_audit"):
            blocks.append(_kv_table("Security & Protocol Audit", leg["security_audit"]))

        elif ch.number == 20 and leg.get("visual_ux"):
            blocks.append(_kv_table("Mobile & Visual UX Telemetry", leg["visual_ux"]))

        elif ch.number in (21, 22):
            ttfb_rows = [
                (str(p.get("url") or "").replace("https://", "").replace("http://", ""), float(p["ttfb_ms"]))
                for p in ctx["pages"]
                if isinstance(p.get("ttfb_ms"), (int, float)) and p["ttfb_ms"] > 0
            ]
            if ttfb_rows:
                blocks.append(_svg_bar_chart(ttfb_rows, "Measured Crawl TTFB by URL (Lab Response Time, Not Field CWV)", "ms"))

        elif ch.number == 23 and leg.get("media_assets"):
            blocks.append(_kv_table("Image & Media Optimization Telemetry", leg["media_assets"]))

        elif ch.number == 25 and leg.get("schema_validation"):
            blocks.append(_kv_table("Structured Data & Schema.org Validation", leg["schema_validation"]))

        elif ch.number == 26:
            if leg.get("geo_readiness"):
                blocks.append(_kv_table("AI & Entity Readiness (GEO)", leg["geo_readiness"]))
            if leg.get("ai_visibility_scorecard"):
                blocks.append(_kv_table("AI Visibility Scorecard", leg["ai_visibility_scorecard"]))

        elif ch.number == 27 and leg.get("meta_rollup"):
            blocks.append(_kv_table("Title & Meta Description Rollup", leg["meta_rollup"]))

        elif ch.number == 28 and leg.get("heading_hierarchy"):
            blocks.append(_kv_table("Heading Hierarchy (H1–H6) Telemetry", leg["heading_hierarchy"]))

        elif ch.number == 29:
            wc_rows = [
                (str(p.get("url") or "").replace("https://", "").replace("http://", ""), float(p["word_count"]))
                for p in ctx["pages"]
                if isinstance(p.get("word_count"), (int, float))
            ]
            if wc_rows:
                blocks.append(_svg_bar_chart(wc_rows, "Observed Word Count by Crawled URL", " words"))

        elif ch.number == 30 and leg.get("commercial_evaluations"):
            ce_rows = "".join(
                f"<tr><td>{_esc(_get(c, 'url') or _get(c, 'page_url') or 'Page')}</td><td>{_esc(_get(c, 'intent') or _get(c, 'primary_intent') or '—')}</td><td>{_esc(_get(c, 'summary') or _get(c, 'notes') or '')}</td></tr>"
                for c in (leg["commercial_evaluations"] or [])[:12]
            )
            if ce_rows:
                blocks.append(f'<h4>Commercial &amp; Search Intent Evaluations</h4><table class="data-table"><thead><tr><th>Page</th><th>Intent</th><th>Assessment</th></tr></thead><tbody>{ce_rows}</tbody></table>')

        elif ch.number == 32 and leg.get("topical_authority"):
            blocks.append(_kv_table("Topical Authority & Cluster Telemetry", leg["topical_authority"]))

        elif ch.number == 33:
            lg = ctx.get("link_graph")
            if isinstance(lg, dict) and (lg.get("nodes") or lg.get("total_nodes")):
                nodes = lg.get("nodes") or []
                hub_rows = "".join(
                    f"<tr><td>{_esc(n.get('url'))}</td><td>{_esc(n.get('page_type') or 'page')}</td><td>{round(float(n.get('pagerank') or 0), 4)}</td><td>{int(n.get('inlinks') or 0)}</td><td>{int(n.get('outlinks') or 0)}</td><td>{_esc(n.get('depth') if n.get('depth') is not None else '—')}</td></tr>"
                    for n in sorted(nodes, key=lambda x: float(x.get("pagerank") or 0), reverse=True)[:12]
                )
                blocks.append(
                    f"<h4>Internal Link Graph &amp; PageRank Hubs</h4>"
                    f"<p>Nodes: <strong>{int(lg.get('total_nodes') or len(nodes))}</strong> · Edges: <strong>{int(lg.get('total_edges') or lg.get('edges_count') or 0)}</strong> · Orphans: <strong>{len(lg.get('orphan_pages') or [])}</strong> · Deep (&gt;3 clicks): <strong>{len(lg.get('deep_pages') or [])}</strong></p>"
                    + (f'<table class="data-table"><thead><tr><th>URL</th><th>Type</th><th>PageRank</th><th>Inlinks</th><th>Outlinks</th><th>Depth</th></tr></thead><tbody>{hub_rows}</tbody></table>' if hub_rows else "")
                )
            for k, lbl in (("click_depth", "Click Depth Audit"), ("orphan_pages", "Orphan Pages Audit"), ("anchor_text_audit", "Anchor Text Audit")):
                if leg.get(k):
                    blocks.append(_kv_table(lbl, leg[k]))

        elif ch.number == 38:
            pr_list = leg.get("page_reports") or []
            copy_cards = []
            for pr in pr_list[:10]:
                cw = _get(pr, "copywriting") or {}
                sug = _get(cw, "suggested") or {}
                if isinstance(sug, dict) and any(sug.get(k) for k in ("title", "meta_description", "h1", "hero")):
                    st = sug.get("title")
                    sm = sug.get("meta_description")
                    sh = sug.get("h1")
                    parts = [f"<div class='finding-card'><p><strong>URL:</strong> {_esc(_get(pr, 'url'))}</p>"]
                    if st:
                        parts.append(f"<p><strong>Suggested Title:</strong> {_esc(st)}</p>")
                    if sm:
                        parts.append(f"<p><strong>Suggested Meta:</strong> {_esc(sm)}</p>")
                    if sh:
                        parts.append(f"<p><strong>Suggested H1:</strong> {_esc(sh)}</p>")
                    parts.append("</div>")
                    copy_cards.append("".join(parts))
            if copy_cards:
                blocks.append("<h4>Specialist Editorial Rewrites &amp; Content Briefs</h4>" + "".join(copy_cards))

        elif ch.number == 39 and leg.get("local_seo"):
            blocks.append(_kv_table("Local SEO & NAP Telemetry", leg["local_seo"]))

        elif ch.number in (41, 42) and leg.get("international_seo"):
            blocks.append(_kv_table("International SEO & Hreflang Telemetry", leg["international_seo"]))

        elif ch.number in (43, 44) and leg.get("ecommerce_seo"):
            blocks.append(_kv_table("E-Commerce SEO Telemetry", leg["ecommerce_seo"]))

        elif ch.number == 45 and leg.get("external_authority"):
            blocks.append(_kv_table("External Authority & Backlink Telemetry", leg["external_authority"]))

        elif ch.number in (48, 49) and leg.get("google_performance"):
            gp = leg["google_performance"]
            sub_key = "search_console" if ch.number == 48 else "analytics"
            if isinstance(gp, dict) and gp.get(sub_key):
                blocks.append(_kv_table(f"Google {sub_key.replace('_', ' ').title()} Telemetry", gp[sub_key]))

        elif ch.number == 51:
            serp = leg.get("serp_appearance")
            if isinstance(serp, dict):
                blocks.append(_kv_table("SERP Snippet & Rich Appearance Audit", serp))
            if leg.get("competitor_seo_parity"):
                blocks.append(_kv_table("Competitive SEO Parity Matrix", leg["competitor_seo_parity"]))
            if leg.get("competitor_bakeoff"):
                blocks.append(_kv_table("Competitor Benchmark Bakeoff", leg["competitor_bakeoff"]))

        elif ch.number == 57:
            # URL-by-URL Diagnostic Dossiers
            pla = leg.get("page_level_assessments") or []
            rows = "".join(
                f"<tr><td>{_esc(_get(p, 'url'))}</td><td>{_esc(_get(p, 'status_code', 200))}</td>"
                f"<td>{_esc(_get(p, 'title') or '—')}</td><td>{_esc(_get(p, 'word_count', '—'))}</td>"
                f"<td>{_esc(_get(p, 'canonical_url') or '—')}</td></tr>"
                for p in (pla or ctx["pages"])[:40]
            )
            if rows:
                blocks.append(f'<h4>URL-by-URL Diagnostic Matrix</h4><table class="data-table"><thead><tr><th>URL</th><th>HTTP</th><th>Title</th><th>Words</th><th>Canonical</th></tr></thead><tbody>{rows}</tbody></table>')

        elif ch.number in (58, 59, 60) and ctx["tasks"]:
            t_cards = []
            for t in ctx["tasks"]:
                ft = str(t.get("fix_type") or "").upper()
                if ch.number == 59 and "CONTENT" not in ft:
                    continue
                if ch.number == 58 and "CONTENT" in ft:
                    continue
                impl = t.get("implementation") or {}
                snippet_html = (
                    f'<pre class="code-snippet">{_esc(impl.get("code_diff_snippet"))}</pre>'
                    if impl.get("code_diff_snippet")
                    else ""
                )
                t_cards.append(
                    f"<div class='finding-card'>"
                    f"<div class='finding-card-head'><strong>{_esc(t.get('task_id'))} · {_esc(t.get('problem'))}</strong>"
                    f"<span class='badge badge-neutral'>{_esc(t.get('priority', 'P1'))} · {_esc(impl.get('platform', 'GENERIC_HTML'))} ({_esc(impl.get('stack_confidence', 'GENERIC_FALLBACK'))})</span></div>"
                    f"<p><strong>Target:</strong> <code>{_esc(impl.get('target_file_pattern', 'Template'))}</code> · <strong>Owner:</strong> {_esc(t.get('owner'))} · <strong>Effort:</strong> {_esc(t.get('effort'))}</p>"
                    f"<p><strong>Fix:</strong> {_esc(t.get('recommended_fix'))}</p>"
                    f"{snippet_html}"
                    f"</div>"
                )
            if t_cards:
                blocks.append("<h4>Stack-Detected Remediation Directives</h4>" + "".join(t_cards[:20]))

        elif ch.number == 61:
            # 7/30/60/90 Roadmap (merge legacy roadmaps + new P0-P3 tasks)
            for label, key in (("7-Day Critical Sprint", "roadmap_7_days"), ("30-Day High-Impact Sprint", "roadmap_30_days"), ("90-Day Strategic Roadmap", "roadmap_90_days")):
                items = leg.get(key) or []
                if items:
                    lis = "".join(
                        f"<li>{_esc(i.get('title') or i.get('action') or i if isinstance(i, dict) else i)}</li>"
                        for i in items[:10]
                    )
                    blocks.append(f"<h4>{_esc(label)} (Sealed Report Roadmap)</h4><ul>{lis}</ul>")
            if ctx["tasks"]:
                buckets = {
                    "Days 1–7 (P0 Critical)": [t for t in ctx["tasks"] if t.get("priority") == "P0"],
                    "Days 8–30 (P1 High)": [t for t in ctx["tasks"] if t.get("priority") == "P1"],
                    "Days 31–60 (P2 Structural)": [t for t in ctx["tasks"] if t.get("priority") == "P2"],
                    "Days 61–90 (P3 Governance)": [t for t in ctx["tasks"] if t.get("priority") not in ("P0", "P1", "P2")],
                }
                for b_lbl, b_items in buckets.items():
                    if b_items:
                        lis = "".join(f"<li><strong>{_esc(t.get('task_id'))}:</strong> {_esc(t.get('problem'))} ({_esc(t.get('owner'))} · {_esc(t.get('effort'))})</li>" for t in b_items[:10])
                        blocks.append(f"<h4>{_esc(b_lbl)}</h4><ul>{lis}</ul>")

        elif ch.number == 62 and ctx.get("verification_runs"):
            for vr in ctx["verification_runs"][:15]:
                v_rows = "".join(
                    f"<tr><td>{_esc(r.get('dimension'))}</td><td>{_esc(r.get('before'))}</td><td>{_esc(r.get('after'))}</td></tr>"
                    for r in (vr.get("comparison_rows") or [])
                )
                blocks.append(
                    f"<div class='finding-card'>"
                    f"<p><strong>Live Verification — {_esc(vr.get('task_id'))}</strong> · URL: <code>{_esc(vr.get('target_url'))}</code> · Result: <strong>{_esc(vr.get('status'))}</strong></p>"
                    f"<p>{_esc(vr.get('check_summary'))}</p>"
                    + (f'<table class="data-table"><thead><tr><th>Dimension</th><th>Before</th><th>After (Live Re-crawl)</th></tr></thead><tbody>{v_rows}</tbody></table>' if v_rows else "")
                    + "</div>"
                )

        return "".join(blocks)

    def _render_appendix_body(self, ch: ChapterDefinition, ctx: Dict[str, Any]) -> str:
        if ch.id == "app_A":
            rows = "".join(
                f"<tr><td>{_esc(p.get('url'))}</td><td>{_esc(p.get('status_code', 200))}</td>"
                f"<td>{_esc(p.get('title') or '—')}</td><td>{_esc(p.get('word_count', 0))}</td>"
                f"<td>{_esc(p.get('canonical_url') or 'Missing')}</td></tr>"
                for p in ctx["pages"][:200]
            ) or "<tr><td colspan='5'>No crawled URLs recorded.</td></tr>"
            return (
                '<table class="data-table"><thead><tr><th>URL</th><th>HTTP</th><th>Title</th><th>Words</th><th>Canonical</th></tr></thead>'
                f"<tbody>{rows}</tbody></table>"
            )
        if ch.id == "app_B":
            rows = "".join(
                f"<tr><td><code>{_esc(e.get('evidence_id'))}</code></td><td>{_esc(e.get('check_id'))}</td>"
                f"<td>{_esc(e.get('url') or 'site')}</td><td>{_esc(e.get('result'))}</td>"
                f"<td><code>{_esc(str(e.get('content_sha256') or e.get('content_hash') or '')[:16])}</code></td></tr>"
                for e in ctx["evidence"][:250]
            ) or "<tr><td colspan='5'>No evidence records captured.</td></tr>"
            return (
                '<table class="data-table"><thead><tr><th>Evidence ID</th><th>Check</th><th>URL</th><th>Result</th><th>SHA-256</th></tr></thead>'
                f"<tbody>{rows}</tbody></table>"
            )
        if ch.id == "app_C":
            cov = ctx["coverage"]
            return (
                f"<p>Discovered: <strong>{cov['urls_discovered']}</strong> · Crawled: <strong>{cov['urls_crawled']}</strong> · "
                f"Rendered: <strong>{cov['urls_rendered']}</strong> · Deeply Inspected: <strong>{cov['urls_deeply_inspected']}</strong> · "
                f"URLs with Verified Findings: <strong>{cov['urls_with_verified_findings']}</strong> · Mode: <code>{_esc(cov['sampling_status'])}</code></p>"
            )
        if ch.id == "app_D":
            rows = "".join(
                f"<tr><td><code>{_esc(a.get('agent_id'))}</code></td><td>{_esc(a.get('department', 'seo'))}</td>"
                f"<td>{_esc(a.get('status'))}</td><td>{_esc(a.get('runtime_ms', 0))} ms</td><td>{_esc(a.get('findings_count', 0))}</td></tr>"
                for a in ctx["agents"]
            ) or "<tr><td colspan='5'>No specialist execution trace recorded.</td></tr>"
            return (
                '<table class="data-table"><thead><tr><th>Agent ID</th><th>Department</th><th>Status</th><th>Runtime</th><th>Findings</th></tr></thead>'
                f"<tbody>{rows}</tbody></table>"
            )
        if ch.id == "app_E":
            rows = "".join(
                f"<tr><td>{_esc(c.get('label') or c.get('provider_id'))}</td><td>{_esc(c.get('status'))}</td>"
                f"<td>{_esc(c.get('daily_quota_used', 0))} / {_esc(c.get('daily_quota_limit', 0))}</td>"
                f"<td>{_esc(c.get('last_sync_timestamp') or 'Never')}</td></tr>"
                for c in ctx["connectors"]
            ) or "<tr><td colspan='4'>No external connectors configured.</td></tr>"
            return (
                '<table class="data-table"><thead><tr><th>Connector</th><th>Status</th><th>Quota</th><th>Last Sync</th></tr></thead>'
                f"<tbody>{rows}</tbody></table>"
            )
        if ch.id == "app_F":
            sc = ctx["scorecard"] or {}
            dims = sc.get("dimensions") or []
            rows = "".join(
                f"<tr><td>{_esc(d.get('name'))}</td><td>{round(float(d.get('configured_weight', 0))*100, 1)}%</td>"
                f"<td>{(str(round(float(d['effective_weight'])*100, 1)) + '%') if d.get('effective_weight') is not None else 'Excluded'}</td>"
                f"<td>{d.get('score') if d.get('score') is not None else 'Unmeasured'}</td>"
                f"<td>{d.get('passed_checks_count', 0)} / {d.get('executed_checks_count', 0)}</td></tr>"
                for d in dims
            )
            return (
                f"<p>Methodology Version: <code>{_esc(sc.get('methodology_version') or 'dristik_seo_v3.0')}</code> · "
                "Formula: <code>S_i = 100 × (Weighted Passed / Weighted Executed)</code> · "
                "<code>S_SEO = Σ(W_d × S_d) / Σ(W_d)</code> over measured applicable dimensions only.</p>"
                '<table class="data-table"><thead><tr><th>Dimension</th><th>Configured Weight</th><th>Effective Weight</th><th>Score</th><th>Checks Passed</th></tr></thead>'
                f"<tbody>{rows}</tbody></table>"
            )
        if ch.id == "app_G":
            return (
                "<p><strong>Canonical URL:</strong> Authoritative URL version preferred for search indexing. "
                "<strong>Core Web Vitals:</strong> LCP (&le;2.5s), INP (&le;200ms), CLS (&le;0.1). "
                "<strong>VERIFIED_FIXED:</strong> Defect confirmed resolved via independent post-deployment re-crawl.</p>"
            )
        if ch.id == "app_H":
            dom = _esc(ctx["domain"])
            return (
                f'<pre class="code-snippet">curl -sIL https://{dom}/\n'
                f"curl -s https://{dom}/robots.txt | head -n 30\n"
                f"curl -s https://{dom}/ | grep -iE '&lt;title|rel=.canonical|&lt;h1'</pre>"
            )
        # app_I: Epistemic limitations & integrity seal
        lim_items = "".join(f"<li>{_esc(l)}</li>" for l in (ctx["limitations"] or ["Only crawled URLs and connected providers were evaluated; missing external sources are excluded without penalty."]))
        qa = ctx.get("qa") or {}
        qa_status = _esc(_get(qa, "status") or "CERTIFIED")
        return f"<ul>{lim_items}</ul><p><strong>QA Certification Status:</strong> <code>{qa_status}</code></p>"

    def render_publication(
        self,
        assessment: Any,
        report_data: Dict[str, Any],
        profile: str = "complete_book",
        *,
        selected_chapters: Optional[List[int]] = None,
        tone: str = "executive",
        qa_report: Optional[QaCertificationReport] = None,
    ) -> str:
        profile_key = profile.lower() if profile.lower() in self.SUPPORTED_PROFILES else "complete_book"
        profile_title = self.SUPPORTED_PROFILES[profile_key]
        ctx = self._extract_canonical(assessment, report_data)
        if qa_report is not None:
            ctx["qa"] = qa_report.model_dump()

        chapters = get_chapters_for_profile(profile_key)
        if selected_chapters:
            # Always preserve Scope/Limitations (Ch 5) and Epistemic Limitations (App I) — never allow hiding limitations
            allowed = set(selected_chapters) | {1, 2, 3, 5, 72}
            chapters = [c for c in chapters if c.number in allowed]

        date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y")
        cov = ctx["coverage"]
        sc = ctx["scorecard"] or {}
        overall_score = sc.get("overall_health_score")
        score_label = sc.get("overall_interpretation") or ("Not measured" if overall_score is None else "Measured")
        score_display = f"{overall_score}/100" if overall_score is not None else "Not measured"
        conf = sc.get("confidence_vectors") or {}
        has_crawl_cov = cov["urls_discovered"] > 0 or cov["urls_crawled"] > 0
        fmt_cov = lambda n: f"{n} URLs" if has_crawl_cov else "Not measured"
        qa = ctx.get("qa") or {}
        qa_status = str(_get(qa, "status") or "CERTIFIED")
        tasks_by_finding = {t.get("finding_id"): t for t in ctx["tasks"]}

        # Dimension scorecard table rows
        dim_rows = "".join(
            f"<tr><td>{_esc(d.get('name'))}</td>"
            f"<td>{round(float(d.get('configured_weight', 0))*100, 1)}%</td>"
            f"<td>{d.get('score') if d.get('score') is not None else 'Unmeasured'}</td>"
            f"<td>{d.get('passed_checks_count', 0)}/{d.get('executed_checks_count', 0)}</td>"
            f"<td>{_esc(d.get('interpretation') or 'Unmeasured')}</td></tr>"
            for d in (sc.get("dimensions") or [])
        )

        # Build clickable TOC
        toc_rows = "".join(
            f'<tr><td class="toc-number"><a href="#{_esc(ch.id)}">CH {ch.number:02d}</a></td>'
            f'<td class="toc-title"><a href="#{_esc(ch.id)}">{_esc(ch.title)}</a></td>'
            f'<td style="text-align:right;color:#64748b;font-size:8pt;">{_esc(ch.part_title)}</td></tr>'
            for ch in chapters
        )

        # Render Chapters (11-Part Anatomy) & Appendices
        body_sections: List[str] = []
        for ch in chapters:
            if ch.id in ("ch_01", "ch_02", "ch_03"):
                continue
            if ch.part == "APPENDIX":
                app_body = self._render_appendix_body(ch, ctx)
                body_sections.append(
                    f'<section id="{_esc(ch.id)}" class="chapter-start">'
                    f'<div class="kicker">{_esc(ch.part_title)} · Section {ch.number:02d}</div>'
                    f'<h2 class="chapter-title">{_esc(ch.title)}</h2>'
                    f'<p class="chapter-desc">{_esc(ch.description)}</p>'
                    f'<div class="card">{app_body}</div></section>'
                )
                continue

            anatomy = self._build_chapter_anatomy(ch, ctx, tone=tone)
            h_ov = anatomy.health_overview
            status_str = str(h_ov.get("status") or "MEASURED")
            st_badge = "badge-critical" if status_str == "ISSUE_VERIFIED" else "badge-good" if status_str == "NO_ISSUE_IN_SAMPLE" else "badge-neutral"
            findings_html = "".join(
                self._render_finding_card_html(f, tasks_by_finding.get(f.get("finding_id")))
                for f in anatomy.findings
            ) or '<p class="muted">No defects recorded for this chapter in the inspected sample.</p>'
            telemetry_html = self._render_chapter_telemetry_html(ch, ctx)

            body_sections.append(f"""
  <section id="{_esc(ch.id)}" class="chapter-start">
    <div class="kicker">{_esc(ch.part_title)} · Chapter {ch.number:02d}</div>
    <h2 class="chapter-title">{_esc(ch.title)}</h2>
    <p class="chapter-desc">{_esc(ch.description)}</p>
    <div class="anatomy-grid">
      <div class="card">
        <h3>1. Executive Interpretation</h3>
        <p>{_esc(anatomy.executive_interpretation)}</p>
        <h3>2. Health Overview</h3>
        <p><span class="badge {st_badge}">{_esc(status_str)}</span> · Score: <strong>{_esc(h_ov.get('score') if h_ov.get('score') is not None else 'Unmeasured')}</strong> · Coverage: <strong>{_esc(h_ov.get('coverage_pct'))}%</strong> · Confidence: <strong>{_esc(h_ov.get('confidence'))}</strong> · Source: <code>{_esc(h_ov.get('connector_status'))}</code></p>
        {telemetry_html}
        <h3>3. What Was Tested</h3>
        <p>{_esc(anatomy.what_was_tested)}</p>
        <h3>4. What Was Observed</h3>
        <p>{_esc(anatomy.what_was_observed)}</p>
        <h3>5. Findings ({len(anatomy.findings)})</h3>
        {findings_html}
        <h3>6. Root-Cause Analysis</h3>
        <p>{_esc(anatomy.root_cause_analysis)}</p>
        <h3>7. Business &amp; SEO Implications</h3>
        <p>{_esc(anatomy.business_seo_implications)}</p>
        <h3>8. Recommended Implementation</h3>
        <pre class="code-snippet">{_esc(anatomy.recommended_implementation)}</pre>
        <h3>9. Ownership &amp; Effort</h3>
        <p>{_esc(anatomy.ownership_and_effort)}</p>
        <h3>10. Validation Protocol</h3>
        <p>{_esc(anatomy.validation_protocol)}</p>
        <h3>11. Remaining Limitations</h3>
        <p>{_esc(anatomy.remaining_limitations)}</p>
      </div>
    </div>
  </section>
""")

        draft_banner = ""
        if qa_status == "BLOCKED_INTEGRITY_FAILURE":
            draft_banner = (
                '<div class="qa-banner-blocked"><strong>DRAFT — UNCERTIFIED PUBLICATION:</strong> '
                f"Blocked by Independent QA Gate ({_esc('; '.join(_get(qa, 'blocking_reasons') or []))})</div>"
            )
        elif qa_status == "PARTIAL_DISCLOSED":
            draft_banner = (
                '<div class="qa-banner-partial"><strong>PARTIAL AUDIT DISCLOSED:</strong> '
                f"Evaluated {cov['urls_crawled']} of {cov['urls_discovered']} discovered URLs ({_esc(cov['sampling_status'])}).</div>"
            )

        body_html = "".join(body_sections)
        integrity_hash = hashlib.sha256(f"{ctx['audit_id']}:{profile_key}:{len(ctx['findings'])}:{overall_score}:{body_html}".encode("utf-8")).hexdigest()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Dristik Enterprise SEO Audit — {_esc(ctx['domain'])}</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 18mm 15mm 20mm 15mm;
      @top-left {{ content: "DRISTIK ENTERPRISE SEO AUDIT"; font-size: 7.5pt; color: #64748b; font-weight: 600; }}
      @top-right {{ content: "{_esc(ctx['domain'])}"; font-size: 7.5pt; color: #64748b; }}
      @bottom-left {{ content: "CONFIDENTIAL · AUDIT ID: {_esc(ctx['audit_id'])} · SHA256: {integrity_hash[:12]}"; font-size: 7pt; color: #94a3b8; }}
      @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font-size: 7.5pt; color: #64748b; font-weight: 600; }}
    }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 9pt; line-height: 1.48; color: #0f172a; background: #fff; margin: 0; }}
    a {{ color: inherit; text-decoration: none; }}
    .chapter-start {{ break-before: page; padding-top: 6mm; }}
    .cover-page {{ break-after: page; background: #020817; color: #f8fafc; padding: 28mm 16mm 20mm 16mm; min-height: 245mm; box-sizing: border-box; }}
    .cover-kicker {{ font-size: 10pt; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #38bdf8; margin-bottom: 6mm; }}
    .cover-title {{ font-size: 30pt; font-weight: 800; line-height: 1.15; margin: 0 0 5mm 0; }}
    .cover-subtitle {{ font-size: 14pt; color: #94a3b8; margin-bottom: 20mm; }}
    .cover-metadata-grid {{ border-top: 1px solid #1e293b; padding-top: 8mm; display: grid; grid-template-columns: repeat(2, 1fr); gap: 5mm; font-size: 8.5pt; }}
    .cover-meta-item strong {{ display: block; color: #64748b; font-size: 7.5pt; text-transform: uppercase; margin-bottom: 1mm; }}
    .kicker {{ font-size: 8pt; font-weight: 700; color: #0284c7; text-transform: uppercase; letter-spacing: 0.06em; }}
    .chapter-title {{ font-size: 15pt; font-weight: 800; margin: 1mm 0 2mm 0; page-break-after: avoid; }}
    .chapter-desc {{ color: #64748b; font-size: 8.5pt; margin: 0 0 4mm 0; }}
    .card {{ border: 1px solid #cbd5e1; border-radius: 6px; padding: 4mm; margin-bottom: 4mm; background: #fff; }}
    .card h3 {{ font-size: 8.5pt; font-weight: 700; text-transform: uppercase; color: #0284c7; margin: 3mm 0 1mm 0; page-break-after: avoid; }}
    .card h3:first-child {{ margin-top: 0; }}
    .finding-card {{ border: 1px solid #e2e8f0; border-left: 3px solid #0284c7; border-radius: 4px; padding: 3mm; margin: 2mm 0; background: #f8fafc; page-break-inside: avoid; }}
    .finding-card-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5mm; }}
    .meta-line {{ font-size: 7.5pt; color: #64748b; font-family: ui-monospace, Menlo, monospace; margin-top: 1.5mm; }}
    .muted {{ color: #64748b; font-size: 8.5pt; }}
    .toc-table, .data-table {{ width: 100%; border-collapse: collapse; margin-top: 3mm; font-size: 8pt; }}
    .toc-table tr, .data-table tr {{ border-bottom: 1px solid #e2e8f0; }}
    .toc-table td, .data-table td, .data-table th {{ padding: 2mm 2mm; text-align: left; overflow-wrap: break-word; }}
    .data-table th {{ background: #f1f5f9; font-size: 7.5pt; text-transform: uppercase; color: #475569; }}
    .toc-number {{ font-weight: 700; color: #0284c7; width: 14mm; }}
    .badge {{ display: inline-block; padding: 1.5px 6px; border-radius: 4px; font-size: 7pt; font-weight: 700; text-transform: uppercase; }}
    .badge-critical {{ background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }}
    .badge-high {{ background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }}
    .badge-good {{ background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }}
    .badge-neutral {{ background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }}
    .code-snippet {{ background: #0f172a; color: #f8fafc; font-family: ui-monospace, Menlo, monospace; font-size: 7.5pt; padding: 2.5mm; border-radius: 4px; white-space: pre-wrap; overflow-wrap: anywhere; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 2.5mm; margin-top: 3mm; }}
    .kpi-box {{ border: 1px solid #e2e8f0; border-radius: 5px; padding: 3mm; background: #f8fafc; }}
    .qa-banner-blocked {{ background: #fef2f2; border: 1px solid #ef4444; color: #991b1b; padding: 3mm; border-radius: 5px; margin: 3mm 0; font-size: 8.5pt; }}
    .qa-banner-partial {{ background: #fffbeb; border: 1px solid #f59e0b; color: #92400e; padding: 3mm; border-radius: 5px; margin: 3mm 0; font-size: 8.5pt; }}
  </style>
</head>
<body>
  <div class="cover-page">
    <div class="cover-kicker">DRISTIK ENTERPRISE SEO INTELLIGENCE</div>
    <h1 class="cover-title">Enterprise SEO Audit Master Book</h1>
    <div class="cover-subtitle">{_esc(profile_title)}</div>
    <div class="cover-metadata-grid">
      <div class="cover-meta-item"><strong>Target Domain</strong><span>https://{_esc(ctx['domain'])}</span></div>
      <div class="cover-meta-item"><strong>Publication Profile</strong><span>{_esc(profile_title)} ({len(chapters)} Modules)</span></div>
      <div class="cover-meta-item"><strong>Canonical Audit ID</strong><code>{_esc(ctx['audit_id'])}</code></div>
      <div class="cover-meta-item"><strong>Published &amp; Methodology</strong><span>{date_str} · {_esc(sc.get('methodology_version') or 'dristik_seo_v3.0')}</span></div>
      <div class="cover-meta-item"><strong>QA Certification</strong><span>{_esc(qa_status)}</span></div>
      <div class="cover-meta-item"><strong>Integrity SHA-256</strong><code>{integrity_hash[:24]}</code></div>
    </div>
  </div>

  <div class="chapter-start">
    <h2 class="chapter-title">Table of Contents ({len(chapters)} Chapters &amp; Appendices)</h2>
    {draft_banner}
    <table class="toc-table"><tbody>{toc_rows}</tbody></table>
  </div>

  <div class="chapter-start">
    <h2 class="chapter-title">Executive SEO Scorecard &amp; Reconciled Crawl Scope</h2>
    <div style="display:flex;align-items:center;gap:6mm;margin-bottom:4mm;">
      <div>{_svg_score_gauge(overall_score)}</div>
      <div>
        <p><strong>SEO Health Rating:</strong> {_esc(score_label)} ({score_display})</p>
        <p><strong>Audit Coverage:</strong> {f"{conf['audit_coverage_pct']}%" if conf.get('audit_coverage_pct') is not None else 'Not measured'} · <strong>Evidence Confidence:</strong> {f"{conf['evidence_confidence_pct']}%" if conf.get('evidence_confidence_pct') is not None else 'Not measured'} · <strong>Connector Completeness:</strong> {f"{conf['connector_completeness_pct']}%" if conf.get('connector_completeness_pct') is not None else 'Not measured'}</p>
        <p><strong>Canonical Findings:</strong> {len(ctx['findings'])} · <strong>Evidence Records:</strong> {len(ctx['evidence'])} · <strong>Remediation Tasks:</strong> {len(ctx['tasks'])}</p>
      </div>
    </div>
    <div class="kpi-grid">
      <div class="kpi-box"><div class="kicker">Discovered</div><strong>{fmt_cov(cov['urls_discovered'])}</strong></div>
      <div class="kpi-box"><div class="kicker">Crawled</div><strong>{fmt_cov(cov['urls_crawled'])}</strong></div>
      <div class="kpi-box"><div class="kicker">Rendered</div><strong>{fmt_cov(cov['urls_rendered'])}</strong></div>
      <div class="kpi-box"><div class="kicker">Inspected</div><strong>{fmt_cov(cov['urls_deeply_inspected'])}</strong></div>
      <div class="kpi-box"><div class="kicker">Defect URLs</div><strong>{fmt_cov(cov['urls_with_verified_findings'])}</strong></div>
    </div>
    {f'<table class="data-table"><thead><tr><th>Dimension</th><th>Weight</th><th>Score</th><th>Passed/Run</th><th>Band</th></tr></thead><tbody>{dim_rows}</tbody></table>' if dim_rows else ''}
  </div>

  {body_html}
</body>
</html>"""

    def publish_with_qa_gate(
        self,
        assessment: Any,
        report_data: Dict[str, Any],
        profile: str = "complete_book",
        *,
        selected_chapters: Optional[List[int]] = None,
        tone: str = "executive",
    ) -> Tuple[str, QaCertificationReport, str]:
        """Runs fail-closed SeoQaValidator before publishing, returning (html, qa_report, sha256_hash)."""
        validator = SeoQaValidator()
        qa = validator.validate(assessment, report_data)
        rendered_html = self.render_publication(
            assessment=assessment,
            report_data=report_data,
            profile=profile,
            selected_chapters=selected_chapters,
            tone=tone,
            qa_report=qa,
        )
        digest = hashlib.sha256(rendered_html.encode("utf-8")).hexdigest()
        return rendered_html, qa, digest

    async def render_pdf_bytes(self, html_content: str) -> Optional[bytes]:
        from app.crawl.browser import BrowserRenderService
        return await BrowserRenderService.render_pdf(html_content)


enterprise_pdf_engine = EnterprisePdfEngine()

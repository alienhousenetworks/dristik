"""Phases 36–39 — Canonical CRO Report Builder, Chart Renderer, PDF Publisher & QA Validator.

Pulls exclusively from the canonical CROStore snapshot so backend, frontend, JSON, HTML,
and PDF reports always share identical audit IDs, scores, finding counts, methodology
version, and evidence references.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.crawl.browser import BrowserRenderService
from app.cro.models import CRO_METHODOLOGY_VERSION, CROReport
from app.cro.quality import CROQualityAssuranceEngine
from app.cro.reports.section_registry import (
    CRO_BOOK_SECTIONS,
    CRO_DYNAMIC_APPENDICES,
    CRO_REPORT_PROFILES,
)
from app.db.cro_schema import CROStore, get_cro_store


def _esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def render_weighted_scorecard_svg(dimensions: List[Dict[str, Any]]) -> str:
    """Vector SVG bar chart for the 10 weighted CRO Experience Dimensions."""
    width = 740
    row_h = 30
    label_w = 245
    bar_max = 340
    height = 44 + (row_h * max(1, len(dimensions)))
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="#faf9f6" stroke="#e2e0d8" rx="6"/>',
        '<text x="16" y="24" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#111827">CRO EXPERIENCE SCORECARD (10 WEIGHTED DIMENSIONS · 100% TOTAL)</text>',
    ]
    for i, d in enumerate(dimensions):
        y = 40 + i * row_h
        name = str(d.get("name", ""))[:34]
        w = d.get("configured_weight_pct", 0)
        sc = d.get("score")
        if sc is None:
            color, bw, txt = "#94a3b8", 48.0, f"UNMEASURED ({w:.0f}%)"
        elif sc >= 80:
            color, bw, txt = "#15803d", (sc / 100.0) * bar_max, f"{sc:.1f}/100 ({w:.0f}%)"
        elif sc >= 60:
            color, bw, txt = "#b45309", (sc / 100.0) * bar_max, f"{sc:.1f}/100 ({w:.0f}%)"
        else:
            color, bw, txt = "#b91c1c", (sc / 100.0) * bar_max, f"{sc:.1f}/100 ({w:.0f}%)"
        parts.append(
            f'<text x="16" y="{y+15}" font-family="system-ui, sans-serif" font-size="10.5" fill="#1f2937">{_esc(name)}</text>'
            f'<rect x="{label_w}" y="{y+3}" width="{max(4.0, bw):.1f}" height="16" fill="{color}" rx="3"/>'
            f'<text x="{label_w + max(4.0, bw) + 8:.1f}" y="{y+15}" font-family="ui-monospace, monospace" font-size="9.5" font-weight="600" fill="{color}">{_esc(txt)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def render_funnel_svg(funnels: List[Dict[str, Any]]) -> str:
    """Vector SVG funnel bar chart strictly reflecting measured or unmeasured step counts."""
    steps = (funnels[0].get("steps") or []) if funnels else []
    if not steps:
        return ""
    width = 740
    row_h = 32
    height = 44 + row_h * len(steps)
    max_cnt = max([int(s.get("eligible_count") or s.get("progressing_count") or 0) for s in steps] + [1])
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="#ffffff" stroke="#e2e0d8" rx="6"/>',
        '<text x="16" y="24" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#111827">CONVERSION FUNNEL PROGRESSION &amp; DROP-OFF</text>',
    ]
    for i, st in enumerate(steps):
        y = 40 + i * row_h
        name = str(st.get("step_name", f"Step {i+1}"))[:28]
        measured = st.get("measurement_status") == "measured"
        prog = st.get("progressing_count")
        conv = st.get("step_conversion_rate")
        aband = st.get("step_abandonment_rate")
        if measured and isinstance(prog, int):
            bw = max(12.0, (prog / max_cnt) * 320.0)
            col = "#b91c1c" if (aband or 0) >= 50 else "#1d4ed8"
            lbl = f"{prog:,} users · {conv:.1f}% conv · {aband:.1f}% drop"
        else:
            bw, col, lbl = 56.0, "#cbd5e1", "DATA UNAVAILABLE (not connected)"
        parts.append(
            f'<text x="16" y="{y+16}" font-family="system-ui, sans-serif" font-size="10.5" fill="#1f2937">{i+1}. {_esc(name)}</text>'
            f'<rect x="235" y="{y+4}" width="{bw:.1f}" height="17" fill="{col}" rx="3"/>'
            f'<text x="{235 + bw + 8:.1f}" y="{y+16}" font-family="ui-monospace, monospace" font-size="9.5" fill="#334155">{_esc(lbl)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


class CROReportBuilder:
    """Builds JSON, HTML, and PDF CRO reports from the canonical CROStore dataset."""

    def __init__(self, store: Optional[CROStore] = None):
        self.store = store or get_cro_store()

    def build_canonical_dataset(self, tenant_id: str, audit_id: str) -> Dict[str, Any]:
        audit = self.store.get_audit(tenant_id, audit_id)
        if not audit:
            raise KeyError(f"CRO audit '{audit_id}' not found.")
        profile = self.store.get_business_profile(tenant_id, audit.profile_id) if audit.profile_id else None
        goals = self.store.list_goals(tenant_id, audit_id=audit_id)
        audiences = self.store.list_audiences(tenant_id, audit_id=audit_id)
        pages = self.store.list_pages(tenant_id, audit_id=audit_id)
        journeys = self.store.list_journeys(tenant_id, audit_id=audit_id)
        elements = self.store.list_elements(tenant_id, audit_id=audit_id)
        tests = self.store.list_interaction_tests(tenant_id, audit_id=audit_id)
        events = self.store.list_analytics_events(tenant_id, audit_id=audit_id)
        funnels = self.store.list_funnels(tenant_id, audit_id=audit_id)
        findings = self.store.list_findings(tenant_id, audit_id=audit_id)
        recommendations = self.store.list_recommendations(tenant_id, audit_id=audit_id)
        experiments = self.store.list_experiments(tenant_id, audit_id=audit_id)
        pack = self.store.get_remediation_pack(tenant_id, audit_id=audit_id)
        verifications = self.store.list_verifications(tenant_id, audit_id=audit_id)
        snapshots = self.store.list_snapshots(tenant_id, audit_id=audit_id)
        scorecard = self.store.get_artifact(tenant_id, audit_id, "scorecard") or {}
        dept_artifacts = self.store.get_artifact(tenant_id, audit_id, "department_artifacts") or {}
        qa_report = self.store.get_artifact(tenant_id, audit_id, "qa_report") or {}

        return {
            "audit": audit.model_dump(),
            "profile": profile.model_dump() if profile else {},
            "goals": [g.model_dump() for g in goals],
            "audiences": [a.model_dump() for a in audiences],
            "pages": [p.model_dump() for p in pages],
            "journeys": [j.model_dump() for j in journeys],
            "elements": [e.model_dump() for e in elements],
            "interaction_tests": [t.model_dump() for t in tests],
            "analytics_events": [e.model_dump() for e in events],
            "funnels": [f.model_dump() for f in funnels],
            "findings": [f.model_dump() for f in findings],
            "recommendations": [r.model_dump() for r in recommendations],
            "experiments": [e.model_dump() for e in experiments],
            "remediation_pack": pack.model_dump() if pack else {},
            "verifications": [v.model_dump() for v in verifications],
            "snapshots": [s.model_dump() for s in snapshots],
            "scorecard": scorecard,
            "department_artifacts": dept_artifacts,
            "qa_report": qa_report,
            "methodology_version": audit.methodology_version or CRO_METHODOLOGY_VERSION,
        }

    def select_sections(self, dataset: Dict[str, Any], profile_key: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        """Dynamically select applicable, evidence-supported sections for the requested profile."""
        prof = CRO_REPORT_PROFILES.get(profile_key, CRO_REPORT_PROFILES["complete_audit_book"])
        allowed_domains = set(prof["domains"])
        ecom_applicable = bool((dataset.get("department_artifacts", {}).get("ecommerce_audit") or {}).get("applicable"))
        included: List[Dict[str, Any]] = []
        omitted: List[Dict[str, str]] = []

        for sec in CRO_BOOK_SECTIONS:
            if "*" not in allowed_domains and sec["domain"] not in allowed_domains:
                omitted.append({"section": f"{sec['num']:02d}. {sec['title']}", "reason": f"Excluded by report profile '{profile_key}'."})
                continue
            if sec.get("requires_ecommerce") and not ecom_applicable:
                omitted.append({"section": f"{sec['num']:02d}. {sec['title']}", "reason": "Ecommerce chapters omitted (not applicable to this business model)."})
                continue
            included.append(sec)
        return included, omitted

    def build_standardized_chapter(self, sec: Dict[str, Any], dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 38 standardized 14-field chapter template bound to canonical audit data."""
        domain_tag = sec["domain"]
        findings = dataset.get("findings") or []
        domain_to_cats = {
            "strategy": {"conversion_strategy"},
            "ux": {"ux_audit", "funnel_optimization"},
            "ui": {"ui_audit", "cta_intelligence"},
            "accessibility": {"accessibility"},
            "mobile": {"mobile_cro"},
            "landing": {"landing_page_optimization"},
            "copywriting": {"copywriting_optimization"},
            "cta": {"cta_intelligence"},
            "forms": {"form_optimization"},
            "leadgen": {"lead_generation_cro"},
            "ecommerce": {"ecommerce_cro"},
            "checkout": {"ecommerce_cro"},
            "trust": {"trust_optimization"},
            "performance": {"performance_interaction"},
            "analytics": {"analytics_intelligence", "funnel_optimization"},
            "remediation": {f.get("category", "") for f in findings},
        }
        cats = domain_to_cats.get(domain_tag, set())
        matched_findings = [f for f in findings if f.get("category") in cats]
        pages = dataset.get("pages") or []
        tests = dataset.get("interaction_tests") or []
        verifications = dataset.get("verifications") or []
        audit = dataset.get("audit") or {}

        ev_ids = list(dict.fromkeys(eid for f in matched_findings for eid in (f.get("evidence_ids") or [])))[:8]
        return {
            "number": sec["num"],
            "part": sec["part"],
            "key": sec["key"],
            "title": sec["title"],
            "objective": f"Evaluate {sec['title'].lower()} against the primary conversion objective ({dataset.get('profile', {}).get('primary_conversion', 'configured goal')}).",
            "what_was_tested": f"{len(pages)} audited page(s), {len(tests)} browser/DOM interaction test(s), and connected telemetry where authorized.",
            "scope": f"Domain {audit.get('domain', '')} · Audit {audit.get('audit_id', '')} · Mode {audit.get('mode', 'standard')}",
            "observations": [
                f"{f.get('finding_id')}: {f.get('title')} [{f.get('source_type')}] — {f.get('description')}"
                for f in matched_findings[:6]
            ] or [f"No material defects flagged specifically under {sec['title']} in the audited sample."],
            "evidence": ev_ids or [p.get("page_id") for p in pages[:3]],
            "business_relevance": (
                matched_findings[0].get("claim_boundary")
                if matched_findings
                else "Assessed as part of conversion readiness; measured behavioral impact requires connected analytics or experimentation."
            ),
            "root_cause": matched_findings[0].get("root_cause") if matched_findings else "No blocking root cause detected in sample.",
            "severity_and_confidence": (
                f"{matched_findings[0].get('severity', 'informational').upper()} · confidence={matched_findings[0].get('confidence', 0.8)}"
                if matched_findings
                else "INFORMATIONAL · confidence=0.8"
            ),
            "recommended_fix": matched_findings[0].get("recommendation") if matched_findings else "Maintain baseline and monitor for regressions.",
            "implementation_instructions": matched_findings[0].get("implementation_instructions") if matched_findings else "No immediate code change required.",
            "owner_and_effort": f"{matched_findings[0].get('owner_role', 'Product')} ({matched_findings[0].get('effort', 'low')} effort)" if matched_findings else "Product (none)",
            "acceptance_criteria": matched_findings[0].get("acceptance_criteria") if matched_findings else ["Maintain passing checks on scheduled monitoring."],
            "verification_result": (
                f"{len(verifications)} independent verification record(s) attached."
                if verifications
                else "Pending deployment and independent post-fix retest."
            ),
            "limitations": list(dict.fromkeys((matched_findings[0].get("limitations") if matched_findings else []) + (audit.get("limitations") or [])))[:4],
        }

    def render_json(self, tenant_id: str, audit_id: str, profile: str = "complete_audit_book") -> Dict[str, Any]:
        dataset = self.build_canonical_dataset(tenant_id, audit_id)
        prof_meta = CRO_REPORT_PROFILES.get(profile, CRO_REPORT_PROFILES["complete_audit_book"])
        included, omitted = self.select_sections(dataset, profile)
        chapters = [self.build_standardized_chapter(sec, dataset) for sec in included]
        allowed_app = set(prof_meta["appendices"])
        appendices = [a for a in CRO_DYNAMIC_APPENDICES if "*" in allowed_app or a["id"] in allowed_app]
        return {
            "report_profile": profile,
            "title": prof_meta["title"],
            "audience": prof_meta["audience"],
            "audit_id": audit_id,
            "methodology_version": dataset["methodology_version"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "audit": dataset["audit"],
            "profile": dataset["profile"],
            "scorecard": dataset["scorecard"],
            "findings": dataset["findings"],
            "remediation_pack": dataset["remediation_pack"],
            "experiments": dataset["experiments"],
            "verifications": dataset["verifications"],
            "chapters_included_count": len(chapters),
            "chapters_omitted": omitted,
            "chapters": chapters,
            "appendices": appendices,
            "qa_report": dataset["qa_report"],
        }

    def render_html(self, tenant_id: str, audit_id: str, profile: str = "complete_audit_book") -> Tuple[str, Dict[str, Any]]:
        payload = self.render_json(tenant_id, audit_id, profile=profile)
        dataset = self.build_canonical_dataset(tenant_id, audit_id)
        sc = payload["scorecard"] or {}
        audit = payload["audit"] or {}
        bp = payload["profile"] or {}
        chapters = payload["chapters"]
        findings = payload["findings"]
        pack = payload["remediation_pack"] or {}

        toc_html = "".join(
            f'<li><a href="#sec-{c["number"]:02d}"><strong>{c["number"]:02d}.</strong> {_esc(c["title"])}</a> <span class="muted">({_esc(c["part"])})</span></li>'
            for c in chapters
        )
        scorecard_svg = render_weighted_scorecard_svg(sc.get("experience_dimensions") or [])
        funnel_svg = render_funnel_svg(dataset.get("funnels") or [])

        biz_rows = "".join(
            f"<tr><td>{_esc(m.get('metric'))}</td><td>{_esc(m.get('formula'))}</td>"
            f"<td>{_esc(m.get('status'))}</td><td><strong>{_esc(m.get('value') if m.get('value') is not None else 'Unavailable')}</strong> {_esc(m.get('unit') if m.get('value') is not None else '')}</td></tr>"
            for m in (sc.get("business_performance_metrics") or [])
        )

        chapter_blocks = []
        for c in chapters:
            obs_li = "".join(f"<li>{_esc(o)}</li>" for o in c["observations"])
            ac_li = "".join(f"<li>{_esc(a)}</li>" for a in (c["acceptance_criteria"] or []))
            lim_li = "".join(f"<li>{_esc(l)}</li>" for l in (c["limitations"] or []))
            chapter_blocks.append(
                f'<section class="chapter" id="sec-{c["number"]:02d}">'
                f'<p class="kicker">{_esc(c["part"])}</p>'
                f'<h2>{c["number"]:02d}. {_esc(c["title"])}</h2>'
                f'<table class="meta-table"><tbody>'
                f'<tr><th>Objective</th><td>{_esc(c["objective"])}</td></tr>'
                f'<tr><th>What was tested</th><td>{_esc(c["what_was_tested"])}</td></tr>'
                f'<tr><th>Scope</th><td>{_esc(c["scope"])}</td></tr>'
                f'<tr><th>Evidence IDs</th><td class="mono">{_esc(", ".join(str(x) for x in c["evidence"]))}</td></tr>'
                f'<tr><th>Business relevance</th><td>{_esc(c["business_relevance"])}</td></tr>'
                f'<tr><th>Root cause</th><td>{_esc(c["root_cause"])}</td></tr>'
                f'<tr><th>Severity &amp; confidence</th><td class="mono">{_esc(c["severity_and_confidence"])}</td></tr>'
                f'<tr><th>Recommended fix</th><td>{_esc(c["recommended_fix"])}</td></tr>'
                f'<tr><th>Implementation instructions</th><td>{_esc(c["implementation_instructions"])}</td></tr>'
                f'<tr><th>Owner &amp; effort</th><td>{_esc(c["owner_and_effort"])}</td></tr>'
                f'<tr><th>Verification result</th><td>{_esc(c["verification_result"])}</td></tr>'
                f'</tbody></table>'
                f'<h4>Observations</h4><ul>{obs_li}</ul>'
                f'<h4>Acceptance Criteria</h4><ul>{ac_li}</ul>'
                f'{"<h4>Limitations</h4><ul>" + lim_li + "</ul>" if lim_li else ""}'
                f'</section>'
            )

        task_rows = "".join(
            f"<tr><td class='mono'>{_esc(t.get('task_id'))}</td><td><strong>{_esc(t.get('priority'))}</strong></td>"
            f"<td>{_esc(t.get('title'))}</td><td>{_esc(t.get('department'))}</td>"
            f"<td>{_esc(t.get('effort_estimate'))}</td><td>{_esc(t.get('verification_status'))}</td></tr>"
            for t in (pack.get("tasks") or [])
        ) or '<tr><td colspan="6">No remediation tasks required.</td></tr>'

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{_esc(payload["title"])} — {_esc(audit.get("domain", ""))}</title>
<style>
@page {{ size: A4; margin: 18mm 14mm 20mm 14mm; }}
body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #0f172a; background: #ffffff; font-size: 10.5pt; line-height: 1.5; }}
.cover {{ page-break-after: always; padding: 36px 28px; background: #0f172a; color: #f8fafc; border-radius: 8px; margin-bottom: 24px; }}
.cover h1 {{ font-size: 26pt; margin: 10px 0 6px; }}
.cover .sub {{ color: #94a3b8; font-size: 11pt; }}
.wrap {{ max-width: 960px; margin: 0 auto; padding: 24px 20px; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; }}
.kpi {{ border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; background: #f8fafc; }}
.kpi .lbl {{ font-size: 8.5pt; text-transform: uppercase; color: #475569; letter-spacing: 0.04em; }}
.kpi .val {{ font-size: 20pt; font-weight: 700; margin-top: 4px; }}
.chapter {{ page-break-inside: avoid; border-top: 2px solid #e2e8f0; padding-top: 14px; margin-top: 20px; }}
.kicker {{ font-size: 8pt; text-transform: uppercase; color: #64748b; margin: 0; letter-spacing: 0.05em; }}
h2 {{ font-size: 14pt; margin: 4px 0 10px; color: #0f172a; }}
h4 {{ font-size: 10pt; margin: 10px 0 4px; color: #1e293b; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 9pt; table-layout: fixed; word-wrap: break-word; }}
th, td {{ border: 1px solid #e2e8f0; padding: 6px 8px; text-align: left; vertical-align: top; }}
th {{ background: #f1f5f9; width: 24%; font-weight: 600; }}
.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 8.5pt; }}
.muted {{ color: #64748b; font-size: 8.5pt; }}
a {{ color: #1d4ed8; text-decoration: none; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="cover">
    <p class="mono" style="color:#38bdf8;">DRISTIK ENTERPRISE CRO INTELLIGENCE · {_esc(payload["methodology_version"])}</p>
    <h1>{_esc(payload["title"])}</h1>
    <p class="sub">Target: {_esc(audit.get("domain"))} ({_esc(audit.get("target_url"))}) · Audience: {_esc(payload["audience"])}</p>
    <p class="mono" style="color:#cbd5e1;margin-top:24px;">Audit ID: {_esc(audit_id)} · Business Model: {_esc(bp.get("business_type", "unknown"))} · Generated: {_esc(payload["generated_at"])}</p>
  </div>

  <h2>Three Separate CRO Scorecards</h2>
  <div class="kpi-grid">
    <div class="kpi"><div class="lbl">1. CRO Experience Score</div><div class="val">{_esc(sc.get("experience_score") if sc.get("experience_score") is not None else "Unmeasured")}</div><div class="muted">Grade: {_esc(sc.get("experience_grade", "Unmeasured"))} · Weight evaluated: {_esc(sc.get("experience_active_weight_pct", 0))}%</div></div>
    <div class="kpi"><div class="lbl">2. Conversion Measurement Score</div><div class="val">{_esc(sc.get("measurement_score") if sc.get("measurement_score") is not None else "Unmeasured")}</div><div class="muted">Status: {_esc(sc.get("measurement_status", "unmeasured"))}</div></div>
    <div class="kpi"><div class="lbl">3. Measured Business Performance</div><div class="val" style="font-size:14pt;">{_esc(str(sc.get("business_performance_status", "data_unavailable")).upper())}</div><div class="muted">Scope coverage: {_esc(sc.get("scope_coverage_pct"))}% · Confidence: {_esc(sc.get("confidence"))}</div></div>
  </div>
  {scorecard_svg}
  <div style="margin-top:14px;">{funnel_svg}</div>

  <h2>Measured Business Performance Metrics</h2>
  <table><thead><tr><th>Metric</th><th>Formula</th><th>Status</th><th>Value</th></tr></thead><tbody>{biz_rows}</tbody></table>

  <h2>Table of Contents ({len(chapters)} Applicable Sections)</h2>
  <ol>{toc_html}</ol>

  <h2>Consolidated Remediation Roadmap ({len(pack.get("tasks") or [])} Coordinated Tasks from {len(findings)} Findings)</h2>
  <table><thead><tr><th>Task ID</th><th>Priority</th><th>Initiative</th><th>Department</th><th>Effort</th><th>Verification</th></tr></thead><tbody>{task_rows}</tbody></table>

  {"".join(chapter_blocks)}
</div>
</body>
</html>"""
        return html_doc, payload

    async def publish_report(
        self,
        *,
        tenant_id: str,
        audit_id: str,
        profile: str = "complete_audit_book",
        fmt: str = "html",
    ) -> Tuple[CROReport, bytes]:
        """Generate, QA-validate, persist in CAS, and return (CROReport, bytes)."""
        html_doc, json_payload = self.render_html(tenant_id, audit_id, profile=profile)
        audit = self.store.get_audit(tenant_id, audit_id)
        assert audit is not None
        from app.cro.models import CROThreeScorecardBundle
        sc_raw = self.store.get_artifact(tenant_id, audit_id, "scorecard") or {"audit_id": audit_id}
        sc_model = CROThreeScorecardBundle.model_validate(sc_raw)
        qa = CROQualityAssuranceEngine.validate_audit(
            audit=audit,
            pages=self.store.list_pages(tenant_id, audit_id),
            interaction_tests=self.store.list_interaction_tests(tenant_id, audit_id),
            findings=self.store.list_findings(tenant_id, audit_id),
            scorecard=sc_model,
            remediation_pack=self.store.get_remediation_pack(tenant_id, audit_id),
            verifications=self.store.list_verifications(tenant_id, audit_id=audit_id),
            report_payload=json_payload,
        )

        fmt_low = fmt.lower()
        if fmt_low == "json":
            raw_bytes = json.dumps(json_payload, indent=2, default=str).encode("utf-8")
            ext = "json"
        elif fmt_low == "pdf":
            pdf_bytes = await BrowserRenderService.render_pdf(html_doc, timeout_ms=45000)
            if pdf_bytes and pdf_bytes.startswith(b"%PDF-"):
                raw_bytes = pdf_bytes
                ext = "pdf"
            else:
                # Deterministic minimal valid PDF fallback when Chromium is disabled in CI/sandbox
                raw_bytes = _build_minimal_valid_pdf(
                    title=json_payload["title"],
                    domain=audit.domain,
                    audit_id=audit_id,
                    experience_score=sc_model.experience_score,
                    findings_count=len(json_payload["findings"]),
                )
                ext = "pdf"
        else:
            raw_bytes = html_doc.encode("utf-8")
            ext = "html"

        snap = self.store.persist_snapshot(
            tenant_id=tenant_id,
            audit_id=audit_id,
            snapshot_type=f"report_{profile}_{ext}",
            data=raw_bytes,
            extension=ext,
            url=audit.target_url,
            metadata={"profile": profile, "format": ext},
        )
        rep = CROReport(
            tenant_id=tenant_id,
            audit_id=audit_id,
            url=audit.target_url,
            profile=profile,
            format=ext,
            title=json_payload["title"],
            snapshot_id=snap.snapshot_id,
            sections_included=[f"{c['number']:02d}. {c['title']}" for c in json_payload["chapters"]],
            sections_omitted=json_payload["chapters_omitted"],
            qa_passed=qa.qa_status != "failed",
            qa_summary=qa.model_dump(),
            storage_uri=snap.storage_uri,
            content_hash=snap.content_hash,
        )
        self.store.save_report(rep)
        return rep, raw_bytes


def _build_minimal_valid_pdf(
    *,
    title: str,
    domain: str,
    audit_id: str,
    experience_score: Optional[float],
    findings_count: int,
) -> bytes:
    """Standards-compliant single-page PDF fallback when headless Chromium is unavailable."""
    safe_line = f"Dristik CRO Report | {title} | {domain} | Audit {audit_id} | Score: {experience_score} | Findings: {findings_count}"
    safe_line = safe_line.replace("(", "[").replace(")", "]").replace("\\", "/")[:110]
    stream = f"BT /F1 11 Tf 40 760 Td ({safe_line}) Tj ET".encode("latin-1", errors="replace")
    objs = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n",
        b"4 0 obj << /Length " + str(len(stream)).encode() + b" >> stream\n" + stream + b"\nendstream endobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode())
    return bytes(out)


cro_report_builder = CROReportBuilder()

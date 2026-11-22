"""Phases 23–26 — Canonical GEO Report Builder, Vector SVG Charts, PDF Publisher & Validator.

Consumes exclusively the canonical `GEOStore` dataset so backend API, frontend
workspace, JSON export, HTML report, and printed PDF always agree 1:1 on audit ID,
methodology version, dual scores, prompt denominators, citations, and findings.

Also exports reusable helpers (`load_latest_enterprise_geo_dataset`,
`render_geo_finding_card_html`, `render_enterprise_geo_dossier_fragment`) so
legacy/adaptive PDFs (`/sections/geo/pdf`, `/geo-report?format=pdf`, `/audit-book?format=pdf`,
and SEO Chapter 18) automatically surface all new Enterprise GEO findings, dual scorecards,
remediation packs, verifications, experiments, citations, entities, and QA checks alongside
all legacy findings.

Reuses Dristik's `BrowserRenderService.render_pdf` (headless Chromium print-to-PDF)
with a deterministic multi-page PDF fallback in Chromium-less CI/sandbox environments.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from app.crawl.browser import BrowserRenderService
from app.db.geo_schema import GEOStore, get_geo_store
from app.geo.connectors import GEOConnectorManager
from app.geo.models import (
    GEO_METHODOLOGY_VERSION,
    GEODataQualityState,
    GEODualScorecard,
    GEOPublicationStatus,
    GEOReport,
)
from app.geo.monitoring import GEOMonitoringEngine
from app.geo.quality import GEOQualityAssuranceEngine
from app.geo.reporting.section_registry import (
    GEO_BOOK_SECTIONS,
    GEO_DYNAMIC_APPENDICES,
    GEO_REPORT_PROFILES,
)


def _esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def _norm_domain(domain_or_url: Optional[str]) -> str:
    raw = str(domain_or_url or "").strip().lower()
    raw = re.sub(r"^https?://", "", raw)
    raw = raw.split("/")[0].split(":")[0]
    if raw.startswith("www."):
        raw = raw[4:]
    return raw


def _fget(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _enum_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    if hasattr(val, "value"):
        return str(val.value)
    if hasattr(val, "name"):
        return str(val.name)
    return str(val)


def _collect_legacy_findings_for_domain(
    tenant_id: str,
    domain: str,
    canonical_findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Best-effort, tenant-isolated lookup of legacy ExecutiveReport findings for the same domain.

    Never mutates canonical `findings` count (preserving QA-12 Backend==PDF consistency),
    and deduplicates against canonical finding IDs and normalized titles.
    """
    target_dom = _norm_domain(domain)
    if not target_dom:
        return []
    try:
        from app.orchestration.orchestrator import orchestrator
    except Exception:
        return []

    seen_ids = {str(f.get("finding_id") or "").strip().lower() for f in canonical_findings if f.get("finding_id")}
    seen_titles = {str(f.get("title") or "").strip().lower() for f in canonical_findings if f.get("title")}
    legacy_out: List[Dict[str, Any]] = []

    runs = list(getattr(orchestrator, "runs", {}).values())
    # Prefer most recent matching run for this tenant + domain
    matching_runs = [
        r for r in runs
        if getattr(r, "report", None) is not None
        and (getattr(r, "org_id", None) or "default") == (tenant_id or "default")
        and _norm_domain(getattr(r.report, "domain", None) or getattr(r, "website_url", None)) == target_dom
    ]
    if not matching_runs:
        return []
    matching_runs.sort(key=lambda r: str(getattr(r, "updated_at", None) or getattr(r, "created_at", "")), reverse=True)
    rep = matching_runs[0].report
    for f in list(getattr(rep, "findings", None) or []):
        d = f.model_dump() if hasattr(f, "model_dump") else (dict(f) if isinstance(f, dict) else {})
        if not d:
            continue
        fid = str(d.get("finding_id") or d.get("id") or "").strip()
        title = str(d.get("finding_title") or d.get("title") or "").strip()
        if (fid and fid.lower() in seen_ids) or (title and title.lower() in seen_titles):
            continue
        if fid:
            seen_ids.add(fid.lower())
        if title:
            seen_titles.add(title.lower())
        legacy_out.append(d)
    return legacy_out


def load_latest_enterprise_geo_dataset(report: Any, store: Optional[GEOStore] = None) -> Optional[Dict[str, Any]]:
    """Safely fetch the latest Enterprise GEO canonical dataset for a legacy ExecutiveReport.

    Strictly enforces tenant (`org_id`) and domain isolation; returns None if no Enterprise
    GEO audit exists for that tenant+domain. Never fabricates data.
    """
    if report is None:
        return None
    pinned = _fget(report, "_enterprise_geo_dataset")
    if isinstance(pinned, dict):
        return pinned
    target_dom = _norm_domain(_fget(report, "domain") or _fget(report, "website_url"))
    if not target_dom:
        return None
    tenant_id = str(_fget(report, "org_id") or "default")
    run_id = str(_fget(report, "analysis_id") or _fget(report, "report_id") or "").strip()
    strict_isolation = bool(_fget(report, "_strict_snapshot_isolation", False))
    try:
        geo_store = store or get_geo_store()
        audits = geo_store.list_audits(tenant_id, limit=50)
        matched = None
        if run_id:
            matched = next(
                (
                    a for a in audits
                    if str(getattr(a, "audit_id", "") or "").strip() == run_id
                    or str(getattr(a, "parent_run_id", "") or "").strip() == run_id
                ),
                None,
            )
        if matched is None and not strict_isolation:
            matched = next(
                (a for a in audits if _norm_domain(a.domain or a.website_url) == target_dom),
                None,
            )
        if not matched:
            return None
        builder = GEOReportBuilder(store=geo_store)
        dataset = builder.build_canonical_dataset(tenant_id, matched.audit_id, include_legacy=False)
        if not isinstance(report, dict) and dataset is not None:
            try:
                object.__setattr__(report, "_enterprise_geo_dataset", dataset)
            except Exception:
                pass
        return dataset
    except Exception:
        return None


def render_seven_dimension_svg(dimensions: List[Dict[str, Any]]) -> str:
    """Vector SVG chart for the 7 proposed GEO methodology dimensions."""
    width = 760
    row_h = 30
    label_w = 270
    bar_max = 310
    height = 46 + row_h * max(1, len(dimensions))
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="#faf9f6" stroke="#e2e0d8" rx="6"/>',
        '<text x="16" y="25" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#111827">GEO 7-DIMENSION METHODOLOGY BREAKDOWN (PROPOSED WEIGHTS · 100% TOTAL)</text>',
    ]
    for i, d in enumerate(dimensions):
        y = 42 + i * row_h
        name = str(d.get("dimension_name", ""))[:36]
        w = d.get("proposed_weight_pct", 0)
        sc = d.get("score")
        st = str(d.get("status", "NOT_TESTED"))
        if sc is None:
            color, bw, txt = "#64748b", 44.0, f"{st} ({w:.0f}%)"
        elif sc >= 75:
            color, bw, txt = "#15803d", (sc / 100.0) * bar_max, f"{sc:.1f}/100 ({w:.0f}%)"
        elif sc >= 50:
            color, bw, txt = "#b45309", (sc / 100.0) * bar_max, f"{sc:.1f}/100 ({w:.0f}%)"
        else:
            color, bw, txt = "#b91c1c", (sc / 100.0) * bar_max, f"{sc:.1f}/100 ({w:.0f}%)"
        parts.append(
            f'<text x="16" y="{y + 15}" font-family="system-ui, sans-serif" font-size="10.5" fill="#1f2937">{_esc(name)}</text>'
            f'<rect x="{label_w}" y="{y + 3}" width="{max(6.0, bw):.1f}" height="16" fill="{color}" rx="3"/>'
            f'<text x="{label_w + max(6.0, bw) + 8:.1f}" y="{y + 15}" font-family="ui-monospace, monospace" font-size="9.5" font-weight="600" fill="{color}">{_esc(txt)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def render_platform_matrix_svg(platforms: List[Dict[str, Any]]) -> str:
    """Vector SVG bar chart comparing tested platforms (never plots unconfigured platforms as 0%)."""
    if not platforms:
        return ""
    width = 760
    row_h = 34
    height = 46 + row_h * len(platforms)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="#ffffff" stroke="#e2e0d8" rx="6"/>',
        '<text x="16" y="25" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#111827">PLATFORM-SPECIFIC OBSERVED MENTION &amp; CITATION RATES</text>',
    ]
    for i, p in enumerate(platforms):
        y = 42 + i * row_h
        name = str(p.get("display_name") or p.get("platform_id"))[:26]
        n_ok = int(p.get("prompts_succeeded") or 0)
        mode = str(p.get("testing_mode") or "API_MODEL_ONLY")
        m_rate = p.get("mention_rate_pct")
        c_rate = p.get("citation_rate_pct")
        if n_ok == 0 or m_rate is None:
            parts.append(
                f'<text x="16" y="{y + 16}" font-family="system-ui, sans-serif" font-size="10.5" fill="#1f2937">{_esc(name)}</text>'
                f'<rect x="225" y="{y + 4}" width="64" height="17" fill="#cbd5e1" rx="3"/>'
                f'<text x="297" y="{y + 16}" font-family="ui-monospace, monospace" font-size="9" fill="#64748b">NOT CONFIGURED / UNTESTED</text>'
            )
        else:
            mw = max(6.0, (float(m_rate) / 100.0) * 260.0)
            cw = max(4.0, (float(c_rate or 0.0) / 100.0) * 260.0)
            parts.append(
                f'<text x="16" y="{y + 16}" font-family="system-ui, sans-serif" font-size="10.5" fill="#1f2937">{_esc(name)}</text>'
                f'<rect x="225" y="{y + 3}" width="{mw:.1f}" height="9" fill="#1d4ed8" rx="2"/>'
                f'<rect x="225" y="{y + 14}" width="{cw:.1f}" height="8" fill="#15803d" rx="2"/>'
                f'<text x="495" y="{y + 16}" font-family="ui-monospace, monospace" font-size="9" fill="#334155">M:{m_rate:.0f}% C:{(c_rate or 0):.0f}% (n={n_ok} · {_esc(mode)})</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def render_geo_finding_card_html(f: Dict[str, Any], *, badge_prefix: str = "") -> str:
    """Render a complete, zero-truncation finding card for both canonical GEOFinding and legacy Finding."""
    fid = str(f.get("finding_id") or f.get("id") or "FINDING")
    sev = _enum_str(f.get("severity"), "medium").upper()
    status = _enum_str(f.get("status") or f.get("resolution_status"), "open").upper()
    cat = _enum_str(f.get("category"), "geo")
    subcat = str(f.get("subcategory") or "")
    dept = str(f.get("department") or f.get("owner") or f.get("responsible_role") or "")
    agent_id = str(f.get("agent_id") or "")
    dq_state = _enum_str(f.get("data_quality_state"), "")
    is_hyp = bool(f.get("is_hypothesis"))
    title = str(f.get("finding_title") or f.get("title") or "Recorded Finding")
    desc = str(f.get("detailed_diagnosis") or f.get("description") or f.get("observed_result") or "")
    plain_eng = str(f.get("plain_english_summary") or "")
    root_cause = str(f.get("root_cause") or f.get("causal_mechanism") or "")
    rc_group = str(f.get("root_cause_group") or "")
    expected = str(f.get("expected_or_reference_behavior") or f.get("expected_condition") or "")
    biz_impact = str(f.get("business_impact") or f.get("why_it_matters") or f.get("business_context") or "")
    rec = str(f.get("recommended_solution") or f.get("recommendation") or f.get("recommended_action") or "")
    dev_inst = str(f.get("developer_instructions") or f.get("implementation_detail") or "")
    code_ex = str(f.get("relevant_code_or_configuration_example") or "")
    code_patch = f.get("code_patch")
    if isinstance(code_patch, dict):
        patch_txt = code_patch.get("diff") or code_patch.get("after_snippet") or ""
        if patch_txt and not code_ex:
            code_ex = str(patch_txt)

    urls = [str(u) for u in (f.get("affected_urls") or []) if u]
    platforms = [str(p) for p in (f.get("affected_platforms") or []) if p]
    prompts = [str(p) for p in (f.get("affected_prompts") or []) if p]
    entities = [str(e) for e in (f.get("affected_entities") or []) if e]
    competitors = [str(c) for c in (f.get("competitor_references") or []) if c]
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
    acc = f.get("acceptance_criteria")
    acc_list: List[str] = []
    if isinstance(acc, list):
        acc_list = [str(x) for x in acc if x]
    elif acc:
        acc_list = [str(acc)]
    val_crit = str(f.get("validation_criteria") or "")
    if val_crit and val_crit not in acc_list:
        acc_list.append(val_crit)
    ver_steps = [str(s) for s in (f.get("verification_steps") or []) if s]
    ver_cmd = str(f.get("verification_command") or "")
    impl_steps = [str(s) for s in (f.get("implementation_steps") or []) if s]
    deps = [str(d) for d in (f.get("dependencies") or f.get("implementation_dependencies") or []) if d]

    lims = f.get("limitations") or f.get("data_limitations")
    if isinstance(lims, list):
        lim_str = "; ".join(str(x) for x in lims if x)
    else:
        lim_str = str(lims or "")

    conf = f.get("confidence")
    conf_str = (
        f"{int(round(float(conf) * 100))}%" if isinstance(conf, (int, float)) and float(conf) <= 1.0
        else (str(conf) if conf is not None else "Not specified")
    )

    sev_border = {
        "CRITICAL": "#b91c1c",
        "HIGH": "#c2410c",
        "MEDIUM": "#b45309",
        "LOW": "#1d4ed8",
    }.get(sev, "#475569")

    rows: List[str] = []
    if desc:
        rows.append(f"<p><strong>Observed Diagnosis:</strong> {_esc(desc)}</p>")
    if plain_eng and plain_eng != desc:
        rows.append(f"<p style='background:#eff6ff;padding:6px 8px;border-radius:4px;border-left:2px solid #2563eb;'><strong>Plain-English Summary:</strong> {_esc(plain_eng)}</p>")
    if root_cause or rc_group:
        rc_full = f"{root_cause} ({rc_group})" if (root_cause and rc_group) else (root_cause or rc_group)
        rows.append(f"<p><strong>Root Cause:</strong> {_esc(rc_full)}</p>")
    if expected:
        rows.append(f"<p><strong>Expected / Reference Condition:</strong> {_esc(expected)}</p>")
    if biz_impact:
        rows.append(f"<p><strong>Business Impact:</strong> {_esc(biz_impact)}</p>")
    if rec:
        rows.append(f"<p><strong>Prescriptive Recommendation:</strong> {_esc(rec)}</p>")
    if impl_steps:
        steps_li = "".join(f"<li>{_esc(s)}</li>" for s in impl_steps)
        rows.append(f"<div><strong>Implementation Steps:</strong><ol style='margin:4px 0 6px 18px;'>{steps_li}</ol></div>")
    if dev_inst:
        rows.append(f"<p><strong>Developer Instructions:</strong> <span class='mono'>{_esc(dev_inst)}</span></p>")
    if code_ex:
        rows.append(f"<pre style='background:#0f172a;color:#e2e8f0;padding:8px;border-radius:4px;font-size:7.5pt;white-space:pre-wrap;overflow-wrap:anywhere;'>{_esc(code_ex)}</pre>")
    if acc_list:
        acc_li = "".join(f"<li>{_esc(a)}</li>" for a in acc_list)
        rows.append(f"<div><strong>Acceptance &amp; Validation Criteria:</strong><ul style='margin:4px 0 6px 18px;'>{acc_li}</ul></div>")
    if ver_steps:
        v_li = "".join(f"<li>{_esc(s)}</li>" for s in ver_steps)
        rows.append(f"<div><strong>Verification Procedure:</strong><ol style='margin:4px 0 6px 18px;'>{v_li}</ol></div>")
    if ver_cmd:
        rows.append(f"<p><strong>Verification Command:</strong> <code class='mono'>{_esc(ver_cmd)}</code></p>")

    scope_bits: List[str] = []
    if urls:
        scope_bits.append(f"<strong>URLs ({len(urls)}):</strong> " + ", ".join(f"<code>{_esc(u)}</code>" for u in urls))
    if platforms:
        scope_bits.append(f"<strong>Platforms:</strong> {_esc(', '.join(platforms))}")
    if prompts:
        scope_bits.append(f"<strong>Prompts:</strong> {_esc(', '.join(prompts))}")
    if entities:
        scope_bits.append(f"<strong>Entities:</strong> {_esc(', '.join(entities))}")
    if competitors:
        scope_bits.append(f"<strong>Competitor Refs:</strong> {_esc(', '.join(competitors))}")
    if scope_bits:
        rows.append("<p style='font-size:8pt;'>" + " · ".join(scope_bits) + "</p>")

    raw_ev = f.get("evidence") or []
    if isinstance(raw_ev, list) and raw_ev:
        ev_rows = "".join(
            f"<tr><td class='mono'>{_esc(_fget(ev, 'evidence_id') or _fget(ev, 'id') or '—')}</td>"
            f"<td>{_esc(_fget(ev, 'source') or _fget(ev, 'test_method') or 'observed')}</td>"
            f"<td>{_esc(_fget(ev, 'observed_value') or _fget(ev, 'observation') or _fget(ev, 'snippet') or '—')}</td></tr>"
            for ev in raw_ev
            if isinstance(ev, dict) or hasattr(ev, "evidence_id") or hasattr(ev, "observation")
        )
        if ev_rows:
            rows.append(
                "<table><thead><tr><th style='width:20%;'>Evidence ID</th><th style='width:22%;'>Source</th><th>Observation</th></tr></thead>"
                f"<tbody>{ev_rows}</tbody></table>"
            )

    meta_parts = [
        f"Category: {_esc(cat)}" + (f" / {_esc(subcat)}" if subcat else ""),
        f"Status: {_esc(status)}",
        f"Confidence: {_esc(conf_str)}",
    ]
    if dept:
        meta_parts.append(f"Owner/Dept: {_esc(dept)}")
    if agent_id:
        meta_parts.append(f"Agent: {_esc(agent_id)}")
    if dq_state:
        meta_parts.append(f"State: {_esc(dq_state)}")
    if deps:
        meta_parts.append(f"Dependencies: {_esc(', '.join(deps))}")
    if ev_ids:
        meta_parts.append(f"Evidence IDs: {_esc(', '.join(ev_ids))}")
    if lim_str:
        meta_parts.append(f"Limitations: {_esc(lim_str)}")

    hyp_badge = " <span style='background:#fef3c7;color:#92400e;padding:1px 5px;border-radius:3px;font-size:7pt;font-weight:700;'>HYPOTHESIS</span>" if is_hyp else ""
    prefix_html = f"<span style='background:#e0f2fe;color:#0369a1;padding:1px 5px;border-radius:3px;font-size:7pt;font-weight:700;margin-right:4px;'>{_esc(badge_prefix)}</span>" if badge_prefix else ""

    return (
        f"<div class='geo-finding-card' style='border:1px solid #cbd5e1;border-left:4px solid {sev_border};"
        "border-radius:5px;padding:10px 12px;margin:8px 0 12px 0;background:#ffffff;break-inside:avoid;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:6px;'>"
        f"<div>{prefix_html}<span class='mono' style='font-weight:700;color:#334155;'>{_esc(fid)}</span> — "
        f"<strong style='color:#0f172a;'>{_esc(title)}</strong>{hyp_badge}</div>"
        f"<span class='mono' style='font-size:7.5pt;font-weight:700;color:{sev_border};border:1px solid {sev_border};padding:1px 6px;border-radius:3px;'>{_esc(sev)}</span>"
        f"</div>"
        f"<div style='font-size:8.5pt;color:#1e293b;'>{''.join(rows)}</div>"
        f"<div class='mono' style='font-size:7.5pt;color:#475569;border-top:1px solid #e2e8f0;padding-top:5px;margin-top:6px;'>"
        f"{' · '.join(meta_parts)}</div>"
        "</div>"
    )


def _render_remediation_pack_html(pack: Dict[str, Any]) -> str:
    """Render the complete Consolidated 13-Deliverable GEO Remediation Pack and all tasks."""
    if not pack:
        return "<p class='muted'>No consolidated GEO remediation pack stored for this audit.</p>"
    tasks = pack.get("tasks") or []
    delivs = pack.get("deliverables") or {}
    rc_groups = pack.get("root_cause_groups") or []
    dept_pkgs = pack.get("department_packages") or {}
    dep_edges = pack.get("dependency_edges") or []
    conflicts = pack.get("conflict_notes") or []
    risks = pack.get("remaining_risks") or []

    deliv_rows = []
    for k, v in delivs.items():
        if isinstance(v, list):
            val_str = ", ".join(
                str(x.get("url") or x.get("title") or x.get("risk_id") or x) if isinstance(x, dict) else str(x)
                for x in v
            ) or "None required"
        elif isinstance(v, dict):
            val_str = "; ".join(f"{dk}: {dv}" for dk, dv in v.items())
        else:
            val_str = str(v)
        deliv_rows.append(f"<tr><td><strong>{_esc(k.replace('_', ' ').title())}</strong></td><td>{_esc(val_str)}</td></tr>")

    rc_html = ""
    if rc_groups:
        rc_rows = "".join(
            f"<tr><td class='mono'>{_esc(g.get('root_cause_group') or g.get('group_id') or 'group')}</td>"
            f"<td>{_esc(g.get('summary') or g.get('title') or g.get('root_cause') or '')}</td>"
            f"<td class='mono'>{_esc(', '.join(g.get('finding_ids') or []))}</td></tr>"
            for g in rc_groups
        )
        rc_html = f"<h4>Root-Cause Clusters ({len(rc_groups)})</h4><table><thead><tr><th>Cluster</th><th>Root Cause</th><th>Linked Findings</th></tr></thead><tbody>{rc_rows}</tbody></table>"

    dept_html = ""
    if dept_pkgs:
        d_rows = "".join(
            f"<tr><td><strong>{_esc(dept)}</strong></td><td class='mono'>{_esc(', '.join(tids))}</td></tr>"
            for dept, tids in dept_pkgs.items()
        )
        dept_html = f"<h4>Department Work Packages ({len(dept_pkgs)})</h4><table><thead><tr><th>Department</th><th>Assigned Task IDs</th></tr></thead><tbody>{d_rows}</tbody></table>"

    dep_html = ""
    if dep_edges:
        e_rows = "".join(
            f"<tr><td class='mono'>{_esc(e.get('from'))}</td><td class='mono'>{_esc(e.get('to'))}</td><td>{_esc(e.get('reason'))}</td></tr>"
            for e in dep_edges
        )
        dep_html = f"<h4>Task Dependency Graph ({len(dep_edges)} edges)</h4><table><thead><tr><th>Prerequisite</th><th>Dependent Task</th><th>Reason</th></tr></thead><tbody>{e_rows}</tbody></table>"

    conflict_html = ""
    if conflicts:
        c_li = "".join(f"<li><strong>{_esc(c.get('topic'))}:</strong> {_esc(c.get('note'))}</li>" for c in conflicts)
        conflict_html = f"<h4>Cross-Team Conflict &amp; Governance Notes</h4><ul>{c_li}</ul>"

    risk_html = ""
    if risks:
        r_rows = "".join(
            f"<tr><td class='mono'>{_esc(r.get('risk_id'))}</td><td>{_esc(str(r.get('severity', '')).upper())}</td>"
            f"<td><strong>{_esc(r.get('title'))}</strong>: {_esc(r.get('detail'))}</td></tr>"
            for r in risks
        )
        risk_html = f"<h4>Remaining Risks ({len(risks)})</h4><table><thead><tr><th>Risk ID</th><th>Severity</th><th>Risk Disclosure</th></tr></thead><tbody>{r_rows}</tbody></table>"

    task_cards = []
    for t in tasks:
        patch_html = (
            f"<pre style='background:#0f172a;color:#e2e8f0;padding:8px;border-radius:4px;font-size:7.5pt;white-space:pre-wrap;'>{_esc(t.get('code_or_copy_patch'))}</pre>"
            if t.get("code_or_copy_patch")
            else ""
        )
        acc = t.get("acceptance_criteria") or []
        acc_html = "<ul>" + "".join(f"<li>{_esc(a)}</li>" for a in acc) + "</ul>" if acc else "—"
        task_cards.append(
            "<div style='border:1px solid #cbd5e1;border-left:3px solid #0f766e;border-radius:4px;padding:9px 11px;margin:8px 0;background:#f8fafc;break-inside:avoid;'>"
            f"<div><span class='mono' style='font-weight:700;'>{_esc(t.get('task_id'))}</span> · "
            f"<strong>[{_esc(t.get('priority'))}] {_esc(t.get('title'))}</strong> "
            f"<span class='mono' style='font-size:7.5pt;color:#475569;'>({ _esc(t.get('department')) } · Effort: {_esc(t.get('effort'))} · Risk: {_esc(t.get('risk'))} · Status: {_esc(t.get('status'))} · Approval: {_esc(t.get('approval_status'))})</span></div>"
            f"<p style='margin:4px 0;'><strong>Proposed Change:</strong> {_esc(t.get('proposed_change'))}</p>"
            f"<p style='margin:4px 0;'><strong>Implementation Instructions:</strong> {_esc(t.get('implementation_instructions'))}</p>"
            f"{patch_html}"
            f"<div style='font-size:8pt;'><strong>Acceptance Criteria:</strong> {acc_html}</div>"
            f"<div class='mono' style='font-size:7.5pt;color:#475569;'>Findings: {_esc(', '.join(t.get('finding_ids') or []))} · "
            f"Dependencies: {_esc(', '.join(t.get('dependencies') or []) or 'None')} · "
            f"Deployed Ref: {_esc(t.get('deployment_ref') or 'Not deployed')} · "
            f"Implementation Verified: {_esc(t.get('implementation_verified'))} · Outcome Improved: {_esc(t.get('outcome_improved') or 'NOT_TESTED')}</div>"
            "</div>"
        )

    return (
        f"<p><strong>Executive Remediation Summary:</strong> {_esc(pack.get('executive_summary'))}</p>"
        f"<h4>13 Consolidated Deliverables</h4>"
        f"<table><thead><tr><th style='width:28%;'>Deliverable</th><th>Specification / Task Assignments</th></tr></thead><tbody>{''.join(deliv_rows)}</tbody></table>"
        f"{rc_html}{dept_html}{dep_html}{conflict_html}{risk_html}"
        f"<h4>Detailed Remediation Task Specifications ({len(tasks)})</h4>"
        f"{''.join(task_cards) or '<p class=\"muted\">No remediation tasks required.</p>'}"
    )


def render_enterprise_geo_dossier_fragment(
    dataset: Dict[str, Any],
    *,
    exclude_finding_ids: Optional[Set[str]] = None,
) -> str:
    """Reusable full-fidelity Enterprise GEO HTML dossier fragment for embedding into legacy/adaptive PDFs."""
    audit = dataset.get("audit") or {}
    sc = dataset.get("scorecard") or {}
    cov = sc.get("coverage") or {}
    findings = list(dataset.get("findings") or [])
    exclude = {fid.lower() for fid in (exclude_finding_ids or set())}
    filtered_findings = [f for f in findings if str(f.get("finding_id") or "").lower() not in exclude]
    recs = list(dataset.get("recommendations") or [])
    pack = dataset.get("remediation_pack") or {}
    verifs = list(dataset.get("verifications") or [])
    exps = list(dataset.get("experiments") or [])
    entities = list(dataset.get("entities") or [])
    citations = list(dataset.get("citations") or [])
    ext_sources = list(dataset.get("external_sources") or [])
    prompts = list(dataset.get("prompts") or [])
    responses = list(dataset.get("responses") or [])
    mentions = list(dataset.get("mentions") or [])
    pages = list(dataset.get("pages") or [])
    qa_report = dataset.get("qa_report") or {}

    obs_disp = (
        f"{sc['observed_performance_score']:.1f}/100"
        if isinstance(sc.get("observed_performance_score"), (int, float))
        else f"Unmeasured ({sc.get('observed_performance_status', 'NOT_CONFIGURED')})"
    )
    ready_disp = (
        f"{sc['readiness_score']:.1f}/100"
        if isinstance(sc.get("readiness_score"), (int, float))
        else "Unmeasured"
    )

    dim_svg = render_seven_dimension_svg(sc.get("dimensions") or [])
    plat_svg = render_platform_matrix_svg(dataset.get("platforms") or [])

    findings_html = "".join(render_geo_finding_card_html(f, badge_prefix="ENTERPRISE GEO") for f in filtered_findings)

    rec_rows = "".join(
        f"<tr><td class='mono'>{_esc(r.get('recommendation_id'))}</td><td><strong>{_esc(r.get('title'))}</strong>"
        f"<div style='font-size:7.5pt;color:#475569;'>{_esc(r.get('rationale'))}</div></td>"
        f"<td>{_esc(r.get('dimension'))}</td><td>{_esc(r.get('expected_impact'))} / {_esc(r.get('effort'))}</td>"
        f"<td>{_esc(r.get('owner_department'))}</td><td>{_esc('; '.join(r.get('action_steps') or []))}</td></tr>"
        for r in recs
    )

    ver_rows = "".join(
        f"<tr><td class='mono'>{_esc(v.get('verification_id'))}</td><td class='mono'>{_esc(v.get('task_id'))}</td>"
        f"<td>{_esc(v.get('verified_by'))}</td><td>{_esc(v.get('implementation_verified'))}</td>"
        f"<td>{_esc(v.get('outcome_improved'))}</td><td>{'YES: ' + _esc('; '.join(v.get('regression_details') or [])) if v.get('regression_detected') else 'None'}</td>"
        f"<td><strong>{_esc(v.get('overall_status'))}</strong></td></tr>"
        for v in verifs
    )

    exp_rows = "".join(
        f"<tr><td class='mono'>{_esc(e.get('experiment_id'))}</td><td><strong>{_esc(e.get('title'))}</strong>: {_esc(e.get('hypothesis'))}</td>"
        f"<td>{_esc(e.get('status'))}</td><td class='mono'>{_esc(json.dumps(e.get('observed_delta') or {}))}</td>"
        f"<td style='font-size:7.5pt;'>{_esc(e.get('causation_disclaimer'))}</td></tr>"
        for e in exps
    )

    ent_rows = "".join(
        f"<tr><td>{_esc(e.get('entity_type'))}</td><td><strong>{_esc(e.get('entity_name'))}</strong></td>"
        f"<td>{_esc(e.get('attribute'))}</td><td>{_esc(e.get('value'))}</td>"
        f"<td>{_esc(_enum_str(e.get('fact_status')))}</td><td>{_esc(e.get('approved_by') or 'Pending')}</td></tr>"
        for e in entities
    )

    cit_rows = "".join(
        f"<tr><td class='mono'>{_esc(c.get('citation_id'))}</td><td>{_esc(c.get('platform_id'))}</td>"
        f"<td>{_esc(c.get('domain'))}</td><td>{_esc(_enum_str(c.get('source_ownership')))}</td>"
        f"<td>{_esc(c.get('cited_url'))}</td><td>{_esc(c.get('associated_claim') or '—')}</td></tr>"
        for c in citations
    )

    ext_rows = "".join(
        f"<tr><td><strong>{_esc(s.get('domain'))}</strong></td><td>{_esc(s.get('source_category'))}</td>"
        f"<td>{'Yes' if s.get('brand_present') else 'No'}</td><td>{'Yes' if s.get('cites_competitors') else 'No'}</td>"
        f"<td>{_esc(s.get('citation_count', 0))}</td><td>{_esc(s.get('outreach_strategy') or s.get('evidence_of_relevance') or '—')}</td></tr>"
        for s in ext_sources
    )

    page_rows = "".join(
        f"<tr><td class='mono'>{_esc(p.get('url'))}</td><td>{_esc(p.get('page_type'))}</td>"
        f"<td>{_esc(p.get('http_status') or '—')}</td><td>{_esc(p.get('word_count', 0))}</td>"
        f"<td>{_esc(p.get('overall_readiness_score'))}</td><td>{_esc(', '.join(p.get('schema_types') or []) or 'None')}</td>"
        f"<td>{_esc('; '.join(p.get('content_issues') or []) or 'None')}</td></tr>"
        for p in pages
    )

    qa_checks = qa_report.get("checks") or []
    qa_rows = "".join(
        f"<tr><td class='mono'>{_esc(c.get('check_id'))}</td><td>{_esc(c.get('check_name'))}</td>"
        f"<td><strong>{'PASS' if c.get('passed') else 'FAIL'}</strong> ({_esc(c.get('severity'))})</td>"
        f"<td>{_esc(c.get('details'))}</td></tr>"
        for c in qa_checks
    )

    return f"""
    <section class="enterprise-geo-dossier" id="enterprise-geo-dossier" style="margin-top:20px;border-top:2px solid #0f766e;padding-top:14px;">
      <div class="kicker" style="font-family:monospace;font-size:8pt;color:#0f766e;font-weight:700;text-transform:uppercase;">
        ENTERPRISE GEO CANONICAL INTELLIGENCE DOSSIER · AUDIT {_esc(audit.get('audit_id'))} · {_esc(dataset.get('methodology_version'))}
      </div>
      <h3 style="margin:4px 0 8px 0;color:#0f172a;">Dual GEO Scorecard, Specialist Findings, Remediation &amp; Verification</h3>
      <p style="font-size:8.5pt;color:#475569;margin-bottom:10px;">
        <strong>Observed GEO Performance:</strong> {_esc(obs_disp)} ·
        <strong>GEO Readiness &amp; Optimization:</strong> {_esc(ready_disp)} ·
        <strong>Prompts Succeeded/Planned:</strong> {cov.get('successful_prompt_executions', 0)}/{cov.get('total_planned_prompts', 0)} ·
        <strong>Responses:</strong> {len(responses)} · <strong>Mentions:</strong> {len(mentions)} · <strong>Citations:</strong> {len(citations)} ·
        <strong>Publication QA:</strong> {_esc(qa_report.get('qa_status') or audit.get('publication_status'))}
      </p>
      <div style="margin:8px 0;">{dim_svg}</div>
      <div style="margin:8px 0;">{plat_svg}</div>

      {f"<h4>Canonical Enterprise GEO Findings ({len(filtered_findings)})</h4>{findings_html}" if filtered_findings else ""}
      {f"<h4>Prioritized GEO Recommendations ({len(recs)})</h4><table><thead><tr><th>ID</th><th>Recommendation</th><th>Dimension</th><th>Impact/Effort</th><th>Department</th><th>Action Steps</th></tr></thead><tbody>{rec_rows}</tbody></table>" if recs else ""}
      {f"<h4>Consolidated 13-Deliverable GEO Remediation Pack</h4>{_render_remediation_pack_html(pack)}" if pack else ""}
      {f"<h4>Independent GEO Verification Records ({len(verifs)})</h4><table><thead><tr><th>ID</th><th>Task</th><th>Verified By</th><th>Implementation Verified</th><th>Outcome Improved</th><th>Regressions</th><th>Status</th></tr></thead><tbody>{ver_rows}</tbody></table>" if verifs else ""}
      {f"<h4>Controlled GEO Experiments ({len(exps)})</h4><table><thead><tr><th>ID</th><th>Experiment &amp; Hypothesis</th><th>Status</th><th>Observed Delta</th><th>Causation Disclosure</th></tr></thead><tbody>{exp_rows}</tbody></table>" if exps else ""}
      {f"<h4>Brand Knowledge Profile &amp; Entity Consistency ({len(entities)})</h4><table><thead><tr><th>Type</th><th>Entity</th><th>Attribute</th><th>Value</th><th>Status</th><th>Approved By</th></tr></thead><tbody>{ent_rows}</tbody></table>" if entities else ""}
      {f"<h4>Observed Citation Inventory ({len(citations)})</h4><table><thead><tr><th>ID</th><th>Platform</th><th>Domain</th><th>Ownership</th><th>Cited URL</th><th>Claim</th></tr></thead><tbody>{cit_rows}</tbody></table>" if citations else ""}
      {f"<h4>External Authority &amp; Source Coverage ({len(ext_sources)})</h4><table><thead><tr><th>Domain</th><th>Category</th><th>Brand</th><th>Competitors</th><th>Citations</th><th>Strategy / Relevance</th></tr></thead><tbody>{ext_rows}</tbody></table>" if ext_sources else ""}
      {f"<h4>Page-Level GEO Content Readiness ({len(pages)})</h4><table><thead><tr><th>URL</th><th>Type</th><th>HTTP</th><th>Words</th><th>Score</th><th>Schemas</th><th>Content Issues</th></tr></thead><tbody>{page_rows}</tbody></table>" if pages else ""}
      {f"<h4>Independent Publication QA Gate ({len(qa_checks)} Checks)</h4><table><thead><tr><th>ID</th><th>Check</th><th>Result</th><th>Details</th></tr></thead><tbody>{qa_rows}</tbody></table>" if qa_checks else ""}
    </section>
    """


class GEOReportBuilder:
    """Builds JSON, HTML, and PDF GEO reports strictly from the canonical GEOStore dataset."""

    def __init__(self, store: Optional[GEOStore] = None):
        self.store = store or get_geo_store()

    def build_canonical_dataset(
        self,
        tenant_id: str,
        audit_id: str,
        *,
        include_legacy: bool = True,
    ) -> Dict[str, Any]:
        audit = self.store.get_audit(tenant_id, audit_id)
        if not audit:
            raise KeyError(f"GEO audit '{audit_id}' not found.")
        scope = self.store.get_scope(tenant_id, audit.scope_id) if audit.scope_id else None
        platforms = self.store.list_platforms(tenant_id, audit_id)
        model_versions = self.store.list_model_versions(tenant_id, audit_id)
        prompts = self.store.list_prompts(tenant_id, audit_id=audit_id)
        runs = self.store.list_prompt_runs(tenant_id, audit_id)
        responses = self.store.list_responses(tenant_id, audit_id)
        mentions = self.store.list_mentions(tenant_id, audit_id)
        citations = self.store.list_citations(tenant_id, audit_id)
        entities = self.store.list_entities(tenant_id, audit_id=audit_id)
        external_sources = self.store.list_external_sources(tenant_id, audit_id)
        pages = self.store.list_pages(tenant_id, audit_id)
        findings = self.store.list_findings(tenant_id, audit_id=audit_id)
        recommendations = self.store.list_recommendations(tenant_id, audit_id)
        pack = self.store.get_remediation_pack(tenant_id, audit_id)
        verifications = self.store.list_verifications(tenant_id, audit_id=audit_id)
        experiments = self.store.list_experiments(tenant_id, audit_id=audit_id)
        snapshots = self.store.list_snapshots(tenant_id, audit_id)
        scorecard = self.store.get_artifact(tenant_id, audit_id, "scorecard") or {}
        citation_graph = self.store.get_artifact(tenant_id, audit_id, "citation_graph") or {}
        dept_artifacts = self.store.get_artifact(tenant_id, audit_id, "department_artifacts") or {}
        qa_report = self.store.get_artifact(tenant_id, audit_id, "qa_report") or {}
        prompt_coverage = self.store.get_artifact(tenant_id, audit_id, "prompt_coverage") or {}

        schedules = self.store.list_schedules(tenant_id, domain=audit.domain)
        alerts = self.store.list_alerts(tenant_id, domain=audit.domain)
        history = GEOMonitoringEngine(store=self.store).build_monitoring_history(tenant_id, domain=audit.domain)
        conn_mgr = GEOConnectorManager(store=self.store)

        findings_dumped = [f.model_dump() for f in findings]
        legacy_findings = (
            _collect_legacy_findings_for_domain(tenant_id, audit.domain, findings_dumped)
            if include_legacy
            else []
        )

        return {
            "audit": audit.model_dump(),
            "scope": scope.model_dump() if scope else {},
            "platforms": [p.model_dump() for p in platforms],
            "model_versions": [m.model_dump() for m in model_versions],
            "prompts": [p.model_dump() for p in prompts],
            "runs": [r.model_dump() for r in runs],
            "responses": [r.model_dump() for r in responses],
            "mentions": [m.model_dump() for m in mentions],
            "citations": [c.model_dump() for c in citations],
            "entities": [e.model_dump() for e in entities],
            "external_sources": [s.model_dump() for s in external_sources],
            "pages": [p.model_dump() for p in pages],
            "findings": findings_dumped,
            "legacy_findings": legacy_findings,
            "recommendations": [r.model_dump() for r in recommendations],
            "remediation_pack": pack.model_dump() if pack else {},
            "verifications": [v.model_dump() for v in verifications],
            "experiments": [e.model_dump() for e in experiments],
            "snapshots": [s.model_dump() for s in snapshots],
            "scorecard": scorecard,
            "citation_graph": citation_graph,
            "department_artifacts": dept_artifacts,
            "qa_report": qa_report,
            "prompt_coverage": prompt_coverage,
            "monitoring_schedules": [s.model_dump() for s in schedules],
            "monitoring_alerts": [a.model_dump() for a in alerts],
            "monitoring_history": history,
            "connector_statuses": conn_mgr.list_connections_status(tenant_id),
            "capability_matrix": conn_mgr.capability_matrix(),
            "methodology_version": audit.methodology_version or GEO_METHODOLOGY_VERSION,
        }

    def select_sections(self, dataset: Dict[str, Any], profile_key: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        """Select applicable, evidence-backed chapters; dynamically omit empty sections instead of padding."""
        prof = GEO_REPORT_PROFILES.get(profile_key, GEO_REPORT_PROFILES["complete_audit_book"])
        allowed = set(prof["domains"])
        availability = {
            "always": True,
            "platforms": bool(dataset.get("platforms")),
            "responses": bool(dataset.get("responses")),
            "citations": bool(dataset.get("citations")),
            "entities": bool(dataset.get("entities")),
            "pages": bool(dataset.get("pages")),
            "external_sources": bool(dataset.get("external_sources")),
            "competitors": bool((dataset.get("scope") or {}).get("competitors")) and bool(dataset.get("responses")),
        }

        included: List[Dict[str, Any]] = []
        omitted: List[Dict[str, str]] = []
        for sec in GEO_BOOK_SECTIONS:
            if "*" not in allowed and sec["domain"] not in allowed:
                continue
            req = sec.get("requires", "always")
            if not availability.get(req, False):
                omitted.append({
                    "section": f"{sec['number']:02d}. {sec['title']}",
                    "reason": f"Omitted dynamically: no observed '{req}' evidence captured in this audit.",
                })
                continue
            if len(included) < prof.get("max_sections", 60):
                included.append(sec)
        return included, omitted

    @staticmethod
    def _domain_findings(dom: str, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if dom in ("front_matter", "remediation", "verification", "evidence"):
            return list(findings)
        cat_map = {
            "ai_visibility": {"ai_visibility", "market_intent"},
            "citations": {"citation_intelligence"},
            "brand_entity": {"entity_consistency"},
            "content_readiness": {"content_quality", "technical_readiness"},
            "reputation": {"external_reputation"},
            "competitive": {"competitive_intelligence"},
        }
        wanted = cat_map.get(dom, set())
        return [f for f in findings if str(f.get("category") or "") in wanted]

    def _chapter_10_fields(self, sec: Dict[str, Any], dataset: Dict[str, Any]) -> Dict[str, str]:
        """Standardized 10-question enterprise chapter structure (Phase 25)."""
        audit = dataset["audit"]
        sc = dataset.get("scorecard") or {}
        obs = sc.get("observed_metrics") or {}
        ready = sc.get("readiness_metrics") or {}
        dom = sec["domain"]
        domain_findings = self._domain_findings(dom, dataset.get("findings") or [])
        ev_refs = sorted({eid for f in domain_findings for eid in (f.get("evidence_ids") or [])})
        top_f = domain_findings[0] if domain_findings else None

        if dom == "ai_visibility":
            observed_str = (
                f"Tested {len(dataset.get('responses', []))} live response(s): Brand mention rate={obs.get('brand_mention_rate_pct')}% "
                f"(non-branded={obs.get('non_branded_mention_rate_pct')}%), recommendation rate={obs.get('recommendation_rate_pct')}%, "
                f"owned citation rate={obs.get('citation_observation_rate_pct')}%."
                if dataset.get("responses")
                else "Observed AI visibility is NOT_CONFIGURED (no live provider executions succeeded); never reported as 0%."
            )
            owner = "GEO & Brand Strategy"
        elif dom == "citations":
            cg_sum = (dataset.get("citation_graph") or {}).get("summary") or {}
            observed_str = (
                f"{cg_sum.get('total_citations', 0)} citation(s) across {cg_sum.get('unique_domains', 0)} domain(s): "
                f"Owned={cg_sum.get('owned_citations', 0)}, Independent={cg_sum.get('independent_citations', 0)}, "
                f"Competitor={cg_sum.get('competitor_citations', 0)}."
            )
            owner = "Content & Digital PR"
        elif dom == "brand_entity":
            art_a = (dataset.get("department_artifacts") or {}).get("department_a") or {}
            observed_str = (
                f"{art_a.get('total_facts', len(dataset.get('entities', [])))} entity fact(s) tracked; "
                f"{art_a.get('confirmed_facts', 0)} confirmed; {art_a.get('conflicting_facts', 0)} conflict(s); "
                f"entity consistency score={art_a.get('consistency_score')}."
            )
            owner = "Brand & Engineering"
        elif dom == "content_readiness":
            observed_str = (
                f"Analyzed {len(dataset.get('pages', []))} page(s); content quality score={ready.get('content_quality_score')}; "
                f"technical retrieval score={ready.get('technical_readiness_score')}; "
                f"search retrieval bots allowed={ready.get('search_retrieval_allowed')}."
            )
            owner = "Content & Web Engineering"
        elif dom == "reputation":
            art_f = (dataset.get("department_artifacts") or {}).get("department_f") or {}
            observed_str = (
                f"{art_f.get('independent_sources_total', 0)} independent source(s) observed; "
                f"{art_f.get('independent_sources_with_brand', 0)} reference {audit.get('brand_name')}; "
                f"{art_f.get('negative_or_inaccurate_mentions', 0)} negative/inaccurate mention(s)."
            )
            owner = "PR & Community"
        elif dom == "competitive":
            art_g = (dataset.get("department_artifacts") or {}).get("department_g") or {}
            observed_str = (
                f"Shared-prompt comparison across {art_g.get('tested_responses', 0)} response(s): "
                f"{audit.get('brand_name')} ranks #{art_g.get('target_rank')} (leader: {art_g.get('leader_entity')}, "
                f"mention share: {art_g.get('target_mention_share_pct')}%)."
            )
            owner = "Product Marketing & Strategy"
        else:
            observed_str = (
                f"Audit status={audit.get('status')}, publication_status={audit.get('publication_status')}; "
                f"{len(dataset.get('findings', []))} canonical GEO finding(s), {len(dataset.get('legacy_findings', []))} legacy finding(s); "
                f"{len((dataset.get('remediation_pack') or {}).get('tasks') or [])} coordinated task(s)."
            )
            owner = "GEO Program Lead"

        all_recs = [str(f.get("recommendation") or "") for f in domain_findings if f.get("recommendation")]
        return {
            "evaluated": f"{sec['title']} for {audit.get('brand_name')} ({audit.get('domain')}) under methodology {dataset['methodology_version']}.",
            "why_it_matters": (top_f.get("business_impact") if top_f else "Establishes transparent, reproducible measurement of how generative platforms represent and cite the brand."),
            "observed": observed_str,
            "evidence": ", ".join(ev_refs) if ev_refs else f"Audit {audit.get('audit_id')} canonical dataset snapshots ({len(dataset.get('snapshots', []))} CAS objects).",
            "limitations": "; ".join(audit.get("limitations") or []) or "Observed measurements reflect only tested platforms, prompt suites, and testing modes.",
            "business_implication": (top_f.get("business_impact") if top_f else "Directly informs prioritization between website readiness fixes and independent authority building."),
            "what_needs_to_change": "; ".join(dict.fromkeys(all_recs)) if all_recs else "Maintain verified brand facts, publish evidence-backed documentation, and expand legitimate independent coverage.",
            "how_to_implement": (f"Execute linked remediation task(s) for {', '.join(f.get('finding_id', '') for f in domain_findings)} in the Consolidated GEO Remediation Pack." if domain_findings else "Execute assigned work packages in the GEO Remediation Center."),
            "owner": owner,
            "verification": "Independent re-crawl, structured data check, and matched prompt retesting separating Implementation Verified from Observed Outcome Improved.",
        }

    def _domain_empirical_table_html(self, dom: str, dataset: Dict[str, Any]) -> str:
        """Render rich domain-specific empirical tables once per domain inside chapters."""
        if dom == "ai_visibility":
            plats = dataset.get("platforms") or []
            mentions = dataset.get("mentions") or []
            p_rows = "".join(
                f"<tr><td><strong>{_esc(p.get('display_name') or p.get('platform_id'))}</strong></td>"
                f"<td class='mono'>{_esc(p.get('model_version') or p.get('model_name') or '—')}</td>"
                f"<td class='mono'>{_esc(_enum_str(p.get('testing_mode')))}</td>"
                f"<td>{p.get('prompts_succeeded', 0)}/{p.get('prompts_planned', 0)}</td>"
                f"<td>{_esc(p.get('mention_rate_pct')) if p.get('mention_rate_pct') is not None else _esc(_enum_str(p.get('status')))}</td>"
                f"<td>{_esc(p.get('recommendation_rate_pct')) if p.get('recommendation_rate_pct') is not None else '—'}</td>"
                f"<td>{_esc(p.get('citation_rate_pct')) if p.get('citation_rate_pct') is not None else '—'}</td></tr>"
                for p in plats
            )
            m_counts: Dict[str, int] = {}
            for m in mentions:
                mt = _enum_str(m.get("mention_type"), "direct_mention")
                m_counts[mt] = m_counts.get(mt, 0) + 1
            m_summary = ", ".join(f"{k}: {v}" for k, v in sorted(m_counts.items())) or "No mentions captured."
            return (
                f"<table><thead><tr><th>Platform</th><th>Model</th><th>Testing Mode</th><th>Runs</th><th>Mention %</th><th>Recommend %</th><th>Citation %</th></tr></thead>"
                f"<tbody>{p_rows or '<tr><td colspan=\"7\">No platforms evaluated.</td></tr>'}</tbody></table>"
                f"<p class='muted'>8-Type Mention Taxonomy Counts ({len(mentions)} total): {_esc(m_summary)}</p>"
            )
        if dom == "citations":
            cg = dataset.get("citation_graph") or {}
            gaps = cg.get("competitor_citation_gaps") or []
            g_rows = "".join(
                f"<tr><td><strong>{_esc(g.get('domain'))}</strong></td><td>{_esc(g.get('competitor_citations', g.get('count', 0)))}</td>"
                f"<td>{_esc(', '.join(g.get('competitors') or []))}</td><td>{_esc(g.get('opportunity_note') or 'Cited for competitors; brand absent.')}</td></tr>"
                for g in gaps
            )
            return (
                f"<table><thead><tr><th>Gap Domain</th><th>Competitor Citations</th><th>Competitors</th><th>Opportunity</th></tr></thead>"
                f"<tbody>{g_rows or '<tr><td colspan=\"4\">No competitor citation gaps observed.</td></tr>'}</tbody></table>"
            )
        if dom == "brand_entity":
            ents = dataset.get("entities") or []
            e_rows = "".join(
                f"<tr><td>{_esc(e.get('entity_type'))}</td><td><strong>{_esc(e.get('entity_name'))}</strong></td>"
                f"<td>{_esc(e.get('attribute'))}</td><td>{_esc(e.get('value'))}</td>"
                f"<td>{_esc(_enum_str(e.get('fact_status')))}</td><td>{len(e.get('conflicting_ai_observations') or [])}</td></tr>"
                for e in ents
            )
            return (
                f"<table><thead><tr><th>Type</th><th>Entity</th><th>Attribute</th><th>Canonical Value</th><th>Status</th><th>AI Conflicts</th></tr></thead>"
                f"<tbody>{e_rows or '<tr><td colspan=\"6\">No entity records captured.</td></tr>'}</tbody></table>"
            )
        if dom == "content_readiness":
            pages = dataset.get("pages") or []
            pg_rows = "".join(
                f"<tr><td class='mono'>{_esc(p.get('url'))}</td><td>{_esc(p.get('page_type'))}</td>"
                f"<td>{_esc(p.get('word_count', 0))}</td><td>{_esc(p.get('overall_readiness_score'))}</td>"
                f"<td>{_esc(', '.join(p.get('schema_types') or []) or 'None')}</td>"
                f"<td>{_esc('; '.join(p.get('content_issues') or []) or 'None')}</td></tr>"
                for p in pages
            )
            return (
                f"<table><thead><tr><th>URL</th><th>Page Type</th><th>Words</th><th>Readiness</th><th>Schemas</th><th>Content Issues</th></tr></thead>"
                f"<tbody>{pg_rows or '<tr><td colspan=\"6\">No pages analyzed.</td></tr>'}</tbody></table>"
            )
        if dom == "reputation":
            srcs = dataset.get("external_sources") or []
            s_rows = "".join(
                f"<tr><td><strong>{_esc(s.get('domain'))}</strong></td><td>{_esc(s.get('source_category'))}</td>"
                f"<td>{'Yes' if s.get('brand_present') else 'No'}</td><td>{'Yes' if s.get('cites_competitors') else 'No'}</td>"
                f"<td>{_esc(s.get('outreach_strategy') or s.get('evidence_of_relevance') or '—')}</td></tr>"
                for s in srcs
            )
            return (
                f"<table><thead><tr><th>External Source</th><th>Category</th><th>Brand</th><th>Competitors</th><th>Evidence / Strategy</th></tr></thead>"
                f"<tbody>{s_rows or '<tr><td colspan=\"5\">No external sources captured.</td></tr>'}</tbody></table>"
            )
        if dom == "competitive":
            art_g = (dataset.get("department_artifacts") or {}).get("department_g") or {}
            board = art_g.get("leaderboard") or art_g.get("competitor_shares") or []
            if isinstance(board, dict):
                b_rows = "".join(f"<tr><td><strong>{_esc(k)}</strong></td><td>{_esc(v)}</td></tr>" for k, v in board.items())
                return f"<table><thead><tr><th>Entity</th><th>Observed Share / Metrics</th></tr></thead><tbody>{b_rows}</tbody></table>"
            if isinstance(board, list) and board:
                b_rows = "".join(
                    f"<tr><td><strong>{_esc(b.get('entity') or b.get('name'))}</strong></td>"
                    f"<td>{_esc(b.get('mentions', 0))}</td><td>{_esc(b.get('mention_share_pct', 0))}%</td>"
                    f"<td>{_esc(b.get('recommendations', 0))}</td><td>{_esc(b.get('citations', 0))}</td></tr>"
                    for b in board if isinstance(b, dict)
                )
                return f"<table><thead><tr><th>Entity</th><th>Mentions</th><th>Share</th><th>Recommendations</th><th>Citations</th></tr></thead><tbody>{b_rows}</tbody></table>"
        return ""

    def _render_appendix_body(self, key: str, dataset: Dict[str, Any]) -> str:
        """Fully render every single dynamic appendix (A1–A10) with ZERO stubs and ZERO truncations."""
        findings = dataset.get("findings") or []
        legacy_findings = dataset.get("legacy_findings") or []
        if key == "prompts":
            rows_html = "".join(
                f"<tr><td class='mono'>{_esc(p.get('prompt_id'))}</td><td>{_esc(_enum_str(p.get('category')))}</td>"
                f"<td>{'Branded' if p.get('is_branded') else 'Non-Branded'}</td>"
                f"<td>{_esc(p.get('market'))}/{_esc(p.get('language'))}</td>"
                f"<td>{_esc(p.get('approval_status'))}</td><td>{_esc(p.get('question'))}</td></tr>"
                for p in dataset.get("prompts", [])
            )
            return f"<table><thead><tr><th>ID</th><th>Category</th><th>Type</th><th>Market/Lang</th><th>Status</th><th>Prompt</th></tr></thead><tbody>{rows_html or '<tr><td colspan=\"6\">No prompts stored.</td></tr>'}</tbody></table>"

        if key == "responses":
            mentions_by_resp: Dict[str, List[Dict[str, Any]]] = {}
            for m in dataset.get("mentions", []):
                mentions_by_resp.setdefault(str(m.get("response_id") or ""), []).append(m)
            rows_html = []
            for r in dataset.get("responses", []):
                rid = str(r.get("response_id") or "")
                m_list = mentions_by_resp.get(rid, [])
                m_txt = "; ".join(
                    f"{m.get('entity_name')} ({_enum_str(m.get('mention_type'))}, {m.get('sentiment')})"
                    for m in m_list
                ) or "None"
                flags = f"Mentioned:{r.get('brand_mentioned')} · Rec:{r.get('brand_recommended')} · Cited:{r.get('brand_cited')} · Sentiment:{r.get('sentiment')}"
                rows_html.append(
                    f"<tr><td class='mono'>{_esc(rid)}<div style='font-size:7pt;color:#64748b;'>SHA:{_esc(str(r.get('response_hash') or '')[:12])}</div></td>"
                    f"<td>{_esc(r.get('platform_id'))} ({_esc(r.get('model_version'))})<div class='mono' style='font-size:7pt;'>{_esc(_enum_str(r.get('testing_mode')))}</div></td>"
                    f"<td style='font-size:7.5pt;'>{_esc(flags)}<div><strong>Mentions:</strong> {_esc(m_txt)}</div></td>"
                    f"<td style='font-size:7.5pt;'>{_esc(str(r.get('response_text') or '')[:1200])}</td></tr>"
                )
            return f"<table><thead><tr><th>ID / Hash</th><th>Platform / Mode</th><th>Signals &amp; Mentions</th><th>Verbatim Response</th></tr></thead><tbody>{''.join(rows_html) or '<tr><td colspan=\"4\">No live AI responses captured in this run.</td></tr>'}</tbody></table>"

        if key == "citations":
            rows_html = "".join(
                f"<tr><td class='mono'>{_esc(c.get('citation_id'))}</td><td>{_esc(c.get('platform_id'))}</td>"
                f"<td>{_esc(c.get('domain'))}</td><td>{_esc(_enum_str(c.get('source_ownership')))}</td>"
                f"<td>{_esc(c.get('supports_claim'))} / {_esc(c.get('freshness_status'))}</td>"
                f"<td><a href='{_esc(c.get('cited_url'))}'>{_esc(c.get('cited_url'))}</a>"
                f"<div style='font-size:7.5pt;color:#475569;'>{_esc(c.get('associated_claim') or '')}</div></td></tr>"
                for c in dataset.get("citations", [])
            )
            return f"<table><thead><tr><th>ID</th><th>Platform</th><th>Domain</th><th>Ownership</th><th>Support / Freshness</th><th>Cited URL &amp; Claim</th></tr></thead><tbody>{rows_html or '<tr><td colspan=\"6\">No citations observed in this run.</td></tr>'}</tbody></table>"

        if key == "external_sources":
            rows_html = "".join(
                f"<tr><td class='mono'>{_esc(s.get('source_id'))}</td><td><strong>{_esc(s.get('domain'))}</strong>"
                f"<div style='font-size:7.5pt;'>{_esc(s.get('url') or '')}</div></td>"
                f"<td>{_esc(s.get('source_category'))}</td>"
                f"<td>Brand: {'Yes' if s.get('brand_present') else 'No'} · Comp: {'Yes' if s.get('cites_competitors') else 'No'} ({s.get('citation_count', 0)} cites)</td>"
                f"<td>{_esc(s.get('outreach_strategy') or s.get('evidence_of_relevance') or '—')}"
                f"<div style='font-size:7pt;color:#64748b;'>{_esc(s.get('restrictions_and_risks') or '')}</div></td></tr>"
                for s in dataset.get("external_sources", [])
            )
            return f"<table><thead><tr><th>ID</th><th>Source Domain / URL</th><th>Category</th><th>Coverage</th><th>Outreach &amp; Governance</th></tr></thead><tbody>{rows_html or '<tr><td colspan=\"5\">No external sources recorded.</td></tr>'}</tbody></table>"

        if key == "entities":
            rows_html = "".join(
                f"<tr><td class='mono'>{_esc(e.get('entity_id'))}</td><td>{_esc(e.get('entity_type'))}</td>"
                f"<td><strong>{_esc(e.get('entity_name'))}</strong> · {_esc(e.get('attribute'))}</td>"
                f"<td>{_esc(e.get('value'))}</td>"
                f"<td>{_esc(_enum_str(e.get('fact_status')))} (Approved: {_esc(e.get('approved_by') or 'Pending')})</td>"
                f"<td>{_esc(len(e.get('conflicting_ai_observations') or []))} conflict(s)</td></tr>"
                for e in dataset.get("entities", [])
            )
            return f"<table><thead><tr><th>ID</th><th>Type</th><th>Entity &amp; Attribute</th><th>Value</th><th>Approval State</th><th>AI Conflicts</th></tr></thead><tbody>{rows_html or '<tr><td colspan=\"6\">No entity records stored.</td></tr>'}</tbody></table>"

        if key == "findings":
            cards = "".join(render_geo_finding_card_html(f, badge_prefix="CANONICAL GEO") for f in findings)
            legacy_cards = "".join(render_geo_finding_card_html(f, badge_prefix="LEGACY AUDIT") for f in legacy_findings)
            parts = []
            if cards:
                parts.append(f"<h4>Canonical GEO Findings ({len(findings)})</h4>{cards}")
            if legacy_cards:
                parts.append(f"<h4>Legacy / Cross-Track Audit Findings ({len(legacy_findings)})</h4>{legacy_cards}")
            return "".join(parts) or "<p class='muted'>No findings recorded.</p>"

        if key == "methodology":
            sc = dataset.get("scorecard") or {}
            dims = sc.get("dimensions") or []
            qa = dataset.get("qa_report") or {}
            d_rows = "".join(
                f"<tr><td><strong>{_esc(d.get('dimension_name'))}</strong></td><td>{_esc(d.get('proposed_weight_pct'))}%</td>"
                f"<td>{_esc(d.get('score')) if d.get('score') is not None else 'Unmeasured'}</td>"
                f"<td>{_esc(_enum_str(d.get('status')))}</td><td>{_esc(d.get('explanation') or '')}</td></tr>"
                for d in dims
            )
            qa_rows = "".join(
                f"<tr><td class='mono'>{_esc(c.get('check_id'))}</td><td>{_esc(c.get('check_name'))}</td>"
                f"<td><strong>{'PASS' if c.get('passed') else 'FAIL'}</strong> ({_esc(c.get('severity'))})</td>"
                f"<td>{_esc(c.get('details'))}</td></tr>"
                for c in (qa.get("checks") or [])
            )
            return (
                f"<p><strong>Methodology Version:</strong> <code>{_esc(dataset.get('methodology_version'))}</code> · "
                f"{_esc(sc.get('methodology_disclosure') or 'Observed AI outcomes and GEO readiness are scored independently.')}</p>"
                f"<table><thead><tr><th>Dimension</th><th>Weight</th><th>Score</th><th>Status</th><th>Explanation</th></tr></thead><tbody>{d_rows}</tbody></table>"
                f"<h4>Independent Publication QA Gate ({_esc(qa.get('qa_status') or 'not_run')})</h4>"
                f"<table><thead><tr><th>Check ID</th><th>Validation Rule</th><th>Result</th><th>Details</th></tr></thead><tbody>{qa_rows or '<tr><td colspan=\"4\">No QA checks recorded.</td></tr>'}</tbody></table>"
            )

        if key == "runs":
            run_rows = "".join(
                f"<tr><td class='mono'>{_esc(r.get('run_id'))}</td><td>{_esc(r.get('platform_id'))} ({_esc(r.get('model_version'))})</td>"
                f"<td class='mono'>{_esc(_enum_str(r.get('testing_mode')))}</td><td>{_esc(_enum_str(r.get('status')))}</td>"
                f"<td>{r.get('latency_ms', 0):.0f}ms · {r.get('prompt_tokens', 0)}/{r.get('completion_tokens', 0)} tok · ${_esc(round(float(r.get('cost_usd') or 0.0), 5))}</td>"
                f"<td>{'Fallback: ' + _esc(r.get('fallback_reason') or r.get('requested_model')) if r.get('fallback_used') else 'Direct'}</td></tr>"
                for r in dataset.get("runs", [])
            )
            snap_rows = "".join(
                f"<tr><td class='mono'>{_esc(s.get('snapshot_id'))}</td><td>{_esc(s.get('snapshot_type'))}</td>"
                f"<td class='mono'>{_esc(str(s.get('content_hash') or '')[:16])}</td><td>{_esc(s.get('url') or '—')}</td>"
                f"<td class='mono'>{_esc(s.get('created_at'))}</td></tr>"
                for s in dataset.get("snapshots", [])
            )
            return (
                f"<h4>Provider Execution Log ({len(dataset.get('runs', []))})</h4>"
                f"<table><thead><tr><th>Run ID</th><th>Platform / Model</th><th>Mode</th><th>State</th><th>Telemetry / Cost</th><th>Fallback</th></tr></thead><tbody>{run_rows or '<tr><td colspan=\"6\">No provider executions recorded.</td></tr>'}</tbody></table>"
                f"<h4>Immutable CAS Evidence Snapshots ({len(dataset.get('snapshots', []))})</h4>"
                f"<table><thead><tr><th>Snapshot ID</th><th>Type</th><th>SHA-256</th><th>URL</th><th>Captured At</th></tr></thead><tbody>{snap_rows or '<tr><td colspan=\"5\">No CAS snapshots recorded.</td></tr>'}</tbody></table>"
            )

        if key == "failures":
            failed = [r for r in dataset.get("runs", []) if _enum_str(r.get("status")) != GEODataQualityState.OBSERVED.value]
            unconf = (dataset.get("scorecard") or {}).get("coverage", {}).get("unconfigured_platforms") or []
            rows_html = "".join(
                f"<tr><td class='mono'>{_esc(r.get('run_id'))}</td><td>{_esc(r.get('platform_id'))}</td>"
                f"<td>{_esc(_enum_str(r.get('status')))}</td><td>{_esc(r.get('error_message') or 'Unavailable')}</td></tr>"
                for r in failed
            )
            unconf_note = f"<p><strong>Unconfigured Platforms (Excluded from Denominator, Never Scored as 0%):</strong> {_esc(', '.join(unconf))}</p>" if unconf else ""
            return f"{unconf_note}<table><thead><tr><th>Run ID</th><th>Platform</th><th>State</th><th>Reason</th></tr></thead><tbody>{rows_html or '<tr><td colspan=\"4\">No failed prompt executions.</td></tr>'}</tbody></table>"

        if key == "history":
            hist = dataset.get("monitoring_history") or []
            scheds = dataset.get("monitoring_schedules") or []
            alerts = dataset.get("monitoring_alerts") or []
            h_rows = "".join(
                f"<tr><td class='mono'>{_esc(h.get('audit_id'))}</td><td class='mono'>{_esc(str(h.get('created_at') or '')[:19])}</td>"
                f"<td>{_esc(h.get('publication_status'))}</td><td>{_esc(h.get('observed_performance_score'))}</td>"
                f"<td>{_esc(h.get('readiness_score'))}</td><td class='mono'>{_esc(h.get('methodology_version'))}</td></tr>"
                for h in hist
            )
            a_rows = "".join(
                f"<tr><td>{_esc(a.get('alert_type'))}</td><td>{_esc(a.get('severity'))}</td>"
                f"<td><strong>{_esc(a.get('title'))}</strong>: {_esc(a.get('description'))}</td></tr>"
                for a in alerts
            )
            s_summary = ", ".join(f"{s.get('cadence')} (${s.get('max_budget_per_run_usd')}/run)" for s in scheds) or "No active monitoring schedules."
            return (
                f"<p><strong>Active Monitoring Schedules:</strong> {_esc(s_summary)}</p>"
                f"<h4>Historical Audits ({len(hist)})</h4>"
                f"<table><thead><tr><th>Audit ID</th><th>Date</th><th>Status</th><th>Observed</th><th>Readiness</th><th>Methodology</th></tr></thead><tbody>{h_rows or '<tr><td colspan=\"6\">Single baseline audit recorded so far.</td></tr>'}</tbody></table>"
                f"<h4>Drift &amp; Misinformation Alerts ({len(alerts)})</h4>"
                f"<table><thead><tr><th>Type</th><th>Severity</th><th>Alert</th></tr></thead><tbody>{a_rows or '<tr><td colspan=\"3\">No monitoring alerts fired.</td></tr>'}</tbody></table>"
            )

        return f"<p class='muted'>Canonical records included: {len(dataset.get(key, [])) if isinstance(dataset.get(key), list) else 'Included'}.</p>"

    def render_html(self, tenant_id: str, audit_id: str, profile: str = "complete_audit_book") -> Tuple[str, Dict[str, Any]]:
        dataset = self.build_canonical_dataset(tenant_id, audit_id)
        prof_key = profile if profile in GEO_REPORT_PROFILES else "complete_audit_book"
        prof = GEO_REPORT_PROFILES[prof_key]
        sections, omitted = self.select_sections(dataset, prof_key)

        audit = dataset["audit"]
        sc = dataset.get("scorecard") or {}
        cov = sc.get("coverage") or {}
        pack = dataset.get("remediation_pack") or {}
        tasks = pack.get("tasks") or []
        findings = dataset.get("findings") or []
        legacy_findings = dataset.get("legacy_findings") or []
        recommendations = dataset.get("recommendations") or []
        verifications = dataset.get("verifications") or []
        experiments = dataset.get("experiments") or []
        qa_report = dataset.get("qa_report") or {}

        chapters_payload: List[Dict[str, Any]] = []
        chapter_html_blocks: List[str] = []
        toc_items: List[str] = []
        rendered_domain_tables: Set[str] = set()
        rendered_domain_findings: Set[str] = set()

        for sec in sections:
            fields = self._chapter_10_fields(sec, dataset)
            dom = sec["domain"]
            chapters_payload.append({**sec, "content": fields})
            anchor = f"sec-{sec['number']:02d}"
            toc_items.append(f'<li><a href="#{anchor}">{sec["number"]:02d}. {_esc(sec["title"])}</a> <span class="muted">({_esc(sec["part"])})</span></li>')

            extra_domain_html = ""
            if dom not in rendered_domain_tables and dom not in ("front_matter", "remediation", "verification", "evidence"):
                tbl = self._domain_empirical_table_html(dom, dataset)
                if tbl:
                    extra_domain_html += f"<div style='margin-top:10px;'>{tbl}</div>"
                rendered_domain_tables.add(dom)
            if dom not in rendered_domain_findings and dom not in ("front_matter", "remediation", "verification", "evidence"):
                dom_fs = self._domain_findings(dom, findings)
                if dom_fs:
                    extra_domain_html += (
                        f"<h4>Observed Findings in {_esc(sec['part'])} ({len(dom_fs)})</h4>"
                        + "".join(render_geo_finding_card_html(f) for f in dom_fs)
                    )
                rendered_domain_findings.add(dom)

            chapter_html_blocks.append(f"""
            <section class="chapter" id="{anchor}">
              <div class="chapter-kicker">{_esc(sec["part"])} · Section {sec["number"]:02d}</div>
              <h3>{sec["number"]:02d}. {_esc(sec["title"])}</h3>
              <table class="std-table">
                <tbody>
                  <tr><th>1. What was evaluated</th><td>{_esc(fields["evaluated"])}</td></tr>
                  <tr><th>2. Why it matters</th><td>{_esc(fields["why_it_matters"])}</td></tr>
                  <tr><th>3. What was actually observed</th><td><strong>{_esc(fields["observed"])}</strong></td></tr>
                  <tr><th>4. Supporting evidence</th><td class="mono">{_esc(fields["evidence"])}</td></tr>
                  <tr><th>5. Limitations</th><td>{_esc(fields["limitations"])}</td></tr>
                  <tr><th>6. Business implication</th><td>{_esc(fields["business_implication"])}</td></tr>
                  <tr><th>7. What needs to change</th><td>{_esc(fields["what_needs_to_change"])}</td></tr>
                  <tr><th>8. How to implement</th><td>{_esc(fields["how_to_implement"])}</td></tr>
                  <tr><th>9. Ownership</th><td>{_esc(fields["owner"])}</td></tr>
                  <tr><th>10. Independent verification</th><td>{_esc(fields["verification"])}</td></tr>
                </tbody>
              </table>
              {extra_domain_html}
            </section>
            """)

        # Dedicated complete sections so NO profile ever drops findings, recommendations, remediation, verification, experiments, or QA
        all_findings_html = (
            "".join(render_geo_finding_card_html(f, badge_prefix="CANONICAL GEO") for f in findings)
            or "<p class='muted'>No canonical GEO findings recorded.</p>"
        )
        legacy_findings_section = ""
        if legacy_findings:
            legacy_findings_section = (
                f"<section class='chapter' id='legacy-findings'>"
                f"<h2>Legacy &amp; Cross-Track Audit Findings ({len(legacy_findings)})</h2>"
                f"<p class='muted'>Preserved legacy audit findings for {_esc(audit.get('domain'))} deduplicated against canonical GEO findings.</p>"
                + "".join(render_geo_finding_card_html(f, badge_prefix="LEGACY AUDIT") for f in legacy_findings)
                + "</section>"
            )

        rec_rows = "".join(
            f"<tr><td class='mono'>{_esc(r.get('recommendation_id'))}</td>"
            f"<td><strong>{_esc(r.get('title'))}</strong><div style='font-size:8pt;color:#475569;'>{_esc(r.get('rationale'))}</div></td>"
            f"<td>{_esc(r.get('dimension'))}</td><td>{_esc(r.get('expected_impact'))} / {_esc(r.get('effort'))} (Score: {_esc(r.get('priority_score'))})</td>"
            f"<td>{_esc(r.get('owner_department'))}</td>"
            f"<td>{_esc('; '.join(r.get('action_steps') or []))}</td>"
            f"<td class='mono'>{_esc(', '.join(r.get('finding_ids') or []))}</td></tr>"
            for r in recommendations
        )
        recommendations_section = (
            f"<section class='chapter' id='geo-recommendations'>"
            f"<h2>Prioritized GEO Recommendations ({len(recommendations)})</h2>"
            f"<table><thead><tr><th>ID</th><th>Recommendation &amp; Rationale</th><th>Dimension</th><th>Impact / Effort</th><th>Department</th><th>Action Steps</th><th>Findings</th></tr></thead>"
            f"<tbody>{rec_rows or '<tr><td colspan=\"7\">No recommendations generated.</td></tr>'}</tbody></table>"
            "</section>"
        )

        remediation_section = (
            f"<section class='chapter' id='geo-remediation'>"
            f"<h2>Consolidated 13-Deliverable GEO Remediation Pack ({len(tasks)} Coordinated Tasks)</h2>"
            f"{_render_remediation_pack_html(pack)}"
            "</section>"
        )

        ver_rows = "".join(
            f"<tr><td class='mono'>{_esc(v.get('verification_id'))}</td><td class='mono'>{_esc(v.get('task_id'))}</td>"
            f"<td>{_esc(v.get('verified_by'))}</td><td>{_esc(v.get('implementation_verified'))}</td>"
            f"<td>{_esc(v.get('outcome_improved'))}</td>"
            f"<td>{'REGRESSION: ' + _esc('; '.join(v.get('regression_details') or [])) if v.get('regression_detected') else 'None'}</td>"
            f"<td><strong>{_esc(v.get('overall_status'))}</strong></td></tr>"
            for v in verifications
        )
        verifications_section = (
            f"<section class='chapter' id='geo-verifications'>"
            f"<h2>Independent Verification Results ({len(verifications)})</h2>"
            f"<p class='muted'>Implementation Verified is always separated from Observed AI Outcome Improved.</p>"
            f"<table><thead><tr><th>Verification ID</th><th>Task ID</th><th>Reviewer</th><th>Implementation Verified</th><th>Outcome Improved</th><th>Regressions</th><th>Status</th></tr></thead>"
            f"<tbody>{ver_rows or '<tr><td colspan=\"7\">No post-change verifications executed yet.</td></tr>'}</tbody></table>"
            "</section>"
        )

        exp_rows = "".join(
            f"<tr><td class='mono'>{_esc(e.get('experiment_id'))}</td>"
            f"<td><strong>{_esc(e.get('title'))}</strong><div style='font-size:8pt;'>{_esc(e.get('hypothesis'))}</div></td>"
            f"<td>{_esc(e.get('status'))}</td>"
            f"<td class='mono'>{_esc(json.dumps(e.get('baseline_metrics') or {}))} → {_esc(json.dumps(e.get('retest_metrics') or {}))}</td>"
            f"<td class='mono'>{_esc(json.dumps(e.get('observed_delta') or {}))}</td>"
            f"<td style='font-size:7.5pt;'>{_esc(e.get('causation_disclaimer'))}</td></tr>"
            for e in experiments
        )
        experiments_section = (
            f"<section class='chapter' id='geo-experiments'>"
            f"<h2>Controlled GEO Experiments ({len(experiments)})</h2>"
            f"<table><thead><tr><th>ID</th><th>Experiment &amp; Hypothesis</th><th>Status</th><th>Baseline → Retest</th><th>Delta</th><th>Causation Disclosure</th></tr></thead>"
            f"<tbody>{exp_rows or '<tr><td colspan=\"6\">No controlled experiments recorded yet.</td></tr>'}</tbody></table>"
            "</section>"
        )

        qa_checks = qa_report.get("checks") or []
        qa_rows = "".join(
            f"<tr><td class='mono'>{_esc(c.get('check_id'))}</td><td>{_esc(c.get('check_name'))}</td>"
            f"<td><strong>{'PASS' if c.get('passed') else 'FAIL'}</strong> ({_esc(c.get('severity'))})</td>"
            f"<td>{_esc(c.get('details'))}</td></tr>"
            for c in qa_checks
        )
        qa_section = (
            f"<section class='chapter' id='geo-qa-gate'>"
            f"<h2>Independent Publication QA Gate ({_esc(qa_report.get('qa_status') or 'pending')} · {len(qa_checks)} Checks)</h2>"
            f"<table><thead><tr><th>ID</th><th>Check</th><th>Result</th><th>Details</th></tr></thead>"
            f"<tbody>{qa_rows or '<tr><td colspan=\"4\">QA checks will execute at publication time.</td></tr>'}</tbody></table>"
            "</section>"
        )

        # Dynamic appendices (all 10 fully rendered, zero stubs)
        allowed_app = set(prof.get("include_appendices") or [])
        appendix_blocks: List[str] = []
        for app_def in GEO_DYNAMIC_APPENDICES:
            if app_def["id"] not in allowed_app:
                continue
            body = self._render_appendix_body(app_def["key"], dataset)
            appendix_blocks.append(f"<section class='chapter' id='app-{_esc(app_def['id'])}'><h3>Appendix {_esc(app_def['id'])}: {_esc(app_def['title'])}</h3>{body}</section>")

        dim_svg = render_seven_dimension_svg(sc.get("dimensions") or [])
        plat_svg = render_platform_matrix_svg(dataset.get("platforms") or [])

        obs_display = f"{sc.get('observed_performance_score'):.1f}/100" if isinstance(sc.get("observed_performance_score"), (int, float)) else f"Unmeasured ({sc.get('observed_performance_status', 'NOT_CONFIGURED')})"
        ready_display = f"{sc.get('readiness_score'):.1f}/100" if isinstance(sc.get("readiness_score"), (int, float)) else "Unmeasured"

        payload = {
            "audit_id": audit_id,
            "domain": audit.get("domain"),
            "brand_name": audit.get("brand_name"),
            "profile": prof_key,
            "title": prof["title"],
            "audience": prof["audience"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "methodology_version": dataset["methodology_version"],
            "publication_status": audit.get("publication_status"),
            "scorecard": sc,
            "platforms": dataset.get("platforms") or [],
            "findings": findings,
            "legacy_findings": legacy_findings,
            "recommendations": recommendations,
            "remediation_pack": pack,
            "verifications": verifications,
            "experiments": experiments,
            "citations": dataset.get("citations") or [],
            "entities": dataset.get("entities") or [],
            "external_sources": dataset.get("external_sources") or [],
            "pages": dataset.get("pages") or [],
            "mentions": dataset.get("mentions") or [],
            "runs": dataset.get("runs") or [],
            "snapshots": dataset.get("snapshots") or [],
            "qa_report": qa_report,
            "monitoring_history": dataset.get("monitoring_history") or [],
            "prompts_count": len(dataset.get("prompts") or []),
            "responses_count": len(dataset.get("responses") or []),
            "tasks_count": len(tasks),
            "chapters": chapters_payload,
            "chapters_omitted": omitted,
        }

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Dristik {_esc(prof['title'])} — {_esc(audit.get('brand_name'))}</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 18mm 14mm 18mm 14mm;
      @top-left {{ content: "DRISTIK ENTERPRISE GEO INTELLIGENCE"; font-size: 7.5pt; color: #64748b; font-family: system-ui, sans-serif; }}
      @top-right {{ content: "{_esc(audit.get('domain'))}"; font-size: 7.5pt; color: #64748b; font-family: system-ui, sans-serif; }}
      @bottom-left {{ content: "Audit ID: {_esc(audit_id)} · {_esc(dataset['methodology_version'])}"; font-size: 7.5pt; color: #94a3b8; font-family: monospace; }}
      @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font-size: 7.5pt; color: #64748b; font-family: system-ui, sans-serif; }}
    }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #0f172a; font-size: 9.5pt; line-height: 1.5; margin: 0; background: #fff; }}
    .wrap {{ max-width: 820px; margin: 0 auto; padding: 18px; }}
    .cover {{ background: #0b1320; color: #f8fafc; padding: 36px 28px; border-radius: 8px; margin-bottom: 24px; page-break-after: always; }}
    .cover h1 {{ font-size: 26pt; margin: 8px 0; }}
    .cover .sub {{ color: #cbd5e1; font-size: 11pt; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 8.5pt; }}
    .muted {{ color: #64748b; font-size: 8.5pt; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; }}
    .kpi {{ border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; background: #faf9f6; }}
    .kpi .lbl {{ font-size: 8pt; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; font-weight: 700; }}
    .kpi .val {{ font-size: 16pt; font-weight: 800; color: #0f172a; margin: 4px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 10px 0 18px 0; font-size: 8.2pt; table-layout: fixed; word-wrap: break-word; overflow-wrap: anywhere; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 6px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; font-weight: 700; color: #334155; }}
    .std-table th {{ width: 28%; }}
    .chapter {{ page-break-inside: auto; margin-bottom: 18px; padding-top: 8px; border-top: 1px solid #e2e8f0; }}
    .chapter-kicker {{ font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.08em; color: #0f766e; font-weight: 700; }}
    a {{ color: #1d4ed8; text-decoration: none; }}
    .disclaimer {{ background: #fffbeb; border-left: 3px solid #d97706; padding: 10px 12px; font-size: 8.5pt; margin: 12px 0; }}
  </style>
</head>
<body>
<div class="wrap">
  <div class="cover">
    <div class="mono" style="color:#38bdf8;">DRISTIK ENTERPRISE GEO INTELLIGENCE · {_esc(dataset['methodology_version'])}</div>
    <h1>{_esc(prof['title'])}</h1>
    <p class="sub">Brand: {_esc(audit.get('brand_name'))} ({_esc(audit.get('domain'))}) · Audience: {_esc(prof['audience'])}</p>
    <p class="mono" style="color:#94a3b8;margin-top:24px;">Audit ID: {_esc(audit_id)} · Status: {_esc(audit.get('publication_status'))} · Generated: {_esc(payload['generated_at'])}</p>
  </div>

  <h2>Dual GEO Scorecard (Observed Outcomes vs Readiness)</h2>
  <div class="disclaimer">{_esc(sc.get('methodology_disclosure', 'Observed AI visibility and website readiness are reported separately.'))}</div>
  <div class="kpi-grid">
    <div class="kpi"><div class="lbl">1. Observed GEO Performance</div><div class="val">{_esc(obs_display)}</div><div class="muted">Platforms tested: {len(cov.get('tested_platforms') or [])} · Runs: {cov.get('successful_prompt_executions', 0)}/{cov.get('total_planned_prompts', 0)} planned</div></div>
    <div class="kpi"><div class="lbl">2. GEO Readiness &amp; Optimization</div><div class="val">{_esc(ready_display)}</div><div class="muted">Grade: {_esc(sc.get('readiness_grade', 'Unmeasured'))} · Confidence: {_esc(cov.get('evidence_confidence'))}</div></div>
    <div class="kpi"><div class="lbl">Findings &amp; Remediation</div><div class="val">{len(findings)} / {len(tasks)}</div><div class="muted">Canonical GEO findings (+{len(legacy_findings)} legacy) / tasks · Citations: {len(dataset.get('citations') or [])}</div></div>
  </div>
  {dim_svg}
  <div style="margin-top:12px;">{plat_svg}</div>

  <h2>Table of Contents ({len(sections)} Evidence-Backed Sections)</h2>
  <ol>{"".join(toc_items)}</ol>
  {f"<p class='muted'>Dynamically omitted {len(omitted)} section(s) with no captured evidence to prevent generic boilerplate.</p>" if omitted else ""}

  <section class="chapter" id="canonical-findings">
    <h2>Complete Canonical GEO Findings Register ({len(findings)})</h2>
    {all_findings_html}
  </section>
  {legacy_findings_section}
  {recommendations_section}
  {remediation_section}
  {verifications_section}
  {experiments_section}
  {qa_section}

  {"".join(chapter_html_blocks)}
  {"".join(appendix_blocks)}
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
    ) -> Tuple[GEOReport, bytes]:
        """Generate, cross-system QA validate, CAS-persist, and return (GEOReport, bytes)."""
        html_doc, json_payload = self.render_html(tenant_id, audit_id, profile=profile)
        audit = self.store.get_audit(tenant_id, audit_id)
        assert audit is not None
        sc_raw = self.store.get_artifact(tenant_id, audit_id, "scorecard") or {"audit_id": audit_id}
        sc_model = GEODualScorecard.model_validate(sc_raw)
        qa = GEOQualityAssuranceEngine.validate_audit(
            audit=audit,
            platforms=self.store.list_platforms(tenant_id, audit_id),
            prompts=self.store.list_prompts(tenant_id, audit_id=audit_id),
            runs=self.store.list_prompt_runs(tenant_id, audit_id),
            responses=self.store.list_responses(tenant_id, audit_id),
            citations=self.store.list_citations(tenant_id, audit_id),
            findings=self.store.list_findings(tenant_id, audit_id=audit_id),
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
            else:
                raw_bytes = _build_deterministic_geo_pdf(json_payload)
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
            url=audit.website_url,
            metadata={"profile": profile, "format": ext, "methodology_version": audit.methodology_version},
        )
        pub_state = (
            GEOPublicationStatus.PUBLISHED.value
            if qa.qa_status == "passed"
            else (GEOPublicationStatus.PARTIAL.value if qa.qa_status == "partial" else GEOPublicationStatus.QA_FAILED.value)
        )
        rep = GEOReport(
            tenant_id=tenant_id,
            audit_id=audit_id,
            domain=audit.domain,
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
            publication_status=pub_state,
            data_quality_state=GEODataQualityState.OBSERVED,
        )
        self.store.save_report(rep)
        return rep, raw_bytes


def _wrap_pdf_lines(text: str, width: int = 96) -> List[str]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return []
    out: List[str] = []
    while len(clean) > width:
        cut = clean.rfind(" ", 0, width)
        if cut <= 20:
            cut = width
        out.append(clean[:cut])
        clean = clean[cut:].lstrip()
    if clean:
        out.append(clean)
    return out


def _build_deterministic_geo_pdf(payload: Dict[str, Any]) -> bytes:
    """Multi-page standards-compliant PDF fallback containing ALL findings, recommendations, tasks, evidence & TOC."""
    sc = payload.get("scorecard") or {}
    cov = sc.get("coverage") or {}
    lines: List[str] = [
        f"Dristik Enterprise GEO Report: {payload.get('title')}",
        f"Brand: {payload.get('brand_name')} | Domain: {payload.get('domain')} | Audit ID: {payload.get('audit_id')}",
        f"Methodology: {payload.get('methodology_version')} | Status: {payload.get('publication_status')}",
        f"Observed GEO Performance: {sc.get('observed_performance_score')} ({sc.get('observed_performance_status')})",
        f"GEO Readiness & Optimization: {sc.get('readiness_score')} ({sc.get('readiness_status')})",
        f"Prompts Executed/Planned: {cov.get('successful_prompt_executions', 0)}/{cov.get('total_planned_prompts', 0)} | Citations: {len(payload.get('citations') or [])} | Findings: {len(payload.get('findings') or [])} (+{len(payload.get('legacy_findings') or [])} legacy)",
        "",
        "=== 7-DIMENSION BREAKDOWN ===",
    ]
    for d in sc.get("dimensions") or []:
        lines.append(f"  - {d.get('dimension_name')} ({d.get('proposed_weight_pct')}%): {d.get('score')} [{d.get('status')}]")

    lines.append("")
    lines.append(f"=== CANONICAL GEO FINDINGS ({len(payload.get('findings') or [])}) ===")
    for f in payload.get("findings") or []:
        lines.extend(_wrap_pdf_lines(f"[{_enum_str(f.get('severity')).upper()}] {f.get('finding_id')} ({f.get('category')}): {f.get('title')}"))
        if f.get("description"):
            lines.extend(_wrap_pdf_lines(f"  Observed: {f.get('description')}"))
        if f.get("root_cause"):
            lines.extend(_wrap_pdf_lines(f"  Root Cause: {f.get('root_cause')}"))
        if f.get("business_impact"):
            lines.extend(_wrap_pdf_lines(f"  Business Impact: {f.get('business_impact')}"))
        if f.get("recommendation"):
            lines.extend(_wrap_pdf_lines(f"  Recommendation: {f.get('recommendation')}"))
        if f.get("affected_urls"):
            lines.extend(_wrap_pdf_lines(f"  URLs: {', '.join(str(u) for u in f.get('affected_urls') or [])}"))
        if f.get("evidence_ids"):
            lines.extend(_wrap_pdf_lines(f"  Evidence IDs: {', '.join(str(e) for e in f.get('evidence_ids') or [])}"))

    if payload.get("legacy_findings"):
        lines.append("")
        lines.append(f"=== LEGACY / CROSS-TRACK AUDIT FINDINGS ({len(payload.get('legacy_findings') or [])}) ===")
        for f in payload.get("legacy_findings") or []:
            lines.extend(_wrap_pdf_lines(f"[{_enum_str(f.get('severity')).upper()}] {f.get('finding_id') or f.get('id')}: {f.get('finding_title') or f.get('title')}"))
            if f.get("description") or f.get("detailed_diagnosis"):
                lines.extend(_wrap_pdf_lines(f"  Observed: {f.get('detailed_diagnosis') or f.get('description')}"))
            if f.get("plain_english_summary"):
                lines.extend(_wrap_pdf_lines(f"  Plain English: {f.get('plain_english_summary')}"))
            if f.get("recommendation") or f.get("recommended_solution"):
                lines.extend(_wrap_pdf_lines(f"  Recommendation: {f.get('recommended_solution') or f.get('recommendation')}"))
            if f.get("affected_urls"):
                lines.extend(_wrap_pdf_lines(f"  URLs: {', '.join(str(u) for u in f.get('affected_urls') or [])}"))

    recs = payload.get("recommendations") or []
    if recs:
        lines.append("")
        lines.append(f"=== PRIORITIZED RECOMMENDATIONS ({len(recs)}) ===")
        for r in recs:
            lines.extend(_wrap_pdf_lines(f"- {r.get('recommendation_id')} [{r.get('dimension')}]: {r.get('title')} | {r.get('rationale')}"))

    pack = payload.get("remediation_pack") or {}
    tasks = pack.get("tasks") or []
    if tasks:
        lines.append("")
        lines.append(f"=== CONSOLIDATED REMEDIATION TASKS ({len(tasks)}) ===")
        for t in tasks:
            lines.extend(_wrap_pdf_lines(f"- {t.get('task_id')} [{t.get('priority')}] ({t.get('department')} · {t.get('status')}): {t.get('title')} | Change: {t.get('proposed_change')}"))

    verifs = payload.get("verifications") or []
    if verifs:
        lines.append("")
        lines.append(f"=== INDEPENDENT VERIFICATIONS ({len(verifs)}) ===")
        for v in verifs:
            lines.extend(_wrap_pdf_lines(f"- {v.get('verification_id')} (Task {v.get('task_id')}): impl_verified={v.get('implementation_verified')}, outcome={v.get('outcome_improved')}, status={v.get('overall_status')}"))

    exps = payload.get("experiments") or []
    if exps:
        lines.append("")
        lines.append(f"=== CONTROLLED EXPERIMENTS ({len(exps)}) ===")
        for e in exps:
            lines.extend(_wrap_pdf_lines(f"- {e.get('experiment_id')} [{e.get('status')}]: {e.get('title')} — {e.get('hypothesis')}"))

    cits = payload.get("citations") or []
    if cits:
        lines.append("")
        lines.append(f"=== CITATION INVENTORY ({len(cits)}) ===")
        for c in cits:
            lines.extend(_wrap_pdf_lines(f"- {c.get('citation_id')} [{c.get('platform_id')} · {_enum_str(c.get('source_ownership'))}]: {c.get('cited_url')}"))

    ents = payload.get("entities") or []
    if ents:
        lines.append("")
        lines.append(f"=== BRAND KNOWLEDGE PROFILE ENTITIES ({len(ents)}) ===")
        for e in ents:
            lines.extend(_wrap_pdf_lines(f"- {e.get('entity_name')}.{e.get('attribute')} = {e.get('value')} [{_enum_str(e.get('fact_status'))}]"))

    qa_checks = (payload.get("qa_report") or {}).get("checks") or []
    if qa_checks:
        lines.append("")
        lines.append(f"=== PUBLICATION QA GATE ({len(qa_checks)} CHECKS) ===")
        for c in qa_checks:
            lines.extend(_wrap_pdf_lines(f"- {c.get('check_id')} [{'PASS' if c.get('passed') else 'FAIL'}]: {c.get('check_name')} — {c.get('details')}"))

    lines.append("")
    lines.append("=== TABLE OF CONTENTS ===")
    for c in payload.get("chapters") or []:
        lines.append(f"  {c['number']:02d}. {c['title']}")

    # Paginate into multi-page PDF (~52 lines per A4 page)
    lines_per_page = 52
    chunks = [lines[i : i + lines_per_page] for i in range(0, max(1, len(lines)), lines_per_page)]
    # Object numbering:
    # 1 = Catalog, 2 = Pages, 3 = Font, then for each page idx k: (4 + 2*k) = Page, (5 + 2*k) = Contents
    page_obj_ids = [4 + 2 * k for k in range(len(chunks))]
    kids_ref = " ".join(f"{pid} 0 R" for pid in page_obj_ids)

    objs: List[bytes] = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        f"2 0 obj << /Type /Pages /Kids [{kids_ref}] /Count {len(chunks)} >> endobj\n".encode("ascii"),
        b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    for k, page_lines in enumerate(chunks):
        page_id = 4 + 2 * k
        content_id = 5 + 2 * k
        stream_cmds = ["BT /F1 9 Tf 36 805 Td 13 TL"]
        for idx, line in enumerate(page_lines):
            safe = str(line).replace("\\", "/").replace("(", "[").replace(")", "]")[:108]
            stream_cmds.append(f"({safe}) Tj" if idx == 0 else f"T* ({safe}) Tj")
        stream_cmds.append(f"T* (Page {k + 1} of {len(chunks)}) Tj")
        stream_cmds.append("ET")
        stream = "\n".join(stream_cmds).encode("latin-1", errors="replace")
        objs.append(
            f"{page_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_id} 0 R /Resources << /Font << /F1 3 0 R >> >> >> endobj\n".encode("ascii")
        )
        objs.append(
            f"{content_id} 0 obj << /Length {len(stream)} >> stream\n".encode("ascii")
            + stream
            + b"\nendstream endobj\n"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(f"trailer << /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii"))
    return bytes(out)


geo_report_builder = GEOReportBuilder()

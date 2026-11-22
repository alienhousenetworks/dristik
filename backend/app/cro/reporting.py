"""
HTML and JSON rendering for the 55-section CRO audit report and audit book.

The four dimensions stay separate. Missing rates stay unmeasured.
"""
from __future__ import annotations

import html
from typing import Any, Dict, Optional

from app.cro.engine import CroIntelligenceReport, build_from_executive_report


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _score_label(score: Optional[float], status: str) -> str:
    if score is None:
        return "Unmeasured"
    return f"{score:.1f}"


class CroReportGenerator:
    """Renders the CRO intelligence report. It does not blend a conversion rate."""

    def render_json_report(
        self,
        intel: CroIntelligenceReport,
        *,
        domain: str = "",
        website_url: str = "",
        generated_at: str = "",
        analysis_id: str = "",
        findings: Optional[list] = None,
    ) -> Dict[str, Any]:
        payload = intel.model_dump()
        payload["domain"] = domain
        payload["website_url"] = website_url
        payload["generated_at"] = generated_at
        payload["analysis_id"] = analysis_id
        payload["chapters"] = intel.chapters
        payload["findings"] = findings or []
        payload.update(compute_cro_status(intel))
        payload["test_groups"] = {k: v for k, v in payload.items() if k in ("page_structure_dom", "mobile_viewport_ux", "desktop_layout_ux", "interactive_forms", "conversion_analytics")}
        return payload

    def render_html_report(
        self,
        intel: CroIntelligenceReport,
        *,
        domain: str = "",
        website_url: str = "",
        generated_at: str = "",
        analysis_id: str = "",
    ) -> str:
        parts = []
        for part in intel.parts:
            owned = [section for section in intel.sections if section.part == part["id"]]
            blocks = []
            for section in owned:
                checks = "".join(
                    "<li><strong>{state}</strong> — {label}: {summary}</li>".format(
                        state=_esc(check.evidence_state),
                        label=_esc(check.label),
                        summary=_esc(check.summary),
                    )
                    for check in section.checks
                )
                blocks.append(
                    "<section id=\"cro-{number}\"><h3>{number}. {title}</h3>"
                    "<p class=\"meta\">{status} · {specialist}</p><ul>{checks}</ul></section>".format(
                        number=_esc(section.number),
                        title=_esc(section.title),
                        status=_esc(section.status),
                        specialist=_esc(section.specialist),
                        checks=checks,
                    )
                )
            parts.append(
                "<section class=\"part\"><h2>Part {pid}. {title}</h2><p class=\"meta\">{span}</p>{body}</section>".format(
                    pid=_esc(part["id"]),
                    title=_esc(part["title"]),
                    span=_esc(part.get("sections", "")),
                    body="".join(blocks),
                )
            )

        dimensions = "".join(
            "<article><h3>{name}</h3><p class=\"score\">{score}</p><p class=\"meta\">{status}</p><p>{note}</p></article>".format(
                name=_esc(item.name),
                score=_esc(_score_label(item.score, item.status)),
                status=_esc(item.status),
                note=_esc(item.note),
            )
            for item in intel.dimensions
        )
        metrics = "".join(
            "<tr><td>{metric}</td><td>{formula}</td><td>{status}</td><td>{display}</td><td>{denominator}</td><td>{note}</td></tr>".format(
                metric=_esc(item.metric),
                formula=_esc(item.formula),
                status=_esc(item.status),
                display=_esc(item.display),
                denominator=_esc(item.denominator or "—"),
                note=_esc(item.note),
            )
            for item in intel.metrics
        )
        findings = "".join(
            "<article class=\"finding\"><h3>{fid} · {priority}</h3>"
            "<p><strong>Status.</strong> {status}</p>"
            "<p><strong>Finding.</strong> {finding}</p>"
            "<p><strong>Evidence.</strong> {evidence}</p>"
            "<p><strong>Observed scope.</strong> {scope}</p>"
            "<p><strong>Hypothesis.</strong> {hypothesis}</p>"
            "<p><strong>Recommended action.</strong> {action}</p>"
            "<p><strong>Primary metric.</strong> {metric}</p>"
            "<p><strong>Guardrails.</strong> {guards}</p>"
            "<p><strong>Validation.</strong> {validation}</p>"
            "<p><strong>Impact estimate.</strong> {impact}</p>"
            "<p><strong>Owner.</strong> {owner}</p></article>".format(
                fid=_esc(item.finding_id),
                priority=_esc(item.priority),
                status=_esc(item.status),
                finding=_esc(item.finding),
                evidence=_esc(item.evidence),
                scope=_esc(item.observed_scope),
                hypothesis=_esc(item.hypothesis),
                action=_esc(item.recommended_action),
                metric=_esc(item.primary_metric),
                guards=_esc(", ".join(item.guardrail_metrics)),
                validation=_esc(item.validation),
                impact=_esc(item.impact_estimate),
                owner=_esc(item.owner),
            )
            for item in intel.findings
        ) or "<p>No experience defect met the evidence bar for a finding.</p>"
        roadmap = "".join(
            "<article><h3>{label}</h3><ul>{items}</ul></article>".format(
                label=_esc(label),
                items="".join(f"<li>{_esc(line)}</li>" for line in intel.roadmap.get(key, [])),
            )
            for key, label in (("days_30", "30 days"), ("days_60", "60 days"), ("days_90", "90 days"))
        )
        appendices = "".join(
            "<article><h3>Appendix {aid}. {title}</h3><p class=\"meta\">{status}</p><p>{contents}</p><p>{summary}</p></article>".format(
                aid=_esc(item.id),
                title=_esc(item.title),
                status=_esc(item.status),
                contents=_esc(item.contents),
                summary=_esc(item.summary),
            )
            for item in intel.appendices
        )
        chapters = "".join(
            "<li><strong>{cid}.</strong> {title}</li>".format(cid=_esc(item["id"]), title=_esc(item["title"]))
            for item in intel.chapters
        )
        rules = "".join(f"<li>{_esc(rule)}</li>" for rule in intel.measurement_rules)
        coverage = intel.coverage or {}
        coverage_html = (
            "<section><h3>Coverage and execution limits</h3><p><strong>Status:</strong> {status}</p>"
            "<p><strong>Inspected pages:</strong> {inspected} · <strong>Discovered URLs:</strong> {discovered} · "
            "<strong>Sample coverage:</strong> {percentage}</p>"
            "<p><strong>Rendered DOM:</strong> {rendered} · <strong>Journey execution:</strong> {journeys}</p>"
            "<p>{note}</p></section>"
        ).format(
            status=_esc(coverage.get("status", "NOT_RECORDED")),
            inspected=_esc(coverage.get("inspected_pages", intel.sample_size)),
            discovered=_esc(coverage.get("discovered_urls", intel.discovered_urls)),
            percentage=(f"{coverage['sample_coverage_pct']:.1f}%" if isinstance(coverage.get("sample_coverage_pct"), (int, float)) else "Unavailable"),
            rendered=_esc(coverage.get("rendered_dom_status", "NOT_VERIFIED")),
            journeys=_esc(coverage.get("journey_execution_status", "NOT_EXECUTED")),
            note=_esc(coverage.get("note", "Coverage was not recorded.")),
        )
        calibration = intel.scoring_calibration or {}
        calibration_html = (
            "<section><h3>Scoring calibration</h3><p><strong>Status:</strong> {status}</p>"
            "<p>{basis}</p><p><strong>Priority model:</strong> {priority}</p><p>{note}</p></section>"
        ).format(
            status=_esc(calibration.get("status", "NOT_RECORDED")),
            basis=_esc(calibration.get("basis", "Scoring basis was not recorded.")),
            priority=_esc(calibration.get("priority_calibration", "NOT_RECORDED")),
            note=_esc(calibration.get("note", "Calibration limitations were not recorded.")),
        )
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CRO audit — {_esc(domain or "website")}</title>
<style>
body {{ margin: 0; background: #f6f4ef; color: #1c1915; font: 16px/1.5 "Source Sans 3", "Segoe UI", sans-serif; }}
main {{ max-width: 920px; margin: 0 auto; padding: 32px 20px 64px; }}
h1, h2, h3 {{ font-weight: 650; letter-spacing: 0; }}
h1 {{ font-family: "Iowan Old Style", "Palatino Linotype", serif; font-size: 2rem; margin-bottom: 0.25rem; }}
.meta {{ color: #5c564c; font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.78rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
article {{ border: 1px solid #ddd6c8; background: #fffdf8; border-radius: 6px; padding: 12px 14px; margin: 10px 0; }}
.score {{ font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 1.4rem; margin: 0; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
th, td {{ border-bottom: 1px solid #ddd6c8; text-align: left; vertical-align: top; padding: 8px 6px; }}
a {{ color: #1c1915; }}
</style>
</head>
<body>
<main>
<p class="meta">CRO audit · {_esc(analysis_id)}</p>
<h1>{_esc(domain or website_url or "CRO audit")}</h1>
<p class="meta">{_esc(website_url)} · {_esc(generated_at)}</p>
<p>{_esc(intel.scope_note)}</p>
<p>{_esc(intel.principle)}</p>
<p class="meta">Business model: {_esc(intel.business_model)}. {_esc(intel.model_basis)}</p>
<h2>01. Cover and scope</h2>
<ol>{chapters}</ol>
<h2>02. Executive summary and funnel scorecard</h2>
<p>These four scores stay separate. None of them is a blended conversion rate.</p>
{coverage_html}
{calibration_html}
<div class="grid">{dimensions}</div>
<h2>Measurement</h2>
<ul>{rules}</ul>
<table>
<thead><tr><th>Metric</th><th>Formula</th><th>Status</th><th>Value</th><th>Denominator</th><th>Note</th></tr></thead>
<tbody>{metrics}</tbody>
</table>
<h2>03. Experience and behavioral diagnostics</h2>
{"".join(parts)}
<h2>04. Measurement and experimentation</h2>
<p>A higher observed rate is not a win. Missing numerators stay unavailable.</p>
<h2>05. Prioritized remediation roadmap</h2>
{findings}
<div class="grid">{roadmap}</div>
<h2>06. Appendices and evidence ledger</h2>
{appendices}
</main>
</body>
</html>
"""


cro_report_generator = CroReportGenerator()


def compute_cro_status(intel: CroIntelligenceReport) -> Dict[str, str]:
    """Single source of truth for certification and test-group status (JSON, HTML and PDF)."""
    coverage = intel.coverage or {}
    rendered = str(coverage.get("rendered_dom_status") or "NOT_VERIFIED_BY_CRO_ENGINE")
    has_rendered = "VERIFIED" in rendered and "NOT_VERIFIED" not in rendered
    has_journeys = str(coverage.get("journey_execution_status") or "NOT_EXECUTED") != "NOT_EXECUTED"
    analytics = any(m.status == "MEASURED" for m in (intel.metrics or []))
    certified = has_rendered and has_journeys and analytics
    return {
        "page_structure_dom": "DOM_CHECKED" if intel.sample_size > 0 else "NOT_TESTED",
        "mobile_viewport_ux": "TESTED" if has_rendered else "NOT_TESTED",
        "desktop_layout_ux": "TESTED" if has_rendered else "NOT_TESTED",
        "interactive_forms": "TESTED" if has_journeys else "NOT_TESTED",
        "conversion_analytics": "MEASURED" if analytics else "UNAVAILABLE",
        "certification_status": "CERTIFIED" if certified else "NOT_CERTIFIED",
        "assurance_status": "FULLY_EVALUATED" if certified else "EVALUATED_WITH_LIMITATIONS",
        "certification_disclaimer": (
            "Browser interaction tests and connected conversion analytics were verified for this audit."
            if certified
            else "Mandatory browser-level interaction and conversion analytics tests were unmeasured; this audit cannot provide certified conversion assurance."
        ),
    }


_STATE_COLOR = {
    "VERIFIED": "#15803d", "SAMPLE_VERIFIED": "#15803d", "INFERRED": "#b45309", "HYPOTHESIS": "#b45309",
    "NOT_TESTED": "#64748b", "DATA_UNAVAILABLE": "#64748b", "NOT_APPLICABLE": "#94a3b8",
}


def _badge(state: str) -> str:
    return f'<span class="mono" style="font-weight:700;font-size:6.5pt;color:{_STATE_COLOR.get(state, "#334155")};">{_esc(state)}</span>'


def _section_html(section: Any, findings: list) -> str:
    """Section block following the objective/observation/diagnosis/recommendation/verification/limitations framework."""
    rows = "".join(
        f"<tr><td>{_badge(c.evidence_state)}</td><td>{_esc(c.label)}</td><td>{_esc(c.outcome)}</td>"
        f"<td>{_esc(c.summary)}</td><td class=\"mono\" style=\"font-size:6.5pt;\">{_esc(', '.join(c.evidence[:3]) or '—')}</td></tr>"
        for c in section.checks if c.outcome != "not_applicable"
    )
    open_ = sum(1 for c in section.checks if c.outcome in ("unmeasured", "not_tested"))
    diag = "".join(
        f'<div class="card" style="margin:6px 0;"><div class="card-kicker">{_esc(f.finding_id)} · {_esc(f.priority)} · {_esc(f.evidence_state)}</div>'
        f"<p><strong>Observation:</strong> {_esc(f.finding)}</p><p><strong>Evidence:</strong> {_esc(f.evidence)} ({_esc(f.observed_scope)})</p>"
        f"<p><strong>Root cause:</strong> {_esc(f.root_cause)}</p><p><strong>Recommendation:</strong> {_esc(f.recommended_action)}</p>"
        f"<p><strong>Owner / effort:</strong> {_esc(f.owner)} · {_esc(f.effort)} · confidence {_esc(f.confidence)}</p>"
        f"<p><strong>Hypothesis (untested):</strong> {_esc(f.hypothesis)}</p>"
        f"<p><strong>Primary metric:</strong> {_esc(f.primary_metric)} · <strong>Retest:</strong> {_esc(f.validation)}</p>"
        f"<p><strong>Impact:</strong> {_esc(f.impact_estimate)}</p></div>"
        for f in findings
    ) or '<p style="font-size:8pt;color:#475569;">No defect met the evidence bar in this section on the audited sample.</p>'
    limits = f"{open_} check(s) were not tested or had no data source and are not scored." if open_ else "All applicable checks in this section produced an observation."
    return (
        f'<h3 id="cro-{_esc(section.number)}" style="font-size:11pt;margin:16px 0 4px 0;">{_esc(section.number)}. {_esc(section.title)}</h3>'
        f'<p class="meta" style="font-size:7.5pt;color:#475569;">Status {_esc(section.status)} · specialist {_esc(section.specialist)}</p>'
        f'<table class="print-table"><thead><tr><th>State</th><th>Check</th><th>Outcome</th><th>Observation</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table>'
        f"{diag}<p style=\"font-size:7.5pt;color:#64748b;\"><strong>Limitations:</strong> {_esc(limits)}</p>"
    )


def build_cro_publication_document(report: Any, intel: Optional[CroIntelligenceReport] = None) -> Any:
    """Builds the CRO PublicationDocument from CroIntelligenceReport so every format shares one data source."""
    from app.cro.cro_chapter_visuals import cro_ten_dimension_scorecard_svg
    from app.reports.adaptive_audit_book import (
        _build_ch_cro_cta, _build_ch_cro_forms, _build_ch_cro_trust, build_publication_manifest,
    )
    from app.reports.publishing_engine import ChapterSpec, PartSpec, PublicationDocument, PublicationMetadata

    from app.reports.snapshot_provenance import (
        format_audit_execution_metadata,
        render_snapshot_provenance_bar,
    )

    intel = intel or build_from_executive_report(report)
    snap = format_audit_execution_metadata(report)
    man = build_publication_manifest(report, "CRO")
    status = compute_cro_status(intel)
    exp = next((d for d in intel.dimensions if d.id == "experience"), None)
    score = snap.score_for_section("cro")
    if score is None and exp is not None:
        score = exp.score
    comp_ref = (
        f"{snap.composite_score_display} · GRADE {snap.composite_grade}"
        if snap.composite_score is not None and snap.composite_grade != "NOT GRADED"
        else snap.composite_score_display
    )
    meta = PublicationMetadata(
        family="CRO", title=man["title"], subtitle=man["subtitle"], domain=man["domain"], brand_name=man["brand_name"],
        audit_date=snap.execution_date, report_ref=snap.report_ref, classification=man["classification"], purpose=man["purpose"],
        score_display=f"{score:.1f}" if score is not None else "NOT MEASURED", grade="NOT GRADED", overall_score=score,
        pages_crawled=snap.pages_inspected if snap.pages_inspected is not None else intel.sample_size,
        findings_count=len(intel.findings),
        execution_timestamp=snap.execution_timestamp,
        snapshot_id=snap.snapshot_id,
        configuration_summary=snap.configuration_summary,
        crawl_scope_summary=snap.crawl_scope_summary,
        composite_score_reference=comp_ref,
    )
    cro_provenance_bar = render_snapshot_provenance_bar(
        snap,
        section_key="cro",
        section_label="CRO",
        section_score=score,
        section_findings_count=len(intel.findings),
    )

    cov = intel.coverage or {}
    dims = "".join(
        f"<tr><td>{_esc(d.name)}</td><td>{_esc(_score_label(d.score, d.status))}</td><td>{_esc(d.status)}</td><td>{_esc(d.note)}</td></tr>"
        for d in intel.dimensions
    )
    metrics = "".join(
        f"<tr><td>{_esc(m.metric)}</td><td>{_esc(m.display)}</td><td>{_esc(m.status)}</td><td>{_esc(m.note)}</td></tr>"
        for m in intel.metrics
    )
    svg = cro_ten_dimension_scorecard_svg(
        [{"name": d.name, "score": d.score, "status": "MEASURED" if d.score is not None else "UNMEASURED"} for d in intel.dimensions]
    )
    top = "".join(
        f"<li><strong>{_esc(f.finding_id)}</strong> ({_esc(f.priority)}): {_esc(f.finding)} — "
        f"<span style='color:#475569;'>{_esc(f.recommended_action[:120])}</span></li>"
        for f in intel.findings[:15]
    ) or "<li>No finding met the evidence bar.</li>"
    from app.reports.pdf_evidence_blocks import (
        render_ai_analysis_card,
        render_page_evidence_table,
        render_unmeasured_scope_summary,
    )
    doc_narr_map = getattr(report, "document_narratives", None) or {}
    cro_bundle = doc_narr_map.get("cro_pdf") if isinstance(doc_narr_map, dict) else None
    cro_narr_mode = str(
        cro_bundle.get("narrative_mode")
        if isinstance(cro_bundle, dict)
        else getattr(report, "narrative_mode", "deterministic_fallback")
    )
    cro_ai_chapters = list((cro_bundle.get("chapters") or []) if isinstance(cro_bundle, dict) else [])
    cro_exec_ai_html = (
        render_ai_analysis_card(
            {
                "executive_takeaway": cro_bundle.get("executive_summary", ""),
                "cited_finding_ids": [f.finding_id for f in intel.findings[:6]],
            },
            narrative_mode=cro_narr_mode,
            title_prefix="CRO AI Executive Diagnosis",
        )
        if isinstance(cro_bundle, dict) and cro_bundle.get("executive_summary")
        else ""
    )
    cro_pages = list(getattr(getattr(report, "crawl_manifest", None), "pages", None) or getattr(report, "page_reports", None) or [])
    cro_evidence_table = render_page_evidence_table(
        cro_pages,
        title="Observed Landing & Conversion Page Evidence",
        max_rows=10,
    )

    exec_html = (
        f'{cro_provenance_bar}'
        f'{cro_exec_ai_html}'
        f'{cro_evidence_table}'
        f'<p style="font-size:9pt;">{_esc(intel.scope_note)} Business model: <strong>{_esc(intel.business_model)}</strong> ({_esc(intel.model_basis)}).</p>'
        f'<div class="card"><div class="card-kicker">COVERAGE</div><p>{_esc(cov.get("inspected_pages"))} page(s) inspected of '
        f'{_esc(cov.get("discovered_urls") if cov.get("discovered_urls") is not None else "unknown")} discovered ({_esc(cov.get("status"))}). '
        f'Rendered DOM: {_esc(cov.get("rendered_dom_status"))}. Journeys: {_esc(cov.get("journey_execution_status"))}.</p>'
        f'<p>{_esc(status["certification_disclaimer"])}</p></div>'
        f'<h3>Scorecard</h3>{svg}<table class="print-table"><thead><tr><th>Dimension</th><th>Score</th><th>Status</th><th>Basis</th></tr></thead><tbody>{dims}</tbody></table>'
        f'<h3>Conversion metrics</h3><table class="print-table"><thead><tr><th>Metric</th><th>Value</th><th>Status</th><th>Note</th></tr></thead><tbody>{metrics}</tbody></table>'
        f'<h3>Highest-priority findings ({len(intel.findings)} total)</h3><ul>{top}</ul>'
    )

    by_section: Dict[int, list] = {}
    for f in intel.findings:
        by_section.setdefault(f.section, []).append(f)

    parts: list = []
    pid = "cro_p0"
    parts.append(PartSpec(id=pid, num="", title="EXECUTIVE SUMMARY", chapters=[
        ChapterSpec(id="cro_exec", num="01", part_id=pid, part_title="EXECUTIVE SUMMARY", title="Executive summary and scorecard",
                    desc="Coverage, scores, metrics and top findings.", html_content=exec_html)]))
    n = 2
    excluded: list = []
    collapsed_unmeasured: list = []
    for part_idx, part in enumerate(intel.parts):
        owned = [s for s in intel.sections if s.part == part["id"]]
        applicable = [s for s in owned if s.status != "NOT_APPLICABLE"]
        excluded += [s for s in owned if s.status == "NOT_APPLICABLE"]
        if not applicable:
            continue
        # Only emit full section blocks for sections with observed findings or measured pass/fail checks;
        # collapse 100%-unmeasured sections into the compact Scope Register to eliminate boilerplate bloat.
        active_sections = []
        for s in applicable:
            sec_findings = by_section.get(int(s.number), [])
            has_measured_check = any(c.outcome in ("pass", "fail", "partial") for c in (s.checks or []))
            if sec_findings or has_measured_check:
                active_sections.append(s)
            else:
                collapsed_unmeasured.append((f"{s.number}. {s.title}", s.status, f"All checks unmeasured/untested ({s.specialist})."))
        if not active_sections:
            continue
        ppid = f"cro_part_{part['id']}"
        part_ai_html = ""
        if cro_ai_chapters:
            p_words = [w for w in str(part["title"]).lower().split() if len(w) >= 4]
            matched_ai = next(
                (c for c in cro_ai_chapters if any(w in str(c.get("title", "")).lower() for w in p_words)),
                cro_ai_chapters[part_idx] if part_idx < len(cro_ai_chapters) else None,
            )
            part_ai_html = render_ai_analysis_card(matched_ai, narrative_mode=cro_narr_mode, title_prefix=f"CRO AI Analysis — {part['title']}")
        body = part_ai_html + "".join(_section_html(s, by_section.get(int(s.number), [])) for s in active_sections)
        parts.append(PartSpec(id=ppid, num=part["id"], title=f"PART {part['id']} — {part['title'].upper()}", chapters=[
            ChapterSpec(id=f"cro_{part['id'].lower()}", num=f"{n:02d}", part_id=ppid, part_title=f"PART {part['id']}",
                        title=part["title"], desc=f"Sections {part.get('sections', '')}", html_content=body)]))
        n += 1

    rm = intel.roadmap or {}
    roadmap_html = "".join(f"<h3>{_esc(k)}</h3><ul>{''.join(f'<li>{_esc(i)}</li>' for i in v)}</ul>" for k, v in rm.items() if v) or "<p>No roadmap items.</p>"
    reg = "".join(
        f"<tr>"
        f'<td class="mono" style="font-weight:700;">{_esc(f.finding_id)}</td>'
        f'<td><span class="mono" style="font-size:7pt;font-weight:700;color:{_STATE_COLOR.get(f.evidence_state, "#334155")};">{_esc(f.priority).upper()}</span></td>'
        f'<td><strong>{_esc(f.finding)}</strong></td>'
        f'<td class="mono" style="font-size:7pt;">{_esc(f.observed_scope)}</td>'
        f'<td class="mono" style="font-size:7pt;">{_esc(f.evidence[:60] if len(f.evidence) > 60 else f.evidence)}</td>'
        f'<td style="font-size:7.5pt;">{_esc(f.recommended_action)}</td>'
        f'<td style="font-size:7.5pt;">{_esc(f.owner)}</td>'
        f'<td style="font-size:7.5pt;">{_esc(f.effort)}</td>'
        f"</tr>"
        for f in intel.findings
    )
    detailed_cards = "".join(
        f'<div class="card" style="margin:8px 0;padding:10px 12px;border-left:4px solid {_STATE_COLOR.get(f.evidence_state, "#0f172a")};break-inside:avoid;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
        f'<span class="mono" style="font-size:8pt;font-weight:700;">{_esc(f.finding_id)} // {_esc(f.priority).upper()} PRIORITY</span>'
        f'<span class="mono" style="font-size:7pt;padding:2px 6px;background:#f1f5f9;border-radius:2px;">{_esc(f.evidence_state)}</span>'
        f'</div>'
        f'<div style="font-size:10pt;font-weight:700;color:#0f172a;margin-bottom:6px;">{_esc(f.finding)}</div>'
        f'<p style="font-size:8pt;color:#334155;margin:3px 0;"><strong>Observed Scope:</strong> {_esc(f.observed_scope)}</p>'
        f'<p style="font-size:8pt;color:#334155;margin:3px 0;"><strong>Evidence:</strong> {_esc(f.evidence)}</p>'
        f'<p style="font-size:8pt;color:#334155;margin:3px 0;"><strong>Root Cause:</strong> {_esc(f.root_cause)}</p>'
        f'<div style="background:#f8fafc;padding:6px 10px;border-radius:4px;margin:6px 0;border:1px solid #e2e8f0;">'
        f'<strong style="font-size:7.5pt;color:#0f172a;text-transform:uppercase;">Recommended Remediation:</strong>'
        f'<p style="font-size:8pt;color:#1e293b;margin:2px 0;">{_esc(f.recommended_action)}</p>'
        f'</div>'
        f'<div style="display:flex;gap:14px;font-size:7.5pt;color:#64748b;margin-top:4px;">'
        f'<span><strong>Owner:</strong> {_esc(f.owner)}</span>'
        f'<span><strong>Effort:</strong> {_esc(f.effort)}</span>'
        f'<span><strong>Primary Metric:</strong> {_esc(f.primary_metric)}</span>'
        f'<span><strong>Validation:</strong> {_esc(f.validation)}</span>'
        f'</div>'
        f'</div>'
        for f in intel.findings
    )
    scope = "".join(f"<li>{_esc(s.number)}. {_esc(s.title)} — NOT_APPLICABLE for this business model</li>" for s in excluded) or "<li>No section was excluded.</li>"
    apps = "".join(
        f'<div class="card" style="margin:6px 0;"><div class="card-kicker">APPENDIX {_esc(a.id)} · {_esc(a.status)}</div><strong>{_esc(a.title)}</strong>'
        f"<p>{_esc(a.summary)}</p></div>" for a in intel.appendices
    )
    tail_id = "cro_tail"
    parts.append(PartSpec(id=tail_id, num="", title="REMEDIATION AND REGISTERS", chapters=[
        ChapterSpec(
            id="cro_register",
            num=f"{n:02d}",
            part_id=tail_id,
            part_title="REMEDIATION AND REGISTERS",
            title="Institutional Findings Register & Strategic Roadmap",
            desc=f"Complete register of all {len(intel.findings)} verified findings and prioritized remediation actions.",
            html_content=(
                f'<div class="card" style="margin-bottom:14px;">'
                f'<div class="card-kicker">INSTITUTIONAL FINDINGS REGISTER ({len(intel.findings)} ITEMS)</div>'
                f'<table class="print-table" style="margin-top:8px;">'
                f'<thead><tr><th>ID</th><th>Priority</th><th>Finding</th><th>Scope</th><th>Evidence</th><th>Recommendation</th><th>Owner</th><th>Effort</th></tr></thead>'
                f'<tbody>{reg}</tbody>'
                f'</table>'
                f'</div>'
                f'<h3 style="font-size:11pt;margin:18px 0 8px 0;">Detailed Finding Diagnoses &amp; Remediation Specifications</h3>'
                f'{detailed_cards}'
                f'<div class="decorative-separator" style="margin:20px 0;"></div>'
                f'<h3 style="font-size:11pt;margin:18px 0 8px 0;">Consolidated Remediation Roadmap</h3>'
                f'{roadmap_html}'
            ),
        ),
        ChapterSpec(id="cro_scope", num=f"{n + 1:02d}", part_id=tail_id, part_title="REMEDIATION AND REGISTERS", title="Scope register and appendices",
                    desc="Excluded sections, collapsed unmeasured sections, and appendices.",
                    html_content=f"{render_unmeasured_scope_summary(collapsed_unmeasured, heading='Collapsed Unmeasured CRO Sections')}<h3>Excluded sections</h3><ul>{scope}</ul>{apps}"),
    ]))
    # Per-record CTA, form and trust registries come from the report's cro_audit data (spec appendices D/E).
    reg_id = "cro_registries"
    parts.append(PartSpec(id=reg_id, num="", title="EVIDENCE REGISTRIES", chapters=[
        ChapterSpec(id=cid, num=f"{n + 2 + i:02d}", part_id=reg_id, part_title="EVIDENCE REGISTRIES", title=title,
                    desc=title, html_content=fn(report, man))
        for i, (cid, title, fn) in enumerate([
            ("cro_cta_registry", "CTA evidence registry", _build_ch_cro_cta),
            ("cro_form_registry", "Form evidence registry", _build_ch_cro_forms),
            ("cro_trust_registry", "Trust and credibility registry", _build_ch_cro_trust),
        ])
    ]))
    count = sum(len(p.chapters) for p in parts)
    toc_pages = max(1, -(-(count + len(parts)) // 30))
    return PublicationDocument(metadata=meta, parts=parts, toc_pages=toc_pages, starting_body_page=2 + toc_pages)


def render_cro_audit_book(report: Any) -> str:
    """Renders the CRO audit book HTML from an executive report."""
    from app.reports.publishing_engine import PublicationHtmlRenderer
    return PublicationHtmlRenderer.render(build_cro_publication_document(report))


__all__ = [
    "CroReportGenerator",
    "build_cro_publication_document",
    "compute_cro_status",
    "cro_report_generator",
    "render_cro_audit_book",
]

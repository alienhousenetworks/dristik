"""Unified 5-Point Finding Card, 4-Part Chapter Layout & Page-Budget Compression Renderer.

Every PDF (Master Book + SEO, GEO, AEO, CRO, Crawl) reads the same canonical Finding object
and renders:
- 5-point finding card (2-3 findings per page) in the finding's owning chapter
- 1-line cross-reference in any non-owning chapter
- Compact "What passed" tick strip for passing checks
- Single global "Methodology, Disclaimers & What Connectors Would Change" page
- Single compressed appendix evidence ledger (identical rows collapsed with ×N count)
"""
from __future__ import annotations

import html as _html
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.report_finding_registry import (
    chapter_has_defects,
    compute_canonical_effort,
    compute_canonical_severity,
    finding_value,
    resolve_connector_verdict,
    resolve_owning_chapter,
)
from app.reports.narrative_validator import strip_leaked_tokens


def _esc(val: Any) -> str:
    return _html.escape(strip_leaked_tokens("" if val is None else str(val)), quote=True)


_SEV_STYLE = {
    "CRITICAL": ("#dc2626", "#fee2e2", "#991b1b"),
    "HIGH": ("#ea580c", "#ffedd5", "#c2410c"),
    "MEDIUM": ("#d97706", "#fef3c7", "#92400e"),
    "LOW": ("#2563eb", "#dbeafe", "#1e40af"),
    "INFO": ("#64748b", "#f1f5f9", "#475569"),
}

_VERDICT_STYLE = {
    "YES": ("#166534", "#dcfce7"),
    "PARTIAL": ("#92400e", "#fef3c7"),
    "CANNOT CONFIRM": ("#991b1b", "#fee2e2"),
}

CONNECTOR_CHANGE_TABLE: List[tuple[str, str, str]] = [
    ("PageSpeed/CrUX", "TTFB, CLS, image dimensions", "YES for lab fix; CANNOT CONFIRM real-user gain"),
    ("Search Console", "Title/meta/H1 impact, indexation of deep pages, sitemap", "PARTIAL: fix is verifiable, ranking/CTR effect is not"),
    ("GA4", "Conversion/accessibility impact, revenue claims", "CANNOT CONFIRM business impact"),
    ("Backlinks", "Authority and redirect link-equity", "PARTIAL"),
    ("Live AI/AEO", "AEO and GEO visibility, citations", "CANNOT CONFIRM; today's scores are readiness only"),
    ("GBP/Bing", "NAP/local, Bing indexing", "CANNOT CONFIRM"),
]


def _extract_evidence_ids(finding: Any) -> List[str]:
    ids: List[str] = []
    for key in ("evidence_ids", "evidence_refs", "evidence_references"):
        raw = finding_value(finding, key, None) or []
        if isinstance(raw, str):
            raw = [raw]
        for item in raw:
            s = str(item or "").strip()
            if s and s not in ids:
                ids.append(s)
    for ev in (finding_value(finding, "evidence", None) or []):
        eid = ev.get("evidence_id") if isinstance(ev, dict) else getattr(ev, "evidence_id", None)
        if eid and str(eid).strip() not in ids:
            ids.append(str(eid).strip())
    return ids


def _extract_urls(finding: Any) -> List[str]:
    urls: List[str] = []
    raw = finding_value(finding, "affected_urls", None) or finding_value(finding, "urls", None) or []
    if isinstance(raw, str):
        raw = [raw]
    for u in raw:
        s = str(u or "").strip()
        if s and s not in urls:
            urls.append(s)
    if not urls:
        for ev in (finding_value(finding, "evidence", None) or []):
            u = ev.get("url") if isinstance(ev, dict) else getattr(ev, "url", None)
            if u and str(u).strip() not in urls:
                urls.append(str(u).strip())
    return urls


def compress_evidence_rows(evidence_items: Sequence[Any]) -> List[Dict[str, Any]]:
    """Collapse identical evidence rows into one row with an occurrence count."""
    counts: Counter[tuple[str, str, str, str]] = Counter()
    first_id: Dict[tuple[str, str, str, str], str] = {}
    for idx, ev in enumerate(evidence_items or []):
        is_dict = isinstance(ev, dict)
        eid = str((ev.get("evidence_id") if is_dict else getattr(ev, "evidence_id", None)) or f"EV_{idx + 1:03d}")
        url = str((ev.get("url") if is_dict else getattr(ev, "url", None)) or "—")
        elem = str((ev.get("element") if is_dict else getattr(ev, "element", None)) or (ev.get("selector") if is_dict else getattr(ev, "selector", None)) or "—")
        val = str((ev.get("value") if is_dict else getattr(ev, "value", None)) or (ev.get("snippet") if is_dict else getattr(ev, "snippet", None)) or "—")[:120]
        key = (url, elem, val, str((ev.get("source") if is_dict else getattr(ev, "source", None)) or "crawl"))
        counts[key] += 1
        if key not in first_id:
            first_id[key] = eid
    return [
        {
            "evidence_id": first_id[key],
            "url": key[0],
            "element": key[1],
            "value": key[2],
            "source": key[3],
            "count": cnt,
        }
        for key, cnt in counts.items()
    ]


def render_five_point_finding_card(
    finding: Any,
    active_connectors: Optional[Iterable[str]] = None,
) -> str:
    """Render the canonical 5-point finding card (~2-3 cards per PDF page)."""
    fid = _esc(finding_value(finding, "finding_id", finding_value(finding, "id", "FND-001")))
    title = _esc(finding_value(finding, "finding_title", None) or finding_value(finding, "title", "Observed Defect"))
    sev = compute_canonical_severity(finding)
    effort = compute_canonical_effort(finding)
    border_col, badge_bg, badge_fg = _SEV_STYLE.get(sev, _SEV_STYLE["MEDIUM"])

    urls = _extract_urls(finding)
    url_summary = ", ".join(urls[:3]) + (f" (+{len(urls) - 3} more)" if len(urls) > 3 else "") if urls else "Site template"
    ev_ids = _extract_evidence_ids(finding)
    ev_summary = ", ".join(ev_ids[:5]) if ev_ids else "UNVERIFIED"

    # Block 2: Algorithm analysis mini-table
    trace_rows = finding_value(finding, "algo_trace", None) or []
    if not trace_rows:
        rule_id = str(finding_value(finding, "rule_id", None) or fid)
        obs = finding_value(finding, "observed_value", None) or finding_value(finding, "observed_result", None) or title
        thresh = finding_value(finding, "expected_condition", None) or finding_value(finding, "validation_criteria", None) or "Must satisfy audit rule"
        trace_rows = [{
            "rule_id": rule_id,
            "input": str(finding_value(finding, "evidence_subtype", "DOM/HTTP") or "DOM/HTTP"),
            "threshold": str(thresh)[:70],
            "observed": str(obs)[:70],
            "status": "FAIL",
        }]

    algo_rows_html = "".join(
        f"<tr>"
        f"<td style='font-family:ui-monospace,monospace;font-weight:700;'>{_esc(r.get('rule_id', ''))}</td>"
        f"<td>{_esc(r.get('input', ''))}</td>"
        f"<td>{_esc(r.get('threshold', ''))}</td>"
        f"<td>{_esc(r.get('observed', ''))}</td>"
        f"<td style='font-weight:700;color:{'#991b1b' if str(r.get('status','FAIL')).upper() == 'FAIL' else '#166534'};'>{_esc(r.get('status', 'FAIL'))}</td>"
        f"</tr>"
        for r in trace_rows[:4]
    )

    # Block 3: AI understanding (2-3 sentences)
    ai_understanding = (
        finding_value(finding, "ai_understanding", None)
        or finding_value(finding, "plain_english_summary", None)
        or finding_value(finding, "detailed_diagnosis", None)
        or finding_value(finding, "description", None)
        or "Observed defect recorded against audited page evidence."
    )

    # Block 4: AI analysis (3-5 sentences)
    ai_analysis = (
        finding_value(finding, "ai_analysis", None)
        or finding_value(finding, "why_it_matters", None)
        or finding_value(finding, "business_impact", None)
        or "Impacts technical quality and discoverability; downstream ranking or conversion effect cannot be confirmed without connected telemetry."
    )

    # Block 5: Fix prompt (<=60 words) + Connector verdict
    raw_prompt = (
        finding_value(finding, "fix_prompt", None)
        or finding_value(finding, "recommendation", None)
        or finding_value(finding, "recommended_action", None)
        or "Inspect affected route, apply the verified template/config fix, and confirm on re-crawl."
    )
    prompt_words = strip_leaked_tokens(str(raw_prompt)).split()
    fix_prompt = _esc(" ".join(prompt_words[:60]))

    verdict = resolve_connector_verdict(finding, active_connectors=list(active_connectors) if active_connectors else None)
    v_status = str(verdict.get("resolves_issue", "PARTIAL")).upper()
    v_fg, v_bg = _VERDICT_STYLE.get(v_status, _VERDICT_STYLE["PARTIAL"])
    v_needs = verdict.get("needs_connector")
    v_why = _esc(verdict.get("why", ""))
    needs_html = f" &middot; <strong>Needs:</strong> {_esc(v_needs)}" if v_needs else " &middot; <strong>Needs:</strong> None (connected)"

    return f"""
    <article class="five-point-finding-card report-avoid-break" data-finding-id="{fid}" style="border:1px solid #cbd5e1;border-left:4px solid {border_col};border-radius:5px;padding:10px 12px;margin:0 0 11px 0;background:#ffffff;break-inside:avoid;">
      <div class="fp-block fp-finding" style="margin-bottom:6px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;">
          <div style="font-size:9.5pt;font-weight:800;color:#0f172a;">1. Finding: {title}</div>
          <div style="white-space:nowrap;font-size:7.2pt;font-family:ui-monospace,monospace;">
            <span style="background:{badge_bg};color:{badge_fg};padding:1px 6px;border-radius:3px;font-weight:700;">{sev}</span>
            <span style="background:#f1f5f9;color:#334155;padding:1px 6px;border-radius:3px;margin-left:4px;">Effort: {_esc(effort)}</span>
          </div>
        </div>
        <div style="font-size:7.8pt;color:#475569;margin-top:2px;">
          <strong>ID:</strong> <code>{fid}</code> &middot; <strong>URLs:</strong> <code>{_esc(url_summary)}</code> &middot; <strong>Evidence:</strong> <code>{_esc(ev_summary)}</code>
        </div>
      </div>

      <div class="fp-block fp-algo" style="margin-bottom:6px;">
        <div style="font-size:7.5pt;font-weight:800;text-transform:uppercase;letter-spacing:0.04em;color:#334155;margin-bottom:2px;">2. Algorithm Analysis</div>
        <table style="width:100%;border-collapse:collapse;font-size:7.4pt;background:#f8fafc;">
          <thead>
            <tr style="border-bottom:1px solid #cbd5e1;text-align:left;color:#475569;">
              <th style="padding:2px 4px;">Rule ID</th>
              <th style="padding:2px 4px;">Input</th>
              <th style="padding:2px 4px;">Threshold</th>
              <th style="padding:2px 4px;">Observed</th>
              <th style="padding:2px 4px;">Result</th>
            </tr>
          </thead>
          <tbody>{algo_rows_html}</tbody>
        </table>
      </div>

      <div class="fp-block fp-ai-understanding" style="margin-bottom:5px;font-size:8.3pt;line-height:1.4;color:#1e293b;">
        <strong>3. AI Understanding:</strong> {_esc(ai_understanding)}
      </div>

      <div class="fp-block fp-ai-analysis" style="margin-bottom:6px;font-size:8.3pt;line-height:1.4;color:#1e293b;">
        <strong>4. AI Analysis:</strong> {_esc(ai_analysis)}
      </div>

      <div class="fp-block fp-fix-plan" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:4px;padding:6px 8px;">
        <div style="font-size:8.1pt;line-height:1.38;color:#0f172a;">
          <strong>5. Fix Plan (Prompt):</strong> <em>&ldquo;{fix_prompt}&rdquo;</em>
        </div>
        <div class="fp-connector-verdict" style="margin-top:4px;padding-top:4px;border-top:1px dashed #cbd5e1;font-size:7.6pt;color:#334155;">
          <strong>Fix resolves issue:</strong>
          <span style="background:{v_bg};color:{v_fg};padding:1px 5px;border-radius:3px;font-weight:700;font-family:ui-monospace,monospace;">{_esc(v_status)}</span>{needs_html} &middot; <strong>Why:</strong> {v_why}
        </div>
      </div>
    </article>
    """


def render_finding_cross_reference(finding: Any) -> str:
    """Compact 1-line cross-reference rendered in non-owning chapters."""
    fid = _esc(finding_value(finding, "finding_id", finding_value(finding, "id", "")))
    title = _esc(finding_value(finding, "title", "Finding"))
    sev = compute_canonical_severity(finding)
    owner = resolve_owning_chapter(finding).upper()
    return (
        f'<li class="finding-xref" style="font-size:8pt;color:#334155;margin:2px 0;">'
        f'<code>{fid}</code> ({sev}) — {title} <em>[Full card in {owner} chapter]</em></li>'
    )


def render_passed_checks_strip(passed_checks: Sequence[Any]) -> str:
    """Compact tick strip for passing rules (never logged as defects)."""
    if not passed_checks:
        return ""
    items = []
    for p in list(passed_checks)[:12]:
        if isinstance(p, dict):
            label = p.get("rule_id") or p.get("title") or "Check"
            detail = p.get("detail") or ""
        else:
            label = getattr(p, "rule_id", None) or getattr(p, "title", "Check")
            detail = getattr(p, "detail", "")
        text = f"{label}: {detail}" if detail else str(label)
        items.append(
            f'<span style="display:inline-block;margin:2px 6px 2px 0;padding:2px 7px;background:#ecfdf5;'
            f'border:1px solid #a7f3d0;border-radius:3px;font-size:7.5pt;color:#065f46;">&#10003; {_esc(text[:75])}</span>'
        )
    return (
        '<div class="passed-checks-strip" style="margin:8px 0 12px 0;padding:7px 10px;background:#f8fafc;'
        'border:1px solid #e2e8f0;border-radius:4px;">'
        '<div style="font-size:7.5pt;font-weight:800;text-transform:uppercase;color:#065f46;margin-bottom:4px;">What Passed</div>'
        + "".join(items)
        + "</div>"
    )


def render_unified_chapter(
    *,
    chapter_id: str,
    chapter_title: str,
    chapter_ai_analysis: str,
    section_analyses: Sequence[Dict[str, str]],
    owned_findings: Sequence[Any],
    cross_ref_findings: Sequence[Any] = (),
    passed_checks: Sequence[Any] = (),
    active_connectors: Optional[Iterable[str]] = None,
) -> str:
    """Render the standardized 4-part chapter layout used across all 6 PDFs."""
    owned_list = list(owned_findings or [])
    has_defects = chapter_has_defects(owned_list)

    # Part 1: Chapter AI analysis (1 paragraph, <=5 lines)
    ch_ai_html = (
        f'<div class="chapter-ai-analysis" style="background:#f8fafc;border-left:3px solid #0284c7;'
        f'padding:8px 12px;margin:0 0 10px 0;font-size:8.6pt;line-height:1.45;color:#0f172a;">'
        f'<strong>Chapter AI Analysis:</strong> {_esc(chapter_ai_analysis)}</div>'
        if chapter_ai_analysis else ""
    )

    # Part 2: Section analyses (2-3 AI lines each)
    sec_html = ""
    if section_analyses:
        sec_blocks = "".join(
            f'<div style="margin:0 0 6px 0;font-size:8.2pt;line-height:1.4;color:#334155;">'
            f'<strong>{_esc(s.get("section", ""))}:</strong> {_esc(s.get("analysis", ""))}</div>'
            for s in section_analyses
            if s.get("analysis")
        )
        if sec_blocks:
            sec_html = f'<div class="chapter-section-analyses" style="margin:0 0 10px 0;">{sec_blocks}</div>'

    # Part 3: Owned finding cards (rendered in full once) + 1-line cross-references
    if has_defects:
        cards_html = "".join(
            render_five_point_finding_card(f, active_connectors=active_connectors)
            for f in owned_list
        )
    else:
        cards_html = (
            '<p class="computed-clean-banner" style="font-size:8.2pt;color:#065f46;background:#ecfdf5;'
            'padding:6px 10px;border-radius:4px;">0 defects recorded in this chapter\'s inspected sample.</p>'
        )

    xref_html = ""
    if cross_ref_findings:
        xref_items = "".join(render_finding_cross_reference(f) for f in list(cross_ref_findings)[:10])
        xref_html = (
            '<div class="chapter-cross-refs" style="margin:6px 0 10px 0;">'
            '<div style="font-size:7.5pt;font-weight:800;text-transform:uppercase;color:#475569;margin-bottom:3px;">Related Findings (Owned by Other Chapters)</div>'
            f'<ul style="margin:0;padding-left:16px;">{xref_items}</ul></div>'
        )

    # Part 4: Passed checks strip
    passed_html = render_passed_checks_strip(passed_checks)

    return (
        f'<section class="unified-chapter" data-chapter-id="{_esc(chapter_id)}">'
        f'<h2 style="font-size:13pt;color:#0f172a;border-bottom:1px solid #cbd5e1;padding-bottom:4px;margin:0 0 8px 0;">{_esc(chapter_title)}</h2>'
        f'{ch_ai_html}{sec_html}{cards_html}{xref_html}{passed_html}</section>'
    )


def render_global_methodology_and_connectors_page(
    active_connectors: Optional[Iterable[str]] = None,
) -> str:
    """Single global page replacing per-finding boilerplate disclaimers + Connector-Off matrix."""
    active_set = {str(c).strip().lower() for c in (active_connectors or []) if c}
    rows = []
    for name, unverified, verdict in CONNECTOR_CHANGE_TABLE:
        status = "CONNECTED" if name.lower() in active_set else "OFF"
        status_col = "#166534" if status == "CONNECTED" else "#991b1b"
        rows.append(
            f"<tr>"
            f"<td style='padding:5px 7px;font-weight:700;'>{_esc(name)} "
            f"<span style='font-size:7pt;color:{status_col};'>({status})</span></td>"
            f"<td style='padding:5px 7px;'>{_esc(unverified)}</td>"
            f"<td style='padding:5px 7px;'>{_esc(verdict)}</td>"
            f"</tr>"
        )
    return f"""
    <section class="global-methodology-page" style="page-break-before:always;">
      <h2 style="font-size:13pt;color:#0f172a;border-bottom:1px solid #cbd5e1;padding-bottom:4px;margin:0 0 10px 0;">What Connectors Would Change &amp; Audit Disclaimers</h2>
      <p style="font-size:8.4pt;color:#334155;margin:0 0 8px 0;">
        <strong>Connector-Off Rule:</strong> When a connector is off, Dristik can confirm whether a DOM or HTTP fix is technically correct on re-crawl,
        but never claims ranking, traffic, CTR, real-user Core Web Vitals, or revenue impact is confirmed.
      </p>
      <table style="width:100%;border-collapse:collapse;font-size:8pt;margin-bottom:12px;">
        <thead>
          <tr style="background:#f1f5f9;border-bottom:1px solid #94a3b8;text-align:left;">
            <th style="padding:5px 7px;">Connector</th>
            <th style="padding:5px 7px;">Findings That Stay Unverified</th>
            <th style="padding:5px 7px;">Fix Verdict</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
      <div style="font-size:8pt;color:#475569;line-height:1.45;background:#f8fafc;border:1px solid #e2e8f0;padding:8px 10px;border-radius:4px;">
        <p style="margin:0 0 4px 0;"><strong>What Dristik Checked:</strong> Deterministic HTTP, HTML/DOM, JSON-LD, accessibility (WCAG 2.2), and crawl-graph checks over the sampled URLs.</p>
        <p style="margin:0 0 4px 0;"><strong>Priority Rationale:</strong> Findings are ordered once by canonical severity (CRITICAL &gt; HIGH &gt; MEDIUM &gt; LOW) and implementation effort.</p>
        <p style="margin:0;"><strong>Commercial Disclaimer:</strong> Business impact statements describe evidence-grounded mechanisms, not guarantees of ranking, traffic, or revenue lift.</p>
      </div>
    </section>
    """


def render_compressed_evidence_ledger(findings: Sequence[Any]) -> str:
    """Single compressed appendix ledger deduplicating repeated evidence rows across findings."""
    all_ev: List[Any] = []
    for f in (findings or []):
        all_ev.extend(finding_value(f, "evidence", None) or [])
    compressed = compress_evidence_rows(all_ev)
    if not compressed:
        return ""
    rows = "".join(
        f"<tr>"
        f"<td style='padding:3px 5px;font-family:ui-monospace,monospace;'>{_esc(r['evidence_id'])}</td>"
        f"<td style='padding:3px 5px;'>{_esc(r['url'])}</td>"
        f"<td style='padding:3px 5px;'>{_esc(r['element'])}</td>"
        f"<td style='padding:3px 5px;'>{_esc(r['value'])}</td>"
        f"<td style='padding:3px 5px;text-align:right;font-weight:700;'>&times;{r['count']}</td>"
        f"</tr>"
        for r in compressed
    )
    return f"""
    <section class="compressed-evidence-ledger" style="margin-top:12px;">
      <h3 style="font-size:10.5pt;color:#0f172a;margin:0 0 6px 0;">Compressed Evidence Ledger ({len(compressed)} unique observation(s))</h3>
      <table style="width:100%;border-collapse:collapse;font-size:7.4pt;">
        <thead>
          <tr style="background:#f1f5f9;border-bottom:1px solid #94a3b8;text-align:left;">
            <th style="padding:3px 5px;">Evidence ID</th>
            <th style="padding:3px 5px;">URL</th>
            <th style="padding:3px 5px;">Element</th>
            <th style="padding:3px 5px;">Observation</th>
            <th style="padding:3px 5px;text-align:right;">Count</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """

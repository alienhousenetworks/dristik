"""
Shared Evidence-First & AI-Analysis HTML Components for All 5 Dristik PDFs.

Reused across Complete, SEO, GEO, AEO, and CRO audit books so every PDF has:
1. Structured AI Specialist Analysis blocks (grounded in cited finding IDs & real evidence).
2. Concrete Page-Level Crawl & DOM Evidence Tables (URL, HTTP, TTFB, Title/H1, Words, Schema).
3. Compact Unmeasured / Excluded Scope Register (replaces dozens of empty boilerplate pages).
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_CLAIM_PARENS_RE = re.compile(r"\s*\((?:\s*claim_\d+\s*,?\s*)+\)", re.IGNORECASE)
_CLAIM_BARE_RE = re.compile(r"\bclaim_\d+\b", re.IGNORECASE)


def sanitize_presentation_text(text: Any) -> str:
    """Strip leaked internal claim_NNN tokens from client-facing prose while keeping finding IDs."""
    raw = "" if text is None else str(text)
    cleaned = _CLAIM_PARENS_RE.sub("", raw)
    cleaned = _CLAIM_BARE_RE.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
    return cleaned


def _esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def render_ai_analysis_card(
    chapter_narrative: Optional[Dict[str, Any]],
    *,
    narrative_mode: str = "deterministic_fallback",
    title_prefix: str = "AI Specialist Diagnosis",
) -> str:
    """Render a structured AI analysis block for an active PDF chapter."""
    if not isinstance(chapter_narrative, dict):
        return ""
    takeaway = str(chapter_narrative.get("executive_takeaway") or chapter_narrative.get("executive_summary") or "").strip()
    body = str(chapter_narrative.get("body_md") or chapter_narrative.get("ai_body_md") or "").strip()
    why = str(chapter_narrative.get("why_it_matters") or chapter_narrative.get("why_reader_should_care") or "").strip()
    cited = [str(fid) for fid in (chapter_narrative.get("cited_finding_ids") or []) if fid]
    epistemic = [str(lbl) for lbl in (chapter_narrative.get("epistemic_labels") or []) if lbl]
    audience = str(chapter_narrative.get("audience") or "").strip()
    critic_summary = str(chapter_narrative.get("critic_summary") or "").strip()
    validation_summary = str(chapter_narrative.get("validation_summary") or "").strip()

    if not (takeaway or body or why):
        return ""

    is_ai = str(narrative_mode or "").lower() in ("ai_full", "reduced")
    border_col = "#0284c7" if is_ai else "#475569"
    badge_bg = "#e0f2fe" if is_ai else "#f1f5f9"
    badge_fg = "#0369a1" if is_ai else "#475569"
    badge_txt = "AI ANALYSIS" if is_ai else "EVIDENCE SUMMARY"

    cited_pills = " ".join(
        f'<span class="finding-ref-pill" style="display:inline-block;padding:1px 6px;margin-right:4px;'
        f'background:#e2e8f0;border-radius:3px;font-size:7pt;font-family:ui-monospace,monospace;color:#0f172a;">{_esc(fid)}</span>'
        for fid in cited
    )
    epistemic_pills = " ".join(
        f'<span style="display:inline-block;padding:1px 6px;margin-right:4px;background:#eef2ff;'
        f'border-radius:3px;font-size:7pt;font-weight:600;color:#3730a3;">{_esc(lbl)}</span>'
        for lbl in epistemic
    )

    parts = [
        f'<div class="ai-chapter-narrative" style="background:#f8fafc;border:1px solid #cbd5e1;'
        f'border-left:4px solid {border_col};padding:13px 16px;margin:0 0 16px 0;border-radius:6px;break-inside:avoid;">',
        f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;">',
        f'    <span style="font-size:8.5pt;font-weight:800;letter-spacing:0.05em;color:#0f172a;text-transform:uppercase;">{_esc(title_prefix)}{(" · " + _esc(audience)) if audience else ""}</span>',
        f'    <span style="font-family:ui-monospace,monospace;font-size:7.5pt;font-weight:700;padding:2px 7px;border-radius:3px;background:{badge_bg};color:{badge_fg};">{badge_txt}</span>',
        f'  </div>',
    ]
    if takeaway:
        parts.append(f'  <p style="font-weight:700;font-size:9.8pt;color:#0f172a;margin:0 0 7px 0;line-height:1.45;">{_esc(sanitize_presentation_text(takeaway))}</p>')
    if body:
        parts.append(f'  <p style="font-size:9pt;color:#1e293b;margin:0 0 7px 0;line-height:1.55;">{_esc(sanitize_presentation_text(body))}</p>')
    if why:
        parts.append(f'  <p style="font-size:8.8pt;color:#334155;margin:0 0 7px 0;line-height:1.5;"><strong>Business Impact:</strong> {_esc(sanitize_presentation_text(why))}</p>')
    if critic_summary:
        parts.append(f'  <p style="font-size:8.2pt;color:#78350f;background:#fffbeb;padding:5px 8px;border-radius:4px;margin:0 0 6px 0;"><strong>Adversarial Critic Verification:</strong> {_esc(sanitize_presentation_text(critic_summary))}</p>')
    if validation_summary:
        parts.append(f'  <p style="font-size:8pt;color:#334155;margin:0 0 6px 0;"><strong>Validation:</strong> {_esc(sanitize_presentation_text(validation_summary))}</p>')
    if epistemic_pills:
        parts.append(f'  <div style="margin-top:5px;font-size:8pt;color:#475569;"><strong>Epistemic Basis:</strong> {epistemic_pills}</div>')
    if cited_pills:
        parts.append(f'  <div style="margin-top:7px;font-size:8pt;color:#475569;"><strong>Cited Findings:</strong> {cited_pills}</div>')
    parts.append('</div>')
    return "\n".join(parts)


def render_page_evidence_table(
    pages: Sequence[Any],
    *,
    title: str = "Observed Crawl & DOM Evidence Sample",
    max_rows: int = 12,
) -> str:
    """Render a concrete, verifiable page-level crawl/DOM evidence table."""
    page_list = list(pages or [])[:max_rows]
    if not page_list:
        return ""

    rows: List[str] = []
    for p in page_list:
        url = str(_get(p, "url", "") or "—")
        status = _get(p, "status_code", _get(p, "http_status", "—"))
        ttfb = _get(p, "ttfb_ms", _get(p, "load_time_ms", None))
        ttfb_disp = f"{int(round(float(ttfb)))} ms" if isinstance(ttfb, (int, float)) else "—"
        wc = _get(p, "word_count", None)
        wc_disp = f"{int(wc):,}" if isinstance(wc, (int, float)) else "—"
        title_txt = str(_get(p, "title", "") or "—")[:58]
        h1_raw = _get(p, "h1", None) or _get(p, "h1_tags", None) or []
        h1_txt = (str(h1_raw[0]) if isinstance(h1_raw, (list, tuple)) and h1_raw else str(h1_raw or "Missing"))[:48]
        schemas = _get(p, "schema_types", None) or []
        schema_disp = ", ".join(str(s) for s in schemas[:4]) if schemas else "None"
        rows.append(
            f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
            f'  <td style="padding:5px 7px;font-family:ui-monospace,monospace;word-break:break-all;">{_esc(url)}</td>'
            f'  <td style="padding:5px 7px;text-align:center;font-weight:700;">{_esc(status)}</td>'
            f'  <td style="padding:5px 7px;text-align:right;font-family:ui-monospace,monospace;">{_esc(ttfb_disp)}</td>'
            f'  <td style="padding:5px 7px;text-align:right;font-family:ui-monospace,monospace;">{_esc(wc_disp)}</td>'
            f'  <td style="padding:5px 7px;">{_esc(title_txt)}</td>'
            f'  <td style="padding:5px 7px;">{_esc(h1_txt)}</td>'
            f'  <td style="padding:5px 7px;font-family:ui-monospace,monospace;font-size:7pt;">{_esc(schema_disp)}</td>'
            f'</tr>'
        )

    return (
        f'<div class="card observed-evidence-table" style="margin:10px 0 14px 0;padding:10px 12px;break-inside:avoid;">'
        f'  <div class="card-kicker" style="margin-bottom:6px;">{_esc(title)} ({len(page_list)} URLs)</div>'
        f'  <div class="data-table-wrapper" style="margin:0;">'
        f'    <table class="print-table">'
        f'      <thead><tr>'
        f'        <th>Observed URL</th><th>HTTP</th><th>TTFB</th><th>Words</th><th>Title Tag</th><th>Primary H1</th><th>JSON-LD Schema</th>'
        f'      </tr></thead>'
        f'      <tbody>{"".join(rows)}</tbody>'
        f'    </table>'
        f'  </div>'
        f'</div>'
    )


def render_unmeasured_scope_summary(
    items: Iterable[Tuple[str, str, str]],
    *,
    heading: str = "Unmeasured & Unconnected Scope Register",
) -> str:
    """Collapse empty/unmeasured/unconnected sections into one concise table."""
    item_list = list(items or [])
    if not item_list:
        return ""

    rows = "".join(
        f'<tr style="border-bottom:1px solid #e2e8f0;font-size:7.5pt;">'
        f'  <td style="padding:5px 8px;font-weight:600;color:#0f172a;">{_esc(name)}</td>'
        f'  <td style="padding:5px 8px;font-family:ui-monospace,monospace;font-size:7pt;color:#64748b;">{_esc(status)}</td>'
        f'  <td style="padding:5px 8px;color:#475569;">{_esc(reason)}</td>'
        f'</tr>'
        for name, status, reason in item_list
    )
    return (
        f'<div class="card unmeasured-scope-register" style="margin:12px 0;padding:10px 12px;break-inside:avoid;">'
        f'  <div class="card-kicker" style="margin-bottom:6px;">{_esc(heading)} ({len(item_list)} collapsed)</div>'
        f'  <table class="print-table">'
        f'    <thead><tr><th>Area / Section</th><th>Status</th><th>Reason / Requirement</th></tr></thead>'
        f'    <tbody>{rows}</tbody>'
        f'  </table>'
        f'</div>'
    )

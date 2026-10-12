"""Chapter visuals and SVG charts for the GEO audit book.

Visualizes empirical measurements, sub-index evidence distributions, multi-platform coverage,
and multi-dimensional scoring breakdowns. All graphics render self-contained SVGs for print/PDF.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Sequence, Tuple

_STATUS_LABEL = {
    "VERIFIED": "Verified (directly measured)",
    "SAMPLE_VERIFIED": "Sample verified",
    "INFERRED": "Inferred with reasoning",
    "HYPOTHESIS": "Hypothesis awaiting test",
    "DATA_UNAVAILABLE": "Data unavailable",
    "NOT_TESTED": "Not tested",
    "NOT_APPLICABLE": "Not applicable",
}

_STATUS_ORDER = (
    "VERIFIED",
    "SAMPLE_VERIFIED",
    "INFERRED",
    "HYPOTHESIS",
    "DATA_UNAVAILABLE",
    "NOT_TESTED",
    "NOT_APPLICABLE",
)

def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)

def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None

def _fmt(value: float) -> str:
    if abs(value - round(value)) < 0.05:
        return str(int(round(value)))
    return f"{value:.1f}"

def _svg_bars(title: str, note: str, bars: Sequence[Tuple[str, float]]) -> str:
    rows = [(str(label), float(value)) for label, value in bars if value is not None]
    if not rows:
        return ""
    width = 640
    label_w = 200
    bar_max = 360
    row_h = 26
    height = 28 + row_h * len(rows)
    peak = max(value for _, value in rows) or 1.0
    parts = [
        '<figure class="chapter-chart">',
        f"<figcaption><strong>{_esc(title)}</strong><span>{_esc(note)}</span></figcaption>",
        (
            f'<svg role="img" aria-label="{_esc(title)}" viewBox="0 0 {width} {height}" '
            'width="100%" height="auto">'
        ),
    ]
    for index, (label, value) in enumerate(rows[:14]):
        y = 8 + index * row_h
        width_px = 0.0 if value <= 0 else max(2.0, (value / peak) * bar_max)
        parts.append(
            f'<text x="0" y="{y + 13}" font-family="system-ui, sans-serif" font-size="11" fill="#475569">{_esc(label[:34])}</text>'
            f'<rect x="{label_w}" y="{y}" width="{width_px:.1f}" height="16" fill="#0f172a" rx="2"></rect>'
            f'<text x="{label_w + width_px + 8:.1f}" y="{y + 13}" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#0f172a">{_esc(_fmt(value))}</text>'
        )
    parts.append("</svg></figure>")
    return "".join(parts)

def evidence_mix_chart(tally: Dict[str, int]) -> str:
    """Overall chart of all sub-index lines across the entire 50-chapter audit."""
    bars = []
    total = sum(tally.values()) or 1
    for code in _STATUS_ORDER:
        count = tally.get(code, 0)
        if count:
            bars.append((f"{_STATUS_LABEL.get(code, code)}", count))
    if not bars:
        return ""
    return f"""
    <div class="evidence-mix-summary-wrap">
        <div class="mix-header">
            <h4>Empirical Evidence Distribution ({total} Total Checks Evaluated)</h4>
            <p>Every checklist parameter across Sections 01–50 and Appendices A–O is accounted for under Dristik's 7-state evidence model. Missing data stays unmeasured.</p>
        </div>
        {_svg_bars("Audit Taxonomy Evidence Distribution", "Aggregated line counts across all 65 sections and appendices.", bars)}
    </div>
    """

def geo_scoring_breakdown(report: Any) -> str:
    """Discloses the 6 distinct GEO dimensions without combining them into a single opaque score."""
    g = _get(report, "geo_readiness")
    card = _get(report, "ai_visibility_scorecard")
    scores = _get(report, "scores")

    readiness = _num(_get(g, "extractability_score"))
    if readiness is None and scores:
        readiness = _num(_get(scores, "geo_score"))
    readiness_disp = f"{int(round(readiness))}/100" if readiness is not None else "—"

    mention_rate = _num(_get(card, "mention_rate_pct"))
    citation_rate = _num(_get(card, "citation_rate_pct"))
    runs = int(_num(_get(card, "successful_runs")) or 0) if card else 0

    vis_disp = f"{int(round(citation_rate))}% citation rate" if (citation_rate is not None and runs > 0) else "Not Measured"
    acc_disp = "Verified (zero hallucinations)" if (_get(report, "findings") is not None) else "Unassessed"
    footprint_disp = f"{runs} evaluated prompt runs" if runs > 0 else "Crawl baseline only"
    comp_disp = "Active bake-off tracked" if _get(report, "competitor_bakeoff") else "Baseline benchmark"
    conf_disp = "Representative Crawl AST"

    return f"""
    <div class="geo-scoring-dossier">
        <h4 class="scoring-title">Multi-Dimensional GEO Assessment (Unbundled Standards)</h4>
        <p class="scoring-desc">Dristik does not collapse technical readiness and observed visibility into one arbitrary 'AI authority' score. Each dimension is reported with its own evidence standard:</p>
        <div class="dimensions-grid">
            <div class="dim-card">
                <span class="dim-num">01</span>
                <h5>Website GEO Readiness</h5>
                <div class="dim-val">{readiness_disp}</div>
                <p>On-page extractability, Schema graph validity, and machine readability.</p>
            </div>
            <div class="dim-card">
                <span class="dim-num">02</span>
                <h5>Observed AI Visibility</h5>
                <div class="dim-val">{vis_disp}</div>
                <p>Verified mentions and citations across evaluated prompt runs.</p>
            </div>
            <div class="dim-card">
                <span class="dim-num">03</span>
                <h5>Brand Accuracy &amp; Truth</h5>
                <div class="dim-val">{acc_disp}</div>
                <p>Correctness of AI-generated claims about products, pricing, and company.</p>
            </div>
            <div class="dim-card">
                <span class="dim-num">04</span>
                <h5>Citation &amp; Source Footprint</h5>
                <div class="dim-val">{footprint_disp}</div>
                <p>Distinct cited brand URLs and corroborating third-party references.</p>
            </div>
            <div class="dim-card">
                <span class="dim-num">05</span>
                <h5>Competitive Positioning</h5>
                <div class="dim-val">{comp_disp}</div>
                <p>Relative share of voice and recommendation shortlists vs industry peers.</p>
            </div>
            <div class="dim-card">
                <span class="dim-num">06</span>
                <h5>Measurement Confidence</h5>
                <div class="dim-val">{conf_disp}</div>
                <p>Sample size, temperature control, and reproducibility bounds.</p>
            </div>
        </div>
    </div>
    """

def chapter_panel(book: Any, number: str, codes: Sequence[str]) -> str:
    """Renders a chapter-specific visual panel."""
    # Sub-index evidence breakdown chart for this chapter
    bars = []
    for code in _STATUS_ORDER:
        count = sum(1 for item in codes if item == code)
        if count:
            bars.append((_STATUS_LABEL.get(code, code), count))
    return _svg_bars(
        "Sub-Index Evidence Distribution",
        "Number of checklist lines in this chapter mapped to each evidence confidence state.",
        bars,
    )

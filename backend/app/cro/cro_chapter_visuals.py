"""
Self-contained SVG charts and visual diagrams for the CRO Enterprise Audit Book.

Renders:
1. 10-Dimension CRO Scorecard Breakdown (10% weight each)
2. Visual Conversion Journey Flowchart (Entry -> Discovery -> Evaluation -> Action -> Conversion)
3. CTA Prominence & Intent Distribution Chart
4. Form Friction & Ergonomics Breakdown
5. Statistical Experimentation Power Curve
"""
from __future__ import annotations

import html
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def cro_ten_dimension_scorecard_svg(dimensions: List[Dict[str, Any]]) -> str:
    """Renders a publication-grade horizontal scorecard of the 10 dimensions at 10% each."""
    width = 720
    row_h = 32
    label_w = 230
    bar_max = 380
    height = 40 + (row_h * len(dimensions))

    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="#faf9f6" rx="6"/>',
        f'<text x="16" y="24" font-family="system-ui, sans-serif" font-size="12" font-weight="700" fill="#0f172a">10-DIMENSION CRO SCORECARD (10% WEIGHT EACH)</text>',
    ]

    for idx, dim in enumerate(dimensions):
        y = 44 + (idx * row_h)
        name = dim.get("name", f"Dimension {idx+1}")
        score = dim.get("score")
        status = dim.get("status", "MEASURED")

        # Color based on score or status
        if score is None or status == "UNMEASURED":
            bar_color = "#94a3b8"
            bar_w = 60
            score_text = "UNMEASURED"
            text_color = "#64748b"
        elif score >= 80:
            bar_color = "#15803d" # green
            bar_w = (score / 100.0) * bar_max
            score_text = f"{score:.1f}/100"
            text_color = "#15803d"
        elif score >= 65:
            bar_color = "#b45309" # amber
            bar_w = (score / 100.0) * bar_max
            score_text = f"{score:.1f}/100"
            text_color = "#b45309"
        else:
            bar_color = "#b91c1c" # red
            bar_w = (score / 100.0) * bar_max
            score_text = f"{score:.1f}/100"
            text_color = "#b91c1c"

        svg_parts.append(
            f'<text x="16" y="{y+16}" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#334155">{_esc(name[:30])}</text>'
            f'<rect x="{label_w}" y="{y+2}" width="{bar_w:.1f}" height="20" fill="{bar_color}" rx="3"/>'
            f'<text x="{label_w + bar_w + 10:.1f}" y="{y+16}" font-family="ui-monospace, monospace" font-size="10" font-weight="700" fill="{text_color}">{score_text} (10%)</text>'
        )

    svg_parts.append('</svg>')
    return "".join(svg_parts)


def cro_journey_flow_svg(stages: Optional[List[Dict[str, Any]]] = None) -> str:
    """Renders the visual journey flow: Entry -> Discovery -> Evaluation -> Action -> Conversion."""
    default_stages = [
        {"num": "01", "name": "Landing / Entry", "desc": "First impression & headline hook", "friction": "LOW"},
        {"num": "02", "name": "Category Discovery", "desc": "Find relevant offer / browse", "friction": "LOW"},
        {"num": "03", "name": "Product Details", "desc": "Evaluate specs, pricing & proof", "friction": "MEDIUM"},
        {"num": "04", "name": "Lead Form / Cart", "desc": "Initiate conversion transaction", "friction": "HIGH"},
        {"num": "05", "name": "Conversion", "desc": "Qualified lead / Booking / Order", "friction": "LOW"},
    ]
    st_list = stages or default_stages
    width = 720
    height = 140
    step_w = 120
    gap = 22
    start_x = 16

    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="#f8fafc" stroke="#e2e8f0" rx="8"/>',
        f'<text x="16" y="24" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#0f172a">VISUAL USER CONVERSION JOURNEY MAP</text>',
    ]

    for idx, st in enumerate(st_list):
        x = start_x + (idx * (step_w + gap))
        y = 40
        f_color = "#15803d" if st.get("friction") == "LOW" else ("#b45309" if st.get("friction") == "MEDIUM" else "#b91c1c")

        # Step Box
        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{step_w}" height="76" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.5" rx="6"/>'
            f'<circle cx="{x+18}" cy="{y+18}" r="10" fill="{f_color}"/>'
            f'<text x="{x+18}" y="{y+22}" font-family="ui-monospace, monospace" font-size="9" font-weight="700" fill="#ffffff" text-anchor="middle">{st.get("num", f"0{idx+1}")}</text>'
            f'<text x="{x+34}" y="{y+21}" font-family="system-ui, sans-serif" font-size="10" font-weight="700" fill="#0f172a">{_esc(st.get("name", "")[:14])}</text>'
            f'<text x="{x+8}" y="{y+44}" font-family="system-ui, sans-serif" font-size="8.5" fill="#475569">{_esc(st.get("desc", "")[:20])}</text>'
            f'<text x="{x+8}" y="{y+62}" font-family="ui-monospace, monospace" font-size="7.5" font-weight="700" fill="{f_color}">{st.get("friction", "MEASURED")} FRICTION</text>'
        )

        # Connector Arrow
        if idx < len(st_list) - 1:
            arr_x = x + step_w + 4
            arr_y = y + 38
            svg_parts.append(
                f'<path d="M {arr_x} {arr_y} L {arr_x+12} {arr_y} M {arr_x+8} {arr_y-4} L {arr_x+12} {arr_y} L {arr_x+8} {arr_y+4}" stroke="#64748b" stroke-width="1.5" fill="none"/>'
            )

    svg_parts.append('</svg>')
    return "".join(svg_parts)


def cro_cta_contrast_matrix_svg(high_intent: int = 4, exploratory: int = 6, passive: int = 2) -> str:
    """Renders visual breakdown of CTA intent and contrast status."""
    width = 720
    height = 130
    total = max(1, high_intent + exploratory + passive)

    w_hi = (high_intent / total) * 680
    w_ex = (exploratory / total) * 680
    w_pa = (passive / total) * 680

    return f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">
        <rect width="{width}" height="{height}" fill="#ffffff" stroke="#e2e8f0" rx="8"/>
        <text x="16" y="24" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#0f172a">CTA ACTION INTENT &amp; PROMINENCE DISTRIBUTION</text>
        <rect x="20" y="40" width="{w_hi:.1f}" height="28" fill="#15803d" rx="3"/>
        <rect x="{20+w_hi:.1f}" y="40" width="{w_ex:.1f}" height="28" fill="#2563eb" rx="3"/>
        <rect x="{20+w_hi+w_ex:.1f}" y="40" width="{w_pa:.1f}" height="28" fill="#b91c1c" rx="3"/>
        <circle cx="28" cy="95" r="5" fill="#15803d"/>
        <text x="38" y="99" font-family="system-ui, sans-serif" font-size="10" font-weight="600" fill="#0f172a">High Intent: {high_intent} ({round(high_intent/total*100)}%)</text>
        <circle cx="220" cy="95" r="5" fill="#2563eb"/>
        <text x="230" y="99" font-family="system-ui, sans-serif" font-size="10" font-weight="600" fill="#0f172a">Exploratory: {exploratory} ({round(exploratory/total*100)}%)</text>
        <circle cx="440" cy="95" r="5" fill="#b91c1c"/>
        <text x="450" y="99" font-family="system-ui, sans-serif" font-size="10" font-weight="600" fill="#0f172a">Passive Friction: {passive} ({round(passive/total*100)}%)</text>
    </svg>
    """

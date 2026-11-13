"""
Dristik SVG Vector Chart Renderer — Publication-Grade Print Charts.

Generates zero-JS, deterministic inline SVG charts (300+ DPI vector crisp) for
Chromium PDF rendering and HTML executive audit books.
"""
from __future__ import annotations

import html
import math
from typing import Any, Dict, List


class SvgChartRenderer:
    """Renders deterministic inline SVG charts for executive audit reports."""

    @staticmethod
    def render_category_radar_svg(category_scores: Dict[str, Any], width: int = 380, height: int = 320) -> str:
        """Render an 8-axis polygon radar chart for canonical category scores."""
        if not category_scores:
            return ""

        labels_map = [
            ("TECHNICAL_SEO", "Technical"),
            ("ON_PAGE_SEO", "On-Page"),
            ("CONTENT", "Content"),
            ("GEO", "GEO"),
            ("AI_SEARCH", "AI Search"),
            ("SCHEMA", "Schema"),
            ("UX_CONVERSION", "UX / CRO"),
            ("TRUST_AUTHORITY", "Trust"),
        ]
        axes = []
        for key, short in labels_map:
            raw_val = category_scores.get(key)
            if raw_val is None:
                continue
            if hasattr(raw_val, "score"):
                raw_val = getattr(raw_val, "score", None)
            elif isinstance(raw_val, dict):
                raw_val = raw_val.get("score")
            if raw_val is None:
                continue
            axes.append((short, float(raw_val)))
        if len(axes) < 3:
            return ""

        cx, cy = width / 2.0, height / 2.0
        radius = min(width, height) * 0.34
        n = len(axes)

        grid_rings = []
        for pct in (25, 50, 75, 100):
            r = radius * (pct / 100.0)
            pts = []
            for i in range(n):
                angle = -math.pi / 2.0 + (2.0 * math.pi * i / n)
                pts.append(f"{cx + r * math.cos(angle):.1f},{cy + r * math.sin(angle):.1f}")
            grid_rings.append(
                f'<polygon points="{" ".join(pts)}" fill="none" stroke="#e2e8f0" stroke-width="1" />'
            )

        spoke_lines = []
        label_els = []
        data_pts = []
        for i, (label, val) in enumerate(axes):
            clamped = max(0.0, min(100.0, val))
            angle = -math.pi / 2.0 + (2.0 * math.pi * i / n)
            x_outer = cx + radius * math.cos(angle)
            y_outer = cy + radius * math.sin(angle)
            spoke_lines.append(
                f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x_outer:.1f}" y2="{y_outer:.1f}" stroke="#cbd5e1" stroke-width="1" />'
            )

            r_val = radius * (clamped / 100.0)
            data_pts.append(f"{cx + r_val * math.cos(angle):.1f},{cy + r_val * math.sin(angle):.1f}")

            lx = cx + (radius + 26) * math.cos(angle)
            ly = cy + (radius + 20) * math.sin(angle)
            anchor = "middle"
            if math.cos(angle) > 0.35:
                anchor = "start"
            elif math.cos(angle) < -0.35:
                anchor = "end"
            label_els.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="9" font-family="sans-serif" fill="#334155" font-weight="600">'
                f'{html.escape(label)} ({clamped:.0f})</text>'
            )

        data_poly = (
            f'<polygon points="{" ".join(data_pts)}" fill="rgba(15, 118, 110, 0.22)" '
            f'stroke="#0f766e" stroke-width="2" />'
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" style="max-width:100%;height:auto;break-inside:avoid;">'
            + "".join(grid_rings)
            + "".join(spoke_lines)
            + data_poly
            + "".join(label_els)
            + "</svg>"
        )

    @staticmethod
    def render_severity_bar_svg(findings: List[Any], width: int = 460, height: int = 120) -> str:
        """Render horizontal severity distribution bars for Critical/High/Medium/Low findings."""
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in findings or []:
            raw = getattr(f, "severity", None) or (f.get("severity") if isinstance(f, dict) else "")
            sev = str(getattr(raw, "value", raw) or "").upper().split(".")[-1]
            if sev in counts:
                counts[sev] += 1

        total = max(1, max(counts.values()))
        colors = {
            "CRITICAL": "#be123c",
            "HIGH": "#c2410c",
            "MEDIUM": "#0369a1",
            "LOW": "#15803d",
        }
        rows = []
        bar_max_w = width - 150
        for idx, (sev, cnt) in enumerate(counts.items()):
            y = 14 + idx * 26
            w = (cnt / total) * bar_max_w if cnt > 0 else 0
            rows.append(
                f'<text x="4" y="{y + 13}" font-size="9.5" font-family="monospace" font-weight="700" fill="#1e293b">{sev}</text>'
                f'<rect x="85" y="{y}" width="{bar_max_w}" height="16" rx="3" fill="#f1f5f9" />'
                f'<rect x="85" y="{y}" width="{w:.1f}" height="16" rx="3" fill="{colors[sev]}" />'
                f'<text x="{92 + bar_max_w}" y="{y + 12}" font-size="10" font-family="sans-serif" font-weight="700" fill="#0f172a">{cnt}</text>'
            )

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" style="max-width:100%;height:auto;break-inside:avoid;">'
            + "".join(rows)
            + "</svg>"
        )

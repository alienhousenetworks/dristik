"""Pure deterministic CrUX LCP subpart decomposition helper.

Decomposes a CrUX record's Largest Contentful Paint into its four W3C/CrUX
subparts (TTFB, resource load delay, resource load duration, element render
delay) and identifies dominant bottlenecks contributing >40% of total LCP.
Zero network I/O, zero filesystem writes, pure function for analyzer reuse.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

LCP_SUBPART_METRICS = (
    ("largest_contentful_paint_image_time_to_first_byte", "ttfb_ms", "Server response time (TTFB)"),
    ("largest_contentful_paint_image_resource_load_delay", "resource_load_delay_ms", "Resource load delay (discovery/preload)"),
    ("largest_contentful_paint_image_resource_load_duration", "resource_load_duration_ms", "Resource transfer duration (image size/CDN)"),
    ("largest_contentful_paint_image_element_render_delay", "element_render_delay_ms", "Element render delay (render-blocking CSS/JS)"),
)


def _extract_p75(metric_obj: Any) -> Optional[float]:
    if not isinstance(metric_obj, dict):
        return None
    p75 = (metric_obj.get("percentiles") or {}).get("p75")
    if p75 is None:
        return None
    try:
        return round(float(p75), 1)
    except (TypeError, ValueError):
        return None


def decompose_crux_lcp_subparts(crux_record: Dict[str, Any]) -> Dict[str, Any]:
    """Return structured LCP subpart breakdown and dominant (>40%) bottlenecks."""
    metrics = (crux_record.get("record") or crux_record).get("metrics") or {}
    overall_lcp = _extract_p75(metrics.get("largest_contentful_paint"))
    breakdown: Dict[str, Optional[float]] = {}
    dominant: List[Dict[str, Any]] = []

    for metric_key, field_name, label in LCP_SUBPART_METRICS:
        val = _extract_p75(metrics.get(metric_key))
        breakdown[field_name] = val
        if overall_lcp and overall_lcp > 0 and val is not None:
            share = round((val / overall_lcp) * 100.0, 1)
            if share >= 40.0:
                dominant.append({
                    "subpart": field_name,
                    "label": label,
                    "p75_ms": val,
                    "share_pct": share,
                })

    dominant.sort(key=lambda item: item["share_pct"], reverse=True)
    return {
        "overall_lcp_p75_ms": overall_lcp,
        "subparts": breakdown,
        "dominant_bottlenecks": dominant,
        "status": "MEASURED" if overall_lcp is not None else "UNMEASURED",
    }

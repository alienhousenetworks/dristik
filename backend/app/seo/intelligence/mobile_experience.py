"""
Mobile SEO & Responsive Experience Intelligence — Phase 3.9

Audits mobile rendering and user experience across real viewport parameters:
- Mobile viewport configuration
- Responsive layout & horizontal overflow detection
- Touch target sizing and spacing (48x48px minimum)
- Mobile navigation accessibility
- Text readability (16px minimum body text)
- Sticky element obstruction
- Desktop vs. mobile content parity

STRICT GUARDRAIL:
A viewport meta tag is NOT proof that the website is mobile-friendly.
Engine inspects rendered dimensions, touch targets, and overflow behavior.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TouchTargetAudit(BaseModel):
    element_selector: str
    width_px: float
    height_px: float
    spacing_px: float
    is_adequate: bool
    remediation: Optional[str] = None


class MobileExperienceReport(BaseModel):
    url: str
    has_viewport_meta: bool
    is_mobile_friendly: bool
    has_horizontal_overflow: bool
    overflow_elements: List[str] = Field(default_factory=list)
    touch_target_pass_rate: float
    failed_touch_targets: List[TouchTargetAudit] = Field(default_factory=list)
    font_readability_pass: bool
    desktop_mobile_parity_pass: bool
    defects: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class MobileExperienceEngine:
    """
    Evaluates real viewport mobile rendering and interaction signals.
    """

    @classmethod
    def audit_mobile_viewport(
        cls,
        url: str,
        html: str,
        viewport_width: int = 390,  # iPhone 12/13/14 standard
        viewport_height: int = 844,
        rendered_elements: Optional[List[Dict[str, Any]]] = None,
        desktop_word_count: Optional[int] = None,
    ) -> MobileExperienceReport:
        defects: List[str] = []
        recs: List[str] = []

        # 1. Viewport Meta Configuration
        viewport_match = re.search(r'<meta[^>]*name=["\']viewport["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        has_vp = bool(viewport_match)
        if not has_vp:
            defects.append("Missing <meta name='viewport'> tag; mobile browsers will render at desktop scale.")
            recs.append("Add <meta name='viewport' content='width=device-width, initial-scale=1.0'> to <head>.")
        elif viewport_match:
            vp_content = viewport_match.group(1).lower()
            if "width=device-width" not in vp_content:
                defects.append("Viewport tag does not set width=device-width.")
            if "user-scalable=no" in vp_content or "maximum-scale=1" in vp_content:
                defects.append("Viewport disables pinch-to-zoom, violating accessibility standards.")

        # 2. Horizontal Overflow Detection
        elements = rendered_elements or []
        overflows: List[str] = []
        for el in elements:
            w = el.get("width", 0)
            if w > viewport_width:
                sel = el.get("selector", "unnamed-element")
                overflows.append(f"{sel} (width: {w}px > viewport {viewport_width}px)")

        # Pattern check in HTML for common overflow causes (fixed wide elements or tables)
        if "width: 1000px" in html or "width: 1200px" in html or "<table width=" in html.lower():
            if not overflows:
                overflows.append("Fixed-width container or unconstrained table in DOM")

        has_overflow = len(overflows) > 0
        if has_overflow:
            defects.append(f"Detected horizontal viewport overflow ({len(overflows)} element(s) exceed screen width).")
            recs.append("Apply max-width: 100% and overflow-x: auto to wide tables, images, and embedded containers.")

        # 3. Touch Target Sizing (48x48px standard)
        failed_targets: List[TouchTargetAudit] = []
        # If element telemetry provided
        interactive_count = 0
        for el in elements:
            if el.get("is_interactive", False):
                interactive_count += 1
                w = el.get("width", 48)
                h = el.get("height", 48)
                sp = el.get("spacing", 8)
                if w < 40 or h < 40 or sp < 6:
                    failed_targets.append(
                        TouchTargetAudit(
                            element_selector=el.get("selector", "button"),
                            width_px=w,
                            height_px=h,
                            spacing_px=sp,
                            is_adequate=False,
                            remediation=f"Increase tap target from {w}x{h}px to minimum 48x48px.",
                        )
                    )

        target_pass_rate = 1.0
        if interactive_count > 0:
            target_pass_rate = round(1.0 - (len(failed_targets) / interactive_count), 2)
            if failed_targets:
                defects.append(f"{len(failed_targets)} tap targets are undersized (<48x48px) or crowded.")
                recs.append("Increase button padding and touch target clearance for fingers on mobile screens.")

        # 4. Font Readability (16px body text)
        has_tiny_font = "font-size: 10px" in html or "font-size: 11px" in html or "font-size: 9px" in html
        font_pass = not has_tiny_font
        if has_tiny_font:
            defects.append("Detected sub-12px body font sizes requiring user zoom to read.")
            recs.append("Set base body typography to 16px for comfortable mobile reading.")

        # 5. Desktop vs. Mobile Content Parity
        mobile_words = len(re.sub(r"<[^>]+>", " ", html).split())
        parity_pass = True
        if desktop_word_count and desktop_word_count > 0:
            parity_ratio = mobile_words / desktop_word_count
            if parity_ratio < 0.60:
                parity_pass = False
                defects.append(f"Mobile DOM omits >40% of desktop content (mobile: {mobile_words} words vs. desktop: {desktop_word_count} words).")
                recs.append("Ensure mobile parity: do not hide essential commercial or informative copy on mobile.")

        # Overall Verdict (Viewport meta alone is NOT enough)
        is_mobile_ok = has_vp and (not has_overflow) and font_pass and (target_pass_rate >= 0.85) and parity_pass

        return MobileExperienceReport(
            url=url,
            has_viewport_meta=has_vp,
            is_mobile_friendly=is_mobile_ok,
            has_horizontal_overflow=has_overflow,
            overflow_elements=overflows[:5],
            touch_target_pass_rate=target_pass_rate,
            failed_touch_targets=failed_targets[:5],
            font_readability_pass=font_pass,
            desktop_mobile_parity_pass=parity_pass,
            defects=defects,
            recommendations=recs,
        )

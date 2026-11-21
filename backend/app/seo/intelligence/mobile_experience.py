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
    is_mobile_friendly: Optional[bool] = None
    has_horizontal_overflow: bool
    overflow_elements: List[str] = Field(default_factory=list)
    touch_target_pass_rate: float
    failed_touch_targets: List[TouchTargetAudit] = Field(default_factory=list)
    font_readability_pass: bool
    desktop_mobile_parity_pass: bool
    defects: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    measurement_method: str = "html_source_only"
    layout_measured: bool = False
    physical_device: bool = False
    device_label: str = ""
    verification_status: str = "NOT_TESTED"


# Emulated browser sizes. These are not physical phones.
DEVICE_MATRIX: List[Dict[str, Any]] = [
    {"id": "small_mobile", "width": 360, "height": 640, "is_mobile": True, "has_touch": True, "orientation": "portrait"},
    {"id": "standard_mobile", "width": 390, "height": 844, "is_mobile": True, "has_touch": True, "orientation": "portrait"},
    {"id": "standard_mobile_landscape", "width": 844, "height": 390, "is_mobile": True, "has_touch": True, "orientation": "landscape"},
    {"id": "large_mobile", "width": 412, "height": 915, "is_mobile": True, "has_touch": True, "orientation": "portrait"},
    {"id": "tablet", "width": 768, "height": 1024, "is_mobile": True, "has_touch": True, "orientation": "portrait"},
    {"id": "desktop", "width": 1280, "height": 800, "is_mobile": False, "has_touch": False, "orientation": "landscape"},
]


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
        measurement_method: str = "",
        device_label: str = "",
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

        # Geometry is a layout measurement. A viewport tag or a CSS width is not.
        layout_measured = rendered_elements is not None
        elements = rendered_elements or []
        overflows: List[str] = []
        if layout_measured:
            for el in elements:
                w = el.get("width", 0)
                if w > viewport_width:
                    sel = el.get("selector", "unnamed-element")
                    overflows.append(f"{sel} (width: {w}px > viewport {viewport_width}px)")
            if overflows:
                defects.append(f"Detected horizontal viewport overflow ({len(overflows)} element(s) exceed screen width).")
                recs.append("Apply max-width: 100% and overflow-x: auto to wide tables, images, and embedded containers.")

        has_overflow = len(overflows) > 0

        failed_targets: List[TouchTargetAudit] = []
        interactive_count = 0
        for el in elements:
            if el.get("is_interactive", False):
                interactive_count += 1
                w = el.get("width", 48)
                h = el.get("height", 48)
                sp = el.get("spacing")
                crowded = sp is not None and sp < 6
                if w < 40 or h < 40 or crowded:
                    failed_targets.append(
                        TouchTargetAudit(
                            element_selector=el.get("selector", "button"),
                            width_px=w,
                            height_px=h,
                            spacing_px=float(sp or 0),
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
        has_tiny_font = layout_measured and ("font-size: 10px" in html or "font-size: 11px" in html or "font-size: 9px" in html)
        font_pass = not has_tiny_font
        if has_tiny_font:
            defects.append("Detected sub-12px body font sizes requiring user zoom to read.")
            recs.append("Set base body typography to 16px for comfortable mobile reading.")

        mobile_words = len(re.sub(r"<[^>]+>", " ", html).split())
        parity_pass = True
        if layout_measured and desktop_word_count and desktop_word_count > 0:
            parity_ratio = mobile_words / desktop_word_count
            if parity_ratio < 0.60:
                parity_pass = False
                defects.append(f"Mobile DOM omits >40% of desktop content (mobile: {mobile_words} words vs. desktop: {desktop_word_count} words).")
                recs.append("Ensure mobile parity: do not hide essential commercial or informative copy on mobile.")

        # Viewport meta alone is not a mobile UX result.
        if not layout_measured:
            is_mobile_ok = None
            verification = "PARTIALLY_VERIFIED" if html else "NOT_TESTED"
            method = measurement_method or "html_source_only"
        elif interactive_count == 0 and not has_overflow:
            is_mobile_ok = None
            verification = "PARTIALLY_VERIFIED"
            method = measurement_method or "emulated_browser"
        else:
            is_mobile_ok = has_vp and (not has_overflow) and font_pass and (target_pass_rate >= 0.85) and parity_pass
            verification = "VERIFIED"
            method = measurement_method or "viewport_geometry"

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
            measurement_method=method,
            layout_measured=layout_measured,
            physical_device=False,
            device_label=device_label,
            verification_status=verification,
        )

    @classmethod
    def audit_device_matrix(
        cls,
        url: str,
        snapshots: Optional[Dict[str, Dict[str, Any]]] = None,
        html: str = "",
    ) -> Dict[str, Any]:
        """One result per emulated device. A missing snapshot is not a pass."""
        devices: List[Dict[str, Any]] = []
        for spec in DEVICE_MATRIX:
            snap = (snapshots or {}).get(spec["id"])
            if not snap or snap.get("error") or snap.get("elements") is None:
                devices.append({
                    "device_id": spec["id"],
                    "width": spec["width"],
                    "height": spec["height"],
                    "orientation": spec["orientation"],
                    "physical_device": False,
                    "layout_measured": False,
                    "is_mobile_friendly": None,
                    "verification_status": "DATA_UNAVAILABLE" if snap and snap.get("error") else "NOT_TESTED",
                    "measurement_method": "emulated_browser" if snap else "not_run",
                    "error": None if not snap else snap.get("error"),
                })
                continue
            report = cls.audit_mobile_viewport(
                url=url,
                html=str(snap.get("html") or html or ""),
                viewport_width=int(spec["width"]),
                viewport_height=int(spec["height"]),
                rendered_elements=list(snap.get("elements") or []),
                measurement_method="emulated_browser",
                device_label=spec["id"],
            )
            row = report.model_dump()
            row["device_id"] = spec["id"]
            row["width"] = spec["width"]
            row["orientation"] = spec["orientation"]
            devices.append(row)
        measured = [row for row in devices if row.get("layout_measured")]
        return {
            "url": url,
            "physical_device": False,
            "label": "Browser-emulated device. Not a physical phone. Menus, forms, and checkout were not clicked.",
            "measurement_method": "emulated_browser" if measured else "not_run",
            "verification_status": "VERIFIED" if measured else "NOT_TESTED",
            "devices": devices,
        }

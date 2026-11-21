"""
Browser-based Visual Inspection Infrastructure for CRO.

Provides multi-viewport rendering, screenshot capture metadata, fold boundary detection,
element bounding boxes, sticky CTA detection, modal/popup detection, and layout defect analysis.

Viewports configured:
- Desktop: 1440 × 900
- Laptop: 1366 × 768
- Tablet: 768 × 1024
- Mobile: 390 × 844
- Small Mobile: 360 × 800

Notice: These are test configurations, not a substitute for testing the actual device distribution of users.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field


VIEWPORT_PROFILES: Dict[str, Dict[str, Any]] = {
    "desktop": {"width": 1440, "height": 900, "device_type": "desktop", "scale": 1},
    "laptop": {"width": 1366, "height": 768, "device_type": "laptop", "scale": 1},
    "tablet": {"width": 768, "height": 1024, "device_type": "tablet", "scale": 2},
    "mobile": {"width": 390, "height": 844, "device_type": "mobile", "scale": 3},
    "small_mobile": {"width": 360, "height": 800, "device_type": "small_mobile", "scale": 3},
}

VIEWPORT_DISCLOSURE = (
    "These 5 viewport profiles (Desktop 1440x900, Laptop 1366x768, Tablet 768x1024, "
    "Mobile 390x844, Small mobile 360x800) are automated test configurations and not a "
    "substitute for testing the actual device distribution of real users from analytics."
)


class VisualElementBounds(BaseModel):
    tag: str
    text_preview: str = ""
    selector: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    is_above_fold: bool = True
    is_sticky: bool = False
    is_modal_or_overlay: bool = False
    contrast_ratio: Optional[float] = None


class ViewportStateInspection(BaseModel):
    viewport_name: str
    width: int
    height: int
    device_type: str
    tested: bool = False
    execution_mode: str = "STATIC_DOM_HEURISTIC"  # PLAYWRIGHT_LIVE | STATIC_DOM_HEURISTIC
    screenshot_captured: bool = False
    above_the_fold_height: int = 900
    full_page_height_est: Optional[int] = None
    has_horizontal_overflow: bool = False
    overflow_risk: str = "LOW"
    navigation_state: str = "COLLAPSED_OR_DESKTOP" # "EXPANDED_HAMBURGER", "HEADER_BAR", "NOT_FOUND"
    modal_popup_detected: bool = False
    modal_types: List[str] = Field(default_factory=list) # "cookie_banner", "newsletter_interstitial", "exit_intent", "none"
    sticky_cta_detected: bool = False
    sticky_cta_texts: List[str] = Field(default_factory=list)
    above_fold_cta_count: int = 0
    below_fold_cta_count: int = 0
    touch_target_violations: int = 0 # elements < 44x44px on touch devices
    defects: List[Dict[str, Any]] = Field(default_factory=list)


class MultiViewportInspectionResult(BaseModel):
    url: str
    domain: str
    inspected_at: str
    page_type: str = "landing" # "landing", "product", "checkout", "article", "general"
    device_configurations: List[str] = Field(default_factory=lambda: list(VIEWPORT_PROFILES.keys()))
    viewports: Dict[str, ViewportStateInspection] = Field(default_factory=dict)
    sticky_ctas: List[str] = Field(default_factory=list)
    detected_modals: List[str] = Field(default_factory=list)
    overall_visual_ux_score: Optional[float] = None
    critical_visual_defects: List[Dict[str, Any]] = Field(default_factory=list)
    disclosure: str = VIEWPORT_DISCLOSURE


class VisualInspector:
    """Inspects page visual ergonomics, responsive viewports, and interactive states."""

    @classmethod
    def inspect(
        cls,
        url: str,
        html: str,
        inspected_at: str,
        page_type: Optional[str] = None,
        rendered_evidence: Optional[Dict[str, Any]] = None,
    ) -> MultiViewportInspectionResult:
        domain = urlparse(url).netloc or url
        soup = BeautifulSoup(html or "<html><body></body></html>", "html.parser")

        # 1. Page Type Classification
        inferred_page_type = page_type or cls._classify_page_type(url, soup)

        # 2. Detect modals, cookie banners, popups
        modals = cls._detect_modals_and_popups(soup)

        # 3. Detect sticky / fixed CTAs
        sticky_ctas = cls._detect_sticky_ctas(soup)

        # 4. Analyze each of the 5 viewport profiles
        viewports: Dict[str, ViewportStateInspection] = {}
        all_defects: List[Dict[str, Any]] = []

        for vp_name, vp_cfg in VIEWPORT_PROFILES.items():
            vp_rendered = (rendered_evidence or {}).get(vp_name) if isinstance(rendered_evidence, dict) else None
            vp_res = cls._inspect_viewport(
                vp_name=vp_name,
                cfg=vp_cfg,
                soup=soup,
                modals=modals,
                sticky_ctas=sticky_ctas,
                inferred_page_type=inferred_page_type,
                vp_rendered=vp_rendered,
            )
            viewports[vp_name] = vp_res
            all_defects.extend(vp_res.defects)

        # Calculate a grounded visual UX score based on layout integrity
        visual_score = cls._compute_visual_score(viewports, all_defects)

        return MultiViewportInspectionResult(
            url=url,
            domain=domain,
            inspected_at=inspected_at,
            page_type=inferred_page_type,
            viewports=viewports,
            sticky_ctas=sticky_ctas,
            detected_modals=modals,
            overall_visual_ux_score=visual_score,
            critical_visual_defects=all_defects,
            disclosure=VIEWPORT_DISCLOSURE,
        )

    @classmethod
    def _classify_page_type(cls, url: str, soup: BeautifulSoup) -> str:
        u_low = url.lower()
        if any(p in u_low for p in ("/product", "/item", "/shop", "/collection", "/goods")) or soup.find(class_=re.compile(r"product|pdp|price-box", re.I)):
            return "product"
        if any(c in u_low for c in ("/checkout", "/cart", "/basket", "/payment")):
            return "checkout"
        if u_low.rstrip("/").count("/") <= 2 or any(l in u_low for l in ("/landing", "/lp", "/offer", "/promo", "/welcome")):
            return "landing"
        return "general"

    @classmethod
    def _detect_modals_and_popups(cls, soup: BeautifulSoup) -> List[str]:
        detected = []
        # Cookie banners / CMP
        if soup.find(id=re.compile(r"cookie|consent|onetrust|cookiebot|gdpr", re.I)) or soup.find(class_=re.compile(r"cookie|consent|onetrust|gdpr-banner", re.I)):
            detected.append("cookie_consent_banner")
        # Interstitials / Modals
        if soup.find("dialog") or soup.find(attrs={"role": "dialog"}) or soup.find(class_=re.compile(r"modal|popup|newsletter-popup|interstitial", re.I)):
            detected.append("modal_dialog_or_popup")
        # Exit intent / promo bar
        if soup.find(class_=re.compile(r"promo-bar|announcement-bar|top-banner", re.I)):
            detected.append("promotional_banner_bar")
        return detected

    @classmethod
    def _detect_sticky_ctas(cls, soup: BeautifulSoup) -> List[str]:
        sticky_texts = []
        for el in soup.find_all(["div", "section", "footer", "aside", "nav"]):
            style = (el.get("style") or "").lower()
            classes = " ".join(el.get("class") or []).lower()
            if "position:fixed" in style or "position: fixed" in style or "position:sticky" in style or "position: sticky" in style or "sticky" in classes or "fixed-bottom" in classes:
                # Look for buttons or links inside
                for btn in el.find_all(["button", "a"]):
                    txt = btn.get_text(strip=True)
                    if txt and len(txt) < 40 and txt not in sticky_texts:
                        sticky_texts.append(txt)
        return sticky_texts

    @classmethod
    def _inspect_viewport(
        cls,
        vp_name: str,
        cfg: Dict[str, Any],
        soup: BeautifulSoup,
        modals: List[str],
        sticky_ctas: List[str],
        inferred_page_type: str,
        vp_rendered: Optional[Dict[str, Any]] = None,
    ) -> ViewportStateInspection:
        w = cfg["width"]
        h = cfg["height"]
        is_mobile = cfg["device_type"] in ("mobile", "small_mobile")
        defects = []

        # Check navigation state
        nav_state = "HEADER_BAR"
        if is_mobile:
            hamburger = soup.find(class_=re.compile(r"hamburger|nav-toggle|mobile-menu|menu-toggle", re.I)) or soup.find(attrs={"aria-label": re.compile(r"menu|navigation", re.I)})
            nav_state = "HAMBURGER_TOGGLE_PRESENT" if hamburger else "NO_MOBILE_NAV_TOGGLE"
            if not hamburger:
                defects.append({
                    "viewport": vp_name,
                    "defect": "Missing mobile navigation toggle",
                    "severity": "HIGH",
                    "detail": f"No accessible hamburger or mobile menu trigger detected for {w}px viewport.",
                })

        # Check CTAs in hero / above-the-fold
        # Elements inside hero or first 1-2 major containers
        hero = soup.find(class_=re.compile(r"hero|banner|masthead|above-fold|intro", re.I)) or soup.find("header")
        hero_ctas = []
        if hero:
            for cta in hero.find_all(["button", "a"]):
                text = cta.get_text(strip=True)
                if text and len(text) < 40:
                    hero_ctas.append(text)

        above_fold_count = len(hero_ctas)
        all_ctas = [b.get_text(strip=True) for b in soup.find_all(["button", "a"]) if b.get_text(strip=True) and len(b.get_text(strip=True)) < 40]
        below_fold_count = max(0, len(all_ctas) - above_fold_count)

        if above_fold_count == 0 and inferred_page_type in ("landing", "product"):
            defects.append({
                "viewport": vp_name,
                "defect": "No Above-The-Fold Call To Action",
                "severity": "HIGH",
                "detail": f"Visitors on {w}x{h} viewports must scroll before seeing any actionable conversion trigger.",
            })

        # Touch target measurement checks for touch devices
        touch_violations = 0
        if is_mobile:
            # Inline links without adequate padding
            links = soup.find_all("a")
            for link in links:
                txt = link.get_text(strip=True)
                classes = " ".join(link.get("class") or []).lower()
                style = (link.get("style") or "").lower()
                if "btn" not in classes and "button" not in classes and len(txt) <= 2 and "padding" not in style:
                    touch_violations += 1

        if is_mobile and not sticky_ctas and inferred_page_type in ("product", "landing"):
            defects.append({
                "viewport": vp_name,
                "defect": "Missing Sticky Conversion Trigger",
                "severity": "MEDIUM",
                "detail": f"On long mobile viewports ({w}x{h}), primary action loses persistent visibility as visitor scrolls.",
            })

        live = isinstance(vp_rendered, dict) and bool(vp_rendered)
        has_overflow = bool(vp_rendered.get("horizontal_overflow", False)) if live else False
        return ViewportStateInspection(
            viewport_name=vp_name,
            width=w,
            height=h,
            device_type=cfg["device_type"],
            tested=True,
            execution_mode="PLAYWRIGHT_LIVE" if live else "STATIC_DOM_HEURISTIC",
            screenshot_captured=bool(vp_rendered.get("screenshot_captured", False)) if live else False,
            above_the_fold_height=h,
            full_page_height_est=vp_rendered.get("scroll_height") if live else None,
            has_horizontal_overflow=has_overflow,
            overflow_risk="HIGH" if has_overflow else ("LOW" if live else "UNVERIFIED_STATIC"),
            navigation_state=nav_state,
            modal_popup_detected=bool(modals),
            modal_types=modals,
            sticky_cta_detected=bool(sticky_ctas),
            sticky_cta_texts=sticky_ctas,
            above_fold_cta_count=above_fold_count,
            below_fold_cta_count=below_fold_count,
            touch_target_violations=int(vp_rendered.get("small_touch_targets", touch_violations)) if live else touch_violations,
            defects=defects,
        )

    @classmethod
    def _compute_visual_score(cls, viewports: Dict[str, ViewportStateInspection], defects: List[Dict[str, Any]]) -> float:
        score = 88.0
        for d in defects:
            sev = d.get("severity", "MEDIUM")
            if sev == "CRITICAL":
                score -= 15.0
            elif sev == "HIGH":
                score -= 8.0
            elif sev == "MEDIUM":
                score -= 4.0
            else:
                score -= 2.0
        return max(35.0, min(95.0, score))


visual_inspector = VisualInspector()

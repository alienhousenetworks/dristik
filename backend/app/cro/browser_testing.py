"""Phase 6 — Controlled Browser-Based Functional CRO Audit Engine.

Reuses Dristik's Playwright BrowserRenderService (`app/crawl/browser.py`), SSRF guard
(`app/core/security/ssrf.py`), and Content-Addressable Storage (`app/db/storage_cas.py`).

Safety guardrails (Phase 6 & Phase 42):
- SSRF validation on target URL and every sub-request.
- `safe_mode=True` by default: intercepts and aborts irreversible POST/PUT/DELETE requests,
  payment endpoints, and live lead submissions unless an explicit sandbox allowlist is supplied.
- PII redaction on captured DOM/input snippets.
- Truthful fallback: when live browser testing is disabled or fixtures are provided offline,
  executes deterministic DOM analysis and explicitly stamps `execution_mode="static_dom_only"`
  (never claiming screenshots, overflow, or live clickability were browser-verified).
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.core.security.ssrf import is_safe_url
from app.crawl.browser import BrowserRenderService
from app.cro.models import (
    CROInteractionTest,
    CROPage,
    CROPageElement,
    CROSnapshot,
)
from app.db.cro_schema import CROStore

logger = logging.getLogger("dristik.cro.browser_testing")

CRO_VIEWPORTS: Dict[str, Tuple[int, int]] = {
    "desktop": (1440, 900),
    "tablet": (768, 1024),
    "mobile": (390, 844),
}

PAYMENT_OR_IRREVERSIBLE_RE = re.compile(
    r"(stripe\.com|paypal\.com|braintree|adyen|razorpay|checkout/complete|orders/create|charge|payment|subscribe|leads/submit)",
    re.I,
)

EMAIL_PII_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PII_RE = re.compile(r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")


def redact_pii(text: str) -> str:
    """Redact email addresses and phone numbers before persisting captured snippets."""
    if not text:
        return ""
    cleaned = EMAIL_PII_RE.sub("[REDACTED_EMAIL]", text)
    cleaned = PHONE_PII_RE.sub("[REDACTED_PHONE]", cleaned)
    return cleaned


def _css_selector_hint(el: Any) -> str:
    if el is None:
        return ""
    el_id = el.get("id")
    if el_id:
        return f"#{el_id}"
    classes = [c for c in (el.get("class") or []) if c][:2]
    if classes:
        return f"{el.name}.{'.'.join(classes)}"
    return el.name or ""


class CROBrowserTestingEngine:
    """Runs safe multi-viewport Playwright CRO audits or truthful static DOM fallback."""

    def __init__(self, store: Optional[CROStore] = None):
        self.store = store

    async def audit_page(
        self,
        *,
        tenant_id: str,
        audit_id: str,
        page: CROPage,
        raw_html: Optional[str] = None,
        viewports: Sequence[str] = ("desktop", "tablet", "mobile"),
        safe_mode: bool = True,
        sandbox_allowlist: Optional[List[str]] = None,
        use_live_browser: bool = True,
        auth_context: str = "logged_out",
        timeout_ms: int = 15000,
    ) -> Tuple[List[CROInteractionTest], List[CROPageElement], List[CROSnapshot]]:
        """Inspect a page across viewports and interactive conversion elements."""
        # Always enforce SSRF check before any live browser navigation
        if use_live_browser:
            safe, reason = is_safe_url(page.url)
            if not safe:
                blocked_test = CROInteractionTest(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    page_id=page.page_id,
                    url=page.url,
                    scenario="ssrf_security_guard",
                    viewport_name="desktop",
                    execution_mode="playwright_live",
                    safe_mode=safe_mode,
                    auth_context=auth_context,
                    passed=False,
                    result_status="blocked_safe_mode",
                    observations=[f"Navigation blocked by SSRF guard: {reason}"],
                )
                return [blocked_test], [], []

        if use_live_browser and BrowserRenderService.is_available() and not raw_html:
            try:
                return await self._run_live_playwright(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    page=page,
                    viewports=viewports,
                    safe_mode=safe_mode,
                    sandbox_allowlist=sandbox_allowlist or [],
                    auth_context=auth_context,
                    timeout_ms=timeout_ms,
                )
            except Exception as exc:
                logger.warning("Playwright CRO test fallback to static DOM for %s: %s", page.url, exc)

        # Deterministic static DOM fallback (honestly labeled static_dom_only)
        return self._run_static_dom_inspection(
            tenant_id=tenant_id,
            audit_id=audit_id,
            page=page,
            raw_html=raw_html or "",
            viewports=viewports,
            safe_mode=safe_mode,
            auth_context=auth_context,
        )

    async def _run_live_playwright(
        self,
        *,
        tenant_id: str,
        audit_id: str,
        page: CROPage,
        viewports: Sequence[str],
        safe_mode: bool,
        sandbox_allowlist: List[str],
        auth_context: str,
        timeout_ms: int,
    ) -> Tuple[List[CROInteractionTest], List[CROPageElement], List[CROSnapshot]]:
        browser = await BrowserRenderService.get_browser()
        if browser is None:
            return self._run_static_dom_inspection(
                tenant_id=tenant_id,
                audit_id=audit_id,
                page=page,
                raw_html="",
                viewports=viewports,
                safe_mode=safe_mode,
                auth_context=auth_context,
            )

        tests: List[CROInteractionTest] = []
        elements: List[CROPageElement] = []
        snapshots: List[CROSnapshot] = []
        browser_version = getattr(browser, "version", None)

        for vp_name in viewports:
            width, height = CRO_VIEWPORTS.get(vp_name, (1440, 900))
            context = None
            pw_page = None
            console_errors: List[str] = []
            network_failures: List[Dict[str, Any]] = []
            blocked_mutations: List[str] = []

            try:
                context = await browser.new_context(
                    viewport={"width": width, "height": height},
                    is_mobile=(vp_name == "mobile"),
                    has_touch=(vp_name in ("mobile", "tablet")),
                    ignore_https_errors=True,
                )
                pw_page = await context.new_page()
                pw_page.on("console", lambda msg: console_errors.append(redact_pii(msg.text)) if msg.type == "error" else None)
                pw_page.on("pageerror", lambda err: console_errors.append(redact_pii(str(err))))
                pw_page.on(
                    "requestfailed",
                    lambda req: network_failures.append({"url": req.url, "method": req.method, "reason": str(req.failure)}),
                )

                async def _guard_route(route):
                    req = route.request
                    # SSRF guard on all sub-requests
                    safe, _ = await asyncio.to_thread(is_safe_url, req.url)
                    if not safe:
                        await route.abort("blockedbyclient")
                        return
                    # Safe mode: block irreversible payments/orders/live form POSTs unless allowlisted
                    if safe_mode and req.method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
                        allowed = any(a in req.url for a in sandbox_allowlist)
                        if not allowed or PAYMENT_OR_IRREVERSIBLE_RE.search(req.url):
                            blocked_mutations.append(f"{req.method} {req.url}")
                            await route.abort("blockedbyclient")
                            return
                    await route.continue_()

                await pw_page.route("**/*", _guard_route)
                resp = await pw_page.goto(page.url, wait_until="domcontentloaded", timeout=timeout_ms)
                await pw_page.wait_for_timeout(500)
                status_code = resp.status if resp else 200
                page.http_status = status_code
                page.rendered_dom_verified = True

                rendered_html = await pw_page.content()
                screenshot_bytes = await pw_page.screenshot(full_page=False, type="png")

                snap_shot_id = None
                dom_snap_id = None
                if self.store:
                    ss = self.store.persist_snapshot(
                        tenant_id=tenant_id,
                        audit_id=audit_id,
                        snapshot_type=f"screenshot_{vp_name}",
                        data=screenshot_bytes,
                        extension="png",
                        url=page.url,
                        viewport=f"{width}x{height}",
                        browser="chromium",
                    )
                    snapshots.append(ss)
                    snap_shot_id = ss.snapshot_id
                    page.screenshot_snapshot_ids[vp_name] = ss.snapshot_id

                    ds = self.store.persist_snapshot(
                        tenant_id=tenant_id,
                        audit_id=audit_id,
                        snapshot_type="rendered_dom",
                        data=rendered_html,
                        extension="html",
                        url=page.url,
                        viewport=f"{width}x{height}",
                        browser="chromium",
                    )
                    snapshots.append(ds)
                    dom_snap_id = ds.snapshot_id
                    if vp_name == "desktop":
                        page.rendered_dom_snapshot_id = ds.snapshot_id

                # Measure real layout, overflow, above-the-fold, touch targets, CTAs, forms, CWV
                probe = await pw_page.evaluate(
                    """() => {
                        const vw = window.innerWidth;
                        const vh = window.innerHeight;
                        const overflow = document.documentElement.scrollWidth > vw + 2;
                        const nav = performance.getEntriesByType('navigation')[0] || {};
                        const paint = performance.getEntriesByType('paint') || [];
                        const fcp = paint.find(p => p.name === 'first-contentful-paint');
                        const lcpList = performance.getEntriesByType('largest-contentful-paint') || [];
                        const lcp = lcpList.length ? lcpList[lcpList.length - 1].startTime : null;
                        const cls = (performance.getEntriesByType('layout-shift') || [])
                            .filter(e => !e.hadRecentInput)
                            .reduce((s, e) => s + (e.value || 0), 0);

                        const ctas = [];
                        let smallTouchTargets = 0;
                        document.querySelectorAll('button, a, input[type="submit"], input[type="button"]').forEach((el, idx) => {
                            if (idx > 80) return;
                            const rect = el.getBoundingClientRect();
                            const style = window.getComputedStyle(el);
                            const visible = style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
                            const txt = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 60);
                            if (visible && vw <= 768 && (rect.width < 44 || rect.height < 44)) smallTouchTargets += 1;
                            const clsStr = (el.className || '').toString().toLowerCase();
                            const isCta = el.tagName === 'BUTTON' || el.tagName === 'INPUT' || clsStr.includes('btn') || clsStr.includes('cta');
                            if (isCta && txt) {
                                ctas.push({
                                    tag: el.tagName.toLowerCase(),
                                    text: txt,
                                    href: el.getAttribute('href') || '',
                                    visible,
                                    disabled: !!el.disabled || style.pointerEvents === 'none',
                                    above_fold: visible && rect.top >= 0 && rect.bottom <= vh,
                                    aria_name: el.getAttribute('aria-label') || txt,
                                    box: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)},
                                });
                            }
                        });
                        const forms = Array.from(document.querySelectorAll('form')).map((f, i) => ({
                            id: f.id || `form_${i+1}`,
                            action: f.getAttribute('action') || '',
                            inputs: f.querySelectorAll('input:not([type="hidden"]):not([type="submit"]), select, textarea').length,
                            required: f.querySelectorAll('[required], [aria-required="true"]').length,
                        }));
                        const modals = document.querySelectorAll('dialog[open], [role="dialog"], [class*="modal"], [class*="popup"]').length;
                        return {
                            horizontal_overflow: overflow,
                            scroll_width: document.documentElement.scrollWidth,
                            inner_width: vw,
                            scroll_height: document.documentElement.scrollHeight,
                            small_touch_targets: smallTouchTargets,
                            ctas,
                            forms,
                            modals_count: modals,
                            perf: {
                                ttfb_ms: nav.responseStart && nav.requestStart ? Math.round(nav.responseStart - nav.requestStart) : null,
                                fcp_ms: fcp ? Math.round(fcp.startTime) : null,
                                lcp_ms: lcp !== null ? Math.round(lcp) : null,
                                cls_score: Math.round(cls * 1000) / 1000,
                                dom_content_loaded_ms: nav.domContentLoadedEventEnd ? Math.round(nav.domContentLoadedEventEnd) : null,
                            }
                        };
                    }"""
                )

                if vp_name == "desktop":
                    page.performance_metrics = probe.get("perf") or {}
                    page.performance_metrics["measurement_type"] = "lab_playwright"
                    page.performance_metrics["viewport"] = f"{width}x{height}"

                # Convert probed CTAs into CROPageElement records
                for c in (probe.get("ctas") or [])[:40]:
                    elements.append(
                        CROPageElement(
                            tenant_id=tenant_id,
                            audit_id=audit_id,
                            page_id=page.page_id,
                            url=page.url,
                            element_category="cta",
                            element_type=c.get("tag", "button"),
                            section="hero" if c.get("above_fold") else "body",
                            text=redact_pii(c.get("text", "")),
                            destination=urljoin(page.url, c["href"]) if c.get("href") else None,
                            visible=c.get("visible"),
                            clickable=bool(c.get("visible") and not c.get("disabled")),
                            above_the_fold=c.get("above_fold"),
                            accessible_name=redact_pii(c.get("aria_name", "")),
                            device=vp_name,
                            bounding_box=c.get("box"),
                            interaction_result="clickable" if (c.get("visible") and not c.get("disabled")) else "unclickable_or_hidden",
                        )
                    )

                vp_passed = status_code < 400 and not probe.get("horizontal_overflow") and len(console_errors) == 0
                obs_notes: List[str] = []
                if probe.get("horizontal_overflow"):
                    obs_notes.append(f"Horizontal overflow detected on {vp_name} ({probe['scroll_width']}px > {probe['inner_width']}px).")
                if vp_name == "mobile" and (probe.get("small_touch_targets") or 0) > 0:
                    obs_notes.append(f"{probe['small_touch_targets']} touch target(s) smaller than 44x44px on mobile.")
                if console_errors:
                    obs_notes.append(f"{len(console_errors)} JavaScript console error(s) observed.")
                if blocked_mutations:
                    obs_notes.append(f"Safe mode prevented {len(blocked_mutations)} live mutating request(s).")

                tests.append(
                    CROInteractionTest(
                        tenant_id=tenant_id,
                        audit_id=audit_id,
                        page_id=page.page_id,
                        url=page.url,
                        scenario="viewport_render",
                        viewport_name=vp_name,
                        viewport_width=width,
                        viewport_height=height,
                        browser="chromium",
                        browser_version=str(browser_version) if browser_version else None,
                        execution_mode="playwright_live",
                        safe_mode=safe_mode,
                        auth_context=auth_context,
                        interaction_sequence=[f"goto({page.url})", f"measure_viewport({width}x{height})"],
                        passed=vp_passed,
                        result_status="passed" if vp_passed else "failed",
                        console_errors=console_errors[:20],
                        network_failures=network_failures[:20],
                        screenshot_snapshot_id=snap_shot_id,
                        dom_snapshot_id=dom_snap_id,
                        metrics={
                            "http_status": status_code,
                            "horizontal_overflow": probe.get("horizontal_overflow", False),
                            "scroll_width": probe.get("scroll_width"),
                            "inner_width": probe.get("inner_width"),
                            "small_touch_targets": probe.get("small_touch_targets", 0),
                            "modals_count": probe.get("modals_count", 0),
                            "perf": probe.get("perf") or {},
                        },
                        observations=obs_notes,
                    )
                )

                # Safe client-side form validation test on desktop (empty submit check without network POST)
                if vp_name == "desktop" and probe.get("forms"):
                    form_check = await pw_page.evaluate(
                        """() => {
                            const f = document.querySelector('form');
                            if (!f) return null;
                            const validBefore = f.checkValidity();
                            const invalidFields = Array.from(f.querySelectorAll(':invalid')).map(el => el.name || el.id || el.type);
                            const submitBtn = f.querySelector('button[type="submit"], input[type="submit"], button');
                            return {
                                form_id: f.id || 'form_1',
                                valid_when_empty: validBefore,
                                invalid_fields_when_empty: invalidFields,
                                submit_disabled: submitBtn ? !!submitBtn.disabled : false,
                                has_novalidate: f.hasAttribute('novalidate'),
                            };
                        }"""
                    )
                    if form_check:
                        form_ok = (not form_check["valid_when_empty"]) or bool(form_check["invalid_fields_when_empty"])
                        tests.append(
                            CROInteractionTest(
                                tenant_id=tenant_id,
                                audit_id=audit_id,
                                page_id=page.page_id,
                                url=page.url,
                                scenario="form_validation",
                                viewport_name="desktop",
                                viewport_width=width,
                                viewport_height=height,
                                browser="chromium",
                                execution_mode="playwright_live",
                                safe_mode=safe_mode,
                                auth_context=auth_context,
                                element_selector=f"#{form_check['form_id']}",
                                interaction_sequence=["check_empty_form_validity"],
                                passed=form_ok,
                                result_status="passed" if form_ok else "failed",
                                metrics=form_check,
                                observations=[
                                    "Client-side required field validation active."
                                    if form_ok
                                    else "Form allows empty submission without HTML5 required validation."
                                ],
                            )
                        )

            finally:
                if pw_page:
                    try:
                        await pw_page.close()
                    except Exception:
                        pass
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass

        page.device_coverage = list(viewports)
        page.functional_test_status = "failed" if any(t.result_status == "failed" for t in tests) else "passed"
        return tests, elements, snapshots

    def _run_static_dom_inspection(
        self,
        *,
        tenant_id: str,
        audit_id: str,
        page: CROPage,
        raw_html: str,
        viewports: Sequence[str],
        safe_mode: bool,
        auth_context: str,
    ) -> Tuple[List[CROInteractionTest], List[CROPageElement], List[CROSnapshot]]:
        """Deterministic static DOM inspection when live Playwright is offline/fixture-backed."""
        tests: List[CROInteractionTest] = []
        elements: List[CROPageElement] = []
        snapshots: List[CROSnapshot] = []

        dom_snap_id = None
        if raw_html and self.store:
            snap = self.store.persist_snapshot(
                tenant_id=tenant_id,
                audit_id=audit_id,
                snapshot_type="raw_html",
                data=raw_html,
                extension="html",
                url=page.url,
            )
            snapshots.append(snap)
            dom_snap_id = snap.snapshot_id
            page.raw_html_snapshot_id = snap.snapshot_id

        soup = BeautifulSoup(raw_html or "<html><body></body></html>", "html.parser")

        # 1. Extract CTAs, Forms, Navigation, Interactive components & detect static technical defects
        broken_ctas: List[str] = []
        for idx, el in enumerate(soup.find_all(["button", "a", "input"])):
            tag = el.name
            classes = " ".join(el.get("class") or []).lower()
            style = (el.get("style") or "").lower().replace(" ", "")
            href = (el.get("href") or "").strip() if tag == "a" else ""
            txt = ""
            is_cta = False
            if tag == "button":
                txt = el.get_text(" ", strip=True)
                is_cta = True
            elif tag == "input" and (el.get("type") or "").lower() in ("submit", "button"):
                txt = (el.get("value") or el.get("aria-label") or "").strip()
                is_cta = True
            elif tag == "a" and (
                any(k in classes for k in ("btn", "button", "cta", "primary", "action"))
                or any(k in href.lower() for k in ("checkout", "cart", "demo", "pricing", "signup", "contact", "book"))
            ):
                txt = el.get_text(" ", strip=True)
                is_cta = True

            if not is_cta:
                continue

            is_disabled = el.has_attr("disabled") or "pointer-events:none" in style or "display:none" in style or "visibility:hidden" in style
            bad_href = tag == "a" and href.lower() in ("", "#", "javascript:void(0)", "javascript:;") and not el.get("onclick")
            clickable = not is_disabled and not bad_href
            parent_names = [p.name for p in el.parents]
            section = "header" if ("header" in parent_names or "nav" in parent_names) else ("footer" if "footer" in parent_names else ("hero" if idx < 6 else "body"))

            if not clickable:
                broken_ctas.append(f"{txt or _css_selector_hint(el)} ({'disabled/hidden' if is_disabled else 'dead href'})")

            elements.append(
                CROPageElement(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    page_id=page.page_id,
                    url=page.url,
                    element_category="cta",
                    element_type=tag,
                    section=section,
                    selector=_css_selector_hint(el),
                    text=redact_pii(txt[:80]),
                    destination=urljoin(page.url, href) if href and not href.startswith(("#", "javascript:")) else (href or None),
                    visible="display:none" not in style and "visibility:hidden" not in style,
                    clickable=clickable,
                    above_the_fold=(section in ("header", "hero")),
                    accessible_name=redact_pii(el.get("aria-label") or txt),
                    device="desktop",
                    interaction_result="clickable" if clickable else "broken_or_unclickable",
                    attributes={"classes": classes, "disabled": is_disabled, "bad_href": bad_href},
                )
            )

        # Extract Forms into CROPageElement
        form_issues: List[str] = []
        for f_idx, f in enumerate(soup.find_all("form")):
            f_id = f.get("id") or f"form_{f_idx + 1}"
            action = f.get("action") or ""
            inputs = [
                inp for inp in f.find_all(["input", "select", "textarea"])
                if (inp.get("type") or "text").lower() not in ("hidden", "submit", "button", "image")
            ]
            missing_labels = 0
            required_fields = 0
            invalid_email_type = 0
            for inp in inputs:
                iid = inp.get("id")
                has_lbl = bool((iid and f.find("label", attrs={"for": iid})) or inp.find_parent("label") or inp.get("aria-label") or inp.get("aria-labelledby"))
                if not has_lbl:
                    missing_labels += 1
                if inp.has_attr("required") or inp.get("aria-required") == "true":
                    required_fields += 1
                name_l = (inp.get("name") or inp.get("id") or "").lower()
                itype = (inp.get("type") or "text").lower()
                if "email" in name_l and itype != "email":
                    invalid_email_type += 1

            has_error_region = bool(
                f.find(attrs={"role": "alert"})
                or f.find(attrs={"aria-live": True})
                or f.find(class_=re.compile(r"error|invalid|validation|feedback", re.I))
            )
            data_error = f.get("data-test-error") or ""
            data_slow_ms = int(f.get("data-response-ms") or 0) if str(f.get("data-response-ms") or "").isdigit() else 0
            novalidate = f.has_attr("novalidate")

            if missing_labels > 0:
                form_issues.append(f"{f_id}: {missing_labels} unlabeled input(s)")
            if novalidate and not has_error_region:
                form_issues.append(f"{f_id}: novalidate without accessible error feedback")
            if data_error:
                form_issues.append(f"{f_id}: submission returns error ({data_error})")
            if data_slow_ms >= 3000:
                form_issues.append(f"{f_id}: slow form submission ({data_slow_ms}ms)")

            elements.append(
                CROPageElement(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    page_id=page.page_id,
                    url=page.url,
                    element_category="form",
                    element_type="form",
                    section="body",
                    selector=f"#{f_id}",
                    text=f"Form #{f_id} ({len(inputs)} fields)",
                    destination=action or None,
                    visible=True,
                    clickable=True,
                    device="desktop",
                    interaction_result="failed" if (data_error or missing_labels > 0 or (novalidate and not has_error_region) or data_slow_ms >= 3000) else "passed",
                    attributes={
                        "form_id": f_id,
                        "field_count": len(inputs),
                        "required_fields": required_fields,
                        "missing_labels": missing_labels,
                        "invalid_email_type": invalid_email_type,
                        "has_error_region": has_error_region,
                        "has_novalidate": novalidate,
                        "simulated_server_error": data_error or None,
                        "response_ms": data_slow_ms or None,
                        "has_privacy_reassurance": bool(re.search(r"privacy|terms|no spam|secure", f.get_text(" ", strip=True), re.I)),
                    },
                )
            )

        # Static viewport / responsive cues (explicitly labeled static_dom_only)
        has_viewport_meta = bool(soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)}))
        fixed_wide_overflow = bool(re.search(r"width\s*:\s*(?:1[0-9]{3}|[2-9]\d{3})px", raw_html, re.I))
        has_mobile_nav = bool(
            soup.find(class_=re.compile(r"hamburger|mobile-menu|nav-toggle|menu-toggle", re.I))
            or soup.find(attrs={"aria-label": re.compile(r"menu|navigation", re.I)})
        )
        small_touch_declared = len(re.findall(r"(?:width|height)\s*:\s*(?:[1-9]|1\d|2[0-3])px", raw_html, re.I))

        for vp_name in viewports:
            width, height = CRO_VIEWPORTS.get(vp_name, (1440, 900))
            vp_obs: List[str] = ["Executed in static_dom_only mode (no live Chromium render)."]
            vp_failed = False
            if vp_name == "mobile":
                if not has_viewport_meta:
                    vp_failed = True
                    vp_obs.append("Missing <meta name='viewport'> tag for mobile responsiveness.")
                if fixed_wide_overflow:
                    vp_failed = True
                    vp_obs.append("Fixed pixel width >= 1000px detected in CSS/inline styles causing mobile horizontal overflow risk.")
                if not has_mobile_nav and soup.find("nav"):
                    vp_obs.append("No mobile navigation toggle detected for <nav> container.")
                if small_touch_declared > 0:
                    vp_obs.append(f"{small_touch_declared} explicit sub-24px dimension rule(s) detected.")

            tests.append(
                CROInteractionTest(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    page_id=page.page_id,
                    url=page.url,
                    scenario="viewport_render",
                    viewport_name=vp_name,
                    viewport_width=width,
                    viewport_height=height,
                    browser="static_dom_parser",
                    execution_mode="static_dom_only",
                    safe_mode=safe_mode,
                    auth_context=auth_context,
                    dom_snapshot_id=dom_snap_id,
                    passed=not vp_failed,
                    result_status="failed" if vp_failed else "static_only",
                    metrics={
                        "has_viewport_meta": has_viewport_meta,
                        "horizontal_overflow": fixed_wide_overflow if vp_name == "mobile" else False,
                        "has_mobile_nav_toggle": has_mobile_nav,
                        "small_touch_targets": small_touch_declared if vp_name == "mobile" else 0,
                        "broken_ctas_count": len(broken_ctas),
                        "form_issues_count": len(form_issues),
                    },
                    observations=vp_obs,
                )
            )

        if broken_ctas:
            tests.append(
                CROInteractionTest(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    page_id=page.page_id,
                    url=page.url,
                    scenario="cta_click",
                    viewport_name="desktop",
                    browser="static_dom_parser",
                    execution_mode="static_dom_only",
                    safe_mode=safe_mode,
                    auth_context=auth_context,
                    dom_snapshot_id=dom_snap_id,
                    passed=False,
                    result_status="failed",
                    metrics={"broken_ctas": broken_ctas},
                    observations=[f"Unclickable or dead-target CTA detected: {c}" for c in broken_ctas[:5]],
                )
            )

        if form_issues:
            tests.append(
                CROInteractionTest(
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    page_id=page.page_id,
                    url=page.url,
                    scenario="form_validation",
                    viewport_name="desktop",
                    browser="static_dom_parser",
                    execution_mode="static_dom_only",
                    safe_mode=safe_mode,
                    auth_context=auth_context,
                    dom_snapshot_id=dom_snap_id,
                    passed=False,
                    result_status="failed",
                    metrics={"form_issues": form_issues},
                    observations=form_issues[:10],
                )
            )

        page.device_coverage = list(viewports)
        page.functional_test_status = "failed" if any(t.result_status == "failed" for t in tests) else "partial"
        return tests, elements, snapshots

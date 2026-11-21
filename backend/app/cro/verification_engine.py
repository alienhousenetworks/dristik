"""Phases 22 & 23 — Independent CRO Verification & Before-and-After Evidence Comparator.

Hard architectural guarantee:
- A developer marking a task deployed MUST NEVER automatically close or verify it.
  Deployment transitions the task to `AWAITING_VERIFICATION`.
- Independent verification re-tests actual DOM/browser/form/CTA/mobile/accessibility/analytics
  evidence and strictly separates four distinct outcomes:
  1. implementation_verified (passed | failed | pending)
  2. functional_verification (passed | failed | not_tested)
  3. analytics_verification  (verified | failed | unavailable)
  4. business_outcome        (improved | degraded | inconclusive | insufficient_data)
- Preserves normalized Before-and-After evidence under recorded test conditions and
  detects cross-dimension regressions (e.g., fix introduced mobile overflow or console errors).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from app.cro.browser_testing import CROBrowserTestingEngine
from app.cro.models import (
    BeforeAfterComparison,
    CROPage,
    CRORemediationTask,
    CROTaskStatus,
    CROVerification,
)
from app.db.cro_schema import CROStore


def _extract_dom_summary(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html or "", "html.parser")
    h1 = soup.find("h1")
    h1_text = h1.get_text(" ", strip=True) if h1 else None
    sub = h1.find_next_sibling(["p", "h2"]) if h1 else None
    sub_text = sub.get_text(" ", strip=True)[:200] if sub else None

    ctas = []
    for el in soup.find_all(["button", "a", "input"]):
        if el.name == "button" or (el.name == "input" and (el.get("type") or "").lower() in ("submit", "button")):
            txt = el.get_text(" ", strip=True) or (el.get("value") or "")
            disabled = el.has_attr("disabled") or "pointer-events:none" in (el.get("style") or "").lower().replace(" ", "")
            ctas.append({"text": txt, "href": el.get("href"), "clickable": not disabled})
        elif el.name == "a" and any(k in " ".join(el.get("class") or []).lower() for k in ("btn", "cta", "primary")):
            href = (el.get("href") or "").strip()
            ctas.append({"text": el.get_text(" ", strip=True), "href": href, "clickable": href not in ("", "#", "javascript:void(0)")})

    forms = []
    for idx, f in enumerate(soup.find_all("form")):
        inputs = [i for i in f.find_all(["input", "select", "textarea"]) if (i.get("type") or "text").lower() not in ("hidden", "submit", "button")]
        unlabeled = sum(
            1 for i in inputs
            if not ((i.get("id") and f.find("label", attrs={"for": i.get("id")})) or i.find_parent("label") or i.get("aria-label"))
        )
        has_err = bool(f.find(attrs={"role": "alert"}) or f.find(class_=lambda c: c and "error" in str(c).lower()))
        forms.append({"form_id": f.get("id") or f"form_{idx+1}", "field_count": len(inputs), "unlabeled": unlabeled, "has_error_region": has_err})

    has_vp = bool(soup.find("meta", attrs={"name": "viewport"}))
    return {
        "headline": h1_text,
        "subheadline": sub_text,
        "primary_cta": ctas[0] if ctas else None,
        "broken_ctas": sum(1 for c in ctas if not c["clickable"]),
        "forms": forms,
        "has_viewport_meta": has_vp,
    }


def _evaluate_business_outcome(
    pre_metrics: Optional[Dict[str, Any]],
    post_metrics: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    """Compare pre/post conversion outcomes with basic sample-size and z-test guardrails."""
    if not pre_metrics or not post_metrics:
        return "insufficient_data", "Pre-change and post-change analytics cohorts were not both supplied."
    n1 = pre_metrics.get("eligible_users")
    c1 = pre_metrics.get("unique_converters")
    n2 = post_metrics.get("eligible_users")
    c2 = post_metrics.get("unique_converters")
    if not all(isinstance(v, int) and v >= 0 for v in (n1, c1, n2, c2)) or n1 < 100 or n2 < 100:
        return "insufficient_data", "Minimum sample size (>=100 eligible users per period) not met for reliable business outcome readout."

    p1 = c1 / n1
    p2 = c2 / n2
    p_pool = (c1 + c2) / (n1 + n2)
    se = math.sqrt(max(1e-12, p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2)))
    z = (p2 - p1) / se
    p_val = math.erfc(abs(z) / math.sqrt(2.0))

    if p_val < 0.05:
        if p2 > p1:
            return "improved", f"Post-change rate {p2*100:.2f}% vs pre-change {p1*100:.2f}% (p={p_val:.4f}; non-randomized pre/post subject to seasonality/traffic-mix caveats)."
        return "degraded", f"Post-change rate {p2*100:.2f}% fell vs pre-change {p1*100:.2f}% (p={p_val:.4f})."
    return "inconclusive", f"Observed difference ({p2*100:.2f}% vs {p1*100:.2f}%, p={p_val:.4f}) is not statistically conclusive."


class CROIndependentVerificationEngine:
    """Independently re-tests deployed CRO remediation tasks and compares Before/After evidence."""

    def __init__(self, store: CROStore):
        self.store = store
        self.browser_engine = CROBrowserTestingEngine(store=store)

    def mark_deployed(
        self,
        *,
        tenant_id: str,
        task_id: str,
        deployed_by: str,
        deployment_ref: str,
    ) -> CRORemediationTask:
        """Developer deployment NEVER closes the task; transitions to AWAITING_VERIFICATION."""
        task = self.store.get_remediation_task(tenant_id, task_id)
        if not task:
            raise KeyError(f"Remediation task '{task_id}' not found.")
        if task.approval_status != "approved":
            raise PermissionError("Task must be explicitly approved before deployment.")

        task.deployment_ref = deployment_ref
        task.deployed_by = deployed_by
        task.deployed_at = datetime.now(timezone.utc).isoformat()
        task.status = CROTaskStatus.AWAITING_VERIFICATION.value
        task.verification_status = "awaiting_verification"
        return self.store.save_remediation_task(task)

    async def verify_task(
        self,
        *,
        tenant_id: str,
        task_id: str,
        verifier: str = "dristik_independent_verifier",
        before_html: Optional[str] = None,
        after_html: Optional[str] = None,
        expected_text_present: Optional[str] = None,
        analytics_event_confirmed: Optional[bool] = None,
        pre_conversion_metrics: Optional[Dict[str, Any]] = None,
        post_conversion_metrics: Optional[Dict[str, Any]] = None,
        use_live_browser: bool = False,
        viewport: str = "desktop",
    ) -> CROVerification:
        """Execute independent retest and record all 4 outcomes + Before/After comparison."""
        task = self.store.get_remediation_task(tenant_id, task_id)
        if not task:
            raise KeyError(f"Remediation task '{task_id}' not found.")

        target_url = (task.affected_urls[0] if task.affected_urls else task.url) or "https://example.com/"
        page_probe = CROPage(tenant_id=tenant_id, audit_id=task.audit_id or "verification", url=target_url)

        # Persist snapshots under matching test conditions
        before_dom_id = None
        after_dom_id = None
        if before_html:
            before_dom_id = self.store.persist_snapshot(
                tenant_id=tenant_id,
                audit_id=task.audit_id,
                snapshot_type="before_state",
                data=before_html,
                extension="html",
                url=target_url,
                viewport=viewport,
            ).snapshot_id
        if after_html:
            after_dom_id = self.store.persist_snapshot(
                tenant_id=tenant_id,
                audit_id=task.audit_id,
                snapshot_type="after_state",
                data=after_html,
                extension="html",
                url=target_url,
                viewport=viewport,
            ).snapshot_id

        tests, _els, _snaps = await self.browser_engine.audit_page(
            tenant_id=tenant_id,
            audit_id=task.audit_id or "verification",
            page=page_probe,
            raw_html=after_html,
            viewports=("desktop", "mobile"),
            safe_mode=True,
            use_live_browser=use_live_browser,
        )

        before_sum = _extract_dom_summary(before_html or "")
        after_sum = _extract_dom_summary(after_html or "")

        # 1. Implementation verification
        criteria_results: List[Dict[str, Any]] = []
        impl_ok = True
        if expected_text_present:
            present = expected_text_present.lower() in (after_html or "").lower()
            criteria_results.append({"criterion": f"Expected content present: '{expected_text_present}'", "passed": present})
            if not present:
                impl_ok = False
        if task.root_cause_group == "cta_and_action_hierarchy":
            ok = after_sum["broken_ctas"] == 0
            criteria_results.append({"criterion": "Zero broken/unclickable CTAs in post-fix DOM", "passed": ok})
            if not ok:
                impl_ok = False
        if task.root_cause_group == "contact_form_friction":
            unlabeled_after = sum(f["unlabeled"] for f in after_sum["forms"])
            ok = unlabeled_after == 0
            criteria_results.append({"criterion": "All form fields have explicit accessible labels", "passed": ok})
            if not ok:
                impl_ok = False
        if task.root_cause_group == "mobile_experience_fixes":
            ok = bool(after_sum["has_viewport_meta"]) and not any(
                (t.metrics or {}).get("horizontal_overflow") for t in tests if t.viewport_name == "mobile"
            )
            criteria_results.append({"criterion": "Mobile viewport meta present and zero horizontal overflow", "passed": ok})
            if not ok:
                impl_ok = False
        if not criteria_results:
            impl_ok = bool(after_html) or any(t.passed for t in tests)
            criteria_results.append({"criterion": "Post-deployment DOM/page captured and inspected", "passed": impl_ok})

        implementation_verified = "passed" if impl_ok else "failed"

        # 2. Functional verification
        failed_tests = [t for t in tests if t.result_status == "failed"]
        functional_verification = "failed" if failed_tests else ("passed" if tests else "not_tested")

        # 3. Analytics verification
        if analytics_event_confirmed is True:
            analytics_verification = "verified"
        elif analytics_event_confirmed is False:
            analytics_verification = "failed"
        else:
            analytics_verification = "unavailable"

        # 4. Business outcome verification (strictly separated from implementation & functional)
        business_outcome, biz_note = _evaluate_business_outcome(pre_conversion_metrics, post_conversion_metrics)

        # Regression detection (compare before vs after)
        regressions: List[Dict[str, Any]] = []
        if before_html and after_html:
            if before_sum["broken_ctas"] == 0 and after_sum["broken_ctas"] > 0:
                regressions.append({"type": "broken_cta_regression", "severity": "critical", "detail": "Fix introduced unclickable CTA(s)."})
            if before_sum["has_viewport_meta"] and not after_sum["has_viewport_meta"]:
                regressions.append({"type": "mobile_viewport_regression", "severity": "high", "detail": "Fix removed viewport meta tag."})
            if any(t.console_errors for t in tests):
                regressions.append({"type": "js_console_error_regression", "severity": "high", "detail": "Post-deploy page emitted JS console errors."})

        before_after = BeforeAfterComparison(
            task_id=task.task_id,
            url=target_url,
            test_conditions={
                "viewport": viewport,
                "browser": tests[0].browser if tests else "static_dom_parser",
                "execution_mode": tests[0].execution_mode if tests else "static_dom_only",
                "verified_at": datetime.now(timezone.utc).isoformat(),
            },
            before_dom_id=before_dom_id,
            after_dom_id=after_dom_id,
            before_headline=before_sum["headline"],
            after_headline=after_sum["headline"],
            before_value_prop=before_sum["subheadline"],
            after_value_prop=after_sum["subheadline"],
            before_cta=before_sum["primary_cta"],
            after_cta=after_sum["primary_cta"],
            before_form_fields={"forms": before_sum["forms"]},
            after_form_fields={"forms": after_sum["forms"]},
            before_mobile_layout={"has_viewport_meta": before_sum["has_viewport_meta"]},
            after_mobile_layout={"has_viewport_meta": after_sum["has_viewport_meta"]},
            before_conversion_metrics=pre_conversion_metrics,
            after_conversion_metrics=post_conversion_metrics,
            before_finding_status="open",
            after_verification_status="regression_detected" if regressions else ("verified" if (implementation_verified == "passed" and functional_verification != "failed") else "failed"),
        )

        ver = CROVerification(
            tenant_id=tenant_id,
            audit_id=task.audit_id,
            url=target_url,
            task_id=task.task_id,
            finding_ids=task.linked_finding_ids,
            source_evidence_ids=[sid for sid in (before_dom_id, after_dom_id) if sid] + [t.test_id for t in tests],
            verifier=verifier,
            implementation_verified=implementation_verified,
            functional_verification=functional_verification,
            analytics_verification=analytics_verification,
            business_outcome=business_outcome,
            criteria_results=criteria_results,
            regressions_detected=regressions,
            before_after=before_after,
            notes=biz_note,
        )
        self.store.save_verification(ver)

        # Update task state strictly based on independent verification
        task.after_evidence = {
            "verification_id": ver.verification_id,
            "implementation_verified": implementation_verified,
            "functional_verification": functional_verification,
            "analytics_verification": analytics_verification,
            "business_outcome": business_outcome,
            "regressions_count": len(regressions),
        }
        if regressions:
            task.verification_status = "regression_detected"
            task.status = CROTaskStatus.REOPENED.value
        elif implementation_verified == "passed" and functional_verification != "failed":
            task.verification_status = "verified"
            task.status = CROTaskStatus.VERIFIED.value
        else:
            task.verification_status = "failed"
            task.status = CROTaskStatus.REOPENED.value
        self.store.save_remediation_task(task)
        return ver

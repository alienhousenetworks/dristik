"""Department E — CTA Intelligence, Forms & Lead-Generation Optimization (Phases 11–12).

Builds the complete CTA registry (with hierarchy classification) and Form Intelligence
engine (field necessity balancing completion rate vs sales qualification quality,
validation behavior, error messaging, slow/failed submission handling, mobile keyboard,
privacy reassurance, and contact/booking journeys).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from app.cro.analyzer import EXPLORATORY_PATTERNS, HIGH_INTENT_PATTERNS, PASSIVE_GENERIC_PATTERNS
from app.cro.models import (
    CROAgentOutput,
    CROBusinessModelType,
    CRODimensionCheck,
    CROFinding,
    CROSeverity,
    EvidenceSourceType,
)
from app.cro.specialists import CROAuditContext


def _classify_cta_hierarchy(text: str, section: str, classes: str) -> str:
    low = text.lower()
    if section == "header":
        return "primary" if any(k in classes for k in ("primary", "cta", "btn")) else "navigation"
    if any(k in low for k in ("privacy", "terms", "support", "help", "faq", "security")):
        return "trust_support"
    if any(k in classes for k in ("primary", "hero-cta")) or (section == "hero" and any(re.search(p, low) for p in HIGH_INTENT_PATTERNS)):
        return "primary"
    if any(k in classes for k in ("secondary", "outline", "ghost")) or any(re.search(p, low) for p in EXPLORATORY_PATTERNS):
        return "secondary"
    return "tertiary"


def run_department_e(ctx: CROAuditContext) -> CROAgentOutput:
    findings: List[CROFinding] = []
    evidence_ids: List[str] = []
    limitations: List[str] = []

    ctas = [e for e in ctx.elements if e.element_category == "cta"]
    forms = [e for e in ctx.elements if e.element_category == "form"]
    primary_goal = next((g for g in ctx.goals if g.goal_type == "primary"), ctx.goals[0] if ctx.goals else None)

    broken_ctas = []
    for c in ctas:
        low = (c.text or "").lower()
        classes = str((c.attributes or {}).get("classes", ""))
        c.cta_hierarchy = _classify_cta_hierarchy(c.text or "", c.section, classes)
        if any(re.search(p, low) for p in PASSIVE_GENERIC_PATTERNS):
            c.intent_category = "passive_generic"
        elif any(re.search(p, low) for p in HIGH_INTENT_PATTERNS):
            c.intent_category = "high_intent"
        else:
            c.intent_category = "exploratory"
        if primary_goal and c.cta_hierarchy == "primary":
            c.related_goal_id = primary_goal.goal_id
        if c.clickable is False or c.interaction_result in ("broken_or_unclickable", "unclickable_or_hidden"):
            broken_ctas.append(c)
        evidence_ids.append(c.element_id)

    # Check 1: Broken/unclickable CTAs (CONFIRMED technical/browser defect)
    cta_tests = [t for t in ctx.interaction_tests if t.scenario == "cta_click"]
    cta_ev_type = (
        EvidenceSourceType.BROWSER_TEST
        if any(t.execution_mode == "playwright_live" for t in cta_tests)
        else EvidenceSourceType.DIRECT_TECHNICAL
    )
    if broken_ctas:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-CTA-BROKEN-{ctx.audit_id[-6:]}-01",
                category="cta_intelligence",
                subcategory="broken_cta",
                department="E",
                agent_id="cro_interaction",
                title=f"Broken or Unclickable CTA Control Detected ({len(broken_ctas)} Element(s))",
                description=(
                    f"Confirmed non-functional CTA element(s): {', '.join(f'{c.text or c.selector} on {c.url}' for c in broken_ctas[:5])}. "
                    "Element is disabled, hidden via CSS/pointer-events, or points to an empty/dead destination."
                ),
                root_cause="Disabled attribute, `pointer-events: none`, or missing/dead `href` destination on conversion CTA.",
                affected_urls=list(dict.fromkeys(c.url for c in broken_ctas))[:10],
                affected_elements=[c.element_id for c in broken_ctas[:10]],
                affected_journeys=[j.journey_id for j in ctx.journeys],
                evidence_ids=[c.element_id for c in broken_ctas[:5]] + [t.test_id for t in cta_tests[:3]],
                source_type=cta_ev_type,
                severity=CROSeverity.CRITICAL,
                confidence=0.98,
                recommendation="Restore clickability and bind a verified working destination URL or active submit handler on every broken conversion CTA.",
                implementation_instructions="Remove blocking `disabled`/`pointer-events: none` states and replace empty `#`/`javascript:void(0)` hrefs with valid target routes.",
                owner_role="Frontend Engineering",
                effort="low",
                priority_score=98.0,
                acceptance_criteria=[
                    "CTA is visible, keyboard focusable, and clickable across desktop and mobile viewports.",
                    "Clicking CTA navigates to a 200 OK target or triggers the expected form/modal interaction.",
                ],
            )
        )

    # Form Intelligence & Qualification Trade-Off
    unlabeled_forms = []
    validation_broken_forms = []
    slow_or_error_forms = []
    long_forms = []
    form_registry: List[Dict[str, Any]] = []
    is_b2b_qual = ctx.profile.business_type in (
        CROBusinessModelType.B2B_LEAD_GEN,
        CROBusinessModelType.PROFESSIONAL_SERVICES,
        CROBusinessModelType.FINANCIAL_SERVICES,
        CROBusinessModelType.SAAS,
    )

    for f in forms:
        attrs = f.attributes or {}
        evidence_ids.append(f.element_id)
        f_count = int(attrs.get("field_count") or 0)
        missing_lbl = int(attrs.get("missing_labels") or 0)
        no_err_region = bool(attrs.get("has_novalidate") and not attrs.get("has_error_region"))
        srv_err = attrs.get("simulated_server_error")
        resp_ms = attrs.get("response_ms")

        if missing_lbl > 0:
            unlabeled_forms.append(f)
        if no_err_region or attrs.get("invalid_email_type", 0) > 0:
            validation_broken_forms.append(f)
        if srv_err or (isinstance(resp_ms, int) and resp_ms >= 3000):
            slow_or_error_forms.append(f)
        if f_count >= 7:
            long_forms.append(f)

        # Explicitly respect Lead Quality vs Completion Volume trade-off (Phase 12)
        if f_count >= 7 and is_b2b_qual:
            qual_note = (
                f"{f_count} fields detected on a {ctx.profile.business_type.value} form. Do NOT blindly delete fields "
                "required for sales qualification; evaluate progressive multi-step disclosure or CRM enrichment to balance completion and lead quality."
            )
        elif f_count >= 7:
            qual_note = f"{f_count} fields detected; review field necessity against conversion goal and consider multi-step disclosure."
        else:
            qual_note = f"{f_count} fields detected; field count within standard range."

        form_registry.append(
            {
                "form_id": attrs.get("form_id") or f.element_id,
                "element_id": f.element_id,
                "url": f.url,
                "field_count": f_count,
                "required_fields": int(attrs.get("required_fields") or 0),
                "missing_labels": missing_lbl,
                "validation_state": "failed" if (no_err_region or srv_err) else ("warning" if attrs.get("invalid_email_type", 0) > 0 else "passed"),
                "submission_test_state": "failed" if srv_err else ("slow_response" if (isinstance(resp_ms, int) and resp_ms >= 3000) else "safe_mode_static"),
                "response_ms": resp_ms,
                "has_privacy_reassurance": bool(attrs.get("has_privacy_reassurance")),
                "qualification_tradeoff_note": qual_note,
            }
        )

    form_tests = [t for t in ctx.interaction_tests if t.scenario == "form_validation"]
    form_ev_type = (
        EvidenceSourceType.BROWSER_TEST
        if any(t.execution_mode == "playwright_live" for t in form_tests)
        else EvidenceSourceType.DIRECT_TECHNICAL
    )

    if unlabeled_forms or validation_broken_forms:
        affected = list(dict.fromkeys([f.url for f in unlabeled_forms + validation_broken_forms]))
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-FORM-VAL-{ctx.audit_id[-6:]}-01",
                category="form_optimization",
                subcategory="form_validation_and_labels",
                department="E",
                agent_id="cro_form_validation",
                title="Form Validation, Error Messaging, or Input Labeling Defects",
                description=(
                    f"Inspected {len(forms)} form(s): {len(unlabeled_forms)} form(s) have unlabeled input fields and "
                    f"{len(validation_broken_forms)} form(s) have missing/invalid validation feedback or improper input types."
                ),
                root_cause="Form inputs omit programmatic `<label for>`, proper `type='email'/'tel'`, or accessible `role='alert'` validation messaging.",
                affected_urls=affected[:10],
                affected_elements=[f.element_id for f in (unlabeled_forms + validation_broken_forms)[:10]],
                affected_journeys=[j.journey_id for j in ctx.journeys],
                evidence_ids=[f.element_id for f in (unlabeled_forms + validation_broken_forms)[:5]] + [t.test_id for t in form_tests[:3]],
                source_type=form_ev_type,
                severity=CROSeverity.HIGH,
                confidence=0.95,
                recommendation="Add explicit `<label for>` associations, semantic HTML5 input types (`email`, `tel`), inline validation, and accessible `role='alert'` error messages explaining how to fix each invalid field.",
                implementation_instructions="Bind every input to a visible `<label>`, enforce field-level validation with clear recovery copy, and preserve user input on validation failure.",
                owner_role="Frontend Engineering",
                effort="medium",
                priority_score=88.0,
                acceptance_criteria=[
                    "All form inputs have explicit accessible labels.",
                    "Empty submission and invalid email/phone produce specific field-level error messages.",
                    "Valid sandbox test submission displays a clear confirmation state and records the conversion event.",
                ],
            )
        )

    if slow_or_error_forms:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-FORM-SUB-{ctx.audit_id[-6:]}-01",
                category="form_optimization",
                subcategory="form_submission_reliability",
                department="E",
                agent_id="cro_error_messaging",
                title="Form Submission Error or Slow Response Handling Defect",
                description=(
                    f"Detected submission error or slow response (>=3000ms) on {len(slow_or_error_forms)} form(s). "
                    "Without clear loading feedback, duplicate-click prevention, and error recovery, visitors abandon or double-submit."
                ),
                root_cause="Form endpoint error or excessive server latency without resilient UI loading/retry states.",
                affected_urls=list(dict.fromkeys(f.url for f in slow_or_error_forms))[:10],
                affected_elements=[f.element_id for f in slow_or_error_forms[:10]],
                affected_journeys=[j.journey_id for j in ctx.journeys],
                evidence_ids=[f.element_id for f in slow_or_error_forms[:5]] + [t.test_id for t in form_tests[:3]],
                source_type=EvidenceSourceType.BROWSER_TEST if form_tests else EvidenceSourceType.DIRECT_TECHNICAL,
                severity=CROSeverity.CRITICAL if any((f.attributes or {}).get("simulated_server_error") for f in slow_or_error_forms) else CROSeverity.HIGH,
                confidence=0.93,
                recommendation="Fix server-side submission failure, optimize response latency under 1s, show an immediate loading spinner with button lock to prevent duplicates, and provide actionable error recovery.",
                implementation_instructions="Disable submit button during in-flight request, surface structured error banners preserving field values, and monitor submission endpoint SLA.",
                owner_role="Full-Stack Engineering",
                effort="medium",
                priority_score=94.0,
                acceptance_criteria=[
                    "Sandbox test submission succeeds with 2xx status in < 1000ms.",
                    "Double-clicking submit does not send duplicate requests.",
                    "Simulated server failure preserves input values and explains recovery.",
                ],
            )
        )

    if long_forms:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-FORM-LEN-{ctx.audit_id[-6:]}-01",
                category="lead_generation_cro",
                subcategory="field_necessity_and_qualification",
                department="E",
                agent_id="cro_lead_qualification",
                title=f"High Form Field Count ({max(int((f.attributes or {}).get('field_count', 0)) for f in long_forms)} Fields) — Evaluate Qualification vs Completion Trade-Off",
                description=(
                    f"{len(long_forms)} form(s) request 7 or more fields. While qualification fields may protect sales capacity, "
                    "long monolithic forms can increase abandonment; test progressive multi-step capture rather than removing required qualification blindly."
                ),
                root_cause="All contact and qualification fields presented simultaneously in a single step.",
                affected_urls=list(dict.fromkeys(f.url for f in long_forms))[:10],
                affected_elements=[f.element_id for f in long_forms[:10]],
                evidence_ids=[f.element_id for f in long_forms[:5]],
                source_type=EvidenceSourceType.HEURISTIC_OBSERVATION,
                severity=CROSeverity.MEDIUM,
                confidence=0.78,
                recommendation="Audit each field with Sales for qualification necessity; convert multi-section forms to a 2-step progressive flow and monitor both completion rate and qualified lead rate.",
                implementation_instructions="Keep mandatory qualification fields while testing progressive disclosure (Step 1: Contact -> Step 2: Qualification) with CRM lead-quality guardrails.",
                owner_role="Product / RevOps",
                effort="medium",
                priority_score=70.0,
                acceptance_criteria=[
                    "Every required field maps to a documented sales qualification rule.",
                    "Experiment monitors both Form Completion Rate and Qualified Lead Rate.",
                ],
            )
        )

    # Dimension checks for Forms & CTA Effectiveness
    cta_func_score = 0.0 if (ctas and len(broken_ctas) == len(ctas)) else (max(0.2, 1.0 - (len(broken_ctas) * 0.45)) if ctas else 0.4)
    form_qual_score = 1.0
    if slow_or_error_forms:
        form_qual_score -= 0.45
    if unlabeled_forms or validation_broken_forms:
        form_qual_score -= 0.35
    if long_forms:
        form_qual_score -= 0.15

    ctx.dimension_checks.extend(
        [
            CRODimensionCheck(
                check_id="dept_e_cta_reliability",
                dimension_id="forms_cta",
                label="CTA clickability, destination integrity, and hierarchy",
                weight=2.0,
                result=round(cta_func_score, 2),
                source_type=cta_ev_type,
                evidence_ids=[c.element_id for c in ctas[:5]],
            ),
            CRODimensionCheck(
                check_id="dept_e_form_usability",
                dimension_id="forms_cta",
                label="Form labels, validation feedback, and submission reliability",
                weight=2.0,
                result=round(max(0.1, form_qual_score), 2) if forms else None,
                applicable=bool(forms),
                executed=bool(forms),
                source_type=form_ev_type,
                evidence_ids=[f.element_id for f in forms[:5]],
                note="Excluded without penalty if site has no forms." if not forms else "",
            ),
        ]
    )

    ctx.artifacts["forms_cta_workspace"] = {
        "cta_count": len(ctas),
        "broken_ctas_count": len(broken_ctas),
        "cta_hierarchy_counts": {
            tier: sum(1 for c in ctas if c.cta_hierarchy == tier)
            for tier in ("primary", "secondary", "tertiary", "navigation", "trust_support")
        },
        "forms_count": len(forms),
        "forms_registry": form_registry,
        "roles_executed": [
            "cro_form_discovery",
            "cro_form_usability",
            "cro_field_necessity",
            "cro_form_validation",
            "cro_error_messaging",
            "cro_lead_qualification",
            "cro_contact_journey",
        ],
    }

    return CROAgentOutput(
        agent_id="cro_department_e_forms_cta",
        department="E",
        status="completed",
        audit_id=ctx.audit_id,
        findings=findings,
        evidence_ids=list(dict.fromkeys(evidence_ids))[:30],
        confidence=0.9,
        limitations=limitations,
        artifacts=ctx.artifacts["forms_cta_workspace"],
    )

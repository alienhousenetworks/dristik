"""Phase 21 — Consolidated CRO Remediation Center.

Core Dristik differentiator: analyzes the complete CRO audit first, validates and
deduplicates findings, clusters related issues into coordinated Root-Cause Initiatives,
detects conflicting changes and dependencies, prioritizes by business importance,
evidence strength, risk, effort, and confidence, and emits ONE coordinated CRO Fixing Pack
containing all 18 enterprise deliverables + Page-Level Implementation Sheets + operational
views (Kanban, List, Priority Matrix, Roadmap, Calendar, Verification Queue, Department
Workload, Blocked Tasks, Before/After Comparison, Regression Tracking).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.cro.models import (
    CROBusinessProfile,
    CROFinding,
    CRORemediationPack,
    CRORemediationTask,
    CROSeverity,
    CROTaskStatus,
    CROThreeScorecardBundle,
    EvidenceSourceType,
)

# Maps finding categories/subcategories into coordinated Root-Cause Initiatives
ROOT_CAUSE_GROUP_MAP: Dict[str, Tuple[str, str, str, str]] = {
    # key -> (group_key, initiative_title, department, deliverable_key)
    "form_optimization": ("contact_form_friction", "Coordinated Form Usability, Validation & Submission Remediation", "Engineering", "form_optimization_plan"),
    "lead_generation_cro": ("contact_form_friction", "Coordinated Form Usability, Validation & Submission Remediation", "Product", "form_optimization_plan"),
    "cta_intelligence": ("cta_and_action_hierarchy", "Primary CTA Reliability, Visibility & Hierarchy Overhaul", "Engineering", "ui_improvement_plan"),
    "ui_audit": ("cta_and_action_hierarchy", "Primary CTA Reliability, Visibility & Hierarchy Overhaul", "Design", "ui_improvement_plan"),
    "landing_page_optimization": ("landing_page_messaging", "Landing Page Value Proposition, Copy & Structure Optimization", "Marketing", "landing_page_plan"),
    "copywriting_optimization": ("landing_page_messaging", "Landing Page Value Proposition, Copy & Structure Optimization", "Marketing", "copywriting_plan"),
    "ecommerce_cro": ("ecommerce_checkout_flow", "Ecommerce Product, Cart, Checkout & Fulfillment Transparency", "Engineering", "ecommerce_plan"),
    "trust_optimization": ("trust_and_credibility", "Trust Signal Attribution, Social Proof & Policy Transparency", "Marketing", "trust_improvement_plan"),
    "mobile_cro": ("mobile_experience_fixes", "Mobile Responsive Layout, Navigation & Touch Ergonomics", "Engineering", "mobile_optimization_plan"),
    "accessibility": ("accessibility_compliance", "Inclusive Conversion Controls & WCAG 2.2 AA Accessibility", "Engineering", "accessibility_plan"),
    "performance_interaction": ("performance_and_stability", "Core Web Vitals, Script Hygiene & Runtime Error Remediation", "Engineering", "performance_plan"),
    "analytics_intelligence": ("analytics_measurement_foundation", "Analytics Tag Integrity, Conversion Event & Data Quality Fixes", "Analytics", "analytics_implementation_plan"),
    "funnel_optimization": ("journey_and_funnel_leakage", "Conversion Journey Continuity & Measured Funnel Leakage Fixes", "Product", "journey_improvement_plan"),
    "ux_audit": ("ux_navigation_usability", "Navigation Architecture, Cognitive Load & Usability Cleanup", "Design", "ux_remediation_plan"),
    "conversion_strategy": ("business_goal_alignment", "Business Profile, Conversion Goal & Strategy Alignment", "Product", "business_objective_plan"),
}

EVIDENCE_STRENGTH_WEIGHT: Dict[str, float] = {
    EvidenceSourceType.DIRECT_TECHNICAL.value: 1.0,
    EvidenceSourceType.BROWSER_TEST.value: 1.0,
    EvidenceSourceType.ANALYTICS_OBSERVATION.value: 0.95,
    EvidenceSourceType.EXPERIMENT_RESULT.value: 1.0,
    EvidenceSourceType.USER_RESEARCH.value: 0.85,
    EvidenceSourceType.HEURISTIC_OBSERVATION.value: 0.70,
    EvidenceSourceType.AI_HYPOTHESIS.value: 0.55,
}

SEVERITY_BASE_SCORE: Dict[str, float] = {
    CROSeverity.CRITICAL.value: 100.0,
    CROSeverity.HIGH.value: 80.0,
    CROSeverity.MEDIUM.value: 55.0,
    CROSeverity.LOW.value: 30.0,
    CROSeverity.INFORMATIONAL.value: 15.0,
}

EFFORT_BONUS: Dict[str, float] = {"low": 10.0, "medium": 0.0, "high": -8.0}


def deduplicate_findings(findings: Sequence[CROFinding]) -> Tuple[List[CROFinding], int]:
    """Deduplicate findings by (category, subcategory, normalized title) while merging URLs and evidence."""
    merged: Dict[str, CROFinding] = {}
    dup_count = 0
    for f in findings:
        sig = hashlib.sha1(
            f"{f.category}|{f.subcategory}|{' '.join(f.title.lower().split())}".encode("utf-8")
        ).hexdigest()[:16]
        if sig not in merged:
            merged[sig] = f.model_copy(deep=True)
        else:
            dup_count += 1
            existing = merged[sig]
            existing.affected_urls = list(dict.fromkeys(existing.affected_urls + f.affected_urls))
            existing.affected_elements = list(dict.fromkeys(existing.affected_elements + f.affected_elements))
            existing.evidence_ids = list(dict.fromkeys(existing.evidence_ids + f.evidence_ids))
            existing.affected_devices = list(dict.fromkeys(existing.affected_devices + f.affected_devices))
            if SEVERITY_BASE_SCORE.get(f.severity.value, 0) > SEVERITY_BASE_SCORE.get(existing.severity.value, 0):
                existing.severity = f.severity
    return list(merged.values()), dup_count


class CRORemediationCenter:
    """Builds the consolidated CRO remediation pack and operational task backlog."""

    @classmethod
    def generate_pack(
        cls,
        *,
        tenant_id: str,
        audit_id: str,
        profile: CROBusinessProfile,
        findings: Sequence[CROFinding],
        scorecard: CROThreeScorecardBundle,
        artifacts: Dict[str, Any],
        experiments: Sequence[Any] = (),
    ) -> CRORemediationPack:
        unique_findings, dup_count = deduplicate_findings(findings)

        # Group findings into coordinated root-cause initiatives
        groups: Dict[str, List[CROFinding]] = {}
        group_meta: Dict[str, Tuple[str, str, str]] = {}
        for f in unique_findings:
            g_key, g_title, dept, deliv = ROOT_CAUSE_GROUP_MAP.get(
                f.category,
                (f"cro_{f.category}", f"Coordinated {f.category.replace('_', ' ').title()} Remediation", "Product", "ux_remediation_plan"),
            )
            f.root_cause_group_id = g_key
            groups.setdefault(g_key, []).append(f)
            group_meta[g_key] = (g_title, dept, deliv)

        # Create coordinated CRORemediationTask per root-cause group
        tasks: List[CRORemediationTask] = []
        root_cause_groups_summary: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        copy_proposals = (artifacts.get("landing_copy_workspace") or {}).get("copy_proposals") or []

        for idx, (g_key, g_findings) in enumerate(groups.items(), start=1):
            g_title, dept, deliv = group_meta[g_key]
            # Composite priority score factoring severity, evidence strength, effort, confidence
            ranked_scores = []
            for gf in g_findings:
                sev_s = SEVERITY_BASE_SCORE.get(gf.severity.value, 50.0)
                ev_w = EVIDENCE_STRENGTH_WEIGHT.get(gf.source_type.value, 0.7)
                eff_b = EFFORT_BONUS.get(gf.effort, 0.0)
                conf_w = gf.confidence if gf.confidence is not None else 0.75
                ranked_scores.append((sev_s * ev_w * (0.7 + 0.3 * conf_w)) + eff_b)
            max_score = max(ranked_scores) if ranked_scores else 50.0

            if max_score >= 82.0 or any(gf.severity == CROSeverity.CRITICAL for gf in g_findings):
                priority, window, due_days = "P0", "days_30", 7
            elif max_score >= 62.0:
                priority, window, due_days = "P1", "days_30", 21
            elif max_score >= 40.0:
                priority, window, due_days = "P2", "days_60", 45
            else:
                priority, window, due_days = "P3", "days_90", 75

            efforts = [gf.effort for gf in g_findings]
            effort = "high" if "high" in efforts else ("medium" if "medium" in efforts else "low")
            urls = list(dict.fromkeys(u for gf in g_findings for u in gf.affected_urls))
            elements = list(dict.fromkeys(e for gf in g_findings for e in gf.affected_elements))
            journeys = list(dict.fromkeys(j for gf in g_findings for j in gf.affected_journeys))
            devices = list(dict.fromkeys(d for gf in g_findings for d in gf.affected_devices)) or ["desktop", "mobile"]
            ev_ids = list(dict.fromkeys(eid for gf in g_findings for eid in gf.evidence_ids))
            criteria = list(dict.fromkeys(c for gf in g_findings for c in gf.acceptance_criteria))
            proposed_changes = " ".join(dict.fromkeys(gf.recommendation for gf in g_findings if gf.recommendation))
            instructions = " | ".join(dict.fromkeys(gf.implementation_instructions for gf in g_findings if gf.implementation_instructions))

            orig_copy, upd_copy = None, None
            if g_key == "landing_page_messaging" and copy_proposals:
                orig_copy = copy_proposals[0].get("original_copy")
                upd_copy = copy_proposals[0].get("recommended_copy")

            task = CRORemediationTask(
                tenant_id=tenant_id,
                audit_id=audit_id,
                task_id=f"CRO-TASK-{audit_id[-6:]}-{idx:02d}",
                url=urls[0] if urls else profile.website_url,
                source_evidence_ids=ev_ids,
                root_cause_group=g_key,
                title=g_title,
                linked_finding_ids=[gf.finding_id for gf in g_findings],
                affected_urls=urls[:25],
                affected_components=elements[:25],
                affected_journeys=journeys[:10],
                affected_devices=devices,
                business_objective=profile.primary_conversion,
                deliverable_section=deliv,
                proposed_change=proposed_changes,
                original_copy_or_design=orig_copy,
                updated_copy_or_design=upd_copy,
                implementation_instructions=instructions,
                owner=g_findings[0].owner_role or dept,
                department=dept,
                effort_estimate=effort,
                priority=priority,
                roadmap_window=window,
                due_date=(now + timedelta(days=due_days)).date().isoformat(),
                approval_status="pending",
                acceptance_criteria=criteria or ["Independent post-deployment functional and visual verification passes."],
                before_evidence={
                    "finding_ids": [gf.finding_id for gf in g_findings],
                    "evidence_ids": ev_ids[:10],
                    "affected_urls": urls[:10],
                    "observed_defects": [gf.title for gf in g_findings],
                },
                verification_status="unverified",
                status=CROTaskStatus.BACKLOG.value,
            )
            tasks.append(task)
            root_cause_groups_summary.append(
                {
                    "group_id": g_key,
                    "title": g_title,
                    "department": dept,
                    "priority": priority,
                    "task_id": task.task_id,
                    "finding_ids": [gf.finding_id for gf in g_findings],
                    "finding_count": len(g_findings),
                }
            )

        # Sort tasks P0 -> P3
        prio_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        tasks.sort(key=lambda t: (prio_order.get(t.priority, 9), t.task_id))

        # Dependencies & Conflict Detection (e.g., analytics fixes before experiment/copy rollout; CTA UI vs copy changes on same URL)
        task_by_group = {t.root_cause_group: t for t in tasks}
        conflicts_detected: List[Dict[str, Any]] = []
        anl_task = task_by_group.get("analytics_measurement_foundation")
        if anl_task:
            for t in tasks:
                if t.root_cause_group in ("landing_page_messaging", "journey_and_funnel_leakage", "ecommerce_checkout_flow"):
                    t.dependencies.append(f"{anl_task.task_id} (Verify analytics tracking before measuring outcome)")

        cta_task = task_by_group.get("cta_and_action_hierarchy")
        lp_task = task_by_group.get("landing_page_messaging")
        if cta_task and lp_task and set(cta_task.affected_urls).intersection(lp_task.affected_urls):
            cta_task.conflicting_task_ids.append(lp_task.task_id)
            lp_task.conflicting_task_ids.append(cta_task.task_id)
            conflicts_detected.append(
                {
                    "task_ids": [cta_task.task_id, lp_task.task_id],
                    "reason": "Both tasks modify hero CTA layout and copy on overlapping URLs; coordinate into one release or isolate inside separate A/B experiment variants.",
                    "overlapping_urls": sorted(set(cta_task.affected_urls).intersection(lp_task.affected_urls))[:5],
                }
            )

        # Page-level implementation sheets (exact changes by URL)
        by_url: Dict[str, List[Dict[str, Any]]] = {}
        for t in tasks:
            for u in t.affected_urls or [profile.website_url]:
                by_url.setdefault(u, []).append(
                    {
                        "task_id": t.task_id,
                        "priority": t.priority,
                        "title": t.title,
                        "proposed_change": t.proposed_change,
                        "acceptance_criteria": t.acceptance_criteria,
                    }
                )
        page_sheets = [{"url": u, "tasks_count": len(items), "changes": items} for u, items in by_url.items()]

        # Remaining-risk report (unresolved, unmeasured, or blocked items)
        remaining_risks: List[Dict[str, Any]] = []
        if scorecard.business_performance_status == "data_unavailable":
            remaining_risks.append(
                {
                    "risk": "Analytics & business performance unmeasured",
                    "status": "unmeasured",
                    "detail": "No connected GA4/CRM telemetry; conversion impact of remediation tasks cannot be proven until tracking is connected.",
                }
            )
        if profile.unknown_fields:
            remaining_risks.append(
                {
                    "risk": "Incomplete business context",
                    "status": "unresolved",
                    "detail": f"Unknown business profile inputs: {', '.join(profile.unknown_fields[:8])}.",
                }
            )
        remaining_risks.append(
            {
                "risk": "Manual assistive-technology accessibility review",
                "status": "manual_review_required",
                "detail": "Automated WCAG screening does not replace keyboard-only and screen-reader (NVDA/VoiceOver) verification.",
            }
        )

        def _tasks_for(deliv_key: str) -> List[Dict[str, Any]]:
            return [
                {"task_id": t.task_id, "priority": t.priority, "title": t.title, "department": t.department, "effort": t.effort_estimate}
                for t in tasks
                if t.deliverable_section == deliv_key
            ]

        # All 18 consolidated CRO remediation pack deliverables (Phase 21)
        exec_summary = (
            f"Consolidated {len(unique_findings)} validated CRO finding(s) ({dup_count} duplicate(s) merged) "
            f"into {len(tasks)} coordinated root-cause remediation task(s) for {profile.domain} "
            f"(business model: {profile.business_type.value}, experience score: {scorecard.experience_score}, "
            f"measurement score: {scorecard.measurement_score})."
        )

        deliverables: Dict[str, Any] = {
            "01_executive_cro_summary": {"summary": exec_summary, "p0_count": sum(1 for t in tasks if t.priority == "P0"), "total_tasks": len(tasks)},
            "02_business_objective_plan": {"primary_conversion": profile.primary_conversion, "secondary_conversions": profile.secondary_conversions, "tasks": _tasks_for("business_objective_plan")},
            "03_journey_improvement_plan": {"tasks": _tasks_for("journey_improvement_plan")},
            "04_ux_remediation_plan": {"tasks": _tasks_for("ux_remediation_plan")},
            "05_ui_improvement_plan": {"tasks": _tasks_for("ui_improvement_plan")},
            "06_landing_page_plan": {"tasks": _tasks_for("landing_page_plan"), "wireframe": (artifacts.get("landing_copy_workspace") or {}).get("proposed_wireframe")},
            "07_copywriting_plan": {"tasks": _tasks_for("copywriting_plan"), "copy_proposals": copy_proposals},
            "08_form_optimization_plan": {"tasks": _tasks_for("form_optimization_plan"), "forms_registry": (artifacts.get("forms_cta_workspace") or {}).get("forms_registry", [])},
            "09_ecommerce_plan": {"applicable": bool((artifacts.get("ecommerce_audit") or {}).get("applicable")), "tasks": _tasks_for("ecommerce_plan")},
            "10_trust_improvement_plan": {"tasks": _tasks_for("trust_improvement_plan"), "missing_proof": (artifacts.get("trust_audit") or {}).get("missing_proof_inventory", [])},
            "11_mobile_optimization_plan": {"tasks": _tasks_for("mobile_optimization_plan")},
            "12_accessibility_plan": {"tasks": _tasks_for("accessibility_plan"), "manual_review": (artifacts.get("ux_mobile_a11y") or {}).get("manual_wcag_checks_required", [])},
            "13_performance_plan": {"tasks": _tasks_for("performance_plan")},
            "14_analytics_implementation_plan": {"tasks": _tasks_for("analytics_implementation_plan"), "measurement_checks": scorecard.measurement_checks},
            "15_experimentation_plan": {"experiments_count": len(experiments), "experiments": [e.model_dump() if hasattr(e, "model_dump") else e for e in experiments]},
            "16_page_level_implementation_sheets": page_sheets,
            "17_verification_plan": {
                "policy": "Developer deployment marks tasks AWAITING_VERIFICATION. Independent verification records implementation, functional, analytics, and business outcomes separately.",
                "tasks_requiring_verification": [t.task_id for t in tasks],
            },
            "18_remaining_risk_report": remaining_risks,
        }

        return CRORemediationPack(
            tenant_id=tenant_id,
            audit_id=audit_id,
            url=profile.website_url,
            executive_summary=exec_summary,
            root_cause_groups=root_cause_groups_summary,
            deliverables=deliverables,
            tasks=tasks,
            conflicts_detected=conflicts_detected,
            remaining_risks=remaining_risks,
            page_implementation_sheets=page_sheets,
            total_findings_consolidated=len(unique_findings),
            deduplicated_count=dup_count,
        )

    @staticmethod
    def build_operational_views(tasks: Sequence[CRORemediationTask]) -> Dict[str, Any]:
        """Return all 10 required remediation workspace views from canonical task records."""
        kanban = {
            "backlog": [t.model_dump() for t in tasks if t.status == CROTaskStatus.BACKLOG.value],
            "approved": [t.model_dump() for t in tasks if t.status == CROTaskStatus.APPROVED.value],
            "in_progress": [t.model_dump() for t in tasks if t.status == CROTaskStatus.IN_PROGRESS.value],
            "awaiting_verification": [t.model_dump() for t in tasks if t.status in (CROTaskStatus.DEPLOYED.value, CROTaskStatus.AWAITING_VERIFICATION.value)],
            "verified": [t.model_dump() for t in tasks if t.status == CROTaskStatus.VERIFIED.value],
            "blocked_or_reopened": [t.model_dump() for t in tasks if t.status in (CROTaskStatus.BLOCKED.value, CROTaskStatus.REOPENED.value)],
        }
        priority_matrix = {
            "quick_wins_high_impact_low_effort": [t.task_id for t in tasks if t.priority in ("P0", "P1") and t.effort_estimate == "low"],
            "major_projects_high_impact_high_effort": [t.task_id for t in tasks if t.priority in ("P0", "P1") and t.effort_estimate != "low"],
            "fill_ins_medium_low_effort": [t.task_id for t in tasks if t.priority in ("P2", "P3") and t.effort_estimate == "low"],
            "strategic_backlog": [t.task_id for t in tasks if t.priority in ("P2", "P3") and t.effort_estimate != "low"],
        }
        roadmap = {
            "days_30": [t.task_id for t in tasks if t.roadmap_window == "days_30"],
            "days_60": [t.task_id for t in tasks if t.roadmap_window == "days_60"],
            "days_90": [t.task_id for t in tasks if t.roadmap_window == "days_90"],
        }
        dept_workload: Dict[str, int] = {}
        for t in tasks:
            dept_workload[t.department] = dept_workload.get(t.department, 0) + 1
        calendar = sorted(
            [{"task_id": t.task_id, "title": t.title, "due_date": t.due_date, "priority": t.priority, "status": t.status} for t in tasks],
            key=lambda x: x["due_date"] or "9999-12-31",
        )
        return {
            "kanban": kanban,
            "list": [t.model_dump() for t in tasks],
            "priority_matrix": priority_matrix,
            "roadmap": roadmap,
            "calendar": calendar,
            "verification_queue": [t.model_dump() for t in tasks if t.status in (CROTaskStatus.DEPLOYED.value, CROTaskStatus.AWAITING_VERIFICATION.value)],
            "department_workload": dept_workload,
            "blocked_tasks": [t.model_dump() for t in tasks if t.status == CROTaskStatus.BLOCKED.value or bool(t.conflicting_task_ids)],
            "before_and_after": [{"task_id": t.task_id, "before": t.before_evidence, "after": t.after_evidence} for t in tasks],
            "regressions": [t.model_dump() for t in tasks if t.verification_status == "regression_detected" or t.status == CROTaskStatus.REOPENED.value],
        }

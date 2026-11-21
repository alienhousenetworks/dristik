"""Phase 25 — Continuous CRO Monitoring & Regression Alerting Engine.

Monitors critical landing pages, forms, CTAs, checkout paths, conversion events,
funnel shifts, mobile layout regressions, JS errors, and experiment guardrails,
generating evidence-backed CROMonitoringAlert records persisted in CROStore.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from app.cro.models import (
    CROAudit,
    CROExperiment,
    CROFinding,
    CROMonitoringAlert,
    CROMonitoringSchedule,
    CROSeverity,
)
from app.db.cro_schema import CROStore


class CROMonitoringEngine:
    """Evaluates audit-over-audit deltas and live CRO health conditions to emit alerts."""

    def __init__(self, store: CROStore):
        self.store = store

    def create_schedule(
        self,
        *,
        tenant_id: str,
        domain: str,
        target_urls: Sequence[str],
        cadence: str = "daily",
        checks_enabled: Optional[List[str]] = None,
    ) -> CROMonitoringSchedule:
        sched = CROMonitoringSchedule(
            tenant_id=tenant_id,
            domain=domain,
            target_urls=list(target_urls),
            cadence=cadence,
            checks_enabled=checks_enabled or CROMonitoringSchedule(domain=domain).checks_enabled,
        )
        return self.store.save_monitoring_schedule(sched)

    def evaluate_audit_regression(
        self,
        *,
        tenant_id: str,
        baseline_audit: Optional[CROAudit],
        current_audit: CROAudit,
        current_findings: Sequence[CROFinding],
        experiments: Sequence[CROExperiment] = (),
        schedule_id: Optional[str] = None,
    ) -> List[CROMonitoringAlert]:
        alerts: List[CROMonitoringAlert] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Critical functional alerts (broken form, broken CTA, checkout errors, stopped events)
        for f in current_findings:
            if f.subcategory in ("broken_cta", "form_submission_reliability") and f.severity in (CROSeverity.CRITICAL, CROSeverity.HIGH):
                alerts.append(
                    CROMonitoringAlert(
                        tenant_id=tenant_id,
                        audit_id=current_audit.audit_id,
                        schedule_id=schedule_id,
                        domain=current_audit.domain,
                        alert_type="form_broken" if "form" in f.subcategory else "cta_dest_changed",
                        severity=CROSeverity.CRITICAL,
                        title=f"Critical Conversion Failure: {f.title}",
                        description=f.description,
                        affected_journeys=f.affected_journeys,
                        affected_urls=f.affected_urls,
                        evidence={"finding_id": f.finding_id, "evidence_ids": f.evidence_ids},
                        suggested_action=f.recommendation,
                    )
                )
            elif f.subcategory in ("missing_conversion_events", "duplicate_event_tracking"):
                alerts.append(
                    CROMonitoringAlert(
                        tenant_id=tenant_id,
                        audit_id=current_audit.audit_id,
                        schedule_id=schedule_id,
                        domain=current_audit.domain,
                        alert_type="event_stopped" if f.subcategory == "missing_conversion_events" else "tracking_inconsistent",
                        severity=CROSeverity.HIGH,
                        title=f"Analytics Tracking Alert: {f.title}",
                        description=f.description,
                        affected_urls=f.affected_urls,
                        evidence={"finding_id": f.finding_id},
                        suggested_action=f.recommendation,
                    )
                )
            elif f.subcategory == "responsive_layout":
                alerts.append(
                    CROMonitoringAlert(
                        tenant_id=tenant_id,
                        audit_id=current_audit.audit_id,
                        schedule_id=schedule_id,
                        domain=current_audit.domain,
                        alert_type="mobile_regression",
                        severity=CROSeverity.HIGH,
                        title=f"Mobile Layout Alert: {f.title}",
                        description=f.description,
                        affected_urls=f.affected_urls,
                        evidence={"finding_id": f.finding_id},
                        suggested_action=f.recommendation,
                    )
                )

        # 2. Score regression compared to previous audit
        if (
            baseline_audit
            and baseline_audit.experience_score is not None
            and current_audit.experience_score is not None
            and (baseline_audit.experience_score - current_audit.experience_score) >= 5.0
        ):
            delta = round(current_audit.experience_score - baseline_audit.experience_score, 1)
            alerts.append(
                CROMonitoringAlert(
                    tenant_id=tenant_id,
                    audit_id=current_audit.audit_id,
                    schedule_id=schedule_id,
                    domain=current_audit.domain,
                    alert_type="experience_score_regression",
                    severity=CROSeverity.HIGH,
                    title=f"CRO Experience Score Dropped by {abs(delta)} Points",
                    description=(
                        f"CRO Experience Score declined from {baseline_audit.experience_score} ({baseline_audit.audit_id}) "
                        f"to {current_audit.experience_score} ({current_audit.audit_id}). "
                        f"Methodology: baseline={baseline_audit.methodology_version}, current={current_audit.methodology_version}."
                    ),
                    affected_urls=[current_audit.target_url],
                    evidence={
                        "baseline_audit_id": baseline_audit.audit_id,
                        "baseline_score": baseline_audit.experience_score,
                        "current_score": current_audit.experience_score,
                        "delta": delta,
                    },
                    suggested_action="Inspect newly introduced critical/high findings and verify recent deployments.",
                )
            )

        # 3. Experiment guardrail breach alerts
        for exp in experiments:
            res = exp.latest_result
            if res and (res.guardrail_breached or res.srm_detected):
                alerts.append(
                    CROMonitoringAlert(
                        tenant_id=tenant_id,
                        audit_id=current_audit.audit_id,
                        schedule_id=schedule_id,
                        domain=current_audit.domain,
                        alert_type="guardrail_breached" if res.guardrail_breached else "experiment_srm",
                        severity=CROSeverity.CRITICAL,
                        title=f"Experiment Safety Alert ({exp.experiment_id}): {res.decision.upper()}",
                        description=res.decision_rationale,
                        evidence={"experiment_id": exp.experiment_id, "srm_p_value": res.srm_p_value, "guardrails": res.guardrail_results},
                        suggested_action="Pause or roll back variant immediately and investigate instrumentation/guardrail degradation.",
                    )
                )

        for al in alerts:
            al.created_at = now_iso
            self.store.save_monitoring_alert(al)
        return alerts

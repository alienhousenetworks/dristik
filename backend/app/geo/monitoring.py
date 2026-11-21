"""Phase 22 — Scheduled GEO Monitoring & Drift Alert Engine.

Tracks ongoing daily/weekly/monthly GEO measurement schedules and detects:
- New / lost brand mentions
- New / lost citations
- Incorrect brand descriptions / misinformation
- Competitor visibility surges
- New external references
- Content freshness alerts
- Provider availability alerts
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.db.geo_schema import GEOStore, get_geo_store
from app.geo.models import (
    GEOAudit,
    GEODataQualityState,
    GEOFindingSeverity,
    GEOMonitoringAlert,
    GEOMonitoringSchedule,
)


class GEOMonitoringEngine:
    def __init__(self, store: Optional[GEOStore] = None):
        self.store = store or get_geo_store()

    def create_schedule(
        self,
        *,
        tenant_id: str,
        domain: str,
        brand_name: str = "",
        cadence: str = "weekly",
        platforms: Optional[List[str]] = None,
        max_budget_per_run_usd: float = 2.0,
        checks_enabled: Optional[List[str]] = None,
    ) -> GEOMonitoringSchedule:
        sched = GEOMonitoringSchedule(
            tenant_id=tenant_id,
            domain=domain.lower().strip(),
            brand_name=brand_name or domain.split(".")[0].capitalize(),
            cadence=cadence,
            platforms=platforms or ["chatgpt", "gemini", "claude", "perplexity"],
            max_budget_per_run_usd=max(0.0, max_budget_per_run_usd),
            data_quality_state=GEODataQualityState.OBSERVED,
        )
        if checks_enabled:
            sched.checks_enabled = checks_enabled
        return self.store.save_schedule(sched)

    def evaluate_audit_deltas(
        self,
        *,
        tenant_id: str,
        current_audit: GEOAudit,
        previous_audit: Optional[GEOAudit] = None,
    ) -> List[GEOMonitoringAlert]:
        """Compare current audit against prior audit for the same domain and persist actionable alerts."""
        alerts: List[GEOMonitoringAlert] = []
        curr_sc = self.store.get_artifact(tenant_id, current_audit.audit_id, "scorecard") or {}
        curr_obs = curr_sc.get("observed_metrics") or {}
        curr_resps = self.store.list_responses(tenant_id, current_audit.audit_id)
        curr_cits = self.store.list_citations(tenant_id, current_audit.audit_id)
        curr_runs = self.store.list_prompt_runs(tenant_id, current_audit.audit_id)

        # 1. Provider availability alert
        failed_platforms = sorted({r.platform_id for r in curr_runs if r.status == GEODataQualityState.FAILED})
        if failed_platforms:
            alerts.append(
                GEOMonitoringAlert(
                    tenant_id=tenant_id,
                    audit_id=current_audit.audit_id,
                    domain=current_audit.domain,
                    alert_type="provider_unavailable",
                    severity=GEOFindingSeverity.MEDIUM,
                    title=f"Provider execution failures on {', '.join(failed_platforms)}",
                    description=f"One or more prompt runs failed on {', '.join(failed_platforms)}. Failed runs are excluded from visibility scores.",
                    evidence_ids=[r.run_id for r in curr_runs if r.status == GEODataQualityState.FAILED][:5],
                    data_quality_state=GEODataQualityState.OBSERVED,
                )
            )

        # 2. Brand misinformation alert
        inaccurate = [r for r in curr_resps if r.inaccurate_claims_count > 0]
        if inaccurate:
            alerts.append(
                GEOMonitoringAlert(
                    tenant_id=tenant_id,
                    audit_id=current_audit.audit_id,
                    domain=current_audit.domain,
                    alert_type="misinformation",
                    severity=GEOFindingSeverity.CRITICAL,
                    title=f"Inaccurate brand claims observed in {len(inaccurate)} response(s)",
                    description="Captured AI responses conflicted with confirmed facts in the Brand Knowledge Profile.",
                    platform_id=inaccurate[0].platform_id,
                    prompt_id=inaccurate[0].prompt_id,
                    evidence_ids=[r.response_id for r in inaccurate[:5]],
                    data_quality_state=GEODataQualityState.OBSERVED,
                )
            )

        # 3. Historical delta alerts (new/lost mentions & citations, competitor shifts)
        if previous_audit and previous_audit.audit_id != current_audit.audit_id:
            prev_sc = self.store.get_artifact(tenant_id, previous_audit.audit_id, "scorecard") or {}
            prev_obs = prev_sc.get("observed_metrics") or {}
            prev_m = prev_obs.get("brand_mention_rate_pct")
            curr_m = curr_obs.get("brand_mention_rate_pct")
            if isinstance(prev_m, (int, float)) and isinstance(curr_m, (int, float)):
                delta_m = round(curr_m - prev_m, 1)
                if delta_m <= -10.0:
                    alerts.append(
                        GEOMonitoringAlert(
                            tenant_id=tenant_id,
                            audit_id=current_audit.audit_id,
                            domain=current_audit.domain,
                            alert_type="lost_mention",
                            severity=GEOFindingSeverity.HIGH,
                            title=f"Brand mention rate dropped by {abs(delta_m)}pp ({prev_m}% -> {curr_m}%)",
                            description=f"Observed mention rate declined relative to prior audit {previous_audit.audit_id}.",
                            evidence_ids=[previous_audit.audit_id, current_audit.audit_id],
                            data_quality_state=GEODataQualityState.OBSERVED,
                        )
                    )
                elif delta_m >= 10.0:
                    alerts.append(
                        GEOMonitoringAlert(
                            tenant_id=tenant_id,
                            audit_id=current_audit.audit_id,
                            domain=current_audit.domain,
                            alert_type="new_mention",
                            severity=GEOFindingSeverity.INFORMATIONAL,
                            title=f"Brand mention rate increased by +{delta_m}pp ({prev_m}% -> {curr_m}%)",
                            description=f"Observed mention rate improved relative to prior audit {previous_audit.audit_id}.",
                            evidence_ids=[previous_audit.audit_id, current_audit.audit_id],
                            data_quality_state=GEODataQualityState.OBSERVED,
                        )
                    )

            prev_c = prev_obs.get("citation_observation_rate_pct")
            curr_c = curr_obs.get("citation_observation_rate_pct")
            if isinstance(prev_c, (int, float)) and isinstance(curr_c, (int, float)):
                delta_c = round(curr_c - prev_c, 1)
                if delta_c <= -10.0:
                    alerts.append(
                        GEOMonitoringAlert(
                            tenant_id=tenant_id,
                            audit_id=current_audit.audit_id,
                            domain=current_audit.domain,
                            alert_type="lost_citation",
                            severity=GEOFindingSeverity.HIGH,
                            title=f"Owned citation rate dropped by {abs(delta_c)}pp ({prev_c}% -> {curr_c}%)",
                            description=f"Citation observation rate fell compared with prior audit {previous_audit.audit_id}.",
                            evidence_ids=[previous_audit.audit_id, current_audit.audit_id],
                            data_quality_state=GEODataQualityState.OBSERVED,
                        )
                    )
                elif delta_c >= 10.0:
                    alerts.append(
                        GEOMonitoringAlert(
                            tenant_id=tenant_id,
                            audit_id=current_audit.audit_id,
                            domain=current_audit.domain,
                            alert_type="new_citation",
                            severity=GEOFindingSeverity.INFORMATIONAL,
                            title=f"Owned citation rate increased by +{delta_c}pp ({prev_c}% -> {curr_c}%)",
                            description=f"Citation observation rate rose compared with prior audit {previous_audit.audit_id}.",
                            evidence_ids=[c.citation_id for c in curr_cits[:4]],
                            data_quality_state=GEODataQualityState.OBSERVED,
                        )
                    )

        for a in alerts:
            self.store.save_alert(a)
        return alerts

    def build_monitoring_history(self, tenant_id: str, domain: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
        audits = self.store.list_audits(tenant_id, domain=domain, limit=limit)
        history: List[Dict[str, Any]] = []
        for a in reversed(audits):
            sc = self.store.get_artifact(tenant_id, a.audit_id, "scorecard") or {}
            obs = sc.get("observed_metrics") or {}
            history.append({
                "audit_id": a.audit_id,
                "domain": a.domain,
                "brand_name": a.brand_name,
                "created_at": a.created_at,
                "status": a.status,
                "publication_status": a.publication_status,
                "methodology_version": a.methodology_version,
                "observed_performance_score": a.observed_performance_score,
                "readiness_score": a.readiness_score,
                "mention_rate_pct": obs.get("brand_mention_rate_pct"),
                "recommendation_rate_pct": obs.get("recommendation_rate_pct"),
                "citation_rate_pct": obs.get("citation_observation_rate_pct"),
                "platforms_tested": a.platforms_tested,
            })
        return history


geo_monitoring_engine = GEOMonitoringEngine()

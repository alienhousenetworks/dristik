"""Phase 10.6: Enterprise Governance Dashboard.

Computes 10 executive-level KPIs for website health and engineering progress:
1. Open findings by severity
2. Remediation completion rate (%)
3. Average resolution time (days)
4. Recurring defects count (>= 3 audits)
5. Unverified fixes count
6. Audit coverage percentage (%)
7. Historical discipline scores
8. Data source availability
9. Monitoring schedule status
10. Team workload (estimated remediation hours)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.monitoring.models import (
    GovernanceDashboardReport,
    MonitoringScheduleConfig,
    _utcnow,
)


class EnterpriseGovernanceDashboard:
    """Aggregates multi-source telemetry into an executive governance scorecard."""

    def generate_report(
        self,
        domain: str,
        findings: list[dict[str, Any]],
        remediation_tasks: list[dict[str, Any]],
        recurring_defects_count: int = 0,
        historical_scores: Optional[dict[str, float]] = None,
        crawled_urls_count: int = 0,
        total_sitemap_urls_count: int = 0,
        data_source_availability: Optional[dict[str, bool]] = None,
        schedules: Optional[list[MonitoringScheduleConfig]] = None,
    ) -> GovernanceDashboardReport:
        # 1. Open findings by severity & 10. Team workload hours
        open_by_sev: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        total_workload_hours: float = 0.0

        for f in findings:
            status = str(f.get("status", "OPEN")).upper()
            if status not in ("VERIFIED_FIXED", "RESOLVED", "CLOSED"):
                sev = str(f.get("severity", "MEDIUM")).upper()
                open_by_sev[sev] = open_by_sev.get(sev, 0) + 1
                # Effort hours estimate
                effort_hrs = float(f.get("estimated_effort_hours", f.get("effort_hours", 2.0)))
                total_workload_hours += effort_hrs

        # 2. Remediation completion rate
        total_tasks = len(remediation_tasks)
        completed_tasks = 0
        unverified_count = 0
        resolution_durations: list[float] = []

        now = _utcnow()
        for task in remediation_tasks:
            t_status = str(task.get("status", "OPEN")).upper()
            if t_status in ("VERIFIED_FIXED", "RESOLVED"):
                completed_tasks += 1
                created_str = task.get("created_at")
                resolved_str = task.get("resolved_at")
                if created_str and resolved_str:
                    try:
                        c_dt = datetime.fromisoformat(created_str)
                        r_dt = datetime.fromisoformat(resolved_str)
                        resolution_durations.append((r_dt - c_dt).total_seconds() / 86400.0)
                    except Exception:
                        pass
            elif t_status in ("PATCH_READY", "DEPLOYED", "VERIFICATION_PENDING"):
                unverified_count += 1

        completion_rate = (completed_tasks / float(total_tasks) * 100.0) if total_tasks > 0 else 100.0
        avg_res_days = (
            sum(resolution_durations) / float(len(resolution_durations)) if resolution_durations else 0.0
        )

        # 6. Audit coverage percentage
        if total_sitemap_urls_count > 0:
            coverage_pct = min(100.0, (crawled_urls_count / float(total_sitemap_urls_count)) * 100.0)
        else:
            coverage_pct = 100.0 if crawled_urls_count > 0 else 0.0

        # 8. Data source availability defaults
        ds_avail = dict(data_source_availability or {
            "CrawlEngine": True,
            "LighthouseRunner": True,
            "GoogleSearchConsole": True,
            "AIEvaluationEngine": True,
        })

        # 9. Monitoring status
        mon_status: dict[str, str] = {}
        for s in schedules or []:
            st = "DUE" if (s.next_run_at and now >= s.next_run_at) else ("ACTIVE" if s.enabled else "PAUSED")
            mon_status[s.monitoring_type.value] = st

        return GovernanceDashboardReport(
            domain=domain,
            open_findings_by_severity=open_by_sev,
            remediation_completion_rate=round(completion_rate, 2),
            average_resolution_time_days=round(avg_res_days, 2),
            recurring_defects_count=recurring_defects_count,
            unverified_fixes_count=unverified_count,
            audit_coverage_pct=round(coverage_pct, 2),
            historical_scores=dict(historical_scores or {}),
            data_source_availability=ds_avail,
            monitoring_status=mon_status,
            team_workload_hours=round(total_workload_hours, 1),
            calculated_at=_utcnow(),
        )

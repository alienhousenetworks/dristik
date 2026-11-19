"""Phase 10: Master Continuous Monitoring Engine.

Orchestrates all monitoring subsystems:
- Config & scheduling (Phase 10.1)
- Website change detection (Phase 10.2)
- Finding lifecycle monitoring (Phase 10.3)
- Historical intelligence & trendlines (Phase 10.4)
- Anomaly & regression alerting (Phase 10.5)
- Enterprise governance dashboard (Phase 10.6)
"""
from __future__ import annotations

from typing import Any, Optional

from app.monitoring.alert_engine import MonitoringAlertEngine
from app.monitoring.change_detector import WebsiteChangeDetector
from app.monitoring.config_manager import MonitoringConfigManager
from app.monitoring.governance_dashboard import EnterpriseGovernanceDashboard
from app.monitoring.historical_intelligence import HistoricalIntelligenceEngine
from app.monitoring.lifecycle_monitor import FindingLifecycleMonitor
from app.monitoring.models import (
    FindingLifecycleDiff,
    GovernanceDashboardReport,
    HistoricalIntelligenceReport,
    MonitoringAlert,
    WebsiteChangeReport,
)


class ContinuousMonitoringEngine:
    """Master engine orchestrating continuous monitoring, change detection, and governance."""

    def __init__(self, domain: str):
        self.domain = domain
        self.config_manager = MonitoringConfigManager(domain)
        self.change_detector = WebsiteChangeDetector()
        self.lifecycle_monitor = FindingLifecycleMonitor()
        self.historical_engine = HistoricalIntelligenceEngine()
        self.alert_engine = MonitoringAlertEngine()
        self.governance_dashboard = EnterpriseGovernanceDashboard()

    def run_continuous_monitoring_cycle(
        self,
        baseline_audit_id: str,
        current_audit_id: str,
        baseline_pages: dict[str, dict[str, Any]],
        current_pages: dict[str, dict[str, Any]],
        baseline_findings: list[dict[str, Any]],
        current_findings: list[dict[str, Any]],
        baseline_audit_scores: dict[str, Any],
        current_audit_scores: dict[str, Any],
        remediation_tasks: Optional[list[dict[str, Any]]] = None,
        historical_resolved_ids: Optional[set[str]] = None,
        historical_occurrence_counts: Optional[dict[str, int]] = None,
        baseline_robots_txt: Optional[str] = None,
        current_robots_txt: Optional[str] = None,
        crawl_status_code: int = 200,
        crawl_error: Optional[str] = None,
        total_sitemap_urls: int = 0,
    ) -> dict[str, Any]:
        """Executes a full continuous monitoring evaluation cycle and returns all outputs."""
        rem_tasks = remediation_tasks or []

        # 1. Detect website changes
        change_report: WebsiteChangeReport = self.change_detector.detect_changes(
            domain=self.domain,
            baseline_crawl_id=baseline_audit_id,
            current_crawl_id=current_audit_id,
            baseline_pages=baseline_pages,
            current_pages=current_pages,
            baseline_robots_txt=baseline_robots_txt,
            current_robots_txt=current_robots_txt,
        )

        # 2. Evaluate finding lifecycle
        unresolved_task_ids = [
            t.get("task_id", t.get("finding_id", ""))
            for t in rem_tasks
            if str(t.get("status", "")).upper() not in ("VERIFIED_FIXED", "RESOLVED")
        ]
        lifecycle_diff: FindingLifecycleDiff = self.lifecycle_monitor.evaluate_lifecycle(
            domain=self.domain,
            baseline_audit_id=baseline_audit_id,
            current_audit_id=current_audit_id,
            baseline_findings=baseline_findings,
            current_findings=current_findings,
            historical_resolved_ids=historical_resolved_ids,
            historical_occurrence_counts=historical_occurrence_counts,
            unresolved_remediation_tasks=unresolved_task_ids,
        )

        # 3. Calculate historical intelligence & verified progress
        verified_count = sum(
            1 for t in rem_tasks if str(t.get("status", "")).upper() in ("VERIFIED_FIXED", "RESOLVED")
        )
        verified_progress = (verified_count / float(len(rem_tasks)) * 100.0) if rem_tasks else 100.0

        historical_report: HistoricalIntelligenceReport = self.historical_engine.compare_audits(
            domain=self.domain,
            baseline_audit=baseline_audit_scores,
            current_audit=current_audit_scores,
            verified_remediation_progress=verified_progress,
        )

        # 4. Trigger monitoring alerts
        change_alerts: list[MonitoringAlert] = self.alert_engine.evaluate_change_report(
            domain=self.domain,
            change_report=change_report,
            crawl_status_code=crawl_status_code,
            crawl_error=crawl_error,
        )
        history_alerts: list[MonitoringAlert] = self.alert_engine.evaluate_historical_report(
            domain=self.domain,
            historical_report=historical_report,
        )
        all_alerts = change_alerts + history_alerts

        # 5. Generate governance dashboard
        hist_scores = {
            "seo_score": float(current_audit_scores.get("seo_score", 0.0)),
            "geo_score": float(current_audit_scores.get("geo_score", 0.0)),
            "aeo_score": float(current_audit_scores.get("aeo_score", 0.0)),
            "cro_score": float(current_audit_scores.get("cro_score", 0.0)),
            "tech_score": float(current_audit_scores.get("tech_score", 0.0)),
        }
        governance_report: GovernanceDashboardReport = self.governance_dashboard.generate_report(
            domain=self.domain,
            findings=current_findings,
            remediation_tasks=rem_tasks,
            recurring_defects_count=len(lifecycle_diff.recurring_findings),
            historical_scores=hist_scores,
            crawled_urls_count=len(current_pages),
            total_sitemap_urls_count=total_sitemap_urls or len(current_pages),
            schedules=self.config_manager.list_schedules(),
        )

        return {
            "domain": self.domain,
            "change_report": change_report,
            "lifecycle_diff": lifecycle_diff,
            "historical_report": historical_report,
            "alerts": all_alerts,
            "governance_report": governance_report,
        }

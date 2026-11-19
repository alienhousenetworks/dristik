"""Phase 10.5: Monitoring Alert Engine.

Evaluates monitoring anomalies across 9 mission-critical operational conditions:
- Critical crawl failures
- Sudden indexing drops
- Major broken link spikes
- Performance degradations
- Schema regressions
- AI visibility drops
- Citation losses
- Conversion deteriorations
- Competitor displacements
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from app.monitoring.models import (
    AlertSeverity,
    AlertType,
    HistoricalIntelligenceReport,
    MonitoringAlert,
    WebsiteChangeReport,
    WebsiteChangeType,
    _utcnow,
)


class MonitoringAlertEngine:
    """Evaluates change signals and triggers prioritized, actionable operational alerts."""

    def __init__(
        self,
        indexing_drop_threshold: float = 0.15,
        broken_link_threshold: int = 5,
        perf_degradation_threshold: float = 0.30,
        score_drop_threshold: float = 15.0,
    ):
        self.indexing_drop_threshold = indexing_drop_threshold
        self.broken_link_threshold = broken_link_threshold
        self.perf_degradation_threshold = perf_degradation_threshold
        self.score_drop_threshold = score_drop_threshold

    def evaluate_change_report(
        self,
        domain: str,
        change_report: WebsiteChangeReport,
        crawl_status_code: int = 200,
        crawl_error: Optional[str] = None,
    ) -> list[MonitoringAlert]:
        alerts: list[MonitoringAlert] = []

        # 1. Critical crawl failure
        if crawl_status_code >= 500 or crawl_error is not None:
            alerts.append(
                MonitoringAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:10]}",
                    alert_type=AlertType.CRITICAL_CRAWL_FAILURE,
                    severity=AlertSeverity.CRITICAL,
                    domain=domain,
                    title="Critical Crawl Failure Detected",
                    message=f"Crawl failed with status {crawl_status_code}: {crawl_error or 'Server unavailable'}.",
                    metric_value=float(crawl_status_code),
                    threshold=500.0,
                    triggered_at=_utcnow(),
                )
            )

        # 2. Sudden indexing drop (deleted pages or noindex)
        noindex_pages = [
            p.url
            for p in change_report.modified_pages
            if WebsiteChangeType.CHANGED_ROBOTS_DIRECTIVES in p.change_types
            and "noindex" in str(p.after_snippet.get("robots_directives", "")).lower()
        ]
        total = max(change_report.total_pages_scanned, 1)
        drop_rate = len(change_report.deleted_pages) / float(total)

        if drop_rate >= self.indexing_drop_threshold or len(noindex_pages) > 0:
            affected = change_report.deleted_pages[:10] + noindex_pages[:10]
            alerts.append(
                MonitoringAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:10]}",
                    alert_type=AlertType.SUDDEN_INDEXING_DROP,
                    severity=AlertSeverity.CRITICAL,
                    domain=domain,
                    title="Sudden Indexing Drop / Noindex Directive Injected",
                    message=(
                        f"{len(change_report.deleted_pages)} pages disappeared ({drop_rate*100:.1f}%) "
                        f"and {len(noindex_pages)} pages received noindex directives."
                    ),
                    metric_value=round(drop_rate * 100, 2),
                    threshold=round(self.indexing_drop_threshold * 100, 2),
                    affected_urls=affected,
                    triggered_at=_utcnow(),
                )
            )

        # 3. Major broken links
        broken_pages = [
            p.url for p in change_report.modified_pages if WebsiteChangeType.BROKEN_LINKS in p.change_types
        ]
        if len(broken_pages) >= self.broken_link_threshold:
            alerts.append(
                MonitoringAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:10]}",
                    alert_type=AlertType.MAJOR_BROKEN_LINKS,
                    severity=AlertSeverity.WARNING,
                    domain=domain,
                    title="Spike in Broken Links Detected",
                    message=f"{len(broken_pages)} pages contain newly broken internal/external links.",
                    metric_value=float(len(broken_pages)),
                    threshold=float(self.broken_link_threshold),
                    affected_urls=broken_pages[:15],
                    triggered_at=_utcnow(),
                )
            )

        # 4. Performance regressions
        perf_pages = [
            p.url for p in change_report.modified_pages if WebsiteChangeType.PERFORMANCE_REGRESSIONS in p.change_types
        ]
        if perf_pages:
            alerts.append(
                MonitoringAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:10]}",
                    alert_type=AlertType.PERFORMANCE_DEGRADATION,
                    severity=AlertSeverity.WARNING,
                    domain=domain,
                    title="Performance Regression Detected",
                    message=f"{len(perf_pages)} pages regressed in TTFB or total load time by >= {self.perf_degradation_threshold*100:.0f}%.",
                    metric_value=float(len(perf_pages)),
                    threshold=1.0,
                    affected_urls=perf_pages[:10],
                    triggered_at=_utcnow(),
                )
            )

        # 5. Schema regression
        schema_pages = [
            p.url for p in change_report.modified_pages if WebsiteChangeType.CHANGED_SCHEMA in p.change_types
        ]
        if schema_pages:
            alerts.append(
                MonitoringAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:10]}",
                    alert_type=AlertType.SCHEMA_REGRESSION,
                    severity=AlertSeverity.INFO,
                    domain=domain,
                    title="Structured Data Schema Regressions Detected",
                    message=f"Schema modifications or deletions detected on {len(schema_pages)} pages.",
                    metric_value=float(len(schema_pages)),
                    threshold=1.0,
                    affected_urls=schema_pages[:10],
                    triggered_at=_utcnow(),
                )
            )

        return alerts

    def evaluate_historical_report(
        self,
        domain: str,
        historical_report: HistoricalIntelligenceReport,
    ) -> list[MonitoringAlert]:
        alerts: list[MonitoringAlert] = []

        # 6. AI visibility drop
        if historical_report.geo_delta <= -self.score_drop_threshold:
            alerts.append(
                MonitoringAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:10]}",
                    alert_type=AlertType.AI_VISIBILITY_DROP,
                    severity=AlertSeverity.CRITICAL,
                    domain=domain,
                    title="AI Search Visibility / GEO Score Decline",
                    message=f"GEO visibility dropped by {abs(historical_report.geo_delta):.1f} points.",
                    metric_value=historical_report.geo_delta,
                    threshold=-self.score_drop_threshold,
                    triggered_at=_utcnow(),
                )
            )

        # 7. Citation loss
        if historical_report.citation_delta <= -self.score_drop_threshold:
            alerts.append(
                MonitoringAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:10]}",
                    alert_type=AlertType.CITATION_LOSS,
                    severity=AlertSeverity.WARNING,
                    domain=domain,
                    title="Authoritative Citation Loss in AI Answers",
                    message=f"Citation authority score dropped by {abs(historical_report.citation_delta):.1f} points.",
                    metric_value=historical_report.citation_delta,
                    threshold=-self.score_drop_threshold,
                    triggered_at=_utcnow(),
                )
            )

        # 8. Conversion deterioration
        if historical_report.cro_delta <= -self.score_drop_threshold:
            alerts.append(
                MonitoringAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:10]}",
                    alert_type=AlertType.CONVERSION_DETERIORATION,
                    severity=AlertSeverity.CRITICAL,
                    domain=domain,
                    title="Conversion Friction / CRO Score Deterioration",
                    message=f"CRO score deteriorated by {abs(historical_report.cro_delta):.1f} points.",
                    metric_value=historical_report.cro_delta,
                    threshold=-self.score_drop_threshold,
                    triggered_at=_utcnow(),
                )
            )

        # 9. Competitor displacement
        if historical_report.competitor_displacement_delta <= -self.score_drop_threshold:
            alerts.append(
                MonitoringAlert(
                    alert_id=f"alt_{uuid.uuid4().hex[:10]}",
                    alert_type=AlertType.COMPETITOR_DISPLACEMENT,
                    severity=AlertSeverity.WARNING,
                    domain=domain,
                    title="Competitor Displaced Target Domain",
                    message=f"Competitor displacement index dropped by {abs(historical_report.competitor_displacement_delta):.1f} points.",
                    metric_value=historical_report.competitor_displacement_delta,
                    threshold=-self.score_drop_threshold,
                    triggered_at=_utcnow(),
                )
            )

        return alerts

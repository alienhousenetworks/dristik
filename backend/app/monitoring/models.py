"""Data models for Phase 10 Continuous Monitoring Intelligence."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MonitoringType(str, Enum):
    CRITICAL_INFRASTRUCTURE = "CRITICAL_INFRASTRUCTURE"
    SITEMAP_INDEXABILITY = "SITEMAP_INDEXABILITY"
    TECHNICAL_CRAWL = "TECHNICAL_CRAWL"
    SEO_CONTENT = "SEO_CONTENT"
    GEO_BENCHMARKING = "GEO_BENCHMARKING"
    AEO_QUESTION_BENCHMARKING = "AEO_QUESTION_BENCHMARKING"
    CRO_ANALYTICS = "CRO_ANALYTICS"
    COMPETITOR_BENCHMARKING = "COMPETITOR_BENCHMARKING"
    FULL_ENTERPRISE_AUDIT = "FULL_ENTERPRISE_AUDIT"


class MonitoringFrequency(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    EVENT_DRIVEN = "EVENT_DRIVEN"


@dataclass
class MonitoringScheduleConfig:
    monitoring_type: MonitoringType
    frequency: MonitoringFrequency
    rate_limit_rps: float = 2.0
    cost_budget_usd: float = 50.0
    provider_call_limit: int = 1000
    enabled: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "monitoring_type": self.monitoring_type.value,
            "frequency": self.frequency.value,
            "rate_limit_rps": self.rate_limit_rps,
            "cost_budget_usd": self.cost_budget_usd,
            "provider_call_limit": self.provider_call_limit,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "tags": list(self.tags),
        }


class WebsiteChangeType(str, Enum):
    NEW_PAGES = "NEW_PAGES"
    DELETED_PAGES = "DELETED_PAGES"
    CHANGED_METADATA = "CHANGED_METADATA"
    CHANGED_HEADINGS = "CHANGED_HEADINGS"
    CHANGED_CONTENT = "CHANGED_CONTENT"
    CHANGED_SCHEMA = "CHANGED_SCHEMA"
    BROKEN_LINKS = "BROKEN_LINKS"
    REDIRECT_CHANGES = "REDIRECT_CHANGES"
    NEW_SCRIPTS = "NEW_SCRIPTS"
    CHANGED_PAGE_TEMPLATES = "CHANGED_PAGE_TEMPLATES"
    PERFORMANCE_REGRESSIONS = "PERFORMANCE_REGRESSIONS"
    CHANGED_ROBOTS_DIRECTIVES = "CHANGED_ROBOTS_DIRECTIVES"


@dataclass
class PageChangeRecord:
    url: str
    change_types: list[WebsiteChangeType] = field(default_factory=list)
    before_snippet: dict[str, Any] = field(default_factory=dict)
    after_snippet: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=_utcnow)
    severity: str = "INFO"  # INFO, WARNING, CRITICAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "change_types": [ct.value for ct in self.change_types],
            "before_snippet": self.before_snippet,
            "after_snippet": self.after_snippet,
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity,
        }


@dataclass
class WebsiteChangeReport:
    domain: str
    baseline_crawl_id: str
    current_crawl_id: str
    total_pages_scanned: int = 0
    new_pages: list[str] = field(default_factory=list)
    deleted_pages: list[str] = field(default_factory=list)
    modified_pages: list[PageChangeRecord] = field(default_factory=list)
    changes_by_type: dict[str, int] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "baseline_crawl_id": self.baseline_crawl_id,
            "current_crawl_id": self.current_crawl_id,
            "total_pages_scanned": self.total_pages_scanned,
            "new_pages": self.new_pages,
            "deleted_pages": self.deleted_pages,
            "modified_pages": [p.to_dict() for p in self.modified_pages],
            "changes_by_type": self.changes_by_type,
            "generated_at": self.generated_at.isoformat(),
        }


class FindingLifecycleState(str, Enum):
    NEW = "NEW"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"
    RECURRING = "RECURRING"
    SEVERITY_CHANGED = "SEVERITY_CHANGED"
    AFFECTED_PAGES_CHANGED = "AFFECTED_PAGES_CHANGED"


@dataclass
class FindingLifecycleRecord:
    finding_id: str
    state: FindingLifecycleState
    previous_severity: Optional[str] = None
    current_severity: Optional[str] = None
    previous_urls: list[str] = field(default_factory=list)
    current_urls: list[str] = field(default_factory=list)
    audit_occurrence_count: int = 1
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "state": self.state.value,
            "previous_severity": self.previous_severity,
            "current_severity": self.current_severity,
            "previous_urls": self.previous_urls,
            "current_urls": self.current_urls,
            "audit_occurrence_count": self.audit_occurrence_count,
            "details": self.details,
        }


@dataclass
class FindingLifecycleDiff:
    domain: str
    baseline_audit_id: str
    current_audit_id: str
    new_findings: list[FindingLifecycleRecord] = field(default_factory=list)
    resolved_findings: list[FindingLifecycleRecord] = field(default_factory=list)
    reopened_findings: list[FindingLifecycleRecord] = field(default_factory=list)
    recurring_findings: list[FindingLifecycleRecord] = field(default_factory=list)
    severity_changes: list[FindingLifecycleRecord] = field(default_factory=list)
    affected_page_changes: list[FindingLifecycleRecord] = field(default_factory=list)
    unresolved_remediation_tasks: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "baseline_audit_id": self.baseline_audit_id,
            "current_audit_id": self.current_audit_id,
            "new_findings": [f.to_dict() for f in self.new_findings],
            "resolved_findings": [f.to_dict() for f in self.resolved_findings],
            "reopened_findings": [f.to_dict() for f in self.reopened_findings],
            "recurring_findings": [f.to_dict() for f in self.recurring_findings],
            "severity_changes": [f.to_dict() for f in self.severity_changes],
            "affected_page_changes": [f.to_dict() for f in self.affected_page_changes],
            "unresolved_remediation_tasks": self.unresolved_remediation_tasks,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class HistoricalDisciplineDelta:
    metric_name: str
    baseline_score: float
    current_score: float
    delta: float
    crawl_coverage_delta: float = 0.0  # percentage difference in crawled sample
    scoring_methodology_changed: bool = False
    sample_size_baseline: int = 0
    sample_size_current: int = 0
    is_real_performance_change: bool = True
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "baseline_score": self.baseline_score,
            "current_score": self.current_score,
            "delta": self.delta,
            "crawl_coverage_delta": self.crawl_coverage_delta,
            "scoring_methodology_changed": self.scoring_methodology_changed,
            "sample_size_baseline": self.sample_size_baseline,
            "sample_size_current": self.sample_size_current,
            "is_real_performance_change": self.is_real_performance_change,
            "explanation": self.explanation,
        }


@dataclass
class HistoricalIntelligenceReport:
    domain: str
    audit_id_baseline: str
    audit_id_current: str
    discipline_deltas: dict[str, HistoricalDisciplineDelta] = field(default_factory=dict)
    seo_delta: float = 0.0
    geo_delta: float = 0.0
    aeo_delta: float = 0.0
    cro_delta: float = 0.0
    tech_delta: float = 0.0
    competitor_displacement_delta: float = 0.0
    citation_delta: float = 0.0
    content_freshness_score: float = 100.0
    verified_remediation_progress: float = 0.0  # percentage of backlog verified fixed
    observation_timestamp: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "audit_id_baseline": self.audit_id_baseline,
            "audit_id_current": self.audit_id_current,
            "discipline_deltas": {k: v.to_dict() for k, v in self.discipline_deltas.items()},
            "seo_delta": self.seo_delta,
            "geo_delta": self.geo_delta,
            "aeo_delta": self.aeo_delta,
            "cro_delta": self.cro_delta,
            "tech_delta": self.tech_delta,
            "competitor_displacement_delta": self.competitor_displacement_delta,
            "citation_delta": self.citation_delta,
            "content_freshness_score": self.content_freshness_score,
            "verified_remediation_progress": self.verified_remediation_progress,
            "observation_timestamp": self.observation_timestamp.isoformat(),
        }


class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class AlertType(str, Enum):
    CRITICAL_CRAWL_FAILURE = "CRITICAL_CRAWL_FAILURE"
    SUDDEN_INDEXING_DROP = "SUDDEN_INDEXING_DROP"
    MAJOR_BROKEN_LINKS = "MAJOR_BROKEN_LINKS"
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
    SCHEMA_REGRESSION = "SCHEMA_REGRESSION"
    AI_VISIBILITY_DROP = "AI_VISIBILITY_DROP"
    CITATION_LOSS = "CITATION_LOSS"
    CONVERSION_DETERIORATION = "CONVERSION_DETERIORATION"
    COMPETITOR_DISPLACEMENT = "COMPETITOR_DISPLACEMENT"


@dataclass
class MonitoringAlert:
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    domain: str
    title: str
    message: str
    metric_value: float = 0.0
    threshold: float = 0.0
    affected_urls: list[str] = field(default_factory=list)
    triggered_at: datetime = field(default_factory=_utcnow)
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "domain": self.domain,
            "title": self.title,
            "message": self.message,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "affected_urls": self.affected_urls,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged": self.acknowledged,
        }


@dataclass
class GovernanceDashboardReport:
    domain: str
    open_findings_by_severity: dict[str, int] = field(default_factory=dict)
    remediation_completion_rate: float = 0.0  # percentage 0-100
    average_resolution_time_days: float = 0.0
    recurring_defects_count: int = 0
    unverified_fixes_count: int = 0
    audit_coverage_pct: float = 0.0
    historical_scores: dict[str, float] = field(default_factory=dict)
    data_source_availability: dict[str, bool] = field(default_factory=dict)
    monitoring_status: dict[str, str] = field(default_factory=dict)
    team_workload_hours: float = 0.0
    calculated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "open_findings_by_severity": self.open_findings_by_severity,
            "remediation_completion_rate": self.remediation_completion_rate,
            "average_resolution_time_days": self.average_resolution_time_days,
            "recurring_defects_count": self.recurring_defects_count,
            "unverified_fixes_count": self.unverified_fixes_count,
            "audit_coverage_pct": self.audit_coverage_pct,
            "historical_scores": self.historical_scores,
            "data_source_availability": self.data_source_availability,
            "monitoring_status": self.monitoring_status,
            "team_workload_hours": self.team_workload_hours,
            "calculated_at": self.calculated_at.isoformat(),
        }

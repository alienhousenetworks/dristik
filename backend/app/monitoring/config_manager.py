"""Phase 10.1: Monitoring Configuration Manager."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.monitoring.models import (
    MonitoringFrequency,
    MonitoringScheduleConfig,
    MonitoringType,
    _utcnow,
)


FREQUENCY_INTERVALS: dict[MonitoringFrequency, timedelta] = {
    MonitoringFrequency.DAILY: timedelta(days=1),
    MonitoringFrequency.WEEKLY: timedelta(days=7),
    MonitoringFrequency.MONTHLY: timedelta(days=30),
    MonitoringFrequency.QUARTERLY: timedelta(days=90),
    MonitoringFrequency.EVENT_DRIVEN: timedelta(seconds=0),
}

DEFAULT_SCHEDULES: dict[MonitoringType, MonitoringFrequency] = {
    MonitoringType.CRITICAL_INFRASTRUCTURE: MonitoringFrequency.DAILY,
    MonitoringType.SITEMAP_INDEXABILITY: MonitoringFrequency.DAILY,
    MonitoringType.TECHNICAL_CRAWL: MonitoringFrequency.WEEKLY,
    MonitoringType.SEO_CONTENT: MonitoringFrequency.WEEKLY,
    MonitoringType.GEO_BENCHMARKING: MonitoringFrequency.WEEKLY,
    MonitoringType.AEO_QUESTION_BENCHMARKING: MonitoringFrequency.WEEKLY,
    MonitoringType.CRO_ANALYTICS: MonitoringFrequency.DAILY,
    MonitoringType.COMPETITOR_BENCHMARKING: MonitoringFrequency.MONTHLY,
    MonitoringType.FULL_ENTERPRISE_AUDIT: MonitoringFrequency.MONTHLY,
}


class MonitoringConfigManager:
    """Manages monitoring schedules, cost/provider boundaries, and dispatch timing."""

    def __init__(self, domain: str):
        self.domain = domain
        self._schedules: dict[MonitoringType, MonitoringScheduleConfig] = {}
        self._init_defaults()

    def _init_defaults(self) -> None:
        """Initialize all 9 monitoring types with standard defaults."""
        now = _utcnow()
        for m_type, freq in DEFAULT_SCHEDULES.items():
            self._schedules[m_type] = MonitoringScheduleConfig(
                monitoring_type=m_type,
                frequency=freq,
                rate_limit_rps=2.0 if m_type != MonitoringType.CRITICAL_INFRASTRUCTURE else 10.0,
                cost_budget_usd=100.0 if m_type == MonitoringType.FULL_ENTERPRISE_AUDIT else 25.0,
                provider_call_limit=5000 if m_type == MonitoringType.FULL_ENTERPRISE_AUDIT else 1000,
                enabled=True,
                last_run_at=None,
                next_run_at=now,
                tags=["default", m_type.value.lower()],
            )

    def configure_schedule(
        self,
        monitoring_type: MonitoringType,
        frequency: MonitoringFrequency,
        rate_limit_rps: Optional[float] = None,
        cost_budget_usd: Optional[float] = None,
        provider_call_limit: Optional[int] = None,
        enabled: Optional[bool] = None,
        tags: Optional[list[str]] = None,
    ) -> MonitoringScheduleConfig:
        """Update or create a monitoring configuration with bounds validation."""
        if rate_limit_rps is not None and rate_limit_rps <= 0:
            raise ValueError("Rate limit rps must be strictly positive.")
        if cost_budget_usd is not None and cost_budget_usd < 0:
            raise ValueError("Cost budget cannot be negative.")
        if provider_call_limit is not None and provider_call_limit <= 0:
            raise ValueError("Provider call limit must be strictly positive.")

        config = self._schedules.get(monitoring_type)
        if not config:
            config = MonitoringScheduleConfig(
                monitoring_type=monitoring_type,
                frequency=frequency,
            )
            self._schedules[monitoring_type] = config

        config.frequency = frequency
        if rate_limit_rps is not None:
            config.rate_limit_rps = rate_limit_rps
        if cost_budget_usd is not None:
            config.cost_budget_usd = cost_budget_usd
        if provider_call_limit is not None:
            config.provider_call_limit = provider_call_limit
        if enabled is not None:
            config.enabled = enabled
        if tags is not None:
            config.tags = tags

        # Recalculate next run time if not event driven
        if config.last_run_at and frequency != MonitoringFrequency.EVENT_DRIVEN:
            config.next_run_at = config.last_run_at + FREQUENCY_INTERVALS[frequency]
        elif frequency == MonitoringFrequency.EVENT_DRIVEN:
            config.next_run_at = None

        return config

    def get_schedule(self, monitoring_type: MonitoringType) -> Optional[MonitoringScheduleConfig]:
        return self._schedules.get(monitoring_type)

    def list_schedules(self) -> list[MonitoringScheduleConfig]:
        return list(self._schedules.values())

    def is_due(self, monitoring_type: MonitoringType, now: Optional[datetime] = None) -> bool:
        """Check if a specific monitoring type is due to run."""
        config = self._schedules.get(monitoring_type)
        if not config or not config.enabled:
            return False
        if config.frequency == MonitoringFrequency.EVENT_DRIVEN:
            return True
        current_time = now or _utcnow()
        if config.next_run_at is None:
            return True
        return current_time >= config.next_run_at

    def record_run(self, monitoring_type: MonitoringType, run_time: Optional[datetime] = None) -> None:
        """Record completion of a run and compute the next scheduled time."""
        config = self._schedules.get(monitoring_type)
        if not config:
            return
        executed_at = run_time or _utcnow()
        config.last_run_at = executed_at
        if config.frequency != MonitoringFrequency.EVENT_DRIVEN:
            interval = FREQUENCY_INTERVALS[config.frequency]
            config.next_run_at = executed_at + interval
        else:
            config.next_run_at = None

    def get_due_schedules(self, now: Optional[datetime] = None) -> list[MonitoringType]:
        """Return all enabled monitoring types that are currently due."""
        current_time = now or _utcnow()
        return [m_type for m_type in self._schedules if self.is_due(m_type, current_time)]

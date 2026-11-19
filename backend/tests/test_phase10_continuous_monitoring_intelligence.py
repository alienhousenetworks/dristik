"""Tests for Phase 10 — Continuous Monitoring Intelligence."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from app.monitoring import (
    AlertSeverity,
    AlertType,
    ContinuousMonitoringEngine,
    EnterpriseGovernanceDashboard,
    FindingLifecycleDiff,
    FindingLifecycleMonitor,
    FindingLifecycleState,
    GovernanceDashboardReport,
    HistoricalIntelligenceEngine,
    HistoricalIntelligenceReport,
    MonitoringAlert,
    MonitoringAlertEngine,
    MonitoringConfigManager,
    MonitoringFrequency,
    MonitoringScheduleConfig,
    MonitoringType,
    RecurringAuditStore,
    WebsiteChangeDetector,
    WebsiteChangeReport,
    WebsiteChangeType,
)


def test_phase10_1_monitoring_configuration():
    """Verify monitoring schedule configuration across 9 types and provider/cost bounds."""
    mgr = MonitoringConfigManager(domain="example.com")
    schedules = mgr.list_schedules()
    assert len(schedules) == 9

    # Verify defaults
    crit_sched = mgr.get_schedule(MonitoringType.CRITICAL_INFRASTRUCTURE)
    assert crit_sched is not None
    assert crit_sched.frequency == MonitoringFrequency.DAILY
    assert crit_sched.enabled is True

    # Reconfigure schedule with custom bounds
    updated = mgr.configure_schedule(
        monitoring_type=MonitoringType.GEO_BENCHMARKING,
        frequency=MonitoringFrequency.MONTHLY,
        rate_limit_rps=5.0,
        cost_budget_usd=75.0,
        provider_call_limit=2500,
        tags=["enterprise", "ai-visibility"],
    )
    assert updated.frequency == MonitoringFrequency.MONTHLY
    assert updated.rate_limit_rps == 5.0
    assert updated.cost_budget_usd == 75.0
    assert updated.provider_call_limit == 2500
    assert "enterprise" in updated.tags

    # Bounds validation checks
    with pytest.raises(ValueError, match="Rate limit rps must be strictly positive"):
        mgr.configure_schedule(MonitoringType.SEO_CONTENT, MonitoringFrequency.WEEKLY, rate_limit_rps=0)

    with pytest.raises(ValueError, match="Cost budget cannot be negative"):
        mgr.configure_schedule(MonitoringType.SEO_CONTENT, MonitoringFrequency.WEEKLY, cost_budget_usd=-10)

    with pytest.raises(ValueError, match="Provider call limit must be strictly positive"):
        mgr.configure_schedule(MonitoringType.SEO_CONTENT, MonitoringFrequency.WEEKLY, provider_call_limit=-5)

    # Check is_due logic and record_run
    now = datetime.now(timezone.utc)
    assert mgr.is_due(MonitoringType.CRITICAL_INFRASTRUCTURE, now=now) is True

    # Record run and verify next run is computed
    mgr.record_run(MonitoringType.CRITICAL_INFRASTRUCTURE, run_time=now)
    assert mgr.get_schedule(MonitoringType.CRITICAL_INFRASTRUCTURE).last_run_at == now
    assert mgr.is_due(MonitoringType.CRITICAL_INFRASTRUCTURE, now=now) is False
    assert mgr.is_due(MonitoringType.CRITICAL_INFRASTRUCTURE, now=now + timedelta(days=2)) is True


def test_phase10_2_website_change_detection_all_12_types():
    """Verify detection of all 12 types of website changes between crawls."""
    detector = WebsiteChangeDetector(performance_regression_threshold=0.25)

    baseline_pages = {
        "https://example.com/": {
            "metadata": {"title": "Home Old", "description": "Old desc"},
            "headings": {"h1": ["Old Headline"]},
            "content_text": "Original company content text goes here.",
            "schema": [{"@type": "Organization", "name": "Example Corp"}],
            "links": [{"url": "https://example.com/about", "status": 200}],
            "redirect_url": None,
            "status_code": 200,
            "scripts": ["https://example.com/main.js"],
            "template_fingerprint": "tpl_v1",
            "performance": {"ttfb_ms": 100, "load_time_ms": 500, "page_size_kb": 200},
            "robots_directives": ["index", "follow"],
        },
        "https://example.com/deleted-page": {
            "metadata": {"title": "To be deleted"},
            "content_text": "This page will be removed.",
        },
    }

    current_pages = {
        "https://example.com/": {
            "metadata": {"title": "Home New", "description": "New desc"},  # 1. CHANGED_METADATA
            "headings": {"h1": ["New Headline"]},  # 2. CHANGED_HEADINGS
            "content_text": "Brand new updated company content text.",  # 3. CHANGED_CONTENT
            "schema": [{"@type": "Organization", "name": "Example Corp 2.0"}, {"@type": "WebSite"}],  # 4. CHANGED_SCHEMA
            "links": [{"url": "https://example.com/404-link", "status": 404}],  # 5. BROKEN_LINKS
            "redirect_url": "https://example.com/home-new",  # 6. REDIRECT_CHANGES
            "status_code": 301,
            "scripts": ["https://example.com/main.js", "https://tagmanager.google.com/gtm.js"],  # 7. NEW_SCRIPTS
            "template_fingerprint": "tpl_v2",  # 8. CHANGED_PAGE_TEMPLATES
            "performance": {"ttfb_ms": 250, "load_time_ms": 1200, "page_size_kb": 450},  # 9. PERFORMANCE_REGRESSIONS (>25%)
            "robots_directives": ["noindex", "nofollow"],  # 10. CHANGED_ROBOTS_DIRECTIVES
        },
        "https://example.com/new-product": {  # 11. NEW_PAGES
            "metadata": {"title": "New Product"},
            "content_text": "Freshly launched product.",
        },
    }
    # 12. DELETED_PAGES: "https://example.com/deleted-page" missing in current

    report: WebsiteChangeReport = detector.detect_changes(
        domain="example.com",
        baseline_crawl_id="crawl_001",
        current_crawl_id="crawl_002",
        baseline_pages=baseline_pages,
        current_pages=current_pages,
        baseline_robots_txt="User-agent: *\nAllow: /",
        current_robots_txt="User-agent: *\nDisallow: /admin/",
    )

    assert "https://example.com/new-product" in report.new_pages
    assert "https://example.com/deleted-page" in report.deleted_pages
    assert len(report.modified_pages) == 1

    home_mod = report.modified_pages[0]
    assert home_mod.url == "https://example.com/"
    expected_types = {
        WebsiteChangeType.CHANGED_METADATA,
        WebsiteChangeType.CHANGED_HEADINGS,
        WebsiteChangeType.CHANGED_CONTENT,
        WebsiteChangeType.CHANGED_SCHEMA,
        WebsiteChangeType.BROKEN_LINKS,
        WebsiteChangeType.REDIRECT_CHANGES,
        WebsiteChangeType.NEW_SCRIPTS,
        WebsiteChangeType.CHANGED_PAGE_TEMPLATES,
        WebsiteChangeType.PERFORMANCE_REGRESSIONS,
        WebsiteChangeType.CHANGED_ROBOTS_DIRECTIVES,
    }
    for et in expected_types:
        assert et in home_mod.change_types

    assert report.changes_by_type[WebsiteChangeType.NEW_PAGES.value] == 1
    assert report.changes_by_type[WebsiteChangeType.DELETED_PAGES.value] == 1
    assert report.changes_by_type[WebsiteChangeType.BROKEN_LINKS.value] == 1


def test_phase10_3_finding_lifecycle_monitoring():
    """Verify lifecycle monitoring across new, resolved, reopened, recurring, and severity changes."""
    monitor = FindingLifecycleMonitor(recurring_threshold=3)

    baseline_findings = [
        {"finding_id": "F-001", "severity": "MEDIUM", "affected_urls": ["/page1"]},
        {"finding_id": "F-002", "severity": "HIGH", "affected_urls": ["/page2"]},
        {"finding_id": "F-003", "severity": "LOW", "affected_urls": ["/page3"]},
    ]

    current_findings = [
        # F-001 persisted, but severity escalated from MEDIUM to CRITICAL and URL scope expanded
        {"finding_id": "F-001", "severity": "CRITICAL", "affected_urls": ["/page1", "/page1b"]},
        # F-002 is absent (resolved)
        # F-003 persisted with count 3 (recurring)
        {"finding_id": "F-003", "severity": "LOW", "affected_urls": ["/page3"]},
        # F-004 is new
        {"finding_id": "F-004", "severity": "HIGH", "affected_urls": ["/page4"]},
        # F-005 was previously resolved but re-detected (reopened)
        {"finding_id": "F-005", "severity": "MEDIUM", "affected_urls": ["/page5"]},
    ]

    hist_resolved = {"F-005"}
    hist_counts = {"F-001": 1, "F-002": 1, "F-003": 2, "F-005": 1}

    diff: FindingLifecycleDiff = monitor.evaluate_lifecycle(
        domain="example.com",
        baseline_audit_id="audit_prev",
        current_audit_id="audit_curr",
        baseline_findings=baseline_findings,
        current_findings=current_findings,
        historical_resolved_ids=hist_resolved,
        historical_occurrence_counts=hist_counts,
        unresolved_remediation_tasks=["task_f001_rem"],
    )

    # 1. New findings
    assert any(f.finding_id == "F-004" and f.state == FindingLifecycleState.NEW for f in diff.new_findings)

    # 2. Reopened findings
    assert any(f.finding_id == "F-005" and f.state == FindingLifecycleState.REOPENED for f in diff.reopened_findings)

    # 3. Resolved findings
    assert any(f.finding_id == "F-002" and f.state == FindingLifecycleState.RESOLVED for f in diff.resolved_findings)

    # 4. Recurring findings (F-003 count reached 3)
    assert any(f.finding_id == "F-003" and f.state == FindingLifecycleState.RECURRING for f in diff.recurring_findings)

    # 5. Severity changes (F-001 MEDIUM -> CRITICAL)
    sev_change = next(f for f in diff.severity_changes if f.finding_id == "F-001")
    assert sev_change.previous_severity == "MEDIUM"
    assert sev_change.current_severity == "CRITICAL"

    # 6. Affected page changes (F-001 1 page -> 2 pages)
    assert any(f.finding_id == "F-001" and f.state == FindingLifecycleState.AFFECTED_PAGES_CHANGED for f in diff.affected_page_changes)

    # 7. Unresolved remediation tasks
    assert "task_f001_rem" in diff.unresolved_remediation_tasks


def test_phase10_4_historical_intelligence_methodology_guardrail():
    """Verify historical delta computation and coverage/methodology confounding guardrails."""
    engine = HistoricalIntelligenceEngine(coverage_skew_threshold=0.30)

    # Scenario A: Real performance change (consistent crawl coverage & methodology)
    base_audit = {
        "audit_id": "aud_01",
        "sample_size": 100,
        "scoring_methodology_version": "1.0",
        "seo_score": 70.0,
        "geo_score": 60.0,
        "aeo_score": 65.0,
        "cro_score": 75.0,
        "tech_score": 80.0,
        "citations_score": 55.0,
        "competitor_displacement_score": 50.0,
    }
    curr_audit_real = {
        "audit_id": "aud_02",
        "sample_size": 105,  # 5% coverage difference (< 30%)
        "scoring_methodology_version": "1.0",
        "seo_score": 85.0,  # +15
        "geo_score": 70.0,  # +10
        "aeo_score": 72.0,  # +7
        "cro_score": 80.0,  # +5
        "tech_score": 90.0,  # +10
        "citations_score": 68.0,  # +13
        "competitor_displacement_score": 62.0,  # +12
        "content_freshness_score": 95.0,
    }

    report_real: HistoricalIntelligenceReport = engine.compare_audits(
        domain="example.com",
        baseline_audit=base_audit,
        current_audit=curr_audit_real,
        verified_remediation_progress=85.0,
    )
    assert report_real.seo_delta == 15.0
    assert report_real.discipline_deltas["seo_score"].is_real_performance_change is True
    assert report_real.verified_remediation_progress == 85.0

    # Scenario B: Coverage skew (sample increased from 100 to 250, +150% > 30%)
    curr_audit_skewed = dict(curr_audit_real)
    curr_audit_skewed["sample_size"] = 250
    report_skewed = engine.compare_audits("example.com", base_audit, curr_audit_skewed)
    assert report_skewed.discipline_deltas["seo_score"].is_real_performance_change is False
    assert "expanded by 150.0%" in report_skewed.discipline_deltas["seo_score"].explanation

    # Scenario C: Methodology change (v1.0 -> v2.0)
    curr_audit_method = dict(curr_audit_real)
    curr_audit_method["scoring_methodology_version"] = "2.0"
    report_method = engine.compare_audits("example.com", base_audit, curr_audit_method)
    assert report_method.discipline_deltas["seo_score"].is_real_performance_change is False
    assert "Scoring methodology updated" in report_method.discipline_deltas["seo_score"].explanation


def test_phase10_5_alert_engine_all_9_types():
    """Verify automated alerting across all 9 mission-critical operational conditions."""
    alert_engine = MonitoringAlertEngine(
        indexing_drop_threshold=0.15,
        broken_link_threshold=2,
        perf_degradation_threshold=0.25,
        score_drop_threshold=15.0,
    )

    # 1. Critical crawl failure
    c_alerts = alert_engine.evaluate_change_report(
        domain="example.com",
        change_report=WebsiteChangeReport(
            domain="example.com",
            baseline_crawl_id="b1",
            current_crawl_id="c1",
            total_pages_scanned=0,
        ),
        crawl_status_code=503,
        crawl_error="Service Unavailable",
    )
    assert any(a.alert_type == AlertType.CRITICAL_CRAWL_FAILURE and a.severity == AlertSeverity.CRITICAL for a in c_alerts)

    # 2. Sudden indexing drop & 3. Major broken links & 4. Perf degradation & 5. Schema regression
    from app.monitoring.models import PageChangeRecord
    change_rep = WebsiteChangeReport(
        domain="example.com",
        baseline_crawl_id="b1",
        current_crawl_id="c1",
        total_pages_scanned=10,
        deleted_pages=["/p1", "/p2"],  # 20% drop > 15%
        modified_pages=[
            PageChangeRecord(
                url="/p3",
                change_types=[WebsiteChangeType.BROKEN_LINKS],
            ),
            PageChangeRecord(
                url="/p4",
                change_types=[WebsiteChangeType.BROKEN_LINKS],
            ),
            PageChangeRecord(
                url="/p5",
                change_types=[WebsiteChangeType.PERFORMANCE_REGRESSIONS],
            ),
            PageChangeRecord(
                url="/p6",
                change_types=[WebsiteChangeType.CHANGED_SCHEMA],
            ),
        ],
    )
    report_alerts = alert_engine.evaluate_change_report("example.com", change_rep)
    types_found = {a.alert_type for a in report_alerts}
    assert AlertType.SUDDEN_INDEXING_DROP in types_found
    assert AlertType.MAJOR_BROKEN_LINKS in types_found
    assert AlertType.PERFORMANCE_DEGRADATION in types_found
    assert AlertType.SCHEMA_REGRESSION in types_found

    # 6. AI visibility drop, 7. Citation loss, 8. Conversion deterioration, 9. Competitor displacement
    hist_report = HistoricalIntelligenceReport(
        domain="example.com",
        audit_id_baseline="b1",
        audit_id_current="c1",
        geo_delta=-18.0,
        citation_delta=-20.0,
        cro_delta=-22.0,
        competitor_displacement_delta=-16.0,
    )
    hist_alerts = alert_engine.evaluate_historical_report("example.com", hist_report)
    hist_types = {a.alert_type for a in hist_alerts}
    assert AlertType.AI_VISIBILITY_DROP in hist_types
    assert AlertType.CITATION_LOSS in hist_types
    assert AlertType.CONVERSION_DETERIORATION in hist_types
    assert AlertType.COMPETITOR_DISPLACEMENT in hist_types


def test_phase10_6_enterprise_governance_dashboard():
    """Verify executive governance dashboard computing all 10 KPIs."""
    dashboard = EnterpriseGovernanceDashboard()

    findings = [
        {"severity": "CRITICAL", "status": "OPEN", "effort_hours": 5.0},
        {"severity": "CRITICAL", "status": "OPEN", "effort_hours": 4.0},
        {"severity": "HIGH", "status": "OPEN", "effort_hours": 3.0},
        {"severity": "MEDIUM", "status": "VERIFIED_FIXED", "effort_hours": 2.0},
    ]

    remediation_tasks = [
        {
            "task_id": "T1",
            "status": "VERIFIED_FIXED",
            "created_at": "2026-11-10T10:00:00+00:00",
            "resolved_at": "2026-11-12T10:00:00+00:00",  # 2 days
        },
        {
            "task_id": "T2",
            "status": "VERIFIED_FIXED",
            "created_at": "2026-11-10T10:00:00+00:00",
            "resolved_at": "2026-11-14T10:00:00+00:00",  # 4 days
        },
        {
            "task_id": "T3",
            "status": "PATCH_READY",  # unverified fix
        },
        {
            "task_id": "T4",
            "status": "OPEN",
        },
    ]

    schedules = [
        MonitoringScheduleConfig(
            monitoring_type=MonitoringType.TECHNICAL_CRAWL,
            frequency=MonitoringFrequency.WEEKLY,
            enabled=True,
            next_run_at=datetime.now(timezone.utc) + timedelta(days=3),
        ),
        MonitoringScheduleConfig(
            monitoring_type=MonitoringType.CRITICAL_INFRASTRUCTURE,
            frequency=MonitoringFrequency.DAILY,
            enabled=True,
            next_run_at=datetime.now(timezone.utc) - timedelta(hours=1),  # DUE
        ),
    ]

    report: GovernanceDashboardReport = dashboard.generate_report(
        domain="example.com",
        findings=findings,
        remediation_tasks=remediation_tasks,
        recurring_defects_count=2,
        historical_scores={"seo_score": 82.0, "cro_score": 79.0},
        crawled_urls_count=90,
        total_sitemap_urls_count=100,
        schedules=schedules,
    )

    # 1. Open findings by severity
    assert report.open_findings_by_severity["CRITICAL"] == 2
    assert report.open_findings_by_severity["HIGH"] == 1

    # 2. Remediation completion rate (2 of 4 = 50%)
    assert report.remediation_completion_rate == 50.0

    # 3. Average resolution time ( (2 + 4) / 2 = 3.0 days )
    assert report.average_resolution_time_days == 3.0

    # 4. Recurring defects count
    assert report.recurring_defects_count == 2

    # 5. Unverified fixes count
    assert report.unverified_fixes_count == 1

    # 6. Audit coverage percentage (90/100 = 90%)
    assert report.audit_coverage_pct == 90.0

    # 7. Historical discipline scores
    assert report.historical_scores["seo_score"] == 82.0

    # 8. Data source availability
    assert report.data_source_availability.get("CrawlEngine") is True

    # 9. Monitoring status
    assert report.monitoring_status[MonitoringType.CRITICAL_INFRASTRUCTURE.value] == "DUE"
    assert report.monitoring_status[MonitoringType.TECHNICAL_CRAWL.value] == "ACTIVE"

    # 10. Team workload hours (5 + 4 + 3 = 12.0 hrs for open findings)
    assert report.team_workload_hours == 12.0


def test_phase10_end_to_end_orchestration():
    """Verify full continuous monitoring cycle running cohesively."""
    engine = ContinuousMonitoringEngine(domain="example.com")

    baseline_pages = {
        "https://example.com/": {
            "metadata": {"title": "Base Home"},
            "content_text": "Base text",
            "performance": {"load_time_ms": 400},
        }
    }
    current_pages = {
        "https://example.com/": {
            "metadata": {"title": "Current Home"},
            "content_text": "Current text",
            "performance": {"load_time_ms": 450},
        },
        "https://example.com/new-feature": {
            "metadata": {"title": "New Feature"},
            "content_text": "Fresh feature description",
        },
    }

    baseline_findings = [
        {"finding_id": "FIND-1", "severity": "MEDIUM", "affected_urls": ["https://example.com/"]}
    ]
    current_findings = [
        {"finding_id": "FIND-1", "severity": "MEDIUM", "affected_urls": ["https://example.com/"]},
        {"finding_id": "FIND-2", "severity": "HIGH", "affected_urls": ["https://example.com/new-feature"]},
    ]

    res = engine.run_continuous_monitoring_cycle(
        baseline_audit_id="audit_base_1",
        current_audit_id="audit_curr_2",
        baseline_pages=baseline_pages,
        current_pages=current_pages,
        baseline_findings=baseline_findings,
        current_findings=current_findings,
        baseline_audit_scores={"seo_score": 75.0, "sample_size": 1},
        current_audit_scores={"seo_score": 80.0, "sample_size": 2},
        remediation_tasks=[
            {"task_id": "task_1", "status": "VERIFIED_FIXED", "created_at": "2026-11-15T00:00:00+00:00", "resolved_at": "2026-11-16T00:00:00+00:00"}
        ],
    )

    assert res["domain"] == "example.com"
    assert isinstance(res["change_report"], WebsiteChangeReport)
    assert "https://example.com/new-feature" in res["change_report"].new_pages
    assert isinstance(res["lifecycle_diff"], FindingLifecycleDiff)
    assert any(f.finding_id == "FIND-2" for f in res["lifecycle_diff"].new_findings)
    assert isinstance(res["historical_report"], HistoricalIntelligenceReport)
    assert res["historical_report"].seo_delta == 5.0
    assert isinstance(res["governance_report"], GovernanceDashboardReport)
    assert res["governance_report"].audit_coverage_pct == 100.0


def test_phase10_backward_compatibility_recurring_audits(tmp_path):
    """Verify that existing RecurringAuditStore functions cleanly with new monitoring structures."""
    db_file = tmp_path / "test_recurring.db"
    store = RecurringAuditStore(database_path=str(db_file))

    sched = store.create(
        org_id="org_test",
        created_by="user_test",
        website_url="https://example.com",
        cadence_days=7,
        max_pages=25,
    )
    assert sched["schedule_id"] is not None
    assert sched["cadence_days"] == 7
    assert sched["status"] == "ACTIVE"

    listed = store.list_for_org(org_id="org_test")
    assert len(listed) == 1
    assert listed[0]["website_url"] == "https://example.com"

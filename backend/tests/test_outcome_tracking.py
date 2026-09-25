"""Outcome Tracking Agent: recheck, deltas, attribution, benchmark table."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.domain.enums import Category, Severity
from app.domain.models import CrawlManifest, Finding, PageEvidence
from app.intelligence.outcomes.store import OutcomeStore
from app.intelligence.outcomes.tracking import (
    OutcomeTrackingAgent,
    snapshot_from_manifest,
)


def _finding(fid, title, rec="Fix it", impact=7, sev=Severity.HIGH, rule=None):
    return Finding(
        finding_id=fid,
        category=Category.TECHNICAL_SEO,
        severity=sev,
        title=title,
        description=title,
        recommendation=rec,
        impact=impact,
        rule_id=rule,
    )


def _manifest(**kwargs):
    page = PageEvidence(
        url="https://example.com/",
        title=kwargs.get("title", "Hi"),
        h1=kwargs.get("h1", []),
        canonical_url=kwargs.get("canonical_url"),
        schema_types=kwargs.get("schema_types", []),
        images_without_alt=kwargs.get("images_without_alt", 0),
        viewport=kwargs.get("viewport"),
        ttfb_ms=kwargs.get("ttfb_ms", 400),
        ctas=kwargs.get("ctas", []),
        body_text=kwargs.get("body_text", ""),
    )
    return CrawlManifest(
        domain="example.com",
        base_url="https://example.com",
        pages=[page],
        robots_txt_found=kwargs.get("robots_txt_found", False),
        sitemap_found=kwargs.get("sitemap_found", False),
        crawl_health={"avg_ttfb_ms": kwargs.get("ttfb_ms", 400)},
    )


def test_robots_finding_resolves_when_file_appears():
    agent = OutcomeTrackingAgent()
    finding = _finding("find_001", "robots.txt was not found at the domain root.")
    baseline = snapshot_from_manifest(_manifest(robots_txt_found=False))
    current = snapshot_from_manifest(_manifest(robots_txt_found=True))
    result = agent.evaluate([finding], baseline, current, analysis_id="run_1", horizon_days=30)
    rec = result.records[0]
    assert rec.finding_id == "find_001"
    assert rec.evidence_condition_resolved is True
    assert rec.remediated is True
    assert rec.condition_key == "robots_txt_present"


def test_title_length_still_fails():
    agent = OutcomeTrackingAgent()
    finding = _finding("find_t", "Title tag is 12 characters; keep titles 50-60 characters.")
    baseline = snapshot_from_manifest(_manifest(title="Short"))
    current = snapshot_from_manifest(_manifest(title="StillShort"))
    rec = agent.evaluate([finding], baseline, current).records[0]
    assert rec.evidence_condition_resolved is False
    assert rec.remediated is False


def test_title_length_resolves_in_band():
    agent = OutcomeTrackingAgent()
    finding = _finding("find_t2", "Title should be 50-60 characters.")
    baseline = snapshot_from_manifest(_manifest(title="Hi"))
    current = snapshot_from_manifest(_manifest(title="X" * 55))
    rec = agent.evaluate([finding], baseline, current).records[0]
    assert 50 <= current.title_length <= 60
    assert rec.evidence_condition_resolved is True


def test_external_delta_and_no_causation_on_confounds():
    agent = OutcomeTrackingAgent()
    finding = _finding("find_h1", "Homepage is missing an H1.")
    baseline = snapshot_from_manifest(
        _manifest(h1=[], title="Old"),
        external_metrics={"lcp_ms": 3200, "review_count": 0},
    )
    current = snapshot_from_manifest(
        _manifest(h1=["We build software"], title="New Title Entirely Different Brand Line"),
        external_metrics={"lcp_ms": 2100, "review_count": 0},
    )
    rec = agent.evaluate(
        [finding],
        baseline,
        current,
        client_remediated_ids=["find_h1"],
        horizon_days=30,
    ).records[0]
    assert rec.evidence_condition_resolved is True
    assert rec.external_metric_delta["lcp_ms"]["direction"] == "improved"
    assert rec.external_metric_delta["lcp_ms"]["delta"] == -1100
    assert rec.confidence_this_delta_is_attributable_to_the_fix in ("MEDIUM", "LOW")
    assert rec.confidence_this_delta_is_attributable_to_the_fix != "HIGH"
    assert any("other_simultaneous_dom_changes" in c for c in rec.confounds)
    assert "correlation, not proof of causation" in rec.attribution_disclaimer.lower()


def test_metric_moved_without_fix_is_low_attribution():
    agent = OutcomeTrackingAgent()
    finding = _finding("find_h1", "Homepage is missing an H1.")
    baseline = snapshot_from_manifest(_manifest(h1=[]), external_metrics={"organic_traffic": 100})
    current = snapshot_from_manifest(_manifest(h1=[]), external_metrics={"organic_traffic": 180})
    rec = agent.evaluate([finding], baseline, current).records[0]
    assert rec.evidence_condition_resolved is False
    assert rec.external_metric_delta["organic_traffic"]["direction"] == "improved"
    assert rec.confidence_this_delta_is_attributable_to_the_fix == "LOW"
    assert "metric_moved_without_condition_resolved" in rec.confounds
    assert rec.observed_outcome == "unresolved_metric_improved"


def test_high_attribution_requires_clean_window():
    agent = OutcomeTrackingAgent()
    finding = _finding("find_r", "robots.txt was not found at the domain root.")
    baseline = snapshot_from_manifest(
        _manifest(robots_txt_found=False, title="Same Title Here"),
        external_metrics={"organic_traffic": 50},
    )
    current = snapshot_from_manifest(
        _manifest(robots_txt_found=True, title="Same Title Here"),
        external_metrics={"organic_traffic": 80},
    )
    rec = agent.evaluate(
        [finding], baseline, current, client_remediated_ids=["find_r"]
    ).records[0]
    assert rec.evidence_condition_resolved is True
    assert rec.confidence_this_delta_is_attributable_to_the_fix == "HIGH"


def test_missing_external_metrics_do_not_invent_delta():
    agent = OutcomeTrackingAgent()
    finding = _finding("find_r", "robots.txt was not found.")
    baseline = snapshot_from_manifest(_manifest(robots_txt_found=False))
    current = snapshot_from_manifest(_manifest(robots_txt_found=True))
    rec = agent.evaluate([finding], baseline, current).records[0]
    assert rec.external_metric_delta == {}
    assert rec.confidence_this_delta_is_attributable_to_the_fix == "LOW"
    assert rec.observed_outcome == "resolved_no_metric"


def test_store_schedule_and_benchmark_table(tmp_path: Path):
    store = OutcomeStore(str(tmp_path / "outcomes.db"))
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    jobs = store.schedule("run_abc", "https://example.com/", horizons=[30, 60, 90], now=now)
    assert [j["horizon_days"] for j in jobs] == [30, 60, 90]
    assert store.due_jobs(now=now) == []
    due = store.due_jobs(now=now + timedelta(days=31))
    assert len(due) == 1
    assert due[0]["horizon_days"] == 30

    agent = OutcomeTrackingAgent()
    finding = _finding("find_001", "robots.txt was not found.")
    baseline = snapshot_from_manifest(_manifest(robots_txt_found=False))
    current = snapshot_from_manifest(_manifest(robots_txt_found=True))
    result = agent.evaluate(
        [finding], baseline, current, analysis_id="run_abc", horizon_days=30
    )
    store.save_run(result, job_id=jobs[0]["job_id"])
    rows = store.benchmark()
    assert rows
    row = rows[0]
    assert "finding_type" in row
    assert "predicted_impact" in row
    assert "observed_outcome_mix" in row
    assert row["sample_size"] == 1
    assert row["resolved_rate"] == 1.0
    saved = store.records_for_analysis("run_abc")
    assert saved[0]["finding_id"] == "find_001"
    assert saved[0]["evidence_condition_resolved"] is True


def test_90_day_horizon_flags_seasonality():
    agent = OutcomeTrackingAgent()
    finding = _finding("find_r", "robots.txt was not found.")
    rec = agent.evaluate(
        [finding],
        snapshot_from_manifest(_manifest(robots_txt_found=False)),
        snapshot_from_manifest(_manifest(robots_txt_found=True)),
        horizon_days=90,
    ).records[0]
    assert "seasonal_traffic_window_possible" in rec.confounds

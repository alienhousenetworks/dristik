"""
Unit and integration tests for RegressionDetector and continuous assurance multi-run snapshots.
"""
from datetime import datetime, timezone

import pytest
from app.domain.models import (
    AuditSnapshot,
    CategoryScore,
    Finding,
    OverallScoreResult,
)
from app.domain.enums import Category, Severity
from app.intelligence.monitoring.regression_detector import RegressionDetector, regression_detector


def _make_cat_score(cat: Category, score: float, weight: float = 0.14) -> CategoryScore:
    return CategoryScore(
        category=cat,
        score=score,
        weight=weight,
        weighted_score=round(score * weight, 2),
        summary=f"{cat.value} test summary",
    )


def test_regression_detector_first_run_has_no_invented_history():
    detector = RegressionDetector()
    current_scores = OverallScoreResult(
        overall_score=84.0,
        grade="B",
        health_label="Healthy",
        category_scores={
            Category.TECHNICAL_SEO.value: _make_cat_score(Category.TECHNICAL_SEO, 63.0, 0.14),
            Category.AI_SEARCH.value: _make_cat_score(Category.AI_SEARCH, 42.0, 0.16),
            Category.SCHEMA.value: _make_cat_score(Category.SCHEMA, 54.0, 0.10),
        },
    )

    findings = [
        Finding(
            finding_id="find_001",
            title="Service schema is missing",
            description="Service schema JSON-LD was not found.",
            category=Category.SCHEMA,
            severity=Severity.HIGH,
            recommendation="Add Service schema JSON-LD",
        )
    ]

    report = detector.evaluate_audit_run(
        domain="example.com",
        current_scores=current_scores,
        findings=findings,
        evidence_ledger={},
        snapshot_id="snap_f3d453addc",
        historical_snapshots=None,
    )

    assert report.has_regression is False
    assert report.regressions == []
    assert report.baseline_run is None
    assert report.score_delta == 0.0
    assert len(report.historical_timeline) == 1
    current = report.historical_timeline[0]
    assert current.run_label == "Run #001"
    assert current.score == 84.0
    assert current.evidence_seal == "snap_f3d453addc"
    assert current.status == "HEALTHY"
    assert current.date == datetime.now(timezone.utc).strftime("%b %d, %Y")
    assert all(item.title != "Service page schema removed" for item in report.regressions)


def test_regression_detector_drops_canned_history():
    detector = RegressionDetector()
    canned = [
        AuditSnapshot(
            snapshot_id="snap_example.com_001",
            run_label="Run #001",
            date="Sep 24",
            score=27.0,
            evidence_seal="sha256:7f3a8b291c4e09f",
            status="HEALTHY",
        ),
        AuditSnapshot(
            snapshot_id="snap_example.com_002",
            run_label="Run #002",
            date="Oct 02",
            score=61.0,
            evidence_seal="sha256:9b1c4e820f17a32",
            verified_schema_types=["Service", "Organization"],
            status="IMPROVED",
        ),
    ]
    current_scores = OverallScoreResult(
        overall_score=84.0,
        grade="B",
        health_label="Healthy",
        category_scores={
            Category.TECHNICAL_SEO.value: _make_cat_score(Category.TECHNICAL_SEO, 63.0, 0.14),
        },
    )
    report = detector.evaluate_audit_run(
        domain="example.com",
        current_scores=current_scores,
        findings=[],
        evidence_ledger={},
        snapshot_id="snap_real",
        historical_snapshots=canned,
    )
    assert len(report.historical_timeline) == 1
    assert report.historical_timeline[0].snapshot_id == "snap_real"
    assert report.has_regression is False
    assert report.regressions == []


def test_regression_detector_custom_snapshots():
    detector = RegressionDetector()
    hist = [
        AuditSnapshot(
            snapshot_id="snap_001",
            run_label="Run #001",
            date="Jan 10",
            score=50.0,
            category_scores={Category.TECHNICAL_SEO.value: 80.0},
            evidence_seal="sha256:111",
            verified_schema_types=["Service"],
            findings_count=5,
            status="HEALTHY",
        )
    ]

    current_scores = OverallScoreResult(
        overall_score=40.0,
        grade="D",
        health_label="Critical",
        category_scores={
            Category.TECHNICAL_SEO.value: _make_cat_score(Category.TECHNICAL_SEO, 70.0, 0.14)
        },
    )

    report = detector.evaluate_audit_run(
        domain="acme.org",
        current_scores=current_scores,
        findings=[],
        evidence_ledger={"ev_1": {"text": "Just plain html"}},
        snapshot_id="snap_002",
        historical_snapshots=hist,
    )

    assert report.has_regression is True
    assert report.score_delta == -10.0
    assert report.baseline_run.snapshot_id == "snap_001"
    assert report.current_run.snapshot_id == "snap_002"
    # Service was in verified_schema_types in snap_001, missing now -> regression
    assert any(r.title == "Service schema removed" for r in report.regressions)
    assert all("50 to 42" not in r.description for r in report.regressions)
    assert all("66 to 63" not in r.description for r in report.regressions)

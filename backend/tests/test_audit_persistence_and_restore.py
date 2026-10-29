"""
Tests for durable audit persistence, DB fallback restoration, and list_analyses endpoint.
"""
import pytest
from datetime import datetime
from app.domain.models import (
    AnalysisRun,
    ExecutiveReport,
    BusinessProfile,
    OverallScoreResult,
    CategoryScore,
    ThreeWayComparison,
    HonestScores,
)
from app.domain.enums import AnalysisStage, Category
from app.orchestration.orchestrator import orchestrator
from app.persistence.repository import get_audit_repository

def test_audit_db_restoration_with_full_report():
    repo = get_audit_repository()
    analysis_id = f"test_persist_{int(datetime.now().timestamp())}"

    business_profile = BusinessProfile(
        business_name="Acme Corporation",
        industry="Technology",
        niche="Enterprise Cloud",
        products=["Cloud Platform"],
        services=["Migration"],
        target_audience="CTOs",
        geography="Global",
        business_model="B2B SaaS",
        value_proposition="Cloud simplicity"
    )

    scores = OverallScoreResult(
        overall_score=85.0,
        grade="A",
        health_label="Excellent",
        category_scores={
            "TECHNICAL_SEO": CategoryScore(
                category=Category.TECHNICAL_SEO,
                score=90.0,
                weight=0.5,
                weighted_score=45.0,
                summary="Excellent"
            ),
            "GEO": CategoryScore(
                category=Category.GEO,
                score=80.0,
                weight=0.5,
                weighted_score=40.0,
                summary="Strong"
            ),
        }
    )

    report = ExecutiveReport(
        report_id=f"rep_{analysis_id}",
        analysis_id=analysis_id,
        website_url="https://acme-test.org",
        domain="acme-test.org",
        generated_at="September 20, 2026 - 12:00 UTC",
        business_profile=business_profile,
        scores=scores,
        story_summary="Acme demonstrates world-class enterprise posture.",
        primary_strategic_opportunity="Scale international expansion.",
        consultant_advice_what_to_ignore="Ignore micro meta tag discrepancies.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="High trust",
            search_engine_perspective="Clean indexation",
            ai_answer_engine_perspective="High citability"
        ),
        honest_scores=HonestScores(
            human_score=88,
            google_score=92,
            ai_citation_score=84,
            score_band="Citation Ready"
        ),
    )

    run = AnalysisRun(
        analysis_id=analysis_id,
        website_url="https://acme-test.org",
        status=AnalysisStage.COMPLETED,
        progress_percentage=100,
        current_step="Audit Completed",
        report=report,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        completed_at=datetime.now().isoformat(),
    )

    # 1. Save to SQLite DB
    repo.save_run(run)

    # 2. Clear orchestrator in-memory cache to force DB restoration
    if analysis_id in orchestrator.runs:
        del orchestrator.runs[analysis_id]

    # 3. Retrieve via orchestrator.get_run (should hit SQLite fallback)
    restored = orchestrator.get_run(analysis_id)
    assert restored is not None, "Failed to restore run from SQLite database"
    assert restored.analysis_id == analysis_id
    assert restored.status == AnalysisStage.COMPLETED
    assert restored.report is not None, "Report was not restored from raw_report_json"
    assert restored.report.domain == "acme-test.org"
    assert restored.report.scores.overall_score == 85.0
    assert restored.report.honest_scores.ai_citation_score == 84

    # 4. Check list_runs includes this audit
    runs = repo.list_runs(limit=20)
    matching = [r for r in runs if r["analysis_id"] == analysis_id]
    assert len(matching) == 1
    assert matching[0]["domain"] == "acme-test.org"

def test_analyses_api_requires_the_owning_organization():
    import uuid
    from fastapi.testclient import TestClient
    from app.main import app

    owner = TestClient(app)
    other = TestClient(app)
    anonymous = owner.get("/api/v1/analyses")
    assert anonymous.status_code == 401

    email = f"persist_{uuid.uuid4().hex[:8]}@example.com"
    signup = owner.post("/api/v1/auth/signup", json={
        "full_name": "Persist Owner",
        "email": email,
        "password": "OwnerPass1",
        "organization_name": "Persist Org",
    })
    assert signup.status_code == 200, signup.text
    user = signup.json()["user"]
    run = orchestrator.create_run("https://acme-owned.example", org_id=user["org_id"], created_by=user["user_id"])

    listed = owner.get("/api/v1/analyses")
    assert listed.status_code == 200
    ids = [item["analysis_id"] for item in listed.json()]
    assert run.analysis_id in ids

    single = owner.get(f"/api/v1/analyses/{run.analysis_id}")
    assert single.status_code == 200
    assert single.json()["analysis_id"] == run.analysis_id

    other_signup = other.post("/api/v1/auth/signup", json={
        "full_name": "Other Owner",
        "email": f"other_{uuid.uuid4().hex[:8]}@example.com",
        "password": "OwnerPass1",
        "organization_name": "Other Org",
    })
    assert other_signup.status_code == 200, other_signup.text
    hidden = other.get(f"/api/v1/analyses/{run.analysis_id}")
    assert hidden.status_code == 404

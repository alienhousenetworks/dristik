"""
Integration tests for P1 API routes:
- GET /api/v1/analyses/{analysis_id}/evidence-explorer
- GET /api/v1/analyses/{analysis_id}/score-explanation
- GET /api/v1/analyses/{analysis_id}/checkpoints
- POST /api/v1/analyses/{analysis_id}/resume
"""
from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.orchestration.orchestrator import orchestrator
from app.persistence.repository import get_audit_repository
from app.persistence.models import StageCheckpoint
from app.domain.enums import AnalysisStage, Category, Severity, UserRole
from app.domain.models import AnalysisRun, Claim, Finding
from app.evidence.models import Evidence
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, get_current_user_optional


client = TestClient(app)


@pytest.fixture
def mock_user():
    return UserIdentity(
        user_id="usr_admin_test",
        org_id="org_enterprise",
        email="admin@enterprise.test",
        role=UserRole.ADMIN,
    )


@pytest.fixture(autouse=True)
def override_auth(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_optional] = lambda: mock_user
    yield
    app.dependency_overrides.clear()


def test_evidence_explorer_endpoint(mock_user):
    now = datetime.now(timezone.utc).isoformat()
    analysis_id = "run_api_ee_01"
    run = AnalysisRun(
        analysis_id=analysis_id,
        org_id=mock_user.org_id,
        website_url="https://linear.app",
        status=AnalysisStage.COMPLETED,
        created_at=now,
        updated_at=now,
    )
    orchestrator.runs[analysis_id] = run
    repo = get_audit_repository()
    repo.save_run(run)

    # Add evidence, claim, finding
    ev = Evidence(
        id="ev_api_01",
        source_type="html_dom",
        analyzer="h1_extractor",
        hash="sha_ev_api_01",
        url="https://linear.app/",
        text="Linear Issue Tracking",
        selector="h1.hero",
        raw_snapshot_id="snap_api_01",
    )
    repo.persist_evidence_items(analysis_id, [ev])

    claim = Claim(
        id="claim_api_01",
        agent_id="seo.onpage.v3",
        category=Category.ON_PAGE_SEO,
        statement="H1 tag is concise and accurate.",
        evidence_refs=["ev_api_01"],
    )
    repo.persist_claims(analysis_id, [claim])

    finding = Finding(
        finding_id="find_api_01",
        category=Category.ON_PAGE_SEO,
        severity=Severity.INFO,
        title="Valid Hero Heading",
        description="Clear H1 heading identified.",
        impact=5,
        recommendation="No changes needed.",
        evidence_refs=["ev_api_01"],
        claim_refs=["claim_api_01"],
    )
    repo.persist_findings(analysis_id, [finding])

    res = client.get(f"/api/v1/analyses/{analysis_id}/evidence-explorer")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["analysis_id"] == analysis_id
    assert data["total_traces"] >= 1
    trace = data["traces"][0]
    assert trace["finding_id"] == "find_api_01"
    assert trace["claim_id"] == "claim_api_01"
    assert trace["evidence_id"] == "ev_api_01"
    assert trace["selector"] == "h1.hero"
    assert trace["raw_snapshot_id"] == "snap_api_01"


def test_score_explanation_endpoint(mock_user):
    now = datetime.now(timezone.utc).isoformat()
    analysis_id = "run_api_se_01"
    run = AnalysisRun(
        analysis_id=analysis_id,
        org_id=mock_user.org_id,
        website_url="https://linear.app",
        status=AnalysisStage.COMPLETED,
        created_at=now,
        updated_at=now,
    )
    orchestrator.runs[analysis_id] = run
    repo = get_audit_repository()
    repo.save_run(run)

    res = client.get(f"/api/v1/analyses/{analysis_id}/score-explanation")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["analysis_id"] == analysis_id
    assert data["domain"] == "linear.app"
    assert len(data["dimensions"]) >= 4
    dim_keys = [d["dimension_key"] for d in data["dimensions"]]
    assert "entity_clarity" in dim_keys
    assert "extractability" in dim_keys
    assert "ai_visibility" in dim_keys
    assert "structured_data" in dim_keys


def test_checkpoints_endpoint(mock_user):
    now = datetime.now(timezone.utc).isoformat()
    analysis_id = f"run_api_chk_{uuid.uuid4().hex[:8]}"
    run = AnalysisRun(
        analysis_id=analysis_id,
        org_id=mock_user.org_id,
        website_url="https://linear.app",
        status=AnalysisStage.INGESTING,
        created_at=now,
        updated_at=now,
    )
    orchestrator.runs[analysis_id] = run
    repo = get_audit_repository()
    repo.save_run(run)

    chk = StageCheckpoint(
        analysis_id=analysis_id,
        stage=AnalysisStage.INGESTING,
        step_number=1,
        status="COMPLETED",
        crawled_count=4,
        evidence_count=18,
    )
    repo.save_checkpoint(chk)

    res = client.get(f"/api/v1/analyses/{analysis_id}/checkpoints")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["analysis_id"] == analysis_id
    assert data["checkpoints_count"] == 1
    assert data["checkpoints"][0]["step_number"] == 1
    assert data["checkpoints"][0]["stage"] == "ingesting"


def test_resume_analysis_endpoint(mock_user, monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    analysis_id = f"run_api_resume_{uuid.uuid4().hex[:8]}"
    run = AnalysisRun(
        analysis_id=analysis_id,
        org_id=mock_user.org_id,
        website_url="https://linear.app",
        status=AnalysisStage.FAILED,
        created_at=now,
        updated_at=now,
    )
    orchestrator.runs[analysis_id] = run
    repo = get_audit_repository()
    repo.save_run(run)

    # Checkpoint at wave 1
    chk = StageCheckpoint(
        analysis_id=analysis_id,
        stage=AnalysisStage.SPECIALIST_EXECUTION,
        step_number=2,
        status="COMPLETED",
    )
    repo.save_checkpoint(chk)

    async def mock_resume(aid: str):
        return aid == analysis_id

    monkeypatch.setattr(orchestrator, "resume_analysis_pipeline", mock_resume)

    res = client.post(f"/api/v1/analyses/{analysis_id}/resume")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "resumed"
    assert data["analysis_id"] == analysis_id


def test_nonexistent_analysis_returns_404():
    res = client.get("/api/v1/analyses/run_does_not_exist/evidence-explorer")
    assert res.status_code == 404

    res = client.get("/api/v1/analyses/run_does_not_exist/score-explanation")
    assert res.status_code == 404

    res = client.get("/api/v1/analyses/run_does_not_exist/checkpoints")
    assert res.status_code == 404

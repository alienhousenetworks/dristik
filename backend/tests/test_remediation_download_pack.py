"""
Integration test for Downloadable Remediation Patch Pack endpoint:
GET /api/v1/remediation/download-pack/{analysis_id}
Verifies that:
- schema.jsonld
- robots.txt
- llms.txt
- security_headers.conf
- geo_definitions.html
are all packaged into dristik-remediation-patches.zip.
"""
import io
import uuid
import zipfile
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.orchestration.orchestrator import orchestrator
from app.domain.models import AnalysisRun, ExecutiveReport, BusinessProfile, OverallScoreResult, ThreeWayComparison
from app.domain.enums import AnalysisStage

client = TestClient(app)


def test_download_remediation_patch_pack():
    anonymous = client.get("/api/v1/remediation/download-pack/run_test_pack_01")
    assert anonymous.status_code == 401
    signup = client.post("/api/v1/auth/signup", json={
        "full_name": "Pack Owner",
        "email": f"pack_{uuid.uuid4().hex[:8]}@example.com",
        "password": "OwnerPass1",
        "organization_name": "Pack Org",
    })
    assert signup.status_code == 200, signup.text
    user = signup.json()["user"]

    now = datetime.now(timezone.utc).isoformat()
    analysis_id = "run_test_pack_01"

    report = ExecutiveReport(
        report_id="rep_test_pack_01",
        analysis_id=analysis_id,
        website_url="https://acme.com",
        domain="acme.com",
        generated_at=now,
        business_profile=BusinessProfile(business_name="Acme", niche="Web Intelligence", value_proposition="Verified AI search optimization"),
        scores=OverallScoreResult(overall_score=85.0, grade="A", health_label="Optimal", category_scores={}),
        story_summary="Acme executive summary",
        primary_strategic_opportunity="AI search optimization",
        consultant_advice_what_to_ignore="Ignore superficial checklist tools",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Human perspective",
            search_engine_perspective="Search perspective",
            ai_answer_engine_perspective="AI perspective"
        )
    )

    run = AnalysisRun(
        analysis_id=analysis_id,
        org_id=user["org_id"],
        website_url="https://acme.com",
        status=AnalysisStage.COMPLETED,
        created_at=now,
        updated_at=now,
        report=report
    )
    orchestrator.runs[analysis_id] = run

    resp = client.get(f"/api/v1/remediation/download-pack/{analysis_id}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "dristik-remediation-patches" in resp.headers["content-disposition"]

    # Open zip and check file entries
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    filenames = zf.namelist()

    assert "schema.jsonld" in filenames
    assert "robots.txt" in filenames
    assert "llms.txt" in filenames
    assert "security_headers.conf" in filenames
    assert "geo_definitions.html" in filenames

    # Verify content in security_headers.conf and geo_definitions.html
    sec_content = zf.read("security_headers.conf").decode("utf-8")
    assert "Strict-Transport-Security" in sec_content
    assert "X-Frame-Options" in sec_content

    geo_content = zf.read("geo_definitions.html").decode("utf-8")
    assert "What is Acme?" in geo_content
    assert "Who is Acme for?" in geo_content

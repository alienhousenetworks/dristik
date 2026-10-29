import io
import uuid
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.orchestration.orchestrator import orchestrator
from app.domain.models import BusinessProfile, CommercialQueryEvaluation

@pytest.mark.asyncio
async def test_patch_pack_routes_and_aliases():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        denied = await ac.get("/api/v1/analyses/missing/patch-pack/files")
        assert denied.status_code == 401

        signup = await ac.post("/api/v1/auth/signup", json={
            "full_name": "Patch Owner",
            "email": f"patch_{uuid.uuid4().hex[:8]}@example.com",
            "password": "OwnerPass1",
            "organization_name": "Patch Org",
        })
        assert signup.status_code == 200, signup.text
        user = signup.json()["user"]

        # 1. Create a dummy run with report
        run = orchestrator.create_run("https://example.com", org_id=user["org_id"], created_by=user["user_id"])
        run_id = run.analysis_id
        rep_id = "rep_test_patch123"

        # Mock an ExecutiveReport on this run
        from app.domain.models import ExecutiveReport, OverallScoreResult, ThreeWayComparison
        report = ExecutiveReport(
            report_id=rep_id,
            analysis_id=run_id,
            website_url="https://example.com",
            domain="example.com",
            generated_at="Now",
            business_profile=BusinessProfile(business_name="Acme Corp", niche="Enterprise SaaS"),
            scores=OverallScoreResult(overall_score=85, overall_confidence=0.9, evidence_coverage=0.9, grade="A", health_label="Strong", category_scores={}, intent_adjusted_weights={}),
            story_summary="Test story",
            what_site_gets_right=[],
            what_is_holding_it_back=[],
            primary_strategic_opportunity="Optimize",
            consultant_advice_what_to_ignore="Ignore vanity",
            three_way_comparison=ThreeWayComparison(
                human_visitor_perspective="Clear value",
                search_engine_perspective="Indexable",
                ai_answer_engine_perspective="Direct answers"
            ),
            commercial_evaluations=[
                CommercialQueryEvaluation(
                    question_key="identity",
                    question_title="Identity",
                    buyer_query="What is Acme Corp?",
                    before_score=7,
                    before_answer="Acme Corp is an Enterprise SaaS platform.",
                    before_evidence_status="VERIFIED"
                )
            ]
        )
        run.report = report

        # Test 1: Fetch patch files via /api/v1 with run_id
        res1 = await ac.get(f"/api/v1/analyses/{run_id}/patch-pack/files")
        assert res1.status_code == 200, res1.text
        data1 = res1.json()
        assert "schema.jsonld" in data1["files"]
        assert "README_DEV_INSTALL.md" in data1["files"]

        # Test 2: Fetch patch notion block via /api with rep_id (the alias and report_id lookup!)
        res2 = await ac.get(f"/api/analyses/{rep_id}/patch-pack/notion")
        assert res2.status_code == 200, res2.text
        data2 = res2.json()
        assert "notion_markdown" in data2
        assert "Acme Corp" in data2["notion_markdown"]

        # Test 3: Download patch pack ZIP via /api/v1 with rep_id
        res3 = await ac.get(f"/api/v1/analyses/{rep_id}/patch-pack/zip")
        assert res3.status_code == 200, res3.text
        assert res3.headers.get("content-type") == "application/zip"
        
        # Verify valid zip archive
        zip_buf = io.BytesIO(res3.content)
        with zipfile.ZipFile(zip_buf, "r") as zf:
            names = zf.namelist()
            assert "schema.jsonld" in names
            assert "robots.txt" in names
            assert "llms.txt" in names
            assert "README_DEV_INSTALL.md" in names

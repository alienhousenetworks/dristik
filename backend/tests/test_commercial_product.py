"""Contracts for the commercial workflow: honest grader, measurement, and integrity."""
from __future__ import annotations

import os

import httpx
import pytest
from fastapi import HTTPException

from app.api.routes.audits.public_grader import enforce_grade_quota, reset_public_grader_limits
from app.commercial.evidence_record import StructuredEvidenceRecord
from app.commercial.integrity import seal_records, verify_seal
from app.commercial.measurement import assess_proportion, required_independent_trials
from app.commercial.remediation_policy import deployment_decision, patch_requires_human_approval
from app.commercial.workflow import project_operating_workflow
from app.domain.enums import Category, Severity
from app.domain.models import Finding
from app.external_authority.traffic_estimator import estimate_domain_traffic
from app.orchestration.public_grader import run_public_grade
from app.scoring.engine import severity_rank
from types import SimpleNamespace


HOME_HTML = """
<html lang="en">
<head>
  <title>Example Instruments For Measured Public Pages</title>
  <meta name="description" content="Example publishes measured instruments and documents the exact pages a buyer can inspect before requesting a full audit.">
  <link rel="canonical" href="https://example.com/">
</head>
<body>
  <h1>Example instruments</h1>
  <p>%s</p>
</body>
</html>
""" % ("measured " * 220)


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/robots.txt":
        return httpx.Response(200, text="User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n")
    if path == "/sitemap.xml":
        return httpx.Response(200, text="<?xml version='1.0'?><urlset><url><loc>https://example.com/</loc></url></urlset>")
    if path == "/llms.txt":
        return httpx.Response(404, text="missing")
    return httpx.Response(200, text=HOME_HTML)


@pytest.mark.asyncio
async def test_public_grader_reports_only_observed_homepage_facts():
    transport = httpx.MockTransport(_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await run_public_grade("https://example.com/pricing", client=client)

    assert result.domain == "example.com"
    assert result.assessment_kind == "preliminary_technical_readiness"
    assert result.score_kind == "preliminary_readiness_not_live_geo"
    assert result.domain_age_years is None
    assert result.domain_creation_date is None
    assert result.has_ssr is None
    assert result.traffic_summary.monthly_visits is None
    assert result.traffic_summary.measurement_status == "not_measured"
    assert result.ai_citations["chatgpt"]["status"] == "not_measured"
    assert result.ai_citations["chatgpt"]["citations"] is None
    assert result.ai_citations["google_ai_overview"]["citations"] is None
    assert len(result.top_findings) <= 3
    assert result.word_count >= 200
    assert result.h1_count == 1
    assert any(page.url.endswith("/robots.txt") or "robots.txt" in page.url for page in result.pages_inspected)
    assert "Live AI visibility across answer engines" in result.checks_not_run
    assert "not a complete GEO score" in result.coverage_note
    assert "truncated" not in result.coverage_note.lower()
    assert all("Alien" not in finding.title for finding in result.top_findings)
    assert all(item.confidence == "observed" for item in result.provenance)


@pytest.mark.asyncio
async def test_public_grader_discloses_a_truncated_response():
    from app.orchestration.public_grader import _MAX_BYTES

    oversized = "<html><head><title>Wide</title></head><body>" + ("word " * (_MAX_BYTES // 4)) + "</body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            return httpx.Response(200, text=oversized)
        return httpx.Response(404, text="missing")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await run_public_grade("https://example.com", client=client)

    assert "truncated before parsing" in result.coverage_note
    assert result.score_kind == "preliminary_readiness_not_live_geo"


@pytest.mark.asyncio
async def test_public_grader_refuses_metadata_and_private_hosts():
    with pytest.raises(ValueError):
        await run_public_grade("http://127.0.0.1/latest/meta-data")
    with pytest.raises(ValueError, match="Blocked"):
        await run_public_grade("https://metadata.google.internal/computeMetadata/v1/")


def test_crux_is_not_turned_into_visits():
    summary = estimate_domain_traffic("example.com", crux_data={"lcp_p75_ms": 2400}, organic_keywords_count=500)
    assert summary.monthly_visits is None
    assert summary.field_experience == {"lcp_p75_ms": 2400}
    measured = estimate_domain_traffic("example.com", measured_monthly_visits=42, measurement_source="GA4")
    assert measured.monthly_visits == 42
    assert measured.measurement_status == "measured"
    assert measured.is_estimated is False


def test_five_runs_do_not_meet_a_ten_point_precision_target():
    needed = required_independent_trials(10)
    assert needed > 5
    empty = assess_proportion(0, 5)
    full = assess_proportion(5, 5)
    wider = assess_proportion(30, 100)
    assert empty.meets_precision_target is False
    assert full.meets_precision_target is False
    assert empty.interval_low_pct == 0.0
    assert full.interval_high_pct == 100.0
    assert wider.trials == 100
    assert wider.independence_assumed is True
    assert wider.dependence_adjusted is False


def test_integrity_seal_fails_closed_and_does_not_claim_correctness():
    seed = os.urandom(32)
    os.environ["DRISTIK_EVIDENCE_SIGNING_SEED"] = seed.hex()
    os.environ["DRISTIK_EVIDENCE_SIGNING_KEY_ID"] = "test-key"
    try:
        _assert_signed_record()
    finally:
        os.environ.pop("DRISTIK_EVIDENCE_SIGNING_SEED", None)
        os.environ.pop("DRISTIK_EVIDENCE_SIGNING_KEY_ID", None)


def _assert_signed_record():
    record = StructuredEvidenceRecord(
        evidence_id="ev_001",
        source="https://example.com/",
        observation="Homepage title is missing.",
        observed_at="2026-10-10T00:00:00Z",
        scope="PAGE_VERIFIED",
        method="public_grader.v3",
        confidence="observed",
    ).canonical_body()
    seal = seal_records([record, {"evidence_id": "ev_002", "observation": "second"}])
    assert seal.proves == "integrity_and_provenance"
    assert "not proof" in seal.limitation
    assert verify_seal(record, seal)["valid"] is True

    tampered = dict(record)
    tampered["observation"] = "Homepage title is present."
    assert verify_seal(tampered, seal)["valid"] is False

    os.environ.pop("DRISTIK_EVIDENCE_SIGNING_SEED", None)
    os.environ.pop("DRISTIK_EVIDENCE_SIGNING_KEY_ID", None)
    closed = verify_seal(record, seal)
    assert closed["valid"] is False
    assert closed["signature_ok"] is False


def test_workflow_keeps_findings_and_separates_outcome_layers():
    projected = project_operating_workflow({
        "domain": "example.com",
        "website_url": "https://example.com",
        "findings": [
            {"finding_id": "low", "title": "Alt text", "severity": "LOW", "impact": 2, "confidence": 0.4, "effort": 1, "category": "CONTENT"},
            {
                "finding_id": "high",
                "title": "Noindex",
                "severity": "CRITICAL",
                "impact": 9,
                "confidence": 0.95,
                "effort": 2,
                "category": "TECHNICAL_SEO",
                "calibrated_impact": {"business_impact": "CRITICAL", "confidence": 0.99},
                "evidence_refs": ["ev_1"],
            },
        ],
        "google_performance": {"analytics": {"state": "NOT_CONNECTED"}, "search_console": {"state": "NOT_CONNECTED"}},
    })
    assert [item["finding_id"] for item in projected["decide"]["findings"]] == ["high", "low"]
    assert projected["existing_coverage_retained"] == ["seo", "geo", "aeo", "cro", "authority", "conversion"]
    layers = {item["level"]: item["status"] for item in projected["prove"]["attribution_layers"]}
    assert layers["observed"] != "measured"
    assert layers["associated"] == "not_measured"
    assert layers["incremental"] == "not_measured"
    assert projected["prove"]["score_increase_is_not_attribution"] is True


def test_consequential_schema_cannot_auto_approve_or_invent_citation_points():
    safe = SimpleNamespace(
        risk_level="SAFE_AUTO",
        title="Canonical",
        explanation="Add the fetched canonical.",
        after_snippet='<link rel="canonical" href="https://example.com/">',
        operation="REPLACE",
        metadata_payload={},
    )
    factual = SimpleNamespace(
        risk_level="SAFE_AUTO",
        title="Offer schema",
        explanation="Generated from a model hallucination.",
        after_snippet='{"@type":"Offer","price":"10"}',
        operation="UPDATE_JSONLD",
        metadata_payload={},
    )
    assert patch_requires_human_approval(safe) is False
    assert patch_requires_human_approval(factual) is True
    decision = deployment_decision(factual, explicit_production_authorization=False)
    assert decision["human_approval_required"] is True
    assert decision["production_deploy_allowed"] is False
    assert decision["unattended_agent_deploy_allowed"] is False
    assert decision["citation_score_delta"] is None


def test_severity_rank_prefers_critical_over_medium():
    critical = Finding(
        finding_id="c",
        category=Category.TECHNICAL_SEO,
        severity=Severity.CRITICAL,
        title="Critical",
        description="Critical",
        recommendation="Fix",
    )
    medium = Finding(
        finding_id="m",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        title="Medium",
        description="Medium",
        recommendation="Fix",
    )
    assert severity_rank(critical) > severity_rank(medium)


def test_public_grader_quota():
    reset_public_grader_limits()
    for _ in range(8):
        enforce_grade_quota("grader-test", now=1_000.0)
    with pytest.raises(HTTPException) as caught:
        enforce_grade_quota("grader-test", now=1_010.0)
    assert caught.value.status_code == 429
    enforce_grade_quota("grader-test", now=1_070.0)
    reset_public_grader_limits()

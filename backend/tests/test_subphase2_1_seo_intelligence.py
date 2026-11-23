"""
Regression tests for Phase 2 Subphase 2.1: SEO Intelligence Rebuild.
Verifies:
1. Search Console attribution emits no fabricated causal chains when findings are empty.
2. Competitive engine does NOT derive GEO citations/mentions from commercial query evaluations.
3. Search demand strictly separates crawled topic clusters from unmeasured external search volume.
4. Keyword gap analysis returns empty opportunities when providers are unconfigured.
5. External authority returns UNAVAILABLE without default 75% dofollow or 5.0 toxicity scores.
6. SEO orchestrator connector runners report truthful unmeasured / not connected states.
"""
from __future__ import annotations

import pytest
from types import SimpleNamespace
from datetime import datetime, timezone

from app.seo.business.search_console import SearchConsoleEngine
from app.seo.competitive.engine import CompetitiveIntelligenceEngine
from app.seo.search_demand import extract_crawl_topic_seeds, build_search_demand
from app.seo.competitive.keyword_gap import KeywordGapEngine
from app.seo.intelligence.external_authority import ExternalAuthorityEngine
from app.domain.models import BusinessProfile, CommercialQueryEvaluation, PageEvidence


def test_search_console_without_findings_emits_no_fabricated_causal_chains():
    engine = SearchConsoleEngine()
    rep = engine.generate_search_attribution(domain="acme-test.org", analysis_id=None)
    # Must NOT have the fake "Unverified schema markup" fallback chain
    assert rep.causal_chains == []
    assert rep.is_connected is False
    assert rep.status in ("unavailable", "NOT_CONNECTED")
    assert rep.top_ranking_keywords == []
    assert rep.metrics is not None
    assert rep.metrics["clicks"] is None
    assert rep.metrics["impressions"] is None
    assert rep.row_count == 0
    assert len(rep.limitations) > 0


def test_competitive_engine_does_not_derive_geo_from_commercial_evaluations():
    engine = CompetitiveIntelligenceEngine()
    # Provide commercial query evaluations that previously passed and caused false GEO citation scores
    commercial_evals = [
        CommercialQueryEvaluation(
            question_key="identity",
            question_title="Identity Question",
            buyer_query="best enterprise b2b platform",
            target_url="https://acme-test.org/platform",
            before_score=10,
            before_answer="Acme is leading enterprise platform.",
            before_evidence_status="FOUND",
            after_score=10,
            status="PASSED",
            passage_found=True,
        ),
        CommercialQueryEvaluation(
            question_key="pricing",
            question_title="Pricing Question",
            buyer_query="acme enterprise pricing",
            target_url="https://acme-test.org/pricing",
            before_score=9,
            before_answer="Transparent enterprise pricing.",
            before_evidence_status="FOUND",
            after_score=9,
            status="PASSED",
            passage_found=True,
        ),
    ]

    report = engine.build_competitive_report(
        target_domain="acme-test.org",
        business_profile=BusinessProfile(business_name="Acme Test"),
        target_pages=[
            PageEvidence(
                url="https://acme-test.org/",
                status_code=200,
                title="Acme Test - Enterprise Platform",
                meta_description="Enterprise software platform",
                h1=["Acme Platform"],
                h2=["Solutions"],
                word_count=500,
            )
        ],
        commercial_evaluations=commercial_evals,
        observatory_records=None,  # No live AI engine observatory records
    )

    # GEO dimension for target domain MUST be UNMEASURED, NOT 100/100 from commercial_evals!
    target_dim_scores = report.dimension_scores.get("acme-test.org", {})
    geo_dim = target_dim_scores.get("geo")
    assert geo_dim is not None
    assert geo_dim.status == "UNMEASURED"
    assert geo_dim.score is None
    assert "unmeasured" in geo_dim.key_metrics.get("reason", "").lower()

    # Landscape coordinates for target domain must reflect unmeasured GEO
    coords = report.landscape_coordinates.get("acme-test.org")
    assert coords is not None
    assert coords.y is None
    assert coords.y_confidence.value == "UNMEASURED"


def test_search_demand_labels_crawl_topics_as_unmeasured_external_volume():
    pages = [
        SimpleNamespace(
            url="https://example.com/products/toothbrush",
            title="Electric Toothbrush | Sonic Cleaning",
            h1=["Sonic Toothbrush"],
            h2=["Key Benefits", "Pricing & Replacement Heads"],
        )
    ]
    profile = BusinessProfile(
        business_name="Perfora Oral Care",
        industry="Consumer Health",
        niche="Oral Care",
        products=["Sonic Toothbrush", "Teeth Whitening Pen"],
    )

    extracted = extract_crawl_topic_seeds(pages=pages, business_profile=profile)
    assert len(extracted["seed_keywords"]) > 0
    assert len(extracted["on_page_topic_clusters"]) > 0
    for cluster in extracted["on_page_topic_clusters"]:
        assert cluster["search_volume"] is None
        assert cluster["volume_status"] == "UNMEASURED_EXTERNAL_VOLUME"
        assert cluster["source"].startswith(("page_", "business_profile."))


def test_keyword_gap_without_provider_returns_empty_opportunities():
    gap_engine = KeywordGapEngine()
    report = gap_engine.evaluate_gap(
        target_domain="example.org",
        competitor_domains=["competitor1.org", "competitor2.org"],
        project_id=None,
    )
    assert report.total_missing_keywords == 0
    assert report.total_weak_keywords == 0
    assert report.total_opportunity_traffic == 0
    assert report.opportunities == []
    assert "No keyword gap" in report.summary


def test_external_authority_disconnected_returns_unavailable_without_fabricated_metrics():
    # 1. When disconnected
    profile_disc = ExternalAuthorityEngine.evaluate_authority("example.org")
    assert profile_disc.is_measured is False
    assert profile_disc.status == "AUTHORITY_UNAVAILABLE"
    assert profile_disc.referring_domains_count is None
    assert profile_disc.total_backlinks_count is None
    assert profile_disc.dofollow_ratio is None
    assert profile_disc.toxicity_score is None

    # 2. When connected with partial data: missing fields must NOT default to 0.75 or 5.0
    partial_data = {
        "referring_domains": 120,
        "total_backlinks": 4500,
        # dofollow_ratio, toxicity_score, new/lost omitted
    }
    profile_part = ExternalAuthorityEngine.evaluate_authority(
        "example.org",
        provider_name="DataForSEO",
        api_data=partial_data,
    )
    assert profile_part.is_measured is True
    assert profile_part.status == "AUTHORITY_MEASURED"
    assert profile_part.referring_domains_count == 120
    assert profile_part.total_backlinks_count == 4500
    assert profile_part.dofollow_ratio is None
    assert profile_part.toxicity_score is None
    assert profile_part.new_backlinks_30d is None


@pytest.mark.asyncio
async def test_seo_orchestrator_connector_runners_truthful_unconnected_state(tmp_path):
    from app.seo.audit.orchestrator import SEOAuditOrchestrator
    from app.seo.audit.orchestration.execution_state import AuditConfiguration, AuditMode
    from app.connectors.seo_connector_manager import ConnectorManager

    db_file = str(tmp_path / "test_seo_orch.db")
    mgr = ConnectorManager(db_path=db_file)
    cfg = AuditConfiguration(
        target_url="https://example.org/",
        mode=AuditMode.QUICK,
        org_id="test_org",
        workspace_id="test_ws",
    )
    orch = SEOAuditOrchestrator(
        audit_id="audit_subphase2_1_test",
        domain="example.org",
        config=cfg,
        db_path=db_file,
        connector_manager=mgr,
    )

    # Execute connector runner for google_search_console
    gsc_runner = orch.executor.task_runners.get("agent_search_console")
    assert gsc_runner is not None

    res = await gsc_runner({})
    assert res["status"] in ("NOT_CONFIGURED", "NOT_CONNECTED")
    assert res["data_state"] == "NOT_CONNECTED"
    assert res["findings"] == []

"""
Test suite validating the consolidated modular monolith SEO domain package: `app.seo`.
"""
import pytest
from app.domain.pillar import PillarId
from app.pillars import get_pillar
from app.seo import (
    SeoPillar,
    SEO_SPECIALISTS,
    build_seo_agents,
    TechnicalSeoAgent,
    ContentSeoAgent,
    InternalLinkingAgent,
    StructuredDataAgent,
    PerformanceAgent,
    SpecializedSeoAgent,
    analyze_canonicals,
    analyze_meta_rollup,
    analyze_heading_hierarchy,
    analyze_media_assets,
    analyze_link_depth_and_orphans,
    analyze_schema_rich_results,
    analyze_local_seo,
    analyze_international_seo,
    analyze_topical_authority,
    analyze_ecommerce_seo,
    analyze_serp_appearance,
    analyze_rendering_disparity,
    probe_host_and_redirects,
    analyze_http_statuses,
    CompleteSeoReportGenerator,
    seo_report_generator,
    render_seo_audit_book,
    seo_audit_book_renderer,
    SEOAuditOrchestrator,
    execute_audit_pipeline,
)
from app.seo.agents import (
    TechnicalSeoAgent as DirectTech,
    ContentSeoAgent as DirectContent,
)
from app.seo.analyzers import (
    CanonicalAuditor,
    CanonicalRedirectConsistencyAnalyzer,
    SitemapOrphanAnalyzer,
)
from app.seo.reporting import (
    SeoPrintReportRenderer,
    SEOReportBuilder,
)
from app.seo.audit import (
    AuditDAG,
    ScoreEngine,
    SEOScorecard,
    AgentOutput,
    FindingContract,
)


def test_seo_domain_pillar_resolution():
    pillar = get_pillar(PillarId.SEO)
    assert isinstance(pillar, SeoPillar)
    assert pillar.pillar_id == PillarId.SEO
    assert "TECHNICAL_SEO" in pillar.domains


def test_seo_specialist_agents_pool():
    agents = build_seo_agents(model_router=None)
    assert len(agents) == 6
    assert set(agents.keys()) == {
        "technical_seo",
        "content_seo",
        "internal_linking",
        "structured_data",
        "performance",
        "specialized_seo",
    }
    assert TechnicalSeoAgent is DirectTech
    assert ContentSeoAgent is DirectContent


def test_seo_analyzers_available():
    assert callable(analyze_canonicals)
    assert callable(analyze_meta_rollup)
    assert callable(analyze_heading_hierarchy)
    assert callable(analyze_media_assets)
    assert callable(analyze_schema_rich_results)
    assert callable(analyze_local_seo)
    assert callable(analyze_international_seo)
    assert callable(analyze_topical_authority)
    assert callable(analyze_ecommerce_seo)
    assert callable(analyze_serp_appearance)
    assert callable(analyze_rendering_disparity)
    assert callable(probe_host_and_redirects)
    assert callable(analyze_http_statuses)
    assert CanonicalAuditor is not None
    assert CanonicalRedirectConsistencyAnalyzer is not None
    assert SitemapOrphanAnalyzer is not None


def test_seo_reporting_interfaces():
    assert isinstance(seo_report_generator, CompleteSeoReportGenerator)
    assert callable(render_seo_audit_book)
    assert seo_audit_book_renderer is not None
    assert SeoPrintReportRenderer is not None
    assert SEOReportBuilder is not None


def test_seo_audit_engine_interfaces():
    dag = AuditDAG()
    assert len(dag.nodes) >= 30
    score_engine = ScoreEngine()
    assert callable(score_engine.calculate_overall_score)
    orchestrator = SEOAuditOrchestrator(audit_id="test_aud", domain="example.com")
    assert orchestrator.audit_id == "test_aud"

"""
Unit and integration tests for Phase 2: Evidence Graph & LLM Fleet Pruning.
Validates:
1. Typed EvidenceRef contract and Evidence.to_ref() binding.
2. CanonicalRedirectConsistencyAnalyzer (loops, excessive hops, cross-domain bounces, canonical mismatches).
3. SitemapOrphanAnalyzer (sitemap orphan detection and reporting).
4. EvidenceCoverageCalculator (observability completeness and transparent un-connected connectors).
5. Pruned Reasoners (Technical, GEO/AEO, CRO/Experience) + CrossAnalyst.
6. CriticAgent adversarial gatekeeper (zero-hallucination rejection of unbacked claims).
7. AgentPool.execute_streamlined_fleet execution pipeline.
"""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from app.evidence.models import Evidence, EvidenceRef
from app.domain.models import (
    CrawlManifest,
    PageEvidence,
    Finding,
    FindingEvidence,
    Claim,
)
from app.domain.enums import Category, Severity, RubricConfidence
from app.analyzers.canonical_redirect_consistency import CanonicalRedirectConsistencyAnalyzer
from app.analyzers.sitemap_orphan_analyzer import SitemapOrphanAnalyzer
from app.evidence.coverage import EvidenceCoverageCalculator, VectorObservationStatus
from app.agents.runtime.reasoners import (
    TechnicalReasonerAgent,
    GeoAeoReasonerAgent,
    CroExperienceReasonerAgent,
    CrossAnalystAgent,
    CriticAgent,
    SynthesizerAgent,
)
from app.orchestration.agent_pool import AgentPool
from app.cognition.blackboard import CognitiveBlackboard


# ------------------------------------------------------------------------------
# 1. EvidenceRef Contract Tests
# ------------------------------------------------------------------------------
def test_evidence_ref_contract_and_immutability():
    ref = EvidenceRef(
        source_type="crawl",
        source_id="ev_001",
        evidence_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90",
        url="https://example.com/",
        selector="link[rel=canonical]",
        snippet="<link rel='canonical' href='https://example.com/'>",
    )
    assert ref.source_type == "crawl"
    assert ref.source_id == "ev_001"
    assert ref.methodology_version == "dristik_v2.1"
    assert ref.url == "https://example.com/"

    # Immutability check (frozen Pydantic model)
    with pytest.raises(Exception):
        ref.source_type = "external"


def test_evidence_to_ref_conversion():
    ev = Evidence(
        id="ev_dom_title",
        source_type="dom",
        url="https://example.com/",
        selector="h1",
        text="Enterprise Intelligence Platform",
        analyzer="dom_analyzer",
        hash="11223344556677889900aabbccddeeff",
    )
    ref = ev.to_ref()
    assert isinstance(ref, EvidenceRef)
    assert ref.source_type == "crawl"
    assert ref.source_id == "ev_dom_title"
    assert ref.evidence_hash == "11223344556677889900aabbccddeeff"
    assert ref.selector == "h1"
    assert ref.snippet == "Enterprise Intelligence Platform"


def test_finding_and_claim_evidence_ref_attachment():
    ref = EvidenceRef(
        source_type="measured",
        source_id="ttfb_test",
        evidence_hash="fedcba9876543210fedcba9876543210",
        url="https://example.com/slow",
    )
    finding = Finding(
        finding_id="f_test_01",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="High Server Latency",
        description="TTFB exceeds 800ms threshold",
        recommendation="Optimize database",
        evidence_refs=[ref.source_id],
        evidence_ref_objects=[ref],
    )
    assert len(finding.evidence_ref_objects) == 1
    assert finding.evidence_ref_objects[0].source_id == "ttfb_test"

    claim = Claim(
        id="c_test_01",
        agent_id="test_agent",
        statement="Page TTFB is 950ms",
        category=Category.TECHNICAL_SEO,
        evidence_refs=[ref.source_id],
        evidence_ref_objects=[ref],
    )
    assert len(claim.evidence_ref_objects) == 1
    assert claim.evidence_ref_objects[0].evidence_hash == "fedcba9876543210fedcba9876543210"


# ------------------------------------------------------------------------------
# 2. Canonical & Redirect Consistency Engine Tests
# ------------------------------------------------------------------------------
def test_canonical_redirect_loop_detection():
    analyzer = CanonicalRedirectConsistencyAnalyzer()
    manifest = CrawlManifest(
        redirect_chains=[
            {
                "initial_url": "https://example.com/loop-start",
                "final_url": "https://example.com/loop-a",
                "hop_count": 3,
                "hops": [
                    {"source": "https://example.com/loop-start", "destination": "https://example.com/loop-a", "status_code": 301},
                    {"source": "https://example.com/loop-a", "destination": "https://example.com/loop-b", "status_code": 302},
                    {"source": "https://example.com/loop-b", "destination": "https://example.com/loop-a", "status_code": 301},
                ]
            }
        ],
        pages=[]
    )
    res = analyzer.analyze(manifest)
    summary = res["summary"]
    findings = res["findings"]

    assert summary["redirect_loops"] == 1
    loop_findings = [f for f in findings if "Redirect Loop" in f.title]
    assert len(loop_findings) == 1
    assert loop_findings[0].severity == Severity.CRITICAL
    assert len(loop_findings[0].evidence_ref_objects) == 1
    assert loop_findings[0].evidence_ref_objects[0].source_type == "crawl"


def test_canonical_excessive_hops_and_cross_domain_bounce():
    analyzer = CanonicalRedirectConsistencyAnalyzer()
    manifest = CrawlManifest(
        redirect_chains=[
            {
                "initial_url": "http://example.com/a",
                "final_url": "https://example.com/d",
                "hop_count": 3,
                "hops": [
                    {"source": "http://example.com/a", "destination": "https://example.com/b", "status_code": 301},
                    {"source": "https://example.com/b", "destination": "https://thirdparty.com/c", "status_code": 302},
                    {"source": "https://thirdparty.com/c", "destination": "https://example.com/d", "status_code": 301},
                ]
            }
        ],
        pages=[]
    )
    res = analyzer.analyze(manifest)
    summary = res["summary"]
    assert summary["excessive_chains"] == 1
    assert summary["cross_domain_bounces"] == 1

    titles = [f.title for f in res["findings"]]
    assert any("Excessive Redirect Chain" in t for t in titles)
    assert any("Cross-Domain Redirect Bounce" in t for t in titles)


def test_redirect_to_non_canonical_target_and_relative_canonical():
    analyzer = CanonicalRedirectConsistencyAnalyzer()
    landing_page = PageEvidence(
        url="https://example.com/landing",
        canonical_url="https://example.com/canonical-master",
    )
    relative_canon_page = PageEvidence(
        url="https://example.com/bad-canonical",
        canonical_url="/bad-canonical",  # Relative!
    )
    manifest = CrawlManifest(
        redirect_chains=[
            {
                "initial_url": "https://example.com/old-campaign",
                "final_url": "https://example.com/landing",
                "hop_count": 1,
                "hops": [
                    {"source": "https://example.com/old-campaign", "destination": "https://example.com/landing", "status_code": 301}
                ]
            }
        ],
        pages=[landing_page, relative_canon_page]
    )
    res = analyzer.analyze(manifest)
    summary = res["summary"]
    assert summary["non_canonical_redirect_targets"] == 1

    titles = [f.title for f in res["findings"]]
    assert any("Redirect Chain Ends on Non-Canonical URL" in t for t in titles)
    assert any("Relative or Malformed Canonical URL" in t for t in titles)


# ------------------------------------------------------------------------------
# 3. Sitemap Orphan Reporting Tests
# ------------------------------------------------------------------------------
def test_sitemap_orphan_analyzer():
    analyzer = SitemapOrphanAnalyzer()
    manifest = CrawlManifest(
        sitemap_urls=[
            "https://example.com/",
            "https://example.com/about",
            "https://example.com/orphaned-landing-1",
            "https://example.com/orphaned-landing-2",
        ],
        orphan_urls=[
            "https://example.com/orphaned-landing-1",
            "https://example.com/orphaned-landing-2",
        ]
    )
    res = analyzer.analyze(manifest)
    assert res["summary"]["orphan_urls_count"] == 2
    assert res["summary"]["sitemap_urls_count"] == 4
    assert res["summary"]["orphan_ratio"] == 0.5
    assert len(res["findings"]) == 1

    f = res["findings"][0]
    assert "Orphan Page(s) Found in XML Sitemap" in f.title
    assert f.severity == Severity.HIGH  # 50% is > 15% threshold
    assert len(f.evidence_ref_objects) == 1
    assert f.evidence_ref_objects[0].source_type == "crawl"


# ------------------------------------------------------------------------------
# 4. Evidence Coverage Metric Tests
# ------------------------------------------------------------------------------
def test_evidence_coverage_calculator():
    calc = EvidenceCoverageCalculator()
    page = PageEvidence(
        url="https://example.com/",
        title="Example Enterprise",
        h1=["Modern Data Platform"],
        ttfb_ms=210.0,
        status_code=200,
        canonical_url="https://example.com/",
        viewport="width=device-width, initial-scale=1.0",
        schema_types=["Organization", "WebSite"],
        image_assets=[{"src": "/hero.png", "width": 1200, "height": 600, "cls_risk": False}],
        call_to_actions=["Get Started"],
        word_count=450,
    )
    manifest = CrawlManifest(
        domain="example.com",
        pages=[page],
        redirect_chains=[],
        robots_txt_found=True,
        sitemap_found=True,
    )
    rep = calc.calculate_coverage("run_test_cov", manifest, [page])

    assert rep.overall_coverage_pct > 80.0
    assert rep.pillars["TECHNICAL"].coverage_pct == 100.0
    assert rep.pillars["GEO_AEO"].coverage_pct >= 80.0
    assert rep.pillars["CRO_EXPERIENCE"].coverage_pct >= 80.0

    # Ensure un-connected external connectors are honestly flagged as NOT_CONNECTED
    assert rep.external_connectors["google_search_console"]["status"] == VectorObservationStatus.NOT_CONNECTED.value
    assert rep.external_connectors["google_analytics_4"]["status"] == VectorObservationStatus.NOT_CONNECTED.value
    assert rep.external_connectors["crux_origin_field_data"]["status"] == VectorObservationStatus.NOT_CONNECTED.value


# ------------------------------------------------------------------------------
# 5. Pruned Reasoners & Critic Agent Tests
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_specialist_reasoners_technical_geo_cro():
    tech_agent = TechnicalReasonerAgent()
    geo_agent = GeoAeoReasonerAgent()
    cro_agent = CroExperienceReasonerAgent()

    slow_page = PageEvidence(
        url="https://example.com/pricing",
        ttfb_ms=1150.0,  # High TTFB
        image_assets=[{"src": "/banner.jpg", "cls_risk": True}],  # Missing dimensions
        canonical_url="https://example.com/pricing",
        h1=[],  # Missing H1
        schema_types=[],  # Missing Org schema
        viewport=None,  # Missing mobile viewport!
        word_count=50,
    )
    manifest = CrawlManifest(
        domain="example.com",
        pages=[slow_page],
        redirect_chains=[],
    )

    tech_findings = await tech_agent.reason(manifest, [slow_page])
    geo_findings = await geo_agent.reason(manifest, [slow_page])
    cro_findings = await cro_agent.reason(manifest, [slow_page])

    # Check Technical findings
    tech_titles = [f.title for f in tech_findings]
    assert any("Slow Server Response Time" in t for t in tech_titles)
    assert any("Image(s) Missing Explicit Dimensions" in t for t in tech_titles)

    # Check GEO findings
    geo_titles = [f.title for f in geo_findings]
    assert any("Missing Organization Schema" in t for t in geo_titles)
    assert any("Missing Primary <h1>" in t for t in geo_titles)

    # Check CRO findings
    cro_titles = [f.title for f in cro_findings]
    assert any("Missing Mobile Viewport" in t for t in cro_titles)


@pytest.mark.asyncio
async def test_cross_analyst_and_critic_gate():
    cross_analyst = CrossAnalystAgent()
    critic = CriticAgent()
    synthesizer = SynthesizerAgent()

    ref1 = EvidenceRef(source_type="crawl", source_id="r1", evidence_hash="1234567890abcdef1234567890abcdef")
    ref2 = EvidenceRef(source_type="crawl", source_id="r2", evidence_hash="abcdef1234567890abcdef1234567890")

    grounded_f1 = Finding(
        finding_id="f1",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Slow Server Response Time: TTFB 1200ms",
        description="High server response delay",
        recommendation="Enable CDN",
        evidence_refs=[ref1.source_id],
        evidence_ref_objects=[ref1],
    )
    grounded_f2 = Finding(
        finding_id="f2",
        category=Category.UX_CONVERSION,
        severity=Severity.HIGH,
        title="High Form Field Friction (9 Fields)",
        description="Too many inputs",
        recommendation="Trim inputs",
        evidence_refs=[ref2.source_id],
        evidence_ref_objects=[ref2],
    )

    # Synthesize cross-pillar synergy
    manifest = CrawlManifest(domain="example.com")
    cross_findings = await cross_analyst.analyze([grounded_f1, grounded_f2], manifest)
    assert len(cross_findings) == 1
    assert "Compounded Conversion Barrier" in cross_findings[0].title

    # Injected fake finding without EvidenceRef
    fake_finding = Finding(
        finding_id="fake_01",
        category=Category.CONTENT,
        severity=Severity.CRITICAL,
        title="Hallucinated Finding with Zero Evidence",
        description="An LLM invented a finding without evidence",
        recommendation="Do something impossible",
        evidence_refs=[],
        evidence_ref_objects=[],
    )

    # Critic Audit
    audit_res = critic.audit_findings([grounded_f1, grounded_f2, cross_findings[0], fake_finding])
    assert len(audit_res["verified"]) == 3
    assert len(audit_res["rejected"]) == 1
    assert audit_res["rejected"][0].finding_id == "fake_01"
    assert audit_res["rejected"][0].held_from_executive is True
    assert audit_res["rejected"][0].confidence_rubric == RubricConfidence.GUESSING

    # Synthesizer order
    final = synthesizer.synthesize(audit_res["verified"])
    assert len(final) == 3
    # Ensure findings are sorted by priority and severity
    assert final[0].priority >= final[1].priority


# ------------------------------------------------------------------------------
# 6. Streamlined Fleet in AgentPool Tests
# ------------------------------------------------------------------------------
class _DummyRouter:
    pass


@pytest.mark.asyncio
async def test_agent_pool_streamlined_fleet_execution():
    pool = AgentPool(_DummyRouter())
    bb = CognitiveBlackboard("run_fleet_test", "https://example.com")

    page = PageEvidence(
        url="https://example.com/",
        title="Example Enterprise",
        h1=["Enterprise AI Platform"],
        word_count=350,
        canonical_url="https://example.com/",
        viewport="width=device-width, initial-scale=1.0",
        schema_types=["WebSite"],  # missing Organization
        ttfb_ms=250.0,
        call_to_actions=["Request Demo"],
    )
    manifest = CrawlManifest(
        domain="example.com",
        base_url="https://example.com",
        pages=[page],
        redirect_chains=[],
        sitemap_urls=["https://example.com/", "https://example.com/orphan-doc"],
        orphan_urls=["https://example.com/orphan-doc"],
        sitemap_found=True,
        robots_txt_found=True,
    )
    bb.crawl_manifest = manifest
    bb.pages = [page]

    summary = await pool.execute_streamlined_fleet(bb)

    assert summary["mode"] == "streamlined_fleet"
    assert summary["specialist_reasoners"] == 3
    assert summary["critic_verified"] > 0
    assert summary["final_findings_count"] > 0
    assert summary["overall_evidence_coverage_pct"] > 75.0

    # Ensure findings were saved to blackboard and claims registered
    assert len(bb.findings) == summary["final_findings_count"]
    registered_claims = bb.claim_registry.get_all()
    assert len(registered_claims) >= len(bb.findings)
    assert "evidence_coverage" in bb.blackboard_state

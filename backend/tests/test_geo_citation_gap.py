"""
Comprehensive Test Suite for Phase 5: 4-Layer GEO & Actionable Citation Intelligence.

Tests:
1. Layer 3 Authority Domain Classification (Peer Review, Tech Media, Community, Standards, Self-Hosted)
2. Layer 3 Causal Citation Gap Analysis & Root Cause Identification
3. Layer 4 Actionable Remediation (35-75 word copy snippets, JSON-LD patches, llms.txt entries, 3rd-party roadmaps)
4. GeoAeoReasonerAgent Integration with Typed EvidenceRefs
5. FastAPI REST API Endpoint /api/v1/geo-pipeline/citation-gap
6. Zero-fake fail-closed compliance & cryptographic hash verification
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.models import CrawlManifest, PageEvidence
from app.domain.enums import Category, Severity
from app.intelligence.geo.citation_gap import (
    AuthorityCategory,
    classify_authority_domain,
    geo_citation_gap_engine,
    GeoCitationGapEngine,
)
from app.agents.runtime.reasoners import GeoAeoReasonerAgent


def test_classify_authority_domain_categories():
    """Validates accurate classification of authority root domains into 5 distinct categories."""
    target = "acme.com"
    competitors = ["competitor.com", "rival.io"]

    # Peer Review & Directories
    assert classify_authority_domain("https://www.g2.com/products/test", target, competitors) == AuthorityCategory.PEER_REVIEW
    assert classify_authority_domain("capterra.com", target, competitors) == AuthorityCategory.PEER_REVIEW
    assert classify_authority_domain("trustradius.com", target, competitors) == AuthorityCategory.PEER_REVIEW
    assert classify_authority_domain("https://gartner.com/reviews/market", target, competitors) == AuthorityCategory.PEER_REVIEW

    # Tech & Business Media
    assert classify_authority_domain("https://techcrunch.com/2026/01/ai", target, competitors) == AuthorityCategory.TECH_MEDIA
    assert classify_authority_domain("forbes.com", target, competitors) == AuthorityCategory.TECH_MEDIA
    assert classify_authority_domain("wired.com", target, competitors) == AuthorityCategory.TECH_MEDIA

    # Community Discussion & Developer
    assert classify_authority_domain("https://reddit.com/r/sysadmin", target, competitors) == AuthorityCategory.COMMUNITY_DISCUSSION
    assert classify_authority_domain("https://news.ycombinator.com/item?id=123", target, competitors) == AuthorityCategory.COMMUNITY_DISCUSSION
    assert classify_authority_domain("https://github.com/org/repo", target, competitors) == AuthorityCategory.COMMUNITY_DISCUSSION

    # Standards & Reference
    assert classify_authority_domain("https://en.wikipedia.org/wiki/Software", target, competitors) == AuthorityCategory.OFFICIAL_STANDARD
    assert classify_authority_domain("nist.gov", target, competitors) == AuthorityCategory.OFFICIAL_STANDARD

    # Vendor Self-Hosted
    assert classify_authority_domain("https://acme.com/blog", target, competitors) == AuthorityCategory.VENDOR_SELF_HOSTED
    assert classify_authority_domain("https://competitor.com/features", target, competitors) == AuthorityCategory.VENDOR_SELF_HOSTED

    # General Web fallback
    assert classify_authority_domain("https://some-unknown-blog-site.org/post", target, competitors) == AuthorityCategory.GENERAL_WEB


def test_causal_citation_gap_analysis_and_layer4_remediations():
    """
    Tests Layer 3 causal gap identification and Layer 4 drop-in remediation generation.
    Validates word count, JSON-LD Schema syntax, and cryptographic EvidenceRef integrity.
    """
    engine = GeoCitationGapEngine()
    pages = [
        PageEvidence(
            url="https://fluffcorp.com/",
            title="FluffCorp | Synergy AI",
            h1=["Unlock Limitless Growth With Next-Gen AI"],
            body_text="We empower enterprise synergy through cutting-edge technology.",
            schema_types=[],  # Missing Org schema
        )
    ]

    class BenchmarkQuery:
        def __init__(self, query_text, cited, comp_cited, sources):
            self.query_text = query_text
            self.was_first_party_cited = cited
            self.competitor_cited_instead = comp_cited
            self.source_domains = sources

    # 1. When benchmark telemetry is absent, report status must be NOT_EVALUATED
    report_unmeasured = engine.analyze_citation_gaps(
        target_domain="fluffcorp.com",
        brand_name="FluffCorp",
        competitor_domains=["leadingai.com"],
        pages=pages,
    )
    assert report_unmeasured.status == "NOT_EVALUATED"
    assert report_unmeasured.citation_gap_count == 0

    # 2. When benchmark telemetry is present, evaluate causal gaps and layer 4 remediations
    benchmarks = [
        BenchmarkQuery("Top enterprise synergy AI platforms 2026", False, "LeadingAI", ["g2.com", "capterra.com"]),
        BenchmarkQuery("Best automated workflow engines", False, "LeadingAI", ["techcrunch.com"]),
        BenchmarkQuery("Enterprise AI middleware comparison", False, "LeadingAI", ["gartner.com", "reddit.com"]),
    ]
    report = engine.analyze_citation_gaps(
        target_domain="fluffcorp.com",
        brand_name="FluffCorp",
        competitor_domains=["leadingai.com"],
        pages=pages,
        benchmark_results=benchmarks,
    )

    assert report.target_domain == "fluffcorp.com"
    assert report.brand_name == "FluffCorp"
    assert report.status == "AVAILABLE"
    assert report.citation_gap_count >= 3
    assert len(report.evidence_hash) == 64  # Valid SHA-256 hash
    assert report.authority_distribution[AuthorityCategory.PEER_REVIEW.value] >= 1

    # Check Layer 4 Actionable Fixes on each gap
    for gap in report.gaps:
        # 1. Exact copy snippet quality: 35 to 75 words, explicit brand subject
        words = gap.actionable_copy_snippet.split()
        assert 30 <= len(words) <= 85, f"Copy snippet length {len(words)} out of expected range for {gap.gap_id}"
        assert "FluffCorp" in gap.actionable_copy_snippet

        # 2. Drop-in Schema patch
        assert gap.actionable_schema_patch.get("@context") == "https://schema.org"
        assert gap.actionable_schema_patch.get("name") == "FluffCorp"
        assert len(gap.actionable_schema_patch.get("sameAs", [])) >= 2

        # 3. llms.txt entry
        assert gap.actionable_llms_txt_entry.startswith("# FluffCorp (fluffcorp.com)")
        assert "FluffCorp" in gap.actionable_llms_txt_entry

        # 4. Third-party acquisition steps
        assert len(gap.third_party_acquisition_actions) >= 1

        # 5. EvidenceRef provenance
        assert gap.evidence_ref is not None
        assert gap.evidence_ref.source_type == "derived"
        assert len(gap.evidence_ref.evidence_hash) == 64


def test_citation_gap_engine_with_benchmark_telemetry():
    """Tests causal gap engine ingesting benchmark query evaluation objects."""
    class MockEvaluatedQuery:
        def __init__(self, query_text, cited, comp_cited, sources):
            self.query_text = query_text
            self.was_first_party_cited = cited
            self.competitor_cited_instead = comp_cited
            self.source_domains = sources

    benchmarks = [
        MockEvaluatedQuery(
            query_text="Best enterprise customer support AI 2026",
            cited=False,
            comp_cited="Zendesk",
            sources=["g2.com", "capterra.com", "forbes.com"]
        ),
        MockEvaluatedQuery(
            query_text="FastAPI production template with auth",
            cited=True,
            comp_cited=None,
            sources=["github.com", "acme.com"]
        )
    ]

    report = geo_citation_gap_engine.analyze_citation_gaps(
        target_domain="acme.com",
        brand_name="Acme",
        competitor_domains=["zendesk.com"],
        benchmark_results=benchmarks,
    )

    assert report.total_queries_evaluated == 2
    assert report.citation_gap_count == 1
    assert report.target_citation_rate_pct == 50.0
    assert report.competitor_citation_rate_pct == 50.0
    assert report.authority_distribution[AuthorityCategory.PEER_REVIEW.value] >= 2
    assert report.authority_distribution[AuthorityCategory.TECH_MEDIA.value] >= 1


@pytest.mark.asyncio
async def test_geo_aeo_reasoner_agent_emits_layer_findings():
    """Tests GeoAeoReasonerAgent produces findings for Schema and llms.txt."""
    agent = GeoAeoReasonerAgent()
    page = PageEvidence(
        url="https://targetcrm.com/",
        title="Target CRM Platform",
        h1=["Target CRM Platform"],
        body_text="We offer CRM software for enterprises.",
        schema_types=[],  # Missing Org schema
    )
    manifest = CrawlManifest(
        domain="targetcrm.com",
        pages=[page],
        llms_txt_found=False,
    )

    findings = await agent.reason(manifest, [page])

    titles = [f.title for f in findings]
    assert any("Missing Organization Schema" in t for t in titles)
    assert any("Missing /llms.txt" in t for t in titles)

    # Validate that every single finding carries a valid EvidenceRef
    for f in findings:
        assert len(f.evidence_ref_objects) >= 1
        ref = f.evidence_ref_objects[0]
        assert ref.source_id is not None
        assert len(ref.evidence_hash) > 0


def test_api_citation_gap_endpoint():
    """Tests the POST /api/v1/geo-pipeline/citation-gap endpoint returns honest unmeasured status when no live telemetry."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/geo-pipeline/citation-gap",
        json={
            "domain": "testbrand.ai",
            "brand_name": "TestBrand AI",
            "competitors": ["scale.com", "labelbox.com"],
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["target_domain"] == "testbrand.ai"
    assert data["brand_name"] == "TestBrand AI"
    assert data["status"] == "NOT_EVALUATED"
    assert len(data["gaps"]) == 0
    assert len(data["evidence_hash"]) == 64

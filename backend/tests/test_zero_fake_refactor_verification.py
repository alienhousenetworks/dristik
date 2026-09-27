"""
Dristik AI - Zero Mock / Zero Fake / Zero Hardcoded Refactor Verification Test Suite
Mandatory 7 Verification Tests as specified in Section 25 of the Refactor Plan.

1. Test 1: Empty Evidence -> Finding Rejected / Not Evaluated
2. Test 2: TTFB High Without Cache Headers -> Does NOT Claim CDN is Root Cause
3. Test 3: Unavailable Connector -> Returns NOT_CONNECTED / UNAVAILABLE
4. Test 4: Contradictory Evidence -> CONTRADICTED / REJECTED
5. Test 5: Real Measurement -> Valid Finding with Traceable EvidenceRef
6. Test 6: Recommendation Traceability -> Finding -> Claim -> Evidence -> Source
7. Test 7: Fabricated Evidence Detection -> Unresolvable EvidenceRef Rejected
"""
import pytest
from app.domain.models import Finding, FindingEvidence, Claim, PageEvidence, CrawlManifest
from app.domain.enums import (
    Category,
    Severity,
    ClaimType,
    VerificationStatus,
    RubricConfidence,
    ConnectorHealthStatus,
)
from app.evidence.models import Evidence, EvidenceRef, DataAvailabilityStatus
from app.evidence.store import EvidenceStore
from app.orchestration.integrity_gate import EvidenceIntegrityValidator
from app.agents.runtime.reasoners import (
    TechnicalReasonerAgent,
    CriticAgent,
    GeoAeoReasonerAgent,
    CroExperienceReasonerAgent,
)
from app.crawl.embeddings import EmbeddingService
from app.intelligence.competitive.semantic_gap import SemanticGapEngine
from app.intelligence.geo.citation_gap import GeoCitationGapEngine
from app.connectors.google.connector import GoogleSearchConsoleConnector
from app.connectors.base.models import ConnectorCredentials


# ------------------------------------------------------------------------------
# Test 1: Empty Evidence -> Finding Rejected / Not Evaluated
# ------------------------------------------------------------------------------
def test_1_empty_evidence_rejected_by_critic_and_gate():
    """Unbacked findings with zero evidence are rejected, never manufactured."""
    critic = CriticAgent()
    gate = EvidenceIntegrityValidator()
    store = EvidenceStore("test_run_01")

    # Finding with 0 evidence
    unbacked_finding = Finding(
        finding_id="f_hallucinated_01",
        category=Category.CONTENT,
        severity=Severity.HIGH,
        title="Unbacked Claim: Ineffective Value Proposition",
        description="Emitted without DOM or crawl evidence.",
        recommendation="Rewrite website copy completely.",
        evidence_refs=[],
        evidence_ref_objects=[],
        evidence=[],
    )

    # Critic audit must reject it
    audit_res = critic.audit_findings([unbacked_finding], evidence_store=store)
    assert len(audit_res["rejected"]) == 1
    rejected_f = audit_res["rejected"][0]
    assert rejected_f.held_from_executive is True
    assert rejected_f.verification_status == VerificationStatus.REJECTED

    # Claim with 0 evidence inspected by IntegrityGate
    unbacked_claim = Claim(
        id="cl_unbacked_01",
        agent_id="test_agent",
        statement="Domain suffers from severe value proposition deficit",
        claim_type=ClaimType.FACT,
        category=Category.CONTENT,
        severity=Severity.HIGH,
        evidence_refs=[],
    )

    validation_result = gate.validate_claims_and_evidence([unbacked_claim], store)
    assert validation_result.is_valid is False
    assert unbacked_claim.verification_status == VerificationStatus.REJECTED
    assert unbacked_claim.held_from_executive is True
    assert unbacked_claim.confidence == 0.0


# ------------------------------------------------------------------------------
# Test 2: TTFB High Without Cache Headers -> Does NOT Claim CDN is Root Cause
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_2_high_ttfb_without_headers_does_not_assert_cdn_cause():
    """High latency without cache headers reports measured latency without asserting CDN cause."""
    tech_agent = TechnicalReasonerAgent()

    # Page with slow TTFB but no CDN / cache-control headers recorded
    page = PageEvidence(
        url="https://example.com/slow-endpoint",
        ttfb_ms=1450.0,
        headers={"content-type": "text/html"},  # No cf-cache-status, x-cache, or age header
        canonical_url="https://example.com/slow-endpoint",
    )
    manifest = CrawlManifest(domain="example.com", pages=[page])

    findings = await tech_agent.reason(manifest, [page])
    ttfb_findings = [f for f in findings if "Slow Server Response Time" in f.title]

    assert len(ttfb_findings) == 1
    f = ttfb_findings[0]

    # Must report observed latency accurately
    assert "1450" in f.title or "1450" in f.description

    # Must NOT claim CDN is the root cause when cache headers were not observed
    assert "CDN is the confirmed root cause" not in f.description
    assert "no CDN is present" not in f.description
    assert "CDN is missing" not in f.description


# ------------------------------------------------------------------------------
# Test 3: Unavailable Connector -> Returns NOT_CONNECTED / UNAVAILABLE
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_3_unavailable_connector_returns_honest_status_no_mock():
    """Offline services fail closed with UNAVAILABLE and never fabricate fake data."""
    from unittest.mock import patch
    from app.domain.enums import ConnectorType

    # 1. Semantic gap analyzer with disabled/unavailable embedding service
    gap_engine = SemanticGapEngine()
    with patch("app.crawl.embeddings.embedding_service.is_available", return_value=False):
        result = gap_engine.evaluate_intent_coverage(
            domain="example.com",
            queries=[{"query": "Acme software platform", "intent": "Commercial"}],
        )
        assert result["status"] == "UNAVAILABLE"
        assert result["overall_semantic_coverage_score"] is None
        assert "Neural embedding model unconfigured or unreachable" in result["reason"]

    # 2. GEO Citation Gap without live telemetry
    citation_engine = GeoCitationGapEngine()
    gap_report = citation_engine.analyze_citation_gaps(
        target_domain="offline-brand.com",
        brand_name="OfflineBrand",
        competitor_domains=["rival.com"],
        pages=[],
    )
    assert gap_report.status == "NOT_EVALUATED"
    assert gap_report.citation_gap_count == 0
    assert gap_report.gaps == []

    # 3. Search Console connector without credentials
    gsc = GoogleSearchConsoleConnector(ConnectorCredentials(provider=ConnectorType.GOOGLE_SEARCH_CONSOLE))
    health = await gsc.test_health()
    assert health.status in (ConnectorHealthStatus.UNAUTHORIZED, ConnectorHealthStatus.DISCONNECTED, ConnectorHealthStatus.ERROR)


# ------------------------------------------------------------------------------
# Test 4: Contradictory Evidence -> CONTRADICTED / REJECTED
# ------------------------------------------------------------------------------
def test_4_contradictory_evidence_marked_contradicted_and_held():
    """Claims with contradictory evidence or peer disputes are marked CONTRADICTED and held."""
    gate = EvidenceIntegrityValidator()
    store = EvidenceStore("test_run_04")

    ev = store.add_evidence(
        source_type="dom",
        analyzer="test_analyzer",
        url="https://example.com/",
        text="Enterprise B2B billing software",
    )

    contradicted_claim = Claim(
        id="cl_disputed_01",
        agent_id="agent_a",
        statement="Website is a B2C direct-to-consumer fashion boutique",
        claim_type=ClaimType.FACT,
        category=Category.COMPETITIVE,
        severity=Severity.HIGH,
        evidence_refs=[ev.id],
        contradicting_agents=["agent_b", "agent_c"],
        supporting_agents=["agent_a"],
    )

    validation_res = gate.validate_claims_and_evidence([contradicted_claim], store)
    assert contradicted_claim.verification_status == VerificationStatus.CONTRADICTED
    assert contradicted_claim.held_from_executive is True


# ------------------------------------------------------------------------------
# Test 5: Real Measurement -> Valid Finding with Traceable EvidenceRef
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_5_real_measurement_produces_fully_traceable_evidence_ref():
    """Real deterministic measurements produce valid findings with complete provenance."""
    cro_agent = CroExperienceReasonerAgent()

    # Real viewport deficiency on mobile
    page = PageEvidence(
        url="https://example.com/checkout",
        viewport=None,  # Missing mobile viewport
    )
    manifest = CrawlManifest(domain="example.com", pages=[page])

    findings = await cro_agent.reason(manifest, [page])
    viewport_findings = [f for f in findings if "Missing Mobile Viewport" in f.title]

    assert len(viewport_findings) == 1
    f = viewport_findings[0]

    assert len(f.evidence_ref_objects) >= 1
    ref = f.evidence_ref_objects[0]

    # Verify provenance contract
    assert ref.source_id.startswith("cro_missing_viewport_")
    assert ref.source_type == "crawl"
    assert ref.url == "https://example.com/checkout"
    assert ref.selector == "meta[name=viewport]"
    assert ref.collector_or_analyzer == "CroExperienceReasonerAgent.viewport_analyzer"
    assert len(ref.evidence_hash) >= 16


# ------------------------------------------------------------------------------
# Test 6: Recommendation Traceability -> Finding -> Claim -> Evidence -> Source
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_6_recommendation_traceability_chain():
    """Recommendations are traceable end-to-end back to observed evidence."""
    tech_agent = TechnicalReasonerAgent()

    page = PageEvidence(
        url="https://example.com/products",
        canonical_url="https://example.com/products",
        image_assets=[
            {"src": "/hero.png", "cls_risk": True},
            {"src": "/banner.png", "cls_risk": True},
        ],
    )
    manifest = CrawlManifest(domain="example.com", pages=[page])

    findings = await tech_agent.reason(manifest, [page])
    cls_findings = [f for f in findings if "Missing Explicit Dimensions" in f.title]
    assert len(cls_findings) >= 1

    f = cls_findings[0]
    assert f.recommendation is not None
    assert len(f.recommendation) > 10

    # Trace back to finding evidence
    assert len(f.evidence_refs) >= 1
    assert len(f.evidence_ref_objects) >= 1
    ref = f.evidence_ref_objects[0]

    assert ref.collector_or_analyzer == "TechnicalReasonerAgent.cls_analyzer"
    assert ref.url == "https://example.com/products"
    assert ref.snippet is not None
    assert ref.observed_value is not None


# ------------------------------------------------------------------------------
# Test 7: Fabricated Evidence Detection -> Unresolvable EvidenceRef Rejected
# ------------------------------------------------------------------------------
def test_7_fabricated_evidence_detected_and_rejected():
    """Claims with forged/unresolvable EvidenceRefs are detected and rejected by IntegrityGate and Critic."""
    gate = EvidenceIntegrityValidator()
    critic = CriticAgent()
    store = EvidenceStore("test_run_07")

    # Store only contains genuine_ev_01
    store.add_evidence(
        source_type="dom",
        analyzer="test_analyzer",
        url="https://example.com/",
        text="Genuine text",
    )

    # Claim citing a fabricated evidence ID
    forged_claim = Claim(
        id="cl_forged_01",
        agent_id="rogue_agent",
        statement="Critical vulnerability in payment pipeline",
        claim_type=ClaimType.FACT,
        category=Category.TECHNICAL_SEO,
        severity=Severity.CRITICAL,
        evidence_refs=["ev_fabricated_nonexistent_id_999"],
    )

    validation_result = gate.validate_claims_and_evidence([forged_claim], store)
    assert validation_result.is_valid is False
    assert validation_result.dangling_refs_removed == 1
    assert forged_claim.verification_status == VerificationStatus.REJECTED
    assert forged_claim.held_from_executive is True
    assert forged_claim.confidence == 0.0

    # Critic audit with unresolvable ref
    forged_finding = Finding(
        finding_id="f_forged_01",
        category=Category.TECHNICAL_SEO,
        severity=Severity.CRITICAL,
        title="Fabricated Security Finding",
        description="Has unresolvable evidence reference",
        recommendation="Fix nonexistent issue",
        evidence_refs=["ev_fabricated_nonexistent_id_999"],
    )
    audit_res = critic.audit_findings([forged_finding], evidence_store=store)
    assert len(audit_res["rejected"]) == 1
    assert audit_res["rejected"][0].held_from_executive is True
    assert audit_res["rejected"][0].verification_status == VerificationStatus.REJECTED

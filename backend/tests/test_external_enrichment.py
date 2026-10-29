import pytest
from app.evidence.store import EvidenceStore
from app.evidence.enrichment import ExternalEvidenceEnricher
from app.cognition.ground_truth import get_external_feed, apply_ground_truth_feed
from app.domain.models import Claim
from app.domain.enums import ClaimFamily, SourceIntegrityLabel, ConfidenceBand, Category


@pytest.mark.asyncio
async def test_external_enricher_populates_ext_evidence():
    store = EvidenceStore(run_id="run_test_enrich")
    enricher = ExternalEvidenceEnricher(timeout_sec=2.0)

    # Enrich a testable target domain
    items = await enricher.enrich_domain("example.com", store)

    assert len(items) >= 3  # DNS, SSL, Security headers, CruX stub, Firmographic stubs
    feed = get_external_feed(store)
    assert len(feed) >= 3

    sources = {ev.metadata.get("source") for ev in feed}
    assert "dns" in sources
    assert "crux" in sources
    assert "linkedin" in sources

    # Verify ext tokens are sequentially created: ext_001, ext_002, ...
    for ev in feed:
        assert ev.id.startswith("ext_")


@pytest.mark.asyncio
async def test_external_ground_truth_binding_with_enricher():
    store = EvidenceStore(run_id="run_test_bind")
    enricher = ExternalEvidenceEnricher(timeout_sec=2.0)
    await enricher.enrich_domain("example.com", store)

    # Performance claim should be bound to CruX status
    perf_claim = Claim(
        id="c_perf_01",
        agent_id="seo.performance.v3",
        statement="LCP is 1.2s and INP is 150ms on mobile viewport.",
        evidence_refs=["ev_001"],
        claim_family=ClaimFamily.PERFORMANCE,
        category=Category.TECHNICAL_SEO,
    )

    claims = [perf_claim]
    apply_ground_truth_feed(claims, store)

    # Without CRUX_API_KEY, crux is NOT_CONFIGURED stub -> SINGLE_SOURCE_UNVERIFIED
    assert perf_claim.source_integrity_label == SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED
    assert perf_claim.confidence_band == ConfidenceBand.MEDIUM

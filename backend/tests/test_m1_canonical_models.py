"""Unit tests for M1.1 Canonical Domain Models, EvidenceState, URL Registry, Finding Backfill & Contradiction Precision."""
from app.domain.enums import Category, EvidenceState, GeoDimensionKey, Severity
from app.domain.models import (
    CanonicalUrlEntry,
    CanonicalUrlRegistry,
    Contradiction,
    ContradictionReport,
    CoverageMetrics,
    CrawlInventory,
    Finding,
    FindingEvidence,
    PageEvidence,
    RemediationPatch,
    RootCauseLink,
    SubObservation,
    TtfbStats,
)


def test_evidence_state_normalization_and_empirical_verification():
    assert EvidenceState.EMPIRICALLY_VERIFIED.is_empirically_verified is True
    assert EvidenceState.SAMPLE_VERIFIED.is_empirically_verified is True
    assert EvidenceState.VERIFIED.is_empirically_verified is True
    assert EvidenceState.OBSERVED.is_empirically_verified is True
    assert EvidenceState.ACCOUNTED_FOR.is_empirically_verified is False
    assert EvidenceState.DATA_UNAVAILABLE.is_empirically_verified is False
    assert EvidenceState.NOT_TESTED.is_empirically_verified is False
    assert EvidenceState.ESTIMATED.is_empirically_verified is False

    assert EvidenceState.normalize("MEASURED") == EvidenceState.EMPIRICALLY_VERIFIED
    assert EvidenceState.normalize("SAMPLED") == EvidenceState.SAMPLE_VERIFIED
    assert EvidenceState.normalize("ACCOUNTED_FOR") == EvidenceState.ACCOUNTED_FOR
    assert EvidenceState.normalize("NOT_CONNECTED") == EvidenceState.DATA_UNAVAILABLE
    assert EvidenceState.normalize("NOT_CONFIGURED") == EvidenceState.NOT_TESTED


def test_crawl_inventory_coverage_never_truncates_nonzero_sample_to_zero():
    inv = CrawlInventory(
        discovered_total=504,
        eligible_total=504,
        analyzed_total=5,
        tested_pages=5,
    )
    assert inv.calculate_coverage() == 1.0

    small_inv = CrawlInventory(
        discovered_total=5000,
        eligible_total=5000,
        analyzed_total=1,
        tested_pages=1,
    )
    assert small_inv.calculate_coverage() == 0.1


def test_finding_backfills_affected_urls_and_counts_from_evidence():
    finding = Finding(
        finding_id="F-TEST-001",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Slow response and missing compression",
        evidence=[
            FindingEvidence(evidence_id="EV-1", url="https://perforacare.com/products/unwind-combo", value="36208ms"),
            FindingEvidence(evidence_id="EV-2", url="https://perforacare.com/products/mouthwash", value="no-br"),
            FindingEvidence(evidence_id="EV-3", url="https://perforacare.com/products/unwind-combo", value="duplicate"),
        ],
        detailed_observations=[
            SubObservation(observation_id="OBS-1", title="Sub", url="https://perforacare.com/products/whitening-strips")
        ],
    )
    assert finding.affected_urls == [
        "https://perforacare.com/products/unwind-combo",
        "https://perforacare.com/products/mouthwash",
        "https://perforacare.com/products/whitening-strips",
    ]
    assert finding.affected_url_count == 3
    assert finding.affected_sample_count == 3
    assert finding.scope_hit_count == 3
    assert "EV-1" in finding.evidence_ids
    assert "EV-2" in finding.evidence_refs


def test_contradiction_and_contradiction_report_precision_fields():
    c = Contradiction(
        id="CONTRA-01",
        claim_a_id="EV-A",
        claim_b_id="EV-B",
        question_text="Is Perfora mouthwash alcohol-free?",
        statement_a="100% Alcohol-Free Probiotic Mouthwash",
        statement_b="Contains denatured alcohol (5%) in legacy ingredient tab",
        source_url_a="https://perforacare.com/products/mouthwash",
        source_url_b="https://perforacare.com/pages/faq",
        evidence_id_a="EV-DOM-001",
        evidence_id_b="EV-DOM-002",
        disputed_fact="Alcohol content in Mouthwash formulation",
        description="Product hero states 100% alcohol-free while legacy FAQ mentions denatured alcohol.",
        resolution="Update FAQ ingredient table to match current alcohol-free formulation.",
    )
    assert c.question_text == "Is Perfora mouthwash alcohol-free?"
    assert c.statement_a == "100% Alcohol-Free Probiotic Mouthwash"
    assert c.statement_b == "Contains denatured alcohol (5%) in legacy ingredient tab"
    assert c.source_url_a == "https://perforacare.com/products/mouthwash"
    assert c.source_url_b == "https://perforacare.com/pages/faq"
    assert c.evidence_id_a == "EV-DOM-001"
    assert c.evidence_id_b == "EV-DOM-002"
    assert c.disputed_fact == "Alcohol content in Mouthwash formulation"
    assert c.conflict_explanation == c.description
    assert c.authoritative_correction == c.resolution

    cr = ContradictionReport(
        id="CR-01",
        contradiction_type="ingredient_conflict",
        declared_type="Alcohol-free",
        detected_type="Alcohol listed",
        reason="Conflicting ingredient claim across product and FAQ pages.",
        evidence=[
            FindingEvidence(evidence_id="EV-10", url="https://perforacare.com/products/mouthwash", value="Alcohol-free"),
            FindingEvidence(evidence_id="EV-11", url="https://perforacare.com/pages/faq", value="Alcohol listed"),
        ],
        authoritative_correction="Remove outdated FAQ line.",
    )
    assert cr.statement_a == "Alcohol-free"
    assert cr.statement_b == "Alcohol listed"
    assert cr.source_url_a == "https://perforacare.com/products/mouthwash"
    assert cr.source_url_b == "https://perforacare.com/pages/faq"
    assert cr.evidence_id_a == "EV-10"
    assert cr.evidence_id_b == "EV-11"
    assert cr.disputed_fact == "Ingredient Conflict"


def test_geo_dimension_keys_and_root_cause_link():
    assert GeoDimensionKey.STRUCTURED_DATA_QUALITY.value == "structured_data_quality"
    assert GeoDimensionKey.SOURCE_CORROBORATION.value == "source_corroboration"
    assert GeoDimensionKey.AI_CRAWLER_ACCESSIBILITY.value == "ai_crawler_accessibility"
    assert GeoDimensionKey.FACTUAL_CONSISTENCY.value == "factual_consistency"
    assert GeoDimensionKey.LIVE_AI_CITATIONS.value == "live_ai_citations"

    rc = RootCauseLink(
        root_cause_id="RC-MISSING-PRODUCT-SPEC",
        canonical_observation="Product pages omit structured ingredient & safety specifications.",
        primary_category=Category.ON_PAGE_SEO,
        affected_urls=["https://perforacare.com/products/mouthwash"],
        evidence_ids=["EV-101"],
        discipline_consequences={
            "SEO": "Reduces long-tail product specification query relevance.",
            "GEO": "Lowers factual grounding and entity attribute completeness.",
            "AEO": "Leaves ingredient & safety buyer questions unanswerable.",
        },
        finding_ids=["F-SEO-1", "F-GEO-1", "F-AEO-1"],
    )
    assert len(rc.discipline_consequences) == 3
    assert rc.affected_urls == ["https://perforacare.com/products/mouthwash"]

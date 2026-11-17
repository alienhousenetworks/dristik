"""
Milestone 3 Verification Test Suite:
P1 Intelligence, Taxonomy & Evidence Fidelity
Covers Issues 6, 7, 8, 10, 11, and 12.
"""
import pytest
from app.domain.enums import (
    EvidenceState,
    GeoDimensionKey,
    Category,
    Severity,
    BusinessIntent,
)
from app.domain.models import (
    BusinessProfile,
    PageEvidence,
    CrawlManifest,
    Contradiction,
    ContradictionReport,
    FindingEvidence,
    AuditScopeInfo,
)
from app.geo.readiness import evaluate_geo_readiness
from app.geo.citation_gap import GeoCitationGapEngine
from app.geo.dynamic_sandbox import validate_questions_against_business_context
from app.domain.evidence.contradiction_detector import ContradictionDetector
from app.seo.search_demand import build_search_demand
from app.connectors.crux.connector import CruxConnector


def test_issue_6_evidence_state_fidelity_accounted_for_vs_empirically_verified():
    """
    Issue 6: Distinguish 'evidence-accounted-for' from 'empirically-verified'.
    An audit accounts for all 457 checks, but only verified/sample_verified
    are empirical measurements; data_unavailable and not_tested are accounted-for deficits.
    """
    assert EvidenceState.EMPIRICALLY_VERIFIED.is_empirically_verified is True
    assert EvidenceState.SAMPLE_VERIFIED.is_empirically_verified is True
    assert EvidenceState.ACCOUNTED_FOR.is_empirically_verified is False
    assert EvidenceState.DATA_UNAVAILABLE.is_empirically_verified is False
    assert EvidenceState.NOT_TESTED.is_empirically_verified is False

    # Normalize aliases
    assert EvidenceState.normalize("empirically_verified") in (EvidenceState.EMPIRICALLY_VERIFIED, EvidenceState.VERIFIED)
    assert EvidenceState.normalize("verified") == EvidenceState.VERIFIED
    assert EvidenceState.normalize("sample_verified") == EvidenceState.SAMPLE_VERIFIED
    assert EvidenceState.normalize("unavailable") == EvidenceState.DATA_UNAVAILABLE

    # Perfora mock distribution: 4 verified, 385 sample verified, 64 unavailable, 4 not tested = 457
    distribution = {
        EvidenceState.EMPIRICALLY_VERIFIED: 4,
        EvidenceState.SAMPLE_VERIFIED: 385,
        EvidenceState.DATA_UNAVAILABLE: 64,
        EvidenceState.NOT_TESTED: 4,
    }
    total_accounted = sum(distribution.values())
    total_empirical = sum(cnt for state, cnt in distribution.items() if state.is_empirically_verified)
    total_deficits = sum(cnt for state, cnt in distribution.items() if not state.is_empirically_verified)

    assert total_accounted == 457
    assert total_empirical == 389
    assert total_deficits == 68
    assert total_empirical < total_accounted, "Empirically verified checks must strictly not equal total accounted checks when unavailable checks exist"


def test_issue_7_geo_readiness_separates_7_dimensions():
    """
    Issue 7: GEO readiness is separated into 7 distinct metrics:
    - Content extractability
    - Entity clarity
    - Structured data quality
    - Source corroboration
    - AI crawler accessibility
    - Factual consistency
    - Live AI citations
    """
    pages = [
        PageEvidence(
            url="https://perforacare.com/",
            status_code=200,
            title="Perfora Oral Care | Electric Toothbrushes, Mouthwash & Whitening",
            h1=["Clean Oral Care for India"],
            h2=["Smart Electric Toothbrush", "Probiotic Mouthwash", "Teeth Whitening Strips"],
            body_text=(
                "Perfora is an Indian clean oral care brand founded in 2021 by Jatan Bawa and Tushar Khurana. "
                "Our SLS-free mouthwash is priced at Rs 399 and smart sonic electric toothbrush at Rs 999. "
                "Products are clinically validated and toxin-free."
            ),
            schema_types=["Organization", "WebSite", "Product"],
            raw_schema=[{
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Smart Sonic Electric Toothbrush",
                "offers": {"@type": "Offer", "price": "999", "priceCurrency": "INR"},
            }],
        )
    ]
    manifest = CrawlManifest(
        base_url="https://perforacare.com",
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nAllow: /\nUser-agent: GPTBot\nAllow: /\n",
        sitemap_found=True,
    )
    profile = BusinessProfile(
        business_name="Perfora",
        primary_intent=BusinessIntent.ECOMMERCE,
        industry="Personal Care / D2C Oral Hygiene",
    )

    report = evaluate_geo_readiness(
        website_url="https://perforacare.com",
        pages=pages,
        manifest=manifest,
        profile=profile,
        visibility_measured=False,
        visibility_score=None,
    )

    dims = report.dimension_scores
    assert len(dims) >= 7

    # 1. Content extractability
    assert dims[GeoDimensionKey.CONTENT_EXTRACTABILITY.value].is_measured is True
    assert dims[GeoDimensionKey.CONTENT_EXTRACTABILITY.value].score > 50

    # 2. Entity clarity
    assert dims[GeoDimensionKey.ENTITY_CLARITY.value].is_measured is True

    # 3. Structured data quality
    assert dims[GeoDimensionKey.STRUCTURED_DATA_QUALITY.value].is_measured is True
    assert dims[GeoDimensionKey.STRUCTURED_DATA_QUALITY.value].score > 0

    # 4. Source corroboration (unmeasured without backlink/authority connector)
    assert dims[GeoDimensionKey.SOURCE_CORROBORATION.value].is_measured is False
    assert dims[GeoDimensionKey.SOURCE_CORROBORATION.value].score is None

    # 5. AI crawler accessibility
    assert dims[GeoDimensionKey.AI_CRAWLER_ACCESSIBILITY.value].is_measured is True
    assert dims[GeoDimensionKey.AI_CRAWLER_ACCESSIBILITY.value].score == 100.0

    # 6. Factual consistency
    assert dims[GeoDimensionKey.FACTUAL_CONSISTENCY.value].is_measured is True

    # 7. Live AI citations (unmeasured without live run)
    assert dims[GeoDimensionKey.LIVE_AI_CITATIONS.value].is_measured is False
    assert dims[GeoDimensionKey.LIVE_AI_CITATIONS.value].score is None


def test_issue_8_competitive_intelligence_fails_closed_when_unmeasured():
    """
    Issue 8: Competitive intelligence is explicitly marked untested/NOT_EVALUATED
    when comparable benchmarks or competitors are missing.
    """
    engine = GeoCitationGapEngine()
    report = engine.analyze_citation_gaps(
        target_domain="perforacare.com",
        brand_name="Perfora",
        competitor_domains=[],
        pages=[],
        benchmark_results=None,
    )
    assert report.status == "NOT_EVALUATED"
    assert "Live AI citation benchmark not run" in report.primary_bottleneck


def test_issue_10_dynamic_100_sandbox_b2b_vs_d2c_oral_care_taxonomy():
    """
    Issue 10: Dynamic 100 Sandbox filters out B2B SaaS questions (e.g. enterprise SLAs,
    multi-seat billing) when testing a consumer D2C oral care brand like Perfora.
    """
    profile = BusinessProfile(
        business_name="Perfora",
        primary_intent=BusinessIntent.ECOMMERCE,
        industry="D2C Oral Care & Personal Hygiene",
        niche="electric toothbrushes, probiotic mouthwash, whitening products",
    )

    candidate_questions = [
        {"question": "What products does Perfora offer?", "category_id": "brand_identity"},
        {"question": "How much does the Perfora electric toothbrush cost?", "category_id": "pricing"},
        {"question": "Does Perfora mouthwash contain alcohol or SLS?", "category_id": "safety_compliance"},
        {"question": "What enterprise SLA and SOC 2 Type II compliance does Perfora provide for engineering teams?", "category_id": "enterprise_sla"},
        {"question": "Can we get volume multi-seat SaaS seat pricing for 500 employee enterprise deployment?", "category_id": "multi_seat_pricing"},
        {"question": "Where can I buy Perfora teeth whitening powder?", "category_id": "retail_availability"},
    ]

    filtered = validate_questions_against_business_context(candidate_questions, profile)
    filtered_queries = [
        q.get("question", "") if isinstance(q, dict) else getattr(q, "question", "")
        for q in filtered
    ]

    assert any("What products does Perfora offer?" in q for q in filtered_queries)
    assert any("How much does the Perfora electric toothbrush cost?" in q for q in filtered_queries)
    assert any("Does Perfora mouthwash contain alcohol or SLS?" in q for q in filtered_queries)
    assert any("Where can I buy Perfora teeth whitening powder?" in q for q in filtered_queries)

    # B2B SaaS enterprise software questions must be excluded
    assert not any("sla" in q.lower() or "soc 2" in q.lower() for q in filtered_queries)
    assert not any("multi-seat" in q.lower() or "saas" in q.lower() for q in filtered_queries)


def test_issue_11_brand_contradiction_precision():
    """
    Issue 11: Brand contradictions must precisely declare:
    - statement_a & statement_b
    - source_url_a & source_url_b
    - evidence_id_a & evidence_id_b
    - disputed_fact
    - conflict_explanation
    - authoritative_correction
    """
    contra = Contradiction(
        id="contra_perfora_001",
        claim_a_id="claim_about_01",
        claim_b_id="claim_unwind_02",
        description="Origin formulation claims conflict between About page and Unwind Combo page",
        resolution="MANUAL_REVIEW_REQUIRED",
        statement_a="Made with 100% natural Indian Ayurvedic herbal ingredients",
        statement_b="Imported formulation packaged in Germany",
        source_url_a="https://perforacare.com/about",
        source_url_b="https://perforacare.com/products/unwind-combo",
        evidence_id_a="ev_dom_about_01",
        evidence_id_b="ev_dom_unwind_02",
        disputed_fact="Origin of Perfora ingredients & country of origin",
        conflict_explanation="About page asserts 100% domestic Ayurvedic formulation, while the Unwind combo page lists German contract packaging.",
        authoritative_correction="Align product description copy to consistently state 'Formulated with Ayurvedic botanicals, packaged according to global safety standards'.",
    )

    assert contra.disputed_fact == "Origin of Perfora ingredients & country of origin"
    assert contra.statement_a != contra.statement_b
    assert contra.source_url_a == "https://perforacare.com/about"
    assert contra.source_url_b == "https://perforacare.com/products/unwind-combo"
    assert contra.evidence_id_a == "ev_dom_about_01"
    assert contra.evidence_id_b == "ev_dom_unwind_02"
    assert len(contra.conflict_explanation) > 10
    assert len(contra.authoritative_correction) > 10


def test_issue_12_external_integrations_honest_unconnected_state():
    """
    Issue 12: External integrations disclose missing status honestly:
    Search Console, DataForSEO, GA4, CruX are reported as NOT_CONNECTED
    without fabricating zero-click or fake analytics data.
    """
    demand = build_search_demand({"state": "NOT_CONNECTED"})
    assert demand["status"] == "NOT_CONNECTED"
    assert demand["sources"] == []
    assert demand["queries"] == []
    assert "skipped" in demand["note"]

    from app.connectors.base.models import ConnectorCredentials
    from app.domain.enums import ConnectorType
    crux = CruxConnector(credentials=ConnectorCredentials(provider=ConnectorType.CRUX))
    assert crux._api_key() is None

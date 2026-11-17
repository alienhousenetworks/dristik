"""
Milestone M2 Tests:
1. ScoringEngine.build_scoring_methodology_appendix reproduces exact pillar & composite scores.
2. evaluate_geo_readiness separates all 7 R3 GEO dimensions, keeps live_ai_citations.score is None when no live run exists,
   can reach 100 on retrieval_accessibility, and does NOT flag multi-product pricing ($19, $49, $99) as CONFLICTING.
3. CalibratedConfidenceEngine gives lower confidence for 5 / 504 sampled pages than for 50 / 50 full crawl.
4. aeo.scoring.EvidenceState is app.domain.enums.EvidenceState.
"""
import pytest

import app.aeo.scoring as aeo_scoring
from app.aeo.specialists import BusinessAttributionSpecialist, CompetitiveIntelligenceSpecialist
from app.domain.enums import BusinessIntent, Category, EvidenceClass, EvidenceState, GeoDimensionKey, RubricConfidence, Severity
from app.domain.models import (
    AuditScopeInfo,
    BusinessProfile,
    Claim,
    CrawlInventory,
    CrawlManifest,
    Finding,
    FindingEvidence,
    Ga4AttributionData,
    LifecycleRevenueIntelligence,
    PageEvidence,
)
from app.domain.scoring.displayed_score import FORMULA_VERSION as DISPLAYED_FORMULA_VERSION
from app.domain.scoring.engine import ScoringEngine
from app.evidence.store import EvidenceStore
from app.geo.readiness import evaluate_geo_readiness
from app.orchestration.cognition.confidence import CalibratedConfidenceEngine


def _sample_profile() -> BusinessProfile:
    return BusinessProfile(
        business_name="Acme Cloud",
        industry="Enterprise SaaS",
        products=["Edge Firewall", "Zero Trust Gateway"],
        value_proposition="Zero-latency cloud security for distributed engineering teams",
        primary_cta="Start Free Trial",
        primary_intent=BusinessIntent.SAAS,
    )


def test_scoring_methodology_appendix_reproduces_pillar_and_composite_scores():
    engine = ScoringEngine()
    profile = _sample_profile()
    finding = Finding(
        finding_id="f_missing_h1",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        title="Missing H1 tag on pricing page",
        description="Pricing page has no H1 heading.",
        recommendation="Add a descriptive H1 tag.",
        confidence=0.95,
        confidence_rubric=RubricConfidence.VERIFIED,
        evidence_class=EvidenceClass.OBSERVED,
        evidence=[FindingEvidence(url="https://acme.io/pricing", snippet="<body><h2>Pricing</h2></body>")],
        evidence_refs=["https://acme.io/pricing"],
    )
    scope = AuditScopeInfo(
        plan_tier="growth",
        requested_pages=10,
        measured_pages=5,
        discovered_urls=[f"https://acme.io/p{i}" for i in range(50)],
    )
    scores = engine.calculate_scores(
        findings=[finding],
        business_profile=profile,
        has_schema=True,
        is_https=True,
        readability=55.0,
        audit_scope=scope,
    )
    honest = engine.calculate_honest_scores(
        findings=[finding],
        business_profile=profile,
        has_schema=True,
        is_https=True,
        readability=55.0,
    )
    crawl_inv = CrawlInventory(discovered_total=50, eligible_total=50, analyzed_total=5, tested_pages=5)

    appendix = engine.build_scoring_methodology_appendix(
        scores=scores,
        honest_scores=honest,
        crawl_inventory=crawl_inv,
    )

    assert appendix["formula_version"] == "dristik_central_scoring_v5.1"
    assert DISPLAYED_FORMULA_VERSION == "dristik_central_scoring_v5.1"
    assert "pillars" in appendix
    assert "severity_adjustments" in appendix
    assert "sample_coverage_confidence_model" in appendix
    assert "unavailable_data_exclusion_rules" in appendix
    assert "composite_derivation" in appendix
    assert "geo_extractability_formula" in appendix

    # Verify sample coverage confidence model reflects 5 / 50 (10%)
    cov_model = appendix["sample_coverage_confidence_model"]
    assert cov_model["tested_pages"] == 5
    assert cov_model["discovered_total"] == 50
    assert cov_model["sample_coverage_pct"] == 10.0

    # Verify composite arithmetic reproduces overall_score
    steps = appendix["composite_derivation"]["steps"]
    assert len(steps) > 0
    recomputed = round(sum(step["raw_score"] * step["normalized_weight"] for step in steps), 1)
    assert abs(recomputed - scores.overall_score) <= 0.2
    assert appendix["composite_derivation"]["overall_score"] == scores.overall_score

    # Verify unmeasured AI_SEARCH and TRUST_AUTHORITY are in excluded_pillars
    excluded = appendix["unavailable_data_exclusion_rules"]["excluded_pillars"]
    assert Category.AI_SEARCH.value in excluded
    assert Category.TRUST_AUTHORITY.value in excluded


def test_zero_pages_crawl_marks_unmatched_checks_not_measured():
    engine = ScoringEngine()
    scope = AuditScopeInfo(plan_tier="starter", requested_pages=5, measured_pages=0)
    scores = engine.calculate_scores(
        findings=[],
        business_profile=_sample_profile(),
        has_schema=None,
        is_https=None,
        audit_scope=scope,
        pages=[],
    )
    on_page = scores.category_scores[Category.ON_PAGE_SEO.value]
    assert on_page.status == "NOT_MEASURED"
    assert on_page.score is None


def test_form_field_count_curve_uses_measured_page_forms():
    engine = ScoringEngine()
    pages_low_friction = [
        PageEvidence(
            url="https://acme.io/contact",
            forms=[{"input_count": 2, "inputs": [{"type": "email"}, {"type": "text"}]}],
        )
    ]
    pages_high_friction = [
        PageEvidence(
            url="https://acme.io/contact",
            forms=[{"input_count": 10}],
        )
    ]
    res_low = engine.calculate_scores(
        findings=[],
        business_profile=_sample_profile(),
        has_schema=True,
        is_https=True,
        pages=pages_low_friction,
    )
    res_high = engine.calculate_scores(
        findings=[],
        business_profile=_sample_profile(),
        has_schema=True,
        is_https=True,
        pages=pages_high_friction,
    )
    chk_low = next(
        c for c in res_low.category_scores[Category.UX_CONVERSION.value].check_results
        if c.check_id == "form_field_count_curve"
    )
    chk_high = next(
        c for c in res_high.category_scores[Category.UX_CONVERSION.value].check_results
        if c.check_id == "form_field_count_curve"
    )
    assert chk_low.score == 1.0
    assert chk_high.score < 0.50


def test_geo_readiness_separates_7_dimensions_and_calibrates_pricing_and_accessibility():
    pages = [
        PageEvidence(
            url="https://acme.io/",
            status_code=200,
            title="Acme Cloud | Enterprise Zero Trust Gateway & Edge Firewall",
            h1=["Acme Cloud Enterprise Security Platform"],
            h2=["What is Acme Cloud?", "Who is Acme Cloud for?", "How much does Acme Cloud cost?"],
            h3=["Core Capabilities", "Customer Case Studies"],
            body_text=(
                "Acme Cloud is an enterprise SaaS platform providing Edge Firewall and Zero Trust Gateway "
                "built for B2B engineering teams of 50 to 5,000 employees. "
                "Our pricing plans start at $19/month for Starter, $49/month for Growth, and $99/month for Enterprise. "
                "We are SOC 2 Type II and ISO 27001 certified with 500+ enterprise customer case studies."
            ),
            schema_types=["Organization", "WebSite", "Product"],
            raw_schema=[
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Acme Cloud",
                    "url": "https://acme.io",
                    "logo": "https://acme.io/logo.png",
                    "description": "Zero-latency cloud security for distributed engineering teams",
                    "sameAs": ["https://www.linkedin.com/company/acme-cloud"],
                },
                {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    "name": "Acme Cloud",
                    "url": "https://acme.io",
                },
            ],
        )
    ]
    manifest = CrawlManifest(
        domain="acme.io",
        base_url="https://acme.io",
        total_pages_discovered=1,
        total_pages_crawled=1,
        pages=pages,
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nAllow: /\nUser-agent: GPTBot\nAllow: /\n",
        sitemap_found=True,
        sitemap_url="https://acme.io/sitemap.xml",
    )

    report = evaluate_geo_readiness(
        website_url="https://acme.io",
        pages=pages,
        manifest=manifest,
        profile=_sample_profile(),
        visibility_measured=False,
        visibility_score=None,
    )

    required_7_keys = [
        GeoDimensionKey.CONTENT_EXTRACTABILITY.value,
        GeoDimensionKey.ENTITY_CLARITY.value,
        GeoDimensionKey.STRUCTURED_DATA_QUALITY.value,
        GeoDimensionKey.SOURCE_CORROBORATION.value,
        GeoDimensionKey.AI_CRAWLER_ACCESSIBILITY.value,
        GeoDimensionKey.FACTUAL_CONSISTENCY.value,
        GeoDimensionKey.LIVE_AI_CITATIONS.value,
    ]
    for k in required_7_keys:
        assert k in report.dimension_scores, f"Missing required GEO dimension key: {k}"

    # 1. Live AI citations must be strictly None / unmeasured when no live run exists
    live_dim = report.dimension_scores[GeoDimensionKey.LIVE_AI_CITATIONS.value]
    assert live_dim.score is None
    assert live_dim.is_measured is False

    # 2. Source corroboration is unmeasured without external authority connector
    corrob_dim = report.dimension_scores[GeoDimensionKey.SOURCE_CORROBORATION.value]
    assert corrob_dim.score is None
    assert corrob_dim.is_measured is False

    # 3. Structured data quality is measured from schema_res
    struct_dim = report.dimension_scores[GeoDimensionKey.STRUCTURED_DATA_QUALITY.value]
    assert struct_dim.is_measured is True
    assert struct_dim.score is not None and struct_dim.score > 0

    # 4. Retrieval accessibility reaches 100 when HTTPS + robots + sitemap + AI bots allowed + clean 200 status
    retr_dim = report.dimension_scores[GeoDimensionKey.RETRIEVAL_ACCESSIBILITY.value]
    ai_crawl_dim = report.dimension_scores[GeoDimensionKey.AI_CRAWLER_ACCESSIBILITY.value]
    assert retr_dim.score == 100.0
    assert ai_crawl_dim.score == 100.0

    # 5. Multi-tier pricing ($19, $49, $99) must NOT be flagged as CONFLICTING
    pricing_q = next(q for q in report.questions if q.question_key == "pricing")
    assert pricing_q.status == "SUPPORTED"
    assert report.questions_conflicting == 0


def test_calibrated_confidence_scales_with_domain_discovery_sample_coverage():
    engine = CalibratedConfidenceEngine()
    store = EvidenceStore(run_id="run_test_m2")
    claims = [
        Claim(
            id="c1",
            agent_id="deterministic_seo",
            statement="Title tag present on sampled pages",
            evidence_refs=["ev_1"],
        )
    ]
    pages_5 = [PageEvidence(url=f"https://acme.io/p{i}") for i in range(5)]
    pages_50 = [PageEvidence(url=f"https://acme.io/p{i}") for i in range(50)]

    res_sparse = engine.calculate_confidence(
        claims=claims,
        evidence_store=store,
        pages=pages_5,
        sample_target=5,
        index_url_count=504,
    )
    res_full = engine.calculate_confidence(
        claims=claims,
        evidence_store=store,
        pages=pages_50,
        sample_target=5,
        index_url_count=50,
    )

    assert res_sparse.signals_breakdown["page_coverage"] < 1.0
    assert res_sparse.index_coverage < 1.0
    assert res_full.evidence_coverage == 1.0
    assert res_sparse.confidence_score < res_full.confidence_score


def test_unified_evidence_state_and_specialist_honesty():
    assert aeo_scoring.EvidenceState is EvidenceState

    class DummyReport:
        competitive_report = {"status": "UNTESTED", "competitors": []}
        lifecycle_revenue = LifecycleRevenueIntelligence(
            domain="acme.io",
            ga4=Ga4AttributionData(is_connected=False),
        )

    spec12 = CompetitiveIntelligenceSpecialist()
    res12 = spec12.evaluate(DummyReport())
    assert res12.status == EvidenceState.NOT_TESTED

    spec14 = BusinessAttributionSpecialist()
    res14 = spec14.evaluate(DummyReport())
    assert res14.status == EvidenceState.DATA_UNAVAILABLE

    class ConnectedReport:
        competitive_report = {"status": "MEASURED", "competitors": [{"domain": "foocorp.com", "status": "MEASURED"}]}
        lifecycle_revenue = LifecycleRevenueIntelligence(
            domain="acme.io",
            ga4=Ga4AttributionData(is_connected=True, conversion_rate=3.2),
        )

    assert spec12.evaluate(ConnectedReport()).status == EvidenceState.SAMPLE_VERIFIED
    assert spec14.evaluate(ConnectedReport()).status == EvidenceState.SAMPLE_VERIFIED

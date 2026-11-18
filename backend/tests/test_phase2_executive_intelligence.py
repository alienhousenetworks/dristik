"""
Test Suite — Phase 2: Executive Intelligence & Business Decision Layer

Verifies:
- Phase 2.1: Business Understanding Engine (10 dimensions, declared vs. inferred provenance)
- Phase 2.2: Three-Perspective Diagnosis (Human, Search, Answer Engine)
- Phase 2.3: Business Impact Model (Strict NOT_MEASURED financial exposure safeguard)
- Phase 2.4: Strategic Opportunity Engine (9 opportunity dimensions tied to evidence)
- Phase 2.5: Executive Decision Dashboard (Complete 10-point executive brief)
- Phase 2.6: Executive QA & Narrative Guard (Buzzword filtering, score parity, limitation disclosures)
"""
import pytest
from app.executive.business_intelligence import (
    BusinessUnderstandingEngine,
    VerifiedBusinessProfile,
    FactProvenance,
)
from app.executive.three_perspective import (
    ThreePerspectiveSynthesizer,
    ThreePerspectiveDiagnostic,
)
from app.executive.business_impact import (
    BusinessImpactEvaluator,
    FindingBusinessImpact,
    TechnicalSeverity,
    BusinessRelevance,
    UserImpact,
    SearchImpact,
    ConfidenceLevel,
)
from app.executive.opportunity_engine import (
    OpportunityEngine,
    OpportunityDimension,
    StrategicOpportunity,
)
from app.executive.executive_dashboard import (
    ExecutiveDashboardBuilder,
    ExecutiveDashboardReport,
)
from app.executive.narrative_qa import (
    ExecutiveNarrativeQAGuard,
    ExecutiveQAResult,
)


class MockFinding:
    def __init__(self, fid: str, title: str, severity: str, category: str = "TECHNICAL_SEO", evidence_status: str = "OBSERVED"):
        self.id = fid
        self.finding_id = fid
        self.title = title
        self.severity = severity
        self.category = category
        self.evidence_status = evidence_status


# ============================================================================
# Phase 2.1: Business Understanding Engine
# ============================================================================

def test_phase_2_1_business_understanding():
    domain = "perfora.co"
    homepage_html = "<html><head><title>Perfora Oral Care</title></head><body><h1>Elevate Your Everyday Oral Care</h1></body></html>"
    page_reports = [
        {"url": "https://perfora.co/", "title": "Perfora - Oral Care"},
        {"url": "https://perfora.co/products/electric-toothbrush", "title": "Electric Toothbrush"},
        {"url": "https://perfora.co/products/probiotic-mouthwash", "title": "Probiotics Mouthwash"},
        {"url": "https://perfora.co/cart", "title": "Shopping Cart"},
    ]
    schemas = [
        {"@type": "Organization", "name": "Perfora", "url": "https://perfora.co"}
    ]

    profile: VerifiedBusinessProfile = BusinessUnderstandingEngine.analyze_business(
        domain=domain,
        homepage_html=homepage_html,
        page_reports=page_reports,
        schema_entities=schemas,
    )

    assert profile.brand_identity.fact_value["brand_name"] == "Perfora"
    assert profile.brand_identity.provenance == FactProvenance.DECLARED_BY_SITE

    # Check products
    products = profile.products_and_services.fact_value
    assert len(products) > 0
    assert any("Electric Toothbrush" in p for p in products)

    # Check business model
    assert profile.business_model.fact_value == "D2C_ECOMMERCE"
    assert profile.business_model.provenance in (FactProvenance.DECLARED_BY_SITE, FactProvenance.INFERRED_BY_DRISTIK)


    # Verify overall confidence
    assert profile.overall_confidence >= 0.80


# ============================================================================
# Phase 2.2: Three-Perspective Diagnosis
# ============================================================================

def test_phase_2_2_three_perspective_diagnosis():
    profile = BusinessUnderstandingEngine.analyze_business("perfora.co")
    seo_findings = [MockFinding("F-SEO-1", "TTFB exceeds 800ms", "HIGH", "TECHNICAL_SEO")]
    cro_findings = [MockFinding("F-CRO-1", "Missing security badge on cart", "HIGH", "CRO")]
    aeo_findings = [MockFinding("F-AEO-1", "Organization schema missing logo", "MEDIUM", "AEO")]

    diagnostics: ThreePerspectiveDiagnostic = ThreePerspectiveSynthesizer.synthesize_diagnostics(
        business_profile=profile,
        seo_findings=seo_findings,
        cro_findings=cro_findings,
        aeo_findings=aeo_findings,
        scores={"SEO": 82.0, "CRO": 74.0, "AEO": 68.0},
    )

    # Human perspective
    assert diagnostics.human_perspective.readiness_score == 74.0
    assert len(diagnostics.human_perspective.evidence_backed_observations) >= 3
    assert len(diagnostics.human_perspective.critical_deficiencies) > 0

    # Search perspective
    assert diagnostics.search_perspective.readiness_score == 82.0
    assert "Search Spider" in diagnostics.search_perspective.perspective_name

    # Answer Engine perspective
    assert diagnostics.answer_engine_perspective.readiness_score == 68.0
    assert "Answer-Engine" in diagnostics.answer_engine_perspective.perspective_name


    # Unified synthesis
    assert "human" in diagnostics.synthesis_statement.lower()
    assert "search" in diagnostics.synthesis_statement.lower()
    assert "answer-engine" in diagnostics.synthesis_statement.lower()



# ============================================================================
# Phase 2.3: Business Impact Model (Strict Safeguards)
# ============================================================================

def test_phase_2_3_business_impact_model_unmeasured():
    finding = MockFinding("F-CHK-1", "Checkout cart drawer button unresponsive on iOS", "CRITICAL", "CRO")
    
    # When analytics are disconnected (default)
    impact: FindingBusinessImpact = BusinessImpactEvaluator.evaluate_finding(
        finding=finding,
        analytics_connected=False,
    )

    assert impact.technical_severity == TechnicalSeverity.CRITICAL
    assert impact.business_relevance == BusinessRelevance.CORE_REVENUE
    assert impact.user_impact == UserImpact.HIGH_FRICTION
    assert impact.financial_exposure.is_measured is False
    assert impact.financial_exposure.status == "NOT_MEASURED"
    assert impact.financial_exposure.estimated_monthly_exposure_usd is None
    assert "Financial impact not measured" in impact.financial_exposure.statement


def test_phase_2_3_business_impact_model_measured():
    finding = MockFinding("F-CHK-1", "Checkout cart drawer button unresponsive on iOS", "CRITICAL", "CRO")

    # When GA4 / revenue analytics are connected
    impact: FindingBusinessImpact = BusinessImpactEvaluator.evaluate_finding(
        finding=finding,
        analytics_connected=True,
        monthly_traffic=100000,
        average_order_value=45.0,
        conversion_rate=0.02,
    )

    assert impact.financial_exposure.is_measured is True
    assert impact.financial_exposure.status == "MEASURED"
    assert impact.financial_exposure.estimated_monthly_exposure_usd is not None
    assert impact.financial_exposure.estimated_monthly_exposure_usd > 0
    assert "$4,500.00" in impact.financial_exposure.statement


# ============================================================================
# Phase 2.4: Strategic Opportunity Engine
# ============================================================================

def test_phase_2_4_strategic_opportunity_engine():
    pages = [
        {"url": "https://perfora.co/"},
        {"url": "https://perfora.co/products/brush"},
        {"url": "https://perfora.co/cart"},
    ]
    opps = OpportunityEngine.identify_opportunities(
        domain="perfora.co",
        page_inventory=pages,
    )

    assert len(opps) >= 7
    dimensions = {o.dimension for o in opps}
    assert OpportunityDimension.LANDING_PAGE_EXPANSION in dimensions
    assert OpportunityDimension.COMMERCIAL_INFO_TRANSPARENCY in dimensions
    assert OpportunityDimension.AI_ANSWER_COVERAGE in dimensions
    assert OpportunityDimension.TECHNICAL_FOUNDATION in dimensions

    # Verify all opportunities cite evidence tokens
    for opp in opps:
        assert len(opp.evidence_ids) > 0
        assert opp.estimated_effort_days > 0


# ============================================================================
# Phase 2.5: Executive Decision Dashboard
# ============================================================================

def test_phase_2_5_executive_dashboard_assembly():
    profile = BusinessUnderstandingEngine.analyze_business("perfora.co")
    f_crit = MockFinding("F-001", "Payment gateway timeout under mobile 3G", "CRITICAL", "CRO")
    impacts = [BusinessImpactEvaluator.evaluate_finding(f_crit, analytics_connected=False)]
    opps = OpportunityEngine.identify_opportunities("perfora.co")

    dashboard: ExecutiveDashboardReport = ExecutiveDashboardBuilder.assemble_dashboard(
        business_profile=profile,
        discovered_urls_count=523,
        crawled_urls_count=25,
        crawl_profile="Quick",
        evaluated_impacts=impacts,
        opportunities=opps,
        current_scores={"SEO": 82.0, "AEO": 70.0, "CRO": 76.0},
        prior_audit_scores={"SEO": 78.0, "AEO": 65.0, "CRO": 76.0},
        analytics_connected=False,
    )

    # 1. Business Profile
    assert dashboard.business_profile.brand_identity.fact_value["brand_name"] == "Perfora"
    # 2. Scope & Coverage
    assert dashboard.audit_scope["discovered_urls"] == 523
    assert dashboard.audit_scope["inspected_urls"] == 25
    assert dashboard.audit_scope["crawl_profile"] == "Quick"
    # 3. Critical Risks
    assert len(dashboard.critical_risks) >= 1
    # 4. Growth Opportunities
    assert len(dashboard.growth_opportunities) > 0
    # 5. Cross-Discipline Overlap
    assert len(dashboard.cross_discipline_overlaps) == 3
    # 6. Resource Requirements
    assert dashboard.total_estimated_hours == 52.0  # 12 + 24 + 16
    # 7. Strategic Priorities
    assert len(dashboard.strategic_priorities) == 3
    # 8. 30/60/90-Day Tactical Plan
    assert len(dashboard.tactical_roadmap) == 3
    # 9. Data Limitations
    assert any("Financial revenue exposure is unmeasured" in lim for lim in dashboard.data_limitations)
    # 10. Historical Tracking
    assert dashboard.historical_tracking["baseline_available"] is True
    assert dashboard.historical_tracking["net_score_delta"]["SEO"] == 4.0


# ============================================================================
# Phase 2.6: Executive QA & Narrative Guard
# ============================================================================

def test_phase_2_6_narrative_qa_buzzwords_and_scores():
    # Narrative containing buzzwords and hallucinated scores
    bad_narrative = (
        "Perfora delivers a revolutionary and world-class oral care solution. "
        "The site achieved an outstanding score of 98 on technical SEO."
    )

    qa_result: ExecutiveQAResult = ExecutiveNarrativeQAGuard.validate_narrative(
        narrative_text=bad_narrative,
        authoritative_scores={"SEO": 82.0, "CRO": 74.0},
        analytics_connected=False,
    )

    assert qa_result.passed is False
    assert len(qa_result.violations) >= 2
    categories = [v.category for v in qa_result.violations]
    assert "BUZZWORD" in categories
    assert "SCORE_MISMATCH" in categories

    # Verify buzzword was sanitized
    assert "revolutionary" not in qa_result.sanitized_text
    assert "world-class" not in qa_result.sanitized_text


def test_phase_2_6_narrative_qa_unmeasured_limitation():
    # Narrative making revenue loss claim without disclosure when analytics are disconnected
    bad_revenue_narrative = (
        "The site is currently losing $50,000 every month due to broken checkout links."
    )

    qa_result: ExecutiveQAResult = ExecutiveNarrativeQAGuard.validate_narrative(
        narrative_text=bad_revenue_narrative,
        analytics_connected=False,
    )

    assert qa_result.passed is False
    assert any(v.category == "MISSING_LIMITATION" for v in qa_result.violations)


def test_phase_2_6_narrative_qa_clean_text_passes():
    clean_narrative = (
        "Perfora oral care products show strong organic visibility with an SEO score of 82.0. "
        "Financial impact is not measured as connected revenue analytics are currently unavailable."
    )

    qa_result: ExecutiveQAResult = ExecutiveNarrativeQAGuard.validate_narrative(
        narrative_text=clean_narrative,
        authoritative_scores={"SEO": 82.0},
        analytics_connected=False,
    )

    assert qa_result.passed is True
    assert len(qa_result.violations) == 0

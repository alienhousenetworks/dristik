"""
Test Suite — Phase 7: Competitive Intelligence (10/10 Transformation)

Verifies all 8 sub-phases:
- 7.1: Competitor Discovery (7 vectors + explicit user approval lifecycle)
- 7.2: Website Ingestion (10 dimensions + strict provenance isolation)
- 7.3: Competitive SEO Intelligence (8 comparisons: keywords, intent, architecture, depth, tech CWV, backlinks, landing pages, visibility)
- 7.4: Competitive GEO Intelligence (8 comparisons: entity clarity, AI crawler access, AI mentions, citation domains, frequency, credibility, positioning, contradictions)
- 7.5: Competitive AEO Intelligence (6 comparisons: question coverage, completeness, extractability, accuracy, live snippets, unanswered commercial questions)
- 7.6: Competitive CRO Intelligence (8 comparisons: value prop, navigation, pricing visibility, product structure, CTAs, forms, trust signals, and CHECKOUT_FLOW_UNTESTED guardrail)
- 7.7: Opportunity Gap Engine (5 ranked gap archetypes with ICE scoring and concrete playbooks)
- 7.8: Competitive Scoring & Provenance (Decoupled 4-discipline scores + 10/10 statement ledger)
"""
import pytest
from datetime import datetime, timezone

from app.competitive.models import (
    CompetitorApprovalStatus,
    DiscoveryVectorType,
    ProvenanceScope,
    OpportunityGapType,
)
from app.competitive.discovery_engine import (
    CompetitorDiscoveryEngine,
    competitor_discovery_engine,
)
from app.competitive.ingestion_engine import (
    CompetitorIngestionEngine,
    competitor_ingestion_engine,
)
from app.competitive.seo_intelligence import (
    CompetitiveSeoIntelligenceEngine,
    competitive_seo_engine,
)
from app.competitive.geo_intelligence import (
    CompetitiveGeoIntelligenceEngine,
    competitive_geo_engine,
)
from app.competitive.aeo_intelligence import (
    CompetitiveAeoIntelligenceEngine,
    competitive_aeo_engine,
)
from app.competitive.cro_intelligence import (
    CompetitiveCroIntelligenceEngine,
    competitive_cro_engine,
)
from app.competitive.opportunity_gap_engine import (
    OpportunityGapEngine,
    opportunity_gap_engine,
)
from app.competitive.competitive_scorecard import (
    CompetitiveScorecardEngine,
    competitive_scorecard_engine,
)
from app.competitive.unified_engine import (
    unified_competitive_engine,
)
from app.seo.competitive.resolution.rejection_store import CompetitorRejectionStore


# ============================================================================
# Phase 7.1: Competitor Discovery & Approval Workflow
# ============================================================================

def test_phase7_1_competitor_discovery_7_vectors():
    target_facts = {
        "business_category": "AI Search Engine Optimization Platform",
        "products": ["AI Audit", "GEO Engine", "Schema Generator"],
        "search_intents": ["geo optimization", "ai visibility audit", "llm citation checker"],
        "geography": "Global",
        "business_model": "B2B",
        "pricing_model": "SUBSCRIPTION",
        "target_audience": ["Head of SEO", "VP Marketing", "Digital Agency"],
    }

    raw_candidates = [
        {
            "domain": "good-rival.ai",
            "company_name": "Good Rival",
            "business_category": "AI Search Optimization & GEO Tools",
            "products": ["AI Audit", "GEO Engine"],
            "search_intents": ["geo optimization", "ai visibility audit"],
            "serp_overlap_pct": 65.0,
            "geography": "Global",
            "business_model": "B2B",
            "pricing_model": "SUBSCRIPTION",
            "target_audience": ["Head of SEO", "VP Marketing"],
        },
        {
            "domain": "distant-ecommerce.com",
            "company_name": "Distant Ecommerce",
            "business_category": "Footwear Retail",
            "products": ["Sneakers", "Running Shoes"],
            "search_intents": ["buy shoes online"],
            "serp_overlap_pct": 0.0,
            "geography": "US",
            "business_model": "B2C",
            "pricing_model": "ONE_TIME",
            "target_audience": ["Consumers"],
        },
    ]

    candidates = competitor_discovery_engine.discover_competitors(
        target_domain="dristik.ai",
        target_facts=target_facts,
        raw_candidates=raw_candidates,
    )

    # Must evaluate all 7 vectors
    top = candidates[0]
    assert top.domain == "good-rival.ai"
    assert len(top.vectors) == 7
    assert DiscoveryVectorType.BUSINESS_CATEGORY.value in top.vectors
    assert DiscoveryVectorType.PRODUCT_CATEGORY.value in top.vectors
    assert DiscoveryVectorType.SEARCH_INTENT.value in top.vectors
    assert DiscoveryVectorType.SEARCH_RESULT_SERP.value in top.vectors
    assert DiscoveryVectorType.GEOGRAPHIC.value in top.vectors
    assert DiscoveryVectorType.COMMERCIAL_SIMILARITY.value in top.vectors
    assert DiscoveryVectorType.CUSTOMER_AUDIENCE.value in top.vectors
    assert top.similarity_score > 70.0

    # Distant ecommerce competitor score should be low
    bottom = candidates[1]
    assert bottom.similarity_score < 40.0


def test_phase7_1_user_approval_lifecycle_guardrail():
    engine = CompetitorDiscoveryEngine()
    target_facts = {"business_category": "SaaS", "products": ["App"]}
    raw_candidates = [{"domain": "peer-saas.com", "company_name": "Peer SaaS"}]

    candidates = engine.discover_competitors("mysaas.com", target_facts, raw_candidates)
    assert candidates[0].approval_status == CompetitorApprovalStatus.DISCOVERED

    # Request approval promotes qualifying candidate
    engine.request_user_approval(candidates, top_k=1, min_similarity=0.0)
    assert candidates[0].approval_status == CompetitorApprovalStatus.PENDING_USER_APPROVAL

    # Official benchmark group strictly rejects unapproved candidates
    unapproved_group = engine.build_official_benchmark_group("mysaas.com", candidates)
    assert len(unapproved_group.approved_competitors) == 0

    # Explicit user approval promotes candidate
    engine.approve_competitor("mysaas.com", candidates[0], approved_by="admin_lead")
    assert candidates[0].approval_status == CompetitorApprovalStatus.APPROVED

    official_group = engine.build_official_benchmark_group("mysaas.com", candidates)
    assert len(official_group.approved_competitors) == 1
    assert official_group.approved_competitors[0].domain == "peer-saas.com"


# ============================================================================
# Phase 7.2: Website Ingestion & Provenance Isolation
# ============================================================================

def test_phase7_2_website_ingestion_10_dimensions():
    html = """
    <html>
    <head>
        <title>Competitor Pro - AI Visibility Solutions</title>
        <meta name="description" content="AI visibility and prompt ranking engine">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script type="application/ld+json">
        {"@type": "Organization", "name": "Competitor Pro"}
        </script>
    </head>
    <body>
        <h1>Dominate Generative Search</h1>
        <h2>Enterprise Features</h2>
        <p>Competitor Pro is an enterprise platform designed to audit and boost generative AI citations across ChatGPT and Claude.</p>
        <a href="/pricing">See Pricing</a>
        <a href="/products/geo">GEO Tool</a>
        <button>Book a Demo</button>
        <form action="/subscribe"><input type="email"/></form>
    </body>
    </html>
    """

    artifact = competitor_ingestion_engine.ingest_competitor_site(
        domain="competitorpro.com",
        raw_pages=[{"url": "https://competitorpro.com/", "html": html, "ttfb_ms": 175.0}],
        audit_run_id="run_999",
    )

    page = artifact.pages[0]
    # 1. URL
    assert page.url == "https://competitorpro.com/"
    # 2. Page Type
    assert page.page_type == "HOMEPAGE"
    # 3. Product categories (detected from links/content)
    # 4. Content Structure
    assert page.content_structure["h1_tags"] == ["Dominate Generative Search"]
    assert page.word_count > 10
    # 5. Metadata
    assert page.metadata["title"] == "Competitor Pro - AI Visibility Solutions"
    # 6. Structured Data
    assert "Organization" in page.structured_data_types
    # 7. Internal Linking
    assert page.internal_links_count >= 2
    # 8. Performance
    assert page.ttfb_ms == 175.0
    # 9. Mobile Layout
    assert page.mobile_viewport_configured is True
    # 10. Conversion Paths
    assert any("Demo" in cta or "Pricing" in cta for cta in page.cta_elements)
    assert page.forms_count == 1


def test_phase7_2_provenance_isolation():
    html = "<html><body><h1>Sample</h1></body></html>"

    # Ingest target page
    target_page = competitor_ingestion_engine.ingest_page(
        url="https://mytarget.com/",
        domain="mytarget.com",
        html_content=html,
        audit_run_id="run_100",
        scope=ProvenanceScope.TARGET_DOMAIN,
    )
    # Ingest competitor page
    competitor_page = competitor_ingestion_engine.ingest_page(
        url="https://rival.com/",
        domain="rival.com",
        html_content=html,
        audit_run_id="run_100",
        scope=ProvenanceScope.COMPETITOR_BENCHMARK,
    )

    # Verify provenance isolation
    assert target_page.provenance.scope == ProvenanceScope.TARGET_DOMAIN
    assert target_page.provenance.storage_partition == "target_audits"
    assert "TARGET_DOMAIN" in target_page.provenance.provenance_id

    assert competitor_page.provenance.scope == ProvenanceScope.COMPETITOR_BENCHMARK
    assert competitor_page.provenance.storage_partition == "competitors"
    assert "COMPETITOR_BENCHMARK" in competitor_page.provenance.provenance_id


# ============================================================================
# Phase 7.3: Competitive SEO Intelligence
# ============================================================================

def test_phase7_3_competitive_seo_intelligence():
    t_art = competitor_ingestion_engine.ingest_competitor_site(
        "target.com",
        [{"url": "https://target.com/", "html": "<html><title>Target</title><body><h1>Target</h1><p>Word " * 50 + "</p></body></html>", "ttfb_ms": 150.0}],
    )
    c_art = competitor_ingestion_engine.ingest_competitor_site(
        "rival.com",
        [{"url": "https://rival.com/", "html": "<html><title>Rival</title><body><h1>Rival</h1><p>Word " * 20 + "</p></body></html>", "ttfb_ms": 300.0}],
    )

    comparison = competitive_seo_engine.compare_seo(
        target_domain="target.com",
        target_artifact=t_art,
        competitor_artifact=c_art,
        target_keywords=["seo audit", "rank checker"],
        competitor_keywords=["seo audit", "backlink monitor"],
    )

    assert comparison.keyword_coverage["shared_keywords_count"] == 1
    assert "backlink monitor" in comparison.keyword_coverage["competitor_exclusive_keywords_sample"]
    assert comparison.content_depth["target_avg_word_count"] > comparison.content_depth["competitor_avg_word_count"]
    assert comparison.technical_quality["technical_speed_winner"] == "target.com"
    # Backlinks should report UNMEASURED when unattached
    assert comparison.backlink_profiles["status"] == "UNMEASURED"
    assert comparison.seo_parity_score >= 60


# ============================================================================
# Phase 7.4: Competitive GEO Intelligence
# ============================================================================

def test_phase7_4_competitive_geo_intelligence():
    t_art = competitor_ingestion_engine.ingest_competitor_site(
        "brand-a.com",
        [{"url": "https://brand-a.com/", "html": '<html><script type="application/ld+json">{"@type": "Organization"}</script></html>'}],
    )
    c_art = competitor_ingestion_engine.ingest_competitor_site(
        "brand-b.com",
        [{"url": "https://brand-b.com/", "html": "<html><body>No schema</body></html>"}],
    )

    t_robots = "User-agent: GPTBot\nAllow: /\nUser-agent: PerplexityBot\nAllow: /"
    c_robots = "User-agent: GPTBot\nDisallow: /"

    llm_evals = {
        "mentions": {"brand-a.com": 8, "brand-b.com": 2},
        "total_evaluations": 10,
        "citation_counts": {"brand-a.com": 6, "brand-b.com": 1},
        "tier1_citations": {"brand-a.com": 3, "brand-b.com": 0},
    }

    geo_comp = competitive_geo_engine.compare_geo(
        target_domain="brand-a.com",
        target_artifact=t_art,
        competitor_artifact=c_art,
        target_robots_txt=t_robots,
        competitor_robots_txt=c_robots,
        llm_benchmark_results=llm_evals,
    )

    assert geo_comp.entity_clarity["target_has_org_schema"] is True
    assert geo_comp.entity_clarity["competitor_has_org_schema"] is False
    assert "gptbot" in geo_comp.ai_crawler_accessibility["target_allowed_bots"]
    assert "gptbot" in geo_comp.ai_crawler_accessibility["competitor_blocked_bots"]
    assert geo_comp.ai_mentions["target_sov_pct"] == 80.0
    assert geo_comp.geo_parity_score >= 70


# ============================================================================
# Phase 7.5: Competitive AEO Intelligence
# ============================================================================

def test_phase7_5_competitive_aeo_intelligence():
    t_art = competitor_ingestion_engine.ingest_competitor_site(
        "company-a.com",
        [{"url": "https://company-a.com/", "html": '<html><script type="application/ld+json">{"@type": "FAQPage"}</script><h1>What is company-a?</h1><p>' + ("Standalone concise answer text here for the user to read carefully. " * 3) + '</p></html>'}],
    )
    # Competitor has pricing page and answers pricing questions
    c_art = competitor_ingestion_engine.ingest_competitor_site(
        "company-b.com",
        [
            {"url": "https://company-b.com/", "html": "<html><h1>Overview</h1></html>"},
            {"url": "https://company-b.com/pricing", "html": "<html><h1>How much does company-b cost?</h1><p>Our pricing starts at $49/mo.</p></html>"},
        ],
    )

    aeo_comp = competitive_aeo_engine.compare_aeo(
        target_domain="company-a.com",
        target_artifact=t_art,
        competitor_artifact=c_art,
    )

    assert aeo_comp.answer_completeness["target_has_faq_schema"] is True
    # Company A has no pricing page, so pricing question is flagged as unanswered
    assert len(aeo_comp.unanswered_commercial_questions) >= 1
    assert any("pricing" in q.lower() for q in aeo_comp.unanswered_commercial_questions)


# ============================================================================
# Phase 7.6: Competitive CRO Intelligence & Checkout Guardrail
# ============================================================================

def test_phase7_6_competitive_cro_untested_checkout_guardrail():
    t_art = competitor_ingestion_engine.ingest_competitor_site(
        "store-a.com",
        [{"url": "https://store-a.com/", "html": "<html><h1>Best Clean Oral Care</h1><button>Get Started</button></html>"}],
    )
    c_art = competitor_ingestion_engine.ingest_competitor_site(
        "store-b.com",
        [{"url": "https://store-b.com/", "html": "<html><h1>Oral Products</h1><a href='/pricing'>Pricing</a></html>"}],
    )

    # When live checkout was NOT tested
    cro_untested = competitive_cro_engine.compare_cro(
        target_domain="store-a.com",
        target_artifact=t_art,
        competitor_artifact=c_art,
        live_checkout_tested=False,
    )

    # Zero-fabrication check: must report CHECKOUT_FLOW_UNTESTED
    assert cro_untested.checkout_tested is False
    assert cro_untested.checkout_status == "CHECKOUT_FLOW_UNTESTED"
    assert "No functional synthetic checkout test" in cro_untested.checkout_friction["notes"]


def test_phase7_6_competitive_cro_tested_checkout():
    t_art = competitor_ingestion_engine.ingest_competitor_site(
        "store-a.com",
        [{"url": "https://store-a.com/", "html": "<html><h1>Store A</h1></html>"}],
    )
    c_art = competitor_ingestion_engine.ingest_competitor_site(
        "store-b.com",
        [{"url": "https://store-b.com/", "html": "<html><h1>Store B</h1></html>"}],
    )

    # When live checkout WAS tested
    checkout_ev = {
        "target_steps": 2,
        "competitor_steps": 4,
        "guest_checkout": True,
        "verdict": "Target has 2 fewer steps and guest checkout.",
    }
    cro_tested = competitive_cro_engine.compare_cro(
        target_domain="store-a.com",
        target_artifact=t_art,
        competitor_artifact=c_art,
        live_checkout_tested=True,
        checkout_test_evidence=checkout_ev,
    )

    assert cro_tested.checkout_tested is True
    assert cro_tested.checkout_status == "TESTED_AND_VERIFIED"
    assert cro_tested.checkout_friction["target_checkout_steps"] == 2


# ============================================================================
# Phase 7.7: Opportunity Gap Engine
# ============================================================================

def test_phase7_7_opportunity_gap_engine():
    # Setup mock comparisons
    t_art = competitor_ingestion_engine.ingest_competitor_site("saas.com", [{"url": "https://saas.com/", "html": "<html><h1>SaaS</h1></html>"}])
    c_art = competitor_ingestion_engine.ingest_competitor_site("rival.com", [{"url": "https://rival.com/pricing", "html": "<html><h1>Pricing</h1></html>"}])

    seo_comp = competitive_seo_engine.compare_seo(
        "saas.com", t_art, c_art,
        target_keywords=["keyword a"], competitor_keywords=["keyword a", "keyword b missing"]
    )
    geo_comp = competitive_geo_engine.compare_geo(
        "saas.com", t_art, c_art,
        llm_benchmark_results={"tier1_citations": {"saas.com": 0, "rival.com": 4}}
    )
    aeo_comp = competitive_aeo_engine.compare_aeo(
        "saas.com", t_art, c_art
    )
    cro_comp = competitive_cro_engine.compare_cro(
        "saas.com", t_art, c_art
    )

    report = opportunity_gap_engine.generate_opportunity_gaps(
        target_domain="saas.com",
        seo_comparisons=[seo_comp],
        geo_comparisons=[geo_comp],
        aeo_comparisons=[aeo_comp],
        cro_comparisons=[cro_comp],
    )

    assert report.total_gaps_identified > 0
    # Check that opportunities are ranked with ICE scores
    assert report.ranked_opportunities[0].ice_score >= report.ranked_opportunities[-1].ice_score
    # Verify presence of actionable playbooks and proof URLs
    for gap in report.ranked_opportunities:
        assert gap.proof_url.startswith("http")
        assert len(gap.actionable_playbook) > 20
        assert gap.gap_type in [
            OpportunityGapType.UNANSWERED_QUESTION,
            OpportunityGapType.AUTHORITY_REPUTATION,
            OpportunityGapType.COMMERCIAL_CLARITY,
            OpportunityGapType.CONVERSION_JOURNEY,
            OpportunityGapType.UNMET_SEARCH_INTENT,
        ]


# ============================================================================
# Phase 7.8: Competitive Scoring & 10/10 Acceptance Ledger
# ============================================================================

def test_phase7_8_competitive_scoring_and_provenance_ledger():
    t_art = competitor_ingestion_engine.ingest_competitor_site("mybrand.com", [{"url": "https://mybrand.com/", "html": "<html><title>My Brand</title></html>"}])
    c_art = competitor_ingestion_engine.ingest_competitor_site("rivalbrand.com", [{"url": "https://rivalbrand.com/", "html": "<html><title>Rival Brand</title></html>"}])

    seo_comp = competitive_seo_engine.compare_seo("mybrand.com", t_art, c_art)
    geo_comp = competitive_geo_engine.compare_geo("mybrand.com", t_art, c_art)
    aeo_comp = competitive_aeo_engine.compare_aeo("mybrand.com", t_art, c_art)
    cro_comp = competitive_cro_engine.compare_cro("mybrand.com", t_art, c_art)

    scorecard = competitive_scorecard_engine.build_scorecard(
        target_domain="mybrand.com",
        seo_comparisons=[seo_comp],
        geo_comparisons=[geo_comp],
        aeo_comparisons=[aeo_comp],
        cro_comparisons=[cro_comp],
        sample_pages_count=5,
    )

    # 4 Decoupled scores
    assert scorecard.seo_score.discipline == "SEO"
    assert scorecard.geo_score.discipline == "GEO"
    assert scorecard.aeo_score.discipline == "AEO"
    assert scorecard.cro_score.discipline == "CRO"
    assert 0 <= scorecard.overall_competitive_index <= 100

    # 10/10 acceptance standards: Every statement has source, date, methodology
    assert len(scorecard.statements_ledger) >= 4
    for stmt in scorecard.statements_ledger:
        assert stmt.claim_id != ""
        assert stmt.source_url.startswith("http")
        assert isinstance(stmt.observation_date, datetime)
        assert len(stmt.methodology) > 10
        assert stmt.is_comparable is True


# ============================================================================
# Phase 7 End-to-End Orchestration
# ============================================================================

def test_phase7_unified_orchestration_e2e():
    report = unified_competitive_engine.execute_competitive_audit(
        target_domain="target-brand.com",
        target_raw_pages=[
            {"url": "https://target-brand.com/", "html": "<html><head><title>Target Brand</title></head><body><h1>Target Platform</h1><p>Comprehensive solution for modern enterprise teams.</p><button>Get Started</button></body></html>", "ttfb_ms": 160.0}
        ],
        target_facts={
            "business_category": "Enterprise Software",
            "products": ["Platform"],
            "business_model": "B2B",
            "geography": "Global",
        },
        raw_competitor_candidates=[
            {
                "domain": "comp-alpha.com",
                "company_name": "Comp Alpha",
                "business_category": "Enterprise Software Solutions",
                "products": ["Platform", "Analytics"],
                "business_model": "B2B",
                "geography": "Global",
                "serp_overlap_pct": 55.0,
            }
        ],
        competitor_raw_pages_map={
            "comp-alpha.com": [
                {"url": "https://comp-alpha.com/", "html": "<html><head><title>Comp Alpha</title></head><body><h1>Comp Alpha Platform</h1><button>Book Demo</button><button>Sign Up Free</button><button>Start Trial</button><button>Contact Sales</button></body></html>", "ttfb_ms": 230.0},
                {"url": "https://comp-alpha.com/pricing", "html": "<html><head><title>Comp Alpha Pricing</title></head><body><h1>Transparent Pricing</h1><p>Our pricing model starts at $49.</p></body></html>", "ttfb_ms": 200.0},
            ]
        },
        auto_approve_top_k=1,
    )

    assert report.target_domain == "target-brand.com"
    assert len(report.benchmark_group.approved_competitors) == 1
    assert "comp-alpha.com" in report.competitor_artifacts
    assert len(report.seo_comparisons) == 1
    assert len(report.geo_comparisons) == 1
    assert len(report.aeo_comparisons) == 1
    assert len(report.cro_comparisons) == 1
    assert report.opportunity_gaps.total_gaps_identified > 0
    assert report.scorecard.overall_competitive_index > 0

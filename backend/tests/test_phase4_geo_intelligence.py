"""
Test Suite — Phase 4: Generative Engine Optimization (GEO) Intelligence (10/10 Transformation)

Verifies all 10 sub-phases:
- 4.1: Brand & Entity Understanding (Canonical brand facts registry, evidence state tracking)
- 4.2: AI Crawler Accessibility (Search vs. training vs. user-fetch crawler purpose separation)
- 4.3: Machine-Readable Content Readiness (8-point passage test, ambiguous pronouns, density)
- 4.4: AI Answer Readiness (8-category Question Universe, source-to-answer mapping, blindspots)
- 4.5: Live AI Answer Benchmarking (Honest untested surface reporting, zero fake citations)
- 4.6: AI Citation Intelligence (Immutable Citation Evidence Ledger, third-party dominance)
- 4.7: External Authority & Reputation (Independent corroboration vs. unverified first-party claims)
- 4.8: Competitor AI Visibility (Uniform benchmark conditions, SOV, recommendation win rate)
- 4.9: Two-Layer GEO Scorecard (Strict firewall: Content Readiness vs. Observed Visibility)
- 4.10: GEO Remediation & Pre/Post Verification (Code patches, pre/post citation rate delta)
"""
import pytest
from app.geo.intelligence.brand_entity_intelligence import (
    BrandEntityIntelligenceAgent,
    BrandEntityProfile,
    BrandFactRecord,
    FactEvidenceState,
)
from app.geo.intelligence.crawler_accessibility import (
    CrawlerAccessibilityEngine,
    CrawlerAccessibilityReport,
    CrawlerPurpose,
)
from app.geo.intelligence.content_readiness import (
    ContentReadinessEngine,
    ContentReadinessReport,
)
from app.geo.intelligence.answer_readiness import (
    AnswerReadinessEngine,
    AnswerReadinessReport,
    QuestionCategory,
)
from app.geo.intelligence.live_benchmarking import (
    LiveBenchmarkingEngine,
    LiveBenchmarkRunReport,
)
from app.geo.intelligence.citation_intelligence import (
    CitationIntelligenceAgent,
    CitationIntelligenceReport,
)
from app.geo.intelligence.external_reputation import (
    ExternalReputationEngine,
    ExternalReputationReport,
)
from app.geo.intelligence.competitor_visibility import (
    CompetitorVisibilityEngine,
    CompetitorVisibilityReport,
)
from app.geo.intelligence.geo_scorecard import (
    GeoScorecardEngine,
    TwoLayerGeoScorecardReport,
)
from app.geo.intelligence.remediation_verification import (
    GeoRemediationVerificationEngine,
    GeoVerificationReport,
)


# ============================================================================
# Phase 4.1: Brand & Entity Understanding
# ============================================================================

def test_phase4_1_brand_entity_intelligence():
    domain = "perfora.co"
    homepage_html = """
    <html>
    <head><title>Perfora - Oral Care Reimagined</title></head>
    <body>
        <p>Copyright © 2024 Chipper Consumer Products Pvt Ltd (Perfora). All rights reserved.</p>
        <p>Registered Office: 45 Cyber Hub, Gurugram, India</p>
        <a href="https://instagram.com/perforacare">Instagram</a>
    </body>
    </html>
    """
    schemas = [
        {"@type": "Organization", "name": "Perfora", "url": "https://perfora.co"}
    ]
    pages = [
        {"url": "https://perfora.co/products/electric-toothbrush", "title": "Electric Toothbrush"},
        {"url": "https://perfora.co/products/probiotic-mouthwash", "title": "Probiotics Mouthwash"},
    ]

    profile: BrandEntityProfile = BrandEntityIntelligenceAgent.extract_brand_profile(
        domain=domain,
        homepage_html=homepage_html,
        page_records=pages,
        schema_entities=schemas,
    )

    # 1. Brand Name
    assert profile.brand_name.attribute_value == "Perfora"
    assert profile.brand_name.evidence_state == FactEvidenceState.OBSERVED

    # 2. Category
    assert profile.business_category.evidence_state == FactEvidenceState.SAMPLE_VERIFIED
    assert "Oral" in profile.business_category.attribute_value

    # 3. Products
    assert len(profile.products_services.attribute_value) == 2
    assert profile.products_services.evidence_state == FactEvidenceState.SAMPLE_VERIFIED

    # 4. Social Profiles
    assert len(profile.social_profiles.attribute_value) >= 1
    assert profile.social_profiles.evidence_state == FactEvidenceState.OBSERVED

    # Guardrail check: Inferences are strictly labeled
    assert profile.overall_confidence > 0.80
    assert len(profile.facts_registry) == 10


# ============================================================================
# Phase 4.2: AI Crawler Accessibility
# ============================================================================

def test_phase4_2_ai_crawler_accessibility():
    # Robots.txt blocks GPTBot (training) but permits OAI-SearchBot and PerplexityBot (search retrieval)
    robots_txt = """
    User-agent: GPTBot
    Disallow: /

    User-agent: ClaudeBot
    Disallow: /

    User-agent: OAI-SearchBot
    Allow: /

    User-agent: PerplexityBot
    Allow: /
    """
    report: CrawlerAccessibilityReport = CrawlerAccessibilityEngine.evaluate_crawler_access(
        robots_txt=robots_txt,
    )

    # Purpose separation guardrail
    assert report.search_retrieval_allowed is True
    assert report.model_training_allowed is False

    # Check bot breakdown
    search_bot = next(b for b in report.crawlers_evaluated if b.bot_name == "OAI-SearchBot")
    assert search_bot.is_allowed is True
    assert search_bot.purpose == CrawlerPurpose.SEARCH_RETRIEVAL

    train_bot = next(b for b in report.crawlers_evaluated if b.bot_name == "GPTBot")
    assert train_bot.is_allowed is False
    assert train_bot.purpose == CrawlerPurpose.MODEL_TRAINING


# ============================================================================
# Phase 4.3: Machine-Readable Content Readiness & Passage Test
# ============================================================================

def test_phase4_3_machine_readable_content_and_passage_test():
    # Text with one good passage and one ambiguous passage starting with pronoun
    body = (
        "Perfora smart sonic electric toothbrush features 26,000 vibrations per minute and an integrated 2-minute quad-interval smart timer. "
        "The product contains dentist-approved ultra-soft bristles and is clinically validated to reduce plaque by 42%. Products are priced starting at $29. "
        "They offer revolutionary and world-class care that will change your life forever. "
        "These solutions deliver miraculous results without any effort."
    )

    report: ContentReadinessReport = ContentReadinessEngine.test_page_passages(
        url="https://perfora.co/products/brush",
        body_text=body,
        brand_name="Perfora",
    )

    assert report.total_passages_tested >= 1
    assert report.has_pricing_declared is True
    # Verify ambiguous pronouns detected
    ambig_passage = next((p for p in report.passages if p.ambiguous_pronouns_detected), None)
    assert ambig_passage is not None
    assert any(pron in ambig_passage.ambiguous_pronouns_detected for pron in ["they", "these"])
    assert "world-class" in ambig_passage.unsupported_claims_detected


# ============================================================================
# Phase 4.4: AI Answer Readiness & Question Universe
# ============================================================================

def test_phase4_4_ai_answer_readiness():
    pages = [
        {"url": "https://perfora.co/", "title": "Perfora Oral Care", "body_text": "Perfora sells smart sonic electric toothbrushes and probiotics mouthwash."},
        {"url": "https://perfora.co/pricing", "title": "Pricing & Plans", "body_text": "Electric toothbrushes cost $29 with monthly subscription brush heads."},
        {"url": "https://perfora.co/returns", "title": "Return Policy", "body_text": "We offer a 30-day money-back guarantee and free domestic shipping."},
    ]

    report: AnswerReadinessReport = AnswerReadinessEngine.evaluate_answer_readiness(
        domain="perfora.co",
        brand_name="Perfora",
        product_category="oral care products",
        crawled_pages=pages,
    )

    assert report.total_questions_in_universe == 11
    assert report.answered_questions_count >= 3
    # Verify blindspots are flagged
    assert report.unanswered_blindspots_count > 0
    categories = {m.category for m in report.question_mappings}
    assert QuestionCategory.BRAND_DISCOVERY in categories
    assert QuestionCategory.COMMERCIAL_RESEARCH in categories
    assert QuestionCategory.PRODUCT_COMPARISONS in categories


# ============================================================================
# Phase 4.5: Live AI Answer Benchmarking (Honest Untested Reporting)
# ============================================================================

def test_phase4_5_live_benchmarking_honesty():
    # Only Perplexity is configured; other surfaces are unconfigured
    active_responses = {
        "Perplexity AI": {
            "response_text": "The top choice for gentle oral wellness is Perfora. Perfora offers sonic toothbrushes designed with ultra-soft bristles.",
            "citations": ["https://perfora.co/products/brush", "https://dentistrytoday.com/reviews"],
            "latency_ms": 1100.0,
        }
    }

    report: LiveBenchmarkRunReport = LiveBenchmarkingEngine.execute_benchmark_query(
        domain="perfora.co",
        brand_name="Perfora",
        query="What is the best electric toothbrush for sensitive teeth in India?",
        active_surface_responses=active_responses,
        competitor_names=["Oral-B", "Colgate"],
    )

    assert report.surfaces_tested_count == 1
    assert report.surfaces_untested_count == 4
    assert report.overall_mention_rate == 100.0
    assert report.overall_citation_rate == 100.0

    # Guardrail check: Untested surfaces explicitly declare reason
    chatgpt_res = next(s for s in report.surface_results if s.surface_name == "ChatGPT Search")
    assert chatgpt_res.status == "SURFACE_UNTESTED"
    assert "No active API connection" in chatgpt_res.untested_reason


# ============================================================================
# Phase 4.6: AI Citation Intelligence & Evidence Ledger
# ============================================================================

def test_phase4_6_citation_intelligence_and_ledger():
    probed_data = [
        {
            "query": "Best sonic toothbrush India",
            "surface": "Perplexity AI",
            "citations": [
                "https://perfora.co/products/electric-toothbrush",
                "https://amazon.in/dp/B09XYZ",
                "https://reddit.com/r/india/comments/toothbrush",
            ],
            "response": "Perfora is recommended for sensitive gums.",
        },
        {
            "query": "Perfora toothbrush reviews",
            "surface": "ChatGPT Search",
            "citations": [
                "https://amazon.in/dp/B09XYZ",
                "https://trustpilot.com/review/perfora.co",
            ],
            "response": "User reviews on Amazon and Trustpilot rate Perfora 4.4 out of 5.",
        },
    ]

    report: CitationIntelligenceReport = CitationIntelligenceAgent.record_and_analyze_citations(
        domain="perfora.co",
        brand_name="Perfora",
        probed_queries_data=probed_data,
    )

    assert report.total_citations_recorded == 5
    assert report.first_party_citations_count == 1
    assert report.third_party_citations_count == 4
    assert report.first_party_share_pct == 20.0
    # Third-party dominance detected
    assert report.third_party_dominance_detected is True
    assert len(report.ledger_entries) == 5
    assert report.ledger_entries[0].validation_status == "VERIFIED_LIVE"


# ============================================================================
# Phase 4.7: External Authority & Reputation
# ============================================================================

def test_phase4_7_external_reputation():
    claims = [
        "Clinically proven 42% plaque reduction",
        "World-renowned dentist formula",
    ]
    external_sources = [
        {"name": "Vogue India", "type": "EDITORIAL", "fact": "Featured Perfora in top eco-friendly oral brands 2024.", "url": "https://vogue.in/perfora"},
        {"name": "Trustpilot", "type": "REVIEW_PORTAL", "rating": 4.5, "fact": "Verified rating of 4.5 across 850 reviews."},
    ]

    report: ExternalReputationReport = ExternalReputationEngine.evaluate_reputation(
        brand_name="Perfora",
        first_party_claims=claims,
        external_sources=external_sources,
        has_kg_entity=False,
    )

    assert report.total_corroborating_sources == 2
    assert report.editorial_coverage_count == 1
    assert report.third_party_review_rating == 4.5
    # Guardrail check: First party claims without 3rd party corroboration are flagged
    assert len(report.unverified_first_party_claims) >= 1
    assert any("UNVERIFIED_FIRST_PARTY" in c for c in report.unverified_first_party_claims)


# ============================================================================
# Phase 4.8: Competitor AI Visibility Benchmark
# ============================================================================

def test_phase4_8_competitor_visibility_benchmark():
    probed_responses = [
        {
            "query": "Best electric toothbrush India",
            "response": "The top choice is Oral-B Pro 1000, followed by Perfora sonic toothbrush.",
            "citations": ["https://oralb.com/pro", "https://perfora.co/products/brush"],
        },
        {
            "query": "Smart toothbrush with timer",
            "response": "Oral-B is the winner for smart timers. Colgate also provides options.",
            "citations": ["https://oralb.com/smart", "https://colgate.com/timer"],
        },
    ]

    report: CompetitorVisibilityReport = CompetitorVisibilityEngine.compare_competitors(
        target_brand="Perfora",
        competitors=["Oral-B", "Colgate"],
        probed_responses=probed_responses,
    )

    assert report.competitors_compared_count == 2
    assert len(report.leaderboard) == 3
    # Oral-B had 2 mentions & 2 citations -> Leader
    assert report.winner_entity == "Oral-B"
    assert report.target_brand_rank == 2
    assert "ranks #2" in report.competitive_displacement_verdict


# ============================================================================
# Phase 4.9: Two-Layer GEO Scorecard (Strict Firewall)
# ============================================================================

def test_phase4_9_two_layer_geo_scorecard_unmeasured_visibility():
    # Layer 1 is measured, but Layer 2 is inactive (no live connectors)
    card: TwoLayerGeoScorecardReport = GeoScorecardEngine.calculate_two_layer_scorecard(
        entity_clarity_score=85.0,
        content_extractability_score=78.0,
        crawler_accessibility_score=95.0,
        factual_grounding_score=80.0,
        live_connectors_ran=False,
    )

    # Layer 1 is fully measured
    assert card.layer_1_readiness_score > 80.0
    assert card.layer_1_status == "MEASURED"

    # Layer 2 firewall guardrail: strictly NOT_MEASURED
    assert card.is_visibility_measured is False
    assert card.layer_2_visibility_score is None
    assert card.layer_2_status == "NOT_MEASURED"
    assert "never merged" in card.firewall_disclosure_statement


def test_phase4_9_two_layer_geo_scorecard_both_measured():
    # Both layers measured
    card: TwoLayerGeoScorecardReport = GeoScorecardEngine.calculate_two_layer_scorecard(
        entity_clarity_score=85.0,
        content_extractability_score=78.0,
        crawler_accessibility_score=95.0,
        factual_grounding_score=80.0,
        live_connectors_ran=True,
        external_authority_score=75.0,
        ai_mention_score=80.0,
        citation_score=70.0,
        competitive_score=65.0,
    )

    assert card.is_visibility_measured is True
    assert card.layer_1_readiness_score > 0
    assert card.layer_2_visibility_score == 72.5
    assert card.layer_2_status == "MEASURED"


# ============================================================================
# Phase 4.10: GEO Remediation & Pre/Post Verification
# ============================================================================

def test_phase4_10_remediation_and_pre_post_verification():
    # 1. Generate Recommendations
    recs = GeoRemediationVerificationEngine.generate_recommendations(
        domain="perfora.co",
        brand_name="Perfora",
        blocked_crawlers=["OAI-SearchBot"],
        third_party_dominance=True,
    )
    assert len(recs) >= 3
    rec_targets = {r.target_area for r in recs}
    assert "ROBOTS_TXT" in rec_targets
    assert "BRAND_SCHEMA" in rec_targets
    assert "PASSAGE_RESTRUCTURE" in rec_targets

    # 2. Pre vs. Post Benchmark Comparison
    pre_runs = [
        {"query": "Best electric toothbrush", "surface": "Perplexity", "cited": False, "mentioned": True},
        {"query": "Perfora price", "surface": "Perplexity", "cited": True, "mentioned": True},
    ]
    post_runs = [
        {"query": "Best electric toothbrush", "surface": "Perplexity", "cited": True, "mentioned": True},  # Improved
        {"query": "Perfora price", "surface": "Perplexity", "cited": True, "mentioned": True},
    ]

    verif: GeoVerificationReport = GeoRemediationVerificationEngine.compare_pre_post_benchmarks(
        domain="perfora.co",
        pre_runs=pre_runs,
        post_runs=post_runs,
    )

    assert verif.benchmarks_retested_count == 2
    assert verif.improved_queries_count == 1
    assert verif.net_citation_rate_delta == 50.0  # from 50% to 100% (+50%)
    assert verif.comparison_results[0].status_change == "IMPROVED"

"""
Test Suite — Phase 3: Technical SEO Intelligence (10/10 Transformation)

Verifies all 12 sub-phases:
- 3.1: Crawlability & Indexability (Robots policy, indexability, URL architecture)
- 3.2: Technical Infrastructure (12 diagnostic checks, observation vs ranking factor guardrail)
- 3.3: Dual-Track CWV & Performance (Strict Lab vs Field separation, zero fake CrUX)
- 3.4: On-Page SEO (17 diagnostic vectors)
- 3.5: Search Intent & Cannibalization (Intent categorization, cannibalization, demand honesty)
- 3.6: Structured Data & Entity Architecture (Syntax validity vs Google Rich Results eligibility)
- 3.7: Internal Linking Graph (Click depth, orphan pages, PageRank proxy, broken links)
- 3.8: Image & Media Intelligence (WCAG decorative alt="" rule, responsive srcset, LCP hero checks)
- 3.9: Mobile SEO & Responsive Experience (Viewport, horizontal overflow, tap targets, parity)
- 3.10: External Authority Safeguard (Zero manufactured backlinks when disconnected)
- 3.11: Versioned 9-Dimension Scorecard (Weighted formula, PARTIAL_ASSESSMENT on missing authority)
- 3.12: SEO Remediation Intelligence (Mandatory 14-point Finding Contract & CLI verification tests)
"""
import pytest
from app.seo.intelligence.crawlability_indexability import (
    RobotsPolicyAnalyzer,
    IndexabilityAnalyzer,
    UrlArchitectureAuditor,
)
from app.seo.intelligence.technical_infrastructure import (
    TechnicalInfrastructureDiagnostic,
    TechnicalInfrastructureDiagnosticReport,
)
from app.seo.intelligence.performance_cwv import (
    DualTrackPerformanceEngine,
    DualTrackPerformanceReport,
)
from app.seo.intelligence.on_page import (
    OnPageSeoEngine,
    PageOnPageReport,
)
from app.seo.intelligence.search_intent import (
    SearchIntentAgent,
    SearchIntentReport,
    SearchIntentType,
)
from app.seo.intelligence.structured_data import (
    StructuredDataEngine,
    StructuredDataReport,
)
from app.seo.intelligence.internal_linking_graph import (
    InternalLinkingGraphEngine,
    InternalLinkingGraphReport,
)
from app.seo.intelligence.media_intelligence import (
    MediaIntelligenceEngine,
    MediaIntelligenceReport,
)
from app.seo.intelligence.mobile_experience import (
    MobileExperienceEngine,
    MobileExperienceReport,
)
from app.seo.intelligence.external_authority import (
    ExternalAuthorityEngine,
    BacklinkProfile,
)
from app.seo.intelligence.seo_scorecard import (
    SeoScorecardEngine,
    SeoScorecardReport,
)
from app.seo.intelligence.remediation_intelligence import (
    SeoRemediationEngine,
    EngineeringSeoFinding,
    PostFixStatus,
)


# ============================================================================
# Phase 3.1: Crawlability & Indexability
# ============================================================================

def test_phase3_1_crawlability_and_indexability():
    # 3.1.1: Robots.txt
    robots_txt = """
    User-agent: *
    Disallow: /admin
    Allow: /admin/login
    Disallow: /admin/login
    Disallow: /static/critical.css
    Sitemap: https://perfora.co/sitemap.xml
    """
    report = RobotsPolicyAnalyzer.parse_robots_txt(
        robots_txt,
        resource_urls=["https://perfora.co/static/critical.css"]
    )
    assert report.has_robots_txt is True
    assert len(report.sitemap_declarations) == 1
    assert len(report.conflicting_directives) >= 1  # conflicting Allow/Disallow on /admin/login
    assert "https://perfora.co/static/critical.css" in report.blocked_critical_resources
    assert report.googlebot_allowed is True

    # 3.1.2: Indexability
    html_noindex = "<html><head><meta name='robots' content='noindex, follow'></head><body>Content</body></html>"
    index_res = IndexabilityAnalyzer.evaluate_page(
        url="https://perfora.co/checkout",
        status_code=200,
        html=html_noindex,
    )
    assert index_res.is_indexable is False
    assert index_res.noindex_detected is True
    assert index_res.noindex_source == "HTML_META"

    # Soft 404 detection
    soft_404_res = IndexabilityAnalyzer.evaluate_page(
        url="https://perfora.co/missing-brush",
        status_code=200,
        html="<html><body><h1>404 Not Found</h1><p>Page not found</p></body></html>",
    )
    assert soft_404_res.is_soft_404 is True
    assert soft_404_res.is_indexable is False

    # 3.1.3: URL Architecture
    url_audit = UrlArchitectureAuditor.audit_url("https://perfora.co/products/category_sub/ELECTRIC_BRUSH?utm_source=fb")
    assert url_audit.folder_depth == 3
    assert url_audit.has_parameter_pollution is True
    assert any("underscore" in d.lower() for d in url_audit.architectural_defects)
    assert any("uppercase" in d.lower() for d in url_audit.architectural_defects)


# ============================================================================
# Phase 3.2: Technical Infrastructure
# ============================================================================

def test_phase3_2_technical_infrastructure():
    headers = {
        "content-encoding": "br",
        "cf-ray": "8937129712a-BOM",
        "cache-control": "public, max-age=31536000",
    }
    report: TechnicalInfrastructureDiagnosticReport = TechnicalInfrastructureDiagnostic.evaluate_infrastructure(
        domain="perfora.co",
        headers=headers,
        ttfb_ms=280.0,
        protocol="HTTP/2",
        cert_days_remaining=120,
    )

    assert len(report.checks) == 12
    # Verify strict guardrail: compression check does not claim ranking factor
    comp_check = next(c for c in report.checks if c.check_name == "Payload Compression")
    assert comp_check.status == "PASS"
    assert comp_check.is_ranking_factor_claim is False

    # TTFB check
    ttfb_check = next(c for c in report.checks if c.check_name == "Server Response Timing (TTFB)")
    assert ttfb_check.status == "PASS"
    assert ttfb_check.is_ranking_factor_claim is True  # TTFB is an official CWV component


# ============================================================================
# Phase 3.3: Dual-Track CWV & Performance (Strict Separation)
# ============================================================================

def test_phase3_3_dual_track_performance():
    # Track A only (Field unavailable)
    perf_report = DualTrackPerformanceEngine.evaluate_performance(
        url="https://perfora.co/",
        lcp_ms=2100.0,
        cls_score=0.04,
        field_connected=False,
    )

    assert perf_report.track_a_laboratory.lab_grade == "GOOD"
    assert perf_report.track_b_field.is_measured is False
    assert perf_report.track_b_field.status == "FIELD_UNAVAILABLE"
    assert "CrUX" in perf_report.track_b_field.statement

    # Track A + Track B connected
    perf_report_field = DualTrackPerformanceEngine.evaluate_performance(
        url="https://perfora.co/",
        lcp_ms=2100.0,
        cls_score=0.04,
        field_connected=True,
        crux_p75_lcp=2350.0,
        crux_p75_cls=0.05,
        field_source="CRUX",
    )
    assert perf_report_field.track_b_field.is_measured is True
    assert perf_report_field.track_b_field.status == "FIELD_MEASURED"
    assert perf_report_field.track_b_field.p75_lcp_ms == 2350.0


# ============================================================================
# Phase 3.4: On-Page SEO (17 Vectors)
# ============================================================================

def test_phase3_4_on_page_seo_17_vectors():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Best Electric Toothbrush for Sensitive Teeth - Perfora</title>
        <meta name="description" content="Discover India's smartest sonic electric toothbrush with ultra-soft bristles and smart timer for superior gum health.">
        <meta property="og:title" content="Best Electric Toothbrush - Perfora">
    </head>
    <body>
        <h1>Best Electric Toothbrush for Superior Gum Health</h1>
        <h2>Designed by Leading Dentists</h2>
        <p>Best electric toothbrush for everyday oral wellness. Experience ultra-gentle sonic vibrations with 3 personalized modes.</p>
        <img src="https://perfora.co/products/brush.webp" alt="Perfora smart electric toothbrush in oceanic blue">
        <a href="/oral-care">Explore All Oral Care Products</a>
        <a href="/cart">Go to Checkout</a>
        <a href="https://dentistassociation.org" rel="noopener">Clinical Endorsement</a>
    </body>
    </html>
    """
    report: PageOnPageReport = OnPageSeoEngine.evaluate_page(
        url="https://perfora.co/products/electric-toothbrush",
        html=html,
        target_keyword="best electric toothbrush",
    )

    assert len(report.diagnostics) == 17
    assert report.overall_on_page_score >= 80.0
    # Check H1 uniqueness
    h1_diag = next(d for d in report.diagnostics if d.vector_name == "H1 Uniqueness")
    assert h1_diag.status == "PASS"


# ============================================================================
# Phase 3.5: Search Intent & Demand Intelligence
# ============================================================================

def test_phase3_5_search_intent_and_cannibalization():
    pages = [
        {"url": "https://perfora.co/products/sonic-brush", "title": "Buy Sonic Toothbrush Online - Perfora"},
        {"url": "https://perfora.co/brush-discount", "title": "Buy Sonic Toothbrush Online - Perfora"},
        {"url": "https://perfora.co/blog/how-to-brush", "title": "How to Brush Teeth Properly - Complete Guide"},
    ]

    report: SearchIntentReport = SearchIntentAgent.analyze_site_intent(
        domain="perfora.co",
        pages=pages,
        gsc_queries=None,  # GSC not connected
    )

    assert report.has_gsc_connected is False
    assert "UNMEASURED" in report.demand_measurement_statement
    assert len(report.cannibalization_issues) >= 1  # 2 URLs sharing "buy sonic toothbrush online"
    assert report.cannibalization_issues[0].intent == SearchIntentType.TRANSACTIONAL
    assert len(report.search_journey) == 3


# ============================================================================
# Phase 3.6: Structured Data & Entity Architecture
# ============================================================================

def test_phase3_6_structured_data_and_rich_results():
    # Syntactically valid JSON-LD Product schema, but missing required Google fields (image and offers)
    html_syntax_valid_but_not_rich = """
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Perfora Smart Electric Toothbrush"
    }
    </script>
    """
    report: StructuredDataReport = StructuredDataEngine.analyze_page_structured_data(
        url="https://perfora.co/products/brush",
        html=html_syntax_valid_but_not_rich,
    )

    assert report.total_entities_found == 1
    entity = report.entities[0]
    assert entity.is_valid_syntax is True
    # Guardrail: Valid syntax != Rich Result eligible
    assert entity.is_rich_result_eligible is False
    assert "offers" in entity.eligibility_details.missing_required_fields


# ============================================================================
# Phase 3.7: Internal Linking Graph
# ============================================================================

def test_phase3_7_internal_linking_graph():
    crawl_pages = [
        {
            "url": "https://perfora.co/",
            "status": 200,
            "links": [
                {"target": "https://perfora.co/products", "anchor": "Shop Oral Care"},
                {"target": "https://perfora.co/about", "anchor": "Our Story"},
            ],
        },
        {
            "url": "https://perfora.co/products",
            "status": 200,
            "links": [
                {"target": "https://perfora.co/products/brush", "anchor": "Sonic Brush"},
                {"target": "https://perfora.co/404-broken", "anchor": "Old Product"},
            ],
        },
        {
            "url": "https://perfora.co/about",
            "status": 200,
            "links": [{"target": "https://perfora.co/", "anchor": "Home"}],
        },
        {
            "url": "https://perfora.co/products/brush",
            "status": 200,
            "links": [{"target": "https://perfora.co/", "anchor": "Home"}],
        },
        {
            "url": "https://perfora.co/orphan-landing-page",
            "status": 200,
            "links": [],
        },
        {
            "url": "https://perfora.co/404-broken",
            "status": 404,
            "links": [],
        },
    ]

    graph_report: InternalLinkingGraphReport = InternalLinkingGraphEngine.build_and_analyze_graph(
        homepage_url="https://perfora.co",
        crawl_pages=crawl_pages,
    )

    assert graph_report.total_nodes >= 5
    assert "https://perfora.co/orphan-landing-page" in graph_report.orphan_pages
    assert len(graph_report.broken_internal_links) == 1
    # Check PageRank calculation
    home_node = next(n for n in graph_report.nodes if n.url == "https://perfora.co")
    assert home_node.pagerank_score > 0


# ============================================================================
# Phase 3.8: Image & Media Intelligence
# ============================================================================

def test_phase3_8_image_and_media_intelligence():
    html = """
    <img src="https://perfora.co/hero-banner.jpg" alt="Hero Toothbrush Banner" loading="lazy">
    <img src="https://perfora.co/icons/arrow-right.svg">
    <img src="https://perfora.co/product-showcase.png" alt="Showcase">
    """
    report: MediaIntelligenceReport = MediaIntelligenceEngine.audit_media(html=html, is_hero_image_present=True)

    assert report.total_images_inspected == 3
    # Guardrail 1: Hero image lazy loading flagged
    assert report.lcp_image_lazy_loaded is True
    hero_asset = report.assets[0]
    assert any("LCP hero image is lazy-loaded" in d for d in hero_asset.defects)

    # Guardrail 2: Decorative icon recommended to have empty alt=""
    icon_asset = report.assets[1]
    assert icon_asset.is_decorative is True
    assert any("empty alt=''" in d for d in icon_asset.defects)


# ============================================================================
# Phase 3.9: Mobile SEO & Responsive Experience
# ============================================================================

def test_phase3_9_mobile_experience():
    # Page with viewport meta, but has horizontal overflow and small tap targets
    html = """
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <table width="1200px"><tr><td>Wide Data</td></tr></table>
    """
    rendered_elements = [
        {"selector": "button#buy", "width": 24, "height": 24, "spacing": 4, "is_interactive": True},
        {"selector": "table", "width": 1200, "height": 400, "spacing": 0, "is_interactive": False},
    ]

    report: MobileExperienceReport = MobileExperienceEngine.audit_mobile_viewport(
        url="https://perfora.co/cart",
        html=html,
        viewport_width=390,
        rendered_elements=rendered_elements,
    )

    assert report.has_viewport_meta is True
    assert report.has_horizontal_overflow is True
    # Guardrail: Viewport meta tag alone does not guarantee mobile friendly
    assert report.is_mobile_friendly is False
    assert len(report.failed_touch_targets) >= 1


# ============================================================================
# Phase 3.10: External Authority Safeguard
# ============================================================================

def test_phase3_10_external_authority_safeguard():
    # Unconnected provider (Zero manufactured backlinks)
    unconnected: BacklinkProfile = ExternalAuthorityEngine.evaluate_authority(
        domain="perfora.co",
        provider_name=None,
    )
    assert unconnected.is_measured is False
    assert unconnected.status == "AUTHORITY_UNAVAILABLE"
    assert unconnected.total_backlinks_count is None
    assert "not measured" in unconnected.statement.lower()

    # Connected provider
    connected: BacklinkProfile = ExternalAuthorityEngine.evaluate_authority(
        domain="perfora.co",
        provider_name="DataForSEO",
        api_data={"referring_domains": 450, "total_backlinks": 3200, "dofollow_ratio": 0.82},
    )
    assert connected.is_measured is True
    assert connected.referring_domains_count == 450


# ============================================================================
# Phase 3.11: Versioned 9-Dimension Scorecard
# ============================================================================

def test_phase3_11_versioned_9_dimension_scorecard():
    # External authority is unmeasured (None)
    scores = {
        "Crawlability & Indexability": 90.0,
        "Technical Infrastructure": 85.0,
        "Performance (Core Web Vitals)": 75.0,
        "On-Page SEO": 82.0,
        "Content & Search Intent": 78.0,
        "Structured Data": 70.0,
        "Internal Linking": 80.0,
        "Mobile Experience": 85.0,
        "External Authority": None,  # UNMEASURED
    }

    card: SeoScorecardReport = SeoScorecardEngine.calculate_scorecard(dimension_scores=scores)

    assert card.assessment_status == "PARTIAL_ASSESSMENT"
    assert card.coverage_percentage == 95.0
    assert "External Authority" in card.unmeasured_dimensions
    assert card.overall_score > 0
    assert "not silently redistributed" in card.limitations_disclosure


# ============================================================================
# Phase 3.12: SEO Remediation Intelligence (14-Point Contract)
# ============================================================================

def test_phase3_12_seo_remediation_14_point_contract():
    finding = EngineeringSeoFinding(
        finding_id="SEO-FND-001",
        problem_description="Missing self-referential rel=canonical tag on primary product page.",
        affected_url="https://perfora.co/products/electric-toothbrush",
        affected_element="<head>",
        raw_evidence="<link rel='canonical'> not found in DOM or HTTP Link header.",
        expected_condition="Self-referential rel=canonical matching https://perfora.co/products/electric-toothbrush.",
        observed_condition="Canonical directive absent.",
        severity="HIGH",
        confidence="STRONG",
        root_cause="Shopify theme product template does not inject canonical liquid object.",
        business_relevance="INDEXATION_LOSS",
        recommended_fix="Inject standard self-referential canonical tag in theme.liquid.",
        implementation_instructions="<link rel='canonical' href='{{ canonical_url }}'>",
        verification_command="curl -sI https://perfora.co/products/electric-toothbrush | grep -i canonical",
        post_fix_result=PostFixStatus.NOT_YET_VERIFIED,
    )

    validation = SeoRemediationEngine.validate_finding_contract(finding)
    assert validation["is_valid"] is True
    assert validation["contract_points_satisfied"] == 14

    # Test verification state machine transition
    updated = SeoRemediationEngine.record_verification_result(finding, test_passed=True)
    assert updated.post_fix_result == PostFixStatus.VERIFIED_FIXED

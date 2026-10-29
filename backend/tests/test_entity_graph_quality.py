"""Entity graph quality is completeness and consistency, not type presence."""
from app.domain.enums import BusinessIntent, Category, ImpactLevel
from app.domain.models import BusinessProfile, PageEvidence
from app.intelligence.business.entity_resolver import UniversalEntityResolver
from app.intelligence.geo.entity_graph import evaluate_entity_graph
from app.scoring.calibration import calibrate_finding
from app.scoring.engine import ScoringEngine


def _home(**kwargs) -> PageEvidence:
    base = dict(
        url="https://alienhouse.net/",
        title="AlienHouse Networks",
        h1=["AlienHouse Networks"],
        page_type="homepage",
        body_text="AlienHouse Networks builds private networks for offices.",
        word_count=12,
    )
    base.update(kwargs)
    return PageEvidence(**base)


def _thin_org_pages():
    return [_home(
        external_links=["https://twitter.com/alienhouse"],
        raw_schema=[{
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "AlienHouse Networks",
            "url": "https://alienhouse.net",
            "logo": "https://alienhouse.net/logo.png",
            "description": "AlienHouse Networks builds private networks for offices.",
            "sameAs": ["https://twitter.com/alienhouse"],
        }],
        schema_types=["Organization"],
    )]


def test_five_grounded_properties_are_not_a_perfect_graph():
    report, findings, _ = evaluate_entity_graph(_thin_org_pages())
    assert report.grounding_score == 100
    assert report.completeness_score < 80
    assert report.quality_score < 100
    assert "validated" not in report.summary.lower()
    assert "entity graph quality 100" not in report.summary.lower()
    assert report.present_properties < report.applicable_properties
    assert any(item.rule_id == "entity_graph_incomplete" for item in findings)


def test_organization_name_contradicts_open_graph_site_name():
    pages = [_home(
        og_tags={"og:site_name": "Unknown Business"},
        raw_schema=[{
            "@type": "Organization",
            "name": "AlienHouse Networks",
            "url": "https://alienhouse.net",
        }],
        schema_types=["Organization"],
    )]
    report, findings, contradictions = evaluate_entity_graph(pages)
    conflict = next(item for item in report.conflicts if item.right_surface == "og:site_name")
    assert conflict.left_value == "AlienHouse Networks"
    assert conflict.right_value == "Unknown Business"
    assert conflict.severity == "HIGH"
    assert report.quality_score <= 59
    finding = next(item for item in findings if item.rule_id == "entity_graph_contradiction")
    assert "AlienHouse Networks" in finding.description
    assert "Unknown Business" in finding.description
    assert contradictions[0].reason == conflict.explanation
    resolved = UniversalEntityResolver.resolve_from_evidence("https://alienhouse.net", pages)
    assert resolved.name == "AlienHouse Networks"


def test_legal_suffix_and_www_are_not_high_conflicts():
    legal_pages = [_home(raw_schema=[{
        "@type": "Organization",
        "name": "AlienHouse Networks",
        "legalName": "AlienHouse Networks LLC",
        "url": "https://alienhouse.net",
    }])]
    legal, _, _ = evaluate_entity_graph(legal_pages)
    assert not any(item.severity == "HIGH" and item.field == "name" for item in legal.conflicts)

    www_pages = [_home(
        canonical_url="https://alienhouse.net/",
        og_tags={"og:url": "https://alienhouse.net/"},
        raw_schema=[{
            "@type": "Organization",
            "name": "AlienHouse Networks",
            "url": "https://www.alienhouse.net",
        }],
    )]
    www, _, _ = evaluate_entity_graph(www_pages)
    assert not any(item.severity == "HIGH" and item.field == "url" for item in www.conflicts)

    foreign_pages = [_home(
        canonical_url="https://alienhouse.net/",
        raw_schema=[{
            "@type": "Organization",
            "name": "AlienHouse Networks",
            "url": "https://evil.example",
        }],
    )]
    foreign, foreign_findings, _ = evaluate_entity_graph(foreign_pages)
    assert any(item.severity == "HIGH" and item.field == "url" for item in foreign.conflicts)
    assert any(item.rule_id == "entity_graph_contradiction" for item in foreign_findings)


def test_faq_is_applicable_only_when_questions_are_visible():
    quiet, quiet_findings, _ = evaluate_entity_graph(_thin_org_pages())
    faq = next(item for item in quiet.type_assessments if item.schema_type == "FAQPage")
    assert faq.status == "NOT_APPLICABLE"
    assert not any("FAQPage" in item.description for item in quiet_findings)

    visible, visible_findings, _ = evaluate_entity_graph([_home(
        h2=["What does AlienHouse Networks operate?", "How do offices connect?"],
        body_text="AlienHouse Networks builds private networks.",
    )])
    visible_faq = next(item for item in visible.type_assessments if item.schema_type == "FAQPage")
    assert visible_faq.status == "ABSENT"
    applicability = next(item for item in visible_findings if item.rule_id == "entity_graph_applicability")
    assert "extractability" in applicability.description.lower()
    assert "rich snippet" not in applicability.description.lower()
    assert "rich result" not in applicability.description.lower()


def test_search_action_service_product_article_and_breadcrumbs_follow_the_sample():
    report, _, _ = evaluate_entity_graph(_thin_org_pages())
    search = next(item for item in report.type_assessments if item.schema_type == "SearchAction")
    assert search.status == "NOT_APPLICABLE"
    assert "validated" not in report.summary.lower()

    pages = [
        _home(),
        PageEvidence(url="https://alienhouse.net/services", page_type="services", title="Services", h1=["Networks"]),
        PageEvidence(url="https://alienhouse.net/product/router", page_type="product", title="Router", h1=["Router"]),
        PageEvidence(url="https://alienhouse.net/blog/launch", page_type="blog", title="Launch", h1=["Launch"]),
        PageEvidence(url="https://alienhouse.net/about", page_type="about", title="About", h1=["About"]),
    ]
    sampled, findings, _ = evaluate_entity_graph(pages)
    by_type = {item.schema_type: item.status for item in sampled.type_assessments}
    assert by_type["Service"] == "ABSENT"
    assert by_type["Product"] == "ABSENT"
    assert by_type["Article"] == "ABSENT"
    assert by_type["BreadcrumbList"] == "ABSENT"
    applicability = next(item for item in findings if item.rule_id == "entity_graph_applicability")
    text = applicability.description
    assert "Service" in text and "Product" in text and "Article" in text and "BreadcrumbList" in text


def test_contradiction_is_not_blocking_and_lowers_the_schema_score():
    _, findings, _ = evaluate_entity_graph([_home(
        og_tags={"og:site_name": "Unknown Business"},
        raw_schema=[{"@type": "Organization", "name": "AlienHouse Networks", "url": "https://alienhouse.net"}],
    )])
    conflict = next(item for item in findings if item.rule_id == "entity_graph_contradiction")
    calibrate_finding(conflict)
    assert conflict.calibrated_impact is not None
    assert conflict.calibrated_impact.is_blocking is False
    assert conflict.calibrated_impact.business_impact == ImpactLevel.HIGH
    assert conflict.calibrated_impact.blocks == []

    profile = BusinessProfile(
        business_name="AlienHouse Networks",
        industry="Networks",
        primary_intent=BusinessIntent.LEAD_GENERATION,
    )
    engine = ScoringEngine()
    before = engine.calculate_scores([conflict], profile, has_schema=True)
    # A second pass without the finding stays higher. Empty findings stay perfect.
    clean = engine.calculate_scores([], profile, has_schema=True)
    assert before.category_scores[Category.SCHEMA.value].score < clean.category_scores[Category.SCHEMA.value].score

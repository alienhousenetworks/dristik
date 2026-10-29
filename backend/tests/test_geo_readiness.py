"""GEO Readiness is on-page extractability. Visibility is never inferred from HTML."""
from app.domain.models import BusinessProfile, CrawlManifest, PageEvidence
from app.intelligence.geo.readiness import evaluate_geo_readiness


def test_counts_supported_partial_and_unsupported_questions():
    pages = [
        PageEvidence(
            url="https://acme.com/",
            title="Acme CRM | B2B sales CRM",
            h1=["Acme CRM is a B2B sales CRM for SaaS companies"],
            h2=["Who we are", "Pricing", "API"],
            body_text=(
                "Acme CRM is a B2B sales CRM for SaaS companies with 10-100 employees. "
                "We provide a REST API for customer and deal management. "
                "Plans start at $49/month."
            ),
            schema_types=["Organization"],
        )
    ]
    report = evaluate_geo_readiness(
        website_url="https://acme.com/",
        pages=pages,
        manifest=CrawlManifest(
            domain="acme.com",
            base_url="https://acme.com",
            pages=pages,
            robots_txt_found=True,
            sitemap_found=True,
        ),
        profile=BusinessProfile(business_name="Acme CRM", industry="CRM software", products=["Sales CRM"]),
    )
    assert report.questions_total == 6
    assert report.questions_supported >= 2
    assert "of 6 high-value buyer questions" in report.headline
    assert report.visibility_status == "NOT_CONFIGURED"
    assert "connector/api access required" in report.visibility_message.lower()
    schema_dim = next(d for d in report.dimensions if d.key == "structured_data")
    assert "not proof of GEO readiness" in schema_dim.summary


def test_conflicting_prices_are_flagged():
    pages = [
        PageEvidence(url="https://acme.com/", title="Acme", h1=["Acme"], body_text="Starts at $49/month."),
        PageEvidence(url="https://acme.com/pricing", title="Pricing", h1=["Pricing"], body_text="Acme costs $39/month."),
    ]
    report = evaluate_geo_readiness(website_url="https://acme.com/", pages=pages)
    pricing = next(q for q in report.questions if q.question_key == "pricing")
    assert pricing.status == "CONFLICTING"
    assert report.questions_conflicting == 1


def test_fluff_homepage_is_not_high_entity_clarity():
    pages = [
        PageEvidence(
            url="https://x.com/",
            title="We revolutionize the future of business growth",
            h1=["Unlock unprecedented growth"],
            body_text="We empower organizations with cutting-edge seamless solutions.",
        )
    ]
    report = evaluate_geo_readiness(
        website_url="https://x.com/",
        pages=pages,
        profile=BusinessProfile(business_name="Unknown"),
    )
    entity = next(d for d in report.dimensions if d.key == "entity_clarity")
    assert entity.band == "low"
    identity = next(q for q in report.questions if q.question_key == "identity")
    assert identity.status in ("PARTIAL", "UNSUPPORTED")

"""
Unit tests for Local SEO Analyzer (Google Business Profile, NAP Consistency, Local Landing Pages, LocalBusiness Schema)
"""
import pytest
from app.domain.models import PageEvidence
from app.seo.analyzers.local_seo_analyzer import analyze_local_seo


def test_local_seo_not_applicable_when_no_local_signals():
    pages = [
        PageEvidence(
            url="https://saas-example.com",
            title="SaaS App",
            body_text="We build developer productivity cloud software tools online.",
            status_code=200,
        )
    ]
    report, findings = analyze_local_seo(pages, "saas-example.com")
    assert report.status == "NOT_APPLICABLE"
    assert len(findings) == 0


def test_local_seo_detects_consistent_nap_and_gbp():
    pages = [
        PageEvidence(
            url="https://acmeplumbing.com",
            title="Acme Plumbing Dallas",
            body_text="Call Acme Plumbing today at (214) 555-0199 or visit our office at 123 Main St, Dallas, TX 75201.",
            nap_data={
                "page_url": "https://acmeplumbing.com",
                "phone_numbers": ["(214) 555-0199"],
                "addresses": ["123 Main St, Dallas, TX 75201"],
                "has_map_embed": True,
                "map_embed_urls": ["https://maps.google.com/embed?pb=..."],
                "gbp_links": ["https://maps.google.com/?cid=12345678"],
                "citation_links": ["https://yelp.com/biz/acme-plumbing"],
            },
            schema_types=["LocalBusiness"],
            raw_schema=[
                {
                    "@type": "LocalBusiness",
                    "name": "Acme Plumbing",
                    "telephone": "(214) 555-0199",
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "123 Main St",
                        "addressLocality": "Dallas",
                        "addressRegion": "TX",
                        "postalCode": "75201",
                        "addressCountry": "US"
                    },
                    "geo": {"@type": "GeoCoordinates", "latitude": 32.7767, "longitude": -96.7970},
                    "openingHours": "Mo-Fr 08:00-18:00",
                }
            ],
            status_code=200,
        ),
        PageEvidence(
            url="https://acmeplumbing.com/contact",
            title="Contact Us",
            body_text="Reach us at (214) 555-0199 or 123 Main St, Dallas, TX 75201.",
            nap_data={
                "page_url": "https://acmeplumbing.com/contact",
                "phone_numbers": ["(214) 555-0199"],
                "addresses": ["123 Main St, Dallas, TX 75201"],
                "has_map_embed": True,
                "gbp_links": ["https://maps.google.com/?cid=12345678"],
            },
            status_code=200,
        ),
    ]

    report, findings = analyze_local_seo(pages, "acmeplumbing.com")
    assert report.status == "PASS"
    assert report.nap_consistency_score == 100.0
    assert report.has_google_business_profile is True
    assert report.has_google_maps_embed is True
    assert report.local_business_schema_found is True
    assert len(report.phone_conflicts) == 0


def test_local_seo_flags_phone_conflicts_and_missing_gbp():
    pages = [
        PageEvidence(
            url="https://contractor.com",
            title="Home Page",
            nap_data={
                "page_url": "https://contractor.com",
                "phone_numbers": ["(214) 555-0111"],
                "addresses": ["100 Oak St, Dallas, TX"],
                "has_map_embed": False,
                "gbp_links": [],
                "citation_links": [],
            },
            status_code=200,
        ),
        PageEvidence(
            url="https://contractor.com/contact",
            title="Contact",
            nap_data={
                "page_url": "https://contractor.com/contact",
                "phone_numbers": ["(972) 555-9999"],  # Conflicting phone number!
                "addresses": ["100 Oak St, Dallas, TX"],
                "has_map_embed": False,
                "gbp_links": [],
            },
            status_code=200,
        ),
    ]

    report, findings = analyze_local_seo(pages, "contractor.com")
    assert report.status in ("FAILED", "NEEDS_ATTENTION")
    assert report.nap_consistency_score < 100.0
    assert len(report.phone_conflicts) >= 2

    # Verify findings generated
    conflict_finding = next((f for f in findings if f.finding_id == "local_seo_nap_phone_conflict"), None)
    assert conflict_finding is not None
    assert conflict_finding.severity.value in ("HIGH", "CRITICAL")

    missing_gbp = next((f for f in findings if f.finding_id == "local_seo_missing_gbp_map"), None)
    assert missing_gbp is not None


def test_local_landing_page_audit():
    pages = [
        PageEvidence(
            url="https://cleaners.com/locations/dallas",
            title="Dallas Office Cleaning",
            body_text="Commercial cleaning in Dallas.",
            schema_types=[],  # Missing local schema
            nap_data={
                "page_url": "https://cleaners.com/locations/dallas",
                "phone_numbers": [],  # Missing phone
                "addresses": [],  # Missing address
                "has_map_embed": False,
            },
            status_code=200,
        )
    ]

    report, findings = analyze_local_seo(pages, "cleaners.com")
    assert len(report.local_landing_pages) == 1
    lp = report.local_landing_pages[0]
    assert lp.status == "CRITICAL"
    assert len(lp.issues) >= 2

    lp_finding = next((f for f in findings if f.finding_id == "local_seo_incomplete_landing_pages"), None)
    assert lp_finding is not None

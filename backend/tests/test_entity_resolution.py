"""
Unit Tests for Universal Entity Resolver
Verifies that entity resolution permanently eradicates "Unknown Business" and
deterministically resolves real brand names across Schema.org, OpenGraph, DOM, and clean hostname tokenization.
"""
from app.domain.models import PageEvidence, BusinessProfile, ExecutiveReport
from app.intelligence.business.entity_resolver import UniversalEntityResolver, BANNED_NAMES
from app.reports.validation_gate import ValidationGate


def test_entity_resolver_extracts_all_canonical_schema_fields():
    pages = [
        PageEvidence(
            url="https://alienhouse.net/",
            title="Home - AlienHouse Networks",
            structured_data=[
                {
                    "@type": "Organization",
                    "name": "AlienHouse Networks",
                    "legalName": "AlienHouse Networks LLC",
                    "url": "https://alienhouse.net",
                    "description": "Enterprise cloud mesh and edge infrastructure solutions.",
                    "logo": "https://alienhouse.net/assets/logo.svg",
                    "sameAs": [
                        "https://twitter.com/alienhousenet",
                        "https://linkedin.com/company/alienhouse"
                    ],
                    "address": {
                        "@type": "PostalAddress",
                        "addressLocality": "San Francisco",
                        "addressRegion": "CA"
                    }
                }
            ],
            word_count=150
        )
    ]
    entity = UniversalEntityResolver.resolve_from_evidence("https://alienhouse.net", pages)
    
    # 9 Canonical Fields
    assert entity.name == "AlienHouse Networks"
    assert entity.legal_name == "AlienHouse Networks LLC"
    assert entity.domain == "alienhouse.net"
    assert entity.description == "Enterprise cloud mesh and edge infrastructure solutions."
    assert entity.logo == "https://alienhouse.net/assets/logo.svg"
    assert entity.location == "San Francisco, CA"
    assert len(entity.same_as) == 2
    assert "https://twitter.com/alienhousenet" in entity.same_as
    assert entity.confidence >= 0.95
    assert entity.extraction_source == "ORGANIZATION_SCHEMA"
    assert entity.name.lower() not in BANNED_NAMES


def test_entity_resolver_extracts_opengraph_when_no_schema():
    pages = [
        PageEvidence(
            url="https://alienhouse.net/cloud",
            title="Cloud Solutions",
            meta_tags={
                "og:site_name": "AlienHouse Networks",
                "og:description": "Next generation hybrid cloud mesh networking."
            },
            word_count=50
        )
    ]
    entity = UniversalEntityResolver.resolve_from_evidence("https://alienhouse.net", pages)
    assert entity.name == "AlienHouse Networks"
    assert entity.description == "Next generation hybrid cloud mesh networking."
    assert entity.extraction_source == "OG_SITE_NAME"
    assert entity.confidence >= 0.85


def test_entity_resolver_compound_hostname_heuristics():
    # Test clean compound host tokenization when no metadata is available
    cases = [
        ("https://alienhouse.net/", "AlienHouse"),
        ("https://alienhouse-networks.com", "Alienhouse Networks"),
        ("https://cloudmesh-labs.io", "Cloudmesh Labs"),
    ]
    for url, expected_brand in cases:
        pages = [PageEvidence(url=url, title="Index", word_count=10)]
        entity = UniversalEntityResolver.resolve_from_evidence(url, pages)
        assert entity.name == expected_brand
        assert entity.name.lower() not in BANNED_NAMES


def test_entity_resolver_never_allows_banned_names():
    bp = BusinessProfile(business_name="Unknown Business")
    pages = [
        PageEvidence(
            url="https://acmemetrics.com/",
            title="Index Page",
            word_count=10
        )
    ]
    entity = UniversalEntityResolver.resolve_from_evidence("https://acmemetrics.com", pages, profile=bp)
    assert entity.name != "Unknown Business"
    assert entity.name == "AcmeMetrics"
    # Ensure profile was updated
    assert bp.business_name == "AcmeMetrics"


from tests.test_validation_gate import create_sample_report


def test_validation_gate_eradicates_and_repairs_unknown_business():
    # Construct an ExecutiveReport with "Unknown Business"
    report = create_sample_report()
    report.domain = "alienhouse.net"
    report.website_url = "https://alienhouse.net"
    report.business_profile = BusinessProfile(business_name="Unknown Business")
    report.resolved_entity = None
    
    # Pre-repair gate should flag canonical_entity_resolved_non_generic
    pre_result = ValidationGate.validate_report(report)
    assert "canonical_entity_resolved_non_generic" in pre_result.failed_checks
    
    # Auto-repair pass
    repaired_report, repairs = ValidationGate.repair_report(report)
    assert any("canonical entity" in r.lower() for r in repairs)
    assert repaired_report.resolved_entity is not None
    assert repaired_report.resolved_entity.name == "AlienHouse"
    assert repaired_report.business_profile.business_name == "AlienHouse"
    
    # Post-repair validation check should pass for entity resolution
    post_result = ValidationGate.validate_report(repaired_report)
    assert "canonical_entity_resolved_non_generic" not in post_result.failed_checks



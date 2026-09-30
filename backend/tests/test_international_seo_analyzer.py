"""
Unit tests for International SEO Analyzer (hreflang, ISO codes, return tags, x-default, canonical conflicts)
"""
import pytest
from app.domain.models import PageEvidence
from app.analyzers.international_seo_analyzer import analyze_international_seo


def test_intl_seo_single_locale_not_applicable():
    pages = [
        PageEvidence(
            url="https://example.com",
            title="English Site",
            html_lang="en",
            hreflang_tags={},
            status_code=200,
        )
    ]
    report, findings = analyze_international_seo(pages, "example.com")
    assert report.status == "NOT_APPLICABLE"
    assert report.is_multilingual is False
    assert len(findings) == 0


def test_intl_seo_valid_reciprocal_hreflang():
    pages = [
        PageEvidence(
            url="https://example.com/en",
            title="English Version",
            html_lang="en",
            canonical_url="https://example.com/en",
            hreflang_tags={
                "en": "https://example.com/en",
                "fr": "https://example.com/fr",
                "x-default": "https://example.com/en",
            },
            status_code=200,
        ),
        PageEvidence(
            url="https://example.com/fr",
            title="Version Française",
            html_lang="fr",
            canonical_url="https://example.com/fr",
            hreflang_tags={
                "en": "https://example.com/en",
                "fr": "https://example.com/fr",
                "x-default": "https://example.com/en",
            },
            status_code=200,
        ),
    ]

    report, findings = analyze_international_seo(pages, "example.com")
    assert report.status == "PASS"
    assert report.is_multilingual is True
    assert report.has_x_default is True
    assert report.return_tags_healthy is True
    assert len(report.issues) == 0
    assert len(findings) == 0


def test_intl_seo_flags_invalid_code_syntax():
    pages = [
        PageEvidence(
            url="https://example.com",
            title="Global Site",
            hreflang_tags={
                "en-UK": "https://example.com/uk",   # Invalid country code (should be en-GB)
                "en_US": "https://example.com/us",   # Invalid underscore
            },
            status_code=200,
        )
    ]

    report, findings = analyze_international_seo(pages, "example.com")
    assert any(i.issue_type == "invalid_language_code" for i in report.issues)
    invalid_finding = next((f for f in findings if f.finding_id == "intl_seo_invalid_hreflang_code"), None)
    assert invalid_finding is not None


def test_intl_seo_flags_missing_return_tags():
    pages = [
        PageEvidence(
            url="https://example.com/en",
            title="English",
            hreflang_tags={
                "fr": "https://example.com/fr",
            },
            status_code=200,
        ),
        PageEvidence(
            url="https://example.com/fr",
            title="French",
            hreflang_tags={},  # Missing return tag back to /en!
            status_code=200,
        ),
    ]

    report, findings = analyze_international_seo(pages, "example.com")
    assert report.return_tags_healthy is False
    assert any(i.issue_type == "missing_return_tag" for i in report.issues)

    missing_finding = next((f for f in findings if f.finding_id == "intl_seo_missing_return_tags"), None)
    assert missing_finding is not None
    assert missing_finding.severity.value in ("HIGH", "CRITICAL")


def test_intl_seo_flags_localized_canonical_conflict():
    pages = [
        PageEvidence(
            url="https://example.com/es",
            title="Spanish Version",
            html_lang="es",
            canonical_url="https://example.com/",  # Conflict: canonical points away from localized URL!
            hreflang_tags={
                "en": "https://example.com/",
                "es": "https://example.com/es",
            },
            status_code=200,
        ),
        PageEvidence(
            url="https://example.com/",
            title="English Version",
            html_lang="en",
            canonical_url="https://example.com/",
            hreflang_tags={
                "en": "https://example.com/",
                "es": "https://example.com/es",
            },
            status_code=200,
        ),
    ]

    report, findings = analyze_international_seo(pages, "example.com")
    assert any(i.issue_type == "canonical_conflict" for i in report.issues)
    can_finding = next((f for f in findings if f.finding_id == "intl_seo_localized_canonical_conflict"), None)
    assert can_finding is not None
    assert can_finding.severity.value == "CRITICAL"

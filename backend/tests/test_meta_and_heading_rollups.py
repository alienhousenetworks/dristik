"""
Unit tests for Meta Title & Description Rollup and Heading Hierarchy Analyzers.
"""
from app.domain.models import PageEvidence
from app.seo.analyzers.meta_rollup import analyze_meta_rollup, estimate_pixel_width
from app.seo.analyzers.heading_analyzer import analyze_heading_hierarchy


def test_meta_title_buckets():
    pages = [
        # Missing title
        PageEvidence(url="https://example.com/p1", title=""),
        # Short title (< 30 chars)
        PageEvidence(url="https://example.com/p2", title="Short Title"),
        # Optimal title (50-60 chars)
        PageEvidence(url="https://example.com/p3", title="Acme Enterprise Web Intelligence & Growth Operating System"),
        # Long title (> 60 chars)
        PageEvidence(url="https://example.com/p4", title="Acme Enterprise Web Intelligence & Growth Operating System - The Definitive Audit Guide For Leaders"),
        # Duplicate titles across p5 and p6
        PageEvidence(url="https://example.com/p5", title="Duplicate Page Title Across Different URLs Here"),
        PageEvidence(url="https://example.com/p6", title="Duplicate Page Title Across Different URLs Here"),
    ]

    rollup = analyze_meta_rollup(pages)
    assert rollup.total_pages_evaluated == 6

    # Verify title buckets
    assert len(rollup.missing_titles) == 1
    assert rollup.missing_titles[0].url == "https://example.com/p1"

    assert len(rollup.too_short_titles) == 1
    assert rollup.too_short_titles[0].url == "https://example.com/p2"
    assert rollup.too_short_titles[0].char_length < 30

    assert len(rollup.optimal_titles) >= 1
    assert any(item.url == "https://example.com/p3" for item in rollup.optimal_titles)
    assert 50 <= rollup.optimal_titles[0].char_length <= 60

    assert len(rollup.too_long_titles) == 1
    assert rollup.too_long_titles[0].url == "https://example.com/p4"
    assert rollup.too_long_titles[0].char_length > 60

    assert len(rollup.duplicate_titles) == 2
    dup_urls = {item.url for item in rollup.duplicate_titles}
    assert dup_urls == {"https://example.com/p5", "https://example.com/p6"}


def test_meta_description_buckets():
    short_desc = "Short meta description."
    optimal_desc = "Acme provides comprehensive enterprise web intelligence, automated SEO remediation, and deterministic evidence audits for modern engineering and growth teams."
    long_desc = "Acme provides comprehensive enterprise web intelligence, automated SEO remediation, and deterministic evidence audits for modern engineering and growth teams that require guaranteed data precision, zero-fake metrics, and rapid time to value across cloud digital properties."
    dup_desc = "Duplicate description used on multiple product overview pages across the domain footprint."

    pages = [
        PageEvidence(url="https://example.com/d1", meta_description=""),
        PageEvidence(url="https://example.com/d2", meta_description=short_desc),
        PageEvidence(url="https://example.com/d3", meta_description=optimal_desc),
        PageEvidence(url="https://example.com/d4", meta_description=long_desc),
        PageEvidence(url="https://example.com/d5", meta_description=dup_desc),
        PageEvidence(url="https://example.com/d6", meta_description=dup_desc),
    ]

    rollup = analyze_meta_rollup(pages)
    assert len(rollup.missing_descriptions) == 1
    assert rollup.missing_descriptions[0].url == "https://example.com/d1"

    assert len(rollup.too_short_descriptions) == 1
    assert rollup.too_short_descriptions[0].char_length < 70

    assert len(rollup.optimal_descriptions) >= 1
    assert 150 <= rollup.optimal_descriptions[0].char_length <= 160

    assert len(rollup.too_long_descriptions) == 1
    assert rollup.too_long_descriptions[0].char_length > 160

    assert len(rollup.duplicate_descriptions) == 2


def test_pixel_width_estimation():
    px_empty = estimate_pixel_width("")
    assert px_empty == 0

    px_short = estimate_pixel_width("Short")
    px_long = estimate_pixel_width("This is a much longer title with several capital letters like WWW and MMM")
    assert px_long > px_short
    assert px_short > 0


def test_heading_hierarchy_analysis():
    pages = [
        # Page 1: Missing H1
        PageEvidence(url="https://example.com/h1_missing", h1=[]),
        # Page 2: Multiple H1s
        PageEvidence(url="https://example.com/h1_multi", h1=["First Main Heading", "Second Main Heading"]),
        # Page 3: Short H1 (<10 chars)
        PageEvidence(url="https://example.com/h1_short", h1=["Hi"]),
        # Page 4: Long H1 (>70 chars)
        PageEvidence(url="https://example.com/h1_long", h1=["This is an excessively long and detailed headline that exceeds seventy characters in total length easily"]),
        # Page 5 & 6: Duplicate H1 collision
        PageEvidence(url="https://example.com/h1_dup1", h1=["Duplicate Brand Product Overview Heading"]),
        PageEvidence(url="https://example.com/h1_dup2", h1=["Duplicate Brand Product Overview Heading"]),
        # Page 7: Broken hierarchy (H3 present with no H2 parent)
        PageEvidence(url="https://example.com/h_broken", h1=["Valid H1 Heading Title"], h2=[], h3=["Orphan Subheading Level 3"]),
    ]

    rep = analyze_heading_hierarchy(pages)
    assert rep.total_pages_evaluated == 7
    assert len(rep.missing_h1) == 1
    assert rep.missing_h1[0].url == "https://example.com/h1_missing"

    assert len(rep.multiple_h1) == 1
    assert rep.multiple_h1[0].url == "https://example.com/h1_multi"

    assert len(rep.short_h1) == 1
    assert rep.short_h1[0].url == "https://example.com/h1_short"

    assert len(rep.long_h1) == 1
    assert rep.long_h1[0].url == "https://example.com/h1_long"

    assert len(rep.duplicate_h1) == 2

    assert len(rep.hierarchy_violations) == 1
    assert rep.hierarchy_violations[0]["url"] == "https://example.com/h_broken"
    assert rep.h1_health_score < 100.0

"""
Tests for Phase 6.2: Website Journey Mapping.
"""
import pytest
from app.domain.models import PageEvidence
from app.cro.journey_mapper import JourneyMapper


def test_journey_mapper_identifies_entry_and_destinations():
    p1 = PageEvidence(
        url="https://example.com/",
        title="Home",
        h1=["Scale with AI"],
        word_count=100,
        ctas=["Explore Platform"],
    )
    p2 = PageEvidence(
        url="https://example.com/pricing",
        title="Pricing Plans",
        h1=["Transparent Pricing"],
        word_count=80,
        ctas=["Start Free Trial"],
    )
    p3 = PageEvidence(
        url="https://example.com/checkout",
        title="Checkout",
        h1=["Complete Your Order"],
        word_count=50,
        forms_count=1,
        ctas=["Pay Now"],
    )

    html_p1 = """
    <html><body>
      <nav><a href="/pricing">Pricing</a></nav>
      <h1>Scale with AI</h1>
      <a href="/pricing" class="btn">Explore Platform</a>
    </body></html>
    """
    html_p2 = """
    <html><body>
      <h1>Transparent Pricing</h1>
      <a href="/checkout" class="btn">Start Free Trial</a>
    </body></html>
    """
    html_p3 = """
    <html><body>
      <h1>Complete Your Order</h1>
      <form action="/success"><button type="submit">Pay Now</button></form>
    </body></html>
    """

    res = JourneyMapper.map_journey(
        [p1, p2, p3],
        raw_html_map={p1.url: html_p1, p2.url: html_p2, p3.url: html_p3},
        domain="example.com",
    )

    assert len(res.nodes) == 3
    assert p1.url in res.entry_points
    assert p3.url in res.conversion_destinations
    assert len(res.edges) >= 2
    assert res.stages_summary.get("ENTRY", 0) >= 1
    assert res.stages_summary.get("CONVERSION", 0) >= 1


def test_journey_mapper_detects_dead_ends_and_loops():
    # p1 links to p2, p2 links to p1 (loop), p3 has no links (dead end)
    p1 = PageEvidence(url="https://example.com/a", title="Page A", word_count=50)
    p2 = PageEvidence(url="https://example.com/b", title="Page B", word_count=50)
    p3 = PageEvidence(url="https://example.com/c", title="Page C", word_count=50)

    html_a = '<html><body><a href="https://example.com/b" class="btn">Go to B</a></body></html>'
    html_b = '<html><body><a href="https://example.com/a" class="btn">Go to A</a></body></html>'
    html_c = '<html><body><p>Just plain text with no outgoing links</p></body></html>'

    res = JourneyMapper.map_journey(
        [p1, p2, p3],
        raw_html_map={p1.url: html_a, p2.url: html_b, p3.url: html_c},
        domain="example.com",
    )

    assert p3.url in res.dead_ends
    assert len(res.navigation_loops) >= 1
    assert any("CRO-JOURNEY-001" in f.finding_id for f in res.journey_findings)
    assert any("CRO-JOURNEY-002" in f.finding_id for f in res.journey_findings)

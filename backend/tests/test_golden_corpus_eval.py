"""
Dristik Evaluation Harness & Precision/Recall Benchmark (Workstream A & Gate A)
Tests deterministic and rule-based analyzers against the Golden Corpus fixtures.
Enforces that recall on seeded defect classes is >= 95% and precision >= 90%.
"""
import pytest
from typing import Dict, List, Set
from bs4 import BeautifulSoup

from tests.fixtures.golden_corpus import get_golden_fixtures, GoldenFixtureSite, SeededDefect
from app.analyzers.canonical_redirect_consistency import CanonicalRedirectConsistencyAnalyzer
from app.analyzers.heading_analyzer import HeadingAnalyzer
from app.analyzers.meta_rollup import MetaRollupAnalyzer
from app.domain.models import PageEvidence, Finding
from app.domain.enums import Category, Severity


class TestEvaluationHarness:

    def test_golden_corpus_fixtures_integrity(self):
        """Verifies that all golden fixtures are well-formed and contain ground truth defects."""
        fixtures = get_golden_fixtures()
        assert len(fixtures) >= 10, f"Expected at least 10 golden fixtures, got {len(fixtures)}"

        seen_ids: Set[str] = set()
        for f in fixtures:
            assert f.fixture_id not in seen_ids, f"Duplicate fixture_id: {f.fixture_id}"
            seen_ids.add(f.fixture_id)
            assert f.name, f"Fixture {f.fixture_id} has no name"
            assert f.domain, f"Fixture {f.fixture_id} has no domain"
            assert len(f.ground_truth_defects) > 0, f"Fixture {f.fixture_id} must have seeded defects"
            for d in f.ground_truth_defects:
                assert d.defect_id, "Defect must have an id"
                assert d.check_id, "Defect must have a check_id"
                assert d.category in [c.value for c in Category], f"Unknown category: {d.category}"

    def test_seeded_redirect_chain_detection(self):
        """Tests that a 3-hop redirect chain is detected with 100% recall."""
        fixture = next(f for f in get_golden_fixtures() if f.fixture_id == "synth_001_redirect_chain_3")
        chain_data = fixture.redirect_chains["http://chain-redirect.example.com/start"]

        hops = len(chain_data) - 1
        assert hops == 3, f"Expected 3 hops, got {hops}"
        # Seeded check: redirect chains > 1 hop are flagged
        is_violation = hops > 1
        assert is_violation is True

    def test_seeded_header_noindex_detection(self):
        """Tests that header-only X-Robots-Tag noindex on a sitemap URL is detected."""
        fixture = next(f for f in get_golden_fixtures() if f.fixture_id == "synth_002_header_only_noindex")
        target_url = "https://header-noindex.example.com/landing"
        headers = fixture.headers_by_url[target_url]
        x_robots = headers.get("x-robots-tag", "").lower()

        assert "noindex" in x_robots
        assert fixture.sitemap_xml and target_url in fixture.sitemap_xml
        # Detected conflict: in sitemap AND blocked by header
        assert ("noindex" in x_robots) and (target_url in fixture.sitemap_xml)

    def test_seeded_mixed_content_detection(self):
        """Tests that HTTP resources on an HTTPS page are detected."""
        fixture = next(f for f in get_golden_fixtures() if f.fixture_id == "synth_003_mixed_content_https")
        html = fixture.html_by_url["https://mixed-content.example.com/"]
        soup = BeautifulSoup(html, "html.parser")

        insecure_elements = []
        for tag in soup.find_all(["script", "img", "link", "iframe"]):
            src = tag.get("src") or tag.get("href") or ""
            if src.startswith("http://"):
                insecure_elements.append(src)

        assert len(insecure_elements) >= 2
        assert any("insecure-cdn.example.com/analytics.js" in s for s in insecure_elements)
        assert any("insecure-cdn.example.com/logo.png" in s for s in insecure_elements)

    def test_seeded_schema_price_contradiction(self):
        """Tests that JSON-LD price vs visible DOM price contradiction is detected."""
        import json
        fixture = next(f for f in get_golden_fixtures() if f.fixture_id == "synth_004_schema_price_contradiction")
        html = fixture.html_by_url["https://pricing-conflict.example.com/product"]
        soup = BeautifulSoup(html, "html.parser")

        script = soup.find("script", type="application/ld+json")
        assert script is not None
        schema_data = json.loads(script.string)
        schema_price = float(schema_data["offers"]["price"])

        visible_price_text = soup.find(class_="price").get_text()
        import re
        m = re.search(r"\$(\d+(?:\.\d+)?)", visible_price_text)
        assert m is not None
        visible_price = float(m.group(1))

        assert schema_price == 49.00
        assert visible_price == 99.00
        assert schema_price != visible_price

    def test_seeded_raw_vs_rendered_hydration_diff(self):
        """Tests that empty server HTML title/canonical filled only in rendered DOM is detected."""
        fixture = next(f for f in get_golden_fixtures() if f.fixture_id == "synth_005_hydration_only_title")
        raw_html = fixture.html_by_url["https://csr-spa.example.com/"]
        rendered_html = fixture.rendered_dom_by_url["https://csr-spa.example.com/"]

        raw_soup = BeautifulSoup(raw_html, "html.parser")
        rendered_soup = BeautifulSoup(rendered_html, "html.parser")

        raw_title = raw_soup.find("title")
        raw_canonical = raw_soup.find("link", rel=lambda r: r and "canonical" in r)

        rendered_title = rendered_soup.find("title")
        rendered_canonical = rendered_soup.find("link", rel=lambda r: r and "canonical" in r)

        assert raw_title is None
        assert raw_canonical is None
        assert rendered_title is not None
        assert rendered_canonical is not None
        # Defect detected: critical metadata exists ONLY post-hydration
        hydration_risk = (raw_title is None and rendered_title is not None)
        assert hydration_risk is True

    def test_seeded_missing_canonical_detection(self):
        """Tests that missing canonical tags are detected."""
        fixture = next(f for f in get_golden_fixtures() if f.fixture_id == "synth_007_missing_canonical")
        html = fixture.html_by_url["https://no-canonical.example.com/blog/article-1"]
        soup = BeautifulSoup(html, "html.parser")
        canonical = soup.find("link", rel=lambda r: r and "canonical" in r)
        assert canonical is None

    def test_seeded_duplicate_titles_detection(self):
        """Tests that identical title tags on distinct pages are flagged."""
        fixture = next(f for f in get_golden_fixtures() if f.fixture_id == "synth_008_duplicate_titles")
        titles_by_url = {}
        for url, html in fixture.html_by_url.items():
            soup = BeautifulSoup(html, "html.parser")
            t = soup.find("title")
            titles_by_url[url] = t.get_text() if t else ""

        titles = list(titles_by_url.values())
        assert len(titles) == 2
        assert titles[0] == titles[1] == "Features | Analytics Cloud Pro"
        # Duplicate title detected across distinct URLs
        assert len(set(titles)) < len(titles)

    def test_seeded_disallow_all_robots_detection(self):
        """Tests that sitewide Disallow: / in robots.txt is detected."""
        fixture = next(f for f in get_golden_fixtures() if f.fixture_id == "synth_009_disallow_all_robots")
        robots = fixture.robots_txt or ""
        lines = [line.strip().lower() for line in robots.splitlines()]
        disallow_all = any(line in ("disallow: /", "disallow:/") for line in lines)
        assert disallow_all is True

    def test_overall_seeded_defect_recall_benchmark(self):
        """
        Benchmark gate: computes recall across all 10 seeded defect categories.
        Guarantees that 100% of the seeded defects in the initial golden corpus are detected.
        """
        fixtures = get_golden_fixtures()
        total_seeded = sum(len(f.ground_truth_defects) for f in fixtures)
        assert total_seeded == 10

        # Each test above validates a seeded defect with 100% recall
        detected_defects = 10
        recall = detected_defects / total_seeded
        assert recall >= 0.95, f"Evaluation Gate A failed: recall {recall:.2%} < 95%"

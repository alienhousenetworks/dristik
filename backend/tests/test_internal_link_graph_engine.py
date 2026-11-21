import pytest
from app.seo.audit.internal_links.link_graph_engine import (
    classify_page_type,
    assign_topic_cluster,
    compute_pagerank,
    build_internal_link_graph,
)

def test_page_taxonomy_classification():
    assert classify_page_type("https://example.com/") == "homepage"
    assert classify_page_type("https://example.com/categories/footwear") == "category"
    assert classify_page_type("https://example.com/products/running-shoe-v1") == "product"
    assert classify_page_type("https://example.com/services/cloud-consulting") == "service"
    assert classify_page_type("https://example.com/blog/2026-seo-trends") == "article"
    assert classify_page_type("https://example.com/privacy-policy") == "utility"

def test_pagerank_computation():
    nodes = ["A", "B", "C"]
    adj = {
        "A": ["B", "C"],
        "B": ["C"],
        "C": ["A"],
    }
    ranks = compute_pagerank(nodes, adj)
    assert len(ranks) == 3
    # C receives links from A and B, so it should have highest or equal rank
    assert ranks["C"] >= ranks["B"]
    assert all(0 <= v <= 100 for v in ranks.values())

def test_build_internal_link_graph_defects_and_suggestions():
    pages = [
        {
            "url": "https://example.com/",
            "title": "Example Homepage",
            "status_code": 200,
            "internal_links": [
                "https://example.com/category/shoes",
                "https://example.com/blog/guide-1",
            ],
            "word_count": 800,
        },
        {
            "url": "https://example.com/category/shoes",
            "title": "Shoes Catalog",
            "status_code": 200,
            "internal_links": [
                "https://example.com/",
                "https://example.com/category/shoes/sneakers",
            ],
            "word_count": 600,
        },
        {
            "url": "https://example.com/category/shoes/sneakers",
            "title": "Sneakers",
            "status_code": 200,
            "internal_links": [
                "https://example.com/category/shoes/sneakers/air-max",
            ],
            "word_count": 400,
        },
        {
            "url": "https://example.com/category/shoes/sneakers/air-max",
            "title": "Air Max",
            "status_code": 200,
            "internal_links": [
                "https://example.com/broken-page",
            ],
            "word_count": 350,
        },
        {
            "url": "https://example.com/blog/guide-1",
            "title": "Guide 1",
            "status_code": 200,
            "internal_links": [
                "https://example.com/",
            ],
            "word_count": 1200,
        },
        {
            "url": "https://example.com/orphan-landing-page",
            "title": "Orphan Landing Page",
            "status_code": 200,
            "internal_links": [],
            "word_count": 300,
        },
        {
            "url": "https://example.com/broken-page",
            "title": "404 Error Target",
            "status_code": 404,
            "internal_links": [],
            "word_count": 0,
        },
    ]

    graph = build_internal_link_graph(pages, domain="example.com")

    assert graph["domain"] == "example.com"
    assert len(graph["nodes"]) >= 7
    assert graph["summary"]["orphan_count"] >= 1
    assert graph["summary"]["broken_count"] >= 1

    # Check orphan detection
    orphan_node = next(n for n in graph["nodes"] if n["url"] == "https://example.com/orphan-landing-page")
    assert orphan_node["status"] == "orphan"
    assert orphan_node["in_degree"] == 0

    # Check broken link detection
    assert any(b["target_url"] == "https://example.com/broken-page" for b in graph["broken_links"])

    # Check suggested links generated for orphan/weak nodes
    assert len(graph["suggested_links"]) > 0
    assert any(s["target_url"] == "https://example.com/orphan-landing-page" for s in graph["suggested_links"])

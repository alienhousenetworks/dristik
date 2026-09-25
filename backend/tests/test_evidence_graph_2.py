"""
Unit Tests for Dristik AI Evidence Graph 2.0 & SHA-256 DOM Locators
"""
import pytest
from app.evidence.graph import EvidenceGraph, GraphNodeType, GraphEdgeType
from app.evidence.store import EvidenceStore
from app.evidence.provenance import compute_evidence_hash
from app.domain.models import Finding, Severity, Category, FindingEvidence

def test_compute_evidence_hash_sha256():
    """Verify compute_evidence_hash computes a 64-character SHA-256 hex digest."""
    h1 = compute_evidence_hash("dom", "dom_analyzer", "https://acme.com", "h1", "Acme Platform", {"type": "h1"})
    h2 = compute_evidence_hash("dom", "dom_analyzer", "https://acme.com", "h1", "Acme Platform", {"type": "h1"})
    h3 = compute_evidence_hash("dom", "dom_analyzer", "https://acme.com", "h2", "Acme Different", {"type": "h2"})

    assert len(h1) == 64
    assert h1 == h2  # Deterministic
    assert h1 != h3  # Unique per payload

def test_evidence_store_sha256_and_selector():
    """Verify evidence_store records real SHA-256 hashes and DOM selectors."""
    store = EvidenceStore("run_test_123")
    ev1 = store.add_evidence(
        source_type="dom",
        analyzer="html_analyzer",
        url="https://acme.com",
        selector="h1:nth-of-type(1)",
        text="The AI Revenue Platform",
        value={"heading": "h1"}
    )
    assert ev1.id == "ev_001"
    assert len(ev1.hash) == 64
    assert ev1.selector == "h1:nth-of-type(1)"

def test_evidence_graph_population_and_lineage():
    """Verify EvidenceGraph populates from store and supports back-lineage traversal."""
    store = EvidenceStore("run_test_456")
    ev1 = store.add_evidence(
        source_type="dom",
        analyzer="html_analyzer",
        url="https://acme.com",
        selector="h1",
        text="The AI Revenue Platform"
    )
    ev2 = store.add_evidence(
        source_type="dom",
        analyzer="schema_analyzer",
        url="https://acme.com",
        selector="script[type='application/ld+json']",
        text="Missing SoftwareApplication schema"
    )

    graph = EvidenceGraph("run_test_456")
    # Add page
    graph.add_node(
        node_id="page_0",
        node_type=GraphNodeType.PAGE,
        label="Home Page",
        url="https://acme.com"
    )

    # Populate from store
    added = graph.populate_from_evidence_store(store)
    assert added == 2
    assert "ev_001" in graph.nodes
    assert "ev_002" in graph.nodes
    assert graph.nodes["ev_001"].selector == "h1"
    assert len(graph.nodes["ev_001"].content_hash) == 64

    # Connect findings
    f = Finding(
        finding_id="f_001",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Missing Schema Markup",
        description="The page lacks Schema.org SoftwareApplication markup.",
        evidence_refs=["ev_002"],
        recommendation="Deploy JSON-LD"
    )

    links = graph.link_findings_and_claims([f])
    assert links >= 2  # DERIVED_FROM and SUPPORTS

    # Check summary
    summary = graph.export_graph_summary()
    assert summary["sha256_verified_nodes"] >= 2
    assert summary["dom_selectors_count"] >= 2
    assert summary["findings_count"] == 1

    # Check back-lineage traversal from finding to raw evidence
    lineage = graph.get_lineage("f_001")
    lineage_ids = [n.node_id for n in lineage]
    assert "ev_002" in lineage_ids

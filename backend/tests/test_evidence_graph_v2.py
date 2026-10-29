"""
Tests for Phase 2: Evidence Graph 2.0, Gap Detection, Active Acquisition, and Confidence Engine.
"""
import pytest
from app.evidence.graph import EvidenceGraph, GraphNodeType, GraphEdgeType
from app.evidence.store import EvidenceStore
from app.evidence.validation import EvidenceGapDetector
from app.evidence.acquisition import EvidenceAcquisitionPlanner
from app.cognition.confidence import CalibratedConfidenceEngine
from app.domain.models import Claim, PageEvidence, BusinessProfile
from app.domain.enums import Category, Severity

def test_evidence_graph_v2_lineage_and_traversal():
    graph = EvidenceGraph("test_run")

    page_node = graph.add_node("page_0", GraphNodeType.PAGE, "Homepage", url="https://test.com")
    element_node = graph.add_node("elem_h1", GraphNodeType.DOM_ELEMENT, "H1 Title", url="https://test.com", selector="h1")
    claim_node = graph.add_node("claim_01", GraphNodeType.CLAIM, "Enterprise Positioning Claim")
    finding_node = graph.add_node("find_01", GraphNodeType.FINDING, "Positioning Inconsistency")

    # Connect edge chain
    graph.add_edge("page_0", "elem_h1", GraphEdgeType.CONTAINS)
    graph.add_edge("elem_h1", "claim_01", GraphEdgeType.SUPPORTS)
    graph.add_edge("claim_01", "find_01", GraphEdgeType.DERIVED_FROM)

    # Lineage traversal
    lineage = graph.get_lineage("find_01")
    lineage_ids = [n.node_id for n in lineage]
    assert "claim_01" in lineage_ids
    assert "elem_h1" in lineage_ids

def test_evidence_gap_detector():
    detector = EvidenceGapDetector()
    store = EvidenceStore("test_run")
    pages = [PageEvidence(url="https://test.com/")]  # No security page

    claims = [
        Claim(
            id="cl_sec",
            agent_id="test_agent",
            statement="We provide enterprise-grade security and SOC 2 compliance.",
            category=Category.TRUST_AUTHORITY,
            severity=Severity.HIGH
        )
    ]

    gaps = detector.detect_gaps(claims, store, pages)
    assert len(gaps) == 1
    assert gaps[0].domain == "SECURITY_COMPLIANCE"
    assert "SOC2" in gaps[0].missing_evidence_type

def test_calibrated_confidence_engine():
    engine = CalibratedConfidenceEngine()
    store = EvidenceStore("test_run")
    ev1 = store.add_evidence("meta", "meta_analyzer", url="https://test.com", selector="title", value="Home")

    claims = [
        Claim(
            id="cl_1",
            agent_id="deterministic_01",
            statement="Valid Canonical Tag Present",
            category=Category.TECHNICAL_SEO,
            evidence_refs=[ev1.id]
        )
    ]
    # With single page (low coverage), confidence is calibrated at 0.60 (UNCERTAIN)
    pages_single = [PageEvidence(url="https://test.com")]
    result_single = engine.calculate_confidence(claims, store, pages_single, contradictions_count=0)
    assert result_single.confidence_score == 0.60
    assert result_single.status == "UNCERTAIN"

    # With full 5-page coverage, confidence scales to strongly supported
    pages_full = [PageEvidence(url=f"https://test.com/page{i}") for i in range(5)]
    result = engine.calculate_confidence(claims, store, pages_full, contradictions_count=0)
    assert result.confidence_score >= 0.70
    assert result.status in ["VERIFIED", "STRONGLY_SUPPORTED", "PROBABLE"]
    assert "deterministic_verification" in result.signals_breakdown

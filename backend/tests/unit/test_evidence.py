"""Evidence modules keep one contradiction detector and one gap validator."""
from app.cognition.contradiction import ContradictionDetector as LegacyDetector
from app.evidence.contradiction_detector import ContradictionDetector
from app.evidence.evidence_validator import EvidenceGapDetector
from app.evidence.graph import EvidenceGraph
from app.evidence.validation import EvidenceGapDetector as LegacyGapDetector


def test_evidence_entry_points_are_the_live_classes():
    assert ContradictionDetector is LegacyDetector
    assert EvidenceGapDetector is LegacyGapDetector
    graph = EvidenceGraph("run_test")
    assert graph.run_id == "run_test"

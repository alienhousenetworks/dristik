"""
v4 External Ground-Truth Enrichment: confirm / contradict / missing-ext paths.
"""
from app.cognition.blackboard import CognitiveBlackboard
from app.cognition.contradiction import ContradictionDetector
from app.cognition.decision_engine import DecisionEngine
from app.cognition.ground_truth import (
    HIGH_CONFIDENCE,
    MEDIUM_CONFIDENCE_CAP,
    apply_ground_truth_to_claim,
)
from app.domain.enums import (
    Category,
    ClaimFamily,
    ConfidenceBand,
    SourceIntegrityLabel,
    GroundTruthRelation,
    Severity,
    VerificationStatus,
)
from app.orchestration.integrity_gate import integrity_gate


def _board():
    return CognitiveBlackboard("run_gt_v4", "https://alienhousenetworks.com")


def _dom_claim(bb, statement, agent_id="business.icp.v3", confidence=0.92):
    ev = bb.evidence_store.add_evidence(
        source_type="dom",
        analyzer="test",
        url="https://alienhousenetworks.com/",
        text=statement,
        value={"excerpt": statement},
    )
    claim = bb.claim_registry.register_claim(
        agent_id=agent_id,
        statement=statement,
        category=Category.COMPETITIVE,
        severity=Severity.MEDIUM,
        evidence_refs=[ev.id],
        confidence=confidence,
    )
    return claim, ev


def test_confirms_cites_both_and_sets_high():
    bb = _board()
    claim, ev = _dom_claim(bb, "ICP is mid-market buyers at 51-200 employee companies.")
    ext = bb.evidence_store.add_external_evidence(
        source="linkedin",
        claim="LinkedIn lists company size as 51-200 employees.",
        raw_value={"company_size": "51-200 employees"},
        confidence_basis="third_party_aggregator",
        conflicts_with=[],
    )
    apply_ground_truth_to_claim(claim, bb.evidence_store, bb.claim_registry)
    assert claim.source_integrity_label == SourceIntegrityLabel.CORROBORATED
    assert claim.ground_truth_relation == GroundTruthRelation.CONFIRMS
    assert claim.confidence_band == ConfidenceBand.HIGH
    assert claim.confidence >= HIGH_CONFIDENCE
    assert ev.id in claim.evidence_refs
    assert ext.id in claim.evidence_refs
    assert claim.verification_status != VerificationStatus.CONTESTED


def test_contradicts_is_contested_and_routes_without_winner():
    bb = _board()
    claim, ev = _dom_claim(bb, "Target audience is Fortune-500 enterprises.")
    ext = bb.evidence_store.add_external_evidence(
        source="linkedin",
        claim="LinkedIn exposes 21 employees for AlienHouse Networks.",
        raw_value={"employee_facepile_cta": "Discover all 21 employees"},
        confidence_basis="third_party_aggregator",
        conflicts_with=[ev.id],
    )
    apply_ground_truth_to_claim(claim, bb.evidence_store, bb.claim_registry)
    assert claim.source_integrity_label == SourceIntegrityLabel.CONTESTED
    assert claim.ground_truth_relation == GroundTruthRelation.CONTRADICTS
    assert claim.verification_status == VerificationStatus.CONTESTED
    assert claim.routed_to == "verification.contradiction.v3"
    assert ev.id in claim.evidence_refs and ext.id in claim.evidence_refs

    detector = ContradictionDetector()
    contras = detector.detect_contradictions(bb.claim_registry.get_all())
    contested = [c for c in contras if c.routed_to == "verification.contradiction.v3"]
    assert contested
    assert all(c.winner_claim_id is None for c in contested)
    assert all("ROUTED_TO_verification.contradiction.v3" in c.resolution for c in contested)


def test_missing_ext_is_single_source_unverified_medium_cap():
    bb = _board()
    claim, ev = _dom_claim(bb, "ICP is enterprise buyers.", confidence=0.95)
    apply_ground_truth_to_claim(claim, bb.evidence_store, bb.claim_registry)
    assert claim.source_integrity_label == SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED
    assert claim.ground_truth_relation == GroundTruthRelation.MISSING_EXTERNAL
    assert claim.confidence_band == ConfidenceBand.MEDIUM
    assert claim.confidence <= MEDIUM_CONFIDENCE_CAP
    assert claim.verification_status == VerificationStatus.SINGLE_SOURCE_UNVERIFIED
    assert ev.id in claim.evidence_refs
    assert not any(r.startswith("ext_") for r in claim.evidence_refs)


def test_not_configured_ext_is_treated_as_missing():
    bb = _board()
    claim, _ = _dom_claim(
        bb,
        "Measured LCP is fast.",
        agent_id="seo.performance.v3",
        confidence=0.93,
    )
    bb.evidence_store.add_external_evidence(
        source="crux",
        claim="Google CrUX API is NOT_CONFIGURED.",
        raw_value={"status": "NOT_CONFIGURED"},
        confidence_basis="direct_api",
    )
    apply_ground_truth_to_claim(claim, bb.evidence_store, bb.claim_registry)
    assert claim.source_integrity_label == SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED
    assert claim.confidence <= MEDIUM_CONFIDENCE_CAP
    assert claim.claim_family == ClaimFamily.PERFORMANCE


def test_ungated_claim_is_not_applicable():
    bb = _board()
    ev = bb.evidence_store.add_evidence("dom", "test", text="Missing H1")
    claim = bb.claim_registry.register_claim(
        agent_id="seo.html.v3",
        statement="Homepage is missing an H1.",
        category=Category.TECHNICAL_SEO,
        evidence_refs=[ev.id],
        confidence=0.95,
    )
    apply_ground_truth_to_claim(claim, bb.evidence_store, bb.claim_registry)
    assert claim.source_integrity_label == SourceIntegrityLabel.NOT_APPLICABLE
    assert claim.confidence == 0.95


def test_integrity_gate_flags_single_source_and_contested():
    bb = _board()
    claim, ev = _dom_claim(bb, "Testimonials prove market-leading trust.", agent_id="trust.authority.v3")
    result = integrity_gate.validate_claims_and_evidence(
        bb.claim_registry.get_all(), bb.evidence_store, bb.claim_registry
    )
    types = {v.violation_type for v in result.violations}
    assert "SINGLE_SOURCE_UNVERIFIED" in types
    assert claim.source_integrity_label == SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED

    bb.evidence_store.add_external_evidence(
        source="ambitionbox",
        claim="AmbitionBox lists 1.0/5 based on 1 review.",
        raw_value={"overall_rating": 1.0, "review_count": 1},
        conflicts_with=[ev.id],
    )
    result2 = integrity_gate.validate_claims_and_evidence(
        bb.claim_registry.get_all(), bb.evidence_store, bb.claim_registry
    )
    types2 = {v.violation_type for v in result2.violations}
    assert "FLAGGED_UNVERIFIED" in types2
    assert claim.verification_status == VerificationStatus.CONTESTED


def test_findings_copy_source_integrity_label():
    bb = _board()
    claim, _ = _dom_claim(bb, "Pricing is INR enterprise contracts.", agent_id="business.commercial.v3")
    apply_ground_truth_to_claim(claim, bb.evidence_store, bb.claim_registry)
    findings = DecisionEngine().synthesize_findings(bb.claim_registry.get_all(), bb.evidence_store)
    assert findings
    assert findings[0].source_integrity_label == SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED
    assert findings[0].claim_family == ClaimFamily.PRICING

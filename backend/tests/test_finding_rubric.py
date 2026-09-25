"""Literal CERTAIN / LIKELY / GUESSING rubric and GUESSING+CRITICAL escalation."""
from app.cognition.blackboard import CognitiveBlackboard
from app.cognition.decision_engine import DecisionEngine
from app.cognition.finding_rubric import (
    ADVERSARIAL_AGENT_ID,
    apply_rubric_to_claim,
    classify_rubric,
    executive_eligible_claims,
)
from app.domain.enums import (
    Category,
    Materiality,
    ObservationType,
    RubricConfidence,
    Severity,
)
from app.domain.models import Finding
from app.scoring.engine import ScoringEngine
from app.domain.models import BusinessProfile


def _board():
    return CognitiveBlackboard("run_rubric", "https://example.com")


def test_certain_requires_dom_plus_external_and_no_conflict():
    bb = _board()
    ev = bb.evidence_store.add_evidence("dom", "test", text="51-200 employees")
    ext = bb.evidence_store.add_external_evidence(
        source="linkedin",
        claim="Company size 51-200 employees",
        raw_value={"company_size": "51-200"},
        confidence_basis="third_party_aggregator",
    )
    result = classify_rubric(
        statement="Company size is 51-200 employees.",
        evidence_refs=[ev.id, ext.id],
        store=bb.evidence_store,
        severity=Severity.MEDIUM,
    )
    assert result["confidence_rubric"] == RubricConfidence.CERTAIN
    assert result["source_agreement"] == 2
    assert result["held_from_executive"] is False
    contract = Finding(
        finding_id="f1",
        category=Category.COMPETITIVE,
        severity=Severity.MEDIUM,
        title="Company size is 51-200 employees.",
        finding="Company size is 51-200 employees.",
        description="",
        recommendation="n/a",
        evidence_refs=[ev.id, ext.id],
        confidence_rubric=result["confidence_rubric"],
        confidence_basis=result["confidence_basis"],
        materiality=result["materiality"],
        source_agreement=result["source_agreement"],
    ).emission_contract()
    assert set(contract.keys()) == {
        "finding", "evidence", "confidence", "confidence_basis", "materiality", "source_agreement",
    }
    assert contract["confidence"] == "CERTAIN"
    assert contract["evidence"] == [ev.id, ext.id]


def test_likely_when_exactly_one_source():
    bb = _board()
    ev = bb.evidence_store.add_evidence("dom", "test", text="Homepage H1 missing")
    result = classify_rubric(
        statement="Homepage is missing an H1.",
        evidence_refs=[ev.id],
        store=bb.evidence_store,
    )
    assert result["confidence_rubric"] == RubricConfidence.LIKELY
    assert result["source_agreement"] == 1
    assert "exactly one" in result["confidence_basis"].lower()


def test_likely_when_two_sources_but_inferred_basis():
    bb = _board()
    ev = bb.evidence_store.add_evidence("dom", "test", text="India HQ")
    ext = bb.evidence_store.add_external_evidence(
        source="inferred_jurisdiction",
        claim="Privacy regime inferred as DPDP",
        raw_value={"inferred_regime": "DPDP_2023_IN"},
        confidence_basis="inferred",
    )
    result = classify_rubric(
        statement="Applicable privacy regime is India's DPDP Act.",
        evidence_refs=[ev.id, ext.id],
        store=bb.evidence_store,
    )
    assert result["confidence_rubric"] == RubricConfidence.LIKELY
    assert result["source_agreement"] == 2
    assert "inferred" in result["confidence_basis"].lower()


def test_guessing_from_absence_language():
    result = classify_rubric(
        statement="Pricing is NOT_IN_EVIDENCE so the firm is probably mid-market.",
        evidence_refs=[],
        severity=Severity.LOW,
    )
    assert result["confidence_rubric"] == RubricConfidence.GUESSING
    assert result["source_agreement"] == 0


def test_guessing_critical_is_held_from_executive_until_adversarial():
    bb = _board()
    claim = bb.claim_registry.register_claim(
        agent_id="business.icp.v3",
        statement="We infer the conversion path is broken from absence of a CTA.",
        category=Category.COMPETITIVE,
        severity=Severity.CRITICAL,
        evidence_refs=[],
        confidence=0.4,
        impact=9,
        observation_type=ObservationType.INFERRED,
    )
    apply_rubric_to_claim(claim, bb.evidence_store)
    assert claim.confidence_rubric == RubricConfidence.GUESSING
    assert claim.materiality == Materiality.CRITICAL
    assert claim.held_from_executive is True
    assert claim.routed_to == ADVERSARIAL_AGENT_ID
    eligible = executive_eligible_claims(bb.claim_registry.get_all())
    assert claim not in eligible

    claim.adversarial_reviewed = True
    apply_rubric_to_claim(claim, bb.evidence_store)
    assert claim.held_from_executive is False
    assert claim in executive_eligible_claims(bb.claim_registry.get_all())


def test_guessing_findings_do_not_affect_scores():
    finding = Finding(
        finding_id="g1",
        category=Category.TECHNICAL_SEO,
        severity=Severity.CRITICAL,
        title="We infer crawl budget is exhausted.",
        description="",
        recommendation="n/a",
        confidence_rubric=RubricConfidence.GUESSING,
        materiality=Materiality.CRITICAL,
    )
    scores = ScoringEngine().calculate_scores(
        findings=[finding],
        business_profile=BusinessProfile(),
        has_schema=True,
        is_https=True,
    )
    assert scores.overall_score == 100


def test_synthesize_findings_stamps_emission_fields():
    bb = _board()
    ev = bb.evidence_store.add_evidence("dom", "test", text="Example Co")
    bb.claim_registry.register_claim(
        agent_id="seo.html.v3",
        statement="Homepage title is Example Co.",
        category=Category.ON_PAGE_SEO,
        evidence_refs=[ev.id],
        confidence=0.9,
    )
    findings = DecisionEngine().synthesize_findings(bb.claim_registry.get_all(), bb.evidence_store)
    assert findings
    f = findings[0]
    assert f.finding
    assert f.confidence_rubric in RubricConfidence
    assert f.confidence_basis
    assert f.materiality in Materiality
    assert f.source_agreement >= 1
    dumped = f.emission_contract()
    assert dumped["confidence"] in {"CERTAIN", "LIKELY", "GUESSING"}

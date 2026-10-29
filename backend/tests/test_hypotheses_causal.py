"""
Tests for Phase 3: Hypothesis Engine, Causal Reasoning, and Causal Prioritization.
"""
import pytest
from app.cognition.hypotheses import HypothesisEngine
from app.cognition.causal import CausalReasoningEngine
from app.cognition.decision_engine import DecisionEngine
from app.domain.models import Claim, PageEvidence, BusinessProfile
from app.domain.enums import Category, Severity
from app.evidence.store import EvidenceStore

def test_hypothesis_engine_evaluation():
    engine = HypothesisEngine()
    store = EvidenceStore("test_run")
    pages = [PageEvidence(url="https://test.com/")]

    hypotheses = engine.generate_initial_hypotheses("test.com", pages)
    assert len(hypotheses) == 3

    # Feed supporting claim for AI search schema hypothesis
    claims = [
        Claim(
            id="cl_schema",
            agent_id="test_worker",
            statement="Missing Schema.org JSON-LD markup on homepage and product pages.",
            category=Category.SCHEMA,
            severity=Severity.HIGH
        )
    ]

    updated = engine.evaluate_hypotheses_against_evidence(hypotheses, claims, store)
    ai_hyp = next(h for h in updated if h.domain == "AI_SEARCH")
    assert ai_hyp.posterior_confidence > ai_hyp.prior_probability
    assert len(ai_hyp.supporting_evidence_refs) == 1

def test_causal_reasoning_root_cause():
    engine = CausalReasoningEngine()
    bp = BusinessProfile(business_name="Acme Inc", niche="B2B Workflow AI")
    claims = [
        Claim(
            id="cl_icp",
            agent_id="test_worker",
            statement="Unclear ICP and target audience definition in hero section.",
            category=Category.COMPETITIVE,
            severity=Severity.HIGH
        ),
        Claim(
            id="cl_cta",
            agent_id="test_worker",
            statement="Generic CTA 'Learn More' does not guide commercial conversion.",
            category=Category.UX_CONVERSION,
            severity=Severity.HIGH
        )
    ]

    bottlenecks = engine.analyze_root_causes(claims, bp)
    assert len(bottlenecks) >= 1
    assert "ICP" in bottlenecks[0].root_cause
    assert len(bottlenecks[0].downstream_symptoms) >= 1

def test_causal_decision_prioritization():
    decision_engine = DecisionEngine()
    store = EvidenceStore("test_run")
    claim = Claim(
        id="cl_crit",
        agent_id="worker_crit",
        statement="Critical DNS / Canonical Redirect Loop",
        category=Category.TECHNICAL_SEO,
        severity=Severity.CRITICAL,
        impact=10,
        effort=2,
        confidence=0.95
    )

    findings = decision_engine.synthesize_findings([claim], store)
    assert len(findings) == 1
    # Priority should be calculated using causal prioritization and be high (8 - 10)
    assert findings[0].priority >= 8

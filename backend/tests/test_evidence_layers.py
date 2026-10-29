"""
Unit and integration tests for Dristik's 4-Layer Zero-Fake Evidence Architecture & Claim Ledger.
Verifies Layer 1 Machine Observations, Layer 2 Deterministic Findings, Layer 3 Derived Intelligence,
Layer 4 Grounded Recommendations, and Phase 2 Claim Ledger enforcement in the Validation Gate.
"""
import pytest
from datetime import datetime, timezone
from app.evidence.models import MachineObservation
from app.evidence.store import EvidenceStore
from app.evidence.deterministic_rules import DeterministicFindingEngine
from app.evidence.derived import DerivedIntelligenceEngine
from app.evidence.claim_ledger import ClaimLedgerBuilder
from app.domain.models import (
    Finding,
    ExecutiveReport,
    BusinessProfile,
    OverallScoreResult,
    CategoryScore,
    ThreeWayComparison,
    GroundedRecommendation,
)
from app.domain.enums import (
    Category,
    Severity,
    ClaimSourceType,
    RubricConfidence,
    EvidenceConfidence,
)
from app.reports.validation_gate import ValidationGate


# ---------------------------------------------------------------------------
# Layer 1: Machine Observation Tests
# ---------------------------------------------------------------------------
def test_layer1_machine_observation_contract():
    """Verify Layer 1 Machine Observation matches exact contract required."""
    obs = MachineObservation(
        type="observation",
        attribute="title",
        value="Business Consulting",
        source="html",
        evidence_id="EV_001",
    )
    layer1_dict = obs.to_layer1_json()
    assert layer1_dict == {
        "type": "observation",
        "attribute": "title",
        "value": "Business Consulting",
        "source": "html",
        "evidence_id": "EV_001",
    }


def test_layer1_store_registration_and_lookup():
    """Verify EvidenceStore records, indexes, and retrieves Layer 1 observations."""
    store = EvidenceStore(run_id="test_run_layer1")
    obs1 = store.add_observation(
        attribute="title",
        value="Acme Strategic Advisory",
        source="html",
        url="https://acme.com",
        selector="title",
    )
    assert obs1.evidence_id == "EV_001"
    assert obs1.attribute == "title"
    assert obs1.value == "Acme Strategic Advisory"

    # Verify retrieval by both upper and lower case ID
    retrieved = store.get_observation("EV_001")
    assert retrieved is not None
    assert retrieved.evidence_id == "EV_001"
    assert store.get_observation("ev_001") is not None

    # Verify retrieval by attribute
    title_obs = store.get_observations_by_attribute("title")
    assert len(title_obs) == 1
    assert title_obs[0].value == "Acme Strategic Advisory"


# ---------------------------------------------------------------------------
# Layer 2: Deterministic Finding Engine Tests
# ---------------------------------------------------------------------------
def test_layer2_duplicate_title_finding():
    """Verify TITLE_DUPLICATE_001 triggers with exact rule_id, evidence_ids, and certain confidence."""
    store = EvidenceStore(run_id="test_run_layer2")
    obs1 = store.add_observation(
        attribute="title",
        value="Business Consulting",
        source="html",
        url="https://acme.com/page-1",
        selector="title",
    )
    obs2 = store.add_observation(
        attribute="title",
        value="Business Consulting",
        source="html",
        url="https://acme.com/page-2",
        selector="title",
    )

    engine = DeterministicFindingEngine()
    findings = engine.evaluate(store)

    dup_findings = [f for f in findings if f.rule_id == "TITLE_DUPLICATE_001"]
    assert len(dup_findings) == 1
    f = dup_findings[0]

    assert f.rule_id == "TITLE_DUPLICATE_001"
    assert "EV_001" in f.evidence_ids
    assert "EV_002" in f.evidence_ids
    assert f.confidence == 1.0
    assert f.confidence_rubric == RubricConfidence.VERIFIED

    # Check Layer 2 export contract
    l2_json = f.to_layer2_json()
    assert l2_json["rule_id"] == "TITLE_DUPLICATE_001"
    assert l2_json["evidence_ids"] == ["EV_001", "EV_002"]
    assert l2_json["confidence"] == "certain"


def test_layer2_missing_h1_and_title_rules():
    """Verify deterministic rules trigger for missing H1, missing title, and HTTP error."""
    store = EvidenceStore(run_id="test_run_rules")
    store.add_observation("title", value="", source="html", url="https://acme.com/no-title")
    store.add_observation("h1", value=[], source="dom", url="https://acme.com/no-h1")
    store.add_observation("status_code", value=404, source="http_header", url="https://acme.com/broken")
    store.add_observation("ttfb_ms", value=1850.0, source="http_header", url="https://acme.com/slow")

    engine = DeterministicFindingEngine()
    findings = engine.evaluate(store)
    rule_ids = {f.rule_id for f in findings}

    assert "TITLE_MISSING_001" in rule_ids
    assert "H1_MISSING_001" in rule_ids
    assert "STATUS_4XX_5XX_001" in rule_ids
    assert "SLOW_TTFB_001" in rule_ids

    for f in findings:
        assert len(f.evidence_ids) >= 1
        assert f.confidence == 1.0
        assert f.to_layer2_json()["confidence"] == "certain"


# ---------------------------------------------------------------------------
# Layer 3: Derived Intelligence Tests
# ---------------------------------------------------------------------------
def test_layer3_derived_intelligence_five_metrics():
    """Verify all 5 derived metrics have explicit formula, input evidence, algorithm version, and timestamp."""
    store = EvidenceStore(run_id="test_run_layer3")
    store.add_observation("title", "Enterprise Cloud Architecture", url="https://acme.com")
    store.add_observation("h1", ["Modern Cloud Platform Infrastructure"], url="https://acme.com")
    store.add_observation("schema_types", ["Organization", "WebSite"], url="https://acme.com")
    store.add_observation("sameas_urls", ["https://linkedin.com/company/acme"], url="https://acme.com")
    store.add_observation("business_name", "Acme Cloud", url="https://acme.com")
    store.add_observation("cta_texts", ["Request Architecture Review", "Start Free Trial"], url="https://acme.com")
    store.add_observation("visible_pricing_text", ["$99/month", "$499/enterprise"], url="https://acme.com/pricing")
    store.add_observation("faq_questions", ["How does migration work?", "What SLA is provided?"], url="https://acme.com")
    store.add_observation("pricing_signals", True, url="https://acme.com")

    engine = DerivedIntelligenceEngine()
    metrics = engine.compute_all(store)
    assert len(metrics) == 5

    metric_names = {m.name for m in metrics}
    assert "topic_coverage" in metric_names
    assert "entity_consistency" in metric_names
    assert "intent_coverage" in metric_names
    assert "information_gain" in metric_names
    assert "citation_readiness" in metric_names

    for m in metrics:
        assert m.formula != "", f"{m.name} missing formula"
        assert len(m.input_evidence_ids) > 0, f"{m.name} missing input evidence IDs"
        assert m.algorithm_version != "", f"{m.name} missing algorithm version"
        assert m.timestamp != "", f"{m.name} missing timestamp"
        assert 0.0 <= m.score <= 100.0


# ---------------------------------------------------------------------------
# Layer 4: Grounded Recommendation Tests
# ---------------------------------------------------------------------------
def test_layer4_grounded_recommendation():
    """Verify Layer 4 recommendations have what, why, how, example, and link to finding & evidence."""
    rec = GroundedRecommendation(
        recommendation_id="REC_001",
        underlying_finding_id="FND_001",
        underlying_evidence_ids=["EV_001", "EV_002"],
        what_to_change="Rewrite page titles to include distinct product categories.",
        why="Duplicate title tags dilute page relevance.",
        how_to_change="Update <title> tags in index.html.",
        example="<title>Acme | Enterprise Security Solutions</title>",
        target_file="index.html",
    )
    assert rec.underlying_finding_id == "FND_001"
    assert rec.underlying_evidence_ids == ["EV_001", "EV_002"]
    assert rec.what_to_change != ""
    assert rec.why != ""
    assert rec.how_to_change != ""
    assert rec.example is not None


# ---------------------------------------------------------------------------
# Phase 2: Claim Ledger & Zero-Fake Validation Gate Tests
# ---------------------------------------------------------------------------
def _build_stub_report(findings=None, story="Standard executive story summary.") -> ExecutiveReport:
    scores = OverallScoreResult(
        overall_score=75.0,
        grade="B",
        health_label="Sound",
        category_scores={
            "TECHNICAL_SEO": CategoryScore(category=Category.TECHNICAL_SEO, score=75.0, weight=50.0, weighted_score=37.5, summary="Technical SEO is sound"),
            "ON_PAGE_SEO": CategoryScore(category=Category.ON_PAGE_SEO, score=75.0, weight=50.0, weighted_score=37.5, summary="On-page SEO is sound"),
        }
    )
    bp = BusinessProfile(
        business_name="Acme Corp",
        value_proposition="Enterprise cloud computing solutions",
        target_audience="CTOs and DevOps Engineers",
        business_model="B2B SaaS",
    )
    return ExecutiveReport(
        report_id="rep_test_01",
        website_url="https://acme.com",
        domain="acme.com",
        generated_at=datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC"),
        business_profile=bp,
        scores=scores,
        story_summary=story,
        what_site_gets_right=["Strong domain authority", "Valid SSL certificate"],
        what_is_holding_it_back=["Duplicate title tags"],
        primary_strategic_opportunity="Deploy unique title tags across catalog",
        consultant_advice_what_to_ignore="Ignore minor animation updates",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear identity",
            search_engine_perspective="Indexable",
            ai_answer_engine_perspective="Structured"
        ),
        findings=findings or [],
    )


def test_claim_ledger_source_types_and_unsupported_rejection():
    """Verify Claim Ledger tags 6 source types and rejects UNSUPPORTED from website facts."""
    store = EvidenceStore(run_id="test_run_ledger")
    obs = store.add_observation("title", "Acme Corp", url="https://acme.com")

    # Finding 1 is supported by EV_001
    supported_finding = Finding(
        finding_id="FND_001",
        rule_id="TITLE_DUPLICATE_001",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        title="Duplicate title observed",
        description="Observed on pages",
        recommendation="Fix title tags",
        evidence_ids=[obs.evidence_id],
        confidence=1.0,
    )

    # Finding 2 is unsupported (0 evidence)
    unbacked_finding = Finding(
        finding_id="FND_002",
        category=Category.CONTENT,
        severity=Severity.HIGH,
        title="Unbacked hallucinated finding",
        description="No backing DOM evidence",
        recommendation="Rewrite everything",
        evidence_ids=[],
        evidence_refs=[],
        confidence=0.5,
    )

    report = _build_stub_report(findings=[supported_finding, unbacked_finding])
    builder = ClaimLedgerBuilder(run_id="test_run_ledger")
    ledger = builder.build_ledger(report, store)

    assert ledger.certified_zero_fake is False
    assert ledger.rejected_unsupported_count >= 1

    # Check source types present
    source_types = {e.source_type for e in ledger.entries}
    assert ClaimSourceType.OBSERVED in source_types
    assert ClaimSourceType.UNSUPPORTED in source_types

    # Attach ledger to report and test ValidationGate
    report.claim_ledger = ledger
    gate_res = ValidationGate.validate_report(report)
    assert gate_res.is_valid is False
    assert "zero_unsupported_website_facts" in gate_res.failed_checks

    # Run auto-repair through ValidationGate
    repaired_report, repaired_gate_res = ValidationGate.enforce_gate(report)
    assert repaired_gate_res.is_valid is True
    assert "zero_unsupported_website_facts" in repaired_gate_res.passed_checks
    assert len(repaired_report.findings) == 1
    assert repaired_report.findings[0].finding_id == "FND_001"

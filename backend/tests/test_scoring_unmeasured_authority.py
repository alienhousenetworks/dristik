"""
Tests for honest scoring behavior when external authority connectors are unmeasured vs measured.
Enforces the professional standard: never assign an unearned 50/100 provisional score to unmeasured authority.
"""
from app.domain.models import BusinessProfile, Finding, CategoryScore
from app.domain.enums import Category, Severity, BusinessIntent, EvidenceClass
from app.evidence.models import EvidenceRef
from app.scoring.engine import ScoringEngine


def test_unmeasured_authority_shows_connector_unavailable():
    engine = ScoringEngine()
    findings = [
        Finding(
            finding_id="f_h1",
            category=Category.CONTENT,
            severity=Severity.MEDIUM,
            title="Weak H1 Value Proposition",
            description="Homepage H1 does not state what the business does.",
            recommendation="Update H1 heading to clearly describe primary value proposition.",
            impact=6,
            confidence=0.85
        )
    ]
    scores = engine.calculate_scores(
        findings=findings,
        business_profile=BusinessProfile(business_name="Acme Corp", primary_intent=BusinessIntent.SAAS),
        external_authority_connected=False
    )
    
    trust_score = scores.category_scores.get(Category.TRUST_AUTHORITY.value)
    assert trust_score is not None
    assert trust_score.score is None
    assert trust_score.status == "NOT_MEASURED"
    assert trust_score.provenance == "CONNECTOR_UNAVAILABLE"
    assert "not measured — connector unavailable" in trust_score.summary.lower()
    assert trust_score.weight == 0.0

    # Ensure overall score is derived from measured categories whose active weights sum to 1.0
    active_weights = scores.intent_adjusted_weights
    assert Category.TRUST_AUTHORITY.value not in active_weights
    assert abs(sum(active_weights.values()) - 1.0) < 1e-4

    # Verify math derivation lists the unmeasured category cleanly
    unmeasured_row = next(r for r in scores.mathematical_derivation if r["category"] == Category.TRUST_AUTHORITY.value)
    assert unmeasured_row["raw_score"] == "Not measured"
    assert unmeasured_row["status"] == "NOT_MEASURED"


def test_measured_authority_when_connector_active():
    engine = ScoringEngine()
    findings = [
        Finding(
            finding_id="f_backlink_penalty",
            category=Category.TRUST_AUTHORITY,
            severity=Severity.HIGH,
            title="Toxic Backlink Spike",
            description="External link graph shows sudden influx of low-quality referring domains.",
            recommendation="Disavow toxic referring domains via GSC disavow tool.",
            impact=8,
            confidence=0.9,
            evidence_class=EvidenceClass.EXTERNALLY_VERIFIED,
            evidence_refs=["hash_123"]
        )
    ]
    scores = engine.calculate_scores(
        findings=findings,
        business_profile=BusinessProfile(business_name="Acme Corp", primary_intent=BusinessIntent.SAAS),
        external_authority_connected=True
    )

    trust_score = scores.category_scores.get(Category.TRUST_AUTHORITY.value)
    assert trust_score is not None
    assert trust_score.score is not None
    assert trust_score.score < 100.0
    assert trust_score.status == "MEASURED"
    assert trust_score.weight > 0.0

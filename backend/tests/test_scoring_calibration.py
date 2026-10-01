"""Calibration keeps technical severity, business impact, confidence, and blocking independent."""
from app.domain.enums import (
    BusinessIntent,
    Category,
    ConfidenceBand,
    ImpactLevel,
    RubricConfidence,
    Severity,
    SourceIntegrityLabel,
)
from app.domain.models import (
    BusinessProfile,
    CodePatch,
    ExecutiveReport,
    Finding,
    FindingEvidence,
    HonestScores,
    OverallScoreResult,
    RoadmapItem,
    ThreeWayComparison,
)
from app.reports.narrative import NarrativeGenerator
from app.reports.validation_gate import ValidationGate
from app.scoring.calibration import calibrate_finding
from app.scoring.engine import ScoringEngine


def _profile() -> BusinessProfile:
    return BusinessProfile(
        business_name="Acme",
        domain="acme.com",
        industry="SaaS",
        value_proposition="Mesh networking",
        primary_cta="Book a demo",
        primary_intent=BusinessIntent.LEAD_GENERATION,
    )


def _scores() -> OverallScoreResult:
    return OverallScoreResult(
        overall_score=54.0,
        grade="D",
        health_label="Needs Attention",
        category_scores={},
    )


def _finding(**kwargs) -> Finding:
    evidence = kwargs.pop("evidence", None)
    if evidence is None:
        evidence = [FindingEvidence(url="https://acme.com/", snippet="observed")]
    base = dict(
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        description="Observed on the crawled response.",
        recommendation="Fix the observed defect.",
        confidence=0.95,
        confidence_rubric=RubricConfidence.CERTAIN,
        source_integrity_label=SourceIntegrityLabel.CORROBORATED,
        evidence=evidence,
    )
    base.update(kwargs)
    return Finding(**base)


def test_hsts_is_high_technical_medium_business_and_not_blocking():
    hsts = _finding(
        finding_id="hsts",
        title="Missing HSTS Header",
        description="Strict-Transport-Security header is not sent.",
    )
    calibrate_finding(hsts)
    cal = hsts.calibrated_impact
    assert cal.technical_severity == Severity.HIGH
    assert cal.business_impact == ImpactLevel.MEDIUM
    assert cal.confidence_band == ConfidenceBand.HIGH
    assert cal.is_blocking is False
    assert cal.blocks == []
    assert cal.affected_outcomes[0].outcome == "security_posture"

    engine = ScoringEngine()
    scores = engine.calculate_scores([hsts], _profile())
    tech = scores.category_scores[Category.TECHNICAL_SEO.value]
    assert tech.deductions[0]["points_lost"] > 0
    assert tech.deductions[0]["blocking"] is False
    for name, cat in scores.category_scores.items():
        if name != Category.TECHNICAL_SEO.value:
            assert all(item["finding_id"] != "hsts" for item in cat.deductions)

    narrative = NarrativeGenerator().build_narrative(
        business_profile=_profile(),
        findings=[hsts],
        scores=_scores(),
        synthesizer_output={
            "story_summary": (
                "Primary constraint: HSTS missing. Until that defect is removed, "
                "additional SEO or design work will not change buyer or citation outcomes."
            )
        },
    )
    story = narrative["story_summary"].lower()
    assert "will not change" not in story
    assert "additional seo or design" not in story
    assert "buyer or citation outcomes" not in story
    assert "do not block" in story
    assert "weighted rollup" in story
    assert "medium" in story


def test_missing_cta_outranks_hsts_and_stays_medium_confidence_without_analytics():
    hsts = _finding(
        finding_id="hsts",
        title="Missing HSTS Header",
        description="Strict-Transport-Security is absent.",
    )
    cta = _finding(
        finding_id="cta",
        category=Category.UX_CONVERSION,
        title="Homepage lacks prominent CTA",
        description="No primary call to action above the fold.",
        confidence_rubric=RubricConfidence.CERTAIN,
    )
    narrative = NarrativeGenerator().build_narrative(
        business_profile=_profile(),
        findings=[hsts, cta],
        scores=_scores(),
        synthesizer_output={},
    )
    assert narrative["what_is_holding_it_back"][0] == "Homepage lacks prominent CTA"
    calibrate_finding(cta)
    assert cta.calibrated_impact.technical_severity == Severity.HIGH
    assert cta.calibrated_impact.business_impact == ImpactLevel.HIGH
    assert cta.calibrated_impact.confidence_band == ConfidenceBand.MEDIUM
    assert cta.calibrated_impact.is_blocking is False
    story = narrative["story_summary"].lower()
    assert "homepage lacks prominent cta" in story or "prominent cta" in story
    assert "transport-header" in story
    assert "not blocking" in story
    assert "will not change" not in story


def test_missing_robots_txt_is_not_a_disallow_blocker():
    missing = _finding(
        finding_id="robots",
        severity=Severity.MEDIUM,
        title="Missing robots.txt",
        description="Fetch returned HTTP 404 for /robots.txt.",
    )
    calibrate_finding(missing)
    cal = missing.calibrated_impact
    assert cal.technical_severity == Severity.MEDIUM
    assert cal.business_impact == ImpactLevel.MEDIUM
    assert cal.confidence_band == ConfidenceBand.HIGH
    assert cal.is_blocking is False
    assert cal.blocks == []

    disallow = _finding(
        finding_id="disallow",
        severity=Severity.CRITICAL,
        title="robots.txt Disallow: / blocks the site",
        description="robots.txt contains Disallow: / for all user agents.",
    )
    calibrate_finding(disallow)
    assert disallow.calibrated_impact.is_blocking is True
    assert disallow.calibrated_impact.blocks == ["indexation"]
    assert disallow.calibrated_impact.business_impact == ImpactLevel.HIGH

    narrative = NarrativeGenerator().build_narrative(
        business_profile=_profile(),
        findings=[disallow],
        scores=_scores(),
        synthesizer_output={
            "story_summary": (
                "Until that defect is removed, additional SEO or design work will not change buyer or citation outcomes."
            )
        },
    )
    story = narrative["story_summary"].lower()
    assert "will not change" not in story
    assert "indexation" in story
    assert "independent" in story

    scores = ScoringEngine().calculate_scores([disallow], _profile())
    tech = scores.category_scores[Category.TECHNICAL_SEO.value]
    assert tech.deductions[0]["points_lost"] > 0
    assert tech.score <= 20.0
    assert all(
        item["finding_id"] != "disallow"
        for name, cat in scores.category_scores.items()
        if name != Category.TECHNICAL_SEO.value
        for item in cat.deductions
    )


def test_missing_alt_is_low_medium_business_impact():
    alt = _finding(
        finding_id="alt",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="Missing alt text on informative images",
        description="Images lack alt attributes.",
    )
    calibrate_finding(alt)
    cal = alt.calibrated_impact
    assert cal.technical_severity == Severity.MEDIUM
    assert cal.business_impact_label == "Low/Medium"
    assert cal.confidence_band == ConfidenceBand.HIGH
    assert cal.is_blocking is False
    outcomes = {item.outcome: item.level for item in cal.affected_outcomes}
    assert outcomes["accessibility"] == ImpactLevel.MEDIUM
    assert outcomes["image_search"] == ImpactLevel.LOW


def test_unknown_high_severity_does_not_become_high_business_impact():
    finding = _finding(
        finding_id="pixel",
        title="Custom tracking pixel missing on the marketing subdomain",
        description="The tag is absent from the sampled page.",
    )
    calibrate_finding(finding)
    assert finding.calibrated_impact.technical_severity == Severity.HIGH
    assert finding.calibrated_impact.business_impact == ImpactLevel.MEDIUM
    assert finding.calibrated_impact.business_impact != ImpactLevel.HIGH
    assert finding.calibrated_impact.is_blocking is False


def test_empty_findings_still_score_100_and_a_defect_scores_below():
    engine = ScoringEngine()
    profile = _profile()
    assert engine.calculate_scores([], profile).overall_score == 100.0
    degraded = engine.calculate_scores(
        [_finding(finding_id="hsts", title="Missing HSTS Header", description="Strict-Transport-Security is absent.")],
        profile,
    )
    assert degraded.overall_score < 100.0


def test_validation_gate_rewrites_non_blocking_outcome_claim():
    report = ExecutiveReport(
        report_id="rep_cal",
        analysis_id="run_cal",
        website_url="https://acme.com",
        domain="acme.com",
        generated_at="September 29, 2026 - 12:00 UTC",
        business_profile=_profile(),
        scores=OverallScoreResult(
            overall_score=54.0,
            grade="D",
            health_label="Needs Attention",
            category_scores={},
        ),
        story_summary=(
            "Primary constraint: HSTS missing. Until that defect is removed, "
            "additional SEO or design work will not change buyer or citation outcomes."
        ),
        primary_strategic_opportunity="Ship the header and pause design work.",
        consultant_advice_what_to_ignore=(
            "Ignore vanity work until the verified root constraint is fixed."
        ),
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Buyer can still load the page.",
            search_engine_perspective="Pages return 200.",
            ai_answer_engine_perspective="No citation measurement was run.",
        ),
        honest_scores=HonestScores(human_score=54, google_score=54, ai_citation_score=54, score_band="Needs Attention"),
        findings=[
            _finding(
                finding_id="hsts",
                title="Missing HSTS Header",
                description="Strict-Transport-Security is absent.",
            )
        ],
        code_patches=[
            CodePatch(
                patch_id="p1",
                title="Security headers",
                category=Category.TECHNICAL_SEO,
                target_file="nginx.conf",
                after_snippet="add_header Strict-Transport-Security \"max-age=31536000\" always;",
                explanation="Add the observed missing header.",
            )
        ],
        roadmap_7_days=[
            RoadmapItem(
                timeframe="7_days",
                title="Add HSTS",
                description="Set the header at the edge.",
                impact="Medium",
                effort="Low",
                category=Category.TECHNICAL_SEO,
            )
        ],
        roadmap_30_days=[
            RoadmapItem(
                timeframe="30_days",
                title="Clarify the primary CTA",
                description="Rewrite the hero action.",
                impact="High",
                effort="Medium",
                category=Category.UX_CONVERSION,
            )
        ],
        roadmap_90_days=[
            RoadmapItem(
                timeframe="90_days",
                title="Measure citation rate",
                description="Query answer engines on the buyer question set.",
                impact="High",
                effort="Medium",
                category=Category.AI_SEARCH,
            )
        ],
    )
    repaired, result = ValidationGate.enforce_gate(report)
    blob = " ".join([
        repaired.story_summary,
        repaired.primary_strategic_opportunity,
        repaired.consultant_advice_what_to_ignore,
    ]).lower()
    assert "will not change" not in blob
    assert "additional seo or design" not in blob
    assert "until the verified root constraint is fixed" not in blob
    assert "outcome_claims_respect_blocking" not in result.failed_checks

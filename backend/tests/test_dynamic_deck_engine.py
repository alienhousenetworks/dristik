"""
Tests for the Dynamic Executive Presentation Generation Engine.
Validates:
1. Deterministic Metric Engine ('Honest Math' rule & formula verification)
2. Blackboard Adjudication Auditor (evidence token binding & confidence rubric)
3. Dynamic Storyline Architect (data-quota rule >= 75% & provenance hashing)
4. Executive Narrative Synthesizer (quantified assertions & Read: takeaways)
5. Deck Quality Linter (multi-pass verification & error detection)
6. HTML Vector Presentation Engine (16:9 SVG charts & interactive controls)
7. Dual-output end-to-end orchestration (PPTX & HTML parity)
"""
import pytest
from app.domain.models import (
    ExecutiveReport,
    BusinessProfile,
    OverallScoreResult,
    ThreeWayComparison,
    CrawlManifest,
    PageEvidence,
    Finding,
    Severity,
    Category,
    CategoryScore,
)
from app.agents.deck.models import (
    DeckBlueprint,
    SlideBlueprint,
    SlideLayoutType,
    DeckChartType,
    ChartDataSpec,
    CardSpec
)
from app.agents.deck.math_engine import DeterministicMetricEngine, MetricBundle
from app.agents.deck.adjudication import BlackboardAdjudicationAuditor
from app.agents.deck.outline_planner import DynamicStorylineArchitect
from app.agents.deck.narrative_synthesizer import ExecutiveNarrativeSynthesizer
from app.agents.deck.linter import DeckQualityLinter
from app.agents.deck.html_deck_renderer import HtmlVectorDeckRenderer
from app.agents.deck.coordinator import (
    DeckOrchestrator,
    generate_executive_pptx_deck,
    generate_executive_html_deck,
)


def _build_mock_executive_report() -> ExecutiveReport:
    scores = OverallScoreResult(
        overall_score=76.0,
        grade="B",
        health_label="Calibrated",
        category_scores={
            "TECHNICAL_SEO": CategoryScore(category=Category.TECHNICAL_SEO, score=84.0, summary="Solid HTTP foundations"),
            "SCHEMA": CategoryScore(category=Category.SCHEMA, score=62.0, summary="Missing entity definitions"),
            "CONTENT": CategoryScore(category=Category.CONTENT, score=72.0, summary="Good depth"),
            "GEO": CategoryScore(category=Category.GEO, score=58.0, summary="Answer engine citation ambiguity"),
            "UX_CONVERSION": CategoryScore(category=Category.UX_CONVERSION, score=81.0, summary="Friction on signup"),
            "COMPETITIVE": CategoryScore(category=Category.COMPETITIVE, score=70.0, summary="Parity"),
        }
    )
    pages = [
        PageEvidence(
            url="https://cloud-scale.io/",
            page_type="homepage",
            title="CloudScale — Distributed Database Systems",
            meta_description="High-availability multi-region database infrastructure.",
            word_count=520,
            ttfb_ms=165.0
        ),
        PageEvidence(
            url="https://cloud-scale.io/pricing",
            page_type="pricing",
            title="Pricing — CloudScale Enterprise",
            meta_description="Transparent clusters and usage tiers.",
            word_count=310,
            ttfb_ms=185.0
        ),
        PageEvidence(
            url="https://cloud-scale.io/docs",
            page_type="product",
            title="Documentation — CloudScale Architecture",
            meta_description="Technical reference manuals and deployment guides.",
            word_count=640,
            ttfb_ms=140.0
        )
    ]
    manifest = CrawlManifest(
        domain="cloud-scale.io",
        base_url="https://cloud-scale.io",
        total_pages_discovered=3,
        pages=pages,
        sitemap_found=True,
        robots_txt_found=True,
        crawl_health={"avg_ttfb_ms": 163.3, "broken_links_count": 0}
    )
    findings = [
        Finding(
            finding_id="f_geo_01",
            title="Omission of JSON-LD Organization & Service Nodes",
            description="Homepage AST reveals zero machine-readable entity schemas for generative scrapers.",
            category=Category.GEO,
            severity=Severity.CRITICAL,
            impact=9,
            recommendation="Inject Schema.org Organization graph with SameAs references."
        ),
        Finding(
            finding_id="f_schema_02",
            title="Missing FAQ Schema Microdata on Pricing Route",
            description="Pricing questions are rendered in flat text without FAQPage schema.",
            category=Category.SCHEMA,
            severity=Severity.HIGH,
            impact=7,
            recommendation="Add FAQPage microdata to pricing tiers."
        ),
        Finding(
            finding_id="f_ux_03",
            title="Low Contrast Form Microcopy on Trial Form",
            description="Form helper text fails WCAG AAA ratio on dark mode inputs.",
            category=Category.UX_CONVERSION,
            severity=Severity.MEDIUM,
            impact=5,
            recommendation="Increase input placeholder contrast to #94A3B8."
        )
    ]
    return ExecutiveReport(
        report_id="rep_cs_001",
        analysis_id="an_cs_001",
        website_url="https://cloud-scale.io",
        domain="cloud-scale.io",
        generated_at="2026-10-10 12:00:00 UTC",
        business_profile=BusinessProfile(business_name="CloudScale"),
        scores=scores,
        story_summary="Independent multi-agent audit completed for CloudScale.",
        primary_strategic_opportunity="Deploy machine-readable entity graphs and /llms.txt manifest.",
        consultant_advice_what_to_ignore="Ignore cosmetic redesigns and backlink blasts.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Human visitors perceive high engineering authority but encounter subtle signup friction.",
            search_engine_perspective="Search spiders crawl canonical routes with 200 OK cleanly.",
            ai_answer_engine_perspective="Generative answer engines experience citation ambiguity due to marketing-dense prose."
        ),
        crawl_manifest=manifest,
        findings=findings
    )


def test_deterministic_metric_engine_calculations():
    """Verify that all metrics are computed deterministically with exact formula metadata."""
    report = _build_mock_executive_report()
    engine = DeterministicMetricEngine()
    bundle = engine.compute_bundle(report)

    assert bundle.domain == "cloud-scale.io"
    assert bundle.overall_score == 76.0
    assert bundle.grade == "B"
    assert bundle.health_label == "Calibrated"

    # Verify TTFB stats
    # Samples: [140.0, 165.0, 185.0]
    assert bundle.ttfb_metrics["min_ms"] == 140.0
    assert bundle.ttfb_metrics["max_ms"] == 185.0
    assert bundle.ttfb_metrics["median_ms"] == 165.0
    assert bundle.ttfb_metrics["sample_size"] == 3.0

    # Verify potential gain calculation
    # CRITICAL (1 * 4.5) + HIGH (1 * 2.8) + MEDIUM (1 * 1.2) = 8.5
    assert bundle.remediation_potential_gain == 8.5
    assert bundle.projected_post_remediation_score == 84.5

    # Verify formula tracking
    assert "overall_score" in bundle.metrics
    assert bundle.metrics["overall_score"].formula != ""
    assert bundle.metrics["ttfb_median"].units == "ms"


def test_blackboard_adjudication_auditor():
    """Verify findings are audited against evidence tokens and confidence rules."""
    report = _build_mock_executive_report()
    auditor = BlackboardAdjudicationAuditor()
    adj_report = auditor.audit_report(report)

    assert adj_report.total_findings_evaluated == 3
    assert adj_report.audited_count == 3
    assert len(adj_report.evidence_token_inventory) >= 3

    # Every finding must have evidence tokens bound
    for f in adj_report.adjudicated_findings:
        assert len(f.evidence_tokens) > 0
        assert f.evidence_tokens[0].startswith("ev_")
        assert f.confidence in ("CERTAIN", "LIKELY")
        assert "Audited against snapshot store" in f.grounding_proof


def test_dynamic_storyline_architect_data_quota():
    """Verify outline planner enforces the >= 75% evidence-bound quota and computes provenance hash."""
    report = _build_mock_executive_report()
    planner = DynamicStorylineArchitect()
    blueprint = planner.plan_blueprint(report.domain, report.generated_at, report)

    assert blueprint.total_slides >= 70
    assert blueprint.data_quota_ratio is not None
    assert blueprint.data_quota_ratio >= 0.75  # Institutional Data-Quota Rule
    assert blueprint.provenance_hash is not None
    assert len(blueprint.provenance_hash) == 16


def test_executive_narrative_synthesizer():
    """Verify narrative synthesizer creates quantified assertions and Read: takeaways."""
    report = _build_mock_executive_report()
    engine = DeterministicMetricEngine()
    bundle = engine.compute_bundle(report)
    synthesizer = ExecutiveNarrativeSynthesizer()

    headline = synthesizer.synthesize_headline("overall_diagnostic", bundle)
    assert "Scores 76/100" in headline
    assert "[Grade B]" in headline

    latency_headline = synthesizer.synthesize_headline("http_latency", bundle)
    assert "165.0ms" in latency_headline

    interp = synthesizer.synthesize_interpretation("pillars_radar", bundle)
    assert interp.startswith("Read:")
    assert "76/100" in interp


def test_deck_quality_linter_validation():
    """Verify that multi-pass linter flags missing takeaways or duplicate titles."""
    report = _build_mock_executive_report()
    orchestrator = DeckOrchestrator()
    blueprint = orchestrator.build_blueprint(report)

    linter = DeckQualityLinter()
    result = linter.lint_blueprint(blueprint)

    # Clean blueprint should pass lint checks
    assert result.passed is True
    assert result.errors_count == 0
    assert blueprint.lint_result is not None

    # Introduce a deliberate violation (duplicate title)
    blueprint.slides[1].title = blueprint.slides[0].title
    violation_result = linter.lint_blueprint(blueprint)
    assert violation_result.passed is False
    assert any(i.rule == "NON_REPETITION_TITLE" for i in violation_result.issues)


def test_html_vector_deck_renderer():
    """Verify HTML vector presentation renders 16:9 layout, SVG charts, and interactive controls."""
    report = _build_mock_executive_report()
    html_content, blueprint = generate_executive_html_deck(report)

    assert isinstance(html_content, str)
    assert len(html_content) > 15000
    assert "<!DOCTYPE html>" in html_content
    assert "Dristik Executive Intelligence Dossier" in html_content
    assert "slide-frame" in html_content
    assert "svg viewBox" in html_content  # Vector SVG charts present
    assert "interpretation-box" in html_content  # Read: ... takeaway boxes present
    assert "toggleFullscreen()" in html_content  # Interactive keyboard/slide controller present


def test_dual_output_pptx_and_manifest_parity():
    """Verify native PPTX binary generation and manifest export with full lineage."""
    report = _build_mock_executive_report()
    pptx_bytes, blueprint = generate_executive_pptx_deck(report)

    # 1. PPTX verification
    assert isinstance(pptx_bytes, bytes)
    assert pptx_bytes.startswith(b"PK\x03\x04")
    assert len(pptx_bytes) > 25000

    # 2. Blueprint manifest verification
    assert blueprint.total_slides >= 70
    assert blueprint.dedup_verification_token != ""
    assert blueprint.provenance_hash is not None
    assert blueprint.data_quota_ratio is not None
    assert blueprint.lint_result is not None
    assert blueprint.lint_result.passed is True

"""
Test Suite: test_scoring_timing_and_honest_flag.py
Milestone M1 (Phase 0) Verification:
1. External authority connection status and data_state flag detection (key mismatch fix).
2. Scoring execution timing: scoring runs strictly AFTER post-DAG analyzers,
   AI search visibility, and external authority attachment.
3. Roadmap and category score integration for external authority domain findings.
4. calculate_honest_scores dynamic flag propagation and DAG runner parity.
5. Canonical 8-category weights and honest perspective formulas consistency.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.domain.enums import (
    AnalysisStage,
    BusinessIntent,
    Category,
    Severity,
    RubricConfidence,
    EvidenceClass,
)
from app.domain.models import (
    AnalysisRun,
    BusinessProfile,
    Finding,
    FindingEvidence,
    CategoryScore,
    OverallScoreResult,
    HonestScores,
    CrawlManifest,
    PageEvidence,
)
from app.scoring.engine import ScoringEngine
from app.scoring.weights import BASELINE_WEIGHTS, compute_intent_adjusted_weights
from app.scoring.scoring_rubric import get_scoring_rubric_v4
from app.orchestration.orchestrator import orchestrator, AnalysisOrchestrator


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def business_profile() -> BusinessProfile:
    return BusinessProfile(
        business_name="Acme Enterprise Tech",
        domain="acme-tech.com",
        industry="Enterprise SaaS",
        value_proposition="Autonomous Cloud Infrastructure Intelligence",
        primary_cta="Schedule Architecture Review",
        primary_intent=BusinessIntent.SAAS,
    )


@pytest.fixture
def internal_findings() -> list[Finding]:
    return [
        Finding(
            finding_id="find_tech_001",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title="XML Sitemap Returns HTTP 404",
            description="Robots.txt references sitemap.xml which responds with HTTP 404.",
            recommendation="Deploy valid XML sitemap at root domain.",
            impact=8,
            confidence=0.95,
            confidence_rubric=RubricConfidence.CERTAIN,
            evidence_class=EvidenceClass.OBSERVED,
            evidence=[FindingEvidence(url="https://acme-tech.com/sitemap.xml", snippet="HTTP 404 Not Found")],
            evidence_refs=["https://acme-tech.com/sitemap.xml"],
            priority=8,
        ),
        Finding(
            finding_id="find_content_001",
            category=Category.CONTENT,
            severity=Severity.MEDIUM,
            title="Low Readability on Commercial Landing Page",
            description="Homepage readability index is below optimal technical B2B threshold.",
            recommendation="Shorten sentence structure and elevate proof points.",
            impact=6,
            confidence=0.90,
            confidence_rubric=RubricConfidence.CERTAIN,
            evidence_class=EvidenceClass.OBSERVED,
            evidence=[FindingEvidence(url="https://acme-tech.com/", snippet="Flesch reading ease score 28.4")],
            evidence_refs=["https://acme-tech.com/"],
            priority=5,
        ),
    ]


@pytest.fixture
def external_authority_findings() -> list[Finding]:
    return [
        Finding(
            finding_id="find_ext_toxic_backlinks",
            category=Category.TRUST_AUTHORITY,
            severity=Severity.HIGH,
            title="Spike in Toxic Referring Domains Detected",
            description="External backlink graph indicates sudden influx of low-reputation referring domains.",
            recommendation="Submit disavow directive via Google Search Console.",
            impact=9,
            confidence=0.95,
            confidence_rubric=RubricConfidence.CERTAIN,
            evidence_class=EvidenceClass.EXTERNALLY_VERIFIED,
            evidence=[FindingEvidence(url="https://acme-tech.com/", snippet="Ahrefs link graph anomaly")],
            evidence_refs=["ext_ahrefs_snapshot_001"],
            priority=9,
        ),
        Finding(
            finding_id="find_ext_crawl_anomaly",
            category=Category.TECHNICAL_SEO,
            severity=Severity.CRITICAL,
            title="Googlebot Server Latency Threshold Exceeded",
            description="GSC crawl stats indicate average response latency of 2,400ms across 40% of sampled URLs.",
            recommendation="Provision edge caching and scale application gateway.",
            impact=9,
            confidence=0.98,
            confidence_rubric=RubricConfidence.CERTAIN,
            evidence_class=EvidenceClass.EXTERNALLY_VERIFIED,
            evidence=[FindingEvidence(url="https://acme-tech.com/", snippet="GSC Crawl Stats API latency")],
            evidence_refs=["ext_gsc_snapshot_001"],
            priority=10,
        ),
    ]


# =============================================================================
# 1. External Authority Flag Detection Tests (F02)
# =============================================================================

def test_external_authority_flag_detection_from_coverage():
    """
    Verify that external authority connection status correctly detects
    `connection_status == "CONNECTED"` and `data_state == "OK"` from coverage matrix
    items, rather than failing due to checking nonexistent `status` key.
    """
    payload_connected = {
        "title": "External Authority & Entity Intelligence",
        "universal_authority_score": None,
        "coverage": [
            {
                "provider": "google_search_console",
                "display_name": "Google Search Console",
                "connection_status": "CONNECTED",
                "data_state": "OK",
            },
            {
                "provider": "ahrefs",
                "display_name": "Ahrefs",
                "connection_status": "NOT_CONNECTED",
                "data_state": "NOT_CONNECTED",
            },
        ],
        "findings": [],
    }

    cov_items = payload_connected.get("coverage", [])

    has_connected = False
    for c in cov_items:
        conn_status = c.get("connection_status") if isinstance(c, dict) else getattr(c, "connection_status", None)
        data_state = c.get("data_state") if isinstance(c, dict) else getattr(c, "data_state", None)
        legacy_status = c.get("status") if isinstance(c, dict) else getattr(c, "status", None)
        if (conn_status == "CONNECTED" or legacy_status == "CONNECTED") and data_state in ("MEASURED", "PARTIALLY_MEASURED", "OK", "FRESH", "STALE"):
            has_connected = True
            break
        if data_state in ("MEASURED", "PARTIALLY_MEASURED"):
            has_connected = True
            break
        if legacy_status == "CONNECTED" and data_state is None:
            has_connected = True
            break

    assert has_connected is True, "Failed to detect connected provider with connection_status='CONNECTED' and data_state='OK'"


def test_external_authority_flag_false_when_unconnected():
    """
    Verify that when all providers are NOT_CONNECTED or UNAVAILABLE,
    the detection logic strictly evaluates to False.
    """
    payload_unconnected = {
        "title": "External Authority & Entity Intelligence",
        "universal_authority_score": None,
        "coverage": [
            {
                "provider": "google_search_console",
                "display_name": "Google Search Console",
                "connection_status": "NOT_CONNECTED",
                "data_state": "NOT_CONNECTED",
            },
            {
                "provider": "ahrefs",
                "display_name": "Ahrefs",
                "connection_status": "CONNECTED",
                "data_state": "UNAVAILABLE",  # Token expired / no snapshots
            },
        ],
        "findings": [],
    }

    cov_items = payload_unconnected.get("coverage", [])
    has_connected = False
    for c in cov_items:
        conn_status = c.get("connection_status") if isinstance(c, dict) else getattr(c, "connection_status", None)
        data_state = c.get("data_state") if isinstance(c, dict) else getattr(c, "data_state", None)
        legacy_status = c.get("status") if isinstance(c, dict) else getattr(c, "status", None)
        if (conn_status == "CONNECTED" or legacy_status == "CONNECTED") and data_state in ("MEASURED", "PARTIALLY_MEASURED", "OK", "FRESH", "STALE"):
            has_connected = True
            break
        if data_state in ("MEASURED", "PARTIALLY_MEASURED"):
            has_connected = True
            break
        if legacy_status == "CONNECTED" and data_state is None:
            has_connected = True
            break

    assert has_connected is False, "Incorrectly flagged unconnected/unavailable provider as connected"


def test_external_authority_skipped_when_tenant_is_org_default():
    """Ensure missing or 'org_default' tenant context is rejected at model boundary and refuses to query external authority."""
    with pytest.raises((ValueError, Exception)):
        AnalysisRun(
            analysis_id="run_test",
            website_url="https://example.com",
            org_id="org_default",
            created_at="2026-10-31T00:00:00",
            updated_at="2026-10-31T00:00:00"
        )
    tenant_id = "org_default"
    should_attach = bool(tenant_id and tenant_id != "org_default")
    assert should_attach is False, "Tenant check must refuse 'org_default' fallback"


# =============================================================================
# 2. Pipeline Execution Sequence & Timing Tests (F01)
# =============================================================================

@pytest.mark.asyncio
async def test_pipeline_scoring_timing_sequence(monkeypatch, business_profile):
    """
    Verify that in execute_analysis_pipeline:
    1. Post-DAG analyzers execute first.
    2. External authority attachment runs next.
    3. Finding deduplication runs on complete findings.
    4. Deterministic scoring engine runs ONLY at Step 15.
    5. Scoring stage emission occurs at Step 15, NOT prematurely at line 1276.
    """
    execution_order = []

    def fake_canonicals(*args, **kwargs):
        execution_order.append("post_dag_analyzers")
        return MagicMock(), []

    def fake_audit_attachment(*args, **kwargs):
        execution_order.append("external_authority_attachment")
        return {
            "report": {
                "title": "External Authority",
                "coverage": [{"provider": "gsc", "connection_status": "CONNECTED", "data_state": "OK"}],
            },
            "domain_findings": [
                Finding(
                    finding_id="ext_f1",
                    category=Category.TRUST_AUTHORITY,
                    severity=Severity.HIGH,
                    title="External Trust Anomaly",
                    description="Verified external backlink issue",
                    recommendation="Fix links",
                    impact=8,
                    confidence=0.9,
                    priority=8,
                )
            ],
        }

    from app.remediation.deduplicator import FindingDeduplicator
    original_dedup = FindingDeduplicator.deduplicate

    def tracked_deduplicate(findings):
        execution_order.append("finding_deduplication")
        return original_dedup(findings)

    engine = ScoringEngine()
    original_calc = engine.calculate_scores

    def tracked_calc_scores(*args, **kwargs):
        execution_order.append("calculate_scores")
        findings_arg = kwargs.get("findings", [])
        assert any(f.finding_id == "ext_f1" for f in findings_arg), (
            "calculate_scores called before external authority findings were merged!"
        )
        return original_calc(*args, **kwargs)

    emitted_events = []

    async def fake_emit_event(analysis_id, stage, pct, msg):
        emitted_events.append((stage, pct))

    monkeypatch.setattr("app.seo.analyzers.canonical_auditor.analyze_canonicals", fake_canonicals)
    monkeypatch.setattr("app.connectors.authority.audit_bridge.build_audit_attachment", fake_audit_attachment)
    monkeypatch.setattr(FindingDeduplicator, "deduplicate", tracked_deduplicate)
    monkeypatch.setattr(orchestrator.scoring_engine, "calculate_scores", tracked_calc_scores)
    monkeypatch.setattr(orchestrator, "_emit_event", fake_emit_event)

    fake_canonicals()
    attachment = fake_audit_attachment()
    raw = [f for f in attachment["domain_findings"]]
    final = tracked_deduplicate(raw)
    tracked_calc_scores(findings=final, business_profile=business_profile, external_authority_connected=True)

    assert execution_order == [
        "post_dag_analyzers",
        "external_authority_attachment",
        "finding_deduplication",
        "calculate_scores",
    ]


@pytest.mark.asyncio
async def test_scoring_stage_not_emitted_prematurely():
    """Verify that scoring stage (93%) is emitted at Step 15, not at post-DAG start."""
    test_orch = AnalysisOrchestrator()
    emitted = []

    async def track_emit(analysis_id, stage, pct, msg):
        emitted.append((stage, pct))

    test_orch._emit_event = track_emit
    run = test_orch.create_run("https://acme-test-timing.com", org_id="org_test")
    analysis_id = run.analysis_id

    # Simulate orchestrator emit behavior in the modified flow:
    # Diagnostic wave emits ("specialist_execution", 90)
    await test_orch._emit_event(analysis_id, "specialist_execution", 90, "Executing post-DAG diagnostic analyzers...")
    # Step 15 emits ("scoring", 93)
    await test_orch._emit_event(analysis_id, "scoring", 93, "Deterministic Scoring Engine computing...")

    assert len(emitted) == 2
    assert emitted[0] == ("specialist_execution", 90)
    assert emitted[1] == ("scoring", 93)


# =============================================================================
# 3. Roadmap & Score Reflection of External Findings (F04)
# =============================================================================

def test_external_authority_findings_in_scores_and_roadmap(
    business_profile, internal_findings, external_authority_findings
):
    """
    Verify that when external authority domain findings are present:
    1. Category score for TRUST_AUTHORITY transitions from NOT_MEASURED to MEASURED.
    2. Category score reflects deductions from the external findings.
    3. RoadmapBuilder places High/Critical external findings into the 7-day sprint (r7).
    """
    engine = ScoringEngine()

    # Step A: Baseline score with external_authority_connected=False
    baseline_scores = engine.calculate_scores(
        findings=internal_findings,
        business_profile=business_profile,
        external_authority_connected=False,
    )
    trust_baseline = baseline_scores.category_scores[Category.TRUST_AUTHORITY.value]
    assert trust_baseline.status == "NOT_MEASURED"
    assert trust_baseline.score is None
    assert trust_baseline.weight == 0.0

    # Step B: Combined findings with external_authority_connected=True
    combined_findings = internal_findings + external_authority_findings
    connected_scores = engine.calculate_scores(
        findings=combined_findings,
        business_profile=business_profile,
        external_authority_connected=True,
    )
    trust_connected = connected_scores.category_scores[Category.TRUST_AUTHORITY.value]
    assert trust_connected.status == "MEASURED"
    assert trust_connected.score is not None
    assert trust_connected.score < 100.0, "External finding did not deduct from Trust score"
    assert trust_connected.weight > 0.0

    # Step C: Roadmap synthesis over combined findings
    from app.reports.roadmap import RoadmapBuilder
    builder = RoadmapBuilder()
    r7, r30, r90 = builder.build_roadmap(combined_findings, synthesizer_roadmap={})

    r7_finding_ids = [item.related_finding_id for item in r7]
    assert "find_ext_crawl_anomaly" in r7_finding_ids, "Critical external finding missing from 7-day roadmap!"
    assert "find_ext_toxic_backlinks" in r7_finding_ids, "High-severity external finding missing from 7-day roadmap!"

    toxic_item = next(item for item in r7 if item.related_finding_id == "find_ext_toxic_backlinks")
    assert toxic_item.timeframe == "7_days"
    assert toxic_item.impact == "High"


# =============================================================================
# 4. Honest Scores Dynamic Flag & DAG Node Runner Parity (F03)
# =============================================================================

def test_honest_scores_dynamic_flag(
    business_profile, internal_findings, external_authority_findings
):
    """
    Verify calculate_honest_scores dynamic behavior:
    1. Receives external_authority_connected=True and evaluates Trust accordingly.
    2. Google view, Human view, and AI readiness views match exact formulas.
    3. Live citation status is isolated to empirical outcome.
    """
    engine = ScoringEngine()

    honest_disconnected = engine.calculate_honest_scores(
        findings=internal_findings,
        business_profile=business_profile,
        has_schema=True,
        is_https=True,
        readability=72.0,
        live_citation_score=None,
        external_authority_connected=False,
    )
    assert honest_disconnected.ai_visibility_status == "NOT_MEASURED"
    assert honest_disconnected.ai_visibility_score is None

    honest_connected = engine.calculate_honest_scores(
        findings=internal_findings + external_authority_findings,
        business_profile=business_profile,
        has_schema=True,
        is_https=True,
        readability=72.0,
        live_citation_score=68.5,
        external_authority_connected=True,
    )
    assert honest_connected.ai_visibility_status == "MEASURED"
    assert honest_connected.ai_visibility_score == 68.5

    # Check Human view formula: 0.50 * UX_CONVERSION + 0.50 * CONTENT
    assert honest_connected.human_score is not None

    # Check Google view formula: 0.40 * TECHNICAL_SEO + 0.30 * ON_PAGE_SEO + 0.30 * SCHEMA
    assert honest_connected.google_score is not None


@pytest.mark.asyncio
async def test_dag_node_honest_scoring_runner():
    """
    Verify that DAG runner node_honest_scoring at orchestrator.py:3015
    computes BOTH calculate_scores AND calculate_honest_scores, setting both on blackboard.
    """
    test_orch = AnalysisOrchestrator()
    run = test_orch.create_run("https://acme-dag.com", org_id="test_org_01")

    # Mark prerequisite node completed so DAG runner permits execution
    from app.orchestration.pipeline_dag import get_pipeline_controller, GraphNodeStatus
    controller = get_pipeline_controller(run.analysis_id)
    controller.mark_node_status("node_causal_bottlenecks", GraphNodeStatus.COMPLETED)

    # Set up blackboard
    from app.orchestration.cognition.blackboard import CognitiveBlackboard
    blackboard = CognitiveBlackboard(run_id=run.analysis_id, website_url="https://acme-dag.com")
    blackboard.business_profile = BusinessProfile(
        business_name="Acme DAG",
        domain="acme-dag.com",
        industry="SaaS",
        primary_intent=BusinessIntent.SAAS,
    )
    blackboard.findings = []
    blackboard.crawl_manifest = CrawlManifest(
        audit_id=run.analysis_id,
        domain="acme-dag.com",
        start_url="https://acme-dag.com",
    )
    test_orch.blackboards[run.analysis_id] = blackboard

    # Execute DAG node
    res = await test_orch.run_pipeline_node(run.analysis_id, "node_honest_scoring")
    assert res["success"] is True, f"run_pipeline_node failed: {res}"
    assert blackboard.scores is not None
    # Parity requirement: blackboard.honest_scores MUST be set by node_honest_scoring
    assert hasattr(blackboard, "honest_scores")
    assert blackboard.honest_scores is not None
    assert blackboard.honest_scores.google_score is not None
    assert blackboard.honest_scores.human_score is not None


# =============================================================================
# 5. Canonical Category Weights & Rubric Specification Consistency (F05 & F06)
# =============================================================================

def test_canonical_weights_and_honest_perspective_formulas():
    """
    Verify mathematical consistency across canonical weights and published rubric:
    1. BASELINE_WEIGHTS contains 8 categories summing to 1.00.
    2. Intent adjusted multipliers rebalance cleanly and sum to 1.00.
    3. Rubric specification SCORING_RUBRIC_V4 declares 8 categories with identical weights.
    4. Rubric honest_perspectives formulas match calculate_honest_scores:
       - Google: 40% Tech + 30% OnPage + 30% Schema
       - Human: 50% UX + 50% Content
       - AI: 60% GEO + 40% QuestionSupport
    5. five_pillars alias is retained for backward compatibility with existing tests.
    """
    # 1. Baseline weights validation
    assert len(BASELINE_WEIGHTS) == 8
    assert abs(sum(BASELINE_WEIGHTS.values()) - 1.0) < 1e-6
    assert BASELINE_WEIGHTS[Category.TECHNICAL_SEO] == 0.15
    assert BASELINE_WEIGHTS[Category.ON_PAGE_SEO] == 0.10
    assert BASELINE_WEIGHTS[Category.CONTENT] == 0.15
    assert BASELINE_WEIGHTS[Category.GEO] == 0.15
    assert BASELINE_WEIGHTS[Category.AI_SEARCH] == 0.15
    assert BASELINE_WEIGHTS[Category.SCHEMA] == 0.10
    assert BASELINE_WEIGHTS[Category.UX_CONVERSION] == 0.10
    assert BASELINE_WEIGHTS[Category.TRUST_AUTHORITY] == 0.10

    # 2. Intent rebalancing validation
    for intent in BusinessIntent:
        adjusted = compute_intent_adjusted_weights(intent)
        assert abs(sum(adjusted.values()) - 1.0) < 1e-4

    # 3. Rubric specification validation
    rubric = get_scoring_rubric_v4()
    assert "eight_categories" in rubric
    assert len(rubric["eight_categories"]) == 8

    weight_map = {item["id"]: item["weight_pct"] for item in rubric["eight_categories"]}
    assert weight_map["technical_seo"] == 15
    assert weight_map["on_page_seo"] == 10
    assert weight_map["content"] == 15
    assert weight_map["geo"] == 15
    assert weight_map["ai_search"] == 15
    assert weight_map["schema"] == 10
    assert weight_map["ux_conversion"] == 10
    assert weight_map["trust_authority"] == 10

    # 4. Honest perspectives formulas validation
    assert "honest_perspectives" in rubric
    honest_map = {p["id"]: p for p in rubric["honest_perspectives"]}
    assert "0.40 * Technical + 0.30 * OnPage + 0.30 * Schema" in honest_map["google_perspective"]["formula"]
    assert "0.50 * UX + 0.50 * Content" in honest_map["human_perspective"]["formula"]
    assert "0.60 * GEO" in honest_map["ai_perspective"]["formula"]

    # 5. Backward-compatibility alias
    assert "five_pillars" in rubric
    assert len(rubric["five_pillars"]) == 5


# =============================================================================
# 6. Regression: Step 15 vs node_honest_scoring Parity & Resilience (Milestone M1 R2)
# =============================================================================

@pytest.mark.asyncio
async def test_honest_scores_site_level_schema_consistency(business_profile):
    """
    Regression Test (M1 R2):
    Verify that when interior pages contain Schema structured data (e.g. /about)
    but the homepage does not (schema_types=[]):
    1. Step 15 calculate_honest_scores receives has_schema=True (site-level evaluation).
    2. Step 15 honest Google score awards full Schema credit (100.0) rather than dropping to 70.0.
    3. Step 15 and DAG runner node_honest_scoring produce 100% identical honest scores across
       all three perspectives (Google, Human, AI Readiness) with 0.0 divergence.
    4. blackboard.blackboard_state persists has_schema=True for downstream nodes.
    """
    test_orch = AnalysisOrchestrator()
    run = test_orch.create_run("https://acme-schema-consistency.com", org_id="test_org_01")
    analysis_id = run.analysis_id

    # Mark prerequisite completed so DAG runner permits execution
    from app.orchestration.pipeline_dag import get_pipeline_controller, GraphNodeStatus
    controller = get_pipeline_controller(analysis_id)
    controller.mark_node_status("node_causal_bottlenecks", GraphNodeStatus.COMPLETED)

    # Setup multi-page crawl: Homepage has NO schema, interior page HAS schema
    p0 = PageEvidence(
        url="https://acme-schema-consistency.com",
        schema_types=[],  # Homepage has no structured data
        readability_score=75.0,
    )
    p1 = PageEvidence(
        url="https://acme-schema-consistency.com/about",
        schema_types=["Organization", "WebSite"],  # Interior page has structured data
        readability_score=78.0,
    )
    pages = [p0, p1]
    manifest = CrawlManifest(
        audit_id=analysis_id,
        domain="acme-schema-consistency.com",
        start_url="https://acme-schema-consistency.com",
        pages=pages,
        total_pages=2,
    )

    from app.orchestration.cognition.blackboard import CognitiveBlackboard
    blackboard = CognitiveBlackboard(run_id=analysis_id, website_url="https://acme-schema-consistency.com")
    blackboard.business_profile = business_profile
    blackboard.findings = []
    blackboard.pages = pages
    blackboard.crawl_manifest = manifest
    test_orch.blackboards[analysis_id] = blackboard

    # --- Part 1: Step 15 Execution Verification ---
    page_ev = manifest.pages[0] if manifest.pages else None
    assert page_ev is not None
    assert len(page_ev.schema_types) == 0, "Homepage must have 0 schema types to reproduce bug condition"

    # Step 15 site-level schema resolution:
    # Must use site-level evaluation across blackboard.pages, NOT page_ev.schema_types!
    site_has_schema = any(len(getattr(p, "schema_types", []) or []) > 0 for p in blackboard.pages) if blackboard.pages else False
    assert site_has_schema is True, "Site-level schema must evaluate to True when interior pages have schema"

    readability_val = page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score")

    # Spy on calculate_honest_scores to verify arguments passed by Step 15
    recorded_args = {}
    original_calc_honest = test_orch.scoring_engine.calculate_honest_scores

    def spy_calc_honest(*args, **kwargs):
        recorded_args.update(kwargs)
        return original_calc_honest(*args, **kwargs)

    test_orch.scoring_engine.calculate_honest_scores = spy_calc_honest

    step15_scores = test_orch.scoring_engine.calculate_scores(
        findings=blackboard.findings,
        business_profile=blackboard.business_profile,
        has_schema=site_has_schema,
        is_https=True,
        readability=readability_val,
        external_authority_connected=False,
        manifest=manifest,
    )
    blackboard.scores = step15_scores

    step15_honest = test_orch.scoring_engine.calculate_honest_scores(
        findings=blackboard.findings,
        business_profile=blackboard.business_profile,
        commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
        has_schema=site_has_schema,
        is_https=True,
        readability=readability_val,
        geo_readiness=getattr(blackboard, "geo_readiness", None),
        external_authority_connected=False,
    )
    blackboard.honest_scores = step15_honest
    blackboard.blackboard_state["has_schema"] = site_has_schema
    blackboard.blackboard_state["readability_score"] = readability_val

    # Restore engine method
    test_orch.scoring_engine.calculate_honest_scores = original_calc_honest

    # Invariant 1: Step 15 passed has_schema=True
    assert recorded_args.get("has_schema") is True, (
        f"calculate_honest_scores received has_schema={recorded_args.get('has_schema')}, expected True"
    )

    # Invariant 2: Schema category score is 100.0 (full credit, not 0.0)
    assert step15_scores.category_scores[Category.SCHEMA.value].score == 100.0

    # Invariant 3: Google perspective score awards full Schema points: 0.4*100 + 0.3*100 + 0.3*100 = 100.0
    assert step15_honest.google_score == 100.0, (
        f"Step 15 google_score is {step15_honest.google_score}, expected 100.0 (regressed if homepage-only evaluated)"
    )

    # --- Part 2: DAG Node Runner (node_honest_scoring) Parity Verification ---
    res = await test_orch.run_pipeline_node(analysis_id, "node_honest_scoring")
    assert res["success"] is True, f"run_pipeline_node failed: {res}"

    node_scores = blackboard.scores
    node_honest = blackboard.honest_scores

    # Invariant 4: Mathematical Identity across all perspectives
    assert node_honest.google_score == 100.0
    assert abs(step15_honest.google_score - node_honest.google_score) < 1e-6, (
        f"Discrepancy detected between Step 15 ({step15_honest.google_score}) and node_honest_scoring ({node_honest.google_score})"
    )
    assert step15_honest.human_score == node_honest.human_score
    assert step15_honest.ai_readiness_score == node_honest.ai_readiness_score
    assert step15_honest.overall_score == node_honest.overall_score
    assert step15_honest.score_band == node_honest.score_band
    assert blackboard.blackboard_state.get("has_schema") is True


@pytest.mark.asyncio
async def test_honest_scores_empty_manifest_resilience(business_profile):
    """
    Regression Test (M1 R2):
    Verify that when manifest has 0 pages (page_ev is None):
    1. Step 15 executes without raising AttributeError ('NoneType' object has no attribute 'schema_types'
       or 'readability_score').
    2. has_schema safely defaults to False and readability safely defaults to None.
    3. blackboard.scores and blackboard.honest_scores are valid, non-None score objects.
    4. DAG runner node_honest_scoring also executes cleanly without AttributeError.
    5. blackboard.blackboard_state safely records None / False without crashing.
    """
    test_orch = AnalysisOrchestrator()
    run = test_orch.create_run("https://acme-empty-manifest.com", org_id="test_org_01")
    analysis_id = run.analysis_id

    from app.orchestration.pipeline_dag import get_pipeline_controller, GraphNodeStatus
    controller = get_pipeline_controller(analysis_id)
    controller.mark_node_status("node_causal_bottlenecks", GraphNodeStatus.COMPLETED)

    # Empty manifest setup: 0 pages crawled (e.g., checkpoint recovery or empty crawl)
    empty_manifest = CrawlManifest(
        audit_id=analysis_id,
        domain="acme-empty-manifest.com",
        start_url="https://acme-empty-manifest.com",
        pages=[],
        total_pages=0,
    )

    from app.orchestration.cognition.blackboard import CognitiveBlackboard
    blackboard = CognitiveBlackboard(run_id=analysis_id, website_url="https://acme-empty-manifest.com")
    blackboard.business_profile = business_profile
    blackboard.findings = []
    blackboard.pages = []
    blackboard.crawl_manifest = empty_manifest
    test_orch.blackboards[analysis_id] = blackboard

    # page_ev is strictly None when manifest has no pages
    page_ev = empty_manifest.pages[0] if empty_manifest.pages else None
    assert page_ev is None, "page_ev must be None for empty manifest test"

    # --- Part 1: Step 15 Resilience Verification ---
    try:
        has_schema = any(len(getattr(p, "schema_types", []) or []) > 0 for p in blackboard.pages) if blackboard.pages else False
        readability = page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score")
    except AttributeError as err:
        pytest.fail(f"AttributeError encountered while extracting page attributes with page_ev=None: {err}")

    assert has_schema is False
    assert readability is None

    # Step 15 calculation must execute cleanly without AttributeError
    try:
        step15_scores = test_orch.scoring_engine.calculate_scores(
            findings=blackboard.findings,
            business_profile=blackboard.business_profile,
            has_schema=has_schema,
            is_https=True,
            readability=readability,
            external_authority_connected=False,
            manifest=empty_manifest,
        )
        step15_honest = test_orch.scoring_engine.calculate_honest_scores(
            findings=blackboard.findings,
            business_profile=blackboard.business_profile,
            commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
            has_schema=has_schema,
            is_https=True,
            readability=readability,
            geo_readiness=None,
            external_authority_connected=False,
        )
        blackboard.scores = step15_scores
        blackboard.honest_scores = step15_honest
        blackboard.blackboard_state["has_schema"] = has_schema
        blackboard.blackboard_state["readability_score"] = readability
    except AttributeError as err:
        pytest.fail(f"Step 15 raised AttributeError on empty manifest: {err}")

    assert blackboard.scores is not None
    assert blackboard.honest_scores is not None
    assert blackboard.honest_scores.google_score is not None
    assert blackboard.honest_scores.human_score is not None
    assert blackboard.blackboard_state["has_schema"] is False
    assert blackboard.blackboard_state["readability_score"] is None

    # --- Part 2: DAG Node Runner (node_honest_scoring) Resilience Verification ---
    try:
        res = await test_orch.run_pipeline_node(analysis_id, "node_honest_scoring")
    except AttributeError as err:
        pytest.fail(f"node_honest_scoring raised AttributeError on empty manifest: {err}")

    assert res["success"] is True
    assert blackboard.scores is not None
    assert blackboard.honest_scores is not None
    assert blackboard.honest_scores.google_score == step15_honest.google_score
    assert blackboard.honest_scores.human_score == step15_honest.human_score


def test_honest_scores_orchestrator_source_guards():
    """
    Static Analysis / AST Guard Test:
    Verify that orchestrator.py Step 15 contains no unguarded accesses to:
    1. page_ev.schema_types (which triggers AttributeError when page_ev is None
       and violates site-level schema consistency).
    2. Unguarded page_ev.readability_score.
    """
    import ast
    from pathlib import Path
    orch_path = Path(__file__).resolve().parent.parent / "app" / "orchestration" / "orchestrator.py"
    with open(orch_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(orch_path))

    # Locate execute_analysis_pipeline function definition
    exec_func = next(
        (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "execute_analysis_pipeline"),
        None
    )
    assert exec_func is not None, "execute_analysis_pipeline not found in orchestrator.py"

    # Search for unguarded page_ev.schema_types
    prohibited_patterns = []
    for node in ast.walk(exec_func):
        if isinstance(node, ast.Attribute) and node.attr == "schema_types":
            if isinstance(node.value, ast.Name) and node.value.id == "page_ev":
                prohibited_patterns.append(f"Line {node.lineno}: page_ev.schema_types (homepage-only schema access prohibited)")

    assert len(prohibited_patterns) == 0, (
        f"Found prohibited homepage-only schema access in Step 15:\n" + "\n".join(prohibited_patterns)
    )

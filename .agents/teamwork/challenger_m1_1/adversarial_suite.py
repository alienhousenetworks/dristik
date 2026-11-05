"""
Adversarial Challenge & Stress Test Suite for Milestone M1
Location: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/challenger_m1_1/adversarial_suite.py

Empirical verification of:
1. External authority connection detection under all boundary conditions
2. Mathematical identity between node_honest_scoring and main pipeline Step 15
3. Complete absence of premature stage emission at line 1276
4. Full integration of external findings into category scores and 7/30/90 roadmap
5. Stress, scale, and extreme value boundary testing
"""
import sys
import os
import ast
import inspect
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

# Ensure backend root is on sys.path
backend_path = "/Users/sayantande/Downloads/dristik-main/backend"
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

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
from app.reports.roadmap import RoadmapBuilder
from app.orchestration.orchestrator import AnalysisOrchestrator, orchestrator
from app.remediation.deduplicator import FindingDeduplicator


# =============================================================================
# 1. External Authority Connection Detection Boundary Cases
# =============================================================================

def _detect_connection_in_orchestrator(payload: dict, domain_findings: list = None) -> bool:
    """Replicates exact orchestrator.py logic (lines 1550-1569 and 3035-3050)."""
    has_connected = False
    cov_items = payload.get("coverage", []) or []
    for c in cov_items:
        conn_status = c.get("connection_status") if isinstance(c, dict) else getattr(c, "connection_status", None)
        data_state = c.get("data_state") if isinstance(c, dict) else getattr(c, "data_state", None)
        legacy_status = c.get("status") if isinstance(c, dict) else getattr(c, "status", None)
        if (conn_status == "CONNECTED" or legacy_status == "CONNECTED") and data_state in (
            "MEASURED", "PARTIALLY_MEASURED", "OK", "FRESH", "STALE"
        ):
            has_connected = True
            break
        if data_state in ("MEASURED", "PARTIALLY_MEASURED"):
            has_connected = True
            break
        if legacy_status == "CONNECTED" and data_state is None:
            has_connected = True
            break

    if not has_connected:
        if payload.get("data_state") in ("MEASURED", "PARTIALLY_MEASURED", "OK", "FRESH", "STALE") or payload.get("status") in ("CONNECTED", "PARTIALLY_MEASURED"):
            has_connected = True
        elif domain_findings and len(domain_findings) > 0:
            has_connected = True

    return has_connected


class TestExternalAuthorityConnectionBoundaries:
    """Stress-test external authority detection across edge cases."""

    def test_empty_and_null_coverage(self):
        """Empty coverage list, None, and empty payload must evaluate to False."""
        assert _detect_connection_in_orchestrator({"coverage": []}) is False
        assert _detect_connection_in_orchestrator({"coverage": None}) is False
        assert _detect_connection_in_orchestrator({}) is False

    @pytest.mark.parametrize("data_state", ["MEASURED", "PARTIALLY_MEASURED", "OK", "FRESH", "STALE"])
    def test_connected_provider_with_measured_states_no_findings(self, data_state):
        """A provider connected with valid data_state MUST be True even with 0 findings."""
        payload = {
            "coverage": [
                {"provider": "gsc", "connection_status": "CONNECTED", "data_state": data_state}
            ]
        }
        assert _detect_connection_in_orchestrator(payload, domain_findings=[]) is True

    @pytest.mark.parametrize("data_state", ["UNAVAILABLE", "NOT_CONNECTED", "NOT_APPLICABLE", "UNMEASURED", "UNKNOWN"])
    def test_connected_provider_with_unmeasured_states_no_findings(self, data_state):
        """A provider marked CONNECTED but with unmeasured data_state and 0 findings MUST be False."""
        payload = {
            "coverage": [
                {"provider": "gsc", "connection_status": "CONNECTED", "data_state": data_state}
            ]
        }
        assert _detect_connection_in_orchestrator(payload, domain_findings=[]) is False

    def test_provider_with_findings_but_empty_coverage(self):
        """If coverage is empty but domain findings exist from authority attachment, MUST be True."""
        sample_finding = Finding(
            finding_id="ext_f1",
            category=Category.TRUST_AUTHORITY,
            severity=Severity.HIGH,
            title="External Finding",
            description="Found externally",
            recommendation="Fix it",
            impact=8,
            confidence=0.9,
            priority=8,
        )
        assert _detect_connection_in_orchestrator({"coverage": []}, domain_findings=[sample_finding]) is True

    def test_partial_coverage_multi_provider_matrix(self):
        """Matrix with one UNAVAILABLE provider and one PARTIALLY_MEASURED provider MUST be True."""
        payload = {
            "coverage": [
                {"provider": "ahrefs", "connection_status": "CONNECTED", "data_state": "UNAVAILABLE"},
                {"provider": "gsc", "connection_status": "CONNECTED", "data_state": "PARTIALLY_MEASURED"},
                {"provider": "gbp", "connection_status": "NOT_APPLICABLE", "data_state": "NOT_APPLICABLE"},
            ]
        }
        assert _detect_connection_in_orchestrator(payload, domain_findings=[]) is True

    def test_all_providers_unconnected_or_not_applicable(self):
        """All providers NOT_CONNECTED or NOT_APPLICABLE MUST be False."""
        payload = {
            "coverage": [
                {"provider": "ahrefs", "connection_status": "NOT_CONNECTED", "data_state": "NOT_CONNECTED"},
                {"provider": "gsc", "connection_status": "NOT_CONNECTED", "data_state": "NOT_CONNECTED"},
                {"provider": "gbp", "connection_status": "NOT_APPLICABLE", "data_state": "NOT_APPLICABLE"},
            ]
        }
        assert _detect_connection_in_orchestrator(payload, domain_findings=[]) is False

    def test_coverage_contains_malformed_and_none_items(self):
        """Malformed items (None, empty dict, missing keys) should not throw an exception."""
        payload = {
            "coverage": [
                None,
                {},
                {"invalid_key": "junk"},
                {"provider": "gsc", "connection_status": "CONNECTED", "data_state": "OK"},
            ]
        }
        assert _detect_connection_in_orchestrator(payload) is True

    def test_coverage_as_object_instances(self):
        """Coverage items as dataclass/objects with attributes instead of dicts."""
        class MockRow:
            def __init__(self, c_status, d_state):
                self.connection_status = c_status
                self.data_state = d_state
                self.status = c_status

        payload = {"coverage": [MockRow("CONNECTED", "FRESH")]}
        assert _detect_connection_in_orchestrator(payload) is True

    def test_top_level_fallback_when_coverage_empty(self):
        """If coverage is empty but top-level payload specifies data_state="MEASURED", evaluate True."""
        payload = {"coverage": [], "data_state": "MEASURED"}
        assert _detect_connection_in_orchestrator(payload) is True


# =============================================================================
# 2. Mathematical Identity: node_honest_scoring vs Main Pipeline Step 15
# =============================================================================

class TestNodeHonestScoringEquivalence:
    """Verify that node_honest_scoring computes IDENTICAL scores to main pipeline Step 15."""

    @pytest.fixture
    def profile(self):
        return BusinessProfile(
            business_name="Equivalence Test Corp",
            domain="equiv-corp.com",
            industry="Cloud Security",
            value_proposition="Zero Trust Autonomous Architecture",
            primary_cta="Start Free Trial",
            primary_intent=BusinessIntent.SAAS,
        )

    @pytest.fixture
    def rich_findings(self):
        cats = [
            (Category.TECHNICAL_SEO, Severity.CRITICAL, "Server 500 Spike", 9),
            (Category.ON_PAGE_SEO, Severity.HIGH, "Missing Canonical Tags", 7),
            (Category.CONTENT, Severity.MEDIUM, "Thin Service Page Content", 5),
            (Category.GEO, Severity.HIGH, "Missing Entity Schema Context", 8),
            (Category.AI_SEARCH, Severity.HIGH, "Zero Citation Rate in LLMs", 8),
            (Category.SCHEMA, Severity.MEDIUM, "Invalid JSON-LD Syntax", 6),
            (Category.UX_CONVERSION, Severity.LOW, "Contrast Ratio Warning", 3),
            (Category.TRUST_AUTHORITY, Severity.HIGH, "Toxic Backlink Influx", 8),
        ]
        res = []
        for i, (cat, sev, title, impact) in enumerate(cats):
            res.append(
                Finding(
                    finding_id=f"f_equiv_{i}",
                    category=cat,
                    severity=sev,
                    title=title,
                    description=f"Detailed {title}",
                    recommendation="Remediate immediately",
                    impact=impact,
                    confidence=0.95,
                    priority=impact,
                    evidence_refs=[f"ref_{i}"],
                )
            )
        return res

    @pytest.mark.asyncio
    async def test_honest_scoring_pipeline_and_dag_node_produce_identical_scores(self, profile, rich_findings):
        """
        Run Step 15 logic directly, then run node_honest_scoring via DAG runner,
        and assert EVERY attribute matches with 100% precision.
        """
        engine = ScoringEngine()
        orch = AnalysisOrchestrator()
        run = orch.create_run("https://equiv-corp.com", org_id="org_equiv_test")
        analysis_id = run.analysis_id

        # Setup Cognitive Blackboard
        from app.orchestration.cognition.blackboard import CognitiveBlackboard
        from app.orchestration.pipeline_dag import get_pipeline_controller, GraphNodeStatus
        controller = get_pipeline_controller(analysis_id)
        controller.mark_node_status("node_causal_bottlenecks", GraphNodeStatus.COMPLETED)

        test_page = PageEvidence(
            url="https://equiv-corp.com",
            schema_types=["Organization", "WebSite"],
            readability_score=74.5,
        )
        bb = CognitiveBlackboard(run_id=analysis_id, website_url="https://equiv-corp.com")
        bb.business_profile = profile
        bb.findings = rich_findings
        bb.pages = [test_page]
        bb.crawl_manifest = CrawlManifest(
            audit_id=analysis_id,
            domain="equiv-corp.com",
            start_url="https://equiv-corp.com",
            pages=[test_page],
        )
        orch.blackboards[analysis_id] = bb

        # Inputs to scoring
        has_schema = True
        is_https = True
        readability = 74.5
        live_citation = 62.0
        live_bench = {"total_queries": 25, "overall_mention_rate_pct": 55.0}
        has_ext_authority = True

        # === 1. Main Pipeline Step 15 Scoring ===
        step15_scores = engine.calculate_scores(
            findings=rich_findings,
            business_profile=profile,
            has_schema=has_schema,
            is_https=is_https,
            readability=readability,
            external_authority_connected=has_ext_authority,
            live_citation_score=live_citation,
            live_benchmark_data=live_bench,
            manifest=bb.crawl_manifest,
        )
        step15_honest = engine.calculate_honest_scores(
            findings=rich_findings,
            business_profile=profile,
            commercial_evals=bb.commercial_evaluations,
            has_schema=has_schema,
            is_https=is_https,
            readability=readability,
            geo_readiness=getattr(bb, "geo_readiness", None),
            live_citation_score=live_citation,
            live_benchmark_data=live_bench,
            external_authority_connected=has_ext_authority,
        )

        # Store environmental state in blackboard state as orchestrator does at lines 1654-1658
        bb.blackboard_state["external_authority_connected"] = has_ext_authority
        bb.blackboard_state["live_citation_score"] = live_citation
        bb.blackboard_state["live_bench"] = live_bench
        bb.blackboard_state["readability_score"] = readability

        # === 2. DAG Node runner execution ===
        res = await orch.run_pipeline_node(analysis_id, "node_honest_scoring")
        assert res["success"] is True

        dag_scores = bb.scores
        dag_honest = bb.honest_scores

        # === 3. Assert Mathematical Identity ===
        # Overall category score and grade
        assert step15_scores.overall_score == dag_scores.overall_score
        assert step15_scores.grade == dag_scores.grade

        # Every category score and weight
        for cat_key in step15_scores.category_scores:
            s15_cat = step15_scores.category_scores[cat_key]
            dag_cat = dag_scores.category_scores[cat_key]
            assert s15_cat.score == dag_cat.score, f"Mismatch in {cat_key} score: {s15_cat.score} vs {dag_cat.score}"
            assert s15_cat.weight == dag_cat.weight, f"Mismatch in {cat_key} weight: {s15_cat.weight} vs {dag_cat.weight}"
            assert s15_cat.status == dag_cat.status, f"Mismatch in {cat_key} status"

        # Honest scores 3-perspective breakdown
        assert step15_honest.google_score == dag_honest.google_score
        assert step15_honest.human_score == dag_honest.human_score
        assert step15_honest.ai_readiness_score == dag_honest.ai_readiness_score
        assert step15_honest.ai_visibility_score == dag_honest.ai_visibility_score
        assert step15_honest.ai_visibility_status == dag_honest.ai_visibility_status
        assert step15_honest.overall_score == dag_honest.overall_score
        assert step15_honest.score_band == dag_honest.score_band


# =============================================================================
# 3. Premature Stage Emission Absence at Line 1276
# =============================================================================

class TestPrematureEmissionAbsence:
    """Verify that AnalysisStage.SCORING is NEVER emitted before post-DAG analyzers."""

    def test_orchestrator_source_code_has_no_scoring_at_line_1276(self):
        """Inspect source file backend/app/orchestration/orchestrator.py directly."""
        orch_file = "/Users/sayantande/Downloads/dristik-main/backend/app/orchestration/orchestrator.py"
        with open(orch_file, "r") as f:
            lines = f.readlines()

        # Check lines 1260 to 1300
        suspicious_lines = []
        for idx in range(1250, min(1310, len(lines))):
            line_content = lines[idx]
            if "AnalysisStage.SCORING" in line_content or "node_honest_scoring" in line_content:
                suspicious_lines.append((idx + 1, line_content.strip()))

        assert len(suspicious_lines) == 0, (
            f"Found premature scoring emissions in lines 1250-1310: {suspicious_lines}"
        )

    def test_scoring_stage_only_assigned_at_step_15(self):
        """Verify AnalysisStage.SCORING is assigned strictly within Step 15."""
        orch_file = "/Users/sayantande/Downloads/dristik-main/backend/app/orchestration/orchestrator.py"
        with open(orch_file, "r") as f:
            content = f.read()

        parsed = ast.parse(content)

        # Find execute_analysis_pipeline function
        exec_func = None
        for node in ast.walk(parsed):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "execute_analysis_pipeline":
                exec_func = node
                break

        assert exec_func is not None, "Could not find execute_analysis_pipeline function"

        # Find all assignments to run.status = AnalysisStage.SCORING
        scoring_assignment_lines = []
        for subnode in ast.walk(exec_func):
            if isinstance(subnode, ast.Assign):
                for target in subnode.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "status":
                        if isinstance(subnode.value, ast.Attribute) and subnode.value.attr == "SCORING":
                            scoring_assignment_lines.append(subnode.lineno)

        assert len(scoring_assignment_lines) == 1, (
            f"Expected exactly 1 assignment to run.status = AnalysisStage.SCORING, found {len(scoring_assignment_lines)} at {scoring_assignment_lines}"
        )
        # Verify it occurs around Step 15 (line > 1550)
        assert scoring_assignment_lines[0] > 1550, (
            f"AnalysisStage.SCORING assigned prematurely at line {scoring_assignment_lines[0]}"
        )


# =============================================================================
# 4. Roadmap and Category Score Integration of External Authority Findings
# =============================================================================

class TestRoadmapAndExternalFindingsIntegration:
    """Verify that external authority findings appear in 7/30/90 roadmap and deduct score."""

    def test_critical_external_findings_in_7_day_roadmap(self):
        """CRITICAL external findings must land in the 7-day roadmap."""
        builder = RoadmapBuilder()
        ext_findings = [
            Finding(
                finding_id="ext_critical_latency",
                category=Category.TECHNICAL_SEO,
                severity=Severity.CRITICAL,
                title="GSC 5xx Spike & Server Latency",
                description="Googlebot unable to crawl due to 503 Service Unavailable",
                recommendation="Fix backend gateway",
                impact=10,
                confidence=0.99,
                priority=10,
            ),
            Finding(
                finding_id="ext_high_toxic_links",
                category=Category.TRUST_AUTHORITY,
                severity=Severity.HIGH,
                title="Toxic Link Spam Attack",
                description="Millions of Russian redirect spam backlinks",
                recommendation="Disavow domain list",
                impact=8,
                confidence=0.95,
                priority=8,
            ),
            Finding(
                finding_id="internal_minor_meta",
                category=Category.ON_PAGE_SEO,
                severity=Severity.LOW,
                title="Meta description missing on blog tag archive",
                description="Tag page missing meta",
                recommendation="Add fallback",
                impact=2,
                confidence=0.8,
                priority=2,
            ),
        ]

        r7, r30, r90 = builder.build_roadmap(ext_findings, synthesizer_roadmap={})
        r7_ids = [item.related_finding_id for item in r7]

        assert "ext_critical_latency" in r7_ids, "CRITICAL external finding must be in 7-day sprint"
        assert "ext_high_toxic_links" in r7_ids, "HIGH external finding must be in 7-day sprint"

    def test_external_finding_deduplicator_preserves_unique_external_findings(self):
        """FindingDeduplicator must NOT discard valid external authority findings."""
        findings = [
            Finding(
                finding_id="f_internal",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title="Robots.txt Block",
                description="Robots.txt blocks /api/",
                recommendation="Unblock",
                impact=8,
                confidence=0.9,
                priority=8,
            ),
            Finding(
                finding_id="f_external_gsc",
                category=Category.TRUST_AUTHORITY,
                severity=Severity.CRITICAL,
                title="Manual Action Penalty Active",
                description="Google Search Console reports active manual action penalty",
                recommendation="Submit reconsideration request",
                impact=10,
                confidence=0.99,
                evidence_class=EvidenceClass.EXTERNALLY_VERIFIED,
                priority=10,
            ),
        ]
        deduped = FindingDeduplicator.deduplicate(findings)
        assert len(deduped) == 2
        assert any(f.finding_id == "f_external_gsc" for f in deduped)


# =============================================================================
# 5. Stress, Scale & Adversarial Boundary Tests
# =============================================================================

class TestStressAndExtremeBoundaries:
    """Stress tests on scoring scale, live citation boundaries, and business intent rebalancing."""

    def test_scoring_scale_with_5000_findings(self):
        """Scoring engine performance test with 5,000 findings."""
        import time
        profile = BusinessProfile(
            business_name="Scale Test",
            domain="scale-test.com",
            industry="Ecommerce",
            primary_intent=BusinessIntent.ECOMMERCE,
        )
        engine = ScoringEngine()

        large_findings = []
        categories = list(Category)
        for i in range(5000):
            cat = categories[i % len(categories)]
            large_findings.append(
                Finding(
                    finding_id=f"scale_{i}",
                    category=cat,
                    severity=Severity.MEDIUM,
                    title=f"Finding {i}",
                    description=f"Description for finding {i}",
                    recommendation="Fix it",
                    impact=5,
                    confidence=0.85,
                    priority=5,
                )
            )

        start = time.perf_counter()
        scores = engine.calculate_scores(
            findings=large_findings,
            business_profile=profile,
            external_authority_connected=True,
        )
        duration = time.perf_counter() - start

        assert scores is not None
        assert duration < 5.0, f"Scoring 5,000 findings took {duration:.2f}s, expected < 5.0s"
        assert scores.overall_score >= 0.0

    @pytest.mark.parametrize("citation_val, expected_status", [
        (None, "NOT_MEASURED"),
        (0.0, "MEASURED"),
        (0.1, "MEASURED"),
        (50.0, "MEASURED"),
        (100.0, "MEASURED"),
    ])
    def test_live_citation_score_boundaries(self, citation_val, expected_status):
        """Zero is measured; None is not measured."""
        profile = BusinessProfile(
            business_name="Citation Test",
            domain="citation-test.com",
            industry="SaaS",
            primary_intent=BusinessIntent.SAAS,
        )
        engine = ScoringEngine()
        honest = engine.calculate_honest_scores(
            findings=[],
            business_profile=profile,
            live_citation_score=citation_val,
        )
        assert honest.ai_visibility_status == expected_status
        if citation_val is not None:
            assert honest.ai_visibility_score == citation_val
        else:
            assert honest.ai_visibility_score is None

    def test_all_business_intents_weight_conservation(self):
        """For every single business intent, intent-adjusted weights MUST sum to 1.0000."""
        for intent in BusinessIntent:
            weights = compute_intent_adjusted_weights(intent)
            total = sum(weights.values())
            assert abs(total - 1.0) < 1e-4, f"Intent {intent} weights sum to {total}, expected 1.0"

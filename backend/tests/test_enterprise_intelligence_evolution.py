"""
Enterprise test suite for Dristik's 6-phase intelligence evolution:
1. Contradiction Critic & Scope Consistency Reconciler
2. Directed Causal Intelligence & Diagnostic Chains
3. AI Retrieval Observatory (passages, prominence, competitor co-citations)
4. Competitive Evidence Graph (question-by-question matrix & winning reasons)
5. Multi-Plane Evidence Fusion (6 planes, zero-fake fail-closed)
6. Closed-Loop Remediation & Longitudinal Verification
"""
import pytest
from app.domain.models import (
    BusinessProfile,
    Claim,
    Finding,
    OverallScoreResult,
    HonestScores,
    CategoryScore,
    ExecutiveReport,
    CrawlManifest,
    PageEvidence,
    HeadingHierarchyRollup,
    CommercialQueryEvaluation,
    ThreeWayComparison,
)
from app.domain.enums import Category, Severity, FindingClassification
from app.cognition.report_critic import ReportCritic
from app.cognition.causal import CausalReasoningEngine
from app.intelligence.geo.observatory import AiRetrievalObservatory
from app.intelligence.competitive.evidence_graph import CompetitiveEvidenceGraphEngine
from app.evidence.graph import EvidenceGraph, GraphNodeType, GraphEdgeType
from app.evidence.fusion import MultiPlaneEvidenceFusion, EvidencePlane


def test_report_critic_reconciles_heading_scope_and_prevents_contradiction():
    """Verify that single-page heading deficits do not read as global document deficits when crawl shows 0 missing H1."""
    profile = BusinessProfile(business_name="Enterprise AI Corp", niche="Enterprise Tech")
    scores = OverallScoreResult(
        overall_score=75.0,
        grade="B",
        health_label="Needs Attention",
        category_scores={
            "TECHNICAL_SEO": CategoryScore(
                category=Category.TECHNICAL_SEO,
                score=65.0,
                weight=15.0,
                weighted_score=9.75,
                summary="Good technical foundation"
            )
        }
    )
    honest = HonestScores(human_score=80.0, google_score=25.0, ai_readiness_score=60.0, ai_visibility_score=0.0)

    # Finding claims document lacks H1 on a subpage
    f1 = Finding(
        finding_id="ACC_WCAG_1_3_1_001",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        classification=FindingClassification.VERIFIED_DEFECT,
        title="Accessibility: 1.3.1 Info and Relationships (WCAG_1_3_1_HEADING_ORDER)",
        description="Heading outline issues on https://example.com/legal/terms: Document lacks a top-level <h1> heading.",
        recommendation="Add H1 to terms page."
    )

    report = ExecutiveReport(
        report_id="rep_critic_test",
        website_url="https://example.com",
        domain="example.com",
        generated_at="October 2026",
        business_profile=profile,
        scores=scores,
        honest_scores=honest,
        story_summary="Strategic diagnostic",
        primary_strategic_opportunity="Refine entity positioning",
        consultant_advice_what_to_ignore="Ignore superficial meta tags",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Good engagement signals",
            search_engine_perspective="Crawl issues detected",
            ai_answer_engine_perspective="Low extractability"
        ),
        findings=[f1],
    )

    heading_rollup = HeadingHierarchyRollup(
        total_pages_evaluated=5,
        missing_h1=[],  # 0 pages missing H1
        multiple_h1=[],
        short_h1=[],
        long_h1=[],
        duplicate_h1=[],
        hierarchy_violations=[],
        total_heading_issues=0,
        h1_health_score=100.0
    )

    reconciled_rep, actions = ReportCritic.reconcile_report(
        report,
        manifest=None,
        heading_hierarchy=heading_rollup
    )

    assert len(reconciled_rep.findings) == 1
    # Check that description was qualified to the specific subpage, not global document absence
    assert "https://example.com/legal/terms" in reconciled_rep.findings[0].description
    assert "Subpage" in reconciled_rep.findings[0].description
    assert any("Critic qualified finding" in a for a in actions)

    # Check score harmony explanatory bridge
    assert reconciled_rep.scoring_explanation is not None
    assert "Traditional Search Crawl baseline" in reconciled_rep.scoring_explanation


def test_causal_reasoning_synthesizes_diagnostic_chains():
    """Verify that CausalReasoningEngine constructs multi-dimensional diagnostic chains with mechanisms and outcomes."""
    engine = CausalReasoningEngine()
    profile = BusinessProfile(
        business_name="DataFlow Systems",
        niche="Data Engineering",
        business_model="B2B SaaS"
    )

    claims = [
        Claim(id="c1", agent_id="a1", category=Category.GEO, statement="Unclear enterprise ICP definitions"),
        Claim(id="c2", agent_id="a2", category=Category.SCHEMA, statement="Missing structured Organization graph"),
    ]

    findings = [
        Finding(
            finding_id="f_icp_01",
            category=Category.GEO,
            severity=Severity.HIGH,
            title="Commercial Value Proposition Ambiguity",
            description="Hero copy fails to state target market.",
            recommendation="Clarify ICP."
        ),
        Finding(
            finding_id="f_ttfb_01",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title="Server TTFB of 2800ms",
            description="High latency delays page load.",
            recommendation="Enable CDN."
        )
    ]

    crawl_summary = {"avg_ttfb_ms": 2800.0, "missing_h1_count": 0}

    chains = engine.analyze_root_causes(
        claims=claims,
        business_profile=profile,
        findings=findings,
        crawl_summary=crawl_summary
    )

    assert len(chains) >= 2
    entity_chain = next(c for c in chains if "entity" in c.bottleneck_id)
    assert entity_chain.expected_mechanism != ""
    assert entity_chain.verification_step != ""
    assert entity_chain.projected_outcome != ""
    assert "f_icp_01" in entity_chain.contributing_finding_ids

    latency_chain = next(c for c in chains if "latency" in c.bottleneck_id)
    assert "2800ms" in latency_chain.observed_symptoms[0]
    assert "f_ttfb_01" in latency_chain.contributing_finding_ids


def test_ai_retrieval_observatory_records():
    """Verify that AiRetrievalObservatory accurately extracts verbatim answers, passages, prominence, and competitor co-citations."""
    class MockRun:
        query_id = "q_secops_1"
        query_text = "best enterprise secops monitoring tools"
        category = "commercial_evaluation"
        engine_id = "perplexity"
        engine_name = "Perplexity AI"
        status = "SUCCESS"
        raw_response = (
            "For enterprise SecOps monitoring, CompetitorA is a top solution with robust cloud compliance. "
            "Another leading option is DataFlow Systems (https://dataflow.io/solutions/secops), which delivers automated "
            "log stream telemetry and zero-trust verification."
        )
        citations = ["https://competitora.com/platform", "https://dataflow.io/solutions/secops"]
        was_mentioned = True
        was_first_party_cited = True
        latency_ms = 412.0

    runs = [MockRun()]
    summary = AiRetrievalObservatory.compile_observatory(
        evaluations=runs,
        brand_name="DataFlow Systems",
        target_domain="dataflow.io",
        competitors=["competitora.com"]
    )

    assert summary.total_evaluations == 1
    assert summary.brand_mention_rate_pct == 100.0
    assert summary.brand_citation_rate_pct == 100.0
    assert "Competitora" in summary.top_competitors_cited

    rec = summary.records[0]
    assert rec.brand_mentioned is True
    assert rec.brand_cited is True
    assert rec.cited_url == "https://dataflow.io/solutions/secops"
    assert rec.cited_passage is not None
    assert "DataFlow Systems" in rec.cited_passage
    assert len(rec.competitors_mentioned) == 1
    assert len(rec.competitors_cited) == 1
    assert rec.competitors_cited[0].name == "Competitora"


def test_competitive_evidence_graph_matrices_and_reasons():
    """Verify that CompetitiveEvidenceGraphEngine creates question rows and explains why winners won."""
    profile = BusinessProfile(
        business_name="DataFlow Systems",
        niche="Log Telemetry"
    )

    target_evals = [
        CommercialQueryEvaluation(
            question_key="identity",
            question_title="Identity",
            buyer_query="What does DataFlow Systems do?",
            before_evidence_status="FOUND",
            before_score=9.0,
            before_answer="DataFlow Systems is an enterprise log telemetry and compliance platform."
        ),
        CommercialQueryEvaluation(
            question_key="pricing",
            question_title="Pricing",
            buyer_query="How much does DataFlow Systems cost?",
            before_evidence_status="FOUND",
            before_score=3.0,
            before_answer="Contact sales for custom pricing."
        ),
    ]

    comp_evals = {
        "rivalcorp.com": [
            CommercialQueryEvaluation(
                question_key="identity",
                question_title="Identity",
                buyer_query="What does RivalCorp do?",
                before_evidence_status="FOUND",
                before_score=7.0,
                before_answer="RivalCorp is a cloud logging tool."
            ),
            CommercialQueryEvaluation(
                question_key="pricing",
                question_title="Pricing",
                buyer_query="How much does RivalCorp cost?",
                before_evidence_status="FOUND",
                before_score=9.0,
                before_answer="RivalCorp starts at $49/mo with transparent per-GB pricing tiers."
            ),
        ]
    }

    graph_res = CompetitiveEvidenceGraphEngine.build_graph(
        target_profile=profile,
        target_domain="dataflow.io",
        target_evals=target_evals,
        competitor_evals=comp_evals
    )

    assert len(graph_res.matrix_rows) == 6
    identity_row = next(r for r in graph_res.matrix_rows if r.question_key == "identity")
    assert identity_row.winning_entity == "target"
    assert "DataFlow Systems provides superior" in identity_row.why_winner_won

    pricing_row = next(r for r in graph_res.matrix_rows if r.question_key == "pricing")
    assert pricing_row.winning_entity == "competitor"
    assert "Rivalcorp" in pricing_row.why_winner_won
    assert "structured" in pricing_row.why_winner_won.lower()


def test_multi_plane_evidence_fusion_fail_closed():
    """Verify that MultiPlaneEvidenceFusion unifies planes and emits CONNECTOR_STATUS without faking data."""
    graph = EvidenceGraph(run_id="run_fusion_test")
    summary = MultiPlaneEvidenceFusion.fuse_all_planes(
        graph=graph,
        domain="dataflow.io",
        manifest=None,
        external_authority=None,  # Not connected
        gsc_data=None,            # Not connected
        ga4_data=None,            # Not connected
    )

    assert summary.domain == "dataflow.io"
    # Check that unconnected connectors emit NOT_CONFIGURED statuses
    gsc_status = next(c for c in summary.connector_statuses if c.connector_id == "google_search_console")
    assert gsc_status.is_connected is False
    assert gsc_status.status_label == "NOT_CONFIGURED"

    backlink_status = next(c for c in summary.connector_statuses if c.connector_id == "backlink_authority_provider")
    assert backlink_status.is_connected is False
    assert backlink_status.status_label == "NOT_CONFIGURED"


def test_report_critic_converts_missing_to_multiple_h1_and_adds_overall_score_bridge():
    """Verify that when 0 pages miss H1 but multiple H1s exist, a spurious missing H1 finding is converted to multiple H1s and scoring bridge is added."""
    from app.domain.models import HeadingIssueItem
    profile = BusinessProfile(business_name="CloudNet", niche="Networking")
    scores = OverallScoreResult(
        overall_score=75.0,
        grade="B",
        health_label="Good",
        category_scores={
            "TECHNICAL_SEO": CategoryScore(
                category=Category.TECHNICAL_SEO,
                score=62.0,
                weight=25.0,
                weighted_score=15.5,
                summary="Technical SEO compliance"
            )
        }
    )
    honest = HonestScores(human_score=85.0, google_score=23.0, ai_readiness_score=55.0, ai_visibility_score=0.0)

    f_spurious = Finding(
        finding_id="F_H1_001",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        classification=FindingClassification.VERIFIED_DEFECT,
        title="Document lacks a top-level <h1> heading",
        description="Document lacks a top-level <h1> heading in HTML body.",
        recommendation="Ensure a single <h1> heading is present."
    )

    report = ExecutiveReport(
        report_id="rep_h1_reconcile_test",
        website_url="https://cloudnet.io",
        domain="cloudnet.io",
        generated_at="October 2026",
        business_profile=profile,
        scores=scores,
        honest_scores=honest,
        story_summary="Strategic test",
        primary_strategic_opportunity="Refine entity definition",
        consultant_advice_what_to_ignore="Ignore minor cosmetic tweaks",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear value proposition",
            search_engine_perspective="Crawl friction",
            ai_answer_engine_perspective="Needs schema"
        ),
        findings=[f_spurious],
    )

    heading_rollup = HeadingHierarchyRollup(
        total_pages_evaluated=5,
        missing_h1=[],  # 0 missing H1
        multiple_h1=[
            HeadingIssueItem(url="https://cloudnet.io", detail="Multiple H1s", snippet="<h1>A</h1><h1>B</h1>"),
            HeadingIssueItem(url="https://cloudnet.io/pricing", detail="Multiple H1s", snippet="<h1>C</h1><h1>D</h1>"),
        ],
        short_h1=[],
        long_h1=[],
        duplicate_h1=[],
        hierarchy_violations=[],
        total_heading_issues=2,
        h1_health_score=80.0
    )

    reconciled_rep, actions = ReportCritic.reconcile_report(
        report,
        manifest=None,
        heading_hierarchy=heading_rollup
    )

    assert len(reconciled_rep.findings) == 1
    # Check that title was converted to multiple H1s instead of claiming document lacks H1
    assert "multiple" in reconciled_rep.findings[0].title.lower()
    assert "lacks" not in reconciled_rep.findings[0].title.lower()
    assert "multiple competing <h1> tags" in reconciled_rep.findings[0].description.lower()

    # Check scoring explanation bridge has Overall Composite Score bridge and AI citation bridge
    assert "Overall Composite Score (75/100)" in reconciled_rep.scoring_explanation
    assert "Live AI Citation Visibility is currently 0/100" in reconciled_rep.scoring_explanation


def test_causal_reasoning_synthesizes_competitive_displacement():
    """Verify that CausalReasoningEngine generates causal_05_competitive_displacement when competitive graph reports competitor wins."""
    engine = CausalReasoningEngine()
    profile = BusinessProfile(
        business_name="DataFlow",
        niche="Data Engineering",
        business_model="B2B SaaS",
        competitors=["rivalcorp.io"]
    )

    claims = [
        Claim(id="clm_comp_1", agent_id="agent_comp", category=Category.COMPETITIVE, statement="Rival domains dominate comparison queries"),
    ]

    target_evals = [
        CommercialQueryEvaluation(
            question_key="pricing",
            question_title="Pricing",
            buyer_query="What is the pricing model?",
            intent_category="Commercial",
            before_evidence_status="FOUND",
            before_score=3.0,
            before_answer="Contact sales for custom enterprise quotes."
        )
    ]
    comp_evals = {
        "rivalcorp.io": [
            CommercialQueryEvaluation(
                question_key="pricing",
                question_title="Pricing",
                buyer_query="What is the pricing model?",
                intent_category="Commercial",
                before_evidence_status="FOUND",
                before_score=9.0,
                before_answer="RivalCorp starts at $49/mo with transparent tiers."
            )
        ]
    }
    graph_res = CompetitiveEvidenceGraphEngine.build_graph(
        target_profile=profile,
        target_domain="dataflow.io",
        target_evals=target_evals,
        competitor_evals=comp_evals
    )

    chains = engine.analyze_root_causes(
        claims=claims,
        business_profile=profile,
        competitive_graph=graph_res
    )

    comp_chain = next((c for c in chains if c.bottleneck_id == "causal_05_competitive_displacement"), None)
    assert comp_chain is not None
    assert "Competitive Answer Engine Displacement" in comp_chain.title
    assert comp_chain.primary_category == Category.COMPETITIVE
    assert "pricing" in comp_chain.prescribed_remediation.lower() or "/vs/" in comp_chain.prescribed_remediation.lower()
    assert comp_chain.expected_mechanism != ""
    assert comp_chain.verification_step != ""
    assert comp_chain.projected_outcome != ""


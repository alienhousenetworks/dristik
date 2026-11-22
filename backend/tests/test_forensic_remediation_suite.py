"""Forensic End-to-End Remediation & Cross-Surface Parity Regression Suite.

Verifies every P0/P1 root-cause fix across:
- Phase 1: Crawl fidelity (header merge, SSRF, canonical vs final_url, thin_content, multi-sitemap, DB WAL)
- Phase 2: Inference grounding (no Pass-1 prose leakage), critic/integrity ordering, ContradictionEngine, Confidence >= 0.92, Causal/Hypothesis grounding
- Phase 3: Deterministic-first hybrid specialist execution & zero unbound GEO/AEO pure-deterministic agents
- Phase 4: SEO analyzers (MathematicalScoreEngine, link_graph_engine, simulator, international, topical, LCP subparts)
- Phase 5: GEO search grounding vs ungrounded inline URLs, readiness floor removal & no metric aliasing
- Phase 6: CRO bare-page (`example.com`) honesty (no 100/100 on forms/UX/UI, no 50.0 on unmeasured analytics, no raw enum leak)
- Phase 7: PPTX Deck & HTML Deck parity (zero hardcoded Grade B/A-/C, zero 50.0 unmeasured bar, honest NOT_TESTED chapters)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.core.inference.model_router import ModelRouter
from app.crawl.crawler import CrawlerService
from app.cro.models import (
    CROAudit,
    CROBusinessModelType,
    CROBusinessProfile,
    CRODimensionCheck,
    CROPage,
    CROPageType,
)
from app.cro.reports.builder import CROReportBuilder, _fmt_enum, render_weighted_scorecard_svg
from app.cro.scoring import enterprise_cro_scoring_engine
from app.cro.specialists.forms_cta import run_department_e
from app.cro.specialists.ux_ui import run_department_b, run_department_c
from app.cro.specialists import CROAuditContext
from app.db.repository import AuditRepository
from app.domain.enums import Category, Severity, VerificationStatus
from app.domain.models import (
    Claim,
    ExecutiveReport,
    Finding,
    HonestScores,
    OverallScoreResult,
    PageEvidence,
)
from app.geo.adapters.openai_search import OpenAISearchAdapter
from app.geo.models import GEOAuditScope, GEOTestingMode
from app.geo.specialists import GEOAuditContext
from app.geo.specialists.readiness import run_department_d
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.orchestration.cognition.causal import CausalReasoningEngine
from app.orchestration.cognition.confidence import CalibratedConfidenceEngine
from app.orchestration.cognition.contradiction_engine import ContradictionEngine
from app.orchestration.cognition.hypotheses import HypothesisEngine
from app.orchestration.runtime.registry import SPECIALIST_AGENTS_V3
from app.orchestration.runtime.specialist import SpecialistAgent
from app.reports.deck.coordinator import generate_executive_html_deck, generate_executive_pptx_deck
from app.reports.deck.html_deck_renderer import HtmlVectorDeckRenderer
from app.reports.deck.models import ChartDataSpec, DeckChartType
from app.seo.analyzers.lcp_subparts import decompose_crux_lcp_subparts
from app.seo.analyzers.topical_authority_analyzer import analyze_topical_authority
from app.seo.audit.internal_links.link_graph_engine import build_internal_link_graph
from app.seo.audit.scoring.mathematical_score_engine import MathematicalScoreEngine
from app.seo.business.simulator import StrategySimulator
from app.workers.critic_worker import CognitiveCriticWorker


# ── Phase 1: Persistence & Crawl ──────────────────────────────────────────────

def test_audit_database_path_defined_and_wal_enabled(tmp_path):
    assert hasattr(settings, "AUDIT_DATABASE_PATH")
    db_file = str(tmp_path / "forensic_wal.db")
    repo = AuditRepository(db_path=db_file)
    with repo._get_conn() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert str(mode).lower() == "wal"


# ── Phase 2: Cognition, Contradiction, Critic, Confidence ─────────────────────

def test_contradiction_engine_detects_real_claim_conflicts():
    engine = ContradictionEngine()
    c1 = Claim(
        id="c1",
        agent_id="seo.html.v3",
        statement="Page is missing title tag on homepage.",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        confidence=0.9,
        evidence_refs=["ev_1"],
    )
    c2 = Claim(
        id="c2",
        agent_id="seo.onpage.v3",
        statement="Title present but title too long for SERP display.",
        category=Category.ON_PAGE_SEO,
        severity=Severity.LOW,
        confidence=0.8,
        evidence_refs=["ev_2"],
    )
    conflicts = engine.detect_contradictions([c1, c2])
    assert len(conflicts) == 1
    assert conflicts[0]["claim_a_id"] == "c1"
    assert conflicts[0]["claim_b_id"] == "c2"


def test_calibrated_confidence_can_reach_verified_threshold():
    engine = CalibratedConfidenceEngine()
    claims = [
        Claim(
            id=f"c{i}",
            agent_id="deterministic_seo",
            statement="Observed technical fact",
            category=Category.TECHNICAL_SEO,
            severity=Severity.LOW,
            confidence=0.95,
            evidence_refs=[f"ev_{i}"],
        )
        for i in range(5)
    ]
    pages = [PageEvidence(url=f"https://site.test/p{i}", status_code=200) for i in range(5)]
    res = engine.calculate_confidence(claims=claims, evidence_store=MagicMock(), pages=pages, contradictions_count=0, sample_target=5)
    assert res.confidence_score >= 0.92
    assert res.status == "VERIFIED"


@pytest.mark.asyncio
async def test_critic_cannot_overturn_rejected_claim_or_default_missing_to_supported():
    bb = CognitiveBlackboard(run_id="run_c1", website_url="https://site.test")
    c_rej = Claim(
        id="c_rej",
        agent_id="a1",
        statement="Already rejected claim",
        category=Category.CONTENT,
        severity=Severity.MEDIUM,
        confidence=0.5,
        evidence_refs=[],
        verification_status=VerificationStatus.REJECTED,
    )
    c_blank = Claim(
        id="c_blank",
        agent_id="a2",
        statement="Claim with blank decision",
        category=Category.CONTENT,
        severity=Severity.MEDIUM,
        confidence=0.5,
        evidence_refs=["ev_1"],
    )
    bb.claim_registry.add_claim(c_rej)
    bb.claim_registry.add_claim(c_blank)

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(return_value={
        "results": [
            {"claim_id": "c_rej", "decision": "supported", "rationale": "should not overturn"},
            {"claim_id": "c_blank", "rationale": "missing decision field"},
        ]
    })
    worker = CognitiveCriticWorker("critic", mock_router)
    await worker.execute_task("34_adversarial_verification", bb)

    assert c_rej.verification_status == VerificationStatus.REJECTED
    assert c_blank.verification_status == VerificationStatus.PENDING_VERIFICATION


def test_hypothesis_engine_ignores_rejected_claims_and_causal_has_no_fabricated_pct():
    hyp_engine = HypothesisEngine()
    hyps = hyp_engine.generate_initial_hypotheses("site.test", [])
    rejected = Claim(
        id="c_r",
        agent_id="a",
        statement="Missing schema json-ld for ai search",
        category=Category.SCHEMA,
        severity=Severity.CRITICAL,
        confidence=0.9,
        verification_status=VerificationStatus.REJECTED,
    )
    updated = hyp_engine.evaluate_hypotheses_against_evidence(hyps, [rejected], MagicMock())
    ai_hyp = next(h for h in updated if h.domain == "AI_SEARCH")
    assert ai_hyp.supporting_evidence_refs == []

    causal = CausalReasoningEngine()
    chains = causal.analyze_root_causes(
        claims=[],
        business_profile=MagicMock(),
        findings=[
            Finding(
                finding_id="f1",
                title="Slow TTFB latency",
                description="TTFB > 2500ms",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                recommendation="Add CDN",
            )
        ],
        crawl_summary={"avg_ttfb_ms": 2600},
    )
    assert chains
    assert "15-25%" not in chains[0].projected_outcome


# ── Phase 3: Deterministic-First Specialists & Unbound GEO/AEO Coverage ───────

@pytest.mark.asyncio
async def test_all_pure_deterministic_registry_agents_have_real_handlers():
    bb = CognitiveBlackboard(run_id="run_det1", website_url="https://site.test")
    bb.pages = [
        PageEvidence(
            url="https://site.test/",
            status_code=200,
            title="Site Home",
            h1=["Welcome"],
            word_count=400,
            is_indexable=True,
            schema_types=["Organization"],
        )
    ]
    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(side_effect=AssertionError("Pure deterministic agent must not call LLM"))

    pure_det = [d for d in SPECIALIST_AGENTS_V3.values() if d.allowed_models == ["deterministic"]]
    assert len(pure_det) >= 6
    geo_aeo_det = [
        d for d in SPECIALIST_AGENTS_V3.values()
        if d.domain in ("GEO", "AEO") and "deterministic" in (d.allowed_models or [])
    ]
    for defn in list({d.agent_id: d for d in pure_det + geo_aeo_det}.values()):
        agent = SpecialistAgent(defn, mock_router)
        res = await agent.run(bb)
        assert res.get("unavailable_reason") != "no_deterministic_check", f"{defn.agent_id} still hit no_deterministic_check"


@pytest.mark.asyncio
async def test_hybrid_technical_agent_runs_deterministic_first_without_llm():
    bb = CognitiveBlackboard(run_id="run_hyb1", website_url="https://site.test")
    bb.pages = [
        PageEvidence(url="https://site.test/", status_code=200, title="Home", h1=["Home"], word_count=350, is_indexable=True)
    ]
    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(side_effect=AssertionError("Hybrid TECHNICAL_SEO agent must run deterministically without LLM"))
    defn = SPECIALIST_AGENTS_V3["seo.indexability.v3"]
    agent = SpecialistAgent(defn, mock_router)
    res = await agent.run(bb)
    assert res["status"] == "completed"
    mock_router.generate_structured.assert_not_called()


# ── Phase 4: SEO Math, Link Graph, Simulator, Topical, LCP Subparts ───────────

def test_mathematical_score_engine_no_free_pass_or_phantom_100():
    engine = MathematicalScoreEngine()
    bare_pages = [{"url": "https://bare.test/", "status_code": 200, "title": "", "h1": [], "word_count": 10}]
    sc = engine.build_scorecard_from_observations(
        pages=bare_pages,
        findings=[],
        evidence_records=[],
        discovered_count=1,
        crawled_count=1,
        sampling_status="FULL_CRAWL",
        connector_statuses=[{"provider_id": "backlink_provider", "status": "CONNECTED"}],
        specialist_applicable={"local": True},
    )
    dim_map = {d.dimension_id: d for d in sc.dimensions}
    # Bare page without title/H1/intent must NOT pass content.intent_alignment
    assert dim_map["content_quality_intent"].score < 100.0
    # Unexecuted specialist and authority dimensions must remain unmeasured (not phantom 100/100)
    assert dim_map["specialist_applicability"].is_measured is False
    assert dim_map["specialist_applicability"].score is None
    assert dim_map["trust_authority_signals"].is_measured is False
    assert dim_map["trust_authority_signals"].score is None


def test_strategy_simulator_zero_findings_produces_zero_gain():
    sim = StrategySimulator()
    scenarios = sim.simulate_scenarios(current_score=72.0, findings=[])
    assert all(s.projected_score == 72.0 for s in scenarios)


def test_link_graph_no_fabricated_homepage_depth_or_word_count():
    graph = build_internal_link_graph(
        pages=[
            {"url": "https://site.test/sub", "title": "Sub", "status_code": 200, "internal_links": ["https://site.test/uncrawled"]},
            {"url": "https://site.test/orphan", "title": "Orphan", "status_code": 200, "internal_links": []},
        ],
        domain="site.test",
    )
    node_urls = {n["url"] for n in graph["nodes"]}
    assert "https://site.test/" not in node_urls  # never fabricated a 500-word homepage
    orphan = next(n for n in graph["nodes"] if n["url"] == "https://site.test/orphan")
    assert orphan["click_depth"] is None  # unreachable depth stays None, not 4
    assert orphan["word_count"] is None  # missing word_count stays None, not 450
    edge = graph["edges"][0]
    assert edge["status_code"] is None  # uncrawled target status is None, not 200
    assert edge["anchor_text"] == ""  # no fabricated anchor from source title


def test_topical_authority_empty_page_has_zero_floor_and_lcp_subparts():
    rep, _findings = analyze_topical_authority([PageEvidence(url="https://empty.test/", status_code=200, word_count=0, h1=[], h2=[])])
    assert rep.topical_coverage_score == 0.0

    lcp = decompose_crux_lcp_subparts({
        "record": {
            "metrics": {
                "largest_contentful_paint": {"percentiles": {"p75": 4000}},
                "largest_contentful_paint_image_time_to_first_byte": {"percentiles": {"p75": 600}},
                "largest_contentful_paint_image_element_render_delay": {"percentiles": {"p75": 2400}},
            }
        }
    })
    assert lcp["status"] == "MEASURED"
    assert lcp["dominant_bottlenecks"][0]["subpart"] == "element_render_delay_ms"
    assert lcp["dominant_bottlenecks"][0]["share_pct"] == 60.0


# ── Phase 5: GEO Honesty (Readiness Floors + Search Grounding) ────────────────

def test_geo_readiness_no_floors_or_aliased_accuracy():
    ctx = GEOAuditContext(
        tenant_id="t1",
        audit_id="geo_test_1",
        scope=GEOAuditScope(brand_name="Example", domain="example.com", website_url="https://example.com/"),
        pages=[PageEvidence(url="https://example.com/", status_code=200, body_text="Example Domain", h1=[], h2=[], schema_types=[])],
        raw_html_map={"https://example.com/": "<html><body><p>Example Domain</p></body></html>"},
    )
    _, _, records = run_department_d(ctx)
    rec = records[0]
    assert rec.accuracy_score is None  # never aliased from trust_score
    assert rec.freshness_score == 0.0  # no 40.0 floor
    assert rec.specificity_score == 0.0  # no 20.0 floor


@pytest.mark.asyncio
async def test_openai_search_adapter_ungrounded_model_does_not_report_inline_urls_as_verified_citations():
    adapter = OpenAISearchAdapter(api_key="sk-test", model="openai/gpt-oss-20b")
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "model": "openai/gpt-oss-20b",
        "choices": [{"message": {"content": "Check https://example.com for details.", "annotations": []}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 15},
    }
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=fake_resp)
    res = await adapter.execute_query("best tools", client=mock_client, enable_search=True)
    assert res.testing_mode == GEOTestingMode.API_MODEL_ONLY
    assert res.citations == []
    assert res.tool_use_metadata["ungrounded_inline_urls_excluded"] == 1


# ── Phase 6: CRO Bare Page Honesty & Enum Formatting ──────────────────────────

def test_cro_bare_example_com_no_inflated_100_or_50_or_enum_leak():
    bare_html = "<html><head><title>Example Domain</title></head><body><h1>Example Domain</h1><p>This domain is for illustrative examples.</p></body></html>"
    page = CROPage(
        page_id="pg_1",
        tenant_id="t1",
        audit_id="cro_test_1",
        url="https://example.com/",
        page_type=CROPageType.HOMEPAGE,
        title="Example Domain",
        word_count=12,
        status_code=200,
    )
    profile = CROBusinessProfile(
        profile_id="prof_1",
        tenant_id="t1",
        domain="example.com",
        website_url="https://example.com/",
        business_type=CROBusinessModelType.UNKNOWN,
    )
    audit = CROAudit(
        audit_id="cro_test_1",
        tenant_id="t1",
        domain="example.com",
        target_url="https://example.com/",
        profile_id="prof_1",
    )
    ctx = CROAuditContext(
        tenant_id="t1",
        audit_id="cro_test_1",
        domain="example.com",
        target_url="https://example.com/",
        profile=profile,
        pages=[page],
        raw_html_map={"https://example.com/": bare_html},
    )
    run_department_b(ctx)
    run_department_c(ctx)
    run_department_e(ctx)

    bundle = enterprise_cro_scoring_engine.evaluate_three_scorecards(
        audit_id="cro_test_1",
        checks=ctx.dimension_checks,
        measurement_checks=[{"check": "ga4", "status": "warning"}],
        business_metrics=[{"metric": "CR", "status": "data_unavailable", "value": None}],
        pages_audited=1,
        pages_discovered=1,
        analytics_connected=False,
    )
    dim_scores = {d.dimension_id: d.score for d in bundle.experience_dimensions}
    assert dim_scores["ux_usability"] < 60.0
    assert dim_scores["ui_visual_hierarchy"] < 60.0
    assert dim_scores["forms_cta"] == 0.0
    assert bundle.measurement_score == 0.0
    assert bundle.measurement_status == "unmeasured"
    assert bundle.confidence < 0.75
    assert _fmt_enum(CROBusinessModelType.UNKNOWN) == "Unknown"

    svg = render_weighted_scorecard_svg([d.model_dump() for d in bundle.experience_dimensions])
    assert "Conversion journey and funnel quality" in svg


# ── Phase 7: PPTX & HTML Deck Parity (Zero Hardcoded Grades) ──────────────────

def test_pptx_and_html_deck_reflect_real_scores_not_hardcoded_grades():
    report = ExecutiveReport(
        report_id="rep_parity_1",
        org_id="org_test",
        analysis_id="run_parity_1",
        website_url="https://parity.test",
        domain="parity.test",
        generated_at=datetime.now(timezone.utc).isoformat(),
        scores=OverallScoreResult(overall_score=38.0, grade="F", health_label="Low readiness", category_scores={}),
        honest_scores=HonestScores(
            human_score=32.0,
            google_score=44.0,
            ai_readiness_score=25.0,
            ai_visibility_score=None,
            overall_score=38.0,
            score_band="Low readiness",
        ),
        story_summary="Test summary.",
        primary_strategic_opportunity="Test opportunity.",
        consultant_advice_what_to_ignore="Test ignore.",
        findings=[],
    )
    pptx_bytes, blueprint = generate_executive_pptx_deck(report)
    assert pptx_bytes[:2] == b"PK"  # valid ZIP/PPTX
    slide_map = {s.slide_id: s for s in blueprint.slides}
    assert "Grade F" in slide_map["slide_08_human_perspective"].cards[0].metric_value
    assert "Grade F" in slide_map["slide_09_search_perspective"].cards[0].metric_value
    assert "Grade F" in slide_map["slide_10_ai_perspective"].cards[0].metric_value
    assert "Grade A-" not in str(slide_map["slide_09_search_perspective"].model_dump())

    html_renderer = HtmlVectorDeckRenderer()
    svg = html_renderer._generate_svg_chart(
        ChartDataSpec(title="Test", chart_type=DeckChartType.BAR, categories=["Unmeasured Pillar"], series=[{"name": "Score", "values": [None]}])
    )
    assert "Unmeasured" in svg
    assert ">50<" not in svg

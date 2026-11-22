"""Fail-closed checks for agent results and published grades."""
import pytest
from unittest.mock import AsyncMock

from app.aeo.intelligence.aeo_scorecard import AeoScorecardEngine
from app.agents.runtime.registry import SPECIALIST_AGENTS_V3
from app.agents.runtime.specialist import SpecialistAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import CrawlManifest, PageEvidence
from app.geo.intelligence.geo_scorecard import GeoScorecardEngine
from app.seo.audit.scoring.mathematical_score_engine import (
    MathematicalScoreEngine,
    MetricCheck,
)
from app.seo.intelligence.seo_scorecard import SeoScorecardEngine


class _UnavailableRouter:
    def __init__(self):
        self.generate_structured = AsyncMock(return_value={
            "status": "unavailable",
            "unavailable_reason": "test_no_llm",
            "claims": [],
        })


def _board(pages):
    board = CognitiveBlackboard("forensic", "https://example.com")
    board.pages = pages
    board.crawl_manifest = CrawlManifest(
        domain="example.com",
        base_url="https://example.com",
        sitemap_found=True,
        robots_txt_found=True,
        pages=pages,
    )
    return board


def test_every_runtime_agent_declares_a_measurement_or_an_unmeasured_reason():
    page = PageEvidence(url="https://example.com/", title="Example", h1=["Example"])
    for agent_id, definition in SPECIALIST_AGENTS_V3.items():
        board = _board([page])
        result = SpecialistAgent(definition, model_router=None)._deterministic_audit(board, [])
        status = result["status"]
        observations = result["observations"]
        assert status in {"completed", "unmeasured", "unavailable"}, agent_id
        if status == "unmeasured":
            assert observations.get("unmeasured_reason"), agent_id
            assert result["claims"] == [], agent_id
        if status == "completed":
            assert observations.get("measurement_state") in {None, "measured", "not_applicable"} or result["claims"]
        for claim in result["claims"]:
            for ref in claim["evidence_refs"]:
                evidence = board.evidence_store.get(ref)
                assert evidence is not None, agent_id
                assert (evidence.text or "").strip() != claim["statement"].strip(), agent_id


def test_claim_evidence_is_not_the_claim_sentence():
    page = PageEvidence(url="https://example.com/missing", title="", h1=[], meta_description="")
    board = _board([page])
    definition = SPECIALIST_AGENTS_V3["seo.html.v3"]
    result = SpecialistAgent(definition, model_router=None)._deterministic_audit(board, [])
    assert result["status"] == "completed"
    assert result["claims"]
    for claim in result["claims"]:
        for ref in claim["evidence_refs"]:
            evidence = board.evidence_store.get(ref)
            assert "pages_inspected=" in (evidence.text or "")
            assert claim["statement"] not in (evidence.text or "")


def test_trust_and_pricing_do_not_fire_from_the_page_url():
    page = PageEvidence(
        url="https://example.com/privacy-pricing-customers",
        title="Home",
        h1=["Home"],
    )
    board = _board([page])
    trust = SpecialistAgent(SPECIALIST_AGENTS_V3["trust.authority.v3"], None)._deterministic_audit(board, [])
    pricing = SpecialistAgent(SPECIALIST_AGENTS_V3["cro.pricing_psychology.v3"], None)._deterministic_audit(board, [])
    proof = SpecialistAgent(SPECIALIST_AGENTS_V3["cro.social_proof_depth.v3"], None)._deterministic_audit(board, [])
    assert trust["status"] == "unmeasured"
    assert trust["observations"]["unmeasured_reason"] == "links_not_extracted"
    assert pricing["status"] == "unmeasured"
    assert proof["status"] == "unmeasured"
    joined = " ".join(
        claim["statement"] + claim["recommendation"]
        for result in (trust, pricing, proof)
        for claim in result["claims"]
    )
    assert "Footer lacks" not in joined
    assert "+40%" not in joined


def test_missing_content_authority_is_not_a_citation_finding():
    page = PageEvidence(url="https://example.com/", title="Example", h1=["Example"])
    board = _board([page])
    result = SpecialistAgent(SPECIALIST_AGENTS_V3["geo.citation_readiness.v3"], None)._deterministic_audit(board, [])
    assert result["status"] == "unmeasured"
    assert result["claims"] == []
    direct = SpecialistAgent(SPECIALIST_AGENTS_V3["aeo.direct_answer_box.v3"], None)._deterministic_audit(board, [])
    assert direct["observations"].get("answer_block_judgment") != "not_written"


def test_agent_without_a_check_is_unmeasured():
    board = _board([PageEvidence(url="https://example.com/", title="Example", h1=["Example"])])
    result = SpecialistAgent(SPECIALIST_AGENTS_V3["content.eeat.v3"], None)._deterministic_audit(board, [])
    assert result["status"] == "unmeasured"
    assert result["observations"]["unmeasured_reason"] == "no_deterministic_check"


@pytest.mark.asyncio
async def test_llm_outage_keeps_deterministic_claims():
    page = PageEvidence(url="https://example.com/a", title="A", h1=["A"], canonical_url=None)
    board = _board([page])
    router = _UnavailableRouter()
    result = await SpecialistAgent(SPECIALIST_AGENTS_V3["seo.indexability.v3"], router).run(board)
    assert result["status"] == "completed"
    assert result["claims"]
    assert result["mode"] == "DETERMINISTIC"
    assert "MEASURED_AWAITING_AGENT" not in str(result.get("mode"))


def test_partial_scores_are_not_published_as_health_grades():
    engine = MathematicalScoreEngine()
    dims = []
    for dim_id in engine.DIMENSION_WEIGHTS:
        if dim_id == "trust_authority_signals":
            dims.append(engine.calculate_dimension_score(dim_id, [], is_applicable=True))
        else:
            dims.append(engine.calculate_dimension_score(
                dim_id,
                [MetricCheck(check_id=dim_id, weight=1.0, passed=True)],
                is_applicable=True,
            ))
    seo = engine.calculate_scorecard(dims)
    assert seo.overall_health_score is None
    assert seo.score_status == "PARTIAL"
    assert seo.measured_subset_score == 100.0

    aeo = AeoScorecardEngine.calculate_scorecard(
        {"question_coverage": 80.0, "answer_completeness": 80.0},
        live_testing_ran=False,
    )
    assert aeo.overall_score is None
    assert aeo.assessment_status == "PARTIAL_ASSESSMENT"

    geo = GeoScorecardEngine.calculate_two_layer_scorecard(
        entity_clarity_score=90.0,
        live_connectors_ran=False,
    )
    assert geo.layer_1_status == "PARTIAL"
    assert geo.layer_1_readiness_score is None
    assert geo.layer_1_measured_subset_score == 90.0
    assert geo.layer_2_visibility_score is None

    card = SeoScorecardEngine.calculate_scorecard({"Crawlability & Indexability": 90.0})
    assert card.overall_score is None
    assert card.measured_subset_score == 90.0

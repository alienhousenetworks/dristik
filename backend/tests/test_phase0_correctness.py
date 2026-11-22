"""Phase 0 correctness and integrity regression tests."""
from types import SimpleNamespace
import pytest

from app.aeo.intelligence.factual_grounding_pipeline import FactualGroundingPipeline
from app.core.config import Settings
from app.crawl.page_intelligence import PageCopyAudit, PageSeoAudit, _fail_copy_audit
from app.cro.agents import PricingTrustAgent, VisualUxFrictionAgent
from app.cro.pillar import CroPillar
from app.domain.enums import Category, PatchOperation, Severity
from app.domain.models import BusinessProfile, Finding, PageEvidence, RemediationPatch
from app.geo.pillar import GeoPillar
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.orchestration.runtime.registry import SPECIALIST_AGENTS_V3
from app.orchestration.runtime.specialist import SpecialistAgent
from app.orchestration.runtime.tool_bus import AgentToolBus
from app.remediation.patch_engine import UniversalPatchEngine
from app.remediation.patch_generator import RemediationPatcher
from app.remediation.verifier import VerificationEngine
from app.verification.models import MachineAcceptanceCriterion, TestCategory, VerificationState
from app.verification.retester import IndependentRetester


def test_0_2_specialist_treats_budget_exceeded_as_unavailable():
    defn = SPECIALIST_AGENTS_V3["business.discovery.v3"]
    agent = SpecialistAgent(defn, model_router=None)
    bb = CognitiveBlackboard(run_id="run_test", website_url="https://example.com")
    res = agent._ingest_llm(
        bb,
        raw={"status": "budget_exceeded", "unavailable_reason": "max_cost_usd_reached", "claims": []},
        evidence_slice=[],
    )
    assert res["status"] == "unavailable"
    assert "max_cost_usd_reached" in res["unavailable_reason"]
    assert res["claims"] == []


def test_0_3_config_cascade_not_duplicated_and_sandbox_flag_declared():
    cfg = Settings(_env_file=None)
    assert cfg.ENABLE_CROSS_PROVIDER_CASCADE is True
    assert hasattr(cfg, "USE_LLM_SANDBOX_SYNTHESIS")
    assert cfg.USE_LLM_SANDBOX_SYNTHESIS is True


def test_0_4_tool_bus_reads_real_page_evidence_attributes():
    bb = CognitiveBlackboard(run_id="run_tb", website_url="https://example.com")
    bb.pages = [
        PageEvidence(
            url="https://example.com/",
            title="Acme Cloud",
            body_text="Real visible body copy for Acme Cloud.",
            images_without_alt=3,
            raw_schema=[{"@type": "Organization", "name": "Acme"}],
            viewport="width=device-width, initial-scale=1",
        )
    ]
    bus = AgentToolBus(bb)
    dom = bus.inspect_page_dom("https://example.com/")
    assert dom["json_ld_count"] == 1
    assert dom["images_missing_alt"] == 3
    assert "Real visible body copy" in dom["visible_text_excerpt"]


@pytest.mark.asyncio
async def test_0_4_cro_agents_read_real_page_evidence_fields():
    bb = CognitiveBlackboard(run_id="run_cro", website_url="https://example.com")
    bb.pages = [
        PageEvidence(
            url="https://example.com/pricing",
            title="Pricing",
            viewport="width=device-width, initial-scale=1",
            body_text="We are SOC 2 Type II and GDPR compliant.",
        )
    ]
    ux_res = await VisualUxFrictionAgent().run(bb)
    assert ux_res["observations"]["mobile_viewport_configured"] is True
    assert ux_res["observations"]["ux_friction_points_count"] == 0

    trust_res = await PricingTrustAgent().run(bb)
    assert trust_res["observations"]["trust_badges_detected"] is True


def test_0_5_factual_grounding_does_not_auto_pass_keywords():
    report = FactualGroundingPipeline.run_grounding_pipeline(
        claims=[
            "Our formula is clinically tested with a 30-day return guarantee.",
        ],
        empirical_catalog={"products": ["Widget Pro"]},
    )
    assert report.grounded_claims_count == 0
    assert report.unsupported_claims_count == 1
    assert report.validations[0].is_factually_grounded is False


def test_0_6_fail_copy_audit_sets_failed_status():
    copy = PageCopyAudit(llm_status="pending")
    out = _fail_copy_audit(copy, PageSeoAudit(), "timeout", "llm_timeout")
    assert out.llm_status == "failed"
    assert out.llm_failure_reason == "timeout"
    assert out.llm_failure_code == "llm_timeout"


def test_0_7_patch_generator_never_fabricates_sameas_or_dummy_image():
    bp = BusinessProfile(
        business_name="Acme Corp",
        niche="Cloud Backup",
        value_proposition="Automated encrypted backups for databases.",
    )
    img_finding = Finding(
        finding_id="F_IMG_1",
        title="Images missing alt text",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        description="Images lack alt text",
    )
    pages = [PageEvidence(url="https://acme.example/", external_links=["https://github.com/acmecorp"])]
    patches = RemediationPatcher().generate_patches(
        findings=[img_finding],
        business_profile=bp,
        website_url="https://acme.example",
        pages=pages,
    )
    joined = "\n".join(p.after_snippet for p in patches)
    assert "/assets/hero-banner.png" not in joined
    assert "linkedin.com/company/acmecorp" not in joined
    assert "twitter.com/acmecorp" not in joined
    assert "https://github.com/acmecorp" in joined


def test_0_7_patch_engine_no_modern_teams_and_no_nextjs_on_wordpress():
    bp = BusinessProfile(
        business_name="Acme Bakery",
        niche="Artisan Bread",
        value_proposition="Fresh sourdough baked every morning.",
    )
    wp_page = PageEvidence(
        url="https://acmebakery.example/",
        raw_html="<html><body><link href='/wp-content/themes/bakery/style.css'/></body></html>",
    )
    patches = UniversalPatchEngine().generate_patches(
        findings=[],
        business_profile=bp,
        website_url="https://acmebakery.example",
        pages=[wp_page],
    )
    assert all(p.finding_id != "F-DEV-NEXTJS" for p in patches)
    assert all("for Modern Teams" not in (p.after_snippet or "") for p in patches)


def test_0_8_retester_fails_closed_when_metrics_unmeasured():
    retester = IndependentRetester()

    http_crit = MachineAcceptanceCriterion(
        criterion_id="C1",
        finding_id="F1",
        test_category=TestCategory.HTTP_CONDITION,
        condition_name="HTTP 200 check",
        expected_condition_text="HTTP status must be 200",
        min_value=200,
    )
    assert retester.evaluate_criterion(http_crit, {}).passed is False

    perf_crit = MachineAcceptanceCriterion(
        criterion_id="C2",
        finding_id="F2",
        test_category=TestCategory.PERFORMANCE,
        condition_name="TTFB check",
        expected_condition_text="TTFB <= 300ms",
        max_value=300.0,
    )
    assert retester.evaluate_criterion(perf_crit, {}).passed is False

    f = Finding(finding_id="F_T", title="Missing Title Tag", category=Category.ON_PAGE_SEO, severity=Severity.HIGH)
    rec = retester.retest_finding(
        f,
        original_evidence={"html": "<html><head></head></html>"},
        new_evidence={"html": "<html><head><title>Hi</title></head></html>"},
    )
    assert rec.verification_passed is False
    assert rec.partially_fixed is False
    assert rec.current_finding_state == VerificationState.FAILED


@pytest.mark.asyncio
async def test_0_8_verifier_insert_head_does_not_pass_on_stray_word(monkeypatch):
    class _FakeResp:
        status_code = 200
        text = "<html><head><title>Hi</title></head><body>Product description only.</body></html>"

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def get(self, *args, **kwargs):
            return _FakeResp()

    monkeypatch.setattr("app.remediation.verifier.httpx.AsyncClient", _FakeClient)
    patch = RemediationPatch(
        patch_id="P1",
        finding_id="F1",
        title="Add canonical",
        category=Category.TECHNICAL_SEO,
        target_url="https://example.com/",
        operation=PatchOperation.INSERT_HEAD,
        after_snippet='<link rel="canonical" href="https://example.com/" />',
        explanation="Add canonical tag",
    )
    res = await VerificationEngine().verify_remediation(patch)
    assert res.is_resolved is False
    assert res.status == "PENDING_VERIFICATION"


def test_0_10_geo_and_cro_pillars_do_not_score_from_finding_count():
    f_geo = Finding(finding_id="G1", title="GEO gap", category=Category.GEO, severity=Severity.MEDIUM)
    geo_res = GeoPillar().calculate_pillar_score([f_geo])
    assert geo_res.metrics["score_status"] == "NOT_MEASURED"
    assert geo_res.grade == "N/A"

    # When measured geo_readiness exists on blackboard, GeoPillar uses it
    bb = SimpleNamespace(geo_readiness=SimpleNamespace(extractability_score=74.2))
    geo_measured = GeoPillar().calculate_pillar_score([f_geo], blackboard=bb)
    assert geo_measured.metrics["score_status"] == "MEASURED"
    assert geo_measured.score == 74.2

    f_cro = Finding(finding_id="C1", title="CRO gap", category=Category.UX_CONVERSION, severity=Severity.MEDIUM)
    cro_res = CroPillar().calculate_pillar_score([f_cro])
    assert cro_res.metrics["score_status"] == "NOT_MEASURED"
    assert cro_res.grade == "N/A"

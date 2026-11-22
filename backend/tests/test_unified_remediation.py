"""
Unit & Integration tests for Unified Multi-Pillar & Competitor Remediation.
Verifies that individual pillar remediation can be cleanly deferred and that the
unified remediation engine accepts cross-pillar findings and competitor context.
"""
import pytest
from app.domain.models import Finding, BusinessProfile, PageEvidence
from app.domain.enums import Category, Severity
from app.remediation.planner import RemediationPlanner
from app.remediation.patch_engine import patch_engine
from app.seo.audit.orchestration.execution_state import AuditConfiguration
from app.seo.audit.orchestrator import SeoAuditOrchestrator


def test_audit_configuration_defer_remediation_flag():
    cfg = AuditConfiguration(target_url="https://example.com", defer_remediation=True)
    assert cfg.defer_remediation is True

    cfg_default = AuditConfiguration(target_url="https://example.com")
    assert cfg_default.defer_remediation is False


def test_remediation_planner_accepts_competitor_context():
    planner = RemediationPlanner()
    profile = BusinessProfile(
        business_name="Acme Dental",
        niche="Clear Aligners",
        target_audience="Adults seeking teeth straightening",
        value_proposition="Fast affordable invisible aligners",
    )
    finding = Finding(
        finding_id="f_seo_001",
        title="Missing Title Tag",
        description="Page lacks canonical title tag",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
    )
    competitor_ctx = {
        "parity_matrix": None,
        "bakeoff": None,
        "domains": ["competitor.com"],
    }
    plan = planner.build_remediation_plan(
        findings=[finding],
        business_profile=profile,
        target_url="https://example.com",
        competitor_context=competitor_ctx,
    )
    assert plan is not None
    assert plan.plan_id.startswith("rem_")


def test_universal_patch_engine_accepts_competitor_context():
    profile = BusinessProfile(
        business_name="Acme Cloud",
        niche="Cloud Hosting",
        target_audience="Developers",
        value_proposition="Fast serverless hosting",
    )
    finding = Finding(
        finding_id="f_geo_001",
        title="Lack of FAQ Schema",
        description="Direct answer extractability requires FAQPage JSON-LD",
        category=Category.GEO,
        severity=Severity.MEDIUM,
    )
    competitor_ctx = {
        "parity_matrix": None,
        "bakeoff": None,
        "domains": ["cloudpeer.io"],
    }
    patches = patch_engine.generate_patches(
        findings=[finding],
        business_profile=profile,
        website_url="https://example.com",
        competitor_context=competitor_ctx,
    )
    assert isinstance(patches, list)


@pytest.mark.asyncio
async def test_seo_audit_deferred_remediation():
    cfg = AuditConfiguration(target_url="https://example.com", defer_remediation=True)
    orch = SeoAuditOrchestrator(audit_id="test_deferred_seo", domain="example.com", config=cfg)
    orch._register_all_agent_runners()
    runner = orch.executor.task_runners.get("remediation_planner")
    res = await runner({})
    assert res["status"] == "DEFERRED_TO_UNIFIED_PACK"
    assert res["tasks_count"] == 0

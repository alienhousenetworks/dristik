"""
Test Suite — Phase 8: AI Remediation Engine (10/10 Transformation)

Verifies all 8 sub-phases:
- 8.1: Canonical Remediation Backlog (All 14 required fields, deduplication)
- 8.2: Root-Cause Analysis Specialist Agents (10 non-conflicting council agents)
- 8.3: Platform Connectors (8 platforms with strict permission boundaries)
- 8.4: Universal Patch Generation (10 patch types with 9 fields + atomic rollback)
- 8.5: 9-Step Patch Validation Pipeline (Syntax, Type, Static, Security, Dep, Build, Test, Diff, Regression)
- 8.6: Human Approval & Deployment (5-tier governance, staging, prod, logs, rollback)
- 8.7: 10-Stage Lifecycle Verification (Complete state machine transitions & retest)
- 8.8: Three-Tier Impact Attribution (Technical vs Search/AI vs Commercial segregation)
"""
import pytest
from datetime import datetime

from app.domain.models import Finding
from app.domain.enums import Category, Severity
from app.remediation.models import (
    ApprovalTier,
    PatchType,
    PlatformType,
    RemediationTaskRecord,
    SpecialistAgentRole,
    TaskStatus,
)
from app.remediation.backlog_engine import (
    CanonicalBacklogEngine,
    canonical_backlog_engine,
)
from app.remediation.root_cause_agents import (
    RootCauseAgentCouncil,
    root_cause_council,
)
from app.remediation.platform_connectors import (
    get_connector,
)
from app.remediation.universal_patch_generator import (
    UniversalPatchGenerator,
    universal_patch_generator,
)
from app.remediation.patch_validation_pipeline import (
    PatchValidationPipeline,
    patch_validation_pipeline,
)
from app.remediation.deployment_governance import (
    DeploymentGovernanceEngine,
    deployment_governance,
)
from app.remediation.lifecycle_verification import (
    LifecycleVerificationEngine,
    lifecycle_verification_engine,
)
from app.remediation.impact_attribution import (
    ImpactAttributionEngine,
    impact_attribution_engine,
)
from app.remediation.remediation_engine import (
    unified_remediation_engine,
)


# ============================================================================
# Phase 8.1: Canonical Remediation Backlog
# ============================================================================

def test_phase8_1_canonical_backlog_all_14_fields():
    finding = Finding(
        finding_id="F_ROBOTS_AI_01",
        title="Unintended AI crawler block in robots.txt",
        category=Category.GEO,
        severity=Severity.HIGH,
        business_impact="Prevents inclusion in AI search engines and citation generation.",
        affected_urls=["https://example.com/robots.txt"],
        recommended_action="Remove Disallow directive for GPTBot and PerplexityBot.",
    )

    task: RemediationTaskRecord = canonical_backlog_engine.create_task_from_finding(finding)

    # 1. Finding ID
    assert task.finding_id == "F_ROBOTS_AI_01"
    # 2. Root cause
    assert len(task.root_cause) > 0
    # 3. Affected URLs
    assert task.affected_urls == ["https://example.com/robots.txt"]
    # 4. Affected templates
    assert len(task.affected_templates) > 0
    # 5. Recommended action
    assert "Remove Disallow" in task.recommended_action
    # 6. Business impact
    assert "citation generation" in task.business_impact
    # 7. Technical severity
    assert task.technical_severity == "HIGH"
    # 8. Confidence
    assert task.confidence > 0.8
    # 9. Estimated effort
    assert task.estimated_effort in ["LOW", "MEDIUM", "HIGH"]
    # 10. Dependencies
    assert isinstance(task.dependencies, list)
    # 11. Required permissions
    assert len(task.required_permissions) > 0
    # 12. Owner
    assert len(task.owner) > 0
    # 13. Status
    assert task.status == TaskStatus.DETECTED
    # 14. Verification criteria
    assert len(task.verification_criteria) > 10


# ============================================================================
# Phase 8.2: Root-Cause Analysis Specialist Agents
# ============================================================================

def test_phase8_2_specialist_agents_council():
    task = canonical_backlog_engine.create_task_from_finding(
        Finding(
            finding_id="F_GEO_SCHEMA_01",
            title="Missing Organization Schema for Entity Disambiguation",
            category=Category.GEO,
            severity=Severity.HIGH,
            affected_urls=["https://example.com/"],
            recommended_action="Inject Organization Schema JSON-LD.",
        )
    )

    report = root_cause_council.analyze_task(task)

    # Must have recommendations from all 10 specialist agents
    agent_roles = [r.agent_role for r in report.recommendations]
    assert len(report.recommendations) == 10
    assert SpecialistAgentRole.TECHNICAL_DIAGNOSIS in agent_roles
    assert SpecialistAgentRole.SEO_REMEDIATION in agent_roles
    assert SpecialistAgentRole.GEO_REMEDIATION in agent_roles
    assert SpecialistAgentRole.AEO_REMEDIATION in agent_roles
    assert SpecialistAgentRole.CRO_REMEDIATION in agent_roles
    assert SpecialistAgentRole.CONTENT_REMEDIATION in agent_roles
    assert SpecialistAgentRole.CODE_REMEDIATION in agent_roles
    assert SpecialistAgentRole.SECURITY_REVIEWER in agent_roles
    assert SpecialistAgentRole.ADVERSARIAL_CRITIC in agent_roles
    assert SpecialistAgentRole.VERIFICATION_AGENT in agent_roles

    assert report.security_approved is True
    assert report.critic_approved is True
    assert task.status == TaskStatus.ROOT_CAUSE_CONFIRMED


# ============================================================================
# Phase 8.3: Platform Connectors & Permission Boundaries
# ============================================================================

def test_phase8_3_platform_connector_boundaries():
    shopify = get_connector(PlatformType.SHOPIFY)
    webflow = get_connector(PlatformType.WEBFLOW)
    nextjs = get_connector(PlatformType.NEXT_JS)

    # 1. Shopify permits Liquid template patch
    task = canonical_backlog_engine.create_task_from_finding(Finding(finding_id="F_01", title="Title", category=Category.ON_PAGE_SEO, severity=Severity.LOW))
    liquid_patch = universal_patch_generator.generate_patch(
        task=task,
        patch_type=PatchType.HTML,
        original_code="<title>Old</title>",
        proposed_code="<title>New</title>",
        file_path="templates/index.liquid",
    )
    compat, _ = shopify.validate_patch_compatibility(liquid_patch)
    assert compat is True

    # 2. Shopify STRICTLY REJECTS arbitrary server code modifications
    server_patch = universal_patch_generator.generate_patch(
        task=task,
        patch_type=PatchType.CONFIGURATION,
        original_code="server { listen 80; }",
        proposed_code="server { listen 443; }",
        file_path="/etc/nginx/server.conf",
    )
    compat, err = shopify.validate_patch_compatibility(server_patch)
    assert compat is False
    assert "SHOPIFY" in err.upper()

    # 3. Webflow rejects configuration patches
    compat, err = webflow.validate_patch_compatibility(server_patch)
    assert compat is False
    assert "WEBFLOW" in err.upper()

    # 4. Next.js permits config patch
    compat, _ = nextjs.validate_patch_compatibility(server_patch)
    assert compat is True


# ============================================================================
# Phase 8.4: Universal Patch Generation & Rollback
# ============================================================================

def test_phase8_4_universal_patch_generation_9_fields():
    task = canonical_backlog_engine.create_task_from_finding(
        Finding(
            finding_id="F_AEO_FAQ_01",
            title="Missing FAQPage Schema",
            category=Category.AI_SEARCH,
            severity=Severity.MEDIUM,
            affected_urls=["https://example.com/faq"],
            recommended_action="Inject FAQPage Schema.",
        )
    )

    schema_json = '{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}'
    patch = universal_patch_generator.generate_json_ld_patch(
        task=task,
        file_path="pages/faq.html",
        schema_json=schema_json,
    )

    # 1. Original code
    assert patch.original_code == ""
    # 2. Proposed code
    assert "FAQPage" in patch.proposed_code
    # 3. File path
    assert patch.file_path == "pages/faq.html"
    # 4. Line references
    assert patch.line_references == "L15-L25"
    # 5. Change explanation
    assert "Schema.org" in patch.change_explanation
    # 6. Related finding
    assert patch.related_finding_id == "F_AEO_FAQ_01"
    # 7. Dependencies
    assert isinstance(patch.dependencies, list)
    # 8. Rollback patch (atomic inverse)
    assert patch.rollback_patch is not None
    assert patch.rollback_patch.original_code == patch.proposed_code
    assert patch.rollback_patch.rollback_code == patch.original_code
    # 9. Validation requirements
    assert "JSON_SYNTAX" in patch.validation_requirements


# ============================================================================
# Phase 8.5: 9-Step Patch Validation Pipeline
# ============================================================================

def test_phase8_5_patch_validation_pipeline_clean_patch():
    task = canonical_backlog_engine.create_task_from_finding(Finding(finding_id="F_META", title="Meta", category=Category.ON_PAGE_SEO, severity=Severity.LOW))
    patch = universal_patch_generator.generate_metadata_patch(
        task=task,
        file_path="index.html",
        orig_title="Old Title",
        new_title="New Optimized Enterprise Title",
        new_meta="New optimized meta description covering platform capabilities.",
    )

    report = patch_validation_pipeline.validate_patch(patch)
    assert len(report.step_results) == 9
    assert report.all_passed is True


def test_phase8_5_patch_validation_pipeline_rejects_malicious_code():
    task = canonical_backlog_engine.create_task_from_finding(Finding(finding_id="F_XSS", title="XSS", category=Category.TECHNICAL_SEO, severity=Severity.HIGH))
    malicious_patch = universal_patch_generator.generate_patch(
        task=task,
        patch_type=PatchType.JAVASCRIPT,
        original_code="// analytics",
        proposed_code="document.cookie = 'stolen'; eval('alert(1)');",
        file_path="public/analytics.js",
    )

    report = patch_validation_pipeline.validate_patch(malicious_patch)
    assert report.all_passed is False
    sec_step = next(s for s in report.step_results if s.step_name == "4_SECURITY_INSPECTION")
    assert sec_step.passed is False
    assert "vulnerability detected" in sec_step.error_message


# ============================================================================
# Phase 8.6: Human Approval & Deployment
# ============================================================================

def test_phase8_6_human_approval_hierarchy():
    gov = DeploymentGovernanceEngine()
    task = canonical_backlog_engine.create_task_from_finding(Finding(finding_id="F_REDIRECT", title="Redirect", category=Category.TECHNICAL_SEO, severity=Severity.HIGH))
    redirect_patch = universal_patch_generator.generate_redirect_rule_patch(
        task=task,
        file_path=".htaccess",
        old_path="/old-blog",
        new_path="/insights/new-blog",
    )

    # Critical infrastructure requires CHANGE_CRITICAL_INFRASTRUCTURE tier
    with pytest.raises(PermissionError):
        gov.authorize_and_deploy(
            patch=redirect_patch,
            target_environment="PRODUCTION",
            authorizer="junior_intern@company.com",
            user_tier=ApprovalTier.APPLY_TO_STAGING,  # Insufficient tier!
        )

    # Elevated user succeeds
    log_entry = gov.authorize_and_deploy(
        patch=redirect_patch,
        target_environment="PRODUCTION",
        authorizer="lead_devops@company.com",
        user_tier=ApprovalTier.CHANGE_CRITICAL_INFRASTRUCTURE,
    )
    assert log_entry.status == "SUCCESS"
    assert len(gov.deployment_logs) == 1

    # Atomic rollback test
    rb_entry = gov.rollback_deployment(
        patch=redirect_patch,
        target_environment="PRODUCTION",
        authorizer="lead_devops@company.com",
    )
    assert rb_entry.status == "ROLLED_BACK"


# ============================================================================
# Phase 8.7: 10-Stage Lifecycle Verification State Machine
# ============================================================================

def test_phase8_7_10_stage_lifecycle_verification():
    engine = LifecycleVerificationEngine()
    task = canonical_backlog_engine.create_task_from_finding(Finding(finding_id="F_01", title="Title", category=Category.GEO, severity=Severity.HIGH))

    # Sequential progression
    assert task.status == TaskStatus.DETECTED
    engine.transition_state(task, TaskStatus.ROOT_CAUSE_CONFIRMED)
    engine.transition_state(task, TaskStatus.PATCH_GENERATED)
    engine.transition_state(task, TaskStatus.PATCH_REVIEWED)
    engine.transition_state(task, TaskStatus.STAGING_VALIDATION_PASSED)
    engine.transition_state(task, TaskStatus.PRODUCTION_DEPLOYMENT_APPROVED)

    # Illegal transition test (cannot jump directly to CLOSED)
    with pytest.raises(ValueError):
        engine.transition_state(task, TaskStatus.CLOSED)

    # Retest evaluation: defect resolved closes task
    post_crawl_html = "<html><head><title>Fixed</title></head><body>No robots disallow here.</body></html>"
    retest = engine.evaluate_retest_and_close(
        task=task,
        observed_html=post_crawl_html,
        defect_indicator="Disallow: /GPTBot",
    )
    assert retest.defect_resolved is True
    assert task.status == TaskStatus.CLOSED

    # If retested with defect still present, task reopens
    task.status = TaskStatus.DETECTED
    engine.transition_state(task, TaskStatus.ROOT_CAUSE_CONFIRMED)
    engine.transition_state(task, TaskStatus.PATCH_GENERATED)
    engine.transition_state(task, TaskStatus.PATCH_REVIEWED)
    engine.transition_state(task, TaskStatus.STAGING_VALIDATION_PASSED)
    engine.transition_state(task, TaskStatus.PRODUCTION_DEPLOYMENT_APPROVED)

    bad_crawl_html = "<html><body>Disallow: /GPTBot still present</body></html>"
    bad_retest = engine.evaluate_retest_and_close(
        task=task,
        observed_html=bad_crawl_html,
        defect_indicator="Disallow: /GPTBot",
    )
    assert bad_retest.defect_resolved is False
    assert task.status == TaskStatus.REOPENED


# ============================================================================
# Phase 8.8: Three-Tier Impact Attribution
# ============================================================================

def test_phase8_8_three_tier_impact_attribution():
    engine = ImpactAttributionEngine()
    task = canonical_backlog_engine.create_task_from_finding(Finding(finding_id="F_01", title="Title", category=Category.AI_SEARCH, severity=Severity.MEDIUM))

    # Tier 1: Technical Success
    impact = engine.record_technical_success(task, evidence="FAQ schema returns 200 OK and validates in SDTT.")
    assert impact.technical_success is True
    # Zero-fabrication check: technical success does not imply search or commercial lift
    assert impact.search_ai_outcome_observed is False
    assert impact.commercial_outcome_observed is False

    # Tier 2: Search/AI Outcome Observed
    engine.attach_search_ai_outcome(impact, observed_citation_lift_pct=35.0, observed_rank_delta=3)
    assert impact.search_ai_outcome_observed is True
    assert "Citation lift=35.0%" in impact.search_ai_evidence
    assert impact.commercial_outcome_observed is False

    # Tier 3: Commercial Outcome Observed
    engine.attach_commercial_outcome(impact, measured_revenue_delta=15000.0)
    assert impact.commercial_outcome_observed is True
    assert "Revenue delta=15000.0" in impact.commercial_evidence


# ============================================================================
# Phase 8 End-to-End Orchestration (Connect -> Scan -> Fix -> Verify)
# ============================================================================

def test_phase8_unified_connect_scan_fix_verify_workflow():
    finding = Finding(
        finding_id="F_E2E_01",
        title="Unintended AI crawler block in robots.txt",
        category=Category.GEO,
        severity=Severity.HIGH,
        business_impact="Blocks ChatGPT from indexing and citing brand.",
        affected_urls=["https://example.com/robots.txt"],
        recommended_action="Remove Disallow: / directive for GPTBot.",
    )

    result = unified_remediation_engine.execute_end_to_end_remediation(
        finding=finding,
        platform_type=PlatformType.NEXT_JS,
        patch_type=PatchType.CONFIGURATION,
        original_code="User-agent: GPTBot\nDisallow: /",
        proposed_code="User-agent: GPTBot\nAllow: /",
        file_path="public/robots.txt",
        authorizer="lead_devops@enterprise.com",
        observed_post_deploy_html="User-agent: GPTBot\nAllow: /",
        defect_indicator="Disallow: /",
        test_search_lift=28.5,
    )

    # 1. Backlog & Council
    assert result.task.finding_id == "F_E2E_01"
    assert "Council consensus" in result.council_diagnosis

    # 2. Patch & Validation
    assert result.patch.patch_type == PatchType.CONFIGURATION
    assert result.validation_report.all_passed is True

    # 3. Governance
    assert result.staging_deployment.status == "SUCCESS"
    assert result.production_deployment.status == "SUCCESS"

    # 4. Lifecycle & Retest
    assert result.task.status == TaskStatus.CLOSED
    assert result.retest_evaluation.defect_resolved is True

    # 5. Impact
    assert result.impact_attribution.technical_success is True
    assert result.impact_attribution.search_ai_outcome_observed is True
    assert result.impact_attribution.commercial_outcome_observed is False  # Zero fabrication preserved

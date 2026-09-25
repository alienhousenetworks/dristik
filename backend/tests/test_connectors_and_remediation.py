"""
Comprehensive Test Suite for Dristik Universal Patch Engine, Connectors SDK, Verification, and ROI
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.domain.models import (
    Finding,
    FindingEvidence,
    BusinessProfile,
    RemediationPatch,
    RoiInput,
)
from app.domain.enums import (
    Category,
    Severity,
    PatchRiskLevel,
    PatchApprovalStatus,
    ConnectorType,
)
from app.remediation.patch_engine import UniversalPatchEngine
from app.remediation.diff_engine import DiffEngine
from app.remediation.approval import PatchApprovalManager
from app.remediation.rollback import PatchRollbackEngine
from app.connectors.base.models import ConnectorCredentials
from app.connectors.base.permissions import ConnectorSecurityGuard, PermissionViolationError
from app.connectors.wordpress import WordPressConnector
from app.connectors.github import GitHubConnector
from app.connectors.generic import GenericWebsiteConnector
from app.verification.verifier import VerificationEngine

def test_universal_patch_engine_classification():
    engine = UniversalPatchEngine()
    findings = [
        Finding(
            finding_id="F-001",
            category=Category.SCHEMA,
            severity=Severity.HIGH,
            title="Missing Organization Schema markup",
            description="The homepage does not have Schema.org Organization microdata.",
            recommendation="Inject validated JSON-LD schema.",
            evidence=[FindingEvidence(element="head", value="None", snippet="<head></head>")]
        ),
        Finding(
            finding_id="F-002",
            category=Category.UX_CONVERSION,
            severity=Severity.MEDIUM,
            title="Vague Hero Value Proposition",
            description="The headline does not clearly articulate the target audience or value.",
            recommendation="Rewrite hero copy with character-safe bounds.",
            evidence=[FindingEvidence(element="h1", value="Welcome", snippet="<h1>Welcome</h1>")]
        )
    ]
    bp = BusinessProfile(
        business_name="Acme Corp",
        niche="Enterprise AI Intelligence",
        value_proposition="Autonomous website intelligence and GEO citation platform."
    )

    patches = engine.generate_patches(findings, bp, "https://acme.com")
    assert len(patches) >= 4

    # Level 1 Safe Auto Check
    safe_patches = [p for p in patches if p.risk_level == PatchRiskLevel.SAFE_AUTO]
    assert len(safe_patches) >= 2
    assert any("schema" in p.title.lower() or "organization" in p.title.lower() for p in safe_patches)

    # Level 2 Human Review Check
    human_patches = [p for p in patches if p.risk_level == PatchRiskLevel.HUMAN_APPROVAL]
    assert len(human_patches) >= 1
    assert any("hero" in p.title.lower() or "content" in p.title.lower() for p in human_patches)

    # Level 3 Developer Required Check
    dev_patches = [p for p in patches if p.risk_level == PatchRiskLevel.DEVELOPER_REQUIRED]
    assert len(dev_patches) >= 1
    assert any("next.js" in p.title.lower() or "security" in p.title.lower() for p in dev_patches)

def test_diff_engine_computation():
    diff_eng = DiffEngine()
    patch = RemediationPatch(
        patch_id="PATCH-DIFF-01",
        finding_id="F-DIFF",
        title="Title Optimization",
        category=Category.TECHNICAL_SEO,
        target_file="index.html",
        before_snippet="<title>Acme</title>",
        after_snippet="<title>Acme — Enterprise AI Intelligence Platform</title>",
        explanation="Enforce 50-60 character length"
    )
    summary = diff_eng.generate_diff_summary(patch)
    assert summary["lines_added"] > 0
    assert "--- a/index.html" in summary["unified_diff"]
    assert "+++ b/index.html" in summary["unified_diff"]

def test_patch_approval_governance():
    mgr = PatchApprovalManager()
    p_safe = RemediationPatch(
        patch_id="P-SAFE",
        finding_id="F-1",
        title="Safe Schema",
        category=Category.SCHEMA,
        risk_level=PatchRiskLevel.SAFE_AUTO,
        after_snippet="{}",
        explanation="Safe auto"
    )
    p_human = RemediationPatch(
        patch_id="P-HUMAN",
        finding_id="F-2",
        title="Brand Rewrite",
        category=Category.UX_CONVERSION,
        risk_level=PatchRiskLevel.HUMAN_APPROVAL,
        after_snippet="{}",
        explanation="Needs approval"
    )

    assert mgr.can_auto_approve(p_safe) is True
    assert mgr.can_auto_approve(p_human) is False

    mgr.approve_patch(p_human, approver="lead_analyst@company.com")
    assert p_human.approval_status == PatchApprovalStatus.APPROVED
    assert p_human.approver == "lead_analyst@company.com"

    trail = mgr.get_audit_trail("P-HUMAN")
    assert len(trail) == 1
    assert trail[0]["action"] == "APPROVE"

def test_security_boundary_guard():
    # Attempt unsafe PHP injection
    malicious_patch = RemediationPatch(
        patch_id="P-MALICIOUS",
        finding_id="F-HACK",
        title="Malicious Script",
        category=Category.TECHNICAL_SEO,
        risk_level=PatchRiskLevel.DEVELOPER_REQUIRED,
        after_snippet="<?php system('rm -rf /'); ?>",
        explanation="Malicious attempt"
    )
    with pytest.raises(PermissionViolationError):
        ConnectorSecurityGuard.validate_patch_permissions(malicious_patch, "wordpress")

@pytest.mark.asyncio
async def test_wordpress_connector_flow():
    creds = ConnectorCredentials(
        provider=ConnectorType.WORDPRESS,
        api_url="https://acme-wp.com",
        username="admin",
        app_password="test_password"
    )
    connector = WordPressConnector(creds)
    health = await connector.test_connection()
    assert health.status.value in ["connected", "unauthorized", "error"]

    discovery = await connector.discover_site_structure()
    assert discovery["cms"] == "WordPress"

    patch = RemediationPatch(
        patch_id="PATCH-WP-01",
        finding_id="F-WP-01",
        title="Add JSON-LD Schema",
        category=Category.SCHEMA,
        risk_level=PatchRiskLevel.SAFE_AUTO,
        before_snippet="<!-- None -->",
        after_snippet='<script type="application/ld+json">{"@type": "Organization"}</script>',
        explanation="Inject Schema"
    )

    result = await connector.apply_patch(patch)
    assert result.success is True
    assert patch.approval_status == PatchApprovalStatus.APPLIED
    assert patch.applied_via == "wordpress"

    verify_res = await connector.verify_patch(patch)
    assert verify_res["verified"] is False
    assert verify_res["status"] == "PENDING_VERIFICATION"
    assert verify_res["citation_score_delta"] is None

@pytest.mark.asyncio
async def test_github_connector_flow():
    # Without token, authentication fails closed
    creds = ConnectorCredentials(
        provider=ConnectorType.GITHUB,
        repository="acme/marketing-site",
        branch="main"
    )
    connector = GitHubConnector(creds)
    health = await connector.test_connection()
    assert health.authenticated is False
    assert health.status.value == "unauthorized"

    discovery = await connector.discover_site_structure()
    assert discovery["detected_framework"] is None
    assert "GitHub token required" in discovery["structure_summary"]

    # When token is provided, framework discovery can proceed
    auth_creds = ConnectorCredentials(
        provider=ConnectorType.GITHUB,
        repository="acme/marketing-site",
        branch="main",
        github_token="ghp_mock_token_123"
    )
    auth_connector = GitHubConnector(auth_creds)
    auth_discovery = await auth_connector.discover_site_structure()
    assert auth_discovery["detected_framework"] is not None

    patch = RemediationPatch(
        patch_id="PATCH-GH-01",
        finding_id="F-GH-01",
        title="Update Root Layout Metadata",
        category=Category.TECHNICAL_SEO,
        risk_level=PatchRiskLevel.DEVELOPER_REQUIRED,
        target_file="src/app/layout.tsx",
        before_snippet="// old",
        after_snippet="export const metadata = { title: 'Acme' };",
        explanation="Next.js metadata update"
    )

    result = await connector.apply_patch(patch)
    assert result.success is True
    assert "pull" in result.pr_url
    assert patch.pr_number is not None

@pytest.mark.asyncio
async def test_api_connectors_and_remediation_routes():
    from app.api.routes.remediation.patches import _PATCH_REGISTRY
    from app.remediation.patch_engine import patch_engine

    # Generate and register patches for test_run_123
    test_findings = [
        Finding(
            finding_id="F-SEED-1",
            category=Category.SCHEMA,
            severity=Severity.HIGH,
            title="Missing Schema",
            description="Missing Schema on client portal",
            recommendation="Inject Organization JSON-LD",
            evidence=[FindingEvidence(element="head", value="none", snippet="<head></head>")]
        ),
        Finding(
            finding_id="F-SEED-2",
            category=Category.UX_CONVERSION,
            severity=Severity.MEDIUM,
            title="Unclear Hero",
            description="Hero lacks clear value prop",
            recommendation="Improve copy",
            evidence=[FindingEvidence(element="h1", value="Welcome", snippet="<h1>Welcome</h1>")]
        ),
        Finding(
            finding_id="F-SEED-3",
            category=Category.TECHNICAL_SEO,
            severity=Severity.LOW,
            title="Robots meta missing",
            description="Robots tag missing",
            recommendation="Add robots meta",
            evidence=[FindingEvidence(element="meta", value="none", snippet="")]
        )
    ]
    bp = BusinessProfile(business_name="Client Portal", niche="Enterprise Web")
    generated = patch_engine.generate_patches(
        findings=test_findings,
        business_profile=bp,
        website_url="https://client-portal.io"
    )
    for p in generated:
        p.metadata_payload["analysis_id"] = "test_run_123"
        _PATCH_REGISTRY[p.patch_id] = p

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Connectors List (zero fake seeded integrations)
        res1 = await ac.get("/api/v1/connectors")
        assert res1.status_code == 200
        integrations = res1.json()
        assert isinstance(integrations, list)

        # 2. Add Generic Website Connector
        res2 = await ac.post("/api/v1/connectors/connect", json={
            "provider": "generic",
            "name": "Live Client Portal",
            "target_url": "https://client-portal.io"
        })
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["success"] is True
        int_id = data2["integration"]["integration_id"]

        # 3. Test Health
        res3 = await ac.get(f"/api/v1/connectors/{int_id}/health")
        assert res3.status_code == 200

        # 4. Remediation Patches for a run
        res4 = await ac.get("/api/v1/remediation/patches/test_run_123")
        assert res4.status_code == 200
        patches_data = res4.json()
        assert patches_data["total_patches"] >= 3
        patch_id = patches_data["patches"][0]["patch_id"]

        # 5. Approve Patch
        res5 = await ac.post(f"/api/v1/remediation/patches/{patch_id}/approve", json={
            "approver": "test_officer@dristik.ai",
            "notes": "Verified for production"
        })
        assert res5.status_code == 200
        assert res5.json()["approval_status"] == "APPROVED"

        # 6. Apply Patch via integration
        res6 = await ac.post(f"/api/v1/remediation/patches/{patch_id}/apply", json={
            "integration_id": int_id
        })
        assert res6.status_code == 200
        assert res6.json()["success"] is True

        # 7. Verify Patch (evidence-first: pending live crawl verification)
        res7 = await ac.post(f"/api/v1/remediation/patches/{patch_id}/verify")
        assert res7.status_code == 200
        v_data = res7.json()
        assert v_data["status"] == "PENDING_VERIFICATION"
        assert v_data["score_delta"] is None

        # 8. ROI Estimation
        res8 = await ac.post("/api/v1/remediation/roi-estimate", json={
            "avg_deal_size_inr": 150000.0,
            "monthly_visitors": 25000,
            "current_conversion_rate": 0.02,
            "expected_traffic_lift_pct": 0.30,
            "expected_cro_lift_pct": 0.20
        })
        assert res8.status_code == 200
        roi_data = res8.json()
        assert roi_data["annual_upside_inr"] > 0
        assert roi_data["roi_multiple"] > 1.0

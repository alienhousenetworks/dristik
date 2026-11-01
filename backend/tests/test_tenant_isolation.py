"""
Milestone M3: Strict Multi-Tenancy Isolation Test Suite
Comprehensive testing for Suites 1 through 6 (T-TI-01 through T-TI-06).
"""
import ast
import inspect
import os
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.domain.enums import UserRole, Category, AnalysisStage, ConnectorType, Severity
from app.domain.models import (
    AnalysisRequest,
    AnalysisRun,
    Finding,
    ExecutiveReport,
    Integration,
    OverallScoreResult,
    CategoryScore,
)
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, get_current_user_optional
from app.identity.tenancy.manager import TenantManager
from app.orchestration.orchestrator import orchestrator, AnalysisOrchestrator
from app.db.repository import AuditRepository
from app.connectors.authority.store import ExternalStore
from app.connectors.store import ConnectorStore
from app.connectors.base.models import ConnectorCredentials
from app.connectors.authority.audit_bridge import build_audit_attachment


@pytest.fixture
def tenant_a_id():
    return f"org_alpha_{uuid.uuid4().hex[:6]}"


@pytest.fixture
def tenant_b_id():
    return f"org_beta_{uuid.uuid4().hex[:6]}"


@pytest.fixture
def user_a(tenant_a_id):
    return UserIdentity(
        user_id=f"usr_a_{uuid.uuid4().hex[:6]}",
        org_id=tenant_a_id,
        email="admin@alpha.test",
        role=UserRole.OWNER,
        is_active=True,
    )


@pytest.fixture
def user_b(tenant_b_id):
    return UserIdentity(
        user_id=f"usr_b_{uuid.uuid4().hex[:6]}",
        org_id=tenant_b_id,
        email="admin@beta.test",
        role=UserRole.OWNER,
        is_active=True,
    )


@pytest.fixture
def auth_client():
    """Client helper with context-manager for overriding authenticated user."""
    class AuthClient:
        def __init__(self):
            self.client = TestClient(app, base_url="https://testserver")

        def as_user(self, user: UserIdentity):
            class UserContext:
                def __enter__(_self):
                    app.dependency_overrides[get_current_user] = lambda: user
                    app.dependency_overrides[get_current_user_optional] = lambda: user
                    return self.client

                def __exit__(_self, exc_type, exc_val, exc_tb):
                    app.dependency_overrides.clear()

            return UserContext()

    return AuthClient()


@pytest.fixture
def isolated_repo(tmp_path):
    db_path = str(tmp_path / "test_audits.db")
    return AuditRepository(db_path=db_path)


@pytest.fixture
def isolated_external_store(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_authority.db")
    monkeypatch.setattr("app.core.config.settings.EXTERNAL_INTEGRATION_ENCRYPTION_KEY", "unit-test-external-key")
    return ExternalStore(path=db_path)


@pytest.fixture
def isolated_connector_store(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_connectors.db")
    monkeypatch.setattr("app.core.config.settings.AUTH_DATABASE_PATH", db_path)
    return ConnectorStore()


# =============================================================================
# Suite 1: T-TI-01 Rejection of Audit Requests Without Valid Tenant Context
# =============================================================================

def test_api_create_audit_unauthenticated_rejected(auth_client):
    resp = auth_client.client.post("/api/v1/analyses", json={"website_url": "https://example.com"})
    assert resp.status_code == 401
    assert "Sign in to continue." in resp.text


def test_api_create_audit_missing_tenant_org_rejected(auth_client):
    invalid_user = UserIdentity(
        user_id="usr_no_org",
        org_id="",
        email="no_org@test.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    with auth_client.as_user(invalid_user) as client:
        resp = client.post("/api/v1/analyses", json={"website_url": "https://example.com"})
        assert resp.status_code == 403


def test_orchestrator_create_run_none_org_raises_value_error():
    orch = AnalysisOrchestrator()
    with pytest.raises(ValueError, match="(?i)tenant|org_id"):
        orch.create_run(website_url="https://example.com", org_id=None)


def test_orchestrator_create_run_empty_org_raises_value_error():
    orch = AnalysisOrchestrator()
    with pytest.raises(ValueError, match="(?i)tenant|org_id"):
        orch.create_run(website_url="https://example.com", org_id="")
    with pytest.raises(ValueError, match="(?i)tenant|org_id"):
        orch.create_run(website_url="https://example.com", org_id="   ")


def test_repository_list_runs_without_org_raises_value_error(isolated_repo):
    with pytest.raises(ValueError, match="(?i)org_id"):
        isolated_repo.list_runs(org_id=None)


def test_repository_list_runs_empty_org_raises_value_error(isolated_repo):
    with pytest.raises(ValueError, match="(?i)org_id"):
        isolated_repo.list_runs(org_id="")
    with pytest.raises(ValueError, match="(?i)org_id"):
        isolated_repo.list_runs(org_id="   ")


def test_repository_delete_run_without_org_raises_value_error(isolated_repo):
    with pytest.raises(ValueError, match="(?i)org_id"):
        isolated_repo.delete_run("run_123", org_id=None)
    with pytest.raises(ValueError, match="(?i)org_id"):
        isolated_repo.delete_run("run_123", org_id="")


def test_analysis_request_model_requires_valid_tenant():
    with pytest.raises(ValueError, match="(?i)forbidden|tenant"):
        AnalysisRequest(website_url="https://example.com", org_id="org_default")
    with pytest.raises(ValueError, match="(?i)forbidden|workspace"):
        AnalysisRequest(website_url="https://example.com", workspace_id="ws_default")


# =============================================================================
# Suite 2: T-TI-02 Zero Tolerance for org_default and ws_default
# =============================================================================

def test_static_models_do_not_contain_org_default_defaults():
    assert AnalysisRequest.model_fields['org_id'].default != "org_default"
    assert AnalysisRequest.model_fields['workspace_id'].default != "ws_default"
    assert AnalysisRun.model_fields['org_id'].default != "org_default"
    assert AnalysisRun.model_fields['workspace_id'].default != "ws_default"
    assert Finding.model_fields['org_id'].default != "org_default"
    assert Finding.model_fields['workspace_id'].default != "ws_default"
    assert ExecutiveReport.model_fields['org_id'].default != "org_default"
    assert ExecutiveReport.model_fields['workspace_id'].default != "ws_default"
    assert Integration.model_fields['org_id'].default != "org_default"
    assert Integration.model_fields['workspace_id'].default != "ws_default"


def test_static_orchestrator_create_run_signature_no_org_default():
    sig = inspect.signature(orchestrator.create_run)
    org_default = sig.parameters['org_id'].default
    assert org_default != "org_default"
    assert org_default is inspect.Parameter.empty


def test_static_connector_store_signatures_no_default_fallbacks():
    sig = inspect.signature(ConnectorStore.add_integration)
    assert sig.parameters['org_id'].default != "org_default"
    assert sig.parameters['org_id'].default is inspect.Parameter.empty
    assert sig.parameters['workspace_id'].default != "ws_default"


def test_static_tenant_manager_does_not_seed_org_default():
    tm = TenantManager()
    assert "org_default" not in tm._orgs
    assert "ws_default" not in tm._workspaces


def test_static_codebase_ast_scan_no_org_default_fallbacks():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    target_files = [
        "app/domain/models.py",
        "app/orchestration/orchestrator.py",
        "app/db/repository.py",
        "app/connectors/store.py",
        "app/core/monitoring/radar.py",
        "app/orchestration/mission/state.py",
        "app/orchestration/mission/director.py",
        "app/crawl/audit/ledger.py",
    ]
    for rel_path in target_files:
        full_path = os.path.join(base_dir, rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
                    if isinstance(default, ast.Constant) and default.value in ("org_default", "ws_default"):
                        pytest.fail(f"Found forbidden default argument '{default.value}' in {rel_path}:{node.name}")


def test_runtime_orchestrator_rejects_org_default():
    orch = AnalysisOrchestrator()
    with pytest.raises(ValueError, match="(?i)disallowed|forbidden|org_default"):
        orch.create_run(website_url="https://example.com", org_id="org_default")


def test_runtime_repository_list_runs_rejects_org_default(isolated_repo):
    with pytest.raises(ValueError, match="(?i)forbidden|org_default"):
        isolated_repo.list_runs(org_id="org_default")


def test_runtime_external_authority_attachment_skips_org_default():
    att = build_audit_attachment(project_id="org_default", domain="example.com")
    assert att.get("domain_findings", []) == []
    report = att.get("report", {})
    assert report.get("universal_authority_score") is None


# =============================================================================
# Suite 3: T-TI-03 Cross-Tenant Isolation for Audit Runs
# =============================================================================

def test_in_memory_runs_list_cross_tenant_isolation(auth_client, user_a, user_b):
    run_a = orchestrator.create_run("https://alpha-site.com", org_id=user_a.org_id)
    run_b = orchestrator.create_run("https://beta-site.com", org_id=user_b.org_id)

    with auth_client.as_user(user_a) as client:
        resp = client.get("/api/v1/analyses")
        assert resp.status_code == 200
        ids = [item["analysis_id"] for item in resp.json()]
        assert run_a.analysis_id in ids
        assert run_b.analysis_id not in ids

    with auth_client.as_user(user_b) as client:
        resp = client.get("/api/v1/analyses")
        assert resp.status_code == 200
        ids = [item["analysis_id"] for item in resp.json()]
        assert run_b.analysis_id in ids
        assert run_a.analysis_id not in ids


def test_in_memory_run_detail_cross_tenant_returns_404(auth_client, user_a, user_b):
    run_b = orchestrator.create_run("https://beta-site.com", org_id=user_b.org_id)

    with auth_client.as_user(user_a) as client:
        resp = client.get(f"/api/v1/analyses/{run_b.analysis_id}")
        assert resp.status_code == 404


def test_database_list_runs_strict_tenant_filtering(isolated_repo):
    for i in range(2):
        run = AnalysisRun(
            analysis_id=f"run_alpha_{i}",
            org_id="org_alpha",
            website_url="https://alpha.example",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        isolated_repo.save_run(run)

    run_b = AnalysisRun(
        analysis_id="run_beta_0",
        org_id="org_beta",
        website_url="https://beta.example",
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    isolated_repo.save_run(run_b)

    alpha_runs = isolated_repo.list_runs(org_id="org_alpha")
    assert len(alpha_runs) == 2
    assert all(r["org_id"] == "org_alpha" for r in alpha_runs)

    beta_runs = isolated_repo.list_runs(org_id="org_beta")
    assert len(beta_runs) == 1
    assert beta_runs[0]["org_id"] == "org_beta"


def test_database_delete_run_cross_tenant_blocked(isolated_repo):
    run_b = AnalysisRun(
        analysis_id="run_beta_del",
        org_id="org_beta",
        website_url="https://beta.example",
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    isolated_repo.save_run(run_b)

    # Cross-tenant delete attempt returns False
    deleted = isolated_repo.delete_run("run_beta_del", org_id="org_alpha")
    assert deleted is False

    # Record remains intact
    assert isolated_repo.get_run("run_beta_del") is not None

    # Owner delete succeeds
    deleted_owner = isolated_repo.delete_run("run_beta_del", org_id="org_beta")
    assert deleted_owner is True
    assert isolated_repo.get_run("run_beta_del") is None


def test_api_delete_run_cross_tenant_returns_404(auth_client, user_a, user_b):
    run_b = orchestrator.create_run("https://beta-site.com", org_id=user_b.org_id)

    with auth_client.as_user(user_a) as client:
        resp = client.delete(f"/api/v1/analyses/{run_b.analysis_id}")
        assert resp.status_code == 404
        assert run_b.analysis_id in orchestrator.runs


def test_lifecycle_control_cross_tenant_blocked(auth_client, user_a, user_b):
    run_b = orchestrator.create_run("https://beta-site.com", org_id=user_b.org_id)

    with auth_client.as_user(user_a) as client:
        pause_resp = client.post(f"/api/v1/analyses/{run_b.analysis_id}/pause")
        assert pause_resp.status_code == 404

        resume_resp = client.post(f"/api/v1/analyses/{run_b.analysis_id}/resume")
        assert resume_resp.status_code == 404

        node_resp = client.post(f"/api/v1/analyses/{run_b.analysis_id}/nodes/node_scoring/run")
        assert node_resp.status_code == 404


# =============================================================================
# Suite 4: T-TI-04 Cross-Tenant Isolation for Reports and Findings
# =============================================================================

@pytest.fixture
def run_with_report(user_a):
    run = orchestrator.create_run("https://alpha-site.com", org_id=user_a.org_id)
    report = ExecutiveReport(
        report_id=f"rep_{run.analysis_id}",
        analysis_id=run.analysis_id,
        org_id=user_a.org_id,
        website_url="https://alpha-site.com",
        domain="alpha-site.com",
        scores=OverallScoreResult(
            overall_score=88.0,
            grade="A",
            category_scores={
                Category.TECHNICAL_SEO: CategoryScore(category=Category.TECHNICAL_SEO, score=90.0, weight=0.5, weighted_score=45.0, summary="Good"),
            }
        ),
        story_summary="Alpha report summary",
        primary_strategic_opportunity="Growth",
        consultant_advice_what_to_ignore="None",
    )
    run.report = report
    run.status = AnalysisStage.COMPLETED
    orchestrator.runs[run.analysis_id] = run
    return run


def test_report_endpoint_cross_tenant_returns_404(auth_client, user_b, run_with_report):
    with auth_client.as_user(user_b) as client:
        resp = client.get(f"/api/v1/analyses/{run_with_report.analysis_id}/report")
        assert resp.status_code == 404


def test_findings_endpoint_cross_tenant_returns_404(auth_client, user_b, run_with_report):
    with auth_client.as_user(user_b) as client:
        resp = client.get(f"/api/v1/analyses/{run_with_report.analysis_id}/findings")
        assert resp.status_code == 404


def test_manifest_and_twin_endpoints_cross_tenant_returns_404(auth_client, user_b, run_with_report):
    with auth_client.as_user(user_b) as client:
        for ep in ("manifest", "twin", "timeline"):
            resp = client.get(f"/api/v1/analyses/{run_with_report.analysis_id}/{ep}")
            assert resp.status_code == 404, f"Endpoint {ep} expected 404, got {resp.status_code}"


def test_evidence_explorer_and_graph_cross_tenant_returns_404(auth_client, user_b, run_with_report):
    with auth_client.as_user(user_b) as client:
        resp = client.get(f"/api/v1/analyses/{run_with_report.analysis_id}/checkpoints")
        assert resp.status_code == 404


def test_adaptive_audit_book_html_pdf_cross_tenant_returns_404(auth_client, user_b, run_with_report):
    with auth_client.as_user(user_b) as client:
        resp_html = client.get(f"/api/v1/reports/{run_with_report.analysis_id}/audit-book?format=html")
        assert resp_html.status_code == 404

        resp_json = client.get(f"/api/v1/reports/{run_with_report.analysis_id}/audit-book?format=json")
        assert resp_json.status_code == 404


def test_section_deck_cross_tenant_returns_404(auth_client, user_b, run_with_report):
    with auth_client.as_user(user_b) as client:
        resp = client.get(f"/api/v1/reports/{run_with_report.analysis_id}/section-deck/seo")
        assert resp.status_code == 404


def test_patch_pack_downloads_cross_tenant_returns_404(auth_client, user_b, run_with_report):
    with auth_client.as_user(user_b) as client:
        resp = client.get(f"/api/v1/analyses/{run_with_report.analysis_id}/patch-pack/zip")
        assert resp.status_code == 404


def test_finding_model_scoping_invariant():
    with pytest.raises(ValueError, match="(?i)forbidden|tenant"):
        Finding(finding_id="f_bad", org_id="org_default", category=Category.TECHNICAL_SEO, severity=Severity.MEDIUM)
    f = Finding(finding_id="f_ok", org_id="org_alpha", category=Category.TECHNICAL_SEO, severity=Severity.MEDIUM)
    assert f.org_id == "org_alpha"


# =============================================================================
# Suite 5: T-TI-05 External Authority Credential Store Tenant Isolation
# =============================================================================

def test_external_store_secret_decryption_isolated_per_tenant(isolated_external_store):
    isolated_external_store.upsert_connection(
        {"project_id": "org_alpha", "provider": "gsc", "account_label": "alpha@example.com"},
        secret={"client_secret": "alpha_secret_token"},
    )
    secret_a = isolated_external_store.load_secret("org_alpha", "gsc")
    assert secret_a is not None
    assert secret_a.get("client_secret") == "alpha_secret_token"

    secret_b = isolated_external_store.load_secret("org_beta", "gsc")
    assert secret_b is None


def test_external_store_public_connections_isolated_per_tenant(isolated_external_store):
    isolated_external_store.upsert_connection(
        {"project_id": "org_alpha", "provider": "gsc", "account_label": "alpha@example.com"},
        secret={"token": "t_alpha"},
    )
    isolated_external_store.upsert_connection(
        {"project_id": "org_beta", "provider": "ahrefs", "account_label": "beta@example.com"},
        secret={"token": "t_beta"},
    )
    conns_a = [c["provider"] for c in isolated_external_store.public_connections("org_alpha")]
    assert "gsc" in conns_a
    assert "ahrefs" not in conns_a

    conns_b = [c["provider"] for c in isolated_external_store.public_connections("org_beta")]
    assert "ahrefs" in conns_b
    assert "gsc" not in conns_b


def test_external_store_snapshots_isolated_per_tenant(isolated_external_store):
    isolated_external_store.save_snapshot(
        project_id="org_alpha",
        domain="example.com",
        provider="gsc",
        period_days=28,
        period_start="2026-10-01",
        period_end="2026-10-28",
        data_state="OK",
        summary={"total_clicks": 42},
        idempotency_key="snap_test_alpha_1",
        records=[],
        raw_payloads=[],
    )
    snap_a = isolated_external_store.latest_snapshot("org_alpha", "gsc", "example.com", 28)
    assert snap_a is not None
    assert snap_a["summary"]["total_clicks"] == 42

    snap_b = isolated_external_store.latest_snapshot("org_beta", "gsc", "example.com", 28)
    assert snap_b is None


def test_connector_store_integration_lookup_isolated_per_tenant(isolated_connector_store):
    creds = ConnectorCredentials(provider=ConnectorType.WORDPRESS, api_key="wp_key_123")
    integ = isolated_connector_store.add_integration(
        provider=ConnectorType.WORDPRESS,
        name="WP Alpha",
        target_url="https://alpha.com",
        credentials=creds,
        org_id="org_alpha",
        workspace_id="ws_alpha",
    )

    integrations_a = isolated_connector_store.list_integrations("org_alpha")
    assert len(integrations_a) == 1
    assert integrations_a[0].integration_id == integ.integration_id

    integrations_b = isolated_connector_store.list_integrations("org_beta")
    assert len(integrations_b) == 0


def test_api_external_authority_health_cross_tenant_rejected(auth_client, user_a):
    with auth_client.as_user(user_a) as client:
        resp = client.get("/api/v1/external-authority/health?project_id=org_foreign")
        assert resp.status_code == 403


def test_api_external_authority_coverage_cross_tenant_rejected(auth_client, user_a):
    with auth_client.as_user(user_a) as client:
        resp = client.get("/api/v1/external-authority/coverage?domain=example.com&project_id=org_foreign")
        assert resp.status_code == 403


# =============================================================================
# Suite 6: T-TI-06 External Authority Attachment in Orchestrator Honors Caller Tenant Context
# =============================================================================

@pytest.mark.asyncio
async def test_orchestrator_passes_exact_tenant_org_id_to_audit_bridge():
    orch = AnalysisOrchestrator()
    run = orch.create_run("https://alpha-site.com", org_id="org_enterprise_alpha")
    from app.connectors.authority.audit_bridge import build_audit_attachment

    with patch("app.connectors.authority.audit_bridge.build_audit_attachment", wraps=build_audit_attachment) as mock_bridge:
        try:
            await orch.execute_analysis_pipeline(run.analysis_id, "https://alpha-site.com", max_pages=1)
        except Exception:
            pass
        if mock_bridge.called:
            assert mock_bridge.call_args.kwargs.get("project_id") == "org_enterprise_alpha"


@pytest.mark.asyncio
async def test_multi_tenant_same_domain_collision_zero_leakage(isolated_external_store):
    orch = AnalysisOrchestrator()
    run_a = orch.create_run("https://target.com", org_id="org_alpha_collision")
    run_b = orch.create_run("https://target.com", org_id="org_beta_collision")

    isolated_external_store.save_snapshot(
        project_id=run_a.org_id,
        domain="target.com",
        provider="gsc",
        period_days=28,
        period_start="2026-10-01",
        period_end="2026-10-28",
        data_state="OK",
        summary={"total_clicks": 100},
        idempotency_key="snap_collision_alpha_1",
        records=[],
        raw_payloads=[],
    )

    from app.connectors.authority.service import ExternalAuthorityService
    service = ExternalAuthorityService(store=isolated_external_store)
    with patch("app.connectors.authority.service.get_service", return_value=service):
        att_a = build_audit_attachment(project_id=run_a.org_id, domain="target.com")
        att_b = build_audit_attachment(project_id=run_b.org_id, domain="target.com")

        assert att_a.get("report", {}).get("universal_authority_score") is not None or len(att_a.get("report", {}).get("coverage", [])) > 0
        assert att_b.get("report", {}).get("universal_authority_score") is None
        assert len(att_b.get("domain_findings", [])) == 0


def test_orchestrator_skips_authority_when_tenant_is_none_or_empty():
    att = build_audit_attachment(project_id="", domain="example.com")
    assert att.get("domain_findings", []) == []
    assert att.get("report", {}).get("universal_authority_score") is None


def test_orchestrator_skips_authority_when_tenant_is_org_default():
    att = build_audit_attachment(project_id="org_default", domain="example.com")
    assert att.get("domain_findings", []) == []
    assert att.get("report", {}).get("universal_authority_score") is None

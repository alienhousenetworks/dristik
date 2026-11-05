## 2026-10-31T21:27:04Z
You are worker_m3_1, a teamwork_preview_worker.
Working directory: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/worker_m3_1
Project root: /Users/sayantande/Downloads/dristik-main
Original Request: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/ORIGINAL_REQUEST.md
Scope document: /Users/sayantande/Downloads/dristik-main/PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task is to implement Milestone M3 (Phase 1: Strict Multi-Tenancy Isolation & Tenant Scoping, Elimination of org_default and ws_default):

1. Review the input blueprints and specifications:
   - Domain & Orchestrator blueprint: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m3_1/strategy_scoping.md
   - API & Credential Isolation blueprint: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m3_2/strategy_api_isolation.md
   - Comprehensive Test blueprint: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m3_3/test_blueprint_m3.md
   - Handoff reports in explorer_m3_1/handoff.md, explorer_m3_2/handoff.md, and spec_miner_m3_3/handoff.md.

2. Exclusive Write Ownership:
   You own and may edit ONLY the following files:
   - backend/app/domain/models.py
   - backend/app/orchestration/orchestrator.py
   - backend/app/db/repository.py
   - backend/app/api/routes/integrations/google.py
   - backend/app/api/routes/integrations/connectors.py
   - backend/app/api/routes/integrations/external_authority.py
   - backend/app/api/routes/platform/workspaces.py
   - backend/app/identity/access.py
   - backend/app/identity/deps.py
   - backend/app/connectors/store.py
   - backend/app/identity/tenancy/manager.py
   - backend/app/core/monitoring/radar.py
   - backend/app/orchestration/mission/state.py
   - backend/app/orchestration/mission/director.py
   - backend/app/crawl/audit/ledger.py
   - backend/tests/test_tenant_isolation.py
   - backend/tests/test_audit_persistence_and_restore.py
   - backend/tests/test_selective_pillars.py
   - backend/tests/test_pipeline.py
   - backend/tests/test_multi_page.py
   - backend/tests/test_scoring_timing_and_honest_flag.py
   - backend/tests/test_visual_ux_and_analytics_connectors.py
   - backend/tests/test_google_connectors.py
   - backend/tests/test_mission_director.py
   - backend/tests/test_radar_pulse.py

3. Implementation Steps:
   A. In backend/app/domain/models.py:
      - In Integration: remove default org_id and workspace_id; validate non-empty string and reject 'org_default'.
      - In Finding: change org_id and workspace_id to Optional[str] = None (preserves backward compatibility for 300+ heuristic unit tests; validator rejects 'org_default' if passed).
      - In ExecutiveReport: require non-empty org_id: str without default.
      - In AnalysisRequest: org_id, workspace_id, project_id as Optional[str] = None (resolved from auth session in API handlers).
      - In AnalysisRun: require org_id: str without default, add validator rejecting 'org_default' and 'default'.
   B. In backend/app/orchestration/orchestrator.py:
      - In create_run: make org_id: str mandatory without default; reject empty or 'org_default'.
      - In execute_analysis_pipeline: fail-fast if not run.org_id or run.org_id == 'org_default'.
      - In resume_analysis_pipeline (line 2751): pass org_id=stored["org_id"] from persistence.
      - In line 349: pass run.org_id and run.workspace_id to create_mission.
      - In line 1533-1572: external authority attachment strictly honors run.org_id and skips if org_id is missing or 'org_default'.
   C. In backend/app/db/repository.py:
      - In list_runs: require mandatory org_id: str (reject None, empty, or 'org_default' with ValueError).
      - In get_run: add optional org_id: Optional[str] = None verifying ownership.
      - In delete_run: require mandatory org_id: str; reject cross-tenant deletion with ValueError or return False.
   D. In backend/app/api/routes/:
      - In google.py: replace get_current_user_optional with get_current_user in get_integrations_status (line 43) and probe_ga4_status (line 175).
      - In connectors.py: remove 'org_default' and 'ws_default' defaults; bind to user.org_id and ws_default_{user.org_id}; enforce 403 on unauthorized cross-tenant operations.
      - In external_authority.py (line 99): raise HTTPException(status_code=403, detail='Cross-tenant access forbidden') when requested != user.org_id and caller is not system admin.
      - In workspaces.py (_owned_workspace): raise HTTPException(status_code=403, detail='Cross-tenant workspace access forbidden') if workspace exists but belongs to foreign org.
   E. In backend/app/identity/access.py and deps.py:
      - Implement and export require_org_context(user, org_id) raising 401 if unauthenticated and 403 if invalid or cross-tenant.
   F. In backend/app/connectors/store.py:
      - In list_integrations and add_integration: require non-empty org_id: str, reject 'org_default'.
   G. In backend/app/identity/tenancy/manager.py:
      - Clean initialization without pre-seeding 'org_default' / 'ws_default'.
   H. In backend/app/core/monitoring/radar.py, mission/state.py, director.py, ledger.py:
      - Remove 'org_default' and 'ws_default' defaults; require explicit tenant IDs.
   I. In backend/tests/test_tenant_isolation.py:
      - Implement the comprehensive test suite specified in test_blueprint_m3.md (Suites 1 through 6: T-TI-01 through T-TI-06).
   J. Update existing test callers that previously omitted org_id:
      - test_audit_persistence_and_restore.py, test_selective_pillars.py, test_pipeline.py, test_multi_page.py, test_scoring_timing_and_honest_flag.py, test_visual_ux_and_analytics_connectors.py, test_google_connectors.py, test_mission_director.py, test_radar_pulse.py: provide explicit test tenant ID (e.g. 'test_org_01', 'ws_test_01').

4. Verification:
   - Run `pytest backend/tests/test_tenant_isolation.py -v` (100% pass)
   - Run `pytest backend/tests/security/test_tenant_isolation.py -v` (100% pass)
   - Run `pytest backend/tests/test_db_session_and_fail_fast.py backend/tests/test_audit_persistence_and_checkpoints.py backend/tests/test_enterprise_schema_and_cas.py backend/tests/test_external_authority.py backend/tests/test_audit_persistence_and_restore.py backend/tests/test_scoring_timing_and_honest_flag.py -v`
   - Run `pytest backend/tests/test_selective_pillars.py backend/tests/test_pipeline.py backend/tests/test_multi_page.py backend/tests/test_visual_ux_and_analytics_connectors.py backend/tests/test_google_connectors.py backend/tests/test_mission_director.py backend/tests/test_radar_pulse.py -v`
   - Run flake8 / syntax checks on modified files.
   - Ensure 100% test pass rate across all suites.

5. Deliverables:
   - Implementation report: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/worker_m3_1/implementation_report.md
   - Complete handoff.md following the Handoff Protocol.
   - Report completion to parent via send_message.

## 2026-10-31T21:12:34Z
You are spec_miner_m3_3, a teamwork_preview_spec_miner.
Working directory: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m3_3
Project root: /Users/sayantande/Downloads/dristik-main
Original Request: /Users/sayantande/Downloads/dristik-main/.agents/teamwork/ORIGINAL_REQUEST.md
Scope document: /Users/sayantande/Downloads/dristik-main/PROJECT.md

Your task is to formulate the comprehensive test specification for Milestone M3 Strict Multi-Tenancy Isolation:
1. Read /Users/sayantande/Downloads/dristik-main/.agents/teamwork/ORIGINAL_REQUEST.md and /Users/sayantande/Downloads/dristik-main/PROJECT.md.
2. Design specific, exhaustive test cases for backend/tests/test_tenant_isolation.py:
   - T-TI-01: Rejection of audit requests without valid tenant context (missing org_id / workspace_id returns 403 Forbidden or ValueError).
   - T-TI-02: Zero tolerance for org_default / ws_default: static and runtime assertions that neither string exists as a default or fallback.
   - T-TI-03: Cross-tenant isolation for audit runs: tenant A cannot query, view, or modify tenant B's audit runs (returns 403 Forbidden or 404/empty depending on spec).
   - T-TI-04: Cross-tenant isolation for reports and findings: reports generated under tenant A are strictly unreachable by tenant B.
   - T-TI-05: External authority credential store tenant isolation: provider credentials/tokens belonging to tenant A are isolated from tenant B.
   - T-TI-06: External authority attachment in orchestrator honors caller tenant context.
3. Output test blueprint to /Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m3_3/test_blueprint_m3.md and handoff.md.
4. Report completion to parent via send_message.
Do NOT edit source code files. You are read-only.

"""Canonical Tenant-Isolated Relational Store for Enterprise GEO (`GEOStore`).

Mirrors Dristik's enterprise SQLite/PostgreSQL pattern (`app/db/cro_schema.py` and
`app/db/seo_orchestrator_schema.py`) with strict `tenant_id` scoping on every query,
immutable CAS snapshot references (`storage_cas.py`), idempotency keys, agent
execution checkpointing, and encrypted provider credential storage (never returned
in plaintext to callers).
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

from app.db.storage_cas import get_cas_storage
from app.geo.models import (
    GEOAudit,
    GEOAuditScope,
    GEOCitation,
    GEOEntity,
    GEOExperiment,
    GEOExternalSource,
    GEOFinding,
    GEOMention,
    GEOModelVersion,
    GEOMonitoringAlert,
    GEOMonitoringSchedule,
    GEOPageReadiness,
    GEOPlatform,
    GEOPromptRun,
    GEOProviderConnection,
    GEORecommendation,
    GEORemediationPack,
    GEORemediationTask,
    GEOReport,
    GEOResponse,
    GEOSnapshot,
    GEOTestPrompt,
    GEOVerification,
)

T = TypeVar("T", bound=BaseModel)

GEO_SQLITE_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS geo_audit_scopes (
    scope_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    domain TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_scopes_tenant_audit ON geo_audit_scopes(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_audits (
    audit_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    website_url TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'standard',
    status TEXT NOT NULL DEFAULT 'queued',
    publication_status TEXT NOT NULL DEFAULT 'DRAFT',
    current_stage TEXT NOT NULL DEFAULT 'init',
    observed_performance_score REAL,
    readiness_score REAL,
    qa_status TEXT NOT NULL DEFAULT 'pending',
    idempotency_key TEXT,
    methodology_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_audits_tenant_domain ON geo_audits(tenant_id, domain);
CREATE INDEX IF NOT EXISTS idx_geo_audits_tenant_idem ON geo_audits(tenant_id, idempotency_key);

CREATE TABLE IF NOT EXISTS geo_platforms (
    record_key TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_platforms_tenant_audit ON geo_platforms(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_model_versions (
    version_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    platform_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_modver_tenant_audit ON geo_model_versions(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_test_prompts (
    prompt_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    category TEXT NOT NULL,
    is_branded INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    approval_status TEXT NOT NULL DEFAULT 'approved',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_prompts_tenant_audit ON geo_test_prompts(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_prompt_runs (
    run_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    status TEXT NOT NULL,
    repetition_number INTEGER NOT NULL DEFAULT 1,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_runs_tenant_audit ON geo_prompt_runs(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_responses (
    response_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    response_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_responses_tenant_audit ON geo_responses(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_mentions (
    mention_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    response_id TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    mention_type TEXT NOT NULL,
    is_target_brand INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_mentions_tenant_audit ON geo_mentions(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_citations (
    citation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    response_id TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    source_ownership TEXT NOT NULL DEFAULT 'unknown',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_citations_tenant_audit ON geo_citations(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_entities (
    entity_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    entity_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    attribute TEXT NOT NULL,
    fact_status TEXT NOT NULL DEFAULT 'unknown',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_entities_tenant_audit ON geo_entities(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_external_sources (
    source_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    source_category TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_sources_tenant_audit ON geo_external_sources(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_pages (
    page_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    url TEXT NOT NULL,
    page_type TEXT NOT NULL DEFAULT 'general',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_pages_tenant_audit ON geo_pages(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_findings (
    finding_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_findings_tenant_audit ON geo_findings(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_recommendations (
    recommendation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    priority_score REAL NOT NULL DEFAULT 50.0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_recs_tenant_audit ON geo_recommendations(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_remediation_packs (
    pack_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_packs_tenant_audit ON geo_remediation_packs(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_remediation_tasks (
    task_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    pack_id TEXT,
    department TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'P1',
    status TEXT NOT NULL DEFAULT 'open',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_tasks_tenant_audit ON geo_remediation_tasks(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_verifications (
    verification_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    task_id TEXT NOT NULL,
    overall_status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_verifs_tenant_task ON geo_verifications(tenant_id, task_id);

CREATE TABLE IF NOT EXISTS geo_experiments (
    experiment_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_exps_tenant_audit ON geo_experiments(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    snapshot_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_snaps_tenant_audit ON geo_snapshots(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_monitoring_schedules (
    schedule_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    cadence TEXT NOT NULL DEFAULT 'weekly',
    enabled INTEGER NOT NULL DEFAULT 1,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_sched_tenant ON geo_monitoring_schedules(tenant_id, domain);

CREATE TABLE IF NOT EXISTS geo_monitoring_alerts (
    alert_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    domain TEXT NOT NULL,
    severity TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_alerts_tenant ON geo_monitoring_alerts(tenant_id, domain);

CREATE TABLE IF NOT EXISTS geo_reports (
    report_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    profile TEXT NOT NULL,
    format TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_reports_tenant_audit ON geo_reports(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_provider_connections (
    connection_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    encrypted_secret TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(tenant_id, platform_id)
);
CREATE INDEX IF NOT EXISTS idx_geo_conns_tenant ON geo_provider_connections(tenant_id, platform_id);

CREATE TABLE IF NOT EXISTS geo_agent_executions (
    execution_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    department TEXT NOT NULL,
    status TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    elapsed_sec REAL NOT NULL DEFAULT 0.0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_exec_tenant_audit ON geo_agent_executions(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS geo_artifacts (
    artifact_key TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_art_tenant_audit ON geo_artifacts(tenant_id, audit_id);
"""


def _default_geo_db_path() -> str:
    env_path = os.getenv("DRISTIK_GEO_DB_PATH")
    if env_path:
        return env_path
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "geo_enterprise.db")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class GEOStore:
    """Tenant-isolated relational store for all canonical GEO entities and CAS snapshots."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _default_geo_db_path()
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(GEO_SQLITE_SCHEMA)
            conn.commit()

    @staticmethod
    def _load(model_cls: Type[T], row: Optional[sqlite3.Row]) -> Optional[T]:
        if not row:
            return None
        return model_cls.model_validate_json(row["payload_json"])

    # ── Scope & Audit ────────────────────────────────────────────────────────

    def save_scope(self, scope: GEOAuditScope) -> GEOAuditScope:
        scope.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_audit_scopes
                   (scope_id, tenant_id, audit_id, domain, brand_name, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scope.scope_id,
                    scope.tenant_id,
                    scope.audit_id,
                    scope.domain,
                    scope.brand_name,
                    scope.model_dump_json(),
                    scope.created_at,
                    scope.updated_at,
                ),
            )
            conn.commit()
        return scope

    def get_scope(self, tenant_id: str, scope_id: str) -> Optional[GEOAuditScope]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_audit_scopes WHERE tenant_id = ? AND scope_id = ?",
                (tenant_id, scope_id),
            ).fetchone()
        return self._load(GEOAuditScope, row)

    def save_audit(self, audit: GEOAudit) -> GEOAudit:
        audit.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_audits
                   (audit_id, tenant_id, domain, website_url, brand_name, mode, status,
                    publication_status, current_stage, observed_performance_score, readiness_score,
                    qa_status, idempotency_key, methodology_version, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    audit.audit_id,
                    audit.tenant_id,
                    audit.domain,
                    audit.website_url,
                    audit.brand_name,
                    audit.mode,
                    audit.status,
                    audit.publication_status,
                    audit.current_stage,
                    audit.observed_performance_score,
                    audit.readiness_score,
                    audit.qa_status,
                    audit.idempotency_key,
                    audit.methodology_version,
                    audit.model_dump_json(),
                    audit.created_at,
                    audit.updated_at,
                ),
            )
            conn.commit()
        return audit

    def get_audit(self, tenant_id: str, audit_id: str) -> Optional[GEOAudit]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_audits WHERE tenant_id = ? AND audit_id = ?",
                (tenant_id, audit_id),
            ).fetchone()
        return self._load(GEOAudit, row)

    def find_audit_by_idempotency(self, tenant_id: str, idempotency_key: str) -> Optional[GEOAudit]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_audits WHERE tenant_id = ? AND idempotency_key = ? ORDER BY created_at DESC LIMIT 1",
                (tenant_id, idempotency_key),
            ).fetchone()
        return self._load(GEOAudit, row)

    def list_audits(self, tenant_id: str, domain: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[GEOAudit]:
        with self._conn() as conn:
            if domain:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_audits WHERE tenant_id = ? AND domain = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (tenant_id, domain, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_audits WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (tenant_id, limit, offset),
                ).fetchall()
        return [GEOAudit.model_validate_json(r["payload_json"]) for r in rows]

    # ── Platforms & Model Versions ───────────────────────────────────────────

    def save_platform(self, platform: GEOPlatform) -> GEOPlatform:
        platform.updated_at = _now_iso()
        rec_key = f"{platform.audit_id}:{platform.platform_id}"
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_platforms
                   (record_key, tenant_id, audit_id, platform_id, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    rec_key,
                    platform.tenant_id,
                    platform.audit_id or "",
                    platform.platform_id,
                    platform.model_dump_json(),
                    platform.created_at,
                    platform.updated_at,
                ),
            )
            conn.commit()
        return platform

    def list_platforms(self, tenant_id: str, audit_id: str) -> List[GEOPlatform]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM geo_platforms WHERE tenant_id = ? AND audit_id = ? ORDER BY platform_id ASC",
                (tenant_id, audit_id),
            ).fetchall()
        return [GEOPlatform.model_validate_json(r["payload_json"]) for r in rows]

    def save_model_version(self, mv: GEOModelVersion) -> GEOModelVersion:
        mv.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_model_versions
                   (version_id, tenant_id, audit_id, platform_id, model_name, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    mv.version_id,
                    mv.tenant_id,
                    mv.audit_id,
                    mv.platform_id,
                    mv.model_name,
                    mv.model_dump_json(),
                    mv.created_at,
                    mv.updated_at,
                ),
            )
            conn.commit()
        return mv

    def list_model_versions(self, tenant_id: str, audit_id: Optional[str] = None) -> List[GEOModelVersion]:
        with self._conn() as conn:
            if audit_id:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_model_versions WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at ASC",
                    (tenant_id, audit_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_model_versions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 100",
                    (tenant_id,),
                ).fetchall()
        return [GEOModelVersion.model_validate_json(r["payload_json"]) for r in rows]

    # ── Prompts, Runs, Responses, Mentions, Citations ────────────────────────

    def save_prompt(self, prompt: GEOTestPrompt) -> GEOTestPrompt:
        prompt.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_test_prompts
                   (prompt_id, tenant_id, audit_id, category, is_branded, version, approval_status, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    prompt.prompt_id,
                    prompt.tenant_id,
                    prompt.audit_id,
                    prompt.category.value,
                    1 if prompt.is_branded else 0,
                    prompt.version,
                    prompt.approval_status,
                    prompt.model_dump_json(),
                    prompt.created_at,
                    prompt.updated_at,
                ),
            )
            conn.commit()
        return prompt

    def list_prompts(
        self,
        tenant_id: str,
        audit_id: Optional[str] = None,
        is_branded: Optional[bool] = None,
        approval_status: Optional[str] = None,
    ) -> List[GEOTestPrompt]:
        clauses = ["tenant_id = ?"]
        params: List[Any] = [tenant_id]
        if audit_id is not None:
            clauses.append("audit_id = ?")
            params.append(audit_id)
        if is_branded is not None:
            clauses.append("is_branded = ?")
            params.append(1 if is_branded else 0)
        if approval_status is not None:
            clauses.append("approval_status = ?")
            params.append(approval_status)
        sql = f"SELECT payload_json FROM geo_test_prompts WHERE {' AND '.join(clauses)} ORDER BY created_at ASC"
        with self._conn() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [GEOTestPrompt.model_validate_json(r["payload_json"]) for r in rows]

    def get_prompt(self, tenant_id: str, prompt_id: str) -> Optional[GEOTestPrompt]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_test_prompts WHERE tenant_id = ? AND prompt_id = ?",
                (tenant_id, prompt_id),
            ).fetchone()
        return self._load(GEOTestPrompt, row)

    def save_prompt_run(self, run: GEOPromptRun) -> GEOPromptRun:
        run.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_prompt_runs
                   (run_id, tenant_id, audit_id, prompt_id, platform_id, status, repetition_number, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.run_id,
                    run.tenant_id,
                    run.audit_id or "",
                    run.prompt_id,
                    run.platform_id,
                    run.status.value,
                    run.repetition_number,
                    run.model_dump_json(),
                    run.created_at,
                    run.updated_at,
                ),
            )
            conn.commit()
        return run

    def list_prompt_runs(self, tenant_id: str, audit_id: str) -> List[GEOPromptRun]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM geo_prompt_runs WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at ASC",
                (tenant_id, audit_id),
            ).fetchall()
        return [GEOPromptRun.model_validate_json(r["payload_json"]) for r in rows]

    def save_response(self, resp: GEOResponse) -> GEOResponse:
        resp.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_responses
                   (response_id, tenant_id, audit_id, run_id, prompt_id, platform_id, response_hash, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    resp.response_id,
                    resp.tenant_id,
                    resp.audit_id or "",
                    resp.run_id,
                    resp.prompt_id,
                    resp.platform_id,
                    resp.response_hash,
                    resp.model_dump_json(),
                    resp.created_at,
                    resp.updated_at,
                ),
            )
            conn.commit()
        return resp

    def list_responses(self, tenant_id: str, audit_id: str, platform_id: Optional[str] = None) -> List[GEOResponse]:
        with self._conn() as conn:
            if platform_id:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_responses WHERE tenant_id = ? AND audit_id = ? AND platform_id = ? ORDER BY created_at ASC",
                    (tenant_id, audit_id, platform_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_responses WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at ASC",
                    (tenant_id, audit_id),
                ).fetchall()
        return [GEOResponse.model_validate_json(r["payload_json"]) for r in rows]

    def save_mention(self, mention: GEOMention) -> GEOMention:
        mention.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_mentions
                   (mention_id, tenant_id, audit_id, response_id, prompt_id, platform_id, mention_type, is_target_brand, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    mention.mention_id,
                    mention.tenant_id,
                    mention.audit_id or "",
                    mention.response_id,
                    mention.prompt_id,
                    mention.platform_id,
                    mention.mention_type.value,
                    1 if mention.is_target_brand else 0,
                    mention.model_dump_json(),
                    mention.created_at,
                    mention.updated_at,
                ),
            )
            conn.commit()
        return mention

    def list_mentions(self, tenant_id: str, audit_id: str) -> List[GEOMention]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM geo_mentions WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at ASC",
                (tenant_id, audit_id),
            ).fetchall()
        return [GEOMention.model_validate_json(r["payload_json"]) for r in rows]

    def save_citation(self, citation: GEOCitation) -> GEOCitation:
        citation.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_citations
                   (citation_id, tenant_id, audit_id, response_id, prompt_id, platform_id, domain, source_ownership, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    citation.citation_id,
                    citation.tenant_id,
                    citation.audit_id or "",
                    citation.response_id,
                    citation.prompt_id,
                    citation.platform_id,
                    citation.domain,
                    citation.source_ownership.value,
                    citation.model_dump_json(),
                    citation.created_at,
                    citation.updated_at,
                ),
            )
            conn.commit()
        return citation

    def list_citations(self, tenant_id: str, audit_id: str, platform_id: Optional[str] = None) -> List[GEOCitation]:
        with self._conn() as conn:
            if platform_id:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_citations WHERE tenant_id = ? AND audit_id = ? AND platform_id = ? ORDER BY created_at ASC",
                    (tenant_id, audit_id, platform_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_citations WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at ASC",
                    (tenant_id, audit_id),
                ).fetchall()
        return [GEOCitation.model_validate_json(r["payload_json"]) for r in rows]

    # ── Entities, External Sources, Pages ────────────────────────────────────

    def save_entity(self, entity: GEOEntity) -> GEOEntity:
        entity.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_entities
                   (entity_id, tenant_id, audit_id, entity_type, entity_name, attribute, fact_status, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entity.entity_id,
                    entity.tenant_id,
                    entity.audit_id,
                    entity.entity_type,
                    entity.entity_name,
                    entity.attribute,
                    entity.fact_status.value,
                    entity.model_dump_json(),
                    entity.created_at,
                    entity.updated_at,
                ),
            )
            conn.commit()
        return entity

    def get_entity(self, tenant_id: str, entity_id: str) -> Optional[GEOEntity]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_entities WHERE tenant_id = ? AND entity_id = ?",
                (tenant_id, entity_id),
            ).fetchone()
        return self._load(GEOEntity, row)

    def list_entities(self, tenant_id: str, audit_id: Optional[str] = None) -> List[GEOEntity]:
        with self._conn() as conn:
            if audit_id:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_entities WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at ASC",
                    (tenant_id, audit_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_entities WHERE tenant_id = ? ORDER BY updated_at DESC",
                    (tenant_id,),
                ).fetchall()
        return [GEOEntity.model_validate_json(r["payload_json"]) for r in rows]

    def save_external_source(self, source: GEOExternalSource) -> GEOExternalSource:
        source.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_external_sources
                   (source_id, tenant_id, audit_id, domain, source_category, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    source.source_id,
                    source.tenant_id,
                    source.audit_id or "",
                    source.domain,
                    source.source_category,
                    source.model_dump_json(),
                    source.created_at,
                    source.updated_at,
                ),
            )
            conn.commit()
        return source

    def list_external_sources(self, tenant_id: str, audit_id: str) -> List[GEOExternalSource]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM geo_external_sources WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at ASC",
                (tenant_id, audit_id),
            ).fetchall()
        return [GEOExternalSource.model_validate_json(r["payload_json"]) for r in rows]

    def save_page(self, page: GEOPageReadiness) -> GEOPageReadiness:
        page.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_pages
                   (page_id, tenant_id, audit_id, url, page_type, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    page.page_id,
                    page.tenant_id,
                    page.audit_id or "",
                    page.url,
                    page.page_type,
                    page.model_dump_json(),
                    page.created_at,
                    page.updated_at,
                ),
            )
            conn.commit()
        return page

    def list_pages(self, tenant_id: str, audit_id: str) -> List[GEOPageReadiness]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM geo_pages WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at ASC",
                (tenant_id, audit_id),
            ).fetchall()
        return [GEOPageReadiness.model_validate_json(r["payload_json"]) for r in rows]

    # ── Findings, Recommendations, Remediation, Verification ─────────────────

    def save_finding(self, finding: GEOFinding) -> GEOFinding:
        finding.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_findings
                   (finding_id, tenant_id, audit_id, category, severity, status, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    finding.finding_id,
                    finding.tenant_id,
                    finding.audit_id or "",
                    finding.category,
                    finding.severity.value,
                    finding.status,
                    finding.model_dump_json(),
                    finding.created_at,
                    finding.updated_at,
                ),
            )
            conn.commit()
        return finding

    def get_finding(self, tenant_id: str, finding_id: str) -> Optional[GEOFinding]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_findings WHERE tenant_id = ? AND finding_id = ?",
                (tenant_id, finding_id),
            ).fetchone()
        return self._load(GEOFinding, row)

    def list_findings(
        self,
        tenant_id: str,
        audit_id: str,
        severity: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[GEOFinding]:
        clauses = ["tenant_id = ?", "audit_id = ?"]
        params: List[Any] = [tenant_id, audit_id]
        if severity:
            clauses.append("severity = ?")
            params.append(severity.lower())
        if category:
            clauses.append("category = ?")
            params.append(category.lower())
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT payload_json FROM geo_findings WHERE {' AND '.join(clauses)} ORDER BY created_at ASC",
                tuple(params),
            ).fetchall()
        return [GEOFinding.model_validate_json(r["payload_json"]) for r in rows]

    def replace_findings(self, tenant_id: str, audit_id: str, findings: List[GEOFinding]) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM geo_findings WHERE tenant_id = ? AND audit_id = ?", (tenant_id, audit_id))
            for f in findings:
                f.tenant_id = tenant_id
                f.audit_id = audit_id
                f.updated_at = _now_iso()
                conn.execute(
                    """INSERT OR REPLACE INTO geo_findings
                       (finding_id, tenant_id, audit_id, category, severity, status, payload_json, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f.finding_id,
                        f.tenant_id,
                        f.audit_id,
                        f.category,
                        f.severity.value,
                        f.status,
                        f.model_dump_json(),
                        f.created_at,
                        f.updated_at,
                    ),
                )
            conn.commit()

    def save_recommendation(self, rec: GEORecommendation) -> GEORecommendation:
        rec.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_recommendations
                   (recommendation_id, tenant_id, audit_id, dimension, priority_score, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rec.recommendation_id,
                    rec.tenant_id,
                    rec.audit_id or "",
                    rec.dimension,
                    rec.priority_score,
                    rec.model_dump_json(),
                    rec.created_at,
                    rec.updated_at,
                ),
            )
            conn.commit()
        return rec

    def list_recommendations(self, tenant_id: str, audit_id: str) -> List[GEORecommendation]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM geo_recommendations WHERE tenant_id = ? AND audit_id = ? ORDER BY priority_score DESC",
                (tenant_id, audit_id),
            ).fetchall()
        return [GEORecommendation.model_validate_json(r["payload_json"]) for r in rows]

    def save_remediation_pack(self, pack: GEORemediationPack) -> GEORemediationPack:
        pack.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_remediation_packs
                   (pack_id, tenant_id, audit_id, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    pack.pack_id,
                    pack.tenant_id,
                    pack.audit_id or "",
                    pack.model_dump_json(),
                    pack.created_at,
                    pack.updated_at,
                ),
            )
            conn.commit()
        for t in pack.tasks:
            t.tenant_id = pack.tenant_id
            t.audit_id = pack.audit_id
            t.pack_id = pack.pack_id
            self.save_remediation_task(t)
        return pack

    def get_remediation_pack(self, tenant_id: str, audit_id: str) -> Optional[GEORemediationPack]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_remediation_packs WHERE tenant_id = ? AND audit_id = ? ORDER BY updated_at DESC LIMIT 1",
                (tenant_id, audit_id),
            ).fetchone()
        pack = self._load(GEORemediationPack, row)
        if pack:
            pack.tasks = self.list_remediation_tasks(tenant_id, audit_id=audit_id)
        return pack

    def list_remediation_packs(self, tenant_id: str) -> List[GEORemediationPack]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM geo_remediation_packs WHERE tenant_id = ? ORDER BY updated_at DESC LIMIT 50",
                (tenant_id,),
            ).fetchall()
        packs = [GEORemediationPack.model_validate_json(r["payload_json"]) for r in rows]
        for p in packs:
            if p.audit_id:
                p.tasks = self.list_remediation_tasks(tenant_id, audit_id=p.audit_id)
        return packs

    def save_remediation_task(self, task: GEORemediationTask) -> GEORemediationTask:
        task.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_remediation_tasks
                   (task_id, tenant_id, audit_id, pack_id, department, priority, status, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.task_id,
                    task.tenant_id,
                    task.audit_id or "",
                    task.pack_id,
                    task.department,
                    task.priority,
                    task.status,
                    task.model_dump_json(),
                    task.created_at,
                    task.updated_at,
                ),
            )
            conn.commit()
        return task

    def get_remediation_task(self, tenant_id: str, task_id: str) -> Optional[GEORemediationTask]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_remediation_tasks WHERE tenant_id = ? AND task_id = ?",
                (tenant_id, task_id),
            ).fetchone()
        return self._load(GEORemediationTask, row)

    def list_remediation_tasks(
        self,
        tenant_id: str,
        audit_id: Optional[str] = None,
        status: Optional[str] = None,
        department: Optional[str] = None,
    ) -> List[GEORemediationTask]:
        clauses = ["tenant_id = ?"]
        params: List[Any] = [tenant_id]
        if audit_id:
            clauses.append("audit_id = ?")
            params.append(audit_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if department:
            clauses.append("department = ?")
            params.append(department)
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT payload_json FROM geo_remediation_tasks WHERE {' AND '.join(clauses)} ORDER BY priority ASC, created_at ASC",
                tuple(params),
            ).fetchall()
        return [GEORemediationTask.model_validate_json(r["payload_json"]) for r in rows]

    def save_verification(self, ver: GEOVerification) -> GEOVerification:
        ver.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_verifications
                   (verification_id, tenant_id, audit_id, task_id, overall_status, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ver.verification_id,
                    ver.tenant_id,
                    ver.audit_id,
                    ver.task_id,
                    ver.overall_status,
                    ver.model_dump_json(),
                    ver.created_at,
                    ver.updated_at,
                ),
            )
            conn.commit()
        return ver

    def list_verifications(self, tenant_id: str, audit_id: Optional[str] = None, task_id: Optional[str] = None) -> List[GEOVerification]:
        clauses = ["tenant_id = ?"]
        params: List[Any] = [tenant_id]
        if audit_id:
            clauses.append("audit_id = ?")
            params.append(audit_id)
        if task_id:
            clauses.append("task_id = ?")
            params.append(task_id)
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT payload_json FROM geo_verifications WHERE {' AND '.join(clauses)} ORDER BY created_at DESC",
                tuple(params),
            ).fetchall()
        return [GEOVerification.model_validate_json(r["payload_json"]) for r in rows]

    # ── Experiments, Snapshots, Monitoring, Reports ──────────────────────────

    def save_experiment(self, exp: GEOExperiment) -> GEOExperiment:
        exp.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_experiments
                   (experiment_id, tenant_id, audit_id, status, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    exp.experiment_id,
                    exp.tenant_id,
                    exp.audit_id,
                    exp.status,
                    exp.model_dump_json(),
                    exp.created_at,
                    exp.updated_at,
                ),
            )
            conn.commit()
        return exp

    def get_experiment(self, tenant_id: str, experiment_id: str) -> Optional[GEOExperiment]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_experiments WHERE tenant_id = ? AND experiment_id = ?",
                (tenant_id, experiment_id),
            ).fetchone()
        return self._load(GEOExperiment, row)

    def list_experiments(self, tenant_id: str, audit_id: Optional[str] = None) -> List[GEOExperiment]:
        with self._conn() as conn:
            if audit_id:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_experiments WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at DESC",
                    (tenant_id, audit_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_experiments WHERE tenant_id = ? ORDER BY created_at DESC",
                    (tenant_id,),
                ).fetchall()
        return [GEOExperiment.model_validate_json(r["payload_json"]) for r in rows]

    def persist_snapshot(
        self,
        *,
        tenant_id: str,
        audit_id: Optional[str],
        snapshot_type: str,
        data: bytes | str,
        extension: str = "json",
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GEOSnapshot:
        cas = get_cas_storage()
        raw_bytes = data.encode("utf-8") if isinstance(data, str) else data
        content_hash, storage_uri = cas.put(raw_bytes, extension=extension)
        snap = GEOSnapshot(
            tenant_id=tenant_id,
            audit_id=audit_id,
            snapshot_type=snapshot_type,
            url=url,
            content_hash=content_hash,
            storage_uri=storage_uri,
            byte_size=len(raw_bytes),
            metadata=metadata or {},
        )
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_snapshots
                   (snapshot_id, tenant_id, audit_id, snapshot_type, content_hash, storage_uri, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    snap.snapshot_id,
                    snap.tenant_id,
                    snap.audit_id,
                    snap.snapshot_type,
                    snap.content_hash,
                    snap.storage_uri,
                    snap.model_dump_json(),
                    snap.created_at,
                ),
            )
            conn.commit()
        return snap

    def read_snapshot_bytes(self, storage_uri: str) -> Optional[bytes]:
        return get_cas_storage().get(storage_uri)

    def list_snapshots(self, tenant_id: str, audit_id: str) -> List[GEOSnapshot]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM geo_snapshots WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at ASC",
                (tenant_id, audit_id),
            ).fetchall()
        return [GEOSnapshot.model_validate_json(r["payload_json"]) for r in rows]

    def save_schedule(self, sched: GEOMonitoringSchedule) -> GEOMonitoringSchedule:
        sched.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_monitoring_schedules
                   (schedule_id, tenant_id, domain, cadence, enabled, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sched.schedule_id,
                    sched.tenant_id,
                    sched.domain,
                    sched.cadence,
                    1 if sched.enabled else 0,
                    sched.model_dump_json(),
                    sched.created_at,
                    sched.updated_at,
                ),
            )
            conn.commit()
        return sched

    def list_schedules(self, tenant_id: str, domain: Optional[str] = None) -> List[GEOMonitoringSchedule]:
        with self._conn() as conn:
            if domain:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_monitoring_schedules WHERE tenant_id = ? AND domain = ? ORDER BY created_at DESC",
                    (tenant_id, domain),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_monitoring_schedules WHERE tenant_id = ? ORDER BY created_at DESC",
                    (tenant_id,),
                ).fetchall()
        return [GEOMonitoringSchedule.model_validate_json(r["payload_json"]) for r in rows]

    def save_alert(self, alert: GEOMonitoringAlert) -> GEOMonitoringAlert:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_monitoring_alerts
                   (alert_id, tenant_id, audit_id, domain, severity, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert.alert_id,
                    alert.tenant_id,
                    alert.audit_id,
                    alert.domain,
                    alert.severity.value,
                    alert.model_dump_json(),
                    alert.created_at,
                ),
            )
            conn.commit()
        return alert

    def list_alerts(self, tenant_id: str, domain: Optional[str] = None, limit: int = 100) -> List[GEOMonitoringAlert]:
        with self._conn() as conn:
            if domain:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_monitoring_alerts WHERE tenant_id = ? AND domain = ? ORDER BY created_at DESC LIMIT ?",
                    (tenant_id, domain, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_monitoring_alerts WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                    (tenant_id, limit),
                ).fetchall()
        return [GEOMonitoringAlert.model_validate_json(r["payload_json"]) for r in rows]

    def save_report(self, report: GEOReport) -> GEOReport:
        report.updated_at = _now_iso()
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_reports
                   (report_id, tenant_id, audit_id, profile, format, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    report.report_id,
                    report.tenant_id,
                    report.audit_id or "",
                    report.profile,
                    report.format,
                    report.model_dump_json(),
                    report.created_at,
                    report.updated_at,
                ),
            )
            conn.commit()
        return report

    def get_report(self, tenant_id: str, report_id: str) -> Optional[GEOReport]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_reports WHERE tenant_id = ? AND report_id = ?",
                (tenant_id, report_id),
            ).fetchone()
        return self._load(GEOReport, row)

    def list_reports(self, tenant_id: str, audit_id: Optional[str] = None) -> List[GEOReport]:
        with self._conn() as conn:
            if audit_id:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_reports WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at DESC",
                    (tenant_id, audit_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM geo_reports WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 50",
                    (tenant_id,),
                ).fetchall()
        return [GEOReport.model_validate_json(r["payload_json"]) for r in rows]

    # ── Provider Connections (Encrypted Secrets) ─────────────────────────────

    def save_provider_connection(
        self,
        conn_record: GEOProviderConnection,
        encrypted_secret: Optional[str] = None,
    ) -> GEOProviderConnection:
        conn_record.updated_at = _now_iso()
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT connection_id, encrypted_secret FROM geo_provider_connections WHERE tenant_id = ? AND platform_id = ?",
                (conn_record.tenant_id, conn_record.platform_id),
            ).fetchone()
            secret_to_store = encrypted_secret if encrypted_secret is not None else (existing["encrypted_secret"] if existing else None)
            if existing:
                conn_record.connection_id = existing["connection_id"]
            conn_record.has_stored_secret = bool(secret_to_store)
            conn.execute(
                """INSERT OR REPLACE INTO geo_provider_connections
                   (connection_id, tenant_id, platform_id, encrypted_secret, payload_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    conn_record.connection_id,
                    conn_record.tenant_id,
                    conn_record.platform_id,
                    secret_to_store,
                    conn_record.model_dump_json(),
                    conn_record.created_at,
                    conn_record.updated_at,
                ),
            )
            conn.commit()
        return conn_record

    def list_provider_connections(self, tenant_id: str) -> List[GEOProviderConnection]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM geo_provider_connections WHERE tenant_id = ? ORDER BY platform_id ASC",
                (tenant_id,),
            ).fetchall()
        return [GEOProviderConnection.model_validate_json(r["payload_json"]) for r in rows]

    def get_encrypted_provider_secret(self, tenant_id: str, platform_id: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT encrypted_secret FROM geo_provider_connections WHERE tenant_id = ? AND platform_id = ?",
                (tenant_id, platform_id),
            ).fetchone()
        return row["encrypted_secret"] if row else None

    def delete_provider_connection(self, tenant_id: str, platform_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM geo_provider_connections WHERE tenant_id = ? AND platform_id = ?",
                (tenant_id, platform_id),
            )
            conn.commit()
        return cur.rowcount > 0

    # ── Agent Checkpoints & Canonical Artifacts ──────────────────────────────

    def save_agent_execution(
        self,
        *,
        execution_id: str,
        tenant_id: str,
        audit_id: str,
        agent_id: str,
        department: str,
        status: str,
        retry_count: int = 0,
        elapsed_sec: float = 0.0,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_agent_executions
                   (execution_id, tenant_id, audit_id, agent_id, department, status, retry_count, elapsed_sec, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    execution_id,
                    tenant_id,
                    audit_id,
                    agent_id,
                    department,
                    status,
                    retry_count,
                    elapsed_sec,
                    json.dumps(payload or {}, default=str),
                    _now_iso(),
                ),
            )
            conn.commit()

    def list_agent_executions(self, tenant_id: str, audit_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT execution_id, agent_id, department, status, retry_count, elapsed_sec, payload_json, created_at FROM geo_agent_executions WHERE tenant_id = ? AND audit_id = ? ORDER BY created_at ASC",
                (tenant_id, audit_id),
            ).fetchall()
        return [
            {
                "execution_id": r["execution_id"],
                "agent_id": r["agent_id"],
                "department": r["department"],
                "status": r["status"],
                "retry_count": r["retry_count"],
                "elapsed_sec": r["elapsed_sec"],
                "payload": json.loads(r["payload_json"] or "{}"),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def save_artifact(self, tenant_id: str, audit_id: str, name: str, payload: Dict[str, Any]) -> None:
        key = f"{tenant_id}:{audit_id}:{name}"
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO geo_artifacts
                   (artifact_key, tenant_id, audit_id, name, payload_json, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (key, tenant_id, audit_id, name, json.dumps(payload, default=str), _now_iso()),
            )
            conn.commit()

    def get_artifact(self, tenant_id: str, audit_id: str, name: str) -> Optional[Dict[str, Any]]:
        key = f"{tenant_id}:{audit_id}:{name}"
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM geo_artifacts WHERE artifact_key = ? AND tenant_id = ?",
                (key, tenant_id),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None


_geo_store_singleton: Optional[GEOStore] = None


def get_geo_store(db_path: Optional[str] = None) -> GEOStore:
    global _geo_store_singleton
    if db_path:
        return GEOStore(db_path=db_path)
    if _geo_store_singleton is None:
        _geo_store_singleton = GEOStore()
    return _geo_store_singleton

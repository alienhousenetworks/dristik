"""Canonical 22-Entity CRO Relational Schema & Tenant-Isolated Store.

Mirrors the Dristik enterprise SQLite/PostgreSQL schema pattern (`seo_orchestrator_schema.py`)
with strict `tenant_id` scoping, audit linkage, immutable timestamps, CAS snapshot references,
idempotency keys, and full provenance across all 22 CRO entities + operational tables.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

from app.cro.models import (
    CROAnalyticsEvent,
    CROAudience,
    CROAudit,
    CROBusinessProfile,
    CROExperiment,
    CROExperimentResult,
    CROFinding,
    CROFunnel,
    CROFunnelStep,
    CROGoal,
    CROHypothesis,
    CROInteractionTest,
    CROJourney,
    CROJourneyStep,
    CROMonitoringAlert,
    CROMonitoringSchedule,
    CROPage,
    CROPageElement,
    CRORecommendation,
    CRORemediationPack,
    CRORemediationTask,
    CROReport,
    CROSnapshot,
    CROVariant,
    CROVerification,
)
from app.db.storage_cas import get_cas_storage

T = TypeVar("T", bound=BaseModel)

CRO_SQLITE_SCHEMA = """
PRAGMA foreign_keys = ON;

-- 1. CROBusinessProfile
CREATE TABLE IF NOT EXISTS cro_business_profiles (
    profile_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    domain TEXT NOT NULL,
    business_type TEXT NOT NULL DEFAULT 'unknown',
    status TEXT NOT NULL DEFAULT 'active',
    methodology_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_bp_tenant_domain ON cro_business_profiles(tenant_id, domain);

-- 2. CROAudit
CREATE TABLE IF NOT EXISTS cro_audits (
    audit_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    target_url TEXT NOT NULL,
    profile_id TEXT,
    mode TEXT NOT NULL DEFAULT 'standard',
    status TEXT NOT NULL DEFAULT 'queued',
    current_stage TEXT NOT NULL DEFAULT 'init',
    experience_score REAL,
    measurement_score REAL,
    qa_status TEXT NOT NULL DEFAULT 'pending',
    idempotency_key TEXT,
    methodology_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_audits_tenant_domain ON cro_audits(tenant_id, domain);
CREATE INDEX IF NOT EXISTS idx_cro_audits_tenant_idem ON cro_audits(tenant_id, idempotency_key);

-- 3. CROGoal
CREATE TABLE IF NOT EXISTS cro_goals (
    goal_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    profile_id TEXT,
    goal_type TEXT NOT NULL DEFAULT 'primary',
    validation_status TEXT NOT NULL DEFAULT 'unvalidated',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_goals_tenant_audit ON cro_goals(tenant_id, audit_id);

-- 4. CROAudience
CREATE TABLE IF NOT EXISTS cro_audiences (
    audience_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    profile_id TEXT,
    name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_audiences_tenant_audit ON cro_audiences(tenant_id, audit_id);

-- 5. CROJourney
CREATE TABLE IF NOT EXISTS cro_journeys (
    journey_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    name TEXT NOT NULL,
    goal_id TEXT,
    technical_health TEXT NOT NULL DEFAULT 'not_tested',
    behavioral_health TEXT NOT NULL DEFAULT 'unmeasured',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_journeys_tenant_audit ON cro_journeys(tenant_id, audit_id);

-- 6. CROJourneyStep
CREATE TABLE IF NOT EXISTS cro_journey_steps (
    step_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    journey_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    technical_status TEXT NOT NULL DEFAULT 'not_tested',
    behavioral_status TEXT NOT NULL DEFAULT 'unmeasured',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_jsteps_journey ON cro_journey_steps(tenant_id, journey_id);

-- 7. CROPage
CREATE TABLE IF NOT EXISTS cro_pages (
    page_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    url TEXT NOT NULL,
    page_type TEXT NOT NULL DEFAULT 'general',
    importance TEXT NOT NULL DEFAULT 'medium',
    functional_test_status TEXT NOT NULL DEFAULT 'not_tested',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_pages_tenant_audit ON cro_pages(tenant_id, audit_id);

-- 8. CROPageElement
CREATE TABLE IF NOT EXISTS cro_page_elements (
    element_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    page_id TEXT NOT NULL,
    element_category TEXT NOT NULL,
    device TEXT NOT NULL DEFAULT 'desktop',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_elements_tenant_audit ON cro_page_elements(tenant_id, audit_id, element_category);

-- 9. CROInteractionTest
CREATE TABLE IF NOT EXISTS cro_interaction_tests (
    test_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    page_id TEXT,
    url TEXT NOT NULL,
    scenario TEXT NOT NULL,
    viewport_name TEXT NOT NULL DEFAULT 'desktop',
    result_status TEXT NOT NULL DEFAULT 'not_tested',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_tests_tenant_audit ON cro_interaction_tests(tenant_id, audit_id);

-- 10. CROAnalyticsEvent
CREATE TABLE IF NOT EXISTS cro_analytics_events (
    event_record_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    event_name TEXT NOT NULL,
    connector_type TEXT NOT NULL DEFAULT 'ga4',
    validation_status TEXT NOT NULL DEFAULT 'unavailable',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_events_tenant_audit ON cro_analytics_events(tenant_id, audit_id);

-- 11. CROFunnel
CREATE TABLE IF NOT EXISTS cro_funnels (
    funnel_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    name TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'not_connected',
    data_completeness TEXT NOT NULL DEFAULT 'unmeasured',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_funnels_tenant_audit ON cro_funnels(tenant_id, audit_id);

-- 12. CROFunnelStep
CREATE TABLE IF NOT EXISTS cro_funnel_steps (
    funnel_step_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    funnel_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    measurement_status TEXT NOT NULL DEFAULT 'data_unavailable',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_fsteps_funnel ON cro_funnel_steps(tenant_id, funnel_id);

-- 13. CROFinding
CREATE TABLE IF NOT EXISTS cro_findings (
    finding_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    priority_score REAL NOT NULL DEFAULT 50.0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_findings_tenant_audit ON cro_findings(tenant_id, audit_id, severity);

-- 14. CROHypothesis
CREATE TABLE IF NOT EXISTS cro_hypotheses (
    hypothesis_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    title TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_hyp_tenant_audit ON cro_hypotheses(tenant_id, audit_id);

-- 15. CRORecommendation
CREATE TABLE IF NOT EXISTS cro_recommendations (
    recommendation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    category TEXT NOT NULL,
    priority_rank INTEGER NOT NULL DEFAULT 2,
    approval_status TEXT NOT NULL DEFAULT 'pending',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_recs_tenant_audit ON cro_recommendations(tenant_id, audit_id);

-- 16. CROExperiment
CREATE TABLE IF NOT EXISTS cro_experiments (
    experiment_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    approval_status TEXT NOT NULL DEFAULT 'pending',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_exp_tenant_status ON cro_experiments(tenant_id, status);

-- 17. CROVariant
CREATE TABLE IF NOT EXISTS cro_variants (
    variant_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    name TEXT NOT NULL,
    is_control INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_var_exp ON cro_variants(tenant_id, experiment_id);

-- 18. CROExperimentResult
CREATE TABLE IF NOT EXISTS cro_experiment_results (
    result_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    decision TEXT NOT NULL DEFAULT 'inconclusive',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_expres_exp ON cro_experiment_results(tenant_id, experiment_id);

-- 19. CRORemediationTask (canonical CORemediationTask entity)
CREATE TABLE IF NOT EXISTS cro_remediation_tasks (
    task_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    pack_id TEXT,
    priority TEXT NOT NULL DEFAULT 'P1',
    department TEXT NOT NULL DEFAULT 'Engineering',
    status TEXT NOT NULL DEFAULT 'backlog',
    approval_status TEXT NOT NULL DEFAULT 'pending',
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_tasks_tenant_audit ON cro_remediation_tasks(tenant_id, audit_id, status);

-- 20. CROVerification
CREATE TABLE IF NOT EXISTS cro_verifications (
    verification_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    task_id TEXT NOT NULL,
    implementation_verified TEXT NOT NULL DEFAULT 'pending',
    functional_verification TEXT NOT NULL DEFAULT 'not_tested',
    analytics_verification TEXT NOT NULL DEFAULT 'unavailable',
    business_outcome TEXT NOT NULL DEFAULT 'insufficient_data',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_ver_tenant_task ON cro_verifications(tenant_id, task_id);

-- 21. CROSnapshot
CREATE TABLE IF NOT EXISTS cro_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT,
    snapshot_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_snaps_tenant_audit ON cro_snapshots(tenant_id, audit_id);

-- 22. CROReport
CREATE TABLE IF NOT EXISTS cro_reports (
    report_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    profile TEXT NOT NULL DEFAULT 'complete_audit_book',
    format TEXT NOT NULL DEFAULT 'html',
    qa_passed INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_reports_tenant_audit ON cro_reports(tenant_id, audit_id);

-- Operational supporting tables (packs, scores/QA, checkpoints, monitoring, connectors)
CREATE TABLE IF NOT EXISTS cro_remediation_packs (
    pack_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_packs_tenant_audit ON cro_remediation_packs(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS cro_audit_artifacts (
    audit_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    artifact_key TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (audit_id, tenant_id, artifact_key)
);

CREATE TABLE IF NOT EXISTS cro_agent_executions (
    execution_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    department TEXT NOT NULL,
    status TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    elapsed_sec REAL NOT NULL DEFAULT 0.0,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_agent_exec_audit ON cro_agent_executions(tenant_id, audit_id);

CREATE TABLE IF NOT EXISTS cro_monitoring_schedules (
    schedule_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_sched_tenant ON cro_monitoring_schedules(tenant_id, domain);

CREATE TABLE IF NOT EXISTS cro_monitoring_alerts (
    alert_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    severity TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_alerts_tenant ON cro_monitoring_alerts(tenant_id, domain);

CREATE TABLE IF NOT EXISTS cro_connectors (
    connector_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    category TEXT NOT NULL,
    connection_status TEXT NOT NULL DEFAULT 'not_connected',
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cro_conn_tenant ON cro_connectors(tenant_id, provider);
"""

# PostgreSQL DDL mirrors the SQLite schema cleanly (TEXT/JSONB/TIMESTAMPTZ)
CRO_POSTGRES_SCHEMA = (
    CRO_SQLITE_SCHEMA.replace("PRAGMA foreign_keys = ON;", "")
    .replace("payload_json TEXT NOT NULL", "payload_json JSONB NOT NULL")
    .replace("REAL", "DOUBLE PRECISION")
)

CRO_CANONICAL_TABLES = (
    "cro_business_profiles",
    "cro_audits",
    "cro_goals",
    "cro_audiences",
    "cro_journeys",
    "cro_journey_steps",
    "cro_pages",
    "cro_page_elements",
    "cro_interaction_tests",
    "cro_analytics_events",
    "cro_funnels",
    "cro_funnel_steps",
    "cro_findings",
    "cro_hypotheses",
    "cro_recommendations",
    "cro_experiments",
    "cro_variants",
    "cro_experiment_results",
    "cro_remediation_tasks",
    "cro_verifications",
    "cro_snapshots",
    "cro_reports",
)


def _default_cro_db_path() -> str:
    try:
        from app.db.connection import resolve_default_sqlite_path
        return resolve_default_sqlite_path("data/dristik_enterprise.db")
    except Exception:
        return "data/dristik_enterprise.db"


def init_cro_schema(db_path: Optional[str] = None) -> None:
    """Idempotently initialize all 22 CRO entities + operational tables."""
    resolved = db_path or _default_cro_db_path()
    parent = os.path.dirname(resolved)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(resolved)
    try:
        conn.executescript(CRO_SQLITE_SCHEMA)
        conn.commit()
    finally:
        conn.close()


class CROStore:
    """Tenant-isolated persistence repository for the canonical CRO data model."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _default_cro_db_path()
        init_cro_schema(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Snapshots (backed by CAS) ───────────────────────────────────────────
    def persist_snapshot(
        self,
        *,
        tenant_id: str,
        audit_id: Optional[str],
        snapshot_type: str,
        data: bytes | str,
        extension: str = "json",
        url: Optional[str] = None,
        viewport: Optional[str] = None,
        browser: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CROSnapshot:
        cas = get_cas_storage()
        content_hash, storage_uri = cas.put(data, extension=extension)
        snap = CROSnapshot(
            tenant_id=tenant_id,
            audit_id=audit_id,
            url=url,
            snapshot_type=snapshot_type,
            content_hash=content_hash,
            storage_uri=storage_uri,
            viewport=viewport,
            browser=browser,
            metadata=metadata or {},
        )
        self.save_snapshot(snap)
        return snap

    def read_snapshot_bytes(self, snapshot: CROSnapshot) -> Optional[bytes]:
        return get_cas_storage().get(snapshot.storage_uri)

    # ── Generic save/get/list helpers ───────────────────────────────────────
    def save_business_profile(self, profile: CROBusinessProfile) -> CROBusinessProfile:
        profile.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_business_profiles
                (profile_id, tenant_id, audit_id, domain, business_type, status, methodology_version, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.profile_id,
                    profile.tenant_id,
                    profile.audit_id,
                    profile.domain,
                    profile.business_type.value,
                    profile.status,
                    profile.methodology_version,
                    profile.model_dump_json(),
                    profile.created_at,
                    profile.updated_at,
                ),
            )
        return profile

    def get_business_profile(self, tenant_id: str, profile_id: str) -> Optional[CROBusinessProfile]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM cro_business_profiles WHERE tenant_id = ? AND profile_id = ?",
                (tenant_id, profile_id),
            ).fetchone()
        return CROBusinessProfile.model_validate_json(row["payload_json"]) if row else None

    def list_business_profiles(self, tenant_id: str, domain: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[CROBusinessProfile]:
        sql = "SELECT payload_json FROM cro_business_profiles WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if domain:
            sql += " AND domain = ?"
            params.append(domain)
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROBusinessProfile.model_validate_json(r["payload_json"]) for r in rows]

    def save_audit(self, audit: CROAudit) -> CROAudit:
        audit.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_audits
                (audit_id, tenant_id, domain, target_url, profile_id, mode, status, current_stage,
                 experience_score, measurement_score, qa_status, idempotency_key, methodology_version,
                 payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit.audit_id,
                    audit.tenant_id,
                    audit.domain,
                    audit.target_url,
                    audit.profile_id,
                    audit.mode,
                    audit.status,
                    audit.current_stage,
                    audit.experience_score,
                    audit.measurement_score,
                    audit.qa_status,
                    audit.idempotency_key,
                    audit.methodology_version,
                    audit.model_dump_json(),
                    audit.created_at,
                    audit.updated_at,
                ),
            )
        return audit

    def get_audit(self, tenant_id: str, audit_id: str) -> Optional[CROAudit]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM cro_audits WHERE tenant_id = ? AND audit_id = ?",
                (tenant_id, audit_id),
            ).fetchone()
        return CROAudit.model_validate_json(row["payload_json"]) if row else None

    def find_audit_by_idempotency(self, tenant_id: str, key: str) -> Optional[CROAudit]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM cro_audits WHERE tenant_id = ? AND idempotency_key = ? LIMIT 1",
                (tenant_id, key),
            ).fetchone()
        return CROAudit.model_validate_json(row["payload_json"]) if row else None

    def list_audits(self, tenant_id: str, domain: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[CROAudit]:
        sql = "SELECT payload_json FROM cro_audits WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if domain:
            sql += " AND domain = ?"
            params.append(domain)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROAudit.model_validate_json(r["payload_json"]) for r in rows]

    def save_goal(self, goal: CROGoal) -> CROGoal:
        goal.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_goals
                (goal_id, tenant_id, audit_id, profile_id, goal_type, validation_status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    goal.goal_id,
                    goal.tenant_id,
                    goal.audit_id,
                    goal.profile_id,
                    goal.goal_type,
                    goal.validation_status,
                    goal.model_dump_json(),
                    goal.created_at,
                    goal.updated_at,
                ),
            )
        return goal

    def get_goal(self, tenant_id: str, goal_id: str) -> Optional[CROGoal]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM cro_goals WHERE tenant_id = ? AND goal_id = ?",
                (tenant_id, goal_id),
            ).fetchone()
        return CROGoal.model_validate_json(row["payload_json"]) if row else None

    def list_goals(self, tenant_id: str, audit_id: Optional[str] = None, profile_id: Optional[str] = None) -> List[CROGoal]:
        sql = "SELECT payload_json FROM cro_goals WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        if profile_id:
            sql += " AND profile_id = ?"
            params.append(profile_id)
        sql += " ORDER BY created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROGoal.model_validate_json(r["payload_json"]) for r in rows]

    def save_audience(self, aud: CROAudience) -> CROAudience:
        aud.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_audiences
                (audience_id, tenant_id, audit_id, profile_id, name, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (aud.audience_id, aud.tenant_id, aud.audit_id, aud.profile_id, aud.name, aud.model_dump_json(), aud.created_at, aud.updated_at),
            )
        return aud

    def list_audiences(self, tenant_id: str, audit_id: Optional[str] = None) -> List[CROAudience]:
        sql = "SELECT payload_json FROM cro_audiences WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROAudience.model_validate_json(r["payload_json"]) for r in rows]

    def save_journey(self, journey: CROJourney) -> CROJourney:
        journey.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_journeys
                (journey_id, tenant_id, audit_id, name, goal_id, technical_health, behavioral_health, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    journey.journey_id,
                    journey.tenant_id,
                    journey.audit_id,
                    journey.name,
                    journey.goal_id,
                    journey.technical_health,
                    journey.behavioral_health,
                    journey.model_dump_json(),
                    journey.created_at,
                    journey.updated_at,
                ),
            )
            for step in journey.steps:
                step.journey_id = journey.journey_id
                step.tenant_id = journey.tenant_id
                step.audit_id = journey.audit_id
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cro_journey_steps
                    (step_id, tenant_id, audit_id, journey_id, step_order, technical_status, behavioral_status, payload_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        step.step_id,
                        step.tenant_id,
                        step.audit_id,
                        step.journey_id,
                        step.step_order,
                        step.technical_status,
                        step.behavioral_status,
                        step.model_dump_json(),
                        step.created_at,
                        step.updated_at,
                    ),
                )
        return journey

    def list_journeys(self, tenant_id: str, audit_id: Optional[str] = None) -> List[CROJourney]:
        sql = "SELECT payload_json FROM cro_journeys WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROJourney.model_validate_json(r["payload_json"]) for r in rows]

    def save_page(self, page: CROPage) -> CROPage:
        page.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_pages
                (page_id, tenant_id, audit_id, url, page_type, importance, functional_test_status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    page.page_id,
                    page.tenant_id,
                    page.audit_id,
                    page.url,
                    page.page_type.value,
                    page.importance,
                    page.functional_test_status,
                    page.model_dump_json(),
                    page.created_at,
                    page.updated_at,
                ),
            )
        return page

    def list_pages(self, tenant_id: str, audit_id: str, page_type: Optional[str] = None, limit: int = 200, offset: int = 0) -> List[CROPage]:
        sql = "SELECT payload_json FROM cro_pages WHERE tenant_id = ? AND audit_id = ?"
        params: List[Any] = [tenant_id, audit_id]
        if page_type:
            sql += " AND page_type = ?"
            params.append(page_type)
        sql += " ORDER BY created_at ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROPage.model_validate_json(r["payload_json"]) for r in rows]

    def save_element(self, el: CROPageElement) -> CROPageElement:
        el.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_page_elements
                (element_id, tenant_id, audit_id, page_id, element_category, device, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (el.element_id, el.tenant_id, el.audit_id, el.page_id, el.element_category, el.device, el.model_dump_json(), el.created_at, el.updated_at),
            )
        return el

    def list_elements(
        self,
        tenant_id: str,
        audit_id: str,
        element_category: Optional[str] = None,
        device: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[CROPageElement]:
        sql = "SELECT payload_json FROM cro_page_elements WHERE tenant_id = ? AND audit_id = ?"
        params: List[Any] = [tenant_id, audit_id]
        if element_category:
            sql += " AND element_category = ?"
            params.append(element_category)
        if device:
            sql += " AND device = ?"
            params.append(device)
        sql += " ORDER BY created_at ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROPageElement.model_validate_json(r["payload_json"]) for r in rows]

    def save_interaction_test(self, test: CROInteractionTest) -> CROInteractionTest:
        test.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_interaction_tests
                (test_id, tenant_id, audit_id, page_id, url, scenario, viewport_name, result_status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test.test_id,
                    test.tenant_id,
                    test.audit_id,
                    test.page_id,
                    test.url,
                    test.scenario,
                    test.viewport_name,
                    test.result_status,
                    test.model_dump_json(),
                    test.created_at,
                    test.updated_at,
                ),
            )
        return test

    def get_interaction_test(self, tenant_id: str, test_id: str) -> Optional[CROInteractionTest]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM cro_interaction_tests WHERE tenant_id = ? AND test_id = ?",
                (tenant_id, test_id),
            ).fetchone()
        return CROInteractionTest.model_validate_json(row["payload_json"]) if row else None

    def list_interaction_tests(self, tenant_id: str, audit_id: Optional[str] = None, limit: int = 500) -> List[CROInteractionTest]:
        sql = "SELECT payload_json FROM cro_interaction_tests WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROInteractionTest.model_validate_json(r["payload_json"]) for r in rows]

    def save_analytics_event(self, evt: CROAnalyticsEvent) -> CROAnalyticsEvent:
        evt.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_analytics_events
                (event_record_id, tenant_id, audit_id, event_name, connector_type, validation_status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evt.event_record_id,
                    evt.tenant_id,
                    evt.audit_id,
                    evt.event_name,
                    evt.connector_type,
                    evt.validation_status,
                    evt.model_dump_json(),
                    evt.created_at,
                    evt.updated_at,
                ),
            )
        return evt

    def list_analytics_events(self, tenant_id: str, audit_id: Optional[str] = None) -> List[CROAnalyticsEvent]:
        sql = "SELECT payload_json FROM cro_analytics_events WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROAnalyticsEvent.model_validate_json(r["payload_json"]) for r in rows]

    def save_funnel(self, funnel: CROFunnel) -> CROFunnel:
        funnel.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_funnels
                (funnel_id, tenant_id, audit_id, name, source, data_completeness, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    funnel.funnel_id,
                    funnel.tenant_id,
                    funnel.audit_id,
                    funnel.name,
                    funnel.source,
                    funnel.data_completeness,
                    funnel.model_dump_json(),
                    funnel.created_at,
                    funnel.updated_at,
                ),
            )
            for st in funnel.steps:
                st.funnel_id = funnel.funnel_id
                st.tenant_id = funnel.tenant_id
                st.audit_id = funnel.audit_id
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cro_funnel_steps
                    (funnel_step_id, tenant_id, audit_id, funnel_id, step_order, measurement_status, payload_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        st.funnel_step_id,
                        st.tenant_id,
                        st.audit_id,
                        st.funnel_id,
                        st.step_order,
                        st.measurement_status,
                        st.model_dump_json(),
                        st.created_at,
                        st.updated_at,
                    ),
                )
        return funnel

    def list_funnels(self, tenant_id: str, audit_id: Optional[str] = None) -> List[CROFunnel]:
        sql = "SELECT payload_json FROM cro_funnels WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROFunnel.model_validate_json(r["payload_json"]) for r in rows]

    def save_finding(self, finding: CROFinding) -> CROFinding:
        finding.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_findings
                (finding_id, tenant_id, audit_id, category, severity, source_type, status, priority_score, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding.finding_id,
                    finding.tenant_id,
                    finding.audit_id,
                    finding.category,
                    finding.severity.value,
                    finding.source_type.value,
                    finding.status,
                    finding.priority_score,
                    finding.model_dump_json(),
                    finding.created_at,
                    finding.updated_at,
                ),
            )
        return finding

    def list_findings(
        self,
        tenant_id: str,
        audit_id: str,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[CROFinding]:
        sql = "SELECT payload_json FROM cro_findings WHERE tenant_id = ? AND audit_id = ?"
        params: List[Any] = [tenant_id, audit_id]
        if severity:
            sql += " AND severity = ?"
            params.append(severity.lower())
        if category:
            sql += " AND category = ?"
            params.append(category)
        if source_type:
            sql += " AND source_type = ?"
            params.append(source_type)
        sql += " ORDER BY priority_score DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROFinding.model_validate_json(r["payload_json"]) for r in rows]

    def save_hypothesis(self, hyp: CROHypothesis) -> CROHypothesis:
        hyp.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_hypotheses
                (hypothesis_id, tenant_id, audit_id, title, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (hyp.hypothesis_id, hyp.tenant_id, hyp.audit_id, hyp.title, hyp.model_dump_json(), hyp.created_at, hyp.updated_at),
            )
        return hyp

    def list_hypotheses(self, tenant_id: str, audit_id: Optional[str] = None) -> List[CROHypothesis]:
        sql = "SELECT payload_json FROM cro_hypotheses WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROHypothesis.model_validate_json(r["payload_json"]) for r in rows]

    def save_recommendation(self, rec: CRORecommendation) -> CRORecommendation:
        rec.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_recommendations
                (recommendation_id, tenant_id, audit_id, category, priority_rank, approval_status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec.recommendation_id,
                    rec.tenant_id,
                    rec.audit_id,
                    rec.category,
                    rec.priority_rank,
                    rec.approval_status,
                    rec.model_dump_json(),
                    rec.created_at,
                    rec.updated_at,
                ),
            )
        return rec

    def list_recommendations(self, tenant_id: str, audit_id: str) -> List[CRORecommendation]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM cro_recommendations WHERE tenant_id = ? AND audit_id = ? ORDER BY priority_rank ASC",
                (tenant_id, audit_id),
            ).fetchall()
        return [CRORecommendation.model_validate_json(r["payload_json"]) for r in rows]

    def save_experiment(self, exp: CROExperiment) -> CROExperiment:
        exp.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_experiments
                (experiment_id, tenant_id, audit_id, title, status, approval_status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exp.experiment_id,
                    exp.tenant_id,
                    exp.audit_id,
                    exp.title,
                    exp.status,
                    exp.approval_status,
                    exp.model_dump_json(),
                    exp.created_at,
                    exp.updated_at,
                ),
            )
            for v in exp.variants:
                v.experiment_id = exp.experiment_id
                v.tenant_id = exp.tenant_id
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cro_variants
                    (variant_id, tenant_id, experiment_id, name, is_control, payload_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (v.variant_id, v.tenant_id, v.experiment_id, v.name, 1 if v.is_control else 0, v.model_dump_json(), v.created_at, v.updated_at),
                )
            if exp.latest_result:
                res = exp.latest_result
                res.experiment_id = exp.experiment_id
                res.tenant_id = exp.tenant_id
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cro_experiment_results
                    (result_id, tenant_id, experiment_id, decision, payload_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (res.result_id, res.tenant_id, res.experiment_id, res.decision, res.model_dump_json(), res.created_at, res.updated_at),
                )
        return exp

    def get_experiment(self, tenant_id: str, experiment_id: str) -> Optional[CROExperiment]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM cro_experiments WHERE tenant_id = ? AND experiment_id = ?",
                (tenant_id, experiment_id),
            ).fetchone()
        return CROExperiment.model_validate_json(row["payload_json"]) if row else None

    def list_experiments(self, tenant_id: str, audit_id: Optional[str] = None, status: Optional[str] = None) -> List[CROExperiment]:
        sql = "SELECT payload_json FROM cro_experiments WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROExperiment.model_validate_json(r["payload_json"]) for r in rows]

    def save_remediation_pack(self, pack: CRORemediationPack) -> CRORemediationPack:
        pack.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_remediation_packs
                (pack_id, tenant_id, audit_id, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (pack.pack_id, pack.tenant_id, pack.audit_id, pack.model_dump_json(), pack.created_at, pack.updated_at),
            )
            for task in pack.tasks:
                task.pack_id = pack.pack_id
                task.tenant_id = pack.tenant_id
                task.audit_id = pack.audit_id
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cro_remediation_tasks
                    (task_id, tenant_id, audit_id, pack_id, priority, department, status, approval_status, verification_status, payload_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.task_id,
                        task.tenant_id,
                        task.audit_id,
                        task.pack_id,
                        task.priority,
                        task.department,
                        task.status,
                        task.approval_status,
                        task.verification_status,
                        task.model_dump_json(),
                        task.created_at,
                        task.updated_at,
                    ),
                )
        return pack

    def get_remediation_pack(self, tenant_id: str, audit_id: str) -> Optional[CRORemediationPack]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM cro_remediation_packs WHERE tenant_id = ? AND audit_id = ? ORDER BY updated_at DESC LIMIT 1",
                (tenant_id, audit_id),
            ).fetchone()
        if not row:
            return None
        pack = CRORemediationPack.model_validate_json(row["payload_json"])
        pack.tasks = self.list_remediation_tasks(tenant_id, audit_id=audit_id)
        return pack

    def list_remediation_packs(self, tenant_id: str, limit: int = 50) -> List[CRORemediationPack]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM cro_remediation_packs WHERE tenant_id = ? ORDER BY updated_at DESC LIMIT ?",
                (tenant_id, limit),
            ).fetchall()
        return [CRORemediationPack.model_validate_json(r["payload_json"]) for r in rows]

    def save_remediation_task(self, task: CRORemediationTask) -> CRORemediationTask:
        task.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_remediation_tasks
                (task_id, tenant_id, audit_id, pack_id, priority, department, status, approval_status, verification_status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.tenant_id,
                    task.audit_id,
                    task.pack_id,
                    task.priority,
                    task.department,
                    task.status,
                    task.approval_status,
                    task.verification_status,
                    task.model_dump_json(),
                    task.created_at,
                    task.updated_at,
                ),
            )
        return task

    def get_remediation_task(self, tenant_id: str, task_id: str) -> Optional[CRORemediationTask]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM cro_remediation_tasks WHERE tenant_id = ? AND task_id = ?",
                (tenant_id, task_id),
            ).fetchone()
        return CRORemediationTask.model_validate_json(row["payload_json"]) if row else None

    def list_remediation_tasks(
        self,
        tenant_id: str,
        audit_id: Optional[str] = None,
        status: Optional[str] = None,
        department: Optional[str] = None,
    ) -> List[CRORemediationTask]:
        sql = "SELECT payload_json FROM cro_remediation_tasks WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if department:
            sql += " AND department = ?"
            params.append(department)
        sql += " ORDER BY priority ASC, created_at ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CRORemediationTask.model_validate_json(r["payload_json"]) for r in rows]

    def save_verification(self, ver: CROVerification) -> CROVerification:
        ver.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_verifications
                (verification_id, tenant_id, audit_id, task_id, implementation_verified, functional_verification,
                 analytics_verification, business_outcome, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ver.verification_id,
                    ver.tenant_id,
                    ver.audit_id,
                    ver.task_id,
                    ver.implementation_verified,
                    ver.functional_verification,
                    ver.analytics_verification,
                    ver.business_outcome,
                    ver.model_dump_json(),
                    ver.created_at,
                    ver.updated_at,
                ),
            )
        return ver

    def list_verifications(self, tenant_id: str, task_id: Optional[str] = None, audit_id: Optional[str] = None) -> List[CROVerification]:
        sql = "SELECT payload_json FROM cro_verifications WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if task_id:
            sql += " AND task_id = ?"
            params.append(task_id)
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROVerification.model_validate_json(r["payload_json"]) for r in rows]

    def save_snapshot(self, snap: CROSnapshot) -> CROSnapshot:
        snap.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_snapshots
                (snapshot_id, tenant_id, audit_id, snapshot_type, content_hash, storage_uri, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (snap.snapshot_id, snap.tenant_id, snap.audit_id, snap.snapshot_type, snap.content_hash, snap.storage_uri, snap.model_dump_json(), snap.created_at, snap.updated_at),
            )
        return snap

    def list_snapshots(self, tenant_id: str, audit_id: Optional[str] = None) -> List[CROSnapshot]:
        sql = "SELECT payload_json FROM cro_snapshots WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROSnapshot.model_validate_json(r["payload_json"]) for r in rows]

    def save_report(self, rep: CROReport) -> CROReport:
        rep.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_reports
                (report_id, tenant_id, audit_id, profile, format, qa_passed, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (rep.report_id, rep.tenant_id, rep.audit_id, rep.profile, rep.format, 1 if rep.qa_passed else 0, rep.model_dump_json(), rep.created_at, rep.updated_at),
            )
        return rep

    def get_report(self, tenant_id: str, report_id: str) -> Optional[CROReport]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM cro_reports WHERE tenant_id = ? AND report_id = ?",
                (tenant_id, report_id),
            ).fetchone()
        return CROReport.model_validate_json(row["payload_json"]) if row else None

    def list_reports(self, tenant_id: str, audit_id: Optional[str] = None) -> List[CROReport]:
        sql = "SELECT payload_json FROM cro_reports WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if audit_id:
            sql += " AND audit_id = ?"
            params.append(audit_id)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROReport.model_validate_json(r["payload_json"]) for r in rows]

    # ── Audit artifacts (scores, QA, specialist outputs, attribution, copy workspace) ──
    def save_artifact(self, tenant_id: str, audit_id: str, key: str, payload: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_audit_artifacts
                (audit_id, tenant_id, artifact_key, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (audit_id, tenant_id, key, json.dumps(payload, default=str), self._now()),
            )

    def get_artifact(self, tenant_id: str, audit_id: str, key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM cro_audit_artifacts WHERE tenant_id = ? AND audit_id = ? AND artifact_key = ?",
                (tenant_id, audit_id, key),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def save_agent_execution(
        self,
        *,
        execution_id: str,
        tenant_id: str,
        audit_id: str,
        agent_id: str,
        department: str,
        status: str,
        retry_count: int,
        elapsed_sec: float,
        payload: Dict[str, Any],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_agent_executions
                (execution_id, tenant_id, audit_id, agent_id, department, status, retry_count, elapsed_sec, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (execution_id, tenant_id, audit_id, agent_id, department, status, retry_count, elapsed_sec, json.dumps(payload, default=str), self._now()),
            )

    def list_agent_executions(self, tenant_id: str, audit_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT agent_id, department, status, retry_count, elapsed_sec, payload_json, updated_at FROM cro_agent_executions WHERE tenant_id = ? AND audit_id = ?",
                (tenant_id, audit_id),
            ).fetchall()
        return [
            {
                "agent_id": r["agent_id"],
                "department": r["department"],
                "status": r["status"],
                "retry_count": r["retry_count"],
                "elapsed_sec": r["elapsed_sec"],
                "output": json.loads(r["payload_json"]),
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    # ── Monitoring ──────────────────────────────────────────────────────────
    def save_monitoring_schedule(self, sched: CROMonitoringSchedule) -> CROMonitoringSchedule:
        sched.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_monitoring_schedules
                (schedule_id, tenant_id, domain, active, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (sched.schedule_id, sched.tenant_id, sched.domain, 1 if sched.active else 0, sched.model_dump_json(), sched.created_at, sched.updated_at),
            )
        return sched

    def list_monitoring_schedules(self, tenant_id: str, domain: Optional[str] = None) -> List[CROMonitoringSchedule]:
        sql = "SELECT payload_json FROM cro_monitoring_schedules WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if domain:
            sql += " AND domain = ?"
            params.append(domain)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROMonitoringSchedule.model_validate_json(r["payload_json"]) for r in rows]

    def save_monitoring_alert(self, alert: CROMonitoringAlert) -> CROMonitoringAlert:
        alert.updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cro_monitoring_alerts
                (alert_id, tenant_id, domain, severity, acknowledged, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (alert.alert_id, alert.tenant_id, alert.domain, alert.severity.value, 1 if alert.acknowledged else 0, alert.model_dump_json(), alert.created_at, alert.updated_at),
            )
        return alert

    def list_monitoring_alerts(self, tenant_id: str, domain: Optional[str] = None, limit: int = 100) -> List[CROMonitoringAlert]:
        sql = "SELECT payload_json FROM cro_monitoring_alerts WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if domain:
            sql += " AND domain = ?"
            params.append(domain)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [CROMonitoringAlert.model_validate_json(r["payload_json"]) for r in rows]


_default_store: Optional[CROStore] = None


def get_cro_store(db_path: Optional[str] = None) -> CROStore:
    global _default_store
    resolved = db_path or _default_cro_db_path()
    if _default_store is None or _default_store.db_path != resolved:
        _default_store = CROStore(db_path=resolved)
    return _default_store

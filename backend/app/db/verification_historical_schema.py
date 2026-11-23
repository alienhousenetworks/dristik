"""
Closed-Loop Remediation Verification (8 Tables) & Historical Longitudinal Intelligence (7 Tables).
Shared unified database schema (SQLite + PostgreSQL compatible).
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from app.db.connection import open_sqlite, resolve_default_sqlite_path

VERIFICATION_AND_HISTORICAL_DDL = """
-- ═══════════════════════════════════════════════════════════════════════════
-- Closed-Loop Remediation & Verification (8 Tables)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS remediation_tasks (
    task_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    audit_run_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    affected_url TEXT NOT NULL,
    severity TEXT NOT NULL,
    current_state TEXT NOT NULL DEFAULT 'OPEN',
    baseline_evidence_ref TEXT NOT NULL,
    baseline_observation_json TEXT NOT NULL,
    wont_fix_justification TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rt_org_finding ON remediation_tasks(org_id, finding_id);

CREATE TABLE IF NOT EXISTS remediation_patches (
    patch_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    patch_type TEXT NOT NULL,
    diff_or_instructions TEXT NOT NULL,
    approved_by TEXT,
    approved_at_utc TEXT,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deployment_records (
    deployment_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    git_commit_sha TEXT,
    pull_request_url TEXT,
    environment TEXT NOT NULL DEFAULT 'production',
    deployed_by TEXT NOT NULL,
    deployed_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verification_runs (
    verification_run_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    deployment_id TEXT,
    retest_timestamp_utc TEXT NOT NULL,
    test_environment TEXT NOT NULL,
    browser_device TEXT NOT NULL,
    verifier_identity TEXT NOT NULL,
    before_observation_json TEXT NOT NULL,
    after_observation_json TEXT NOT NULL,
    outcome_state TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verification_assertions (
    assertion_id TEXT PRIMARY KEY,
    verification_run_id TEXT NOT NULL,
    assertion_type TEXT NOT NULL,
    description TEXT NOT NULL,
    passed INTEGER NOT NULL,
    observed_value TEXT
);

CREATE TABLE IF NOT EXISTS verification_artifacts (
    artifact_id TEXT PRIMARY KEY,
    verification_run_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS finding_state_history (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    reason TEXT,
    transitioned_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS regression_results (
    regression_id TEXT PRIMARY KEY,
    verification_run_id TEXT NOT NULL,
    check_name TEXT NOT NULL,
    has_regression INTEGER NOT NULL DEFAULT 0,
    details TEXT NOT NULL,
    checked_at_utc TEXT NOT NULL
);

-- ═══════════════════════════════════════════════════════════════════════════
-- Historical Longitudinal Intelligence (7 Tables)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS methodology_versions (
    version_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    weights_json TEXT NOT NULL,
    released_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_run_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    audit_run_id TEXT NOT NULL UNIQUE,
    methodology_version TEXT NOT NULL,
    discovered_urls INTEGER NOT NULL DEFAULT 0,
    crawled_urls INTEGER NOT NULL DEFAULT 0,
    rendered_urls INTEGER NOT NULL DEFAULT 0,
    inspected_urls INTEGER NOT NULL DEFAULT 0,
    tested_urls INTEGER NOT NULL DEFAULT 0,
    crawled_url_set_json TEXT NOT NULL DEFAULT '[]',
    connectors_available_json TEXT NOT NULL DEFAULT '[]',
    capability_completeness REAL,
    evidence_coverage REAL,
    optimization_effectiveness REAL,
    scorecard_sha256 TEXT NOT NULL,
    captured_at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ars_org_domain ON audit_run_snapshots(org_id, domain, captured_at_utc);

CREATE TABLE IF NOT EXISTS audit_score_history (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    audit_run_id TEXT NOT NULL,
    pillar TEXT NOT NULL,
    capability_completeness REAL,
    evidence_coverage REAL,
    measured_health_score REAL,
    methodology_version TEXT NOT NULL,
    captured_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS finding_history (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    audit_run_id TEXT NOT NULL,
    finding_signature TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    pillar TEXT NOT NULL,
    severity TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL,
    captured_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS url_state_snapshots (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    audit_run_id TEXT NOT NULL,
    url TEXT NOT NULL,
    http_status INTEGER,
    canonical_url TEXT,
    title_hash TEXT,
    schema_types_json TEXT NOT NULL DEFAULT '[]',
    captured_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS competitor_snapshots (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    competitor_domain TEXT NOT NULL,
    audit_run_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    citation_share_pct REAL,
    referring_domains INTEGER,
    captured_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metric_timeseries (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    unit TEXT,
    source_provider TEXT NOT NULL,
    observed_at_utc TEXT NOT NULL
);
"""


def connect_verification_history_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    resolved = db_path or resolve_default_sqlite_path("data/dristik.db")
    conn = open_sqlite(resolved)
    conn.executescript(VERIFICATION_AND_HISTORICAL_DDL)
    conn.commit()
    return conn

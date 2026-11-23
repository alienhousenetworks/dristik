"""
Unified Enterprise Intelligence Relational Schema (SQLite + PostgreSQL compatible).

Covers all tenant-isolated enterprise tables across:
- Data Reliability, Provenance & Cross-System Reconciliation (4 tables)
- Backlink Intelligence (7 tables)
- AI Referral Analytics (6 tables)
- Universal Conversion Attribution (8 tables)
- Privacy, Consent, Retention & DSAR Governance (2 tables)
- Enterprise Operations Jobs & Dead-Letter Queue (2 tables)

Uses the unified database path from `app.db.connection.resolve_default_sqlite_path`.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from app.db.connection import open_sqlite, resolve_default_sqlite_path

ENTERPRISE_INTELLIGENCE_DDL = """
-- ═══════════════════════════════════════════════════════════════════════════
-- 1. Data Reliability, Provenance, Connector Sync & Reconciliation
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS metric_provenance_records (
    provenance_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    audit_run_id TEXT,
    metric_name TEXT NOT NULL,
    metric_definition_version TEXT NOT NULL,
    source_provider TEXT NOT NULL,
    source_endpoint TEXT,
    retrieved_at_utc TEXT NOT NULL,
    freshness_status TEXT NOT NULL DEFAULT 'FRESH',
    payload_sha256 TEXT NOT NULL,
    raw_value_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mpr_org_run ON metric_provenance_records(org_id, audit_run_id);

CREATE TABLE IF NOT EXISTS data_reconciliation_reports (
    reconciliation_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    period_start_utc TEXT NOT NULL,
    period_end_utc TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    source_a_name TEXT NOT NULL,
    source_a_value REAL,
    source_b_name TEXT NOT NULL,
    source_b_value REAL,
    discrepancy_delta REAL,
    discrepancy_pct REAL,
    reconciliation_status TEXT NOT NULL,
    explanation TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_drr_org_domain ON data_reconciliation_reports(org_id, domain);

CREATE TABLE IF NOT EXISTS connector_sync_runs (
    sync_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT,
    records_synced INTEGER NOT NULL DEFAULT 0,
    partial_errors_json TEXT NOT NULL DEFAULT '[]',
    freshness_sla_hours INTEGER NOT NULL DEFAULT 24,
    cursor_token TEXT
);
CREATE INDEX IF NOT EXISTS idx_csr_org_provider ON connector_sync_runs(org_id, provider);

CREATE TABLE IF NOT EXISTS connector_quota_state (
    org_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    requests_used INTEGER NOT NULL DEFAULT 0,
    requests_limit INTEGER NOT NULL DEFAULT 1000,
    window_reset_utc TEXT,
    updated_at_utc TEXT NOT NULL,
    PRIMARY KEY (org_id, provider)
);

-- ═══════════════════════════════════════════════════════════════════════════
-- 2. Backlink Intelligence (7 Tables)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS backlink_provider_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    provider TEXT NOT NULL,
    retrieved_at_utc TEXT NOT NULL,
    provider_authority_metric_name TEXT,
    provider_authority_metric_value REAL,
    total_backlinks INTEGER,
    referring_domains INTEGER,
    schema_valid INTEGER NOT NULL DEFAULT 1,
    payload_sha256 TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'MEASURED'
);
CREATE INDEX IF NOT EXISTS idx_bps_org_domain ON backlink_provider_snapshots(org_id, domain, provider);

CREATE TABLE IF NOT EXISTS backlink_domains (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    target_domain TEXT NOT NULL,
    referring_domain TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_authority_label TEXT,
    provider_authority_value REAL,
    dristik_quality_heuristic REAL,
    dristik_toxic_flags_json TEXT NOT NULL DEFAULT '[]',
    backlinks_count INTEGER NOT NULL DEFAULT 1,
    first_seen_utc TEXT,
    last_seen_utc TEXT,
    retrieved_at_utc TEXT NOT NULL,
    UNIQUE (org_id, target_domain, referring_domain, provider)
);

CREATE TABLE IF NOT EXISTS backlinks (
    backlink_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    target_domain TEXT NOT NULL,
    source_url TEXT NOT NULL,
    target_url TEXT NOT NULL,
    referring_domain TEXT NOT NULL,
    anchor_text TEXT,
    anchor_type TEXT,
    rel_attribute TEXT,
    http_status INTEGER,
    link_status TEXT NOT NULL DEFAULT 'LIVE',
    provider TEXT NOT NULL,
    dristik_toxic_risk_flag INTEGER NOT NULL DEFAULT 0,
    disavow_approval_status TEXT NOT NULL DEFAULT 'NOT_RECOMMENDED',
    disavow_approved_by TEXT,
    first_seen_utc TEXT,
    last_seen_utc TEXT,
    verified_at_utc TEXT,
    UNIQUE (org_id, source_url, target_url, provider)
);
CREATE INDEX IF NOT EXISTS idx_bl_org_target ON backlinks(org_id, target_domain);

CREATE TABLE IF NOT EXISTS backlink_history (
    history_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    target_domain TEXT NOT NULL,
    provider TEXT NOT NULL,
    snapshot_date_utc TEXT NOT NULL,
    new_backlinks INTEGER NOT NULL DEFAULT 0,
    lost_backlinks INTEGER NOT NULL DEFAULT 0,
    new_referring_domains INTEGER NOT NULL DEFAULT 0,
    lost_referring_domains INTEGER NOT NULL DEFAULT 0,
    acquisition_velocity REAL
);

CREATE TABLE IF NOT EXISTS backlink_anchors (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    target_domain TEXT NOT NULL,
    provider TEXT NOT NULL,
    anchor_text TEXT NOT NULL,
    anchor_category TEXT NOT NULL,
    backlinks_count INTEGER NOT NULL DEFAULT 0,
    referring_domains_count INTEGER NOT NULL DEFAULT 0,
    retrieved_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backlink_competitors (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    target_domain TEXT NOT NULL,
    competitor_domain TEXT NOT NULL,
    provider TEXT NOT NULL,
    comparison_date_utc TEXT NOT NULL,
    shared_referring_domains INTEGER NOT NULL DEFAULT 0,
    competitor_only_domains INTEGER NOT NULL DEFAULT 0,
    gap_domains_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS backlink_opportunities (
    opportunity_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    target_domain TEXT NOT NULL,
    candidate_domain TEXT NOT NULL,
    provider TEXT NOT NULL,
    competitors_linked_count INTEGER NOT NULL DEFAULT 0,
    dristik_priority_score REAL NOT NULL DEFAULT 0.0,
    rationale TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

-- ═══════════════════════════════════════════════════════════════════════════
-- 3. AI Referral Analytics (6 Tables)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ai_referral_sources (
    source_id TEXT PRIMARY KEY,
    platform_name TEXT NOT NULL,
    referrer_domain TEXT NOT NULL UNIQUE,
    classification_tier TEXT NOT NULL DEFAULT 'OBSERVED_REFERRER',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS visitor_sessions (
    session_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    visitor_id TEXT NOT NULL,
    landing_page TEXT NOT NULL,
    http_referrer TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    ai_platform TEXT,
    attribution_visibility TEXT NOT NULL DEFAULT 'OBSERVED',
    device_category TEXT NOT NULL DEFAULT 'desktop',
    is_new_visitor INTEGER NOT NULL DEFAULT 1,
    is_bot_or_internal INTEGER NOT NULL DEFAULT 0,
    consent_analytics INTEGER NOT NULL DEFAULT 1,
    started_at_utc TEXT NOT NULL,
    timezone_offset TEXT DEFAULT 'UTC'
);
CREATE INDEX IF NOT EXISTS idx_vs_org_domain ON visitor_sessions(org_id, domain, started_at_utc);

CREATE TABLE IF NOT EXISTS attribution_touchpoints (
    touchpoint_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    visitor_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    ai_platform TEXT,
    landing_page TEXT,
    touchpoint_order INTEGER NOT NULL DEFAULT 1,
    touchpoint_ts_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_at_org_visitor ON attribution_touchpoints(org_id, visitor_id);

CREATE TABLE IF NOT EXISTS conversion_events (
    event_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    visitor_id TEXT NOT NULL,
    session_id TEXT,
    event_name TEXT NOT NULL,
    funnel_type TEXT NOT NULL DEFAULT 'ecommerce',
    order_id TEXT,
    monetary_value REAL,
    currency TEXT NOT NULL DEFAULT 'INR',
    normalized_value_base REAL,
    base_currency TEXT NOT NULL DEFAULT 'INR',
    fx_rate REAL NOT NULL DEFAULT 1.0,
    event_ts_utc TEXT NOT NULL,
    ingested_at_utc TEXT NOT NULL,
    source_system TEXT NOT NULL DEFAULT 'sdk'
);
CREATE INDEX IF NOT EXISTS idx_ce_org_domain ON conversion_events(org_id, domain, event_ts_utc);

CREATE TABLE IF NOT EXISTS revenue_attributions (
    attribution_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    conversion_event_id TEXT NOT NULL,
    order_id TEXT,
    model_name TEXT NOT NULL,
    ai_platform TEXT,
    attributed_revenue REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'INR',
    attribution_confidence REAL NOT NULL DEFAULT 0.0,
    is_assisted INTEGER NOT NULL DEFAULT 0,
    reconciled_with_order INTEGER NOT NULL DEFAULT 0,
    computed_at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ra_org_model ON revenue_attributions(org_id, model_name);

CREATE TABLE IF NOT EXISTS ai_referral_daily_metrics (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    metric_date_utc TEXT NOT NULL,
    ai_platform TEXT NOT NULL,
    sessions INTEGER NOT NULL DEFAULT 0,
    new_visitors INTEGER NOT NULL DEFAULT 0,
    returning_visitors INTEGER NOT NULL DEFAULT 0,
    attributed_conversions INTEGER NOT NULL DEFAULT 0,
    assisted_conversions INTEGER NOT NULL DEFAULT 0,
    attributed_revenue REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'INR',
    UNIQUE (org_id, domain, metric_date_utc, ai_platform)
);

-- ═══════════════════════════════════════════════════════════════════════════
-- 4. Universal Conversion Attribution (8 Tables)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS analytics_events (
    event_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    visitor_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    event_name TEXT NOT NULL,
    page_url TEXT NOT NULL,
    device_category TEXT NOT NULL DEFAULT 'desktop',
    viewport_w INTEGER,
    viewport_h INTEGER,
    click_x REAL,
    click_y REAL,
    scroll_depth_pct REAL,
    dom_selector TEXT,
    form_id TEXT,
    form_field_name TEXT,
    backend_submit_status INTEGER,
    is_rage_click INTEGER NOT NULL DEFAULT 0,
    is_dead_click INTEGER NOT NULL DEFAULT 0,
    is_bot_or_internal INTEGER NOT NULL DEFAULT 0,
    consent_granted INTEGER NOT NULL DEFAULT 1,
    sdk_load_ms REAL,
    event_ts_utc TEXT NOT NULL,
    ingested_at_utc TEXT NOT NULL,
    is_out_of_order INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ae_org_domain_ts ON analytics_events(org_id, domain, event_ts_utc);

CREATE TABLE IF NOT EXISTS conversion_goals (
    goal_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    name TEXT NOT NULL,
    funnel_type TEXT NOT NULL,
    target_event_name TEXT NOT NULL,
    is_revenue_goal INTEGER NOT NULL DEFAULT 0,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversion_funnels (
    funnel_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    name TEXT NOT NULL,
    funnel_type TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversion_sessions (
    session_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    visitor_id TEXT NOT NULL,
    device_category TEXT NOT NULL,
    entry_url TEXT NOT NULL,
    converted INTEGER NOT NULL DEFAULT 0,
    revenue REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'INR',
    started_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversion_attributions (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    conversion_event_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    channel TEXT NOT NULL,
    credit_weight REAL NOT NULL,
    attributed_revenue REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'INR',
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    order_id TEXT NOT NULL,
    source_platform TEXT NOT NULL,
    visitor_id TEXT,
    gross_amount REAL NOT NULL,
    net_amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'CONFIRMED',
    transacted_at_utc TEXT NOT NULL,
    reconciled_at_utc TEXT NOT NULL,
    UNIQUE (org_id, order_id, source_platform)
);

CREATE TABLE IF NOT EXISTS transaction_refunds (
    refund_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    source_platform TEXT NOT NULL,
    refund_amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    reason TEXT,
    refunded_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversion_cohorts (
    cohort_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    cohort_period TEXT NOT NULL,
    segment_key TEXT NOT NULL,
    eligible_visitors INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    revenue REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'INR',
    computed_at_utc TEXT NOT NULL
);

-- ═══════════════════════════════════════════════════════════════════════════
-- 5. Privacy, Consent & DSAR Governance (2 Tables)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS consent_records (
    consent_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    analytics_granted INTEGER NOT NULL DEFAULT 0,
    replay_granted INTEGER NOT NULL DEFAULT 0,
    experimentation_granted INTEGER NOT NULL DEFAULT 0,
    cmp_provider TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    updated_at_utc TEXT NOT NULL,
    UNIQUE (org_id, subject_id)
);

CREATE TABLE IF NOT EXISTS dsar_requests (
    request_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    request_type TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    records_affected INTEGER NOT NULL DEFAULT 0,
    created_at_utc TEXT NOT NULL,
    completed_at_utc TEXT
);

-- ═══════════════════════════════════════════════════════════════════════════
-- 6. Enterprise Operations: Retries & Dead-Letter Queue (2 Tables)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS background_jobs (
    job_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    job_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    next_retry_at_utc TEXT,
    last_error TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dead_letter_jobs (
    dlq_id TEXT PRIMARY KEY,
    original_job_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    job_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    failure_reason TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    quarantined_at_utc TEXT NOT NULL,
    replayed_at_utc TEXT
);
"""


def get_enterprise_db_path(db_path: Optional[str] = None) -> str:
    return db_path or resolve_default_sqlite_path("data/dristik.db")


def init_enterprise_intelligence_schema(db_path: Optional[str] = None) -> str:
    resolved = get_enterprise_db_path(db_path)
    conn = open_sqlite(resolved)
    try:
        conn.executescript(ENTERPRISE_INTELLIGENCE_DDL)
        conn.commit()
    finally:
        conn.close()
    return resolved


def connect_enterprise_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    resolved = init_enterprise_intelligence_schema(db_path)
    return open_sqlite(resolved)

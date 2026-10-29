-- External Authority & Entity Intelligence.
-- Idempotent. Customer tokens live only in token_ciphertext.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS external_connections (
    connection_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    auth_mode TEXT NOT NULL,
    account_label TEXT,
    external_account_id TEXT,
    property_id TEXT,
    property_label TEXT,
    domain TEXT,
    scopes_json TEXT,
    token_ciphertext TEXT,
    token_status TEXT,
    token_expires_at TEXT,
    capabilities_json TEXT,
    collection_tier TEXT,
    credential_source TEXT,
    last_success_at TEXT,
    last_attempt_at TEXT,
    next_sync_at TEXT,
    last_error TEXT,
    quota_status TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(project_id, provider)
);

CREATE TABLE IF NOT EXISTS external_accounts (
    account_row_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    external_account_id TEXT NOT NULL,
    label TEXT,
    metadata_json TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS external_properties (
    property_row_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    external_property_id TEXT NOT NULL,
    label TEXT,
    domain TEXT,
    metadata_json TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS external_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    domain TEXT,
    period_days INTEGER NOT NULL,
    period_start TEXT,
    period_end TEXT,
    collected_at TEXT NOT NULL,
    data_state TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS external_raw_payloads (
    raw_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    http_status INTEGER,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS external_records (
    record_id TEXT PRIMARY KEY,
    record_type TEXT NOT NULL,
    project_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    source TEXT NOT NULL,
    external_account_id TEXT,
    external_property_id TEXT,
    domain TEXT,
    url TEXT,
    metric TEXT NOT NULL,
    metric_type TEXT,
    value_num REAL,
    value_text TEXT,
    unit TEXT,
    period_start TEXT,
    period_end TEXT,
    collected_at TEXT NOT NULL,
    evidence_url TEXT,
    raw_provider_reference TEXT,
    confidence REAL,
    status TEXT NOT NULL,
    evidence_basis TEXT,
    metadata_json TEXT,
    snapshot_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_ext_records_snapshot ON external_records(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_ext_records_lookup ON external_records(project_id, provider, record_type);

CREATE VIEW IF NOT EXISTS search_performance_records AS
    SELECT * FROM external_records WHERE record_type = 'search_performance';
CREATE VIEW IF NOT EXISTS backlink_records AS
    SELECT * FROM external_records WHERE record_type = 'backlink';
CREATE VIEW IF NOT EXISTS referring_domain_records AS
    SELECT * FROM external_records WHERE record_type = 'referring_domain';
CREATE VIEW IF NOT EXISTS brand_mention_records AS
    SELECT * FROM external_records WHERE record_type = 'brand_mention';
CREATE VIEW IF NOT EXISTS business_listing_records AS
    SELECT * FROM external_records WHERE record_type = 'business_listing';
CREATE VIEW IF NOT EXISTS business_profile_metrics AS
    SELECT * FROM external_records WHERE record_type = 'business_profile_metric';
CREATE VIEW IF NOT EXISTS entity_signals AS
    SELECT * FROM external_records WHERE record_type = 'entity_signal';
CREATE VIEW IF NOT EXISTS competitor_signals AS
    SELECT * FROM external_records WHERE record_type = 'competitor_signal';

CREATE TABLE IF NOT EXISTS external_profiles (
    project_id TEXT NOT NULL,
    profile_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, profile_type)
);

CREATE TABLE IF NOT EXISTS oauth_states (
    state TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    domain TEXT,
    payload_json TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS external_jobs (
    job_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    domain TEXT,
    job_type TEXT NOT NULL,
    provider TEXT,
    period_days INTEGER,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 4,
    next_run_at TEXT NOT NULL,
    last_error TEXT,
    result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ext_jobs_due ON external_jobs(status, next_run_at);

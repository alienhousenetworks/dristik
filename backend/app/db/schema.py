"""
Dristik AI Durable Audit Database Schema
Compatible with both PostgreSQL and SQLite.
"""

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free_scan',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audits (
    analysis_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    website_url TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    stage TEXT NOT NULL DEFAULT 'queued',
    max_pages INTEGER NOT NULL DEFAULT 1,
    score_overall REAL,
    score_human REAL,
    score_google REAL,
    score_ai_readiness REAL,
    score_ai_visibility REAL,
    score_band TEXT,
    started_at TEXT,
    completed_at TEXT,
    input_hash TEXT,
    output_hash TEXT,
    raw_report_json TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audits_org ON audits(org_id);
CREATE INDEX IF NOT EXISTS idx_audits_domain ON audits(domain);
CREATE INDEX IF NOT EXISTS idx_audits_status ON audits(status);

CREATE TABLE IF NOT EXISTS audit_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    input_hash TEXT,
    output_hash TEXT,
    crawled_count INTEGER DEFAULT 0,
    evidence_count INTEGER DEFAULT 0,
    claims_count INTEGER DEFAULT 0,
    findings_count INTEGER DEFAULT 0,
    accumulated_cost_usd REAL DEFAULT 0.0,
    state_payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(analysis_id) REFERENCES audits(analysis_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_analysis ON audit_checkpoints(analysis_id);

CREATE TABLE IF NOT EXISTS audit_pages (
    page_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    url TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    title TEXT,
    word_count INTEGER DEFAULT 0,
    readability_score REAL,
    ttfb_ms REAL,
    page_type TEXT,
    raw_metadata_json TEXT,
    crawled_at TEXT NOT NULL,
    FOREIGN KEY(analysis_id) REFERENCES audits(analysis_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pages_analysis ON audit_pages(analysis_id);

CREATE TABLE IF NOT EXISTS audit_evidence (
    evidence_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    evidence_class TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    url TEXT,
    selector TEXT,
    text_extract TEXT,
    evidence_hash TEXT,
    raw_snapshot_id TEXT,
    provenance_state TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(analysis_id) REFERENCES audits(analysis_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evidence_analysis ON audit_evidence(analysis_id);
CREATE INDEX IF NOT EXISTS idx_evidence_hash ON audit_evidence(evidence_hash);

CREATE TABLE IF NOT EXISTS audit_claims (
    claim_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    category TEXT NOT NULL,
    claim_family TEXT,
    statement TEXT NOT NULL,
    confidence_band TEXT,
    rubric_confidence TEXT,
    materiality TEXT,
    source_integrity TEXT,
    verification_status TEXT,
    evidence_refs_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(analysis_id) REFERENCES audits(analysis_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_claims_analysis ON audit_claims(analysis_id);

CREATE TABLE IF NOT EXISTS audit_findings (
    finding_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    impact TEXT,
    recommendation TEXT,
    evidence_refs_json TEXT,
    claim_refs_json TEXT,
    verification_status TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(analysis_id) REFERENCES audits(analysis_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_findings_analysis ON audit_findings(analysis_id);

CREATE TABLE IF NOT EXISTS agent_telemetry (
    telemetry_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    latency_ms REAL DEFAULT 0.0,
    prompt_hash TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(analysis_id) REFERENCES audits(analysis_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS project_keywords (
    keyword_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    keyword TEXT NOT NULL,
    target_url TEXT,
    intent TEXT DEFAULT 'Commercial',
    search_volume INTEGER DEFAULT 0,
    cpc_usd REAL DEFAULT 0.0,
    competition REAL DEFAULT 0.0,
    keyword_difficulty INTEGER,
    current_position INTEGER,
    previous_position INTEGER,
    best_position INTEGER,
    serp_features_json TEXT,
    is_active INTEGER DEFAULT 1,
    tags_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(project_id, keyword)
);

CREATE INDEX IF NOT EXISTS idx_pk_project ON project_keywords(project_id, is_active);
CREATE INDEX IF NOT EXISTS idx_pk_domain ON project_keywords(domain);

CREATE TABLE IF NOT EXISTS keyword_serp_history (
    history_id TEXT PRIMARY KEY,
    keyword_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    position INTEGER,
    previous_position INTEGER,
    position_delta INTEGER DEFAULT 0,
    ranking_url TEXT,
    serp_features_json TEXT,
    has_ai_overview INTEGER DEFAULT 0,
    has_featured_snippet INTEGER DEFAULT 0,
    has_local_pack INTEGER DEFAULT 0,
    snapshot_date TEXT NOT NULL,
    raw_serp_ref TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(keyword_id) REFERENCES project_keywords(keyword_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ksh_keyword_date ON keyword_serp_history(keyword_id, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_ksh_project_date ON keyword_serp_history(project_id, snapshot_date);

CREATE TABLE IF NOT EXISTS keyword_competitors (
    comp_history_id TEXT PRIMARY KEY,
    keyword_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    competitor_domain TEXT NOT NULL,
    position INTEGER,
    ranking_url TEXT,
    snapshot_date TEXT NOT NULL,
    FOREIGN KEY(keyword_id) REFERENCES project_keywords(keyword_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kc_keyword_comp ON keyword_competitors(keyword_id, competitor_domain);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    org_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(64) NOT NULL DEFAULT 'free_scan',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audits (
    analysis_id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    website_url TEXT NOT NULL,
    domain VARCHAR(255) NOT NULL,
    status VARCHAR(64) NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    stage VARCHAR(64) NOT NULL DEFAULT 'queued',
    max_pages INTEGER NOT NULL DEFAULT 1,
    score_overall NUMERIC(5,2),
    score_human NUMERIC(5,2),
    score_google NUMERIC(5,2),
    score_ai_readiness NUMERIC(5,2),
    score_ai_visibility NUMERIC(5,2),
    score_band VARCHAR(64),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    input_hash VARCHAR(128),
    output_hash VARCHAR(128),
    raw_report_json JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audits_org ON audits(org_id);
CREATE INDEX IF NOT EXISTS idx_audits_domain ON audits(domain);
CREATE INDEX IF NOT EXISTS idx_audits_status ON audits(status);

CREATE TABLE IF NOT EXISTS audit_checkpoints (
    checkpoint_id VARCHAR(64) PRIMARY KEY,
    analysis_id VARCHAR(64) NOT NULL REFERENCES audits(analysis_id) ON DELETE CASCADE,
    stage VARCHAR(64) NOT NULL,
    step_number INTEGER NOT NULL,
    status VARCHAR(64) NOT NULL,
    input_hash VARCHAR(128),
    output_hash VARCHAR(128),
    crawled_count INTEGER DEFAULT 0,
    evidence_count INTEGER DEFAULT 0,
    claims_count INTEGER DEFAULT 0,
    findings_count INTEGER DEFAULT 0,
    accumulated_cost_usd NUMERIC(10,5) DEFAULT 0.0,
    state_payload_json JSONB,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_analysis ON audit_checkpoints(analysis_id);

CREATE TABLE IF NOT EXISTS audit_pages (
    page_id VARCHAR(64) PRIMARY KEY,
    analysis_id VARCHAR(64) NOT NULL REFERENCES audits(analysis_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    title TEXT,
    word_count INTEGER DEFAULT 0,
    readability_score NUMERIC(5,2),
    ttfb_ms NUMERIC(8,2),
    page_type VARCHAR(64),
    raw_metadata_json JSONB,
    crawled_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pages_analysis ON audit_pages(analysis_id);

CREATE TABLE IF NOT EXISTS audit_evidence (
    evidence_id VARCHAR(64) PRIMARY KEY,
    analysis_id VARCHAR(64) NOT NULL REFERENCES audits(analysis_id) ON DELETE CASCADE,
    evidence_class VARCHAR(64) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_name VARCHAR(128) NOT NULL,
    url TEXT,
    selector TEXT,
    text_extract TEXT,
    evidence_hash VARCHAR(128),
    raw_snapshot_id VARCHAR(128),
    provenance_state VARCHAR(64) NOT NULL,
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evidence_analysis ON audit_evidence(analysis_id);
CREATE INDEX IF NOT EXISTS idx_evidence_hash ON audit_evidence(evidence_hash);

CREATE TABLE IF NOT EXISTS audit_claims (
    claim_id VARCHAR(64) PRIMARY KEY,
    analysis_id VARCHAR(64) NOT NULL REFERENCES audits(analysis_id) ON DELETE CASCADE,
    agent_id VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    claim_family VARCHAR(64),
    statement TEXT NOT NULL,
    confidence_band VARCHAR(32),
    rubric_confidence VARCHAR(32),
    materiality VARCHAR(32),
    source_integrity VARCHAR(64),
    verification_status VARCHAR(64),
    evidence_refs_json JSONB,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claims_analysis ON audit_claims(analysis_id);

CREATE TABLE IF NOT EXISTS audit_findings (
    finding_id VARCHAR(64) PRIMARY KEY,
    analysis_id VARCHAR(64) NOT NULL REFERENCES audits(analysis_id) ON DELETE CASCADE,
    category VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    impact TEXT,
    recommendation TEXT,
    evidence_refs_json JSONB,
    claim_refs_json JSONB,
    verification_status VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_findings_analysis ON audit_findings(analysis_id);

CREATE TABLE IF NOT EXISTS agent_telemetry (
    telemetry_id VARCHAR(64) PRIMARY KEY,
    analysis_id VARCHAR(64) NOT NULL REFERENCES audits(analysis_id) ON DELETE CASCADE,
    agent_id VARCHAR(128) NOT NULL,
    provider VARCHAR(64),
    model VARCHAR(128),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd NUMERIC(10,5) DEFAULT 0.0,
    latency_ms NUMERIC(10,2) DEFAULT 0.0,
    prompt_hash VARCHAR(128),
    status VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_telemetry_analysis ON agent_telemetry(analysis_id);
"""

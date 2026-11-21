"""
Enterprise Relational Schema for the Central SEO Orchestrator and Workflow Engine.
Defines all 26 authoritative entities with workspace/tenant scoping, audit linkage,
immutable timestamps, and performance indexes for both SQLite and PostgreSQL.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Optional

SEO_ORCHESTRATOR_SQLITE_SCHEMA = """
-- 1. Master SEO Audit Runs
CREATE TABLE IF NOT EXISTS seo_audit_runs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'STANDARD', -- QUICK | STANDARD | DEEP | CONTINUOUS
    status TEXT NOT NULL DEFAULT 'QUEUED', -- QUEUED | RUNNING | PAUSED | COMPLETED | FAILED | CANCELLED
    current_stage TEXT NOT NULL DEFAULT 'INIT',
    execution_budget_sec INTEGER NOT NULL DEFAULT 300,
    elapsed_time_sec REAL NOT NULL DEFAULT 0.0,
    total_tasks INTEGER NOT NULL DEFAULT 0,
    completed_tasks INTEGER NOT NULL DEFAULT 0,
    failed_tasks INTEGER NOT NULL DEFAULT 0,
    overall_score REAL,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_audit_runs_ws_status ON seo_audit_runs(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_seo_audit_runs_domain ON seo_audit_runs(domain);

-- 2. Audit Configurations
CREATE TABLE IF NOT EXISTS seo_audit_configurations (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    target_url TEXT NOT NULL,
    mode TEXT NOT NULL,
    max_pages INTEGER NOT NULL DEFAULT 250,
    max_depth INTEGER NOT NULL DEFAULT 3,
    max_concurrency INTEGER NOT NULL DEFAULT 5,
    requests_per_second REAL NOT NULL DEFAULT 5.0,
    respect_robots_txt TEXT NOT NULL DEFAULT 'OBEY',
    render_javascript INTEGER NOT NULL DEFAULT 1,
    connectors_enabled TEXT DEFAULT '[]',
    excluded_paths TEXT DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_audit_cfg_audit ON seo_audit_configurations(audit_id);

-- 3. Agent Registry
CREATE TABLE IF NOT EXISTS seo_agent_registry (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    group_name TEXT NOT NULL, -- technical | on_page | content | schema | specialist | strategic
    version TEXT NOT NULL DEFAULT 'v1',
    mode TEXT NOT NULL DEFAULT 'deterministic', -- deterministic | ai_assisted
    timeout_sec INTEGER NOT NULL DEFAULT 60,
    retry_limit INTEGER NOT NULL DEFAULT 2,
    required_inputs TEXT DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 4. Agent Executions
CREATE TABLE IF NOT EXISTS seo_agent_executions (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    agent_id TEXT NOT NULL REFERENCES seo_agent_registry(agent_id),
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING | RUNNING | COMPLETED | FAILED | SKIPPED
    inputs_hash TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    execution_time_sec REAL NOT NULL DEFAULT 0.0,
    token_usage INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
    error_code TEXT,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_agent_exec_audit ON seo_agent_executions(audit_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_seo_agent_exec_status ON seo_agent_executions(audit_id, status);

-- 5. Agent Outputs
CREATE TABLE IF NOT EXISTS seo_agent_outputs (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL REFERENCES seo_agent_executions(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    findings_count INTEGER NOT NULL DEFAULT 0,
    output_payload TEXT NOT NULL, -- JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_agent_outputs_audit ON seo_agent_outputs(audit_id);

-- 6. Workflow Tasks
CREATE TABLE IF NOT EXISTS seo_workflow_tasks (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    task_name TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_wf_tasks_audit ON seo_workflow_tasks(audit_id, status);

-- 7. Workflow Dependencies
CREATE TABLE IF NOT EXISTS seo_workflow_dependencies (
    task_id TEXT NOT NULL REFERENCES seo_workflow_tasks(id) ON DELETE CASCADE,
    depends_on_task_id TEXT NOT NULL REFERENCES seo_workflow_tasks(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL,
    PRIMARY KEY (task_id, depends_on_task_id)
);
CREATE INDEX IF NOT EXISTS idx_seo_wf_deps_audit ON seo_workflow_dependencies(audit_id);

-- 8. URL Inventory
CREATE TABLE IF NOT EXISTS seo_url_inventory (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    url TEXT NOT NULL,
    url_hash TEXT NOT NULL,
    discovery_source TEXT NOT NULL, -- sitemap | inlink | seed
    classification_tier TEXT NOT NULL DEFAULT 'ELG', -- DISCOVERED | CRAWLED | RENDERED | DEEP_INSPECTED
    status_code INTEGER,
    click_depth INTEGER DEFAULT 0,
    is_indexable INTEGER DEFAULT 1,
    priority_tier INTEGER DEFAULT 2,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    UNIQUE(audit_id, url_hash)
);
CREATE INDEX IF NOT EXISTS idx_seo_url_inv_audit ON seo_url_inventory(audit_id, classification_tier);

-- 9. Crawl Sessions
CREATE TABLE IF NOT EXISTS seo_crawl_sessions (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    pages_discovered INTEGER NOT NULL DEFAULT 0,
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    pages_rendered INTEGER NOT NULL DEFAULT 0,
    pages_failed INTEGER NOT NULL DEFAULT 0,
    avg_ttfb_ms REAL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 10. Crawl Pages
CREATE TABLE IF NOT EXISTS seo_crawl_pages (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES seo_crawl_sessions(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    url_hash TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    ttfb_ms REAL,
    content_type TEXT,
    content_length INTEGER,
    redirect_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_crawl_pages_audit ON seo_crawl_pages(audit_id, url_hash);

-- 11. Page Snapshots (CAS references)
CREATE TABLE IF NOT EXISTS seo_page_snapshots (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    url_hash TEXT NOT NULL,
    raw_html_hash TEXT,
    rendered_dom_hash TEXT,
    har_snapshot_hash TEXT,
    screenshot_hash TEXT,
    storage_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_snapshots_audit ON seo_page_snapshots(audit_id, url_hash);

-- 12. HTTP Observations
CREATE TABLE IF NOT EXISTS seo_http_observations (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    url_hash TEXT NOT NULL,
    protocol TEXT,
    hsts_enabled INTEGER DEFAULT 0,
    compression TEXT,
    cache_control TEXT,
    server_header TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 13. DOM Observations
CREATE TABLE IF NOT EXISTS seo_dom_observations (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    url_hash TEXT NOT NULL,
    title TEXT,
    meta_description TEXT,
    h1_count INTEGER DEFAULT 0,
    canonical_tag TEXT,
    robots_meta TEXT,
    images_count INTEGER DEFAULT 0,
    missing_alt_count INTEGER DEFAULT 0,
    internal_links_count INTEGER DEFAULT 0,
    external_links_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 14. Metrics
CREATE TABLE IF NOT EXISTS seo_metrics (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    url_hash TEXT,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    rating TEXT, -- GOOD | NEEDS_IMPROVEMENT | POOR
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_metrics_audit ON seo_metrics(audit_id, metric_name);

-- 15. Findings
CREATE TABLE IF NOT EXISTS seo_findings (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL, -- CRITICAL | HIGH | MEDIUM | LOW | INFO
    title TEXT NOT NULL,
    affected_urls_count INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'OPEN',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_findings_audit ON seo_findings(audit_id, severity);

-- 16. Finding Evidence
CREATE TABLE IF NOT EXISTS seo_finding_evidence (
    id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL REFERENCES seo_findings(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    url_hash TEXT,
    evidence_id TEXT NOT NULL,
    dom_selector TEXT,
    snippet TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 17. Recommendations
CREATE TABLE IF NOT EXISTS seo_recommendations (
    id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL REFERENCES seo_findings(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    priority TEXT NOT NULL DEFAULT 'P1', -- P0 | P1 | P2 | P3
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    effort_estimate TEXT DEFAULT 'MEDIUM',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 18. Remediation Tasks
CREATE TABLE IF NOT EXISTS seo_remediation_tasks (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT NOT NULL REFERENCES seo_recommendations(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'BACKLOG',
    patch_type TEXT,
    diff_payload TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 19. Verification Runs
CREATE TABLE IF NOT EXISTS seo_verification_runs (
    id TEXT PRIMARY KEY,
    remediation_task_id TEXT NOT NULL REFERENCES seo_remediation_tasks(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    status TEXT NOT NULL, -- VERIFIED | REJECTED | UNVERIFIED
    verification_check TEXT NOT NULL,
    executed_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 20. Scorecards
CREATE TABLE IF NOT EXISTS seo_scorecards (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    overall_score REAL NOT NULL,
    technical_score REAL,
    content_score REAL,
    onpage_score REAL,
    schema_score REAL,
    authority_score REAL,
    methodology_version TEXT NOT NULL,
    sealed_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 21. Score Components
CREATE TABLE IF NOT EXISTS seo_score_components (
    id TEXT PRIMARY KEY,
    scorecard_id TEXT NOT NULL REFERENCES seo_scorecards(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL,
    component_name TEXT NOT NULL,
    weight REAL NOT NULL,
    raw_score REAL NOT NULL,
    penalty REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 22. Connectors
CREATE TABLE IF NOT EXISTS seo_connectors (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    connector_type TEXT NOT NULL, -- GSC | GA4 | PAGESPEED | DATAFORSEO | BACKLINKS
    status TEXT NOT NULL DEFAULT 'DISCONNECTED', -- CONNECTED | DISCONNECTED | ERROR
    last_synced_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 23. Competitor Profiles
CREATE TABLE IF NOT EXISTS seo_competitor_profiles (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    competitor_domain TEXT NOT NULL,
    market_overlap_pct REAL,
    organic_keyword_gap_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 24. Keyword Datasets
CREATE TABLE IF NOT EXISTS seo_keyword_datasets (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    intent TEXT,
    search_volume INTEGER DEFAULT 0,
    current_position INTEGER,
    serp_features TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 25. Report Publications
CREATE TABLE IF NOT EXISTS seo_report_publications (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    format TEXT NOT NULL, -- HTML | PDF | JSON
    status TEXT NOT NULL DEFAULT 'PUBLISHED',
    publication_url TEXT,
    published_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 26. Methodology Versions
CREATE TABLE IF NOT EXISTS seo_methodology_versions (
    version_tag TEXT PRIMARY KEY,
    formula_spec TEXT NOT NULL,
    released_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);
"""


def init_seo_orchestrator_schema(db_path: str = "data/dristik_enterprise.db") -> None:
    """Idempotently initializes all 26 orchestrator tables and indexes."""
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SEO_ORCHESTRATOR_SQLITE_SCHEMA)
        conn.commit()
    finally:
        conn.close()

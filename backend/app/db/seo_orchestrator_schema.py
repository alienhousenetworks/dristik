"""
Enterprise Relational Schema for the Central SEO Orchestrator and Workflow Engine.
Defines all 26 authoritative entities with org/workspace tenant scoping, audit linkage,
immutable timestamps, idempotent column migrations, and performance indexes.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Dict, List, Optional, Tuple


def default_seo_db_path() -> str:
    try:
        from app.core.config import settings
        return getattr(settings, "AUDIT_DATABASE_PATH", None) or "data/dristik_audits.db"
    except Exception:
        return "data/dristik_audits.db"


SEO_ORCHESTRATOR_SQLITE_SCHEMA = """
-- 1. Master SEO Audit Runs
CREATE TABLE IF NOT EXISTS seo_audit_runs (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'STANDARD', -- QUICK | STANDARD | DEEP | CONTINUOUS
    status TEXT NOT NULL DEFAULT 'QUEUED', -- QUEUED | RUNNING | PAUSED | COMPLETED | PARTIAL | FAILED | CANCELLED
    current_stage TEXT NOT NULL DEFAULT 'INIT',
    execution_budget_sec INTEGER NOT NULL DEFAULT 300,
    elapsed_time_sec REAL NOT NULL DEFAULT 0.0,
    total_tasks INTEGER NOT NULL DEFAULT 0,
    completed_tasks INTEGER NOT NULL DEFAULT 0,
    failed_tasks INTEGER NOT NULL DEFAULT 0,
    overall_score REAL,
    qa_status TEXT DEFAULT 'PENDING',
    idempotency_key TEXT,
    canonical_assessment_json TEXT,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_audit_runs_ws_status ON seo_audit_runs(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_seo_audit_runs_org_domain ON seo_audit_runs(org_id, domain);
CREATE INDEX IF NOT EXISTS idx_seo_audit_runs_domain ON seo_audit_runs(domain);

-- 2. Audit Configurations
CREATE TABLE IF NOT EXISTS seo_audit_configurations (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL DEFAULT '',
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

-- 3. Agent Registry (40 Specialist Roles across 10 Departments)
CREATE TABLE IF NOT EXISTS seo_agent_registry (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    group_name TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'general',
    version TEXT NOT NULL DEFAULT 'v2',
    mode TEXT NOT NULL DEFAULT 'deterministic', -- deterministic | ai_assisted | connector_gated
    timeout_sec INTEGER NOT NULL DEFAULT 60,
    retry_limit INTEGER NOT NULL DEFAULT 2,
    required_connector TEXT,
    required_inputs TEXT DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 4. Agent Executions
CREATE TABLE IF NOT EXISTS seo_agent_executions (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
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
    workspace_id TEXT NOT NULL DEFAULT '',
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
    workspace_id TEXT NOT NULL DEFAULT '',
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

-- 8. URL Inventory (6-Tier Reconciled Taxonomy)
CREATE TABLE IF NOT EXISTS seo_url_inventory (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL,
    url TEXT NOT NULL,
    url_hash TEXT NOT NULL,
    discovery_source TEXT NOT NULL, -- sitemap | inlink | seed
    classification_tier TEXT NOT NULL DEFAULT 'DISCOVERED', -- DISCOVERED | CRAWLED | RENDERED | DEEP_INSPECTED
    page_type TEXT DEFAULT 'page',
    template_pattern TEXT DEFAULT '/*',
    language TEXT,
    status_code INTEGER,
    click_depth INTEGER DEFAULT 0,
    is_indexable INTEGER DEFAULT 1,
    canonical_url TEXT,
    priority_tier INTEGER DEFAULT 2,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    UNIQUE(audit_id, url_hash)
);
CREATE INDEX IF NOT EXISTS idx_seo_url_inv_audit ON seo_url_inventory(audit_id, classification_tier);

-- 9. Crawl Sessions
CREATE TABLE IF NOT EXISTS seo_crawl_sessions (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL,
    pages_discovered INTEGER NOT NULL DEFAULT 0,
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    pages_rendered INTEGER NOT NULL DEFAULT 0,
    pages_deeply_inspected INTEGER NOT NULL DEFAULT 0,
    pages_with_verified_findings INTEGER NOT NULL DEFAULT 0,
    pages_failed INTEGER NOT NULL DEFAULT 0,
    sampling_status TEXT NOT NULL DEFAULT 'SAMPLED_AUDIT',
    avg_ttfb_ms REAL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 10. Crawl Pages
CREATE TABLE IF NOT EXISTS seo_crawl_pages (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES seo_crawl_sessions(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    url_hash TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    ttfb_ms REAL,
    content_type TEXT,
    content_length INTEGER,
    redirect_url TEXT,
    page_payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_crawl_pages_audit ON seo_crawl_pages(audit_id, url_hash);

-- 11. Page Snapshots (CAS references)
CREATE TABLE IF NOT EXISTS seo_page_snapshots (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL DEFAULT '',
    url TEXT,
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
    workspace_id TEXT NOT NULL DEFAULT '',
    url_hash TEXT NOT NULL,
    protocol TEXT,
    hsts_enabled INTEGER DEFAULT 0,
    compression TEXT,
    cache_control TEXT,
    server_header TEXT,
    x_robots_tag TEXT,
    headers_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 13. DOM Observations
CREATE TABLE IF NOT EXISTS seo_dom_observations (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL DEFAULT '',
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
    schema_types_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 14. Metrics
CREATE TABLE IF NOT EXISTS seo_metrics (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL DEFAULT '',
    url_hash TEXT,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    measurement_type TEXT DEFAULT 'lab', -- lab | field | deterministic
    rating TEXT, -- GOOD | NEEDS_IMPROVEMENT | POOR
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_metrics_audit ON seo_metrics(audit_id, metric_name);

-- 15. Findings (Full 15-State Lifecycle + Root-Cause Deduplication)
CREATE TABLE IF NOT EXISTS seo_findings (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    root_cause_id TEXT,
    category TEXT NOT NULL,
    severity TEXT NOT NULL, -- CRITICAL | HIGH | MEDIUM | LOW | INFO
    title TEXT NOT NULL,
    description TEXT,
    recommendation TEXT,
    recommendation_id TEXT,
    affected_urls_json TEXT DEFAULT '[]',
    affected_urls_count INTEGER NOT NULL DEFAULT 1,
    evidence_ids_json TEXT DEFAULT '[]',
    business_impact_json TEXT DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'VERIFIED',
    assigned_owner TEXT,
    verification_required INTEGER NOT NULL DEFAULT 1,
    status_history_json TEXT DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_findings_audit ON seo_findings(audit_id, severity);
CREATE INDEX IF NOT EXISTS idx_seo_findings_rc ON seo_findings(audit_id, root_cause_id);

-- 16. Finding Evidence (14-Field Canonical Evidence Record)
CREATE TABLE IF NOT EXISTS seo_finding_evidence (
    id TEXT PRIMARY KEY,
    finding_id TEXT REFERENCES seo_findings(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL DEFAULT '',
    url TEXT,
    url_hash TEXT,
    evidence_id TEXT NOT NULL,
    check_id TEXT,
    source_type TEXT DEFAULT 'rendered_dom',
    source_location TEXT,
    observed_value TEXT,
    expected_value TEXT,
    result TEXT DEFAULT 'failed',
    evidence_status TEXT DEFAULT 'verified',
    snapshot_id TEXT,
    content_sha256 TEXT,
    agent_id TEXT,
    methodology_version TEXT DEFAULT 'dristik_seo_v3.0',
    dom_selector TEXT,
    snippet TEXT,
    observed_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_evidence_audit ON seo_finding_evidence(audit_id, evidence_id);

-- 17. Recommendations
CREATE TABLE IF NOT EXISTS seo_recommendations (
    id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL REFERENCES seo_findings(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'P1', -- P0 | P1 | P2 | P3
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    effort_estimate TEXT DEFAULT 'MEDIUM',
    owner_role TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 18. Remediation Tasks
CREATE TABLE IF NOT EXISTS seo_remediation_tasks (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT,
    finding_id TEXT,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL,
    title TEXT,
    fix_type TEXT,
    priority TEXT DEFAULT 'P1',
    status TEXT NOT NULL DEFAULT 'REMEDIATION_PLANNED',
    approval_status TEXT DEFAULT 'PENDING_APPROVAL',
    assigned_owner TEXT,
    department TEXT DEFAULT 'Engineering',
    effort TEXT,
    due_date TEXT,
    patch_type TEXT,
    diff_payload TEXT,
    acceptance_criteria TEXT,
    verification_protocol TEXT,
    dependencies_json TEXT DEFAULT '[]',
    implementation_json TEXT DEFAULT '{}',
    affected_scope_json TEXT DEFAULT '{}',
    before_evidence_json TEXT DEFAULT '{}',
    after_evidence_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_rem_tasks_audit ON seo_remediation_tasks(audit_id, status);

-- 19. Verification Runs (Independent Retest Proof)
CREATE TABLE IF NOT EXISTS seo_verification_runs (
    id TEXT PRIMARY KEY,
    remediation_task_id TEXT NOT NULL REFERENCES seo_remediation_tasks(id) ON DELETE CASCADE,
    finding_id TEXT,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL DEFAULT '',
    target_url TEXT,
    status TEXT NOT NULL, -- VERIFIED_FIXED | STILL_OPEN | FAILED | NOT_VERIFIABLE
    passed INTEGER NOT NULL DEFAULT 0,
    verification_check TEXT NOT NULL,
    before_snapshot_json TEXT DEFAULT '{}',
    after_snapshot_json TEXT DEFAULT '{}',
    diff_summary_json TEXT DEFAULT '{}',
    verified_by TEXT DEFAULT 'seo_verification_engine',
    executed_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_verif_runs_task ON seo_verification_runs(remediation_task_id, executed_at);

-- 20. Scorecards (9 Dimensions + 5 Confidence Vectors)
CREATE TABLE IF NOT EXISTS seo_scorecards (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL DEFAULT '',
    overall_score REAL,
    score_status TEXT NOT NULL DEFAULT 'MEASURED',
    overall_interpretation TEXT,
    technical_score REAL,
    indexation_score REAL,
    content_score REAL,
    onpage_score REAL,
    internal_linking_score REAL,
    schema_score REAL,
    performance_score REAL,
    specialist_score REAL,
    authority_score REAL,
    active_weight_sum REAL DEFAULT 0.0,
    measured_dimensions_count INTEGER DEFAULT 0,
    excluded_dimensions_count INTEGER DEFAULT 0,
    audit_coverage_pct REAL DEFAULT 0.0,
    evidence_confidence_pct REAL DEFAULT 0.0,
    data_freshness_hours REAL DEFAULT 0.0,
    connector_completeness_pct REAL DEFAULT 0.0,
    sampling_status TEXT DEFAULT 'SAMPLED_AUDIT',
    disclosures_json TEXT DEFAULT '[]',
    raw_json TEXT,
    methodology_version TEXT NOT NULL,
    sealed_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_scorecards_audit ON seo_scorecards(audit_id);

-- 21. Score Components
CREATE TABLE IF NOT EXISTS seo_score_components (
    id TEXT PRIMARY KEY,
    scorecard_id TEXT NOT NULL REFERENCES seo_scorecards(id) ON DELETE CASCADE,
    audit_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL DEFAULT '',
    component_name TEXT NOT NULL,
    weight REAL NOT NULL,
    effective_weight REAL,
    is_applicable INTEGER NOT NULL DEFAULT 1,
    is_measured INTEGER NOT NULL DEFAULT 1,
    raw_score REAL,
    passed_checks INTEGER DEFAULT 0,
    executed_checks INTEGER DEFAULT 0,
    penalty REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 22. Connectors (Encrypted Tenant-Scoped Credentials)
CREATE TABLE IF NOT EXISTS seo_connectors (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL,
    connector_type TEXT NOT NULL, -- google_search_console | google_analytics_4 | pagespeed_crux | backlink_provider | keyword_serp_provider | google_business_profile | bing_webmaster
    status TEXT NOT NULL DEFAULT 'NOT_CONFIGURED', -- CONNECTED | NOT_CONFIGURED | ERROR | QUOTA_EXCEEDED
    encrypted_credentials TEXT,
    scopes_json TEXT DEFAULT '[]',
    daily_quota_limit INTEGER NOT NULL DEFAULT 10000,
    daily_quota_used INTEGER NOT NULL DEFAULT 0,
    health_message TEXT DEFAULT '',
    last_synced_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    UNIQUE(workspace_id, connector_type)
);
CREATE INDEX IF NOT EXISTS idx_seo_connectors_ws ON seo_connectors(workspace_id, connector_type);

-- 23. Competitor Profiles
CREATE TABLE IF NOT EXISTS seo_competitor_profiles (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL,
    competitor_domain TEXT NOT NULL,
    market_overlap_pct REAL,
    organic_keyword_gap_count INTEGER DEFAULT 0,
    source_provider TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 24. Keyword Datasets
CREATE TABLE IF NOT EXISTS seo_keyword_datasets (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL DEFAULT '',
    keyword TEXT NOT NULL,
    intent TEXT,
    search_volume INTEGER,
    keyword_difficulty REAL,
    cpc REAL,
    current_position REAL,
    target_url TEXT,
    serp_features TEXT,
    source_provider TEXT NOT NULL DEFAULT 'unconnected',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

-- 25. Report Publications (Versioned, QA-Gated, Integrity-Hashed Archives)
CREATE TABLE IF NOT EXISTS seo_report_publications (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES seo_audit_runs(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL DEFAULT '',
    workspace_id TEXT NOT NULL DEFAULT '',
    profile TEXT NOT NULL DEFAULT 'complete_book',
    format TEXT NOT NULL, -- HTML | PDF | JSON
    status TEXT NOT NULL DEFAULT 'PUBLISHED', -- PUBLISHED | DRAFT_BLOCKED | PARTIAL_PUBLISHED
    qa_status TEXT NOT NULL DEFAULT 'CERTIFIED',
    qa_report_json TEXT,
    included_chapters_json TEXT DEFAULT '[]',
    sha256_integrity_hash TEXT,
    publication_url TEXT,
    html_content TEXT,
    created_by TEXT,
    published_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);
CREATE INDEX IF NOT EXISTS idx_seo_pubs_audit ON seo_report_publications(audit_id, published_at);

-- 26. Methodology Versions
CREATE TABLE IF NOT EXISTS seo_methodology_versions (
    version_tag TEXT PRIMARY KEY,
    formula_spec TEXT NOT NULL,
    released_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);
"""

_COLUMN_MIGRATIONS: Dict[str, List[Tuple[str, str]]] = {
    "seo_audit_runs": [
        ("org_id", "TEXT NOT NULL DEFAULT ''"),
        ("qa_status", "TEXT DEFAULT 'PENDING'"),
        ("idempotency_key", "TEXT"),
        ("canonical_assessment_json", "TEXT"),
    ],
    "seo_audit_configurations": [("org_id", "TEXT NOT NULL DEFAULT ''")],
    "seo_agent_registry": [
        ("department", "TEXT NOT NULL DEFAULT 'general'"),
        ("required_connector", "TEXT"),
    ],
    "seo_agent_executions": [("org_id", "TEXT NOT NULL DEFAULT ''")],
    "seo_agent_outputs": [("workspace_id", "TEXT NOT NULL DEFAULT ''")],
    "seo_workflow_tasks": [("workspace_id", "TEXT NOT NULL DEFAULT ''")],
    "seo_url_inventory": [
        ("org_id", "TEXT NOT NULL DEFAULT ''"),
        ("page_type", "TEXT DEFAULT 'page'"),
        ("template_pattern", "TEXT DEFAULT '/*'"),
        ("language", "TEXT"),
        ("canonical_url", "TEXT"),
    ],
    "seo_crawl_sessions": [
        ("org_id", "TEXT NOT NULL DEFAULT ''"),
        ("pages_deeply_inspected", "INTEGER NOT NULL DEFAULT 0"),
        ("pages_with_verified_findings", "INTEGER NOT NULL DEFAULT 0"),
        ("sampling_status", "TEXT NOT NULL DEFAULT 'SAMPLED_AUDIT'"),
    ],
    "seo_crawl_pages": [
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("page_payload_json", "TEXT"),
    ],
    "seo_page_snapshots": [
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("url", "TEXT"),
    ],
    "seo_http_observations": [
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("x_robots_tag", "TEXT"),
        ("headers_json", "TEXT"),
    ],
    "seo_dom_observations": [
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("schema_types_json", "TEXT"),
    ],
    "seo_metrics": [
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("measurement_type", "TEXT DEFAULT 'lab'"),
    ],
    "seo_findings": [
        ("org_id", "TEXT NOT NULL DEFAULT ''"),
        ("root_cause_id", "TEXT"),
        ("description", "TEXT"),
        ("recommendation", "TEXT"),
        ("recommendation_id", "TEXT"),
        ("affected_urls_json", "TEXT DEFAULT '[]'"),
        ("evidence_ids_json", "TEXT DEFAULT '[]'"),
        ("business_impact_json", "TEXT DEFAULT '{}'"),
        ("assigned_owner", "TEXT"),
        ("verification_required", "INTEGER NOT NULL DEFAULT 1"),
        ("status_history_json", "TEXT DEFAULT '[]'"),
        ("updated_at", "TEXT NOT NULL DEFAULT (datetime('now', 'utc'))"),
    ],
    "seo_finding_evidence": [
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("url", "TEXT"),
        ("check_id", "TEXT"),
        ("source_type", "TEXT DEFAULT 'rendered_dom'"),
        ("source_location", "TEXT"),
        ("observed_value", "TEXT"),
        ("expected_value", "TEXT"),
        ("result", "TEXT DEFAULT 'failed'"),
        ("evidence_status", "TEXT DEFAULT 'verified'"),
        ("snapshot_id", "TEXT"),
        ("content_sha256", "TEXT"),
        ("agent_id", "TEXT"),
        ("methodology_version", "TEXT DEFAULT 'dristik_seo_v3.0'"),
        ("observed_at", "TEXT NOT NULL DEFAULT (datetime('now', 'utc'))"),
    ],
    "seo_recommendations": [
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("owner_role", "TEXT"),
    ],
    "seo_remediation_tasks": [
        ("finding_id", "TEXT"),
        ("org_id", "TEXT NOT NULL DEFAULT ''"),
        ("title", "TEXT"),
        ("fix_type", "TEXT"),
        ("priority", "TEXT DEFAULT 'P1'"),
        ("approval_status", "TEXT DEFAULT 'PENDING_APPROVAL'"),
        ("assigned_owner", "TEXT"),
        ("department", "TEXT DEFAULT 'Engineering'"),
        ("effort", "TEXT"),
        ("due_date", "TEXT"),
        ("acceptance_criteria", "TEXT"),
        ("verification_protocol", "TEXT"),
        ("dependencies_json", "TEXT DEFAULT '[]'"),
        ("implementation_json", "TEXT DEFAULT '{}'"),
        ("affected_scope_json", "TEXT DEFAULT '{}'"),
        ("before_evidence_json", "TEXT DEFAULT '{}'"),
        ("after_evidence_json", "TEXT DEFAULT '{}'"),
        ("updated_at", "TEXT NOT NULL DEFAULT (datetime('now', 'utc'))"),
    ],
    "seo_verification_runs": [
        ("finding_id", "TEXT"),
        ("org_id", "TEXT NOT NULL DEFAULT ''"),
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("target_url", "TEXT"),
        ("passed", "INTEGER NOT NULL DEFAULT 0"),
        ("before_snapshot_json", "TEXT DEFAULT '{}'"),
        ("after_snapshot_json", "TEXT DEFAULT '{}'"),
        ("diff_summary_json", "TEXT DEFAULT '{}'"),
        ("verified_by", "TEXT DEFAULT 'seo_verification_engine'"),
    ],
    "seo_scorecards": [
        ("org_id", "TEXT NOT NULL DEFAULT ''"),
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("score_status", "TEXT NOT NULL DEFAULT 'MEASURED'"),
        ("overall_interpretation", "TEXT"),
        ("indexation_score", "REAL"),
        ("internal_linking_score", "REAL"),
        ("performance_score", "REAL"),
        ("specialist_score", "REAL"),
        ("active_weight_sum", "REAL DEFAULT 0.0"),
        ("measured_dimensions_count", "INTEGER DEFAULT 0"),
        ("excluded_dimensions_count", "INTEGER DEFAULT 0"),
        ("audit_coverage_pct", "REAL DEFAULT 0.0"),
        ("evidence_confidence_pct", "REAL DEFAULT 0.0"),
        ("data_freshness_hours", "REAL DEFAULT 0.0"),
        ("connector_completeness_pct", "REAL DEFAULT 0.0"),
        ("sampling_status", "TEXT DEFAULT 'SAMPLED_AUDIT'"),
        ("disclosures_json", "TEXT DEFAULT '[]'"),
        ("raw_json", "TEXT"),
    ],
    "seo_score_components": [
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("effective_weight", "REAL"),
        ("is_applicable", "INTEGER NOT NULL DEFAULT 1"),
        ("is_measured", "INTEGER NOT NULL DEFAULT 1"),
        ("passed_checks", "INTEGER DEFAULT 0"),
        ("executed_checks", "INTEGER DEFAULT 0"),
    ],
    "seo_connectors": [
        ("org_id", "TEXT NOT NULL DEFAULT ''"),
        ("encrypted_credentials", "TEXT"),
        ("scopes_json", "TEXT DEFAULT '[]'"),
        ("daily_quota_limit", "INTEGER NOT NULL DEFAULT 10000"),
        ("daily_quota_used", "INTEGER NOT NULL DEFAULT 0"),
        ("health_message", "TEXT DEFAULT ''"),
        ("updated_at", "TEXT NOT NULL DEFAULT (datetime('now', 'utc'))"),
    ],
    "seo_competitor_profiles": [
        ("org_id", "TEXT NOT NULL DEFAULT ''"),
        ("source_provider", "TEXT"),
    ],
    "seo_keyword_datasets": [
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("keyword_difficulty", "REAL"),
        ("cpc", "REAL"),
        ("target_url", "TEXT"),
        ("source_provider", "TEXT NOT NULL DEFAULT 'unconnected'"),
    ],
    "seo_report_publications": [
        ("org_id", "TEXT NOT NULL DEFAULT ''"),
        ("workspace_id", "TEXT NOT NULL DEFAULT ''"),
        ("profile", "TEXT NOT NULL DEFAULT 'complete_book'"),
        ("qa_status", "TEXT NOT NULL DEFAULT 'CERTIFIED'"),
        ("qa_report_json", "TEXT"),
        ("included_chapters_json", "TEXT DEFAULT '[]'"),
        ("sha256_integrity_hash", "TEXT"),
        ("html_content", "TEXT"),
        ("created_by", "TEXT"),
    ],
}


def _apply_column_migrations(conn: sqlite3.Connection) -> None:
    for table, migrations in _COLUMN_MIGRATIONS.items():
        cur = conn.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cur.fetchall()}
        if not existing:
            continue
        for col_name, col_def in migrations:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")


def init_seo_orchestrator_schema(db_path: Optional[str] = None) -> None:
    """Idempotently initializes all 26 orchestrator tables, migrations, and indexes."""
    resolved = db_path or default_seo_db_path()
    os.makedirs(os.path.dirname(resolved) if os.path.dirname(resolved) else ".", exist_ok=True)
    conn = sqlite3.connect(resolved)
    try:
        conn.executescript(SEO_ORCHESTRATOR_SQLITE_SCHEMA)
        _apply_column_migrations(conn)
        conn.commit()
    finally:
        conn.close()

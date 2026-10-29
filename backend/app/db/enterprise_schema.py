"""
Enterprise SaaS PostgreSQL & SQLite Relational Schema
Implements the 8 foundational tables from docs/ENTERPRISE_SAAS_UPGRADE_ROADMAP.md:
1. organizations
2. workspaces
3. domains
4. audit_runs
5. evidence_nodes
6. findings
7. ai_citations
8. enterprise_audit_logs
"""
import os
import sqlite3
from typing import Optional, Dict, Any, List

ENTERPRISE_POSTGRES_SCHEMA = """
-- 1. Organizations & Tenancy
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    plan VARCHAR(50) NOT NULL DEFAULT 'enterprise',
    sso_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    sso_provider VARCHAR(50),
    sso_metadata_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Workspaces
CREATE TABLE IF NOT EXISTS workspaces (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (org_id, slug)
);

-- 3. Domains & Monitored Properties
CREATE TABLE IF NOT EXISTS domains (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    hostname VARCHAR(255) NOT NULL,
    default_scheme VARCHAR(10) NOT NULL DEFAULT 'https',
    site_type VARCHAR(50) NOT NULL DEFAULT 'b2b_saas',
    crawl_frequency VARCHAR(50) NOT NULL DEFAULT 'weekly',
    max_pages INT NOT NULL DEFAULT 500,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Audit Runs & Execution State
CREATE TABLE IF NOT EXISTS audit_runs (
    id VARCHAR(64) PRIMARY KEY,
    domain_id VARCHAR(64) NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    triggered_by VARCHAR(64),
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    stage VARCHAR(50) NOT NULL DEFAULT 'discovery',
    pages_crawled INT NOT NULL DEFAULT 0,
    overall_score INT,
    confidence_score INT,
    evidence_coverage INT,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Evidence Nodes & Storage References
CREATE TABLE IF NOT EXISTS evidence_nodes (
    id VARCHAR(64) PRIMARY KEY,
    audit_run_id VARCHAR(64) NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    storage_uri TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Audit Findings & Remediation Items
CREATE TABLE IF NOT EXISTS findings (
    id VARCHAR(64) PRIMARY KEY,
    audit_run_id VARCHAR(64) NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    impact_explanation TEXT NOT NULL,
    remediation_advice TEXT NOT NULL,
    suggested_patch JSONB,
    jira_issue_key VARCHAR(50),
    github_pr_url TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Live AI Citation Tracking
CREATE TABLE IF NOT EXISTS ai_citations (
    id VARCHAR(64) PRIMARY KEY,
    domain_id VARCHAR(64) NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    engine VARCHAR(50) NOT NULL,
    is_cited BOOLEAN NOT NULL DEFAULT FALSE,
    citation_rank INT,
    cited_url TEXT,
    extracted_snippet TEXT,
    competitor_citations JSONB DEFAULT '[]',
    queried_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. Enterprise Audit Logs (SOC 2)
CREATE TABLE IF NOT EXISTS enterprise_audit_logs (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id VARCHAR(64),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

ENTERPRISE_SQLITE_SCHEMA = """
-- 1. Organizations & Tenancy
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    plan TEXT NOT NULL DEFAULT 'enterprise',
    sso_enabled INTEGER NOT NULL DEFAULT 0,
    sso_provider TEXT,
    sso_metadata_url TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. Workspaces
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (org_id, slug)
);

-- 3. Domains & Monitored Properties
CREATE TABLE IF NOT EXISTS domains (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    hostname TEXT NOT NULL,
    default_scheme TEXT NOT NULL DEFAULT 'https',
    site_type TEXT NOT NULL DEFAULT 'b2b_saas',
    crawl_frequency TEXT NOT NULL DEFAULT 'weekly',
    max_pages INTEGER NOT NULL DEFAULT 500,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- 4. Audit Runs & Execution State
CREATE TABLE IF NOT EXISTS audit_runs (
    id TEXT PRIMARY KEY,
    domain_id TEXT NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    triggered_by TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    stage TEXT NOT NULL DEFAULT 'discovery',
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    overall_score INTEGER,
    confidence_score INTEGER,
    evidence_coverage INTEGER,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL
);

-- 5. Evidence Nodes & Storage References
CREATE TABLE IF NOT EXISTS evidence_nodes (
    id TEXT PRIMARY KEY,
    audit_run_id TEXT NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    node_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

-- 6. Audit Findings & Remediation Items
CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    audit_run_id TEXT NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    impact_explanation TEXT NOT NULL,
    remediation_advice TEXT NOT NULL,
    suggested_patch TEXT,
    jira_issue_key TEXT,
    github_pr_url TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);

-- 7. Live AI Citation Tracking
CREATE TABLE IF NOT EXISTS ai_citations (
    id TEXT PRIMARY KEY,
    domain_id TEXT NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    engine TEXT NOT NULL,
    is_cited INTEGER NOT NULL DEFAULT 0,
    citation_rank INTEGER,
    cited_url TEXT,
    extracted_snippet TEXT,
    competitor_citations TEXT DEFAULT '[]',
    queried_at TEXT NOT NULL
);

-- 8. Enterprise Audit Logs (SOC 2)
CREATE TABLE IF NOT EXISTS enterprise_audit_logs (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    payload TEXT,
    created_at TEXT NOT NULL
);

-- Indexes for optimal enterprise querying
CREATE INDEX IF NOT EXISTS idx_workspaces_org ON workspaces(org_id);
CREATE INDEX IF NOT EXISTS idx_domains_workspace ON domains(workspace_id);
CREATE INDEX IF NOT EXISTS idx_audit_runs_domain ON audit_runs(domain_id);
CREATE INDEX IF NOT EXISTS idx_evidence_nodes_run ON evidence_nodes(audit_run_id);
CREATE INDEX IF NOT EXISTS idx_findings_run ON findings(audit_run_id);
CREATE INDEX IF NOT EXISTS idx_ai_citations_domain ON ai_citations(domain_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON enterprise_audit_logs(org_id);
"""


def init_enterprise_schema(db_path: str = "data/dristik_enterprise.db"):
    """Initializes the enterprise SQLite database schema if not present."""
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(ENTERPRISE_SQLITE_SCHEMA)
        conn.commit()
    finally:
        conn.close()

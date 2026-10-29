-- Continuous Keyword Tracking, SERP History, and Competitor Positions
-- Version 2 migration

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

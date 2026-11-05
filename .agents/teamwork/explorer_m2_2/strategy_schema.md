# Milestone M2 Technical Strategy: Unified Relational Schema & Alembic Migrations

**Author**: `explorer_m2_2`  
**Milestone**: M2 (Phase 1: Unified Enterprise Persistence & MockSession Elimination)  
**Target Features**: F07 (`MockSession` Elimination), F08 (`DATABASE_URL` in `Settings`), F09 (Unified Relational Schema & Alembic Migrations), F10 (Circular Import Fix)  
**Working Directory**: `/Users/sayantande/Downloads/dristik-main/.agents/teamwork/explorer_m2_2`  
**Scope**: `PROJECT.md`, `ORIGINAL_REQUEST.md`, `backend/app/db/`, `backend/migrations/`, `backend/alembic.ini`

---

## 1. Executive Summary

Milestone M2 resolves the persistence fragmentation and architectural instability in Dristik AI by establishing a production-grade relational database layer.

Currently, Dristik's persistence suffers from four critical defects:
1. **Database Fragmentation**: State is split across four distinct SQLite databases (`dristik.db`, `dristik_audits.db`, `external_authority.db`, `geo_aeo_pipeline.db`) and in-memory process dictionaries (`_WORKSPACES_STORE`, `_DOMAINS_STORE`), resulting in data desynchronization and lack of foreign key integrity.
2. **Silent Failure Fallback (`MockSession`)**: `backend/app/db/session.py:28-74` catches `ImportError` and falls back to a dummy `MockSession` where write operations (`add`, `refresh`) are no-ops and queries return `None`/`[]`. This causes silent data loss and phantom audit successes if dependencies fail.
3. **Broken Alembic Migration Pipeline**: `backend/alembic.ini` is missing logging sections, causing `alembic` CLI invocations to immediately crash with `KeyError: 'formatters'`. Furthermore, `backend/migrations/env.py` fails to import model classes, leaving `Base.metadata` with 0 tables, and no migration versions exist in `backend/migrations/versions/`.
4. **Test Suite Circular Import Blockers**: Test collection aborts with `ModuleNotFoundError: No module named 'app.persistence.models'` due to a circular import triggered when `app.domain.scoring.score_explanations:6` prematurely imports `app.persistence.models` before `app.persistence` has initialized its module dictionary.

This technical blueprint provides the exact, production-ready implementation strategy to unify the 8 enterprise tables (`organizations`, `workspaces`, `domains`, `audit_runs`, `evidence_nodes`, `findings`, `ai_citations`, `enterprise_audit_logs`) and application models into SQLAlchemy declarative classes, configure Alembic with cross-dialect compatibility (PostgreSQL and SQLite), eliminate `MockSession`, and resolve import cycles.

---

## 2. Codebase Investigation & Root Cause Analysis

### 2.1 The 8 Foundational Tables (`backend/app/db/enterprise_schema.py`)
`enterprise_schema.py` defines the canonical schema (`ENTERPRISE_POSTGRES_SCHEMA` and `ENTERPRISE_SQLITE_SCHEMA`) consisting of 8 foundational tables:

| # | Table Name | Primary Key | Foreign Keys | Key Columns | Existing Model Status |
|---|------------|-------------|--------------|-------------|-----------------------|
| 1 | `organizations` | `id VARCHAR(64)` | None | `name`, `slug`, `plan`, `sso_enabled`, `sso_provider`, `sso_metadata_url`, `created_at`, `updated_at` | Exists in `organization.py` (missing `sso_provider`, `sso_metadata_url`, `updated_at`) |
| 2 | `workspaces` | `id VARCHAR(64)` | `org_id -> organizations.id` | `name`, `slug`, `created_at`, `UNIQUE(org_id, slug)` | **Missing** (currently in-memory `_WORKSPACES_STORE`) |
| 3 | `domains` | `id VARCHAR(64)` | `workspace_id -> workspaces.id` | `hostname`, `default_scheme`, `site_type`, `crawl_frequency`, `max_pages`, `is_active`, `created_at` | **Missing** (currently in-memory `_DOMAINS_STORE`) |
| 4 | `audit_runs` | `id VARCHAR(64)` | `domain_id -> domains.id` | `triggered_by`, `status`, `stage`, `pages_crawled`, `overall_score`, `confidence_score`, `evidence_coverage`, `error_message`, `started_at`, `completed_at`, `created_at` | Exists in `audit_run.py` (has `domain` column instead of `domain_id`, missing confidence/coverage) |
| 5 | `evidence_nodes` | `id VARCHAR(64)` | `audit_run_id -> audit_runs.id` | `url`, `node_type`, `content_hash`, `storage_uri`, `metadata`, `created_at` | **Missing** (`evidence.py` defines legacy table `evidence`) |
| 6 | `findings` | `id VARCHAR(64)` | `audit_run_id -> audit_runs.id` | `code`, `category`, `severity`, `title`, `description`, `impact_explanation`, `remediation_advice`, `suggested_patch`, `jira_issue_key`, `github_pr_url`, `status`, `created_at` | Exists in `finding.py` (uses `audit_id` instead of `audit_run_id`, lacks `suggested_patch` and ticket links) |
| 7 | `ai_citations` | `id VARCHAR(64)` | `domain_id -> domains.id` | `query`, `engine`, `is_cited`, `citation_rank`, `cited_url`, `extracted_snippet`, `competitor_citations`, `queried_at` | **Missing** |
| 8 | `enterprise_audit_logs` | `id VARCHAR(64)` | `org_id -> organizations.id` | `user_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `user_agent`, `payload`, `created_at` | **Missing** (currently logged via `EnterpriseAuditLogger` to `dristik_enterprise.db`) |

### 2.2 Root Cause Analysis: Circular Import Bug (F10)
When pytest collects test files like `tests/test_enterprise_schema_and_cas.py` or `tests/test_audit_persistence_and_checkpoints.py`, collection aborts:
```
tests/test_enterprise_schema_and_cas.py:10: in <module>
    from app.persistence.enterprise_schema import init_enterprise_schema
app/persistence.py:11: in <module>
    from app.db import storage_cas, enterprise_schema, schema, repository
app/db/repository.py:18: in <module>
    from app.core.config import settings
app/core/__init__.py:14: in <module>
    from app.core.inference import (
app/core/inference/budget_manager.py:12: in <module>
    from app.domain.models import TelemetryData, StageCostRecord, SubStepCostRecord
app/domain/__init__.py:49: in <module>
    from app.domain.scoring import (
app/domain/scoring/score_explanations.py:6: in <module>
    from app.persistence.models import ScoreExplanation, ScoreExplanationDimension
E   ModuleNotFoundError: No module named 'app.persistence.models'
```
**Mechanism**:
1. `app.persistence` is being imported. It executes line 11 (`from app.db import repository`).
2. `app.db.repository` imports `settings`, which triggers `app.core` -> `app.domain` -> `app.domain.scoring.score_explanations`.
3. In `score_explanations.py:6`, it executes `from app.persistence.models import ScoreExplanation, ScoreExplanationDimension`.
4. But `app.persistence` has not reached line 19 (`sys.modules["app.persistence.models"] = models`).
5. Python raises `ModuleNotFoundError: No module named 'app.persistence.models'`.

**Furthermore**:
If `sys.modules["app.persistence.models"]` is assigned earlier, `app/db/repository.py:22` does `from app.db.models import ( EvidenceTraceItem, ... )`, which tries to import from `app.db.models.__init__.py` while it is partially initialized, raising:
`ImportError: cannot import name 'EvidenceTraceItem' from partially initialized module 'app.db.models'`.

**Direct Fix**:
1. In `backend/app/domain/scoring/score_explanations.py:6`:
   Replace `from app.persistence.models import ScoreExplanation, ScoreExplanationDimension` with:
   `from app.db.models.audit import ScoreExplanation, ScoreExplanationDimension`
   (Since `ScoreExplanation` and `ScoreExplanationDimension` are Pydantic schemas declared directly in `app/db/models/audit.py`).
2. In `backend/app/db/repository.py:22-27`:
   Change `from app.db.models import (...)` to:
   `from app.db.models.audit import ( EvidenceTraceItem, ScoreExplanation, ScoreExplanationDimension, StageCheckpoint )`
3. In `backend/conftest.py`:
   Pre-import `app.domain` and `app.connectors` so all compatibility shims are registered before test collection begins.

### 2.3 Root Cause Analysis: Alembic Configuration Defects
Running `alembic` commands currently results in two immediate failures:
1. **`KeyError: 'formatters'`**:
   `backend/migrations/env.py:11` unconditionally executes `fileConfig(config.config_file_name)`. Because `backend/alembic.ini` only contains `[alembic]` and `[logging]` without `[loggers]`, `[handlers]`, `[formatters]`, Python's `logging.config.fileConfig` crashes.
2. **Empty Metadata**:
   `backend/migrations/env.py:13-14` imports only `Base` (`from app.db.base import Base; target_metadata = Base.metadata`). Without importing `app.db.models`, none of the declarative classes have been loaded, so `target_metadata.tables` is empty (`{}`).
3. **Missing `versions/` Directory**:
   `backend/migrations/versions/` does not exist in the repository.

---

## 3. Unified Relational Models Architecture

To satisfy both the target enterprise schema and backward compatibility with existing services, all 8 enterprise tables and related application models must be declared under `backend/app/db/models/` using `Base` from `backend/app/db/base.py`.

### 3.1 `Organization` (`backend/app/db/models/organization.py`)
```python
from datetime import datetime, timezone
from sqlalchemy.orm import relationship, synonym
from app.db.base import Base, Column, String, Boolean, DateTime, Text

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    plan = Column(String(50), default="enterprise", nullable=False)
    sso_enabled = Column(Boolean, default=False, nullable=False)
    sso_provider = Column(String(50), nullable=True)
    sso_metadata_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Backward compatibility synonym for legacy code expecting .org_id
    org_id = synonym("id")

    # Relationships
    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
    enterprise_audit_logs = relationship("EnterpriseAuditLog", back_populates="organization", cascade="all, delete-orphan")
```

### 3.2 `Workspace` (`backend/app/db/models/workspace.py`) - NEW
```python
from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, DateTime, ForeignKey

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True, index=True)
    org_id = Column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_workspaces_org_slug"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="workspaces")
    domains = relationship("Domain", back_populates="workspace", cascade="all, delete-orphan")
```

### 3.3 `Domain` (`backend/app/db/models/domain.py`) - NEW
```python
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, Integer, Boolean, DateTime, ForeignKey

class Domain(Base):
    __tablename__ = "domains"

    id = Column(String(64), primary_key=True, index=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    hostname = Column(String(255), nullable=False, index=True)
    default_scheme = Column(String(10), default="https", nullable=False)
    site_type = Column(String(50), default="b2b_saas", nullable=False)
    crawl_frequency = Column(String(50), default="weekly", nullable=False)
    max_pages = Column(Integer, default=500, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="domains")
    audit_runs = relationship("AuditRun", back_populates="domain_rel", cascade="all, delete-orphan")
    ai_citations = relationship("AICitation", back_populates="domain", cascade="all, delete-orphan")
```

### 3.4 `AuditRun` (`backend/app/db/models/audit_run.py`) - RECONCILED
Harmonizes `enterprise_schema.py` requirements with existing pipeline fields:
```python
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON

class AuditRun(Base):
    __tablename__ = "audit_runs"

    id = Column(String(64), primary_key=True, index=True)
    domain_id = Column(String(64), ForeignKey("domains.id", ondelete="CASCADE"), nullable=True, index=True)
    domain = Column(String(255), nullable=True, index=True)
    triggered_by = Column(String(64), nullable=True)
    status = Column(String(50), default="queued", nullable=False)
    stage = Column(String(50), default="discovery", nullable=False)
    tier = Column(String(50), default="enterprise", nullable=True)
    pages_crawled = Column(Integer, default=0, nullable=False)
    findings_count = Column(Integer, default=0, nullable=False)
    overall_score = Column(Integer, nullable=True)
    total_score = Column(Float, default=0.0, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    evidence_coverage = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    config = Column(JSON, default=dict, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    domain_rel = relationship("Domain", back_populates="audit_runs")
    evidence_nodes = relationship("EvidenceNode", back_populates="audit_run", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="audit_run", cascade="all, delete-orphan")
```

### 3.5 `EvidenceNode` (`backend/app/db/models/evidence_node.py`) - NEW
```python
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, DateTime, ForeignKey, Text, JSON

class EvidenceNode(Base):
    __tablename__ = "evidence_nodes"

    id = Column(String(64), primary_key=True, index=True)
    audit_run_id = Column(String(64), ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    node_type = Column(String(50), nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    storage_uri = Column(Text, nullable=False)
    node_metadata = Column("metadata", JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    audit_run = relationship("AuditRun", back_populates="evidence_nodes")
```

### 3.6 `Finding` (`backend/app/db/models/finding.py`) - RECONCILED
Harmonizes `enterprise_schema.py` and existing finding fields:
```python
from datetime import datetime, timezone
from sqlalchemy.orm import relationship, synonym
from app.db.base import Base, Column, String, Float, DateTime, ForeignKey, Text, JSON

class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(64), primary_key=True, index=True)
    audit_run_id = Column(String(64), ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=True)
    category = Column(String(50), nullable=False)
    severity = Column(String(20), default="MEDIUM", nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    impact_explanation = Column(Text, nullable=True)
    remediation_advice = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    suggested_patch = Column(JSON, nullable=True)
    jira_issue_key = Column(String(50), nullable=True)
    github_pr_url = Column(Text, nullable=True)
    status = Column(String(50), default="open", nullable=False)
    remediation_status = Column(String(50), default="OPEN", nullable=True)
    confidence = Column(Float, default=1.0, nullable=True)
    evidence_ids = Column(JSON, default=list, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Backward compatibility synonym for code expecting .audit_id
    audit_id = synonym("audit_run_id")

    # Relationships
    audit_run = relationship("AuditRun", back_populates="findings")
```

### 3.7 `AICitation` (`backend/app/db/models/ai_citation.py`) - NEW
```python
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON

class AICitation(Base):
    __tablename__ = "ai_citations"

    id = Column(String(64), primary_key=True, index=True)
    domain_id = Column(String(64), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False, index=True)
    query = Column(Text, nullable=False)
    engine = Column(String(50), nullable=False)
    is_cited = Column(Boolean, default=False, nullable=False)
    citation_rank = Column(Integer, nullable=True)
    cited_url = Column(Text, nullable=True)
    extracted_snippet = Column(Text, nullable=True)
    competitor_citations = Column(JSON, default=list, nullable=True)
    queried_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    domain = relationship("Domain", back_populates="ai_citations")
```

### 3.8 `EnterpriseAuditLog` (`backend/app/db/models/enterprise_audit_log.py`) - NEW
```python
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, DateTime, ForeignKey, Text, JSON

class EnterpriseAuditLog(Base):
    __tablename__ = "enterprise_audit_logs"

    id = Column(String(64), primary_key=True, index=True)
    org_id = Column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    payload = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="enterprise_audit_logs")
```

### 3.9 Package Exports (`backend/app/db/models/__init__.py`)
Update `__all__` to expose the entire model graph:
```python
from app.db.models.organization import Organization
from app.db.models.workspace import Workspace
from app.db.models.domain import Domain
from app.db.models.audit_run import AuditRun
from app.db.models.evidence_node import EvidenceNode
from app.db.models.finding import Finding
from app.db.models.ai_citation import AICitation
from app.db.models.enterprise_audit_log import EnterpriseAuditLog
from app.db.models.user import User
from app.db.models.crawl_page import CrawlPage
from app.db.models.evidence import Evidence
from app.db.models.remediation import Remediation
from app.db.models.report import Report
from app.db.models.scorecard import Scorecard
from app.db.models.integration import Integration
from app.db.models.agent_execution import AgentExecution
from app.db.models.audit import (
    StageCheckpoint,
    ScoreExplanation,
    ScoreExplanationDimension,
    EvidenceTraceItem,
)

__all__ = [
    "Organization", "Workspace", "Domain", "AuditRun", "EvidenceNode",
    "Finding", "AICitation", "EnterpriseAuditLog", "User", "CrawlPage",
    "Evidence", "Remediation", "Report", "Scorecard", "Integration",
    "AgentExecution", "StageCheckpoint", "ScoreExplanation",
    "ScoreExplanationDimension", "EvidenceTraceItem",
]
```

---

## 4. Database Configuration & Fail-Fast Connectivity (F07 & F08)

### 4.1 `Settings` Configuration (`backend/app/core/config.py`)
Add explicit `DATABASE_URL` with default SQLite URI for zero-config local development, allowing PostgreSQL via environment variable:
```python
DATABASE_URL: str = Field(
    default="sqlite:///data/dristik.db",
    description="Unified relational database URL. Supports PostgreSQL (postgresql+psycopg2://...) and SQLite (sqlite:///...)."
)
```

### 4.2 Fail-Fast Connectivity Engine (`backend/app/db/session.py`)
Replace the entire contents of `session.py` to:
1. Delete `MockSession` completely.
2. Enable connection pool recycling (`pool_pre_ping=True`).
3. Implement `verify_database_connection` for startup diagnostics.

```python
"""
Unified Database Session & Engine Lifecycle Management.
Fail-fast connectivity without silent mock fallbacks.
"""
import logging
import os
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.db.base import Base

logger = logging.getLogger(__name__)

DATABASE_URL = getattr(settings, "DATABASE_URL", None) or os.getenv("DATABASE_URL", "sqlite:///data/dristik.db")

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verify_database_connection(timeout_seconds: float = 5.0) -> bool:
    """
    Verifies database connectivity during application startup.
    Fails fast with descriptive diagnostics if database is unreachable.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        sanitized = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
        logger.critical(f"FATAL: Database connection failed for {sanitized}: {exc}")
        raise RuntimeError(f"Database connection failure ({sanitized}): {exc}") from exc

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding an active SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes tables registered with Base.metadata."""
    import app.db.models  # Ensure all models are registered
    Base.metadata.create_all(bind=engine)
```

---

## 5. Alembic Configuration & Initial Migration (F09)

### 5.1 `backend/alembic.ini` Logging Sections
Add standard logging sections to prevent `KeyError: 'formatters'`:
```ini
[alembic]
script_location = migrations
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
prepend_sys_path = .
timezone = UTC
sqlalchemy.url = sqlite:///data/dristik.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 5.2 `backend/migrations/env.py`
Update `env.py` to:
1. Dynamically read URL from `settings.DATABASE_URL` (or env var).
2. Import `app.db.models` so all tables register with `target_metadata`.
3. Enable `render_as_batch=True` for SQLite compatibility.

```python
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

config = context.config

if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

# Ensure all models are loaded
from app.db.base import Base
import app.db.models
target_metadata = Base.metadata

def get_database_url() -> str:
    try:
        from app.core.config import settings
        if getattr(settings, "DATABASE_URL", None):
            return settings.DATABASE_URL
    except Exception:
        pass
    return os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")

def run_migrations_offline():
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 5.3 Initial Migration: `backend/migrations/versions/001_initial_enterprise_schema.py`
Create directory `backend/migrations/versions/` and script:
```python
"""Initial Unified Enterprise Schema

Revision ID: 001_enterprise_schema
Revises: 
Create Date: 2026-10-31 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_enterprise_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1. organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False, unique=True),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='enterprise'),
        sa.Column('sso_enabled', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('sso_provider', sa.String(length=50), nullable=True),
        sa.Column('sso_metadata_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'])
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])

    # 2. workspaces
    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('org_id', 'slug', name='uq_workspaces_org_slug'),
    )
    op.create_index('idx_workspaces_org', 'workspaces', ['org_id'])

    # 3. domains
    op.create_table(
        'domains',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('workspace_id', sa.String(length=64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('default_scheme', sa.String(length=10), nullable=False, server_default='https'),
        sa.Column('site_type', sa.String(length=50), nullable=False, server_default='b2b_saas'),
        sa.Column('crawl_frequency', sa.String(length=50), nullable=False, server_default='weekly'),
        sa.Column('max_pages', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_domains_workspace', 'domains', ['workspace_id'])
    op.create_index('ix_domains_hostname', 'domains', ['hostname'])

    # 4. audit_runs
    op.create_table(
        'audit_runs',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('domain_id', sa.String(length=64), sa.ForeignKey('domains.id', ondelete='CASCADE'), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('triggered_by', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('stage', sa.String(length=50), nullable=False, server_default='discovery'),
        sa.Column('tier', sa.String(length=50), nullable=True, server_default='enterprise'),
        sa.Column('pages_crawled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overall_score', sa.Integer(), nullable=True),
        sa.Column('total_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('confidence_score', sa.Integer(), nullable=True),
        sa.Column('evidence_coverage', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_audit_runs_domain', 'audit_runs', ['domain_id'])
    op.create_index('ix_audit_runs_domain_str', 'audit_runs', ['domain'])

    # 5. evidence_nodes
    op.create_table(
        'evidence_nodes',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('audit_run_id', sa.String(length=64), sa.ForeignKey('audit_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('storage_uri', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_evidence_nodes_run', 'evidence_nodes', ['audit_run_id'])
    op.create_index('idx_evidence_nodes_hash', 'evidence_nodes', ['content_hash'])

    # 6. findings
    op.create_table(
        'findings',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('audit_run_id', sa.String(length=64), sa.ForeignKey('audit_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('impact_explanation', sa.Text(), nullable=True),
        sa.Column('remediation_advice', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('suggested_patch', sa.JSON(), nullable=True),
        sa.Column('jira_issue_key', sa.String(length=50), nullable=True),
        sa.Column('github_pr_url', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('remediation_status', sa.String(length=50), nullable=True, server_default='OPEN'),
        sa.Column('confidence', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('evidence_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_findings_run', 'findings', ['audit_run_id'])

    # 7. ai_citations
    op.create_table(
        'ai_citations',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('domain_id', sa.String(length=64), sa.ForeignKey('domains.id', ondelete='CASCADE'), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('engine', sa.String(length=50), nullable=False),
        sa.Column('is_cited', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('citation_rank', sa.Integer(), nullable=True),
        sa.Column('cited_url', sa.Text(), nullable=True),
        sa.Column('extracted_snippet', sa.Text(), nullable=True),
        sa.Column('competitor_citations', sa.JSON(), nullable=True),
        sa.Column('queried_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_ai_citations_domain', 'ai_citations', ['domain_id'])

    # 8. enterprise_audit_logs
    op.create_table(
        'enterprise_audit_logs',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_audit_logs_org', 'enterprise_audit_logs', ['org_id'])

    # Supporting application tables: users, integrations, crawl_pages, evidence, remediations, reports, scorecards, agent_executions
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), server_default='member'),
        sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'integrations',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('credentials_encrypted', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('integrations')
    op.drop_table('users')
    op.drop_table('enterprise_audit_logs')
    op.drop_table('ai_citations')
    op.drop_table('findings')
    op.drop_table('evidence_nodes')
    op.drop_table('audit_runs')
    op.drop_table('domains')
    op.drop_table('workspaces')
    op.drop_table('organizations')
```

---

## 6. PostgreSQL & SQLite Cross-Dialect Compatibility Matrix

| Feature | PostgreSQL | SQLite | Unified SQLAlchemy Strategy |
|---|---|---|---|
| **JSON Fields** | Native `JSONB` | Stored as `TEXT` | `sqlalchemy.JSON`: handles transparent serialization and parses to Python `dict`/`list` on both engines. |
| **Timestamps** | `TIMESTAMPTZ` with timezone | ISO-8601 string or numeric | `DateTime(timezone=True)`: maps to `TIMESTAMPTZ` on Postgres and ISO string on SQLite. |
| **Boolean Flags** | Native `BOOLEAN` (`true`/`false`) | `INTEGER` (`0`/`1`) | `sa.Boolean`: maps to native boolean on PostgreSQL and integer on SQLite. |
| **Foreign Keys** | Always enforced | Enforced only with `PRAGMA foreign_keys = ON;` | SQLAlchemy listener or explicit `PRAGMA foreign_keys=ON` on connection. |
| **Schema Alterations** | Native `ALTER TABLE` | Table recreate / batch mode | Alembic `render_as_batch=True` enabled in `env.py`. |
| **Connection Pooling** | `pool_pre_ping=True`, pool recycling | In-memory or file lock (`check_same_thread=False`) | `create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})`. |
| **String / Text** | `VARCHAR(n)` and `TEXT` | `TEXT` | `String(length)` for indexed keys, `Text` for unbounded descriptions and URLs. |

---

## 7. Concrete Step-by-Step Implementation Action Plan for M2

### Step 1: Fix Circular Import in Scoring Explanations (F10)
1. In `backend/app/domain/scoring/score_explanations.py:6`:
   ```python
   # Before
   from app.persistence.models import ScoreExplanation, ScoreExplanationDimension

   # After
   from app.db.models.audit import ScoreExplanation, ScoreExplanationDimension
   ```
2. In `backend/app/db/repository.py:22-27`:
   ```python
   # Before
   from app.db.models import (
       EvidenceTraceItem,
       ScoreExplanation,
       ScoreExplanationDimension,
       StageCheckpoint,
   )

   # After
   from app.db.models.audit import (
       EvidenceTraceItem,
       ScoreExplanation,
       ScoreExplanationDimension,
       StageCheckpoint,
   )
   ```
3. In `backend/conftest.py`:
   Ensure `import app.domain` and `import app.connectors` are executed at module load.

### Step 2: Database Configuration & Fail-Fast Connectivity (F07 & F08)
1. In `backend/app/core/config.py`:
   Add `DATABASE_URL: str = Field(default="sqlite:///data/dristik.db")`.
2. In `backend/app/db/session.py`:
   - Delete lines 28-74 (`MockSession` fallback).
   - Implement `verify_database_connection()`.
   - Configure `create_engine` with `pool_pre_ping=True`.

### Step 3: Implement Unified Relational Models (F09)
1. Update `backend/app/db/models/organization.py` with `sso_provider`, `sso_metadata_url`, `updated_at`, and `org_id` synonym.
2. Create `backend/app/db/models/workspace.py` with `Workspace` model.
3. Create `backend/app/db/models/domain.py` with `Domain` model.
4. Update `backend/app/db/models/audit_run.py` to reconcile fields with `enterprise_schema.py`.
5. Create `backend/app/db/models/evidence_node.py` with `EvidenceNode` model.
6. Update `backend/app/db/models/finding.py` with reconciled columns and `audit_id` synonym.
7. Create `backend/app/db/models/ai_citation.py` with `AICitation` model.
8. Create `backend/app/db/models/enterprise_audit_log.py` with `EnterpriseAuditLog` model.
9. Update `backend/app/db/models/__init__.py` to export all models.

### Step 4: Configure Alembic & Create Initial Migration (F09)
1. In `backend/alembic.ini`:
   Add `[loggers]`, `[handlers]`, `[formatters]` standard logging blocks.
2. In `backend/migrations/env.py`:
   - Connect to `settings.DATABASE_URL`.
   - Import `app.db.models`.
   - Enable `render_as_batch=True`.
3. Create `backend/migrations/versions/001_initial_enterprise_schema.py`.

---

## 8. Verification & Test Plan

1. **Test Collection & Execution**:
   - `pytest tests/test_enterprise_schema_and_cas.py` -> All 4 tests must pass without `ModuleNotFoundError`.
   - `pytest tests/test_audit_persistence_and_checkpoints.py` -> All 5 tests must pass.
   - `pytest tests/test_workspace_hierarchy_routes.py` -> All tests pass.
2. **Alembic Migration Verification**:
   - Run `alembic current` -> Successfully reports current revision without `KeyError: 'formatters'`.
   - Run `alembic upgrade head` on a test SQLite DB -> All 8 tables and indexes created successfully.
   - Run `alembic downgrade base` -> Cleanly drops all tables in reverse foreign key order.
3. **Fail-Fast Connectivity Verification**:
   - Provide invalid `DATABASE_URL=postgresql://invalid:invalid@localhost:5432/nonexistent`.
   - Call `verify_database_connection()` -> Must raise `RuntimeError` with connection diagnostic message; must NOT fall back to `MockSession`.

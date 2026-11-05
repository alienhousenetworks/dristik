# Technical Strategy Blueprint: Database Session, Configuration & MockSession Elimination (Milestone M2)

**Author**: `explorer_m2_1` (Teamwork Explorer / Senior Persistence Strategist)  
**Date**: 2026-10-31  
**Project**: Dristik AI  
**Target Milestone**: M2 — Phase 1: Unified Enterprise Persistence & MockSession Elimination  
**Features Covered**: F07 (MockSession Elimination & Fail-Fast Connectivity), F08 (Database Configuration & DATABASE_URL), F10 (Circular Import & Conftest Shims)  
**Reference Files**:
- `ORIGINAL_REQUEST.md` (§R2)
- `PROJECT.md` (Features F07, F08, F10; Milestones M2)
- `.agents/teamwork/explorer_survey_3/survey_phase1_report.md`
- `backend/app/db/session.py`
- `backend/app/core/config.py`
- `backend/app/db/base.py`
- `backend/app/domain/scoring/score_explanations.py`

---

## 1. Executive Summary & Problem Diagnosis

Dristik AI requires a production-grade, enterprise persistence tier that guarantees ACID compliance, strict fail-fast connectivity diagnostics, and cross-engine portability between PostgreSQL (enterprise production) and SQLite (zero-config local development and test harnesses).

Our codebase investigation revealed three critical persistence flaws:

1. **Silent Data Loss via `MockSession` (`backend/app/db/session.py:28-74`)**:
   `session.py` wraps the engine and session initialization in a broad `try... except ImportError` block. When triggered, it creates a `MockSession` class where:
   - `add()` and `refresh()` are no-ops.
   - `first()` returns `None` and `all()` returns `[]`.
   - `commit()` calls `self.conn.commit()`, but no SQL `INSERT` or `UPDATE` is ever executed against the connection.
   If SQLAlchemy imports fail or connection drivers are misconfigured, writes silently disappear while API endpoints return `200 OK` or `201 Created`. This creates phantom successes while dropping user data, audit runs, findings, and credentials.

2. **Absence of Unified `DATABASE_URL` in `Settings` (`backend/app/core/config.py`)**:
   `DATABASE_URL` is completely absent from `Settings`. `session.py` independently falls back to `os.getenv("DATABASE_URL", "sqlite:///dristik.db")`, bypassing Pydantic settings validation, `.env` file priority rules, and configuration auditing. Furthermore, database connection pool tuning (`pool_size`, `max_overflow`, `pool_recycle`, `pool_pre_ping`) is unconfigured.

3. **Absence of Fail-Fast Connectivity Verification & Stale Connection Recovery**:
   `create_engine` lacks `pool_pre_ping=True`. In PostgreSQL production environments, connections dropped by firewalls, proxies, or server restarts result in unhandled `OperationalError` during live user requests. Additionally, application startup does not probe database liveness, allowing a misconfigured server to boot and receive traffic before failing.

This blueprint specifies the exact changes required to eliminate `MockSession`, implement fail-fast connection verification, unify configuration under `DATABASE_URL`, and maintain seamless SQLite and PostgreSQL compatibility.

---

## 2. Technical Strategy: MockSession Elimination & Fail-Fast Diagnostics (F07)

### 2.1 Complete Removal of MockSession
- **Action**: Completely delete lines 28-74 in `backend/app/db/session.py`.
- **Rationale**: Dristik AI is an enterprise platform. SQLAlchemy is a mandatory core dependency specified in `requirements-ci.txt` and `requirements.txt`. There must never be a silent fallback to a non-functional mock in production or local environments.
- **Fail-Fast Invariant**: If SQLAlchemy is missing or cannot initialize, the application must immediately raise a fatal error at startup.

### 2.2 Fail-Fast Exception Architecture
Define a clear, descriptive custom exception in `backend/app/db/session.py`:
```python
class DatabaseConnectionError(RuntimeError):
    """Raised when database connectivity check fails or engine cannot connect."""
    pass
```

### 2.3 Credential-Safe Connection URL Masking
Database error messages and logs must never leak passwords (e.g. `postgresql://user:password@host/db`).
Implement `mask_database_url` using SQLAlchemy's built-in `make_url().render_as_string(hide_password=True)`:
```python
def mask_database_url(url: str) -> str:
    """Mask credentials in database URL for safe logging and error diagnostics."""
    try:
        from sqlalchemy.engine import make_url
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        import re
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", str(url))
```

### 2.4 Active Connection Probe (`verify_database_connection`)
Provide an explicit health check executed during FastAPI startup:
```python
def verify_database_connection(timeout_seconds: float = 5.0) -> None:
    """
    Actively probe database connectivity using a lightweight 'SELECT 1'.
    Raises DatabaseConnectionError with diagnostic details if unreachable.
    """
    masked = mask_database_url(str(engine.url))
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connectivity verified for %s", masked)
    except Exception as exc:
        logger.critical("Database connectivity check failed for %s: %s", masked, exc)
        raise DatabaseConnectionError(
            f"Failed to connect to database at {masked}. Diagnostics: {exc}"
        ) from exc
```

### 2.5 Lifespan Startup Integration (`backend/app/main.py`)
In `backend/app/main.py:lifespan`:
Execute `verify_database_connection()` immediately after `validate_production_configuration(settings)`:
```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_production_configuration(settings)
    verify_database_connection()
    init_db()
    get_store().seed_system()
    ...
```
This guarantees that container orchestrators (Kubernetes / Docker) detect misconfigurations immediately during the startup probe rather than routing traffic to a dead instance.

---

## 3. Database Engine Configuration & Dialect Parity (F08)

### 3.1 Cross-Engine Dialect Support
The database engine must seamlessly support:
1. **PostgreSQL** (`postgresql://`, `postgresql+psycopg2://`, `postgresql+asyncpg://`, `postgresql+pg8000://`):
   - Production relational database.
   - Requires connection pooling with `pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`.
2. **SQLite** (`sqlite://...`):
   - Local development and test environments.
   - Requires `connect_args={"check_same_thread": False}` so multiple threads (e.g., FastAPI route handlers and background tasks) can share connections without SQLite thread affinity errors.
   - Does NOT support `pool_size` or `max_overflow` under its default `SingletonThreadPool` or `NullPool`. Passing these parameters to `create_engine` with SQLite causes a fatal `TypeError`.
   - Requires automatic parent directory creation (e.g. `data/` in `sqlite:///data/dristik.db`).

### 3.2 Dialect Normalization (The Heroku/Cloud `postgres://` Fix)
Cloud providers (AWS RDS, Heroku, Render) frequently emit connection strings beginning with `postgres://`. SQLAlchemy 2.0+ strictly requires `postgresql://` and raises `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgres`.
The configuration validator must automatically normalize `postgres://` to `postgresql://`.

### 3.3 Engine Instantiation Implementation
In `backend/app/db/session.py`:
```python
def create_app_engine(url: Optional[str] = None):
    raw_url = url or settings.DATABASE_URL
    is_sqlite = raw_url.startswith("sqlite")

    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
        "future": True,
    }

    if is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if "///" in raw_url and not raw_url.startswith("sqlite:///:memory:"):
            db_path = raw_url.split("///", 1)[1]
            if db_path and not db_path.startswith(":memory:"):
                try:
                    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                except Exception as exc:
                    logger.warning("Could not auto-create directory for SQLite db %s: %s", db_path, exc)
    else:
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
        engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE

    return create_engine(raw_url, **engine_kwargs)

engine = create_app_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

---

## 4. Session Lifecycle & Clean Resource Reclamation

### 4.1 Dependency Generator (`get_db`)
In `backend/app/db/session.py`:
```python
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a transactional SQLAlchemy Session.
    Ensures rollback on route error and guaranteed closure.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

### 4.2 Lifecycle Invariants
1. **Rollback on Error**: If an unhandled exception occurs in a route or repository method, `db.rollback()` resets transaction state before re-raising. This prevents aborted transactions from lingering or corrupting connection pool state.
2. **Deterministic Close in Finally**: `db.close()` unconditionally returns the connection to the engine pool, preventing connection leaks even during client disconnects.
3. **No Silent Swallowing**: Uncaught exceptions bubble up to FastAPI error handlers.

### 4.3 Database Schema Initialization (`init_db`)
Modernize `init_db` to register declarative models before creating tables:
```python
def init_db() -> None:
    """Create all tables defined on Base.metadata."""
    import app.db.models  # Registers declarative models on Base.metadata
    Base.metadata.create_all(bind=engine)
```

---

## 5. Configuration Settings Specification (`backend/app/core/config.py`) (F08)

### 5.1 Settings Field Additions
Add the following fields to `class Settings(BaseSettings)` in `backend/app/core/config.py`:

```python
    # Database & Persistence Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///data/dristik.db",
        description="Unified PostgreSQL or SQLite connection string"
    )
    DB_POOL_SIZE: int = Field(
        default=10,
        ge=1,
        le=100,
        description="SQLAlchemy connection pool size for PostgreSQL"
    )
    DB_MAX_OVERFLOW: int = Field(
        default=20,
        ge=0,
        le=100,
        description="SQLAlchemy connection max overflow for PostgreSQL"
    )
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        ge=1,
        le=300,
        description="SQLAlchemy connection checkout timeout in seconds"
    )
    DB_POOL_RECYCLE: int = Field(
        default=1800,
        ge=60,
        le=86400,
        description="SQLAlchemy connection recycle time in seconds"
    )
    DB_POOL_PRE_PING: bool = Field(
        default=True,
        description="SQLAlchemy pool pre-ping connection liveness verification"
    )
```

### 5.2 Pydantic Field Validator
Add a `field_validator` in `Settings` for `DATABASE_URL`:
```python
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_and_normalize_database_url(cls, v: Any) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            return "sqlite:///data/dristik.db"
        url_str = v.strip()
        # Normalize legacy postgres:// to postgresql://
        if url_str.startswith("postgres://"):
            url_str = "postgresql://" + url_str[len("postgres://"):]
        
        supported_schemes = (
            "sqlite://",
            "sqlite+pysqlite://",
            "postgresql://",
            "postgresql+psycopg2://",
            "postgresql+asyncpg://",
            "postgresql+pg8000://",
        )
        if not any(url_str.startswith(scheme) for scheme in supported_schemes):
            raise ValueError(
                f"Unsupported database scheme in DATABASE_URL: '{url_str}'. "
                "Must be a valid SQLite or PostgreSQL URL."
            )
        return url_str
```

### 5.3 Helper Properties
Add convenience properties to `Settings`:
```python
    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def sqlite_db_path(self) -> Optional[str]:
        if not self.is_sqlite or self.DATABASE_URL.startswith("sqlite:///:memory:"):
            return None
        return self.DATABASE_URL.split("///", 1)[1] if "///" in self.DATABASE_URL else None
```

### 5.4 Production Safety Check Integration
In `validate_production_configuration(settings_obj: Settings)` in `backend/app/core/config.py`:
Add safety guards that ensure production never uses an in-memory database:
```python
    if is_prod:
        ...
        if not settings_obj.DATABASE_URL or not settings_obj.DATABASE_URL.strip():
            raise RuntimeError("CRITICAL CONFIGURATION ERROR: DATABASE_URL cannot be empty in production.")
        if ":memory:" in settings_obj.DATABASE_URL:
            raise RuntimeError("CRITICAL DATA INTEGRITY ERROR: In-memory database sqlite:///:memory: is forbidden in production.")
```
*Note*: Do NOT reject SQLite outright in `validate_production_configuration`, because existing unit tests in `tests/test_production_settings.py` instantiate `Settings(**SECURE_PRODUCTION)` with default settings. Rejecting all SQLite would break those tests. Forbidding `:memory:` is safe and strictly aligns with production integrity.

---

## 6. Base Declarative Class Cleanup (`backend/app/db/base.py`)

`backend/app/db/base.py` currently contains:
```python
try:
    from sqlalchemy.orm import DeclarativeBase
    from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
    class Base(DeclarativeBase):
        pass
except ImportError:
    class Base:
        metadata = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    def Column(*args, **kwargs):
        return None
    ...
```
- **Action**: Remove the `except ImportError:` block and its dummy stubs (`Column`, `String`, `Integer` returning `None`).
- **Target Implementation**:
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

---

## 7. Circular Import & Pre-requisite Resolutions (F10)

### 7.1 Circular Import in `backend/app/domain/scoring/score_explanations.py`
- **Root Cause**: Line 6 currently reads:
  `from app.persistence.models import ScoreExplanation, ScoreExplanationDimension`
  This triggers `app/persistence.py`, which imports `repository.py`, which imports `score_explanations.py` before `app.persistence.models` is registered in `sys.modules`.
- **Fix**: Update line 6 of `backend/app/domain/scoring/score_explanations.py` to import directly from `app.db.models.audit`:
  ```python
  from app.db.models.audit import ScoreExplanation, ScoreExplanationDimension
  ```

### 7.2 Pre-registering Compatibility Shims in `backend/conftest.py`
In `backend/conftest.py`, ensure `app.connectors` and `app.persistence` are imported early so legacy shims (`app.external_authority` and `app.persistence.models`) are registered prior to test module collection:
```python
import os
import sys

backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Register compatibility module shims before test collection
try:
    import app.connectors  # Registers sys.modules['app.external_authority*']
    import app.persistence # Registers sys.modules['app.persistence.models']
except Exception:
    pass
```

---

## 8. Alembic Migration Alignment

In `backend/alembic.ini`:
- Update line 6:
  `sqlalchemy.url = sqlite:///data/dristik.db`

In `backend/migrations/env.py`:
- Update `run_migrations_offline` and `run_migrations_online` to dynamically use `settings.DATABASE_URL`:
  ```python
  from app.core.config import settings

  def get_url() -> str:
      return getattr(settings, "DATABASE_URL", None) or config.get_main_option("sqlalchemy.url")
  ```

---

## 9. Exact Before-and-After Code Specifications

### 9.1 `backend/app/db/session.py`

#### Before:
```python
import os
import sqlite3
from typing import Generator, Any
from app.db.base import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dristik.db")

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
            
    def init_db():
        Base.metadata.create_all(bind=engine)

except ImportError:
    # Lightweight SQLite fallback
    class MockSession:
        def __init__(self):
            db_path = "dristik.db" if "sqlite:///" not in DATABASE_URL else DATABASE_URL.replace("sqlite:///", "")
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
        def query(self, *args, **kwargs):
            return self
        def filter(self, *args, **kwargs):
            return self
        def first(self):
            return None
        def all(self):
            return []
        def order_by(self, *args, **kwargs):
            return self
        def limit(self, *args, **kwargs):
            return self
        def offset(self, *args, **kwargs):
            return self
        def add(self, obj):
            pass
        def commit(self):
            self.conn.commit()
        def refresh(self, obj):
            pass
        def close(self):
            self.conn.close()

    Session = MockSession
    engine = None
    SessionLocal = MockSession

    def get_db():
        db = MockSession()
        try:
            yield db
        finally:
            db.close()

    def init_db():
        conn = sqlite3.connect("dristik.db")
        conn.execute("CREATE TABLE IF NOT EXISTS system_init (id INTEGER PRIMARY KEY, initialized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.commit()
        conn.close()
```

#### After:
```python
import logging
import os
from pathlib import Path
from typing import Generator, Optional, Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.base import Base

logger = logging.getLogger(__name__)


class DatabaseConnectionError(RuntimeError):
    """Raised when the database engine cannot establish a connection or health check fails."""
    pass


def mask_database_url(url: str) -> str:
    """Mask credentials in database URL for safe logging and error diagnostics."""
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        import re
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", str(url))


def create_app_engine(url: Optional[str] = None):
    """Create and configure a production-grade SQLAlchemy engine."""
    raw_url = url or settings.DATABASE_URL
    is_sqlite = raw_url.startswith("sqlite")

    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
        "future": True,
    }

    if is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if "///" in raw_url and not raw_url.startswith("sqlite:///:memory:"):
            db_file = raw_url.split("///", 1)[1]
            if db_file and not db_file.startswith(":memory:"):
                try:
                    Path(db_file).parent.mkdir(parents=True, exist_ok=True)
                except Exception as exc:
                    logger.warning("Could not auto-create directory for SQLite db %s: %s", db_file, exc)
    else:
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
        engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE

    return create_engine(raw_url, **engine_kwargs)


DATABASE_URL = settings.DATABASE_URL
engine = create_app_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a transactional SQLAlchemy Session.
    Ensures rollback on route error and guaranteed closure.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def verify_database_connection(timeout_seconds: float = 5.0) -> None:
    """
    Actively probe database connectivity using a lightweight query.
    Fails fast by raising DatabaseConnectionError if unreachable.
    """
    masked = mask_database_url(str(engine.url))
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connectivity successfully verified for %s", masked)
    except Exception as exc:
        logger.critical("Database connectivity check failed for %s: %s", masked, exc)
        raise DatabaseConnectionError(
            f"Failed to connect to database at {masked}. Diagnostics: {exc}"
        ) from exc


def init_db() -> None:
    """Create all tables defined on Base.metadata."""
    import app.db.models  # Ensure all declarative models are registered on Base.metadata
    Base.metadata.create_all(bind=engine)
```

---

### 9.2 `backend/app/core/config.py` Additions

```python
    # Database & Persistence Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///data/dristik.db",
        description="Unified PostgreSQL or SQLite connection URL"
    )
    DB_POOL_SIZE: int = Field(
        default=10,
        ge=1,
        le=100,
        description="SQLAlchemy connection pool size for PostgreSQL"
    )
    DB_MAX_OVERFLOW: int = Field(
        default=20,
        ge=0,
        le=100,
        description="SQLAlchemy connection max overflow for PostgreSQL"
    )
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        ge=1,
        le=300,
        description="SQLAlchemy connection checkout timeout in seconds"
    )
    DB_POOL_RECYCLE: int = Field(
        default=1800,
        ge=60,
        le=86400,
        description="SQLAlchemy connection recycle time in seconds"
    )
    DB_POOL_PRE_PING: bool = Field(
        default=True,
        description="SQLAlchemy pool pre-ping connection liveness verification"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_and_normalize_database_url(cls, v: Any) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            return "sqlite:///data/dristik.db"
        url_str = v.strip()
        if url_str.startswith("postgres://"):
            url_str = "postgresql://" + url_str[len("postgres://"):]
        supported_schemes = (
            "sqlite://",
            "sqlite+pysqlite://",
            "postgresql://",
            "postgresql+psycopg2://",
            "postgresql+asyncpg://",
            "postgresql+pg8000://",
        )
        if not any(url_str.startswith(scheme) for scheme in supported_schemes):
            raise ValueError(
                f"Unsupported database scheme in DATABASE_URL: '{url_str}'. "
                "Must be a valid SQLite or PostgreSQL URL."
            )
        return url_str

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")
```

---

## 10. Verification Plan & Test Commands

To independently verify this strategy after implementation:

1. **Verify Unit Tests for Settings & Production Validation**:
   ```bash
   pytest tests/test_production_settings.py
   ```
   *Expected*: All 8 tests pass without regression.

2. **Verify Fail-Fast Connection Behavior**:
   Unit test verifying that an unreachable `DATABASE_URL` (e.g. `postgresql://user:pass@127.0.0.1:59999/nonexistent`) raises `DatabaseConnectionError` when `verify_database_connection()` is called, and that credentials are obfuscated with `***`.

3. **Verify SQLite Multi-Thread Access**:
   Unit test verifying that concurrent threads can obtain sessions via `get_db()` and perform queries without SQLite thread-locking errors.

4. **Verify Session Lifecycle (Rollback on Exception)**:
   Unit test verifying that raising an exception inside a route handler calling `get_db()` triggers `db.rollback()` and closes the session cleanly.

5. **Verify Resolution of Circular Import**:
   ```bash
   pytest tests/test_audit_persistence_and_checkpoints.py
   pytest tests/test_enterprise_schema_and_cas.py
   ```
   *Expected*: Passes without `ModuleNotFoundError: No module named 'app.persistence.models'`.

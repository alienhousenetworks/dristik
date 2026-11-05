# Regression Test Specification Blueprint: Milestone M2-R2

## Executive Summary

This document specifies the regression test suite designed to be appended to `backend/tests/test_db_session_and_fail_fast.py` to prevent regressions for the 5 critical database session, configuration, and connectivity defects discovered during empirical adversarial testing by `challenger_m2_1`.

### Authoritative Specification Sources
- `ORIGINAL_REQUEST.md`: §R2 Unified Enterprise Persistence & Tenant Scoping (fail-fast connectivity, PostgreSQL compatibility, elimination of silent mock sessions).
- `PROJECT.md`: Feature F07 (MockSession Elimination & Fail-Fast Connectivity) and Feature F08 (Database Configuration & `DATABASE_URL`).
- `challenger_m2_1/challenge_report.md`: Empirical findings for ADV-03, ADV-07, ADV-09, ADV-12b, and ADV-13.
- `challenger_m2_1/adversarial_suite.py`: Empirical attack scripts reproducing all 5 failures.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Security / Diagnostics | `mask_database_url` with unencoded `@` in password | Redacts passwords containing `@` symbols without leaking password fragments to logs. | URI strings with `@` in credentials, e.g. `postgresql+psycopg2://user:p@ssword!@localhost:5432/mydb` | Masked URI string with password replaced by `***`, e.g. `postgresql+psycopg2://user:***@localhost:5432/mydb` | Never raises; never emits plaintext password substrings. | `challenger_m2_1/adversarial_suite.py:ADV-03` |
| 2 | Configuration / Driver | `Settings.validate_and_normalize_database_url` Psycopg 3 URI support | Accepts `postgresql+psycopg://` URI scheme standard for SQLAlchemy 2.0+ and Psycopg 3 driver. | `postgresql+psycopg://user:pass@localhost:5432/dristik` | Validated `Settings` instance with normalized `DATABASE_URL`, `is_sqlite=False`, `sqlite_db_path=None` | Invalid schemes raise `ValueError` ("Unsupported database scheme"); Psycopg 3 scheme must NOT raise. | `challenger_m2_1/adversarial_suite.py:ADV-09` |
| 3 | Core Engine Lifecycle | `create_app_engine` URL object support | Accepts `sqlalchemy.engine.URL` instances (from `make_url()`) without type error. | `make_url("sqlite:///data/test.db")` or `make_url("postgresql://...")` | Configured `sqlalchemy.engine.Engine` instance with appropriate pool and dialect options. | Must NOT raise `AttributeError: 'URL' object has no attribute 'startswith'`. | `challenger_m2_1/adversarial_suite.py:ADV-07` |
| 4 | Fail-Fast Diagnostics | `verify_database_connection` physical SQLite header validation | Actively verifies database header on disk rather than relying on in-memory `SELECT 1`. | Engine connected to corrupted SQLite file containing garbage bytes. | `True` for valid databases. | Must raise `DatabaseConnectionError` when SQLite file on disk is corrupted. | `challenger_m2_1/adversarial_suite.py:ADV-13` |
| 5 | Fail-Fast Diagnostics | `create_app_engine` PostgreSQL `connect_timeout` | Configures `connect_timeout` in `connect_args` for PostgreSQL engines to prevent TCP SYN hangs on unroutable hosts. | PostgreSQL connection string or URL object. | SQLAlchemy `Engine` configured with `connect_args={"connect_timeout": 5}`. | Without `connect_timeout`, unroutable hosts block for 75-120s; with `connect_timeout`, connection establishment fails within configured seconds. | `challenger_m2_1/adversarial_suite.py:ADV-12b` |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| E1 | `mask_database_url` | `postgresql+psycopg2://user:p@ssword!@localhost:5432/mydb` | Leaks secret suffix `'ssword!'` because non-greedy fallback regex `([^@]+)@` stopped at first `@`. Fixed via greedy authority match. |
| E2 | `mask_database_url` | `postgresql://admin:p@ss@w0rd@db.example.com:5432/prod` (multiple `@`) | `make_url` misparses password as `p` and host as `ss@w0rd@db.example.com`, leaking password in host field. Fixed by checking `parsed.host` for `@` or applying authority regex. |
| E3 | `mask_database_url` | `postgresql://user:p@ss!@localhost:5432/mydb?key=val@ue` (query param with `@`) | Authority-scoped regex `://([^:]+):([^/?#]+)@` prevents greedy match from consuming query parameters. |
| E4 | `Settings` database URL | `postgresql+psycopg://user:pass@localhost:5432/dristik?sslmode=require` | Correctly preserves driver prefix and query parameters while validating scheme. |
| E5 | `create_app_engine` | `make_url("sqlite:///:memory:")` | Correctly detects SQLite dialect and applies `check_same_thread=False` and `pool_pre_ping=True`. |
| E6 | `create_app_engine` | `make_url("postgresql://u:p@localhost:5432/db")` | Correctly detects PostgreSQL dialect and applies `connect_timeout` and connection pool settings. |
| E7 | `verify_database_connection` | Corrupted SQLite file with valid extension (`corrupt.db`) | `SELECT 1` in SQLite executes in-memory without reading file header; `PRAGMA schema_version;` forces disk page read and raises `sqlite3.DatabaseError: file is not a database`, caught and raised as `DatabaseConnectionError`. |
| E8 | `create_app_engine` | PostgreSQL engine under custom `DB_CONNECT_TIMEOUT` setting | Passes configured integer value into `connect_args={"connect_timeout": N}`. |

---

## Pytest Test Blueprint for `backend/tests/test_db_session_and_fail_fast.py`

Below is the complete, self-contained Python code designed to be appended to `backend/tests/test_db_session_and_fail_fast.py`.

### Required Imports Update
Ensure the following imports are present at the top of `backend/tests/test_db_session_and_fail_fast.py`:

```python
from sqlalchemy.engine import make_url
from app.db.session import (
    create_app_engine,
    create_db_engine,
    get_db,
    mask_database_url,
    verify_database_connection,
)
```

### Test Functions Code

```python
def test_mask_database_url_with_unencoded_at_in_password():
    """Verify passwords containing unencoded '@' do not leak secrets in fallback regex."""
    # Single unencoded @ in password
    url = "postgresql+psycopg2://user:p@ssword!@localhost:5432/mydb"
    masked = mask_database_url(url)
    assert "p@ssword!" not in masked, "Plaintext password must not appear in masked URL"
    assert "ssword!" not in masked, "Password fragment must not be leaked after @"
    assert "p@" not in masked or "user:***@" in masked
    assert "user:***@localhost:5432/mydb" in masked
    assert "mydb" in masked

    # Multiple unencoded @ in password
    multi_at_url = "postgresql://admin:p@ss@w0rd@db.example.com:5432/prod"
    masked_multi = mask_database_url(multi_at_url)
    assert "p@ss@w0rd" not in masked_multi, "Multi-@ password must not leak"
    assert "admin:***@db.example.com:5432/prod" in masked_multi

    # Password with @ and query parameters containing @
    query_at_url = "postgresql://user:sec@ret@localhost:5432/db?token=tok@123"
    masked_query = mask_database_url(query_at_url)
    assert "sec@ret" not in masked_query
    assert "user:***@localhost:5432/db" in masked_query


def test_database_url_settings_supports_psycopg3_scheme():
    """Verify Settings accepts standard SQLAlchemy 2.0+ Psycopg 3 dialect URI."""
    url = "postgresql+psycopg://user:pass@localhost:5432/dristik"
    settings = Settings(DATABASE_URL=url)
    assert settings.DATABASE_URL == url
    assert settings.is_sqlite is False
    assert settings.sqlite_db_path is None

    # Verify query parameters support with psycopg 3
    url_with_params = "postgresql+psycopg://user:pass@localhost:5432/dristik?sslmode=require"
    settings_params = Settings(DATABASE_URL=url_with_params)
    assert settings_params.DATABASE_URL == url_with_params
    assert settings_params.is_sqlite is False


def test_create_app_engine_accepts_url_object():
    """Verify create_app_engine accepts a structured sqlalchemy.engine.URL instance."""
    # Test SQLite URL object
    sqlite_url_obj = make_url("sqlite:///:memory:")
    eng_sqlite = create_app_engine(sqlite_url_obj)
    assert eng_sqlite.dialect.name == "sqlite"
    assert getattr(eng_sqlite.pool, "_pre_ping", False) is True

    # Test SQLite file URL object
    sqlite_file_obj = make_url("sqlite:///data/test_url_obj.db")
    eng_file = create_app_engine(sqlite_file_obj)
    assert eng_file.dialect.name == "sqlite"

    # Test PostgreSQL URL object
    pg_url_obj = make_url("postgresql://user:pass@localhost:5432/dristik")
    eng_pg = create_app_engine(pg_url_obj)
    assert eng_pg.dialect.name == "postgresql"
    assert getattr(eng_pg.pool, "_pre_ping", False) is True


def test_verify_database_connection_detects_corrupt_sqlite_file(tmp_path):
    """Verify connection health check fails fast on corrupted SQLite database file."""
    corrupt_db = tmp_path / "corrupted_test.db"
    corrupt_db.write_bytes(b"CORRUPT_HEADER_GARBAGE_DATA_1234567890" * 40)

    corrupt_engine = create_app_engine(f"sqlite:///{corrupt_db}")
    with pytest.raises(DatabaseConnectionError) as exc_info:
        verify_database_connection(corrupt_engine)

    assert "Database connection failed" in str(exc_info.value)


def test_create_app_engine_postgres_includes_connect_timeout(monkeypatch):
    """Verify PostgreSQL engine creation configures connect_timeout in connect_args."""
    pg_url = "postgresql://user:pass@localhost:5432/dristik"

    # Test default connect_timeout is configured
    with patch("app.db.session.create_engine") as mock_create_engine:
        create_app_engine(pg_url)
        mock_create_engine.assert_called_once()
        _, kwargs = mock_create_engine.call_args
        assert "connect_args" in kwargs, "PostgreSQL engine must pass connect_args"
        connect_args = kwargs["connect_args"]
        assert "connect_timeout" in connect_args, (
            "connect_args must specify connect_timeout to prevent infinite hangs"
        )
        assert isinstance(connect_args["connect_timeout"], (int, float))
        assert connect_args["connect_timeout"] > 0

    # Test custom DB_CONNECT_TIMEOUT setting override
    monkeypatch.setattr(session_module.settings, "DB_CONNECT_TIMEOUT", 12, raising=False)
    with patch("app.db.session.create_engine") as mock_create_engine:
        create_app_engine(pg_url)
        mock_create_engine.assert_called_once()
        _, kwargs = mock_create_engine.call_args
        assert kwargs["connect_args"]["connect_timeout"] == 12
```

---

## Implementation Guidance for Remediation

To assist the engineer implementing the fixes, the required codebase adjustments are:

### 1. `backend/app/db/session.py`
- In `mask_database_url(url: str | Any) -> str`:
  ```python
  def mask_database_url(url: str | Any) -> str:
      """Mask credentials in database URL for safe logging/diagnostics."""
      url_str = str(url)
      try:
          parsed = make_url(url_str)
          # If host contains '@', make_url misparsed an unencoded '@' in password
          if parsed.host and "@" in parsed.host:
              return re.sub(r"://([^:]+):([^/?#]+)@", r"://\1:***@", url_str)
          return parsed.render_as_string(hide_password=True)
      except Exception:
          return re.sub(r"://([^:]+):([^/?#]+)@", r"://\1:***@", url_str)
  ```

- In `create_app_engine(url: Optional[str | Any] = None)`:
  ```python
  def create_app_engine(url: Optional[str | Any] = None):
      """Create and configure a production-grade SQLAlchemy engine."""
      default_url = "sqlite:///data/dristik.db"
      raw_url = url or getattr(settings, "DATABASE_URL", default_url)
      url_str = str(raw_url)
      is_sqlite = url_str.startswith("sqlite")

      pool_pre_ping = getattr(settings, "DB_POOL_PRE_PING", True)

      engine_kwargs: dict[str, Any] = {
          "pool_pre_ping": pool_pre_ping,
          "future": True,
      }

      if is_sqlite:
          engine_kwargs["connect_args"] = {"check_same_thread": False}
          if "///" in url_str and not url_str.startswith("sqlite:///:memory:"):
              db_file = url_str.split("///", 1)[1]
              if db_file and not db_file.startswith(":memory:"):
                  try:
                      Path(db_file).parent.mkdir(parents=True, exist_ok=True)
                  except Exception as exc:
                      logger.warning(
                          "Could not auto-create directory for SQLite db %s: %s",
                          db_file,
                          exc,
                      )
      else:
          connect_timeout = getattr(settings, "DB_CONNECT_TIMEOUT", 5)
          engine_kwargs["connect_args"] = {"connect_timeout": connect_timeout}
          engine_kwargs["pool_size"] = getattr(settings, "DB_POOL_SIZE", 10)
          engine_kwargs["max_overflow"] = getattr(
              settings, "DB_MAX_OVERFLOW", 20
          )
          engine_kwargs["pool_timeout"] = getattr(
              settings, "DB_POOL_TIMEOUT", 30
          )
          engine_kwargs["pool_recycle"] = getattr(
              settings, "DB_POOL_RECYCLE", 1800
          )

      return create_engine(raw_url, **engine_kwargs)
  ```

- In `verify_database_connection(target_engine=None, timeout_seconds: float = 5.0)`:
  ```python
      is_sqlite = eng.dialect.name == "sqlite"
      probe_sql = "PRAGMA schema_version" if is_sqlite else "SELECT 1"
      try:
          with eng.connect() as conn:
              conn.execute(
                  text(probe_sql).execution_options(timeout=timeout_seconds)
              )
  ```

### 2. `backend/app/core/config.py`
- In `supported_schemes` tuple within `validate_and_normalize_database_url`:
  ```python
      supported_schemes = (
          "sqlite://",
          "sqlite+pysqlite://",
          "postgresql://",
          "postgresql+psycopg://",
          "postgresql+psycopg2://",
          "postgresql+asyncpg://",
          "postgresql+pg8000://",
      )
  ```

- In `Settings` class:
  ```python
      DB_CONNECT_TIMEOUT: int = Field(
          default=5,
          ge=1,
          le=60,
          description="Database socket connect timeout in seconds for PostgreSQL",
      )
  ```

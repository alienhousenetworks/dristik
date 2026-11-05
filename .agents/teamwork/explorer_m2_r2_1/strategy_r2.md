# Remediation Blueprint: Milestone M2 Iteration 2

**Author**: explorer_m2_r2_1 (Teamwork Explorer)  
**Date**: 2026-10-31  
**Scope**: `backend/app/db/session.py`, `backend/app/core/config.py`  
**Input Findings**: Challenger Report (`challenger_m2_1/challenge_report.md`), Adversarial Suite (`adversarial_suite.py`)

---

## 1. Executive Summary

Milestone M2 eliminates the legacy silent `MockSession` fallback and unifies enterprise persistence across PostgreSQL and SQLite. In Iteration 1, adversarial challenge suite testing (`adversarial_suite.py`) revealed 5 empirical defects:
1. **Critical Security (ADV-03)**: `mask_database_url` leaks plaintext password suffixes into logs when passwords contain unencoded `@` characters.
2. **High Availability (ADV-12b)**: `verify_database_connection` hangs for 75–120s on unroutable hosts or packet-dropping firewalls because query execution timeout does not govern the TCP handshake.
3. **Medium Compatibility (ADV-09)**: `Settings` rejects standard SQLAlchemy 2.0+ Psycopg 3 URIs (`postgresql+psycopg://`), despite `psycopg` (v3.2.1) being installed in the environment.
4. **Low/Medium Correctness (ADV-07)**: `create_app_engine` raises `AttributeError: 'URL' object has no attribute 'startswith'` when passed an `sqlalchemy.engine.URL` instance.
5. **Low Resilience (ADV-13)**: `verify_database_connection` performs `SELECT 1` on SQLite, which evaluates purely in-memory and fails to detect physically corrupt database file headers on disk.

This document details the exact, minimal, non-regressive remediation blueprint to resolve all 5 findings and transition all 17 adversarial checks from 12 PASS / 5 FAIL to **17 PASS / 0 FAIL**.

---

## 2. In-Depth Root Cause & Failure Analysis

### Finding 1: Credential Leakage in `mask_database_url` (ADV-03)
- **Target File & Lines**: `backend/app/db/session.py:38-44`
- **Observed Behavior**:
  ```python
  mask_database_url("postgresql+psycopg2://user:p@ssword!@localhost:5432/mydb")
  # Returns: 'postgresql+psycopg2://user:***@ssword!@localhost:5432/mydb'
  ```
- **Root Cause**:
  In SQLAlchemy 2.x, `make_url` does not raise an exception on passwords containing unencoded `@`; instead, it splits on the first `@`, assigns `p` as the password, and treats `ssword!@localhost` as the `host`. When `render_as_string(hide_password=True)` is called, the password `p` is masked as `***`, but the remainder of the secret `ssword!` is rendered as part of the host!
  Furthermore, the fallback regex `r"://([^:]+):([^@]+)@"` matched only up to the first `@`, failing to capture the full password.
- **Remediation**:
  1. Inspect `parsed = make_url(url_str)`. If `parsed.host and "@" in parsed.host`, detect the unencoded credential partition and trigger the regex path.
  2. In the regex fallback, match greedily up to the last `@` before host/port/database by bounding the match to non-delimiter characters: `r"://([^:]+):([^/?#]*)@"`. This matches through any embedded `@` symbols in the authority segment without bleeding into path, query parameters, or fragments.

### Finding 2: Connection Timeout Bypass on Unroutable Hosts / Firewalls (ADV-12b)
- **Target File & Lines**: `backend/app/db/session.py:59-84`, `backend/app/db/session.py:109-141`
- **Observed Behavior**:
  Calling `verify_database_connection(unroutable_eng, timeout_seconds=1.0)` blocks for 75+ seconds (the OS TCP SYN retransmission timeout) before failing.
- **Root Cause**:
  `timeout_seconds` was only applied as an execution option on the SQL statement (`text("SELECT 1").execution_options(timeout=timeout_seconds)`). It was never applied to `eng.connect()`.
  Additionally, `create_app_engine` did not configure `connect_args={"connect_timeout": ...}` on PostgreSQL engines.
- **Remediation**:
  1. In `create_app_engine`, inject `connect_args={"connect_timeout": int(getattr(settings, "DB_CONNECT_TIMEOUT", 5))}` for non-SQLite engines.
  2. In `verify_database_connection`, execute the socket connection and probe inside a daemon thread (`threading.Thread(target=_probe_worker, daemon=True)`), joining with `timeout=timeout_seconds`. If the thread does not terminate within `timeout_seconds`, immediately raise `DatabaseConnectionError(f"Database connection timed out after {timeout_seconds}s for {masked}")`.

### Finding 3: Psycopg 3 Scheme Rejection (`postgresql+psycopg://`) (ADV-09)
- **Target File & Lines**: `backend/app/core/config.py:542-550`
- **Observed Behavior**:
  ```python
  Settings(DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/dristik")
  # Raises ValueError: Unsupported database scheme in DATABASE_URL: 'postgresql+psycopg://...'
  ```
- **Root Cause**:
  The tuple `supported_schemes` in `Settings.validate_and_normalize_database_url` included `postgresql+psycopg2://` but omitted `postgresql+psycopg://`, which is the canonical SQLAlchemy 2.0+ scheme for Psycopg 3.
- **Remediation**:
  Add `"postgresql+psycopg://"` to `supported_schemes` in `config.py:542`. Also declare `DB_CONNECT_TIMEOUT: int = Field(default=5, ge=1, le=300)` on `Settings` for explicit persistence configuration.

### Finding 4: Type Crash When Passing `sqlalchemy.engine.URL` (ADV-07)
- **Target File & Lines**: `backend/app/db/session.py:49-50`
- **Observed Behavior**:
  `create_app_engine(make_url("sqlite:///data/test.db"))` raises `AttributeError: 'URL' object has no attribute 'startswith'`.
- **Root Cause**:
  `create_app_engine` directly called `.startswith()` and string slicing operations on `raw_url`, assuming it was always a `str`.
- **Remediation**:
  Coerce `url_str = str(raw_url)` before inspecting scheme prefixes or database file paths, while still passing `raw_url` to `create_engine` (which natively supports `URL` instances).

### Finding 5: In-Memory `SELECT 1` Bypass on Corrupt SQLite Files (ADV-13)
- **Target File & Lines**: `backend/app/db/session.py:126-129`
- **Observed Behavior**:
  `verify_database_connection` against an SQLite engine pointing to a file filled with garbage bytes returned `True`.
- **Root Cause**:
  In SQLite, `SELECT 1` is evaluated purely in-memory by the query planner without reading the database file header or pages from disk.
- **Remediation**:
  When `eng.name == "sqlite"`, execute `PRAGMA schema_version;` instead of `SELECT 1`. This forces SQLite to parse the database file header on disk, immediately catching file corruption (`sqlite3.DatabaseError: file is not a database`) while taking less than 1ms.

---

## 3. Exact Code Proposals & Diff Patches

### File 1: `backend/app/core/config.py`

#### Changes:
1. Add `DB_CONNECT_TIMEOUT` setting field (under Database & Persistence Configuration).
2. Add `"postgresql+psycopg://"` to `supported_schemes` in `validate_and_normalize_database_url`.

#### Unified Diff:
```diff
--- a/backend/app/core/config.py
+++ b/backend/app/core/config.py
@@ -318,6 +318,12 @@ class Settings(BaseSettings):
         default=True,
         description="SQLAlchemy pool pre-ping connection liveness verification"
     )
+    DB_CONNECT_TIMEOUT: int = Field(
+        default=5,
+        ge=1,
+        le=300,
+        description="Database connection handshake timeout in seconds for PostgreSQL"
+    )
     SESSION_DAYS: int = 14
     FRONTEND_URL: str = "http://localhost:5173"
     SYSTEM_ADMIN_EMAIL: str = "admin@dristik.ai"
@@ -543,6 +549,7 @@ class Settings(BaseSettings):
             "sqlite://",
             "sqlite+pysqlite://",
             "postgresql://",
+            "postgresql+psycopg://",
             "postgresql+psycopg2://",
             "postgresql+asyncpg://",
             "postgresql+pg8000://",
```

---

### File 2: `backend/app/db/session.py`

#### Changes:
1. Import `threading` at top.
2. In `mask_database_url`, detect unencoded `@` where `parsed.host and "@" in parsed.host`, and update fallback regex to `r"://([^:]+):([^/?#]*)@"`.
3. In `create_app_engine`, support `URL` objects via `url_str = str(raw_url)`, support `**kwargs`, and set `connect_args={"connect_timeout": int(getattr(settings, "DB_CONNECT_TIMEOUT", 5))}` for non-SQLite engines.
4. In `verify_database_connection`, execute the connection probe inside a daemon thread bounded by `timeout_seconds`, and execute `PRAGMA schema_version;` for SQLite engines.

#### Unified Diff:
```diff
--- a/backend/app/db/session.py
+++ b/backend/app/db/session.py
@@ -8,6 +8,7 @@ from __future__ import annotations
 import logging
 import re
+import threading
 from pathlib import Path
 from typing import Any, Generator, Optional
 
@@ -38,16 +39,23 @@ _core_exceptions.DatabaseConnectionError = DatabaseConnectionError
-def mask_database_url(url: str) -> str:
+def mask_database_url(url: Any) -> str:
     """Mask credentials in database URL for safe logging/diagnostics."""
+    url_str = str(url)
     try:
-        return make_url(url).render_as_string(hide_password=True)
+        parsed = make_url(url_str)
+        # If password contains unencoded '@', make_url misparses the suffix into parsed.host
+        if parsed.host and "@" in parsed.host:
+            raise ValueError("Host contains '@'; unencoded credential detected in authority")
+        return parsed.render_as_string(hide_password=True)
     except Exception:
-        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", str(url))
+        return re.sub(r"://([^:]+):([^/?#]*)@", r"://\1:***@", url_str)
 
 
-def create_app_engine(url: Optional[str] = None):
+def create_app_engine(url: Optional[Any] = None, **kwargs: Any):
     """Create and configure a production-grade SQLAlchemy engine."""
     default_url = "sqlite:///data/dristik.db"
     raw_url = url or getattr(settings, "DATABASE_URL", default_url)
-    is_sqlite = raw_url.startswith("sqlite")
+    url_str = str(raw_url)
+    is_sqlite = url_str.startswith("sqlite")
 
     pool_pre_ping = getattr(settings, "DB_POOL_PRE_PING", True)
 
@@ -60,8 +68,8 @@ def create_app_engine(url: Optional[str] = None):
     if is_sqlite:
         engine_kwargs["connect_args"] = {"check_same_thread": False}
-        if "///" in raw_url and not raw_url.startswith("sqlite:///:memory:"):
-            db_file = raw_url.split("///", 1)[1]
+        if "///" in url_str and not url_str.startswith("sqlite:///:memory:"):
+            db_file = url_str.split("///", 1)[1]
             if db_file and not db_file.startswith(":memory:"):
                 try:
                     Path(db_file).parent.mkdir(parents=True, exist_ok=True)
@@ -72,6 +80,8 @@ def create_app_engine(url: Optional[str] = None):
                         exc,
                     )
     else:
+        connect_timeout = int(getattr(settings, "DB_CONNECT_TIMEOUT", 5))
+        engine_kwargs["connect_args"] = {"connect_timeout": connect_timeout}
         engine_kwargs["pool_size"] = getattr(settings, "DB_POOL_SIZE", 10)
         engine_kwargs["max_overflow"] = getattr(
             settings, "DB_MAX_OVERFLOW", 20
@@ -83,6 +93,7 @@ def create_app_engine(url: Optional[str] = None):
             settings, "DB_POOL_RECYCLE", 1800
         )
 
+    engine_kwargs.update(kwargs)
     return create_engine(raw_url, **engine_kwargs)
 
 
@@ -113,6 +124,8 @@ def verify_database_connection(
     """
     Actively probe database connectivity using a lightweight query.
     Fails fast by raising DatabaseConnectionError if unreachable.
+    Guarantees probe terminates within timeout_seconds even during TCP handshake.
+    For SQLite engines, executes PRAGMA schema_version to validate physical disk header.
     """
     if isinstance(target_engine, (int, float)):
         timeout_seconds = float(target_engine)
@@ -124,11 +137,36 @@ def verify_database_connection(
     masked = mask_database_url(str(eng.url))
+    is_sqlite = eng.name == "sqlite"
+    probe_query = text("PRAGMA schema_version;") if is_sqlite else text("SELECT 1")
+
+    probe_result: dict[str, Any] = {"success": False, "error": None}
+
+    def _probe_worker():
+        try:
+            with eng.connect() as conn:
+                conn.execute(
+                    probe_query.execution_options(timeout=timeout_seconds)
+                )
+            probe_result["success"] = True
+        except Exception as exc:
+            probe_result["error"] = exc
+
+    probe_thread = threading.Thread(target=_probe_worker, daemon=True)
+    probe_thread.start()
+    probe_thread.join(timeout=timeout_seconds)
+
+    if probe_thread.is_alive():
+        logger.critical(
+            "Database connectivity check timed out after %.1fs for %s",
+            timeout_seconds,
+            masked,
+        )
+        raise DatabaseConnectionError(
+            f"Database connection timed out after {timeout_seconds}s for {masked}"
+        )
+
+    if not probe_result["success"]:
+        exc = probe_result["error"]
+        logger.critical(
+            "Database connectivity check failed for %s: %s", masked, exc
+        )
+        raise DatabaseConnectionError(
+            f"Database connection failed for {masked}: {exc}"
+        ) from exc
+
     logger.info(
         "Database connectivity successfully verified for %s", masked
     )
     return True
-    except Exception as exc:
-        logger.critical(
-            "Database connectivity check failed for %s: %s", masked, exc
-        )
-        raise DatabaseConnectionError(
-            f"Database connection failed for {masked}: {exc}"
-        ) from exc
```

---

## 4. Verification Protocol

The implementer should execute the following steps after applying the patch:

### Step 1: Run Adversarial Challenge Suite
```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 \
    /Users/sayantande/Downloads/dristik-main/.agents/teamwork/challenger_m2_1/adversarial_suite.py
```
**Expected Outcome**:
```text
==================================================================
SUMMARY: 17 PASSED, 0 FAILED
==================================================================
```
All previously failing tests (`ADV-03`, `ADV-07`, `ADV-09`, `ADV-12b`, `ADV-13`) must report `[PASS]`.

### Step 2: Run Existing Database Session Test Suite
```bash
pytest backend/tests/test_db_session_and_fail_fast.py -v
```
**Expected Outcome**:
`11 passed in < 1.0s` with zero errors or warnings.

### Step 3: Run Full Backend Test Suite
```bash
pytest backend/ -q --ignore=backend/tests/manual
```
**Expected Outcome**:
All 2,248 existing backend tests pass.

---

## 5. Risk, Compatibility, and Scope Review

- **Security**: Completely prevents credential leakage in error messages and logs when unencoded special characters are present in connection URIs.
- **Availability**: Protects containers and worker nodes from thread exhaustion and liveness probe timeouts during network blackholes or cloud failovers by enforcing bounded connection handshakes.
- **Maintainability & Minimal Diff**: Follows Ponytail / Senior Engineer discipline. Modifies only the 2 target files (`session.py` and `config.py`), introduces zero new dependencies, and uses standard Python `threading` and SQLAlchemy primitives already present in the runtime.

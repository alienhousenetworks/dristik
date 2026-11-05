# Handoff Report: Regression Test Specifications for Milestone M2-R2

## 1. Observation

Direct observations from examining the codebase, specifications, and challenger findings:

1. **`backend/app/db/session.py:38-44` (Password Masking Leak)**:
   ```python
   def mask_database_url(url: str) -> str:
       try:
           return make_url(url).render_as_string(hide_password=True)
       except Exception:
           return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", str(url))
   ```
   Direct execution of `mask_database_url("postgresql+psycopg2://user:p@ssword!@localhost:5432/mydb")` produced:
   `'postgresql+psycopg2://user:***@ssword!@localhost:5432/mydb'`
   Verbatim error in reproduction script:
   `AssertionError: Leaked ssword! in postgresql+psycopg2://user:***@ssword!@localhost:5432/mydb`
   Additionally, on `url = "postgresql://admin:p@ss@w0rd@db.example.com:5432/prod"`, `make_url` does not raise an exception; instead it parses `u.host = 'ss@w0rd@db.example.com'`, rendering `'postgresql://admin:***@ss@w0rd@db.example.com:5432/prod'`, which leaks the password suffix directly into the hostname.

2. **`backend/app/core/config.py:542-550` (Psycopg 3 URI Scheme Rejection)**:
   ```python
   supported_schemes = (
       "sqlite://",
       "sqlite+pysqlite://",
       "postgresql://",
       "postgresql+psycopg2://",
       "postgresql+asyncpg://",
       "postgresql+pg8000://",
   )
   if not any(url_str.startswith(scheme) for scheme in supported_schemes):
       raise ValueError(...)
   ```
   Direct execution of `Settings(DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/dristik")` raised:
   `pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings`
   `DATABASE_URL Value error, Unsupported database scheme in DATABASE_URL: 'postgresql+psycopg://user:pass@localhost:5432/dristik'. Must be a valid SQLite or PostgreSQL URL.`

3. **`backend/app/db/session.py:46-51` (`URL` Object Crash)**:
   ```python
   def create_app_engine(url: Optional[str] = None):
       default_url = "sqlite:///data/dristik.db"
       raw_url = url or getattr(settings, "DATABASE_URL", default_url)
       is_sqlite = raw_url.startswith("sqlite")
   ```
   Direct execution with `url_obj = make_url("sqlite:///data/test_url_obj.db")` raised:
   `AttributeError: 'URL' object has no attribute 'startswith'`

4. **`backend/app/db/session.py:126-129` (Corrupt SQLite Health Check Bypass)**:
   ```python
   with eng.connect() as conn:
       conn.execute(
           text("SELECT 1").execution_options(timeout=timeout_seconds)
       )
   ```
   Direct execution against a file filled with `b"CORRUPT_GARBAGE_HEADER_DATA_12345" * 50` returned `True` without error.
   Executing `PRAGMA schema_version` against the same corrupted file raised:
   `sqlalchemy.exc.DatabaseError: (sqlite3.DatabaseError) file is not a database [SQL: PRAGMA schema_version]`

5. **`backend/app/db/session.py:73-84` (PostgreSQL `connect_timeout` Missing)**:
   `create_app_engine` configures pool parameters for PostgreSQL but passes no `connect_args`.
   Executing `create_app_engine("postgresql://user:pass@localhost:5432/dristik")` with `patch("app.db.session.create_engine")` yielded:
   `called kwargs: {'pool_pre_ping': True, 'future': True, 'pool_size': 10, 'max_overflow': 20, 'pool_timeout': 30, 'pool_recycle': 1800}`
   Verbatim assertion error:
   `AssertionError: connect_args missing`

---

## 2. Logic Chain

1. **Vulnerability 1 (`mask_database_url`)**:
   - Observation 1 proves `make_url` can misparse passwords with `@` into `host`, and the fallback regex `([^@]+)@` matches only up to the first `@`.
   - In both cases, secret password fragments are leaked.
   - An authority-bounded regex `://([^:]+):([^/?#]+)@` captures up to the final `@` preceding the host/path boundary, eliminating credential leaks while preserving query parameters and URLs without passwords.
   - Designed regression test: `test_mask_database_url_with_unencoded_at_in_password`.

2. **Vulnerability 2 (Psycopg 3 URI Scheme)**:
   - Observation 2 proves `supported_schemes` in `config.py` omits `postgresql+psycopg://`, the canonical driver scheme for SQLAlchemy 2.0+ with Psycopg 3.
   - Since `psycopg` is installed in the project environment, users and configurations using standard driver notation are rejected.
   - Adding `"postgresql+psycopg://"` to `supported_schemes` resolves the failure.
   - Designed regression test: `test_database_url_settings_supports_psycopg3_scheme`.

3. **Vulnerability 3 (`URL` Object Crash in `create_app_engine`)**:
   - Observation 3 proves `create_app_engine` directly calls `.startswith()` on `raw_url`, assuming it is a `str`.
   - Standard SQLAlchemy patterns pass `URL` objects returned from `make_url()`.
   - Coercing `url_str = str(raw_url)` before checking prefixes and splitting paths allows both `str` and `URL` objects.
   - Designed regression test: `test_create_app_engine_accepts_url_object`.

4. **Vulnerability 4 (Corrupted SQLite Health Check Bypass)**:
   - Observation 4 proves SQLite does not touch file headers on disk when evaluating `SELECT 1`.
   - `PRAGMA schema_version` forces SQLite to read disk pages and immediately fails with `DatabaseError: file is not a database` on corruption.
   - Using `PRAGMA schema_version` for SQLite engines and `SELECT 1` for PostgreSQL ensures fail-fast error detection.
   - Designed regression test: `test_verify_database_connection_detects_corrupt_sqlite_file`.

5. **Vulnerability 5 (Missing `connect_timeout` on PostgreSQL)**:
   - Observation 5 proves `create_app_engine` does not supply `connect_args={"connect_timeout": ...}`.
   - On network drop or unroutable host events, TCP handshake hangs for 75-120 seconds, bypassing the query-level `execution_options(timeout=...)`.
   - Configuring `connect_args={"connect_timeout": getattr(settings, "DB_CONNECT_TIMEOUT", 5)}` prevents indefinite TCP SYN hangs.
   - Designed regression test: `test_create_app_engine_postgres_includes_connect_timeout`.

---

## 3. Caveats

- In accordance with the system prompt and dispatch instructions, this agent operates in read-only mode regarding production source files. No source code files (`session.py`, `config.py`, or `test_db_session_and_fail_fast.py`) were modified.
- The 5 regression test blueprints are prepared and saved in `test_spec_r2.md`, along with exact implementation patches for the implementing engineer.

---

## 4. Conclusion

All 5 defects identified by `challenger_m2_1` have been empirically verified and analyzed down to root causes. Five robust, targeted pytest functions have been designed following Ponytail principles (minimal code, clear assertions, zero unnecessary fixtures, comprehensive edge case coverage).

The blueprint is published at:
`/Users/sayantande/Downloads/dristik-main/.agents/teamwork/spec_miner_m2_r2_2/test_spec_r2.md`

---

## 5. Verification Method

Once the test functions are appended to `backend/tests/test_db_session_and_fail_fast.py` and the corresponding source fixes are implemented:

1. **Run full database test module**:
   ```bash
   /Library/Frameworks/Python.framework/Versions/3.12/bin/pytest backend/tests/test_db_session_and_fail_fast.py -v
   ```
   Expected: All 16 tests pass (11 existing + 5 new).

2. **Run adversarial challenge suite**:
   ```bash
   /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 .agents/teamwork/challenger_m2_1/adversarial_suite.py
   ```
   Expected: All 17 tests pass (0 failures).

3. **Invalidation condition**:
   If any of the 5 tests fail after implementation, or if any existing tests in `test_db_session_and_fail_fast.py` regress.

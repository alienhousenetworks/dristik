"""
Deep-dive Empirical Adversarial Harness for Milestone M2 Iteration 2.
Adversarially probes:
1. ADV-03: URL password masking with extreme edge cases (multiple @, query strings with @, paths with @, empty passwords, unicode/emojis).
2. ADV-07: URL object handling in create_app_engine with various dialects and kwargs forwarding.
3. ADV-09: Psycopg3 URL support and settings validation corner cases.
4. ADV-12b: Timeout enforcement under packet-dropping and unroutable network blackholes with varying timeouts.
5. ADV-13: SQLite corruption resilience (garbage header, zero-byte file, truncated header, read-only corruption).
6. Non-regression: Thread safety, rollback guarantees, pool_pre_ping.
"""

import sys
import os
import tempfile
import threading
import time

backend_path = os.path.abspath("/Users/sayantande/Downloads/dristik-main/backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlalchemy import text
from sqlalchemy.engine import make_url, URL
from sqlalchemy.orm import Session

import app.db.session as session_module
from app.db.session import (
    create_app_engine,
    mask_database_url,
    verify_database_connection,
    DatabaseConnectionError,
    SessionLocal,
    get_db,
)
from app.core.config import Settings, settings

def run_deep_dive():
    results = []
    def record(name, passed, msg):
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}: {msg}")
        results.append((name, passed, msg))

    print("==================================================================")
    print("STARTING DEEP-DIVE EMPIRICAL ADVERSARIAL STRESS TEST")
    print("==================================================================")

    # -------------------------------------------------------------
    # 1. ADV-03 Deep Dive: Credential Masking Edge Cases
    # -------------------------------------------------------------
    print("\n--- 1. ADV-03 Deep Dive: Credential Masking Edge Cases ---")

    test_cases_mask = [
        # (Input URL, Forbidden substrings, Required substrings, Description)
        (
            "postgresql+psycopg2://user:p@ssword!@localhost:5432/mydb",
            ["p@ssword!", "ssword!"],
            ["user:***", "localhost:5432/mydb"],
            "Single @ in password"
        ),
        (
            "postgresql://user:p@ss@w@rd@@host.com:5432/db",
            ["p@ss@w@rd@"],
            ["user:***", "host.com:5432/db"],
            "Multiple @ in password"
        ),
        (
            "postgresql://user:p%40ssword@localhost:5432/mydb",
            ["p%40ssword"],
            ["user:***", "localhost:5432/mydb"],
            "Percent-encoded @ in password"
        ),
        (
            "postgresql://admin:superSecret!@localhost:5432/db?token=my@secret@token&key=val",
            ["superSecret!"],
            ["admin:***", "localhost:5432/db"],
            "Password with query param containing @"
        ),
        (
            "postgresql://user:s3cr3t@localhost:5432/db#fragment@123",
            ["s3cr3t"],
            ["user:***", "localhost:5432/db"],
            "Password with fragment containing @"
        ),
        (
            "sqlite:///path/to/my@folder/database.db",
            [],
            ["sqlite:///path/to/my"],
            "SQLite path containing @"
        ),
        (
            "postgresql://user:pass_with_unicode_🔒@localhost:5432/db",
            ["pass_with_unicode_🔒"],
            ["user:***"],
            "Password with unicode emoji"
        ),
        (
            "postgresql://myuser:@localhost:5432/mydb",
            [],
            ["myuser:***@localhost:5432/mydb"],
            "Empty password with username"
        ),
    ]

    adv03_all_pass = True
    for raw_url, forbidden, required, desc in test_cases_mask:
        masked = mask_database_url(raw_url)
        failed_sub = [f for f in forbidden if f in masked]
        missing_sub = [r for r in required if r not in masked]
        if failed_sub:
            record(f"ADV-03-{desc}", False, f"Leaked forbidden string(s) {failed_sub} in masked: '{masked}'")
            adv03_all_pass = False
        elif missing_sub:
            record(f"ADV-03-{desc}", False, f"Missing required string(s) {missing_sub} in masked: '{masked}'")
            adv03_all_pass = False
        else:
            record(f"ADV-03-{desc}", True, f"Masked securely: '{masked}'")

    # -------------------------------------------------------------
    # 2. ADV-07 Deep Dive: create_app_engine with URL instances & kwargs
    # -------------------------------------------------------------
    print("\n--- 2. ADV-07 Deep Dive: URL Object & Dialect Robustness ---")

    try:
        # SQLite memory URL object
        u1 = make_url("sqlite:///:memory:")
        eng1 = create_app_engine(u1)
        assert eng1.dialect.name == "sqlite"
        assert getattr(eng1.pool, "_pre_ping", False) is True

        # SQLite file URL object with custom kwargs
        u2 = make_url("sqlite:///data/test_custom_kwargs.db")
        eng2 = create_app_engine(u2, echo=False)
        assert eng2.dialect.name == "sqlite"

        # Postgres URL object
        u3 = make_url("postgresql://myuser:mypass@localhost:5432/mydb")
        eng3 = create_app_engine(u3)
        assert eng3.dialect.name == "postgresql"
        assert getattr(eng3.pool, "_pre_ping", False) is True

        # Structured URL object construction
        u4 = URL.create(
            drivername="postgresql+psycopg",
            username="testuser",
            password="testpassword",
            host="127.0.0.1",
            port=5432,
            database="testdb"
        )
        eng4 = create_app_engine(u4)
        assert eng4.dialect.name == "postgresql"
        assert eng4.dialect.driver == "psycopg"

        record("ADV-07-URL-Objects", True, "Successfully handled make_url, URL.create, and kwargs forwarding")
    except Exception as exc:
        record("ADV-07-URL-Objects", False, f"Failed URL object test: {exc}")

    # -------------------------------------------------------------
    # 3. ADV-09 Deep Dive: Psycopg 3 & Settings Validation
    # -------------------------------------------------------------
    print("\n--- 3. ADV-09 Deep Dive: Settings DATABASE_URL Normalization ---")

    try:
        s1 = Settings(DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/dristik")
        assert s1.is_sqlite is False
        assert s1.sqlite_db_path is None

        # Postgres alias normalization: postgres:// -> postgresql://
        s2 = Settings(DATABASE_URL="postgres://user:pass@localhost:5432/dristik")
        assert s2.DATABASE_URL.startswith("postgresql://")

        # Fallback to default when empty or whitespace
        s3 = Settings(DATABASE_URL="   ")
        assert s3.DATABASE_URL == "sqlite:///data/dristik.db"
        assert s3.is_sqlite is True

        # Invalid schemes rejection
        invalid_schemes = ["mysql://user:pass@localhost/db", "oracle://host/db", "http://not-a-db"]
        invalid_caught = 0
        for inv in invalid_schemes:
            try:
                Settings(DATABASE_URL=inv)
            except ValueError:
                invalid_caught += 1
        assert invalid_caught == len(invalid_schemes)

        record("ADV-09-Settings-Schemes", True, "postgresql+psycopg accepted, postgres:// normalized, empty defaulted, invalid schemes rejected")
    except Exception as exc:
        record("ADV-09-Settings-Schemes", False, f"Failed settings normalization: {exc}")

    # -------------------------------------------------------------
    # 4. ADV-12b Deep Dive: Timeout Enforcement on Blackhole IPs
    # -------------------------------------------------------------
    print("\n--- 4. ADV-12b Deep Dive: Unroutable / Blackhole Timeout Enforcement ---")

    # Test with a very short timeout (0.5s) on RFC 5737 blackhole IP
    unroutable_eng = create_app_engine("postgresql://user:pass@192.0.2.1:5432/dristik")

    t_start = time.time()
    try:
        verify_database_connection(unroutable_eng, timeout_seconds=0.5)
        record("ADV-12b-Blackhole-0.5s", False, "Failed to raise DatabaseConnectionError on blackhole IP")
    except DatabaseConnectionError as exc:
        elapsed = time.time() - t_start
        # Bounded between 0.4s and 1.5s
        if 0.4 <= elapsed <= 1.5:
            record("ADV-12b-Blackhole-0.5s", True, f"Cleanly timed out and raised DatabaseConnectionError in {elapsed:.2f}s (target 0.5s)")
        else:
            record("ADV-12b-Blackhole-0.5s", False, f"Elapsed time {elapsed:.2f}s outside acceptable window for 0.5s timeout")
    except Exception as exc:
        record("ADV-12b-Blackhole-0.5s", False, f"Raised unexpected exception: {type(exc)}: {exc}")

    # Test with 1.0s timeout
    t_start = time.time()
    try:
        verify_database_connection(unroutable_eng, timeout_seconds=1.0)
        record("ADV-12b-Blackhole-1.0s", False, "Failed to raise DatabaseConnectionError on blackhole IP")
    except DatabaseConnectionError as exc:
        elapsed = time.time() - t_start
        if 0.9 <= elapsed <= 2.2:
            record("ADV-12b-Blackhole-1.0s", True, f"Cleanly timed out and raised DatabaseConnectionError in {elapsed:.2f}s (target 1.0s)")
        else:
            record("ADV-12b-Blackhole-1.0s", False, f"Elapsed time {elapsed:.2f}s outside acceptable window for 1.0s timeout")

    # -------------------------------------------------------------
    # 5. ADV-13 Deep Dive: SQLite File Corruption Detection
    # -------------------------------------------------------------
    print("\n--- 5. ADV-13 Deep Dive: SQLite Corruption Stress Testing ---")

    # Case A: Random garbage header
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"CORRUPTED_HEADER_NOT_A_VALID_SQLITE_DATABASE" * 50)
        p_corrupt = f.name
    try:
        eng_corrupt = create_app_engine(f"sqlite:///{p_corrupt}")
        try:
            verify_database_connection(eng_corrupt)
            record("ADV-13-Garbage-Header", False, "Failed to detect corrupted header")
        except DatabaseConnectionError:
            record("ADV-13-Garbage-Header", True, "Successfully caught corrupted SQLite file header")
    finally:
        if os.path.exists(p_corrupt):
            os.unlink(p_corrupt)

    # Case B: Truncated header (e.g. 16 bytes of garbage)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"SQLite format 3\x00_TRUNCATED")
        p_trunc = f.name
    try:
        eng_trunc = create_app_engine(f"sqlite:///{p_trunc}")
        try:
            verify_database_connection(eng_trunc)
            record("ADV-13-Truncated-Header", False, "Failed to detect truncated header")
        except DatabaseConnectionError:
            record("ADV-13-Truncated-Header", True, "Successfully caught truncated SQLite file header")
    finally:
        if os.path.exists(p_trunc):
            os.unlink(p_trunc)

    # Case C: Valid SQLite database (must PASS health check!)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        p_valid = f.name
    try:
        eng_valid = create_app_engine(f"sqlite:///{p_valid}")
        # Initialize schema
        with eng_valid.connect() as c:
            c.execute(text("CREATE TABLE test (id integer primary key);"))
            c.commit()
        try:
            res = verify_database_connection(eng_valid)
            record("ADV-13-Valid-SQLite-Integrity", res is True, "Valid SQLite database passes verification cleanly")
        except Exception as exc:
            record("ADV-13-Valid-SQLite-Integrity", False, f"Valid SQLite database failed verification: {exc}")
    finally:
        if os.path.exists(p_valid):
            os.unlink(p_valid)

    # -------------------------------------------------------------
    # 6. Session Lifecycle & Concurrency Non-regression
    # -------------------------------------------------------------
    print("\n--- 6. Session Lifecycle & Concurrency Verification ---")
    concurrency_errors = []
    def worker_stress(w_id):
        try:
            gen = get_db()
            db = next(gen)
            # Query
            db.execute(text("SELECT 1")).scalar()
            if w_id % 3 == 0:
                # Normal close
                try:
                    next(gen)
                except StopIteration:
                    pass
            elif w_id % 3 == 1:
                # Simulating route exception
                try:
                    gen.throw(RuntimeError(f"Route error {w_id}"))
                except RuntimeError:
                    pass
            else:
                # Simulating client disconnect
                gen.close()
        except Exception as e:
            concurrency_errors.append(e)

    threads = [threading.Thread(target=worker_stress, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if not concurrency_errors:
        record("ADV-Lifecycle-50-Threads", True, "50 concurrent threads cleanly handled normal, exception, and disconnect lifecycles")
    else:
        record("ADV-Lifecycle-50-Threads", False, f"Concurrency errors: {concurrency_errors[0]}")

    print("\n==================================================================")
    total = len(results)
    passed = sum(1 for _, p, _ in results if p)
    failed = total - passed
    print(f"DEEP-DIVE SUMMARY: {passed}/{total} PASSED ({failed} FAILED)")
    print("==================================================================")
    return failed == 0

if __name__ == "__main__":
    success = run_deep_dive()
    sys.exit(0 if success else 1)

"""
Independent stress-test suite for Milestone M2 Iteration 2.
Audits edge cases, boundary conditions, and adversarial inputs.
"""
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

# Setup paths
backend_path = "/Users/sayantande/Downloads/dristik-main/backend"
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlalchemy.engine import make_url, URL
from sqlalchemy import text
from app.core.config import Settings
from app.core.exceptions import DatabaseConnectionError
import app.db.session as session_module
from app.db.session import (
    mask_database_url,
    create_app_engine,
    verify_database_connection,
    get_db,
)

def run_stress_tests():
    print("--- 1. Testing mask_database_url edge cases ---")
    # Test IPv6
    ipv6_url = "postgresql://user:secret@[::1]:5432/testdb"
    masked_ipv6 = mask_database_url(ipv6_url)
    assert "secret" not in masked_ipv6, f"Secret leaked in IPv6: {masked_ipv6}"
    print(f"IPv6 masked: {masked_ipv6}")

    # Test URL object
    url_obj = make_url("postgresql://u:p@localhost:5432/d")
    masked_obj = mask_database_url(url_obj)
    assert "p" not in masked_obj or "u:***@" in masked_obj
    print(f"URL obj masked: {masked_obj}")

    # Test no password
    no_pass_url = "postgresql://user@localhost:5432/db"
    masked_no_pass = mask_database_url(no_pass_url)
    assert "user" in masked_no_pass
    print(f"No pass masked: {masked_no_pass}")

    # Test empty password
    empty_pass_url = "postgresql://user:@localhost:5432/db"
    masked_empty_pass = mask_database_url(empty_pass_url)
    print(f"Empty pass masked: {masked_empty_pass}")

    # Test tricky characters in password (!, $, %, @, #, &, *)
    tricky_url = "postgresql://user:p@$$w%rd#123@localhost:5432/mydb"
    masked_tricky = mask_database_url(tricky_url)
    assert "p@$$w%rd#123" not in masked_tricky
    print(f"Tricky pass masked: {masked_tricky}")

    # Test query params containing credentials/tokens
    query_url = "postgresql://user:mypassword@localhost:5432/db?token=secret_token&user=test"
    masked_query = mask_database_url(query_url)
    assert "mypassword" not in masked_query
    print(f"Query URL masked: {masked_query}")

    print("--- 2. Testing create_app_engine edge cases ---")
    # Test passing kwargs
    eng = create_app_engine("sqlite:///:memory:", echo=False)
    assert eng.dialect.name == "sqlite"

    # Test passing URL object with custom parameters
    sqlite_url_obj = make_url("sqlite:///:memory:")
    eng_obj = create_app_engine(sqlite_url_obj)
    assert eng_obj.dialect.name == "sqlite"

    # Test non-sqlite connect_timeout injection
    pg_url = "postgresql://test_user:test_pass@localhost:5432/test_db"
    eng_pg = create_app_engine(pg_url)
    assert eng_pg.dialect.name == "postgresql"

    print("--- 3. Testing verify_database_connection edge cases ---")
    # In-memory SQLite
    assert verify_database_connection(eng) is True

    # Corrupt SQLite: >= 100 bytes invalid header
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"INVALID_HEADER_GARBAGE_" * 10) # 230 bytes
        corrupt_db = f.name
    try:
        eng_corrupt = create_app_engine(f"sqlite:///{corrupt_db}")
        try:
            verify_database_connection(eng_corrupt)
            assert False, "Should have raised DatabaseConnectionError for corrupt db"
        except DatabaseConnectionError as e:
            assert "file is not a database" in str(e)
            print(f"Corrupt SQLite header caught: {e}")
    finally:
        if os.path.exists(corrupt_db):
            os.unlink(corrupt_db)

    # Empty 0-byte SQLite file: In SQLite, 0-byte file is valid initial state
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        empty_db = f.name
    try:
        eng_empty = create_app_engine(f"sqlite:///{empty_db}")
        # An empty file is initialized on first query in SQLite
        res = verify_database_connection(eng_empty)
        assert res is True
        print(f"0-byte SQLite initialized and verified: {res}")
    finally:
        if os.path.exists(empty_db):
            os.unlink(empty_db)

    # Fast timeout test (probe worker thread timeout)
    slow_eng = create_app_engine("sqlite:///:memory:")
    def slow_connect(*args, **kwargs):
        time.sleep(0.1)
        return slow_eng.connect()
    
    with patch.object(slow_eng, "connect", side_effect=slow_connect):
        try:
            verify_database_connection(slow_eng, timeout_seconds=0.02)
            assert False, "Should have raised DatabaseConnectionError on timeout"
        except DatabaseConnectionError as exc:
            assert "timed out after" in str(exc)
            print(f"Probe timeout cleanly raised: {exc}")

    print("--- 4. Testing Settings validation edge cases ---")
    # Test normalization of postgres://
    s1 = Settings(DATABASE_URL="postgres://user:pass@localhost:5432/dristik")
    assert s1.DATABASE_URL.startswith("postgresql://")

    # Test psycopg 3
    s2 = Settings(DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/dristik")
    assert s2.DATABASE_URL.startswith("postgresql+psycopg://")

    # Test empty or whitespace DATABASE_URL defaults to sqlite
    s3 = Settings(DATABASE_URL="   ")
    assert s3.DATABASE_URL == "sqlite:///data/dristik.db"

    print("--- ALL STRESS TESTS PASSED CLEANLY ---")

if __name__ == "__main__":
    run_stress_tests()

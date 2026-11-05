"""
Empirical Adversarial Challenge Suite for Milestone M2.
Tests database session lifecycle, error handling, URL masking, engine configuration,
and connectivity edge cases.
"""
import sys
import os
import re
import tempfile
import threading
import time
from unittest.mock import patch

# Setup paths
backend_path = os.path.abspath("/Users/sayantande/Downloads/dristik-main/backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlalchemy import text, Column, Integer, String
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError

import app.db.session as session_module
from app.db.session import (
    create_app_engine,
    create_db_engine,
    get_db,
    mask_database_url,
    verify_database_connection,
    DatabaseConnectionError,
    SessionLocal,
    Base,
    engine,
)
from app.core.config import Settings, settings

class AdversarialRunner:
    def __init__(self):
        self.results = []

    def record(self, test_id: str, title: str, passed: bool, details: str):
        self.results.append({
            "id": test_id,
            "title": title,
            "passed": passed,
            "details": details
        })
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_id}: {title} - {details}")

    def run_all(self):
        print("==================================================================")
        print("STARTING EMPIRICAL ADVERSARIAL TEST SUITE (MILESTONE M2)")
        print("==================================================================")
        self.test_mock_session_removal()
        self.test_mask_database_url_standard()
        self.test_mask_database_url_unencoded_at()
        self.test_mask_database_url_sqlite()
        self.test_create_engine_pool_pre_ping()
        self.test_create_engine_sqlite_threads()
        self.test_create_engine_url_object()
        self.test_config_database_url_schemes()
        self.test_config_psycopg3_scheme()
        self.test_verify_connection_bad_port()
        self.test_verify_connection_unreachable_socket()
        self.test_verify_connection_auth_failure()
        self.test_verify_connection_unroutable_timeout()
        self.test_verify_connection_corrupt_sqlite()
        self.test_get_db_rollback_on_error()
        self.test_get_db_generator_exit()
        self.test_get_db_concurrency_stress()
        print("==================================================================")
        print(f"SUMMARY: {sum(1 for r in self.results if r['passed'])} PASSED, {sum(1 for r in self.results if not r['passed'])} FAILED")
        print("==================================================================")

    def test_mock_session_removal(self):
        has_mock = hasattr(session_module, "MockSession")
        if not has_mock:
            self.record("ADV-01", "MockSession Elimination", True, "MockSession attribute does not exist on app.db.session")
        else:
            self.record("ADV-01", "MockSession Elimination", False, "MockSession still exists on app.db.session")

    def test_mask_database_url_standard(self):
        url = "postgresql://myuser:secretpassword123@db.example.com:5432/proddb"
        masked = mask_database_url(url)
        if "secretpassword123" not in masked and "myuser" in masked and "db.example.com" in masked:
            self.record("ADV-02", "Standard URL Password Masking", True, f"Rendered safely: {masked}")
        else:
            self.record("ADV-02", "Standard URL Password Masking", False, f"Password leaked in masked string: {masked}")

    def test_mask_database_url_unencoded_at(self):
        url = "postgresql+psycopg2://user:p@ssword!@localhost:5432/mydb"
        masked = mask_database_url(url)
        # Check if any part of password after @ is leaked
        if "ssword!" in masked:
            self.record("ADV-03", "URL Masking with Unencoded @ in Password", False, f"Leaked password fragment 'ssword!' in fallback regex: {masked}")
        else:
            self.record("ADV-03", "URL Masking with Unencoded @ in Password", True, f"Masked without leaking: {masked}")

    def test_mask_database_url_sqlite(self):
        urls = ["sqlite:///data/dristik.db", "sqlite:///:memory:", "sqlite://"]
        all_ok = True
        for u in urls:
            m = mask_database_url(u)
            if not m.startswith("sqlite://"):
                all_ok = False
        self.record("ADV-04", "SQLite URL Masking Preservation", all_ok, f"Preserved SQLite paths across variants")

    def test_create_engine_pool_pre_ping(self):
        eng = create_app_engine("sqlite:///:memory:")
        has_pre_ping = getattr(eng.pool, "_pre_ping", False)
        if has_pre_ping is True:
            self.record("ADV-05", "Engine pool_pre_ping Enforcement", True, "Engine pool._pre_ping is True")
        else:
            self.record("ADV-05", "Engine pool_pre_ping Enforcement", False, f"Engine pool._pre_ping is {has_pre_ping}")

    def test_create_engine_sqlite_threads(self):
        eng = create_app_engine("sqlite:///:memory:")
        conn = eng.connect()
        thread_error = []
        def worker():
            try:
                res = conn.execute(text("SELECT 100")).scalar()
                if res != 100:
                    thread_error.append(f"Unexpected result: {res}")
            except Exception as e:
                thread_error.append(str(e))
        t = threading.Thread(target=worker)
        t.start()
        t.join()
        conn.close()
        if not thread_error:
            self.record("ADV-06", "SQLite check_same_thread=False Enforcement", True, "Cross-thread execution succeeded without error")
        else:
            self.record("ADV-06", "SQLite check_same_thread=False Enforcement", False, f"Failed with: {thread_error[0]}")

    def test_create_engine_url_object(self):
        url_obj = make_url("sqlite:///data/test_url_obj.db")
        try:
            eng = create_app_engine(url_obj)
            self.record("ADV-07", "Engine Creation from URL Object", True, "Successfully created engine from make_url() URL object")
        except AttributeError as e:
            self.record("ADV-07", "Engine Creation from URL Object", False, f"AttributeError on URL object: {e}")
        except Exception as e:
            self.record("ADV-07", "Engine Creation from URL Object", False, f"Unexpected error: {e}")

    def test_config_database_url_schemes(self):
        valid_schemes = [
            "sqlite:///test.db",
            "sqlite+pysqlite:///test.db",
            "postgresql://u:p@h:5432/d",
            "postgresql+psycopg2://u:p@h:5432/d",
            "postgresql+asyncpg://u:p@h:5432/d",
            "postgresql+pg8000://u:p@h:5432/d",
        ]
        all_passed = True
        for vs in valid_schemes:
            try:
                Settings(DATABASE_URL=vs)
            except Exception:
                all_passed = False
        self.record("ADV-08", "Settings DATABASE_URL Standard Schemes", all_passed, "Standard SQLite and PostgreSQL schemes accepted")

    def test_config_psycopg3_scheme(self):
        scheme = "postgresql+psycopg://user:pass@localhost:5432/dristik"
        try:
            Settings(DATABASE_URL=scheme)
            self.record("ADV-09", "Settings DATABASE_URL postgresql+psycopg Support", True, "Accepted postgresql+psycopg scheme")
        except ValueError as e:
            self.record("ADV-09", "Settings DATABASE_URL postgresql+psycopg Support", False, f"Rejected postgresql+psycopg://: {e}")

    def test_verify_connection_bad_port(self):
        bad_engine = create_app_engine("postgresql://user:secret123@127.0.0.1:59999/dristik")
        try:
            verify_database_connection(bad_engine, timeout_seconds=1.0)
            self.record("ADV-10", "Fail-fast Connection Check on Bad Port", False, "Did not raise DatabaseConnectionError")
        except DatabaseConnectionError as e:
            msg = str(e)
            if "secret123" in msg:
                self.record("ADV-10", "Fail-fast Connection Check on Bad Port", False, "Raised error but leaked password in exception message")
            else:
                self.record("ADV-10", "Fail-fast Connection Check on Bad Port", True, "Cleanly raised DatabaseConnectionError with masked credentials")

    def test_verify_connection_unreachable_socket(self):
        bad_socket_engine = create_app_engine("postgresql://user:pass@/dristik?host=/tmp/nonexistent_socket_path_12345")
        try:
            verify_database_connection(bad_socket_engine, timeout_seconds=1.0)
            self.record("ADV-11", "Fail-fast Connection Check on Unreachable Socket", False, "Did not raise DatabaseConnectionError")
        except DatabaseConnectionError:
            self.record("ADV-11", "Fail-fast Connection Check on Unreachable Socket", True, "Cleanly raised DatabaseConnectionError on missing unix socket")

    def test_verify_connection_auth_failure(self):
        engine_mock = create_app_engine("postgresql://validuser:wrongpass@localhost:5432/dristik")
        auth_err = OperationalError("FATAL: password authentication failed for user 'validuser'", None, None)
        with patch.object(engine_mock, "connect", side_effect=auth_err):
            try:
                verify_database_connection(engine_mock)
                self.record("ADV-12", "Fail-fast on Invalid Credentials", False, "Did not raise DatabaseConnectionError")
            except DatabaseConnectionError:
                self.record("ADV-12", "Fail-fast on Invalid Credentials", True, "Cleanly raised DatabaseConnectionError on credential rejection")

    def test_verify_connection_unroutable_timeout(self):
        # 192.0.2.1 is TEST-NET-1 (RFC 5737), blackholed IP that drops SYN packets
        unroutable_eng = create_app_engine("postgresql://user:pass@192.0.2.1:5432/dristik")
        t_start = time.time()
        timeout_limit = 1.0
        
        result_container = {"completed": False, "elapsed": None, "error": None}
        def probe():
            try:
                verify_database_connection(unroutable_eng, timeout_seconds=timeout_limit)
            except Exception as exc:
                result_container["error"] = exc
            finally:
                result_container["elapsed"] = time.time() - t_start
                result_container["completed"] = True

        probe_thread = threading.Thread(target=probe)
        probe_thread.daemon = True
        probe_thread.start()
        # Give it up to 2.5s (2.5x the requested 1.0s timeout)
        probe_thread.join(timeout=2.5)

        if not result_container["completed"]:
            self.record("ADV-12b", "Connection Timeout Enforcement on Unroutable Host", False, f"Hanged: Connection probe failed to terminate within requested {timeout_limit}s timeout (exceeded 2.5s because connect_timeout is not configured)")
        else:
            self.record("ADV-12b", "Connection Timeout Enforcement on Unroutable Host", True, f"Terminated in {result_container['elapsed']:.2f}s with {result_container['error']}")

    def test_verify_connection_corrupt_sqlite(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            f.write(b"CORRUPT_GARBAGE_HEADER_DATA_12345" * 50)
            path = f.name
        try:
            corrupt_eng = create_app_engine(f"sqlite:///{path}")
            try:
                verify_database_connection(corrupt_eng)
                self.record("ADV-13", "Corrupt SQLite File Health Check", False, "SELECT 1 succeeded on corrupt database file without detecting invalid header")
            except DatabaseConnectionError:
                self.record("ADV-13", "Corrupt SQLite File Health Check", True, "Detected corrupt SQLite header")
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_get_db_rollback_on_error(self):
        # Create temporary table
        with engine.connect() as c:
            c.execute(text("CREATE TABLE IF NOT EXISTS test_adv_rollback (val text);"))
            c.execute(text("DELETE FROM test_adv_rollback;"))
            c.commit()

        gen = get_db()
        db = next(gen)
        db.execute(text("INSERT INTO test_adv_rollback VALUES ('pending_commit')"))
        
        # Verify pending insert in same session
        val = db.execute(text("SELECT val FROM test_adv_rollback")).scalar()
        assert val == "pending_commit"

        # Route exception
        try:
            gen.throw(RuntimeError("Simulated route crash"))
        except RuntimeError:
            pass

        # Check from fresh session
        with SessionLocal() as s:
            check_val = s.execute(text("SELECT count(*) FROM test_adv_rollback")).scalar()
            
        with engine.connect() as c:
            c.execute(text("DROP TABLE IF EXISTS test_adv_rollback;"))
            c.commit()

        if check_val == 0:
            self.record("ADV-14", "get_db Rollback on Route Exception", True, "Transaction successfully rolled back and verified in clean DB session")
        else:
            self.record("ADV-14", "get_db Rollback on Route Exception", False, f"Uncommitted transaction leaked: {check_val} rows found")

    def test_get_db_generator_exit(self):
        gen = get_db()
        db = next(gen)
        with patch.object(db, "close", wraps=db.close) as mock_close:
            gen.close()
            if mock_close.called:
                self.record("ADV-15", "get_db Cleanup on GeneratorExit (Client Disconnect)", True, "db.close() invoked on generator.close()")
            else:
                self.record("ADV-15", "get_db Cleanup on GeneratorExit (Client Disconnect)", False, "db.close() was not invoked on GeneratorExit")

    def test_get_db_concurrency_stress(self):
        concurrency_errors = []
        def task(idx):
            try:
                gen = get_db()
                db = next(gen)
                db.execute(text("SELECT 1")).scalar()
                if idx % 2 == 0:
                    try:
                        gen.throw(ValueError("Error"))
                    except ValueError:
                        pass
                else:
                    try:
                        next(gen)
                    except StopIteration:
                        pass
            except Exception as e:
                concurrency_errors.append(e)

        threads = [threading.Thread(target=task, args=(i,)) for i in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if not concurrency_errors:
            self.record("ADV-16", "get_db 40-Thread Concurrency Pressure", True, "All 40 concurrent sessions executed, rolled back, and closed without pool leaks")
        else:
            self.record("ADV-16", "get_db 40-Thread Concurrency Pressure", False, f"Concurrency errors occurred: {concurrency_errors[0]}")

if __name__ == "__main__":
    runner = AdversarialRunner()
    runner.run_all()

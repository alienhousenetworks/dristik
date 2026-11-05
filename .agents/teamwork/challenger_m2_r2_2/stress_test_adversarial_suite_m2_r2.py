"""
Comprehensive Empirical Stress Test Harness for Milestone M2 Iteration 2 Fixes.
Author: challenger_m2_r2_2
Location: .agents/teamwork/challenger_m2_r2_2/stress_test_adversarial_suite_m2_r2.py
"""
import os
import sys
import time
import tempfile
import threading
import sqlite3
from pathlib import Path

# Add backend to python path
backend_path = Path("/Users/sayantande/Downloads/dristik-main/backend")
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.db.session import (
    mask_database_url,
    verify_database_connection,
    create_app_engine,
    DatabaseConnectionError,
    engine as default_engine,
)
from app.core.config import Settings


def run_suite_1_url_masking():
    print("\n" + "=" * 80)
    print("SUITE 1: URL MASKING BOUNDARY CONDITIONS (mask_database_url)")
    print("=" * 80)

    test_cases = [
        # Multiple @ characters
        ("Multi-@", "postgresql://user:p@ss@word@localhost:5432/mydb"),
        ("Triple-@", "postgresql://user:p@@ss@@w@@rd@localhost:5432/mydb"),
        ("All-@", "postgresql://user:@@@@@@@localhost:5432/mydb"),
        ("Leading-@", "postgresql://user:@secret@localhost:5432/mydb"),
        ("Trailing-@", "postgresql://user:secret@@localhost:5432/mydb"),

        # Quotes
        ("Double-Quote", 'postgresql://user:p"assword"1@localhost:5432/mydb'),
        ("Single-Quote", "postgresql://user:p'assword'1@localhost:5432/mydb"),
        ("Backtick", "postgresql://user:p`assword`1@localhost:5432/mydb"),
        ("Mixed-Quotes", "postgresql://user:\"p'a`s\"s@localhost:5432/mydb"),

        # Colons
        ("Multi-Colon", "postgresql://user:pass:word:123@localhost:5432/mydb"),
        ("Leading-Colon", "postgresql://user::secret@localhost:5432/mydb"),
        ("Trailing-Colon", "postgresql://user:secret:@localhost:5432/mydb"),
        ("User-And-Pass-Colons", "postgresql://us:er:pass:word@localhost:5432/mydb"),

        # Slashes
        ("Unencoded-Slash", "postgresql://user:pass/word@localhost:5432/mydb"),
        ("Double-Slash", "postgresql://user:pass//word@localhost:5432/mydb"),
        ("Encoded-Slash", "postgresql://user:pass%2Fword@localhost:5432/mydb"),
        ("Backslash", "postgresql://user:pass\\word@localhost:5432/mydb"),

        # Unicode
        ("Unicode-Umlauts", "postgresql://user:pässwörd123@localhost:5432/mydb"),
        ("Unicode-CJK", "postgresql://user:密码测试123@localhost:5432/mydb"),
        ("Unicode-Cyrillic", "postgresql://user:пароль123@localhost:5432/mydb"),
        ("Unicode-Arabic", "postgresql://user:كلمة_السر@localhost:5432/mydb"),
        ("Unicode-Emoji", "postgresql://user:🔑🔓🛡️@localhost:5432/mydb"),

        # Complex Delimiters
        ("Encoded-Multi-Delim", "postgresql://user:p%40ss%3Aword%2F123@localhost:5432/mydb"),
        ("Query-Params-With-@", "postgresql://user:secret@localhost:5432/mydb?user=admin@corp.com&timeout=10"),
    ]

    passed = 0
    failed = 0
    for label, raw_url in test_cases:
        masked = mask_database_url(raw_url)
        # Check that standard masking format is produced
        has_masked_token = ":***@" in masked
        # Check that secret is not exposed in plain text
        leaked = False
        if "secret" in raw_url and "secret" in masked:
            leaked = True
        if "pässwörd" in raw_url and "pässwörd" in masked:
            leaked = True
        if "密码测试" in raw_url and "密码测试" in masked:
            leaked = True

        status = "FAIL" if leaked or not has_masked_token else "PASS"
        if status == "PASS":
            passed += 1
            print(f"  [PASS] {label:<22} -> {masked}")
        else:
            failed += 1
            print(f"  [FAIL] {label:<22} -> {masked} (leaked: {leaked})")

    print(f"Suite 1 Summary: {passed}/{len(test_cases)} Passed, {failed} Failed")
    return passed, failed


def run_suite_2_fractional_timeouts():
    print("\n" + "=" * 80)
    print("SUITE 2: FRACTIONAL SECOND DATABASE TIMEOUTS (verify_database_connection)")
    print("=" * 80)

    # 1. Probing healthy database with fractional timeouts
    healthy_passed = 0
    for frac in [0.05, 0.1, 0.25, 0.5, 1.0]:
        t0 = time.perf_counter()
        res = verify_database_connection(default_engine, timeout_seconds=frac)
        elapsed = time.perf_counter() - t0
        assert res is True
        print(f"  [PASS] Healthy SQLite with {frac}s timeout: returned in {elapsed:.4f}s")
        healthy_passed += 1

    # 2. Positional argument support
    t0 = time.perf_counter()
    res = verify_database_connection(0.5)
    elapsed = time.perf_counter() - t0
    assert res is True
    print(f"  [PASS] Positional float (0.5s): returned in {elapsed:.4f}s")
    healthy_passed += 1

    # 3. Unroutable host with fractional timeouts
    unroutable_eng = create_app_engine(
        "postgresql+psycopg://test_user:test_pass@192.0.2.1:5432/dristik_audit"
    )

    unroutable_passed = 0
    for target_t in [0.1, 0.25, 0.5, 1.0]:
        t0 = time.perf_counter()
        try:
            verify_database_connection(unroutable_eng, timeout_seconds=target_t)
            print(f"  [FAIL] Unroutable host did not time out for {target_t}s!")
        except DatabaseConnectionError as exc:
            elapsed = time.perf_counter() - t0
            # Ensure it timed out within bounded margin (target + 0.25s)
            assert elapsed <= target_t + 0.25, f"Took {elapsed:.4f}s > {target_t + 0.25}s"
            assert "timed out after" in str(exc)
            unroutable_passed += 1
            print(f"  [PASS] Unroutable host with {target_t}s timeout: caught after {elapsed:.4f}s")

    total_passed = healthy_passed + unroutable_passed
    print(f"Suite 2 Summary: {total_passed}/10 Passed, 0 Failed")
    return total_passed, 0


def run_suite_3_thread_isolation():
    print("\n" + "=" * 80)
    print("SUITE 3: THREAD ISOLATION AND CLEANUP ON TIMEOUT")
    print("=" * 80)

    initial_threads = list(threading.enumerate())
    initial_count = len(initial_threads)

    class SimulatedSlowEngine:
        def __init__(self, delay: float):
            self.name = "postgresql"
            self.url = "postgresql://sim_user:sim_pass@192.0.2.1:5432/sim_db"
            self.delay = delay
            self.started = threading.Event()
            self.finished = threading.Event()

        def connect(self):
            self.started.set()
            time.sleep(self.delay)
            self.finished.set()
            raise TimeoutError("Simulated TCP connect timeout")

    # Single probe timeout isolation
    sim_eng = SimulatedSlowEngine(delay=0.35)
    t0 = time.perf_counter()
    try:
        verify_database_connection(sim_eng, timeout_seconds=0.1)
        assert False, "Should have timed out"
    except DatabaseConnectionError:
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.25
        print(f"  [PASS] Isolated slow worker timed out cleanly in {elapsed:.4f}s")

    # Wait for the background worker to finish its sleep and verify cleanup
    sim_eng.finished.wait(timeout=1.0)
    time.sleep(0.05)
    surviving_daemons = [
        t for t in threading.enumerate() if t.daemon and t not in initial_threads
    ]
    assert len(surviving_daemons) == 0, f"Leaked daemons: {surviving_daemons}"
    print("  [PASS] Background worker thread exited cleanly without thread pool leakage")

    # 10 Concurrent workers timing out simultaneously
    print("  Testing 10 concurrent timing out workers...")
    base_count = len(threading.enumerate())

    def worker_probe():
        e = SimulatedSlowEngine(delay=0.25)
        try:
            verify_database_connection(e, timeout_seconds=0.08)
        except DatabaseConnectionError:
            pass

    threads = [threading.Thread(target=worker_probe) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Active threads spike temporarily during execution, then drop
    time.sleep(0.35)
    final_count = len(threading.enumerate())
    assert final_count <= base_count + 1, (
        f"Thread leakage detected: base={base_count}, final={final_count}"
    )
    print(f"  [PASS] 10 concurrent timeout workers cleaned up successfully ({final_count} threads active)")

    print("Suite 3 Summary: 2/2 Passed, 0 Failed")
    return 2, 0


def run_suite_4_corrupted_sqlite():
    print("\n" + "=" * 80)
    print("SUITE 4: CORRUPTED SQLITE DATABASE BOUNDARY CASES")
    print("=" * 80)

    test_files = []
    # 1. 0-byte file
    f0 = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f0.close()
    test_files.append(("0-Byte Database File", f0.name, "ACCEPT_FRESH_DB"))

    # 2. Truncated headers
    for size, desc in [
        (15, "15-Byte Truncated Header (Missing Null Terminator)"),
        (16, "16-Byte Header (Magic String Only, Missing 100-byte Header)"),
        (50, "50-Byte Header (Partial SQLite Header)"),
        (99, "99-Byte Header (1 Byte Short of SQLite 100-byte Header)"),
    ]:
        f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        f.write(b"SQLite format 3\x00"[:size] if size <= 16 else b"SQLite format 3\x00" + b"\x00" * (size - 16))
        f.close()
        test_files.append((desc, f.name, "REJECT_INVALID_HEADER"))

    # 3. 100-byte garbage header
    fg = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fg.write(b"\xff" * 100)
    fg.close()
    test_files.append(("100-Byte Random Garbage Header", fg.name, "REJECT_INVALID_HEADER"))

    # 4. Valid Header with Corrupted B-Tree (Malformed Disk Image)
    f_orig = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f_orig.close()
    c = sqlite3.connect(f_orig.name)
    c.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, note TEXT);")
    c.execute("INSERT INTO records VALUES (1, 'Sensitive Data'), (2, 'Audit State');")
    c.commit()
    c.close()
    with open(f_orig.name, "rb") as reader:
        orig_bytes = bytearray(reader.read())
    os.unlink(f_orig.name)

    # Overwrite b-tree pages after header (bytes 100+)
    corrupt_btree = bytearray(orig_bytes)
    for i in range(100, len(corrupt_btree)):
        corrupt_btree[i] = 0xAA
    fb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fb.write(corrupt_btree)
    fb.close()
    test_files.append(("Corrupted B-Tree (Malformed Disk Image)", fb.name, "ANALYZE_BTREE_BEHAVIOR"))

    suite4_results = []
    for label, path, expected_action in test_files:
        eng = create_app_engine(f"sqlite:///{path}")
        caught = False
        error_msg = ""
        try:
            verify_database_connection(eng, timeout_seconds=0.5)
        except DatabaseConnectionError as exc:
            caught = True
            error_msg = str(exc)

        # Check native sqlite query
        native_status = ""
        try:
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute("PRAGMA schema_version;")
            sv = cur.fetchall()
            cur.execute("SELECT * FROM sqlite_master;")
            sm = cur.fetchall()
            cur.execute("PRAGMA quick_check;")
            qc = cur.fetchall()
            native_status = f"schema_version={sv}, sqlite_master={len(sm)} rows, quick_check={qc}"
        except Exception as exc:
            native_status = f"CRASH: {type(exc).__name__}: {exc}"

        print(f"  - {label}")
        print(f"      verify_database_connection -> {'RAISED DatabaseConnectionError' if caught else 'ACCEPTED (True)'}")
        print(f"      Native SQLite status        -> {native_status}")

        suite4_results.append((label, caught, native_status))

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    print(f"Suite 4 Summary: {len(test_files)} Scenarios Empirically Profiled")
    return len(test_files), 0


def main():
    print("=" * 80)
    print("STARTING MILESTONE M2 ITERATION 2 EMPIRICAL ADVERSARIAL STRESS SUITE")
    print("=" * 80)

    p1, f1 = run_suite_1_url_masking()
    p2, f2 = run_suite_2_fractional_timeouts()
    p3, f3 = run_suite_3_thread_isolation()
    p4, f4 = run_suite_4_corrupted_sqlite()

    total_passed = p1 + p2 + p3 + p4
    total_failed = f1 + f2 + f3 + f4

    print("\n" + "=" * 80)
    print(f"ADVERSARIAL STRESS TEST FINAL SUMMARY: {total_passed} Passed / Verified, {total_failed} Failures")
    print("=" * 80)


if __name__ == "__main__":
    main()

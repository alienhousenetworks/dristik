import sys
import time
import threading
from pathlib import Path

backend_path = Path("/Users/sayantande/Downloads/dristik-main/backend")
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.db.session import (
    verify_database_connection,
    create_app_engine,
    DatabaseConnectionError,
    engine as default_engine
)

def test_fractional_timeouts():
    print("=" * 80)
    print("TESTING FRACTIONAL SECOND TIMEOUTS IN verify_database_connection")
    print("=" * 80)
    
    # 1. Test healthy engine with fractional timeouts
    for t in [0.05, 0.1, 0.25, 0.5, 1.0]:
        t0 = time.perf_counter()
        res = verify_database_connection(default_engine, timeout_seconds=t)
        elapsed = time.perf_counter() - t0
        print(f"[PASS] Healthy SQLite with timeout={t}s: returned {res} in {elapsed:.4f}s")
        assert res is True
        assert elapsed < t or elapsed < 0.1, f"Elapsed {elapsed}s too high for timeout {t}s"

    # 2. Test positional float argument (e.g. verify_database_connection(0.5))
    t0 = time.perf_counter()
    res = verify_database_connection(0.5)
    elapsed = time.perf_counter() - t0
    print(f"[PASS] Positional float arg (0.5s): returned {res} in {elapsed:.4f}s")
    assert res is True

    # 3. Test unroutable host with fractional timeouts: 0.1s, 0.5s, 1.0s
    unroutable_engine = create_app_engine(
        "postgresql+psycopg://user:pass@192.0.2.1:5432/dristik"
    )

    test_intervals = [0.1, 0.25, 0.5, 1.0]
    for target_t in test_intervals:
        t0 = time.perf_counter()
        try:
            verify_database_connection(unroutable_engine, timeout_seconds=target_t)
            print(f"[FAIL] Expected timeout for {target_t}s did not raise exception!")
            assert False, "Expected DatabaseConnectionError"
        except DatabaseConnectionError as exc:
            elapsed = time.perf_counter() - t0
            # Allow reasonable delta (e.g., +0.15s for thread start/join overhead)
            print(f"[PASS] Unroutable host timeout={target_t}s: raised DatabaseConnectionError in {elapsed:.4f}s (message: '{exc}')")
            assert "timed out after" in str(exc)
            # Ensure it didn't hang indefinitely (must terminate within target_t + 0.25s)
            assert elapsed <= target_t + 0.25, f"Timeout took {elapsed:.4f}s, exceeded limit of {target_t + 0.25}s"

    print("=" * 80)
    print("ALL FRACTIONAL TIMEOUT TESTS PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    test_fractional_timeouts()

import sys
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock

backend_path = Path("/Users/sayantande/Downloads/dristik-main/backend")
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.db.session import (
    verify_database_connection,
    create_app_engine,
    DatabaseConnectionError,
    engine as default_engine
)

def test_thread_lifecycle_and_cleanup_on_timeout():
    print("=" * 80)
    print("TESTING THREAD ISOLATION AND WORKER LIFECYCLE ON TIMEOUT")
    print("=" * 80)
    
    initial_threads = threading.enumerate()
    initial_count = len(initial_threads)
    print(f"Initial active threads: {initial_count} ({[t.name for t in initial_threads]})")
    
    # 1. Test thread cleanup with a mock engine that simulates slow connect
    class SlowConnectEngine:
        def __init__(self, delay_sec: float):
            self.name = "postgresql"
            self.url = "postgresql://mock_user:mock_pass@mock_host:5432/mock_db"
            self.delay_sec = delay_sec
            self.thread_started = threading.Event()
            self.thread_finished = threading.Event()
            
        def connect(self):
            self.thread_started.set()
            time.sleep(self.delay_sec)
            self.thread_finished.set()
            raise TimeoutError("Simulated slow driver connect timeout")

    slow_eng = SlowConnectEngine(delay_sec=0.4)
    
    t0 = time.perf_counter()
    try:
        # Timeout is 0.1s, while connect sleeps for 0.4s
        verify_database_connection(slow_eng, timeout_seconds=0.1)
        assert False, "Should have timed out"
    except DatabaseConnectionError as exc:
        elapsed = time.perf_counter() - t0
        print(f"[PASS] verify_database_connection timed out in {elapsed:.4f}s as expected: {exc}")
        assert elapsed < 0.25
        
    # Thread should be alive immediately after timeout
    assert slow_eng.thread_started.is_set(), "Probe thread should have started"
    assert not slow_eng.thread_finished.is_set(), "Probe thread should still be running at 0.1s"
    mid_threads = [t for t in threading.enumerate() if t.daemon and t not in initial_threads]
    print(f"Threads during sleep delay: {len(threading.enumerate())} (daemon probe threads active: {len(mid_threads)})")
    assert len(mid_threads) >= 1, "Daemon worker thread is running during connect sleep"
    
    # Now wait for the slow connect to finish (0.4s total, remaining ~0.3s)
    finished = slow_eng.thread_finished.wait(timeout=1.0)
    assert finished, "Probe thread failed to complete connect simulation within 1.0s"
    
    # Give a tiny slice for thread exit
    time.sleep(0.05)
    
    # Verify the daemon thread is no longer running (cleaned up)
    final_daemon_threads = [t for t in threading.enumerate() if t.daemon and t not in initial_threads]
    print(f"Threads after delay expired: {len(threading.enumerate())} (probe threads remaining: {len(final_daemon_threads)})")
    assert len(final_daemon_threads) == 0, f"Thread leaked! Remaining daemon threads: {final_daemon_threads}"
    print("[PASS] Probe worker thread terminated and cleaned up cleanly without leaking!")

    # 2. Test concurrent timeouts: 10 parallel calls each with slow engines
    print("\n--- Testing 10 Concurrent Timeout Workers ---")
    threads_before_batch = len(threading.enumerate())
    
    def run_failing_probe(idx):
        eng = SlowConnectEngine(delay_sec=0.3)
        try:
            verify_database_connection(eng, timeout_seconds=0.08)
        except DatabaseConnectionError:
            pass

    batch = [threading.Thread(target=run_failing_probe, args=(i,)) for i in range(10)]
    for t in batch:
        t.start()
    for t in batch:
        t.join()
        
    print(f"10 batch caller threads finished. Active threads immediately after: {len(threading.enumerate())}")
    
    # Wait 0.4s for the 10 worker threads to finish their 0.3s sleep
    time.sleep(0.4)
    
    threads_after_batch = len(threading.enumerate())
    print(f"Active threads after delay expiration: {threads_after_batch}")
    # Compare with threads_before_batch
    assert threads_after_batch <= threads_before_batch + 1, (
        f"Thread leak detected after 10 concurrent timeouts! "
        f"Before: {threads_before_batch}, After: {threads_after_batch}"
    )
    print("[PASS] All 10 concurrent timeout workers cleaned up without leaking!")

    print("=" * 80)
    print("THREAD ISOLATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    test_thread_lifecycle_and_cleanup_on_timeout()

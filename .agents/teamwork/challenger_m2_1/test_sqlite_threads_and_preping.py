"""
Empirical test of check_same_thread=False and pool_pre_ping for SQLite.
"""
import sys
import os
import threading
import sqlite3

backend_path = os.path.abspath("/Users/sayantande/Downloads/dristik-main/backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.db.session import create_app_engine
from sqlalchemy import text

def test_multithreaded_connection():
    eng = create_app_engine("sqlite:///:memory:")
    conn = eng.connect()
    
    worker_error = []
    
    def worker():
        try:
            # Attempt to execute query on the connection created in the main thread
            val = conn.execute(text("SELECT 42")).scalar()
            if val != 42:
                worker_error.append(f"Unexpected val: {val}")
        except Exception as e:
            worker_error.append(e)

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    
    conn.close()
    
    if worker_error:
        print(f"FAILED: Thread worker encountered error: {worker_error[0]}")
    else:
        print("PASSED: check_same_thread=False successfully permits cross-thread execution.")

def test_pool_pre_ping_reconnection():
    # Test whether pool_pre_ping detects a dead connection and reconnects
    eng = create_app_engine("sqlite:///data/test_pre_ping.db")
    with eng.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS ping_test (id int);"))
        conn.execute(text("INSERT INTO ping_test VALUES (1);"))
        conn.commit()

    # Now checkout connection from pool
    conn = eng.connect()
    raw_conn = conn.connection.dbapi_connection
    # Close raw dbapi connection behind SQLAlchemy's back to simulate dead socket
    raw_conn.close()
    
    # Return connection proxy to pool
    conn.close()
    
    # Next checkout should trigger pool_pre_ping, detect closed connection, discard it and open fresh one
    try:
        with eng.connect() as conn2:
            res = conn2.execute(text("SELECT count(*) FROM ping_test")).scalar()
            assert res == 1
        print("PASSED: pool_pre_ping detected dead connection and cleanly reconnected.")
    except Exception as e:
        print(f"FAILED: pool_pre_ping failed to recover: {e}")

if __name__ == "__main__":
    test_multithreaded_connection()
    test_pool_pre_ping_reconnection()

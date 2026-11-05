"""
Test unreachable Unix socket, corrupted SQLite file, permission denied SQLite file.
"""
import sys
import os
import tempfile
from pathlib import Path

backend_path = os.path.abspath("/Users/sayantande/Downloads/dristik-main/backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.db.session import (
    create_app_engine,
    verify_database_connection,
    DatabaseConnectionError,
)

def test_unreachable_unix_socket():
    print("--- Test unreachable unix socket ---")
    socket_url = "postgresql://user:pass@/dristik?host=/tmp/nonexistent_socket_dir"
    eng = create_app_engine(socket_url)
    try:
        verify_database_connection(eng, timeout_seconds=1.0)
        print("FAILED: Did not raise on nonexistent unix socket!")
    except DatabaseConnectionError as exc:
        print(f"PASSED: Raised DatabaseConnectionError on missing unix socket: {exc}")
    except Exception as exc:
        print(f"FAILED: Raised unexpected exception: {type(exc)}: {exc}")

def test_corrupt_sqlite_file():
    print("--- Test corrupt sqlite file ---")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        f.write(b"GARBAGE_DATA_NOT_A_VALID_SQLITE_HEADER_1234567890")
        corrupt_path = f.name
    
    try:
        eng = create_app_engine(f"sqlite:///{corrupt_path}")
        try:
            verify_database_connection(eng)
            print("FAILED: Did not raise on corrupt SQLite file!")
        except DatabaseConnectionError as exc:
            print(f"PASSED: Raised DatabaseConnectionError on corrupt SQLite file: {exc}")
        except Exception as exc:
            print(f"FAILED: Raised unexpected exception: {type(exc)}: {exc}")
    finally:
        os.unlink(corrupt_path)

def test_directory_as_sqlite_file():
    print("--- Test directory path as sqlite db file ---")
    with tempfile.TemporaryDirectory() as temp_dir:
        eng = create_app_engine(f"sqlite:///{temp_dir}")
        try:
            verify_database_connection(eng)
            print("FAILED: Did not raise when db path is a directory!")
        except DatabaseConnectionError as exc:
            print(f"PASSED: Raised DatabaseConnectionError when db path is directory: {exc}")
        except Exception as exc:
            print(f"FAILED: Raised unexpected exception: {type(exc)}: {exc}")

if __name__ == "__main__":
    test_unreachable_unix_socket()
    test_corrupt_sqlite_file()
    test_directory_as_sqlite_file()

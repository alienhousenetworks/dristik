"""
Test verify_database_connection on bad ports, invalid credentials, unreachable sockets,
and check whether exc leaks secrets.
"""
import sys
import os
from unittest.mock import patch, MagicMock

backend_path = os.path.abspath("/Users/sayantande/Downloads/dristik-main/backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.db.session import (
    create_app_engine,
    verify_database_connection,
    DatabaseConnectionError,
    mask_database_url
)
from sqlalchemy.exc import OperationalError

def test_bad_port():
    print("--- Test bad port (closed port) ---")
    bad_url = "postgresql://myuser:supersecretpass@127.0.0.1:59999/nonexistent"
    engine = create_app_engine(bad_url)
    try:
        verify_database_connection(engine, timeout_seconds=1.0)
        print("FAILED: Did not raise on bad port!")
    except DatabaseConnectionError as exc:
        msg = str(exc)
        print(f"Raised DatabaseConnectionError as expected: {msg[:100]}...")
        if "supersecretpass" in msg:
            print("CRITICAL VULNERABILITY: Password leaked in DatabaseConnectionError message!")
        else:
            print("OK: Password not in exception message.")

def test_unreachable_socket():
    print("--- Test unreachable socket (invalid host) ---")
    bad_url = "postgresql://myuser:secret123@this-domain-does-not-exist-123456789.invalid:5432/db"
    engine = create_app_engine(bad_url)
    try:
        verify_database_connection(engine, timeout_seconds=1.0)
        print("FAILED: Did not raise on non-existent host!")
    except DatabaseConnectionError as exc:
        msg = str(exc)
        print(f"Raised DatabaseConnectionError as expected: {msg[:100]}...")
        if "secret123" in msg:
            print("CRITICAL VULNERABILITY: Password leaked in DatabaseConnectionError message!")
        else:
            print("OK: Password not in exception message.")

def test_invalid_credentials_simulation():
    print("--- Test invalid credentials simulation ---")
    url = "postgresql://validuser:wrongpassword999@localhost:5432/dristik"
    engine = create_app_engine(url)
    
    # Simulate DBAPI OperationalError for invalid credentials
    auth_error = OperationalError(
        "password authentication failed for user 'validuser'",
        params=None,
        orig=Exception('FATAL: password authentication failed for user "validuser"\nDETAIL: Connection matched pg_hba.conf line 86')
    )
    
    with patch.object(engine, "connect", side_effect=auth_error):
        try:
            verify_database_connection(engine)
            print("FAILED: Did not raise on auth error!")
        except DatabaseConnectionError as exc:
            msg = str(exc)
            print(f"Raised DatabaseConnectionError on auth error: {msg[:100]}...")
            if "wrongpassword999" in msg:
                print("CRITICAL VULNERABILITY: Password leaked in auth error message!")
            else:
                print("OK: Password not in auth error message.")

def test_none_engine():
    print("--- Test None engine ---")
    try:
        verify_database_connection(None)
        # Note: if global engine is configured, verify_database_connection defaults to global engine
        print("verify_database_connection(None) used default engine or passed")
    except DatabaseConnectionError as exc:
        print(f"Raised DatabaseConnectionError: {exc}")

if __name__ == "__main__":
    test_bad_port()
    test_unreachable_socket()
    test_invalid_credentials_simulation()
    test_none_engine()

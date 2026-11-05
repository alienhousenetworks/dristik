"""
Exploratory adversarial tests for Milestone M2.
Tests session.py and config.py edge cases, failure modes, and security.
"""
import sys
import os

# Ensure backend is in python path
backend_path = os.path.abspath("/Users/sayantande/Downloads/dristik-main/backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import app.db.session as session_module
from app.db.session import (
    create_app_engine,
    create_db_engine,
    get_db,
    mask_database_url,
    verify_database_connection,
    DatabaseConnectionError,
)
from app.core.config import Settings, settings

def test_mask_database_url_permutations():
    print("--- Testing mask_database_url permutations ---")
    urls = [
        # Standard postgres
        ("postgresql://user:secret123@localhost:5432/mydb", "secret123"),
        ("postgresql+psycopg2://user:p@ssword!@localhost:5432/mydb", "p@ssword!"),
        ("postgresql+asyncpg://admin:Complex%23Pass!@db.internal:5432/prod", "Complex%23Pass!"),
        ("postgresql://user:pass%40word@host:5432/db", "pass%40word"),
        # Empty or no password
        ("postgresql://user@localhost:5432/mydb", None),
        ("postgresql://user:@localhost:5432/mydb", ""),
        ("postgresql://localhost:5432/mydb", None),
        # Sqlite forms
        ("sqlite:///data/dristik.db", None),
        ("sqlite:////var/lib/data/dristik.db", None),
        ("sqlite:///:memory:", None),
        ("sqlite://", None),
        # Malformed URLs or weird characters
        ("postgresql://user:unencoded@pass@host:5432/db", "unencoded@pass"),
        ("invalid://bad-url", None),
        ("postgresql://user:p:a:s:s@host:5432/db", "p:a:s:s"),
        ("http://user:secret@example.com", "secret"),
        ("", None),
    ]
    for url, secret in urls:
        masked = mask_database_url(url)
        print(f"Original: {url!r}\nMasked:   {masked!r}")
        if secret and secret in masked:
            print(f"FAILED TO MASK SECRET: {secret} in {masked}")
        else:
            print("OK")
    print()

if __name__ == "__main__":
    test_mask_database_url_permutations()

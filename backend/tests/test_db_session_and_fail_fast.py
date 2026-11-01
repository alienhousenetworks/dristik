"""Tests for Database Session, Engine creation, and Fail-Fast Connectivity."""
import pytest
from unittest.mock import patch
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import app.db.session as session_module
from app.core.config import Settings
from app.core.exceptions import DatabaseConnectionError
from app.db.session import (
    create_app_engine,
    create_db_engine,
    get_db,
    mask_database_url,
    verify_database_connection,
)


def test_mock_session_completely_removed():
    """Verify MockSession has been deleted from session.py."""
    assert not hasattr(session_module, "MockSession"), (
        "MockSession must be completely eliminated from app.db.session"
    )
    assert getattr(session_module, "MockSession", None) is None


def test_database_url_in_settings_default():
    """Verify DATABASE_URL is defined on Settings."""
    settings = Settings()
    assert hasattr(settings, "DATABASE_URL")
    assert isinstance(settings.DATABASE_URL, str)
    assert len(settings.DATABASE_URL) > 0
    is_valid_scheme = (
        settings.DATABASE_URL.startswith("sqlite")
        or settings.DATABASE_URL.startswith("postgresql")
    )
    assert is_valid_scheme


def test_database_url_env_override(monkeypatch):
    """Verify DATABASE_URL can be overridden via environment variable."""
    test_url = "postgresql://test_user:test_pass@localhost:5432/test_dristik"
    monkeypatch.setenv("DATABASE_URL", test_url)
    custom_settings = Settings()
    assert custom_settings.DATABASE_URL == test_url


def test_database_url_invalid_scheme_raises_error():
    """Verify unsupported database scheme raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Settings(DATABASE_URL="mongodb://localhost:27017/dristik")
    assert "Unsupported database scheme" in str(exc_info.value)


def test_mask_database_url():
    """Verify credentials in database URL are safely masked."""
    url = "postgresql://admin_user:secret_password@db.example.com:5432/db"
    masked = mask_database_url(url)
    assert "secret_password" not in masked
    assert "db.example.com" in masked
    assert "db" in masked


def test_create_db_engine_sqlite_configuration():
    """Verify SQLite engine creation configuration."""
    sqlite_url = "sqlite:///:memory:"
    eng = create_db_engine(sqlite_url)
    assert eng.dialect.name == "sqlite"
    assert eng.pool is not None
    # Verify connectivity
    with eng.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1


def test_create_db_engine_postgres_configuration():
    """Verify PostgreSQL engine creation configuration."""
    pg_url = "postgresql://user:pass@localhost:5432/dristik"
    eng = create_db_engine(pg_url)
    assert eng.dialect.name == "postgresql"
    assert "check_same_thread" not in eng.url.query


def test_verify_database_connection_success():
    """Verify healthy engine passes verification probe."""
    eng = create_db_engine("sqlite:///:memory:")
    # Should not raise
    result = verify_database_connection(eng)
    assert result is True


def test_verify_database_connection_fail_fast_on_unreachable():
    """Verify unreachable engine raises DatabaseConnectionError immediately."""
    bad_url = "postgresql://user:pass@127.0.0.1:59999/nonexistent"
    bad_engine = create_db_engine(bad_url)
    with pytest.raises(DatabaseConnectionError) as exc_info:
        verify_database_connection(bad_engine)
    assert "Database connection failed" in str(exc_info.value)
    # Ensure credentials are masked in error message
    assert "pass@" not in str(exc_info.value)


def test_get_db_session_lifecycle():
    """Verify get_db session generator yields active session and closes it."""
    db_gen = get_db()
    db = next(db_gen)
    assert isinstance(db, Session)
    try:
        # Check active session query
        val = db.execute(text("SELECT 1")).scalar()
        assert val == 1
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


def test_get_db_session_lifecycle_and_rollback():
    """Verify get_db rolls back on route exception and closes cleanly."""
    db_gen = get_db()
    db = next(db_gen)
    assert isinstance(db, Session)

    with patch.object(db, "rollback", wraps=db.rollback) as mock_rollback:
        with patch.object(db, "close", wraps=db.close) as mock_close:
            with pytest.raises(RuntimeError, match="Simulated route error"):
                db_gen.throw(RuntimeError("Simulated route error"))
            assert mock_rollback.called, "rollback() must be called on error"
            assert mock_close.called, "close() must be called in finally"


def test_mask_database_url_with_unencoded_at_in_password():
    """Verify passwords with unencoded '@' do not leak secrets."""
    # Single unencoded @ in password
    url = "postgresql+psycopg2://user:p@ssword!@localhost:5432/mydb"
    masked = mask_database_url(url)
    assert "p@ssword!" not in masked, "Plaintext password must not appear"
    assert "ssword!" not in masked, "Password fragment must not be leaked"
    assert "p@" not in masked or "user:***@" in masked
    assert "user:***@localhost:5432/mydb" in masked
    assert "mydb" in masked

    # Multiple unencoded @ in password
    multi_at_url = "postgresql://admin:p@ss@w0rd@db.example.com:5432/prod"
    masked_multi = mask_database_url(multi_at_url)
    assert "p@ss@w0rd" not in masked_multi, "Multi-@ password must not leak"
    assert "admin:***@db.example.com:5432/prod" in masked_multi

    # Password with @ and query parameters containing @
    query_at_url = "postgresql://user:sec@ret@localhost:5432/db?token=tok@123"
    masked_query = mask_database_url(query_at_url)
    assert "sec@ret" not in masked_query
    assert "user:***@localhost:5432/db" in masked_query


def test_database_url_settings_supports_psycopg3_scheme():
    """Verify Settings accepts standard SQLAlchemy 2.0+ Psycopg 3 URI."""
    url = "postgresql+psycopg://user:pass@localhost:5432/dristik"
    settings = Settings(DATABASE_URL=url)
    assert settings.DATABASE_URL == url
    assert settings.is_sqlite is False
    assert settings.sqlite_db_path is None

    # Verify query parameters support with psycopg 3
    url_with_params = (
        "postgresql+psycopg://user:pass@localhost:5432/dristik?sslmode=require"
    )
    settings_params = Settings(DATABASE_URL=url_with_params)
    assert settings_params.DATABASE_URL == url_with_params
    assert settings_params.is_sqlite is False


def test_create_app_engine_accepts_url_object():
    """Verify create_app_engine accepts an sqlalchemy.engine.URL instance."""
    # Test SQLite URL object
    sqlite_url_obj = make_url("sqlite:///:memory:")
    eng_sqlite = create_app_engine(sqlite_url_obj)
    assert eng_sqlite.dialect.name == "sqlite"
    assert getattr(eng_sqlite.pool, "_pre_ping", False) is True

    # Test SQLite file URL object
    sqlite_file_obj = make_url("sqlite:///data/test_url_obj.db")
    eng_file = create_app_engine(sqlite_file_obj)
    assert eng_file.dialect.name == "sqlite"

    # Test PostgreSQL URL object
    pg_url_obj = make_url("postgresql://user:pass@localhost:5432/dristik")
    eng_pg = create_app_engine(pg_url_obj)
    assert eng_pg.dialect.name == "postgresql"
    assert getattr(eng_pg.pool, "_pre_ping", False) is True


def test_verify_database_connection_detects_corrupt_sqlite_file(tmp_path):
    """Verify health check fails fast on corrupted SQLite database file."""
    corrupt_db = tmp_path / "corrupted_test.db"
    corrupt_db.write_bytes(b"CORRUPT_HEADER_GARBAGE_DATA_1234567890" * 40)

    corrupt_engine = create_app_engine(f"sqlite:///{corrupt_db}")
    with pytest.raises(DatabaseConnectionError) as exc_info:
        verify_database_connection(corrupt_engine)

    assert "Database connection failed" in str(exc_info.value)


def test_create_app_engine_postgres_includes_connect_timeout(monkeypatch):
    """Verify PostgreSQL engine configures connect_timeout in connect_args."""
    pg_url = "postgresql://user:pass@localhost:5432/dristik"

    # Test default connect_timeout is configured
    with patch("app.db.session.create_engine") as mock_create_engine:
        create_app_engine(pg_url)
        mock_create_engine.assert_called_once()
        _, kwargs = mock_create_engine.call_args
        assert "connect_args" in kwargs, (
            "PostgreSQL engine must pass connect_args"
        )
        connect_args = kwargs["connect_args"]
        assert "connect_timeout" in connect_args, (
            "connect_args must specify connect_timeout to prevent hangs"
        )
        assert isinstance(connect_args["connect_timeout"], (int, float))
        assert connect_args["connect_timeout"] > 0

    # Test custom DB_CONNECT_TIMEOUT setting override
    monkeypatch.setattr(
        session_module.settings, "DB_CONNECT_TIMEOUT", 12, raising=False
    )
    with patch("app.db.session.create_engine") as mock_create_engine:
        create_app_engine(pg_url)
        mock_create_engine.assert_called_once()
        _, kwargs = mock_create_engine.call_args
        assert kwargs["connect_args"]["connect_timeout"] == 12

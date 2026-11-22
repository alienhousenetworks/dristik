"""Canonical Database Path & Engine Resolver.

Consolidates legacy split SQLite paths under one unified DATABASE_URL (supporting
PostgreSQL via SQLAlchemy + psycopg in production and a single SQLite file in
zero-config local dev/tests) while preserving explicit db_path overrides for tests.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.engine import Engine

from app.core.config import settings

logger = logging.getLogger(__name__)

_ENGINES: Dict[str, Engine] = {}

LEGACY_SQLITE_FILES = (
    "data/dristik_audits.db",
    "data/dristik_enterprise.db",
    "data/external_authority.db",
    "data/geo_enterprise.db",
    "data/geo_aeo_pipeline.db",
    "data/aeo_analytics_history.db",
    "data/competitor_registry.db",
)


def get_database_url(url_override: Optional[str] = None) -> str:
    return str(url_override or getattr(settings, "DATABASE_URL", None) or "sqlite:///data/dristik.db").strip()


def is_postgres_url(url: Optional[str] = None) -> bool:
    raw = get_database_url(url).lower()
    return raw.startswith("postgresql://") or raw.startswith("postgres://") or raw.startswith("postgresql+")


def sqlite_path_from_url(url: Optional[str] = None) -> Optional[str]:
    raw = get_database_url(url)
    if not raw.lower().startswith("sqlite"):
        return None
    if raw.startswith("sqlite:///:memory:") or raw == "sqlite://":
        return ":memory:"
    if raw.startswith("sqlite:////"):
        return "/" + raw[len("sqlite:////"):]
    if raw.startswith("sqlite:///"):
        return raw[len("sqlite:///"):]
    return None


def resolve_default_sqlite_path(legacy_path: str) -> str:
    """Resolve the default SQLite file path for a store.

    When UNIFIED_DATABASE_ENABLED is True and DATABASE_URL points to a SQLite file,
    all domain stores share that single database file instead of scattering 8 files.
    """
    if getattr(settings, "UNIFIED_DATABASE_ENABLED", True):
        unified = sqlite_path_from_url()
        if unified and unified != ":memory:":
            return unified
        auth_db = getattr(settings, "AUTH_DATABASE_PATH", None)
        if auth_db:
            return auth_db
    return legacy_path


def open_sqlite(path: str, *, timeout: float = 10.0) -> sqlite3.Connection:
    if path != ":memory:":
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def get_unified_engine(url: Optional[str] = None) -> Engine:
    """Return a cached SQLAlchemy Engine for PostgreSQL or SQLite."""
    resolved = get_database_url(url)
    engine = _ENGINES.get(resolved)
    if engine is None:
        from app.db.session import create_app_engine
        engine = create_app_engine(resolved)
        _ENGINES[resolved] = engine
    return engine


def dispose_unified_engines() -> None:
    engines = list(_ENGINES.values())
    _ENGINES.clear()
    for eng in engines:
        try:
            eng.dispose()
        except Exception:
            pass

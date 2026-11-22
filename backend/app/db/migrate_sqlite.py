"""Idempotent SQLite consolidation & PostgreSQL migration utility.

Copies tables and rows from legacy split SQLite files (dristik_audits.db,
dristik_enterprise.db, external_authority.db, geo_enterprise.db, etc.) into the
unified SQLite DB or PostgreSQL DATABASE_URL without overwriting existing rows.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app.db.connection import (
    LEGACY_SQLITE_FILES,
    get_database_url,
    get_unified_engine,
    is_postgres_url,
    open_sqlite,
    sqlite_path_from_url,
)

logger = logging.getLogger(__name__)


def _list_user_tables(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [str(r[0]) for r in rows]


def migrate_legacy_sqlite_dbs(
    target_url: Optional[str] = None,
    legacy_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Copy non-conflicting tables/rows from legacy SQLite DB files into target_url."""
    resolved_url = get_database_url(target_url)
    sources = [p for p in (legacy_paths or list(LEGACY_SQLITE_FILES)) if os.path.exists(p)]
    summary: Dict[str, Any] = {
        "target_url": resolved_url.split("@")[-1] if "@" in resolved_url else resolved_url,
        "target_dialect": "postgresql" if is_postgres_url(resolved_url) else "sqlite",
        "files_processed": [],
        "tables_migrated": {},
        "rows_copied": 0,
    }

    if is_postgres_url(resolved_url):
        engine = get_unified_engine(resolved_url)
        for src_path in sources:
            src = sqlite3.connect(src_path)
            src.row_factory = sqlite3.Row
            try:
                tables = _list_user_tables(src)
                with engine.begin() as pg_conn:
                    for table in tables:
                        rows = src.execute(f'SELECT * FROM "{table}"').fetchall()
                        if not rows:
                            continue
                        cols = list(rows[0].keys())
                        col_sql = ", ".join(f'"{c}"' for c in cols)
                        bind_sql = ", ".join(f":c{i}" for i in range(len(cols)))
                        copied = 0
                        for row in rows:
                            params = {f"c{i}": row[c] for i, c in enumerate(cols)}
                            try:
                                pg_conn.execute(
                                    text(f'INSERT INTO "{table}" ({col_sql}) VALUES ({bind_sql}) ON CONFLICT DO NOTHING'),
                                    params,
                                )
                                copied += 1
                            except Exception as exc:
                                logger.debug("PG row skip on %s: %s", table, exc)
                        summary["tables_migrated"][table] = summary["tables_migrated"].get(table, 0) + copied
                        summary["rows_copied"] += copied
                summary["files_processed"].append(src_path)
            finally:
                src.close()
        return summary

    target_sqlite = sqlite_path_from_url(resolved_url) or "data/dristik.db"
    target_abs = os.path.abspath(target_sqlite)
    dst = open_sqlite(target_sqlite)
    try:
        for src_path in sources:
            if os.path.abspath(src_path) == target_abs:
                continue
            src = sqlite3.connect(src_path)
            src.row_factory = sqlite3.Row
            try:
                for table in _list_user_tables(src):
                    # Ensure target table exists using source DDL if absent
                    ddl_row = src.execute(
                        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                        (table,),
                    ).fetchone()
                    if ddl_row and ddl_row[0]:
                        ddl = str(ddl_row[0]).replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1)
                        try:
                            dst.execute(ddl)
                        except sqlite3.OperationalError:
                            pass
                    dst_cols = {r[1] for r in dst.execute(f'PRAGMA table_info("{table}")').fetchall()}
                    rows = src.execute(f'SELECT * FROM "{table}"').fetchall()
                    if not rows:
                        continue
                    src_cols = [c for c in rows[0].keys() if c in dst_cols]
                    if not src_cols:
                        continue
                    col_sql = ", ".join(f'"{c}"' for c in src_cols)
                    qmarks = ", ".join("?" for _ in src_cols)
                    copied = 0
                    for row in rows:
                        cur = dst.execute(
                            f'INSERT OR IGNORE INTO "{table}" ({col_sql}) VALUES ({qmarks})',
                            tuple(row[c] for c in src_cols),
                        )
                        if cur.rowcount and cur.rowcount > 0:
                            copied += cur.rowcount
                    summary["tables_migrated"][table] = summary["tables_migrated"].get(table, 0) + copied
                    summary["rows_copied"] += copied
                dst.commit()
                summary["files_processed"].append(src_path)
            finally:
                src.close()
    finally:
        dst.close()
    return summary

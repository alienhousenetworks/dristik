"""
Dristik AI Competitor Rejection & Preference Registry
Stores rejected competitor domains per domain/project so they are never re-suggested.
Thread-safe and persistent in SQLite.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from typing import List, Set

DB_PATH = "data/competitor_registry.db"


class CompetitorRejectionStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with self._lock:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rejected_competitors (
                        target_domain TEXT NOT NULL,
                        rejected_domain TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (target_domain, rejected_domain)
                    )
                """)
                conn.commit()

    def record_rejection(self, target_domain: str, rejected_domain: str) -> None:
        t_clean = (target_domain or "").lower().strip()
        r_clean = (rejected_domain or "").lower().strip()
        if not t_clean or not r_clean:
            return
        with self._lock:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO rejected_competitors (target_domain, rejected_domain) VALUES (?, ?)",
                    (t_clean, r_clean)
                )
                conn.commit()

    def get_rejected_domains(self, target_domain: str) -> List[str]:
        t_clean = (target_domain or "").lower().strip()
        if not t_clean:
            return []
        with self._lock:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                cur = conn.execute(
                    "SELECT rejected_domain FROM rejected_competitors WHERE target_domain = ?",
                    (t_clean,)
                )
                rows = cur.fetchall()
                return [r[0] for r in rows]


rejection_store = CompetitorRejectionStore()

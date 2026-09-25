"""SQLite persistence for outcome jobs, records, and benchmark calibration."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import settings
from app.intelligence.outcomes.tracking import OutcomeRecord, OutcomeRunResult, summarize_benchmark

SCHEMA = """
CREATE TABLE IF NOT EXISTS outcome_jobs (
    job_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    org_id TEXT,
    website_url TEXT,
    horizon_days INTEGER NOT NULL,
    due_at REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    run_id TEXT,
    created_at REAL NOT NULL,
    run_at REAL
);
CREATE INDEX IF NOT EXISTS idx_outcome_jobs_due ON outcome_jobs(status, due_at);

CREATE TABLE IF NOT EXISTS outcome_records (
    record_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    job_id TEXT,
    analysis_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    finding_type TEXT NOT NULL,
    predicted_impact TEXT NOT NULL,
    remediated INTEGER NOT NULL,
    evidence_condition_resolved INTEGER NOT NULL,
    condition_key TEXT,
    condition_detail TEXT,
    external_metric_delta TEXT NOT NULL,
    attribution_confidence TEXT NOT NULL,
    confounds TEXT NOT NULL,
    observed_outcome TEXT NOT NULL,
    horizon_days INTEGER NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outcome_records_type ON outcome_records(finding_type, predicted_impact);
CREATE INDEX IF NOT EXISTS idx_outcome_records_analysis ON outcome_records(analysis_id);
"""


class OutcomeStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or settings.AUTH_DATABASE_PATH
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def _query(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def schedule(
        self,
        analysis_id: str,
        website_url: str,
        org_id: Optional[str] = None,
        horizons: Optional[List[int]] = None,
        now: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        now = now or datetime.now(timezone.utc)
        jobs = []
        for days in horizons or [30, 60, 90]:
            job_id = f"oj_{uuid4().hex[:12]}"
            due = now + timedelta(days=days)
            self._execute(
                """INSERT INTO outcome_jobs
                   (job_id, analysis_id, org_id, website_url, horizon_days, due_at, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'scheduled', ?)""",
                (job_id, analysis_id, org_id, website_url, days, due.timestamp(), time.time()),
            )
            jobs.append({
                "job_id": job_id,
                "analysis_id": analysis_id,
                "horizon_days": days,
                "due_at": due.isoformat(),
                "status": "scheduled",
            })
        return jobs

    def due_jobs(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        ts = (now or datetime.now(timezone.utc)).timestamp()
        rows = self._query(
            "SELECT * FROM outcome_jobs WHERE status='scheduled' AND due_at <= ? ORDER BY due_at",
            (ts,),
        )
        return [dict(r) for r in rows]

    def list_jobs(self, analysis_id: str) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._query(
            "SELECT * FROM outcome_jobs WHERE analysis_id=? ORDER BY horizon_days",
            (analysis_id,),
        )]

    def save_run(self, result: OutcomeRunResult, job_id: Optional[str] = None) -> None:
        now = time.time()
        if job_id:
            self._execute(
                "UPDATE outcome_jobs SET status='completed', run_id=?, run_at=? WHERE job_id=?",
                (result.run_id, now, job_id),
            )
        for rec in result.records:
            self._execute(
                """INSERT INTO outcome_records (
                    record_id, run_id, job_id, analysis_id, finding_id, finding_type,
                    predicted_impact, remediated, evidence_condition_resolved, condition_key,
                    condition_detail, external_metric_delta, attribution_confidence, confounds,
                    observed_outcome, horizon_days, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"or_{uuid4().hex[:12]}",
                    result.run_id,
                    job_id,
                    result.analysis_id,
                    rec.finding_id,
                    rec.finding_type,
                    rec.predicted_impact,
                    1 if rec.remediated else 0,
                    1 if rec.evidence_condition_resolved else 0,
                    rec.condition_key,
                    rec.condition_detail,
                    json.dumps(rec.external_metric_delta),
                    rec.confidence_this_delta_is_attributable_to_the_fix,
                    json.dumps(rec.confounds),
                    rec.observed_outcome,
                    rec.horizon_days,
                    now,
                ),
            )

    def records_for_analysis(self, analysis_id: str) -> List[Dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM outcome_records WHERE analysis_id=? ORDER BY created_at",
            (analysis_id,),
        )
        out = []
        for r in rows:
            item = dict(r)
            item["external_metric_delta"] = json.loads(item["external_metric_delta"] or "{}")
            item["confounds"] = json.loads(item["confounds"] or "[]")
            item["remediated"] = bool(item["remediated"])
            item["evidence_condition_resolved"] = bool(item["evidence_condition_resolved"])
            out.append(item)
        return out

    def benchmark(self) -> List[Dict[str, Any]]:
        rows = self._query("SELECT * FROM outcome_records")
        records = []
        for r in rows:
            records.append(OutcomeRecord(
                finding_id=r["finding_id"],
                finding_type=r["finding_type"],
                predicted_impact=r["predicted_impact"],
                remediated=bool(r["remediated"]),
                evidence_condition_resolved=bool(r["evidence_condition_resolved"]),
                condition_key=r["condition_key"],
                condition_detail=r["condition_detail"] or "",
                external_metric_delta=json.loads(r["external_metric_delta"] or "{}"),
                confidence_this_delta_is_attributable_to_the_fix=r["attribution_confidence"],
                confounds=json.loads(r["confounds"] or "[]"),
                observed_outcome=r["observed_outcome"],
                horizon_days=r["horizon_days"],
            ))
        return summarize_benchmark(records)


_store: Optional[OutcomeStore] = None


def get_outcome_store() -> OutcomeStore:
    global _store
    if _store is None:
        _store = OutcomeStore()
    return _store

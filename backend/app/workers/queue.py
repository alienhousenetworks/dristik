"""Enterprise Durable Background Job Queue.

Persists background jobs to the canonical database (SQLite or PostgreSQL via
DATABASE_URL) with atomic lease claiming, retries, crash recovery on startup,
and optional Redis dispatch notifications when REDIS_URL is configured.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Coroutine, Dict, List, Optional

from sqlalchemy import text

from app.core.config import settings
from app.db.connection import get_unified_engine, is_postgres_url, open_sqlite, resolve_default_sqlite_path

logger = logging.getLogger("dristik.workers.queue")

JobHandler = Callable[[Dict[str, Any]], Awaitable[Any]]

_JOBS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS background_jobs (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    org_id TEXT NOT NULL DEFAULT '',
    analysis_id TEXT,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    lease_owner TEXT,
    lease_expires_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_bg_jobs_status ON background_jobs(status, lease_expires_at);
CREATE INDEX IF NOT EXISTS idx_bg_jobs_analysis ON background_jobs(analysis_id);
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class DurableJobQueue:
    """Crash-recoverable durable job queue backed by SQLite/PostgreSQL + optional Redis."""

    def __init__(
        self,
        *,
        db_path: Optional[str] = None,
        database_url: Optional[str] = None,
        redis_url: Optional[str] = None,
        lease_seconds: int = 300,
        poll_interval: float = 0.5,
    ):
        self.database_url = database_url
        self._use_postgres = bool(database_url and is_postgres_url(database_url)) or (
            database_url is None and db_path is None and is_postgres_url()
        )
        self.db_path = db_path or resolve_default_sqlite_path("data/dristik_audits.db")
        self.redis_url = redis_url if redis_url is not None else getattr(settings, "REDIS_URL", None)
        self.lease_seconds = max(10, int(lease_seconds))
        self.poll_interval = max(0.05, float(poll_interval))
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
        self._lock = threading.RLock()
        self._handlers: Dict[str, JobHandler] = {}
        self._tasks: set[asyncio.Task] = set()
        self._worker_task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._redis_client: Any = None
        self._init_schema()

    def _get_redis(self) -> Any:
        if not self.redis_url:
            return None
        if self._redis_client is None:
            try:
                import redis
                self._redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True, socket_timeout=2.0)
            except Exception as exc:
                logger.warning("Redis unavailable (%s); continuing with DB durable queue.", exc)
                self._redis_client = False
        return self._redis_client if self._redis_client is not False else None

    def _init_schema(self) -> None:
        with self._lock:
            if self._use_postgres:
                eng = get_unified_engine(self.database_url)
                with eng.begin() as conn:
                    for stmt in _JOBS_TABLE_SQL.strip().split(";"):
                        s = stmt.strip()
                        if s:
                            conn.execute(text(s))
            else:
                with open_sqlite(self.db_path) as conn:
                    conn.executescript(_JOBS_TABLE_SQL)
                    conn.commit()

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        self._handlers[job_type] = handler

    # Backward-compatible fire-and-forget helper (fixes unbounded task list leak)
    def enqueue(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def enqueue_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        *,
        org_id: str = "",
        analysis_id: Optional[str] = None,
        max_attempts: int = 3,
    ) -> str:
        """Persist a durable job row (and notify Redis if configured)."""
        job_id = f"job_{uuid.uuid4().hex[:14]}"
        now_iso = _iso(_utcnow())
        params = {
            "job_id": job_id,
            "job_type": job_type,
            "org_id": org_id or "",
            "analysis_id": analysis_id,
            "payload_json": json.dumps(payload, default=str),
            "status": "queued",
            "attempts": 0,
            "max_attempts": max(1, int(max_attempts)),
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        sql = """
            INSERT INTO background_jobs (
                job_id, job_type, org_id, analysis_id, payload_json,
                status, attempts, max_attempts, created_at, updated_at
            ) VALUES (
                :job_id, :job_type, :org_id, :analysis_id, :payload_json,
                :status, :attempts, :max_attempts, :created_at, :updated_at
            )
        """
        with self._lock:
            if self._use_postgres:
                with get_unified_engine(self.database_url).begin() as conn:
                    conn.execute(text(sql), params)
            else:
                with open_sqlite(self.db_path) as conn:
                    conn.execute(sql, params)
                    conn.commit()

        rc = self._get_redis()
        if rc is not None:
            try:
                rc.rpush("dristik:jobs:queue", job_id)
            except Exception as exc:
                logger.debug("Redis push failed for %s: %s", job_id, exc)
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM background_jobs WHERE job_id = :job_id"
        with self._lock:
            if self._use_postgres:
                with get_unified_engine(self.database_url).connect() as conn:
                    row = conn.execute(text(sql), {"job_id": job_id}).mappings().first()
                    return dict(row) if row else None
            with open_sqlite(self.db_path) as conn:
                row = conn.execute(sql, {"job_id": job_id}).fetchone()
                return dict(row) if row else None

    def requeue_expired_leases(self, *, now: Optional[datetime] = None) -> Dict[str, int]:
        """Recover jobs stranded in 'running' after a crash or expired lease."""
        ref = now or _utcnow()
        now_iso = _iso(ref)
        requeued = 0
        failed = 0
        with self._lock:
            select_sql = (
                "SELECT job_id, attempts, max_attempts, analysis_id FROM background_jobs "
                "WHERE status = 'running' AND lease_expires_at IS NOT NULL AND lease_expires_at <= :now"
            )
            if self._use_postgres:
                with get_unified_engine(self.database_url).begin() as conn:
                    stale = list(conn.execute(text(select_sql), {"now": now_iso}).mappings().all())
                    for row in stale:
                        if int(row["attempts"]) < int(row["max_attempts"]):
                            conn.execute(
                                text(
                                    "UPDATE background_jobs SET status='queued', lease_owner=NULL, "
                                    "lease_expires_at=NULL, last_error='lease_expired_requeued', updated_at=:now "
                                    "WHERE job_id=:jid"
                                ),
                                {"now": now_iso, "jid": row["job_id"]},
                            )
                            requeued += 1
                        else:
                            conn.execute(
                                text(
                                    "UPDATE background_jobs SET status='failed', lease_owner=NULL, "
                                    "lease_expires_at=NULL, last_error='lease_expired_max_attempts', "
                                    "completed_at=:now, updated_at=:now WHERE job_id=:jid"
                                ),
                                {"now": now_iso, "jid": row["job_id"]},
                            )
                            failed += 1
            else:
                with open_sqlite(self.db_path) as conn:
                    stale = conn.execute(select_sql, {"now": now_iso}).fetchall()
                    for row in stale:
                        if int(row["attempts"]) < int(row["max_attempts"]):
                            conn.execute(
                                "UPDATE background_jobs SET status='queued', lease_owner=NULL, "
                                "lease_expires_at=NULL, last_error='lease_expired_requeued', updated_at=? "
                                "WHERE job_id=?",
                                (now_iso, row["job_id"]),
                            )
                            requeued += 1
                        else:
                            conn.execute(
                                "UPDATE background_jobs SET status='failed', lease_owner=NULL, "
                                "lease_expires_at=NULL, last_error='lease_expired_max_attempts', "
                                "completed_at=?, updated_at=? WHERE job_id=?",
                                (now_iso, now_iso, row["job_id"]),
                            )
                            failed += 1
                    conn.commit()
        if requeued or failed:
            logger.warning("DurableJobQueue startup recovery: requeued=%d, failed=%d", requeued, failed)
        return {"requeued": requeued, "failed": failed}

    def claim_next_job(self) -> Optional[Dict[str, Any]]:
        """Atomically claim the oldest queued job with a lease."""
        now = _utcnow()
        now_iso = _iso(now)
        lease_until = _iso(now + timedelta(seconds=self.lease_seconds))
        with self._lock:
            if self._use_postgres:
                with get_unified_engine(self.database_url).begin() as conn:
                    row = conn.execute(
                        text(
                            "SELECT * FROM background_jobs WHERE status = 'queued' "
                            "ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED"
                        )
                    ).mappings().first()
                    if not row:
                        return None
                    conn.execute(
                        text(
                            "UPDATE background_jobs SET status='running', attempts=attempts+1, "
                            "lease_owner=:owner, lease_expires_at=:exp, started_at=COALESCE(started_at, :now), "
                            "updated_at=:now WHERE job_id=:jid"
                        ),
                        {"owner": self.worker_id, "exp": lease_until, "now": now_iso, "jid": row["job_id"]},
                    )
                    claimed = dict(row)
                    claimed["status"] = "running"
                    claimed["attempts"] = int(claimed["attempts"]) + 1
                    claimed["lease_owner"] = self.worker_id
                    claimed["lease_expires_at"] = lease_until
                    return claimed
            else:
                with open_sqlite(self.db_path) as conn:
                    row = conn.execute(
                        "SELECT * FROM background_jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1"
                    ).fetchone()
                    if not row:
                        return None
                    cur = conn.execute(
                        "UPDATE background_jobs SET status='running', attempts=attempts+1, "
                        "lease_owner=?, lease_expires_at=?, started_at=COALESCE(started_at, ?), updated_at=? "
                        "WHERE job_id=? AND status='queued'",
                        (self.worker_id, lease_until, now_iso, now_iso, row["job_id"]),
                    )
                    conn.commit()
                    if cur.rowcount != 1:
                        return None
                    claimed = dict(row)
                    claimed["status"] = "running"
                    claimed["attempts"] = int(claimed["attempts"]) + 1
                    claimed["lease_owner"] = self.worker_id
                    claimed["lease_expires_at"] = lease_until
                    return claimed

    def _finish_job(self, job_id: str, *, ok: bool, error: Optional[str] = None, requeue: bool = False) -> None:
        now_iso = _iso(_utcnow())
        status = "completed" if ok else ("queued" if requeue else "failed")
        completed_at = None if requeue else now_iso
        sql = (
            "UPDATE background_jobs SET status=:status, lease_owner=NULL, lease_expires_at=NULL, "
            "last_error=:err, completed_at=:done, updated_at=:now WHERE job_id=:jid"
        )
        params = {"status": status, "err": error, "done": completed_at, "now": now_iso, "jid": job_id}
        with self._lock:
            if self._use_postgres:
                with get_unified_engine(self.database_url).begin() as conn:
                    conn.execute(text(sql), params)
            else:
                with open_sqlite(self.db_path) as conn:
                    conn.execute(sql, params)
                    conn.commit()

    async def process_one(self) -> Optional[Dict[str, Any]]:
        """Claim and execute a single queued job."""
        job = self.claim_next_job()
        if not job:
            return None
        job_id = job["job_id"]
        job_type = job["job_type"]
        handler = self._handlers.get(job_type)
        if handler is None:
            self._finish_job(job_id, ok=False, error=f"No handler registered for job_type '{job_type}'")
            return {"job_id": job_id, "status": "failed", "error": "unregistered_handler"}
        try:
            payload = json.loads(job.get("payload_json") or "{}")
            await handler(payload)
            self._finish_job(job_id, ok=True)
            return {"job_id": job_id, "status": "completed"}
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            can_retry = int(job["attempts"]) < int(job["max_attempts"])
            logger.warning(
                "DurableJobQueue job %s (%s) failed on attempt %d/%d: %s",
                job_id, job_type, job["attempts"], job["max_attempts"], err_msg,
            )
            self._finish_job(job_id, ok=False, error=err_msg[:500], requeue=can_retry)
            return {"job_id": job_id, "status": "queued" if can_retry else "failed", "error": err_msg}

    @property
    def is_running(self) -> bool:
        return self._worker_task is not None and not self._worker_task.done()

    async def start(self) -> None:
        if self.is_running:
            return
        self.requeue_expired_leases()
        self._stop_event = asyncio.Event()

        async def _loop() -> None:
            assert self._stop_event is not None
            while not self._stop_event.is_set():
                try:
                    processed = await self.process_one()
                    if processed is None:
                        try:
                            await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
                        except asyncio.TimeoutError:
                            pass
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.warning("DurableJobQueue worker loop error: %s", exc)
                    await asyncio.sleep(self.poll_interval)

        self._worker_task = asyncio.create_task(_loop())
        logger.info("DurableJobQueue worker started (id=%s, postgres=%s)", self.worker_id, self._use_postgres)

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        for t in list(self._tasks):
            t.cancel()
        self._tasks.clear()


TaskQueue = DurableJobQueue
task_queue = DurableJobQueue()

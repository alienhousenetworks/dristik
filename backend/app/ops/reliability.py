"""
Enterprise Operations & Reliability Layer:
- API availability, error-rate, and p50/p95/p99 latency collector (Prometheus + JSON).
- Persistent background job retry with exponential backoff and Dead-Letter Queue (DLQ).
- Unified Connector Health Dashboard across all external providers (Zero-Fake status).
"""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from app.core.config import settings
from app.db.enterprise_intelligence_schema import connect_enterprise_db
from app.governance.data_reliability import DataReliabilityGovernance, utc_now_iso
from app.security.privacy_governance import require_rbac_permission


class LatencyMetricsCollector:
    """In-process API availability & latency metrics (Prometheus-compatible)."""

    def __init__(self, max_samples_per_route: int = 1000):
        self._max_samples = max_samples_per_route
        self._samples: Dict[str, List[float]] = {}
        self._counts: Dict[str, int] = {}
        self._errors: Dict[str, int] = {}

    def record(self, route: str, duration_ms: float, status_code: int) -> None:
        self._counts[route] = self._counts.get(route, 0) + 1
        if status_code >= 500:
            self._errors[route] = self._errors.get(route, 0) + 1
        bucket = self._samples.setdefault(route, [])
        bucket.append(round(float(duration_ms), 2))
        if len(bucket) > self._max_samples:
            del bucket[: len(bucket) - self._max_samples]

    @staticmethod
    def _percentile(sorted_vals: List[float], p: float) -> float:
        if not sorted_vals:
            return 0.0
        idx = min(len(sorted_vals) - 1, max(0, math.ceil((p / 100.0) * len(sorted_vals)) - 1))
        return round(sorted_vals[idx], 2)

    def snapshot(self) -> Dict[str, Any]:
        routes: Dict[str, Any] = {}
        total_req = sum(self._counts.values())
        total_err = sum(self._errors.values())
        for route, cnt in self._counts.items():
            vals = sorted(self._samples.get(route, []))
            err = self._errors.get(route, 0)
            routes[route] = {
                "requests": cnt,
                "errors_5xx": err,
                "availability_pct": round(((cnt - err) / cnt) * 100.0, 3) if cnt > 0 else 100.0,
                "p50_ms": self._percentile(vals, 50),
                "p95_ms": self._percentile(vals, 95),
                "p99_ms": self._percentile(vals, 99),
            }
        return {
            "total_requests": total_req,
            "total_errors_5xx": total_err,
            "overall_availability_pct": round(((total_req - total_err) / total_req) * 100.0, 3) if total_req > 0 else 100.0,
            "routes": routes,
        }

    def to_prometheus_text(self) -> str:
        snap = self.snapshot()
        lines = [
            "# HELP dristik_http_requests_total Total HTTP requests by route",
            "# TYPE dristik_http_requests_total counter",
        ]
        for route, m in snap["routes"].items():
            safe_r = route.replace('"', "")
            lines.append(f'dristik_http_requests_total{{route="{safe_r}"}} {m["requests"]}')
            lines.append(f'dristik_http_errors_5xx_total{{route="{safe_r}"}} {m["errors_5xx"]}')
            lines.append(f'dristik_http_latency_p95_ms{{route="{safe_r}"}} {m["p95_ms"]}')
        return "\n".join(lines) + "\n"


metrics_collector = LatencyMetricsCollector()


class DeadLetterQueueManager:
    """Durable background job queue with retry/backoff and Dead-Letter Queue (DLQ) replay."""

    @classmethod
    def enqueue(
        cls,
        *,
        org_id: str,
        job_type: str,
        payload: Dict[str, Any],
        max_attempts: int = 3,
        db_path: Optional[str] = None,
    ) -> str:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        conn = connect_enterprise_db(db_path)
        try:
            conn.execute(
                """
                INSERT INTO background_jobs (
                    job_id, org_id, job_type, payload_json, status, attempts, max_attempts,
                    next_retry_at_utc, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, 'QUEUED', 0, ?, ?, ?, ?)
                """,
                (job_id, org_id, job_type, json.dumps(payload, default=str), max_attempts, now, now, now),
            )
            conn.commit()
            return job_id
        finally:
            conn.close()

    @classmethod
    def process_job(
        cls,
        *,
        job_id: str,
        handler: Callable[[Dict[str, Any]], Any],
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        conn = connect_enterprise_db(db_path)
        try:
            row = conn.execute("SELECT * FROM background_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not row:
                raise KeyError(f"Job '{job_id}' not found.")
            payload = json.loads(row["payload_json"])
            attempts = int(row["attempts"]) + 1
            max_attempts = int(row["max_attempts"])
            try:
                result = handler(payload)
                conn.execute(
                    "UPDATE background_jobs SET status = 'COMPLETED', attempts = ?, updated_at_utc = ? WHERE job_id = ?",
                    (attempts, now, job_id),
                )
                conn.commit()
                return {"job_id": job_id, "status": "COMPLETED", "attempts": attempts, "result": result}
            except Exception as exc:
                err_msg = str(exc)
                if attempts >= max_attempts:
                    dlq_id = f"dlq_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        "UPDATE background_jobs SET status = 'DEAD_LETTERED', attempts = ?, last_error = ?, updated_at_utc = ? WHERE job_id = ?",
                        (attempts, err_msg, now, job_id),
                    )
                    conn.execute(
                        """
                        INSERT INTO dead_letter_jobs (
                            dlq_id, original_job_id, org_id, job_type, payload_json,
                            failure_reason, attempts, quarantined_at_utc
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (dlq_id, job_id, row["org_id"], row["job_type"], row["payload_json"], err_msg, attempts, now),
                    )
                    conn.commit()
                    return {"job_id": job_id, "status": "DEAD_LETTERED", "dlq_id": dlq_id, "attempts": attempts, "error": err_msg}
                backoff_sec = 2 ** attempts
                next_retry = (now_dt + timedelta(seconds=backoff_sec)).isoformat()
                conn.execute(
                    "UPDATE background_jobs SET status = 'RETRY_SCHEDULED', attempts = ?, next_retry_at_utc = ?, last_error = ?, updated_at_utc = ? WHERE job_id = ?",
                    (attempts, next_retry, err_msg, now, job_id),
                )
                conn.commit()
                return {"job_id": job_id, "status": "RETRY_SCHEDULED", "attempts": attempts, "next_retry_at_utc": next_retry, "error": err_msg}
        finally:
            conn.close()

    @classmethod
    def replay_dlq_job(
        cls,
        *,
        org_id: str,
        dlq_id: str,
        actor_role: str,
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        require_rbac_permission(actor_role, "ops:dlq_replay")
        now = utc_now_iso()
        conn = connect_enterprise_db(db_path)
        try:
            dlq = conn.execute("SELECT * FROM dead_letter_jobs WHERE org_id = ? AND dlq_id = ?", (org_id, dlq_id)).fetchone()
            if not dlq:
                raise KeyError(f"DLQ item '{dlq_id}' not found for org '{org_id}'.")
            new_job_id = f"job_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO background_jobs (
                    job_id, org_id, job_type, payload_json, status, attempts, max_attempts,
                    next_retry_at_utc, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, 'QUEUED', 0, 3, ?, ?, ?)
                """,
                (new_job_id, org_id, dlq["job_type"], dlq["payload_json"], now, now, now),
            )
            conn.execute("UPDATE dead_letter_jobs SET replayed_at_utc = ? WHERE dlq_id = ?", (now, dlq_id))
            conn.commit()
            return {"dlq_id": dlq_id, "replayed_job_id": new_job_id, "status": "REPLAYED"}
        finally:
            conn.close()


def get_connector_health_dashboard(org_id: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Reports real .env configuration status & recent sync freshness across all enterprise connectors."""
    providers = [
        ("google_search_console", bool(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or getattr(settings, "GSC_SITE_URL", None)), ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "GSC_SITE_URL"]),
        ("google_analytics_4", bool(getattr(settings, "GA4_PROPERTY_ID", None)), ["GA4_PROPERTY_ID", "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"]),
        ("dataforseo", bool(getattr(settings, "DATAFORSEO_LOGIN", None) and getattr(settings, "DATAFORSEO_PASSWORD", None)), ["DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"]),
        ("ahrefs", bool(getattr(settings, "AHREFS_API_KEY", None)), ["AHREFS_API_KEY"]),
        ("semrush", bool(getattr(settings, "SEMRUSH_API_KEY", None)), ["SEMRUSH_API_KEY"]),
        ("openai", bool(getattr(settings, "OPENAI_API_KEY", None)), ["OPENAI_API_KEY"]),
        ("perplexity", bool(getattr(settings, "PERPLEXITY_API_KEY", None)), ["PERPLEXITY_API_KEY"]),
        ("gemini", bool(getattr(settings, "GEMINI_API_KEY", None) or getattr(settings, "GOOGLE_API_KEY", None)), ["GEMINI_API_KEY"]),
        ("anthropic", bool(getattr(settings, "ANTHROPIC_API_KEY", None)), ["ANTHROPIC_API_KEY"]),
        ("posthog", bool(getattr(settings, "POSTHOG_API_KEY", None) and getattr(settings, "POSTHOG_PROJECT_ID", None)), ["POSTHOG_API_KEY", "POSTHOG_PROJECT_ID"]),
        ("microsoft_clarity", bool(getattr(settings, "CLARITY_API_TOKEN", None) and getattr(settings, "CLARITY_PROJECT_ID", None)), ["CLARITY_API_TOKEN", "CLARITY_PROJECT_ID"]),
        ("growthbook", bool(getattr(settings, "GROWTHBOOK_API_KEY", None)), ["GROWTHBOOK_API_KEY"]),
        ("shopify", bool(getattr(settings, "SHOPIFY_STORE_DOMAIN", None) and getattr(settings, "SHOPIFY_ACCESS_TOKEN", None)), ["SHOPIFY_STORE_DOMAIN", "SHOPIFY_ACCESS_TOKEN", "SHOPIFY_WEBHOOK_SECRET"]),
        ("woocommerce", bool(getattr(settings, "WOOCOMMERCE_URL", None) and getattr(settings, "WOOCOMMERCE_CONSUMER_KEY", None)), ["WOOCOMMERCE_URL", "WOOCOMMERCE_CONSUMER_KEY", "WOOCOMMERCE_CONSUMER_SECRET"]),
        ("hubspot", bool(getattr(settings, "HUBSPOT_API_KEY", None)), ["HUBSPOT_API_KEY"]),
        ("stripe", bool(getattr(settings, "STRIPE_API_KEY", None)), ["STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET"]),
    ]

    conn = connect_enterprise_db(db_path)
    try:
        rows = conn.execute(
            """
            SELECT provider, status, completed_at_utc, partial_errors_json
            FROM connector_sync_runs
            WHERE org_id = ?
            ORDER BY started_at_utc DESC
            """,
            (org_id,),
        ).fetchall()
    finally:
        conn.close()

    latest_sync: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        if r["provider"] not in latest_sync:
            latest_sync[r["provider"]] = dict(r)

    connectors = []
    sla_hours = int(getattr(settings, "DATA_FRESHNESS_SLA_HOURS", 24))
    for pid, configured, env_vars in providers:
        sync = latest_sync.get(pid)
        freshness = (
            DataReliabilityGovernance.check_freshness(sync["completed_at_utc"], sla_hours=sla_hours).status
            if sync and sync.get("completed_at_utc")
            else "NEVER_SYNCED"
        )
        connectors.append({
            "provider": pid,
            "configured_in_env": configured,
            "status": (sync["status"] if sync else ("CONFIGURED_AWAITING_SYNC" if configured else "NOT_CONNECTED")),
            "freshness_status": freshness,
            "last_sync_utc": sync.get("completed_at_utc") if sync else None,
            "required_env_vars": env_vars,
        })

    return {
        "org_id": org_id,
        "total_connectors": len(connectors),
        "configured_count": sum(1 for c in connectors if c["configured_in_env"]),
        "connectors": connectors,
    }

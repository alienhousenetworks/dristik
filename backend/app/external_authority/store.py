"""SQLite persistence for external authority. Tokens stay encrypted."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from cryptography.fernet import InvalidToken

from app.external_authority.crypto import decrypt_json, encrypt_json
from app.external_authority.models import ExternalRecord, isoformat, stable_id, utcnow
from app.external_authority.redact import strip_secrets

_SCHEMA = Path(__file__).resolve().parent / "migrations" / "001_external_authority.sql"


def default_db_path() -> str:
    from app.core.config import settings
    return settings.EXTERNAL_AUTHORITY_DB_PATH


class ExternalStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or default_db_path()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_schema(self) -> None:
        migrations_dir = Path(__file__).resolve().parent / "migrations"
        migration_files = sorted(migrations_dir.glob("*.sql"))
        with self._lock, self._connect() as conn:
            for m_file in migration_files:
                version_str = m_file.stem.split("_")[0]
                try:
                    version = int(version_str)
                except ValueError:
                    version = 1
                script = m_file.read_text(encoding="utf-8")
                conn.executescript(script)
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (version, isoformat(utcnow())),
                )

    def upsert_connection(self, row: Dict[str, Any], secret: Optional[Dict[str, Any]] = None) -> str:
        now = isoformat(utcnow())
        connection_id = row.get("connection_id") or stable_id(
            "con_", row["project_id"], row["provider"]
        )
        ciphertext = encrypt_json(secret) if secret is not None else row.get("token_ciphertext")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO external_connections (
                    connection_id, project_id, provider, status, auth_mode, account_label,
                    external_account_id, property_id, property_label, domain, scopes_json,
                    token_ciphertext, token_status, token_expires_at, capabilities_json,
                    collection_tier, credential_source, last_success_at, last_attempt_at,
                    next_sync_at, last_error, quota_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, provider) DO UPDATE SET
                    status=excluded.status,
                    auth_mode=excluded.auth_mode,
                    account_label=COALESCE(excluded.account_label, external_connections.account_label),
                    external_account_id=COALESCE(excluded.external_account_id, external_connections.external_account_id),
                    property_id=COALESCE(excluded.property_id, external_connections.property_id),
                    property_label=COALESCE(excluded.property_label, external_connections.property_label),
                    domain=COALESCE(excluded.domain, external_connections.domain),
                    scopes_json=COALESCE(excluded.scopes_json, external_connections.scopes_json),
                    token_ciphertext=COALESCE(excluded.token_ciphertext, external_connections.token_ciphertext),
                    token_status=excluded.token_status,
                    token_expires_at=COALESCE(excluded.token_expires_at, external_connections.token_expires_at),
                    capabilities_json=excluded.capabilities_json,
                    collection_tier=excluded.collection_tier,
                    credential_source=excluded.credential_source,
                    last_error=excluded.last_error,
                    quota_status=COALESCE(excluded.quota_status, external_connections.quota_status),
                    updated_at=excluded.updated_at
                """,
                (
                    connection_id,
                    row["project_id"],
                    row["provider"],
                    row.get("status", "CONNECTED"),
                    row.get("auth_mode", "oauth"),
                    row.get("account_label"),
                    row.get("external_account_id"),
                    row.get("property_id"),
                    row.get("property_label"),
                    row.get("domain"),
                    json.dumps(row.get("scopes") or []),
                    ciphertext,
                    row.get("token_status", "valid" if secret else "missing"),
                    row.get("token_expires_at"),
                    json.dumps(row.get("capabilities") or {}),
                    row.get("collection_tier"),
                    row.get("credential_source", "account"),
                    row.get("last_success_at"),
                    row.get("last_attempt_at"),
                    row.get("next_sync_at"),
                    row.get("last_error"),
                    row.get("quota_status"),
                    now,
                    now,
                ),
            )
        return self.connection_id(row["project_id"], row["provider"]) or connection_id

    def connection_id(self, project_id: str, provider: str) -> Optional[str]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT connection_id FROM external_connections WHERE project_id=? AND provider=?",
                (project_id, provider),
            ).fetchone()
        return row["connection_id"] if row else None

    def public_connections(self, project_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT connection_id, project_id, provider, status, auth_mode, account_label,
                       external_account_id, property_id, property_label, domain, scopes_json,
                       token_status, token_expires_at, capabilities_json, collection_tier,
                       credential_source, last_success_at, last_attempt_at, next_sync_at,
                       last_error, quota_status, created_at, updated_at
                FROM external_connections WHERE project_id=?
                """,
                (project_id,),
            ).fetchall()
        return [_public_connection(row) for row in rows]

    def get_public_connection(self, project_id: str, provider: str) -> Optional[Dict[str, Any]]:
        for row in self.public_connections(project_id):
            if row["provider"] == provider:
                return row
        return None

    def load_secret(self, project_id: str, provider: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT token_ciphertext, status FROM external_connections WHERE project_id=? AND provider=?",
                (project_id, provider),
            ).fetchone()
        if not row or not row["token_ciphertext"] or row["status"] in {"DISCONNECTED", "REVOKED"}:
            return None
        try:
            return decrypt_json(row["token_ciphertext"])
        except (InvalidToken, ValueError):
            self.mark_connection(project_id, provider, token_status="unreadable", last_error="stored credential could not be decrypted")
            return None

    def mark_connection(self, project_id: str, provider: str, **fields: Any) -> None:
        allowed = {
            "status", "token_status", "token_expires_at", "last_success_at", "last_attempt_at",
            "next_sync_at", "last_error", "quota_status", "property_id", "property_label",
            "domain", "account_label", "external_account_id",
        }
        sets = []
        values: List[Any] = []
        for key, value in fields.items():
            if key in allowed:
                sets.append(f"{key}=?")
                values.append(value)
        if not sets:
            return
        sets.append("updated_at=?")
        values.append(isoformat(utcnow()))
        values.extend([project_id, provider])
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE external_connections SET {', '.join(sets)} WHERE project_id=? AND provider=?",
                values,
            )

    def clear_secret(self, project_id: str, provider: str) -> None:
        now = isoformat(utcnow())
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE external_connections
                SET token_ciphertext=NULL, token_status='revoked', status='DISCONNECTED',
                    last_error=NULL, updated_at=?
                WHERE project_id=? AND provider=?
                """,
                (now, project_id, provider),
            )

    def replace_secret(self, project_id: str, provider: str, secret: Dict[str, Any], **fields: Any) -> None:
        ciphertext = encrypt_json(secret)
        fields = dict(fields)
        fields["token_status"] = fields.get("token_status", "valid")
        now = isoformat(utcnow())
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE external_connections
                SET token_ciphertext=?, token_status=?, token_expires_at=?, updated_at=?
                WHERE project_id=? AND provider=?
                """,
                (
                    ciphertext,
                    fields["token_status"],
                    fields.get("token_expires_at"),
                    now,
                    project_id,
                    provider,
                ),
            )

    def save_catalog(
        self,
        project_id: str,
        provider: str,
        accounts: Iterable[Any],
        properties: Iterable[Any],
    ) -> None:
        now = isoformat(utcnow())
        with self._lock, self._connect() as conn:
            for account in accounts:
                data = account.model_dump() if hasattr(account, "model_dump") else dict(account)
                conn.execute(
                    """
                    INSERT INTO external_accounts (
                        account_row_id, project_id, provider, external_account_id, label, metadata_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(account_row_id) DO UPDATE SET
                        label=excluded.label, metadata_json=excluded.metadata_json, updated_at=excluded.updated_at
                    """,
                    (
                        stable_id("acc_", project_id, provider, data.get("external_account_id")),
                        project_id,
                        provider,
                        data.get("external_account_id"),
                        data.get("label"),
                        json.dumps(strip_secrets(data.get("metadata") or {})),
                        now,
                    ),
                )
            for prop in properties:
                data = prop.model_dump() if hasattr(prop, "model_dump") else dict(prop)
                conn.execute(
                    """
                    INSERT INTO external_properties (
                        property_row_id, project_id, provider, external_property_id, label, domain, metadata_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(property_row_id) DO UPDATE SET
                        label=excluded.label, domain=excluded.domain, metadata_json=excluded.metadata_json, updated_at=excluded.updated_at
                    """,
                    (
                        stable_id("prop_", project_id, provider, data.get("external_property_id")),
                        project_id,
                        provider,
                        data.get("external_property_id"),
                        data.get("label"),
                        data.get("domain"),
                        json.dumps(strip_secrets(data.get("metadata") or {})),
                        now,
                    ),
                )

    def list_properties(self, project_id: str, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM external_properties WHERE project_id=?"
        args: List[Any] = [project_id]
        if provider:
            sql += " AND provider=?"
            args.append(provider)
        with self._lock, self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [dict(row) for row in rows]

    def save_snapshot(
        self,
        *,
        project_id: str,
        provider: str,
        domain: str,
        period_days: int,
        period_start: Optional[str],
        period_end: Optional[str],
        data_state: str,
        summary: Dict[str, Any],
        idempotency_key: str,
        records: List[ExternalRecord],
        raw_payloads: List[Any],
        collected_at: Optional[str] = None,
    ) -> str:
        collected = collected_at or isoformat(utcnow())
        snapshot_id = stable_id("snap_", idempotency_key)
        safe_summary = strip_secrets(summary)
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM external_records WHERE snapshot_id=?", (snapshot_id,))
            conn.execute("DELETE FROM external_raw_payloads WHERE snapshot_id=?", (snapshot_id,))
            conn.execute(
                """
                INSERT INTO external_snapshots (
                    snapshot_id, project_id, provider, domain, period_days, period_start,
                    period_end, collected_at, data_state, summary_json, idempotency_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(snapshot_id) DO UPDATE SET
                    collected_at=excluded.collected_at,
                    data_state=excluded.data_state,
                    summary_json=excluded.summary_json,
                    period_start=excluded.period_start,
                    period_end=excluded.period_end
                """,
                (
                    snapshot_id, project_id, provider, domain, period_days, period_start,
                    period_end, collected, data_state, json.dumps(safe_summary), idempotency_key,
                ),
            )
            for record in records:
                record.snapshot_id = snapshot_id
                payload = record.model_dump()
                conn.execute(
                    """
                    INSERT INTO external_records (
                        record_id, record_type, project_id, provider, source, external_account_id,
                        external_property_id, domain, url, metric, metric_type, value_num, value_text,
                        unit, period_start, period_end, collected_at, evidence_url, raw_provider_reference,
                        confidence, status, evidence_basis, metadata_json, snapshot_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(record_id) DO UPDATE SET
                        value_num=excluded.value_num,
                        value_text=excluded.value_text,
                        collected_at=excluded.collected_at,
                        status=excluded.status,
                        evidence_basis=excluded.evidence_basis,
                        metadata_json=excluded.metadata_json,
                        snapshot_id=excluded.snapshot_id,
                        confidence=excluded.confidence
                    """,
                    (
                        payload["record_id"], payload["record_type"], payload["project_id"], payload["provider"],
                        payload["source"], payload.get("external_account_id"), payload.get("external_property_id"),
                        payload.get("domain"), payload.get("url"), payload["metric"], payload.get("metric_type"),
                        payload.get("value"), payload.get("value_text"), payload.get("unit"),
                        payload.get("period_start"), payload.get("period_end"), payload["collected_at"],
                        payload.get("evidence_url"), payload.get("raw_provider_reference"),
                        payload.get("confidence"), payload.get("status"), payload.get("evidence_basis"),
                        json.dumps(strip_secrets(payload.get("metadata") or {})), snapshot_id,
                    ),
                )
            for raw in raw_payloads:
                data = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
                body = strip_secrets(data.get("payload"))
                raw_id = stable_id("raw_", snapshot_id, data.get("endpoint"))
                conn.execute(
                    """
                    INSERT INTO external_raw_payloads (
                        raw_id, snapshot_id, provider, endpoint, collected_at, http_status, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(raw_id) DO UPDATE SET
                        payload_json=excluded.payload_json, http_status=excluded.http_status, collected_at=excluded.collected_at
                    """,
                    (raw_id, snapshot_id, provider, data.get("endpoint"), collected, data.get("http_status", 200), json.dumps(body)),
                )
        return snapshot_id

    def fresh_snapshot(self, idempotency_key: str, max_age_hours: int, now_iso: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM external_snapshots WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
        if not row:
            return None
        collected = datetime_from_iso(row["collected_at"])
        anchor = datetime_from_iso(now_iso) if now_iso else utcnow()
        age_hours = (anchor - collected).total_seconds() / 3600
        if age_hours > max_age_hours:
            return None
        if row["data_state"] in {"UNAVAILABLE", "NOT_CONNECTED"}:
            return None
        return _snapshot_dict(row)

    def latest_snapshot(self, project_id: str, provider: str, domain: str, period_days: int) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM external_snapshots
                WHERE project_id=? AND provider=? AND domain=? AND period_days=?
                ORDER BY collected_at DESC LIMIT 1
                """,
                (project_id, provider, domain, period_days),
            ).fetchone()
        return _snapshot_dict(row) if row else None

    def snapshot_history(self, project_id: str, domain: str, period_days: int) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM external_snapshots
                WHERE project_id=? AND domain=? AND period_days=?
                ORDER BY collected_at ASC
                """,
                (project_id, domain, period_days),
            ).fetchall()
        return [_snapshot_dict(row) for row in rows]

    def records_for_snapshot(self, snapshot_id: str) -> List[ExternalRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM external_records WHERE snapshot_id=?",
                (snapshot_id,),
            ).fetchall()
        return [_record(row) for row in rows]

    def save_profile(self, project_id: str, profile_type: str, payload: Dict[str, Any]) -> None:
        now = isoformat(utcnow())
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO external_profiles (project_id, profile_type, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id, profile_type) DO UPDATE SET
                    payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (project_id, profile_type, json.dumps(strip_secrets(payload)), now),
            )

    def get_profile(self, project_id: str, profile_type: str) -> Dict[str, Any]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM external_profiles WHERE project_id=? AND profile_type=?",
                (project_id, profile_type),
            ).fetchone()
        if not row:
            return {}
        data = json.loads(row["payload_json"])
        return data if isinstance(data, dict) else {}

    def save_oauth_state(self, state: str, project_id: str, provider: str, domain: Optional[str], payload: Dict[str, Any], expires_at: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO oauth_states (state, project_id, provider, domain, payload_json, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (state, project_id, provider, domain, json.dumps(payload), expires_at, isoformat(utcnow())),
            )

    def consume_oauth_state(self, state: str, now_iso: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM oauth_states WHERE state=?", (state,)).fetchone()
            if not row:
                return None
            conn.execute("DELETE FROM oauth_states WHERE state=?", (state,))
        if row["expires_at"] < (now_iso or isoformat(utcnow())):
            return None
        payload = json.loads(row["payload_json"])
        payload.update({"project_id": row["project_id"], "provider": row["provider"], "domain": row["domain"]})
        return payload

    def enqueue_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        now = isoformat(utcnow())
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                """
                SELECT * FROM external_jobs
                WHERE idempotency_key=? AND status IN ('queued', 'running', 'succeeded', 'partial')
                ORDER BY created_at DESC LIMIT 1
                """,
                (job["idempotency_key"],),
            ).fetchone()
            if existing and not job.get("force"):
                return _job_dict(existing)
            job_id = job.get("job_id") or stable_id("job_", job["idempotency_key"], now)
            conn.execute(
                """
                INSERT INTO external_jobs (
                    job_id, project_id, domain, job_type, provider, period_days, idempotency_key,
                    status, attempt, max_attempts, next_run_at, last_error, result_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', 0, ?, ?, NULL, NULL, ?, ?)
                """,
                (
                    job_id, job["project_id"], job.get("domain"), job["job_type"], job.get("provider"),
                    job.get("period_days"), job["idempotency_key"], job.get("max_attempts", 4),
                    job.get("next_run_at", now), now, now,
                ),
            )
            row = conn.execute("SELECT * FROM external_jobs WHERE job_id=?", (job_id,)).fetchone()
        return _job_dict(row)

    def claim_due_jobs(self, now_iso: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        now = now_iso or isoformat(utcnow())
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM external_jobs
                WHERE status='queued' AND next_run_at<=?
                ORDER BY next_run_at ASC LIMIT ?
                """,
                (now, limit),
            ).fetchall()
            claimed = []
            for row in rows:
                conn.execute(
                    "UPDATE external_jobs SET status='running', attempt=attempt+1, updated_at=? WHERE job_id=? AND status='queued'",
                    (now, row["job_id"]),
                )
                if conn.execute("SELECT changes()").fetchone()[0]:
                    fresh = conn.execute("SELECT * FROM external_jobs WHERE job_id=?", (row["job_id"],)).fetchone()
                    claimed.append(_job_dict(fresh))
        return claimed

    def finish_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None, next_run_at: Optional[str] = None) -> None:
        now = isoformat(utcnow())
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE external_jobs
                SET status=?, result_json=?, last_error=?, next_run_at=COALESCE(?, next_run_at), updated_at=?
                WHERE job_id=?
                """,
                (status, json.dumps(strip_secrets(result or {})), error, next_run_at, now, job_id),
            )

    def list_jobs(self, project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM external_jobs WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        return [_job_dict(row) for row in rows]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM external_jobs WHERE job_id=?", (job_id,)).fetchone()
        return _job_dict(row) if row else None

    def ciphertext_for(self, project_id: str, provider: str) -> Optional[str]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT token_ciphertext FROM external_connections WHERE project_id=? AND provider=?",
                (project_id, provider),
            ).fetchone()
        return row["token_ciphertext"] if row else None

    def upsert_project_keyword(self, row: Dict[str, Any]) -> str:
        keyword_id = row.get("keyword_id") or stable_id("kw_", row["project_id"], row["keyword"])
        now = isoformat(utcnow())
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO project_keywords (
                    keyword_id, project_id, domain, keyword, target_url, intent,
                    search_volume, cpc_usd, competition, keyword_difficulty,
                    current_position, previous_position, best_position,
                    serp_features_json, is_active, tags_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, keyword) DO UPDATE SET
                    domain=excluded.domain,
                    target_url=COALESCE(excluded.target_url, project_keywords.target_url),
                    intent=excluded.intent,
                    search_volume=COALESCE(excluded.search_volume, project_keywords.search_volume),
                    cpc_usd=COALESCE(excluded.cpc_usd, project_keywords.cpc_usd),
                    competition=COALESCE(excluded.competition, project_keywords.competition),
                    keyword_difficulty=COALESCE(excluded.keyword_difficulty, project_keywords.keyword_difficulty),
                    current_position=COALESCE(excluded.current_position, project_keywords.current_position),
                    previous_position=COALESCE(excluded.previous_position, project_keywords.previous_position),
                    best_position=CASE 
                        WHEN excluded.current_position IS NOT NULL AND (project_keywords.best_position IS NULL OR excluded.current_position < project_keywords.best_position)
                        THEN excluded.current_position 
                        ELSE project_keywords.best_position 
                    END,
                    serp_features_json=COALESCE(excluded.serp_features_json, project_keywords.serp_features_json),
                    is_active=excluded.is_active,
                    tags_json=COALESCE(excluded.tags_json, project_keywords.tags_json),
                    updated_at=excluded.updated_at
                """,
                (
                    keyword_id,
                    row["project_id"],
                    row.get("domain", ""),
                    row["keyword"].strip(),
                    row.get("target_url"),
                    row.get("intent", "Commercial"),
                    int(row.get("search_volume") or 0),
                    float(row.get("cpc_usd") or 0.0),
                    float(row.get("competition") or 0.0),
                    row.get("keyword_difficulty"),
                    row.get("current_position"),
                    row.get("previous_position"),
                    row.get("best_position") or row.get("current_position"),
                    json.dumps(row.get("serp_features") or []),
                    int(row.get("is_active", 1)),
                    json.dumps(row.get("tags") or []),
                    row.get("created_at") or now,
                    now,
                ),
            )
        return keyword_id

    def list_project_keywords(self, project_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        query = "SELECT * FROM project_keywords WHERE project_id=?"
        params: List[Any] = [project_id]
        if active_only:
            query += " AND is_active=1"
        query += " ORDER BY search_volume DESC, created_at DESC"
        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_keyword_dict(r) for r in rows]

    def get_project_keyword(self, keyword_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM project_keywords WHERE keyword_id=?", (keyword_id,)).fetchone()
        return _keyword_dict(row) if row else None

    def delete_project_keyword(self, project_id: str, keyword_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM project_keywords WHERE project_id=? AND keyword_id=?", (project_id, keyword_id))
        return cur.rowcount > 0

    def record_keyword_serp_history(self, row: Dict[str, Any]) -> str:
        history_id = row.get("history_id") or stable_id("ksh_", row["keyword_id"], row["snapshot_date"])
        now = isoformat(utcnow())
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO keyword_serp_history (
                    history_id, keyword_id, project_id, domain, position, previous_position,
                    position_delta, ranking_url, serp_features_json, has_ai_overview,
                    has_featured_snippet, has_local_pack, snapshot_date, raw_serp_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(history_id) DO UPDATE SET
                    position=excluded.position,
                    previous_position=excluded.previous_position,
                    position_delta=excluded.position_delta,
                    ranking_url=excluded.ranking_url,
                    serp_features_json=excluded.serp_features_json,
                    has_ai_overview=excluded.has_ai_overview,
                    has_featured_snippet=excluded.has_featured_snippet,
                    has_local_pack=excluded.has_local_pack
                """,
                (
                    history_id,
                    row["keyword_id"],
                    row["project_id"],
                    row["domain"],
                    row.get("position"),
                    row.get("previous_position"),
                    int(row.get("position_delta") or 0),
                    row.get("ranking_url"),
                    json.dumps(row.get("serp_features") or []),
                    int(bool(row.get("has_ai_overview"))),
                    int(bool(row.get("has_featured_snippet"))),
                    int(bool(row.get("has_local_pack"))),
                    row["snapshot_date"],
                    row.get("raw_serp_ref"),
                    now,
                ),
            )
            conn.execute(
                """
                UPDATE project_keywords SET
                    previous_position=COALESCE(?, current_position),
                    current_position=?,
                    best_position=CASE 
                        WHEN ? IS NOT NULL AND (best_position IS NULL OR ? < best_position) THEN ?
                        ELSE best_position
                    END,
                    serp_features_json=?,
                    updated_at=?
                WHERE keyword_id=?
                """,
                (
                    row.get("previous_position"),
                    row.get("position"),
                    row.get("position"),
                    row.get("position"),
                    row.get("position"),
                    json.dumps(row.get("serp_features") or []),
                    now,
                    row["keyword_id"],
                ),
            )
        return history_id

    def get_keyword_serp_history(self, keyword_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM keyword_serp_history WHERE keyword_id=? ORDER BY snapshot_date DESC LIMIT ?",
                (keyword_id, limit),
            ).fetchall()
        return [_history_dict(r) for r in rows]

    def record_keyword_competitors(self, rows: List[Dict[str, Any]]) -> int:
        count = 0
        with self._lock, self._connect() as conn:
            for r in rows:
                comp_id = r.get("comp_history_id") or stable_id("kc_", r["keyword_id"], r["competitor_domain"], r["snapshot_date"])
                conn.execute(
                    """
                    INSERT OR REPLACE INTO keyword_competitors (
                        comp_history_id, keyword_id, project_id, competitor_domain,
                        position, ranking_url, snapshot_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        comp_id,
                        r["keyword_id"],
                        r["project_id"],
                        r["competitor_domain"],
                        r.get("position"),
                        r.get("ranking_url"),
                        r["snapshot_date"],
                    ),
                )
                count += 1
        return count

    def get_keyword_competitors(self, keyword_id: str, snapshot_date: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM keyword_competitors WHERE keyword_id=?"
        params = [keyword_id]
        if snapshot_date:
            query += " AND snapshot_date=?"
            params.append(snapshot_date)
        query += " ORDER BY position ASC"
        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def datetime_from_iso(value: str):
    text = value.replace("Z", "+00:00")
    parsed = datetime_parse(text)
    if parsed.tzinfo is None:
        from datetime import timezone as tz
        return parsed.replace(tzinfo=tz.utc)
    return parsed


def datetime_parse(value: str):
    from datetime import datetime
    return datetime.fromisoformat(value)


def _public_connection(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["scopes"] = json.loads(data.pop("scopes_json") or "[]")
    data["capabilities"] = json.loads(data.pop("capabilities_json") or "{}")
    return data


def _snapshot_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["summary"] = json.loads(data.pop("summary_json") or "{}")
    return data


def _record(row: sqlite3.Row) -> ExternalRecord:
    data = dict(row)
    metadata = json.loads(data.pop("metadata_json") or "{}")
    return ExternalRecord(
        record_id=data["record_id"],
        record_type=data["record_type"],
        project_id=data["project_id"],
        provider=data["provider"],
        source=data["source"],
        external_account_id=data.get("external_account_id"),
        external_property_id=data.get("external_property_id"),
        domain=data.get("domain"),
        url=data.get("url"),
        metric=data["metric"],
        metric_type=data.get("metric_type"),
        value=data.get("value_num"),
        value_text=data.get("value_text"),
        unit=data.get("unit"),
        period_start=data.get("period_start"),
        period_end=data.get("period_end"),
        collected_at=data["collected_at"],
        evidence_url=data.get("evidence_url"),
        raw_provider_reference=data.get("raw_provider_reference"),
        confidence=data.get("confidence") if data.get("confidence") is not None else 1.0,
        status=data.get("status") or "MEASURED",
        evidence_basis=data.get("evidence_basis") or "DIRECT_PROVIDER_EVIDENCE",
        metadata=metadata,
        snapshot_id=data.get("snapshot_id"),
    )


def _job_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    raw = data.get("result_json")
    data["result"] = json.loads(raw) if raw else None
    data.pop("result_json", None)
    return data


def _keyword_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["serp_features"] = json.loads(data.pop("serp_features_json") or "[]")
    data["tags"] = json.loads(data.pop("tags_json") or "[]")
    curr = data.get("current_position")
    prev = data.get("previous_position")
    data["position_delta"] = (prev - curr) if (prev is not None and curr is not None) else 0
    data["has_ai_overview"] = "ai_overview" in data["serp_features"]
    data["has_featured_snippet"] = "featured_snippet" in data["serp_features"]
    return data


def _history_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["serp_features"] = json.loads(data.pop("serp_features_json") or "[]")
    data["has_ai_overview"] = bool(data.get("has_ai_overview"))
    data["has_featured_snippet"] = bool(data.get("has_featured_snippet"))
    data["has_local_pack"] = bool(data.get("has_local_pack"))
    return data


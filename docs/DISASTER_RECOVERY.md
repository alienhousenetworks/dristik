# Dristik Enterprise Disaster Recovery & Operations Runbook

## 1. Database Migrations & Rollback
- Apply latest schema: `cd backend && alembic upgrade head`
- Roll back one revision: `cd backend && alembic downgrade -1`
- CI gate verifies `upgrade head -> downgrade -1 -> upgrade head` before release.

## 2. Automated Backups & Restore Verification
- Run daily via cron/systemd timer: `bash scripts/backup_restore_verify.sh <db_path> <backup_dir>`
- Uses atomic online backup (`sqlite3.backup` / `pg_dump --format=custom` for PostgreSQL) and validates `PRAGMA integrity_check` on a restored copy before declaring success.
- **Target RPO**: 24 hours (or 15 minutes with PostgreSQL WAL archiving). **Target RTO**: < 30 minutes.

## 3. Dead-Letter Queue (DLQ) & Connector Recovery
- Failed background jobs retry with exponential backoff up to `max_attempts`, then quarantine into `dead_letter_jobs`.
- Inspect health & latency: `GET /api/v1/enterprise/ops/health` and `GET /api/v1/enterprise/ops/metrics`.
- Replay quarantined jobs (requires `ops:dlq_replay` RBAC role): `POST /api/v1/enterprise/ops/dlq/{dlq_id}/replay`.

## 4. Credential Rotation & Incident Response
- Rotate `CREDENTIAL_ENCRYPTION_KEY` via `SecretVault(new_key, previous_keys=[old_key]).rotate_token(...)` with zero downtime.
- Revoke compromised webhook secrets immediately in vendor console and `.env`, then restart `dristik-api`.

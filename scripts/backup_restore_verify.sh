#!/usr/bin/env bash
# Automated Backup & Restore Verification Script for Dristik Unified Database
set -euo pipefail

DB_PATH="${1:-/Users/sayantande/dristik-main2/dristik/backend/data/dristik.db}"
BACKUP_DIR="${2:-/tmp/dristik_backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

if [[ ! -f "$DB_PATH" ]]; then
  echo "Database file not found at $DB_PATH" >&2
  exit 1
fi

BACKUP_FILE="$BACKUP_DIR/dristik_${STAMP}.db"
RESTORE_TEST_FILE="$BACKUP_DIR/restore_verify_${STAMP}.db"

# 1. Hot-safe SQLite backup via Python sqlite3.backup API
python3 - "$DB_PATH" "$BACKUP_FILE" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
with dst:
    src.backup(dst)
src.close()
dst.close()
PY

# 2. Restore copy & run PRAGMA integrity_check
cp "$BACKUP_FILE" "$RESTORE_TEST_FILE"
INTEGRITY=$(python3 - "$RESTORE_TEST_FILE" <<'PY'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
res = c.execute("PRAGMA integrity_check;").fetchone()[0]
tables = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';").fetchone()[0]
c.close()
print(f"{res}:{tables}")
PY
)

rm -f "$RESTORE_TEST_FILE"
if [[ "$INTEGRITY" != ok:* ]]; then
  echo "Restore integrity check FAILED: $INTEGRITY" >&2
  exit 2
fi

echo "Backup & restore verification PASSED ($INTEGRITY tables) -> $BACKUP_FILE"

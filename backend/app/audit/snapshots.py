"""
Content-addressed immutable snapshots of raw page bodies and API responses.

A snapshot ID is snap_<sha256>. The same bytes always produce the same ID.
Re-fetching later can prove the stored body is exactly what was hashed at fetch time.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.evidence.provenance import canonical_bytes, sha256_bytes


def artifacts_root() -> Path:
    override = os.environ.get("DRISTIK_RUN_ARTIFACTS")
    if override:
        return Path(override)
    try:
        from app.core.config import settings
        db = Path(settings.AUTH_DATABASE_PATH)
        return (db.parent if db.parent.name else Path("data")) / "runs"
    except Exception:
        return Path("data") / "runs"


class SnapshotRecord(BaseModel):
    snapshot_id: str
    sha256: str
    fetched_at: str
    source: str
    source_type: str = "http"
    media_type: str = "text/plain"
    url: Optional[str] = None
    token_id: Optional[str] = None
    byte_length: int = 0
    body: Any = None


class SnapshotStore:
    def __init__(self, run_id: str, root: Optional[Path] = None):
        self.run_id = run_id
        self.root = Path(root) if root else artifacts_root() / run_id
        self._memory: Dict[str, SnapshotRecord] = {}

    def put(
        self,
        source: str,
        body: Any,
        *,
        source_type: str = "http",
        media_type: str = "text/plain",
        url: Optional[str] = None,
        token_id: Optional[str] = None,
        fetched_at: Optional[str] = None,
    ) -> SnapshotRecord:
        raw = canonical_bytes(body)
        digest = sha256_bytes(raw)
        snapshot_id = f"snap_{digest}"
        fetched = fetched_at or datetime.now(timezone.utc).isoformat()
        if isinstance(body, bytes):
            stored_body = body.decode("utf-8", errors="replace")
        else:
            stored_body = body
        record = SnapshotRecord(
            snapshot_id=snapshot_id,
            sha256=digest,
            fetched_at=fetched,
            source=source,
            source_type=source_type,
            media_type=media_type,
            url=url,
            token_id=token_id,
            byte_length=len(raw),
            body=stored_body,
        )
        existing = self.get(snapshot_id)
        if existing:
            if existing.sha256 != digest:
                raise ValueError(f"Snapshot {snapshot_id} is immutable and does not match stored hash.")
            return existing
        self._memory[snapshot_id] = record
        path = self._path(snapshot_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(record.model_dump_json(), encoding="utf-8")
        else:
            on_disk = SnapshotRecord.model_validate_json(path.read_text(encoding="utf-8"))
            if on_disk.sha256 != digest:
                raise ValueError(f"Snapshot {snapshot_id} on disk is immutable and hash-mismatched.")
        return record

    def get(self, snapshot_id: str) -> Optional[SnapshotRecord]:
        if snapshot_id in self._memory:
            return self._memory[snapshot_id]
        path = self._path(snapshot_id)
        if path.exists():
            record = SnapshotRecord.model_validate_json(path.read_text(encoding="utf-8"))
            self._memory[snapshot_id] = record
            return record
        return None

    def verify(self, snapshot_id: str) -> bool:
        record = self.get(snapshot_id)
        if not record:
            return False
        return sha256_bytes(canonical_bytes(record.body)) == record.sha256

    def list_ids(self) -> List[str]:
        snap_dir = self.root / "snapshots"
        disk = {p.stem for p in snap_dir.glob("snap_*.json")} if snap_dir.exists() else set()
        return sorted(set(self._memory.keys()) | disk)

    def _path(self, snapshot_id: str) -> Path:
        return self.root / "snapshots" / f"{snapshot_id}.json"


def load_run_snapshot_store(run_id: str, root: Optional[Path] = None) -> SnapshotStore:
    return SnapshotStore(run_id, root=root)

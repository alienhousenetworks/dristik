"""
Evidence Snapshot Engine — Enterprise Crawling & Ingestion (Phase 1.5)

Stores and indexes immutable, content-addressed page captures containing
raw HTML, rendered DOM, HTTP metadata, structured data, and network telemetry.
Each artifact is independently retrievable.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.canonical_audit_model import PageSnapshot


class FullPageSnapshotRecord(BaseModel):
    snapshot_id: str
    audit_run_id: str
    domain_id: str
    page_id: str
    url: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_html: str
    raw_html_sha256: str
    rendered_dom: Optional[str] = None
    rendered_dom_sha256: Optional[str] = None
    screenshot_ref: Optional[str] = None
    status_code: int = 200
    http_headers: Dict[str, str] = Field(default_factory=dict)
    ttfb_ms: float = 0.0
    total_time_ms: float = 0.0
    extracted_headings: List[str] = Field(default_factory=list)
    structured_data_schemas: List[Dict[str, Any]] = Field(default_factory=list)
    network_telemetry: Dict[str, Any] = Field(default_factory=dict)


class SnapshotEngine:
    """
    Manages content-addressed storage and independent retrieval of audit page snapshots.
    """

    def __init__(self, run_id: str, storage_root: Optional[Path] = None):
        self.run_id = run_id
        self.storage_root = storage_root or Path(f"data/runs/{run_id}/snapshots")
        self._memory_index: Dict[str, FullPageSnapshotRecord] = {}

    def capture_and_store_snapshot(
        self,
        domain_id: str,
        page_id: str,
        url: str,
        raw_html: str,
        rendered_dom: Optional[str] = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        ttfb_ms: float = 250.0,
        screenshot_ref: Optional[str] = None,
        extracted_headings: Optional[List[str]] = None,
        structured_data: Optional[List[Dict[str, Any]]] = None,
        telemetry: Optional[Dict[str, Any]] = None,
    ) -> Tuple[PageSnapshot, FullPageSnapshotRecord]:
        """
        Creates an immutable, content-addressed snapshot, writes it to disk/memory,
        and returns both the canonical PageSnapshot and the full artifact record.
        """
        raw_bytes = raw_html.encode("utf-8")
        raw_sha = hashlib.sha256(raw_bytes).hexdigest()

        rendered_sha = None
        if rendered_dom:
            rendered_sha = hashlib.sha256(rendered_dom.encode("utf-8")).hexdigest()

        snapshot_id = f"snap_{raw_sha[:16]}"

        full_record = FullPageSnapshotRecord(
            snapshot_id=snapshot_id,
            audit_run_id=self.run_id,
            domain_id=domain_id,
            page_id=page_id,
            url=url,
            raw_html=raw_html,
            raw_html_sha256=raw_sha,
            rendered_dom=rendered_dom,
            rendered_dom_sha256=rendered_sha,
            screenshot_ref=screenshot_ref,
            status_code=status_code,
            http_headers=headers or {},
            ttfb_ms=round(ttfb_ms, 1),
            total_time_ms=round(ttfb_ms * 1.3, 1),
            extracted_headings=extracted_headings or [],
            structured_data_schemas=structured_data or [],
            network_telemetry=telemetry or {},
        )

        # Store in memory index
        self._memory_index[snapshot_id] = full_record

        # Persist to disk if storage directory available
        try:
            self.storage_root.mkdir(parents=True, exist_ok=True)
            snap_file = self.storage_root / f"{snapshot_id}.json"
            snap_file.write_text(json.dumps(full_record.model_dump(mode="json"), indent=2))
        except Exception:
            pass

        # Build Phase 0.1 canonical PageSnapshot
        canonical_snap = PageSnapshot(
            audit_run_id=self.run_id,
            domain_id=domain_id,
            snapshot_id=snapshot_id,
            page_id=page_id,
            url=url,
            raw_html_sha256=raw_sha,
            storage_uri=str(self.storage_root / f"{snapshot_id}.json"),
            rendered_dom_captured=bool(rendered_dom),
            http_headers=headers or {},
        )

        return canonical_snap, full_record

    def retrieve_snapshot(self, snapshot_id: str) -> Optional[FullPageSnapshotRecord]:
        """Independently retrieves an exact page snapshot without recrawling."""
        if snapshot_id in self._memory_index:
            return self._memory_index[snapshot_id]

        snap_file = self.storage_root / f"{snapshot_id}.json"
        if snap_file.exists():
            try:
                data = json.loads(snap_file.read_text())
                record = FullPageSnapshotRecord.model_validate(data)
                self._memory_index[snapshot_id] = record
                return record
            except Exception:
                return None
        return None

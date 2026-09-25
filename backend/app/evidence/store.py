"""
Dristik AI Immutable Evidence Store
Thread-safe registry of all deterministic observations for an audit run.
"""
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from app.evidence.models import Evidence
from app.evidence.provenance import compute_evidence_hash, compute_raw_source_hash

class EvidenceStore:
    def __init__(self, run_id: str, snapshots=None):
        self.run_id = run_id
        self._evidence: Dict[str, Evidence] = {}
        self._counter: int = 0
        self._ext_counter: int = 0
        self.snapshots = snapshots
        self._current_fetch: Optional[Dict[str, Any]] = None

    def _ensure_snapshots(self):
        if self.snapshots is None:
            from app.audit.snapshots import SnapshotStore
            self.snapshots = SnapshotStore(self.run_id)
        return self.snapshots

    def record_fetch(
        self,
        url: str,
        raw_body: Any,
        *,
        source: str = "http",
        source_type: str = "http",
        media_type: str = "text/html",
    ) -> Any:
        """Snapshot the raw page/API body. Subsequent add_evidence inherits this fetch."""
        fetched_at = datetime.now(timezone.utc)
        store = self._ensure_snapshots()
        record = store.put(
            source=source,
            body=raw_body,
            source_type=source_type,
            media_type=media_type,
            url=url,
            fetched_at=fetched_at.isoformat(),
        )
        self._current_fetch = {
            "url": url,
            "raw_snapshot_id": record.snapshot_id,
            "content_sha256": record.sha256,
            "fetched_at": fetched_at,
        }
        return record

    def add_evidence(
        self,
        source_type: str,
        analyzer: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        raw_source: Optional[Any] = None,
    ) -> Evidence:
        self._counter += 1
        ev_id = f"ev_{self._counter:03d}"
        ev_hash = compute_evidence_hash(source_type, analyzer, url, selector, text, value)
        fetch = self._current_fetch or {}
        fetched_at = fetch.get("fetched_at") or datetime.now(timezone.utc)
        snapshot_id = fetch.get("raw_snapshot_id")
        if raw_source is not None:
            content_sha = compute_raw_source_hash(raw_source)
            snap = self._ensure_snapshots().put(
                source=analyzer,
                body=raw_source,
                source_type=source_type,
                url=url,
                token_id=ev_id,
                fetched_at=fetched_at.isoformat() if hasattr(fetched_at, "isoformat") else str(fetched_at),
            )
            snapshot_id = snap.snapshot_id
            content_sha = snap.sha256
        else:
            content_sha = fetch.get("content_sha256") or compute_raw_source_hash(
                {"text": text or "", "value": value, "url": url or "", "selector": selector or ""}
            )

        evidence = Evidence(
            id=ev_id,
            source_type=source_type,
            url=url,
            selector=selector,
            text=text,
            value=value,
            analyzer=analyzer,
            hash=ev_hash,
            content_sha256=content_sha,
            fetched_at=fetched_at if isinstance(fetched_at, datetime) else None,
            raw_snapshot_id=snapshot_id,
            metadata=metadata or {},
        )
        self._evidence[ev_id] = evidence
        return evidence

    def add_external_evidence(
        self,
        source: str,
        claim: str,
        raw_value: Optional[Any] = None,
        confidence_basis: str = "direct_api",
        conflicts_with: Optional[List[str]] = None,
        fetched_at: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Evidence:
        """Append an EXTERNAL_EVIDENCE item with token prefix ext_001, ext_002, ..."""
        self._ext_counter += 1
        ext_id = f"ext_{self._ext_counter:03d}"
        now = datetime.now(timezone.utc)
        fetched = fetched_at or now.isoformat()
        meta = dict(metadata or {})
        payload = raw_value if raw_value is not None else {}
        snap = self._ensure_snapshots().put(
            source=source,
            body=payload,
            source_type="api",
            media_type="application/json",
            url=url,
            token_id=ext_id,
            fetched_at=fetched,
        )
        meta.update({
            "source": source,
            "confidence_basis": confidence_basis,
            "conflicts_with": list(conflicts_with or []),
            "fetched_at": fetched,
            "evidence_class": "EXTERNAL_EVIDENCE",
            "raw_snapshot_id": snap.snapshot_id,
        })
        ev_hash = compute_evidence_hash("external", source, url, None, claim, payload)
        evidence = Evidence(
            id=ext_id,
            source_type="external",
            url=url,
            text=claim,
            value=payload,
            analyzer=source,
            hash=ev_hash,
            content_sha256=snap.sha256,
            fetched_at=now,
            raw_snapshot_id=snap.snapshot_id,
            metadata=meta,
        )
        self._evidence[ext_id] = evidence
        return evidence

    def get_external(self) -> List[Evidence]:
        return [ev for ev in self._evidence.values() if ev.id.startswith("ext_")]

    def add(self, evidence: Evidence) -> Evidence:
        self._evidence[evidence.id] = evidence
        if evidence.id.startswith("ext_"):
            try:
                n = int(evidence.id.split("_", 1)[1])
                self._ext_counter = max(self._ext_counter, n)
            except (ValueError, IndexError):
                pass
        return evidence

    def get(self, evidence_id: str) -> Optional[Evidence]:
        return self._evidence.get(evidence_id)

    def get_all(self) -> List[Evidence]:
        return list(self._evidence.values())

    def get_by_source_type(self, source_type: str) -> List[Evidence]:
        return [ev for ev in self._evidence.values() if ev.source_type == source_type]

    def count(self) -> int:
        return len(self._evidence)

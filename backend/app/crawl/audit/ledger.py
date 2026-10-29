"""
Dristik AI Append-Only Cryptographic Audit Ledger (Plane 6)
Stores immutable hash-chained audit events for every crawl, capability execution,
finding approval, patch generation, and data export.
"""
import hashlib
import json
import time
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    org_id: str
    workspace_id: str = "ws_default"
    mission_id: Optional[str] = None
    actor: str  # User ID, System Agent ID, or API Key ID
    action: str  # "mission:create", "crawler:fetch", "critic:reject", "patch:approve", "report:export"
    target: str  # URL, Finding ID, Patch ID
    timestamp: float = Field(default_factory=time.time)
    details: Dict[str, Any] = Field(default_factory=dict)
    prev_hash: str = "0" * 64
    event_hash: str = ""

class AuditLedger:
    """In-memory append-only tamper-evident audit ledger with cryptographic hash chaining."""

    def __init__(self):
        self._events: List[AuditEvent] = []
        self._latest_hash: str = "0" * 64

    def record_event(
        self,
        org_id: str,
        actor: str,
        action: str,
        target: str,
        mission_id: Optional[str] = None,
        workspace_id: str = "ws_default",
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        event = AuditEvent(
            org_id=org_id,
            workspace_id=workspace_id,
            mission_id=mission_id,
            actor=actor,
            action=action,
            target=target,
            details=details or {},
            prev_hash=self._latest_hash
        )

        # Compute SHA-256 hash over serialized event content
        payload = f"{event.event_id}:{event.org_id}:{event.actor}:{event.action}:{event.target}:{event.timestamp}:{event.prev_hash}:{json.dumps(event.details, sort_keys=True)}"
        event.event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        self._latest_hash = event.event_hash
        self._events.append(event)
        return event

    def get_events_for_org(self, org_id: str) -> List[AuditEvent]:
        return [e for e in self._events if e.org_id == org_id]

    def verify_integrity(self) -> bool:
        """Verifies the entire hash chain from genesis to head."""
        expected_prev = "0" * 64
        for event in self._events:
            if event.prev_hash != expected_prev:
                return False
            payload = f"{event.event_id}:{event.org_id}:{event.actor}:{event.action}:{event.target}:{event.timestamp}:{event.prev_hash}:{json.dumps(event.details, sort_keys=True)}"
            recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if recomputed != event.event_hash:
                return False
            expected_prev = event.event_hash
        return True

audit_ledger = AuditLedger()

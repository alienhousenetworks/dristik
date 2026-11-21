"""
Audit Event Store & Real-Time SSE Streamer for the SEO Orchestrator.
Supports all 16 canonical blueprint SSE event types as well as backward-compatible terminal markers.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Set

CANONICAL_SSE_EVENTS = frozenset({
    "audit.started",
    "crawl.discovering",
    "crawl.progress",
    "agent.started",
    "agent.progress",
    "agent.completed",
    "agent.failed",
    "evidence.persisted",
    "findings.validated",
    "scoring.completed",
    "remediation.generated",
    "qa.started",
    "qa.completed",
    "audit.completed",
    "audit.partial",
    "audit.failed",
    "audit.cancelled",
})

_TERMINAL_EVENTS = frozenset({
    "AUDIT_COMPLETED",
    "AUDIT_FAILED",
    "AUDIT_CANCELLED",
    "audit.completed",
    "audit.partial",
    "audit.failed",
    "audit.cancelled",
})


class EventStore:
    """
    Stores historical audit events and broadcasts real-time SSE updates to subscribers.
    """

    def __init__(self, audit_id: str):
        self.audit_id = audit_id
        self.events: List[Dict[str, Any]] = []
        self._subscribers: Set[asyncio.Queue] = set()

    def emit(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Records an event and broadcasts to all active SSE queues."""
        payload = {
            "audit_id": self.audit_id,
            "type": event_type,
            "event": event_type,
            "agent_id": data.get("agent_id"),
            "task_id": data.get("task_id") or data.get("agent_id"),
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.events.append(payload)

        dead_queues = set()
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead_queues.add(q)
        for q in dead_queues:
            self._subscribers.discard(q)

        return payload

    async def stream(self) -> AsyncGenerator[str, None]:
        """Asynchronous generator yielding SSE formatted strings for FastAPI StreamingResponse."""
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        finished = False
        for past_event in self.events:
            yield f"event: {past_event.get('type', 'message')}\ndata: {json.dumps(past_event)}\n\n"
            if past_event.get("type") in _TERMINAL_EVENTS:
                finished = True
                break

        if finished:
            return

        self._subscribers.add(q)
        try:
            while True:
                event = await q.get()
                yield f"event: {event.get('type', 'message')}\ndata: {json.dumps(event)}\n\n"
                if event.get("type") in _TERMINAL_EVENTS:
                    break
        finally:
            self._subscribers.discard(q)

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self.events)

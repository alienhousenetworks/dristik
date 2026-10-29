"""Finding lifecycle. A proposed fix is not a verified result."""

from __future__ import annotations

FINDING_STATUSES = (
    "open",
    "approved",
    "in_progress",
    "fixed_unverified",
    "verified",
    "partially_verified",
    "reopened",
    "not_applicable",
    "insufficient_evidence",
    "accepted_risk",
)

# A status may move only along these edges. Verification requires a fresh crawl.
_EDGES: dict[str, frozenset[str]] = {
    "open": frozenset({"approved", "in_progress", "not_applicable", "insufficient_evidence", "accepted_risk"}),
    "approved": frozenset({"in_progress", "open"}),
    "in_progress": frozenset({"fixed_unverified", "open"}),
    "fixed_unverified": frozenset({"verified", "partially_verified", "reopened", "in_progress"}),
    "verified": frozenset({"reopened"}),
    "partially_verified": frozenset({"verified", "reopened", "in_progress"}),
    "reopened": frozenset({"in_progress", "approved"}),
    "not_applicable": frozenset(),
    "insufficient_evidence": frozenset({"open"}),
    "accepted_risk": frozenset({"reopened", "open"}),
}


class LifecycleError(ValueError):
    pass


def transition(current: str, new: str) -> str:
    """Return the new status, or raise if the edge is not allowed."""
    if current not in _EDGES:
        raise LifecycleError(f"Unknown finding status: {current}")
    if new not in FINDING_STATUSES:
        raise LifecycleError(f"Unknown finding status: {new}")
    if new not in _EDGES[current]:
        raise LifecycleError(f"Cannot move a finding from {current} to {new}")
    return new

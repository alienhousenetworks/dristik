"""Copy finding-attached observations into the report evidence ledger."""
from __future__ import annotations

from typing import Any, Dict, Optional


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " · ".join(str(item) for item in value if item is not None)
    return str(value)


def ledger_entry_for_evidence(evidence: Any) -> Optional[tuple[str, Dict[str, Any]]]:
    """Return a ledger row for evidence that already sits on a finding."""
    if isinstance(evidence, dict):
        evidence_id = _text(evidence.get("evidence_id")).strip()
        source = evidence.get("source") or evidence.get("type") or "finding"
        analyzer = evidence.get("test_method")
        url = evidence.get("url")
        selector = evidence.get("selector") or evidence.get("element")
        text = evidence.get("snippet") or evidence.get("value")
        value = evidence.get("value")
        digest = evidence.get("hash")
        content_sha256 = evidence.get("content_sha256")
        snapshot_id = evidence.get("raw_snapshot_id")
        fetched_at = evidence.get("collection_timestamp")
    else:
        evidence_id = _text(getattr(evidence, "evidence_id", None)).strip()
        source = getattr(evidence, "source", None) or getattr(evidence, "type", None) or "finding"
        analyzer = getattr(evidence, "test_method", None)
        url = getattr(evidence, "url", None)
        selector = getattr(evidence, "selector", None) or getattr(evidence, "element", None)
        text = getattr(evidence, "snippet", None) or getattr(evidence, "value", None)
        value = getattr(evidence, "value", None)
        digest = getattr(evidence, "hash", None)
        content_sha256 = getattr(evidence, "content_sha256", None)
        snapshot_id = getattr(evidence, "raw_snapshot_id", None)
        fetched_at = getattr(evidence, "collection_timestamp", None)
    if not evidence_id:
        return None
    return evidence_id, {
        "id": evidence_id,
        "source_type": _text(source) or "finding",
        "analyzer": _text(analyzer),
        "url": _text(url),
        "selector": _text(selector),
        "text": _text(text),
        "value": _text(value),
        "hash": _text(digest),
        "content_sha256": _text(content_sha256),
        "raw_snapshot_id": _text(snapshot_id),
        "fetched_at": _text(fetched_at),
        "metadata": {"attached_to_finding": True},
    }


def merge_finding_evidence(ledger: Dict[str, Dict[str, Any]], findings: Any) -> Dict[str, Dict[str, Any]]:
    """Add finding evidence that the crawl store did not already index.

    Heading and similar analyzers attach observations directly to a finding.
    The publication gate treats an ID as missing when that observation is not
    also a ledger row.
    """
    for finding in findings or []:
        evidence_items = finding.get("evidence") if isinstance(finding, dict) else getattr(finding, "evidence", None)
        for evidence in evidence_items or []:
            entry = ledger_entry_for_evidence(evidence)
            if entry is None:
                continue
            evidence_id, payload = entry
            ledger.setdefault(evidence_id, payload)
    return ledger

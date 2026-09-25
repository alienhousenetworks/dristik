"""
Dristik AI Provenance Utilities
Computes deterministic SHA-256 hashes and evidence identifiers.
"""
import hashlib
import json
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_bytes(raw: Any) -> bytes:
    """Serialize raw source material for hashing. Strings/bytes are hashed as-is."""
    if raw is None:
        return b""
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, str):
        return raw.encode("utf-8")
    return json.dumps(raw, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")


def compute_raw_source_hash(raw: Any) -> str:
    """SHA-256 of the raw page body or API payload at fetch time (not a truncated extract)."""
    return sha256_bytes(canonical_bytes(raw))


def compute_evidence_hash(source_type: str, analyzer: str, url: str | None, selector: str | None, text: str | None, value: Any) -> str:
    payload = {
        "source_type": source_type,
        "analyzer": analyzer,
        "url": url or "",
        "selector": selector or "",
        "text": (text or "").strip()[:500],
        "value": str(value) if value is not None else ""
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

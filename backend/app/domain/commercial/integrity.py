"""Integrity and provenance for evidence records.

A content hash, a Merkle inclusion proof, and an Ed25519 signature show that
a record was not altered after it was sealed. They do not show that the
underlying analysis was correct, complete, or legally certified.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Optional

from pydantic import BaseModel


INTEGRITY_CLAIM = "integrity_and_provenance"
NOT_A_CORRECTNESS_PROOF = (
    "This proof shows that the sealed bytes match the signature and the inclusion path. "
    "It is not proof that the finding is correct, that the source was authentic, "
    "or that the analysis was sound."
)


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def content_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def merkle_root(leaf_payloads: list[Any]) -> str:
    if not leaf_payloads:
        raise ValueError("A Merkle root requires at least one leaf.")
    level = [_sha256(canonical_bytes(item)) for item in leaf_payloads]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [_sha256(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0].hex()


def merkle_proof(leaf_payloads: list[Any], index: int) -> list[dict[str, str]]:
    if index < 0 or index >= len(leaf_payloads):
        raise ValueError("Leaf index is outside the sealed set.")
    level = [_sha256(canonical_bytes(item)) for item in leaf_payloads]
    proof: list[dict[str, str]] = []
    cursor = index
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        sibling = cursor ^ 1
        proof.append({
            "side": "right" if sibling > cursor else "left",
            "hash": level[sibling].hex(),
        })
        level = [_sha256(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
        cursor //= 2
    return proof


def verify_merkle_proof(leaf_payload: Any, proof: list[dict[str, str]], root_hex: str) -> bool:
    try:
        current = _sha256(canonical_bytes(leaf_payload))
        for step in proof:
            sibling = bytes.fromhex(step["hash"])
            if step["side"] == "left":
                current = _sha256(sibling + current)
            elif step["side"] == "right":
                current = _sha256(current + sibling)
            else:
                return False
        return current.hex() == root_hex
    except (KeyError, ValueError):
        return False


class IntegritySeal(BaseModel):
    leaf_hash: str
    merkle_root: str
    leaf_index: int
    proof: list[dict[str, str]]
    key_id: Optional[str] = None
    signature_hex: Optional[str] = None
    signature_status: str = "unsigned"
    proves: str = INTEGRITY_CLAIM
    limitation: str = NOT_A_CORRECTNESS_PROOF


def _signing_keys() -> dict[str, bytes]:
    keys: dict[str, bytes] = {}
    raw_map = os.environ.get("DRISTIK_EVIDENCE_SIGNING_KEYS", "").strip()
    if raw_map:
        parsed = json.loads(raw_map)
        if not isinstance(parsed, dict):
            raise ValueError("DRISTIK_EVIDENCE_SIGNING_KEYS must be a JSON object of key id to hex seed.")
        for key_id, seed_hex in parsed.items():
            seed = bytes.fromhex(str(seed_hex))
            if len(seed) != 32:
                raise ValueError(f"Signing seed for {key_id} must be 32 bytes.")
            keys[str(key_id)] = seed
    seed_hex = os.environ.get("DRISTIK_EVIDENCE_SIGNING_SEED", "").strip()
    if seed_hex:
        seed = bytes.fromhex(seed_hex)
        if len(seed) != 32:
            raise ValueError("DRISTIK_EVIDENCE_SIGNING_SEED must be 32 bytes.")
        keys.setdefault(os.environ.get("DRISTIK_EVIDENCE_SIGNING_KEY_ID", "current"), seed)
    return keys


def current_key_id() -> Optional[str]:
    keys = _signing_keys()
    if not keys:
        return None
    preferred = os.environ.get("DRISTIK_EVIDENCE_SIGNING_KEY_ID", "").strip()
    if preferred and preferred in keys:
        return preferred
    return next(iter(keys))


def seal_records(records: list[Any], *, leaf_index: int = 0) -> IntegritySeal:
    if not records:
        raise ValueError("Nothing to seal.")
    root = merkle_root(records)
    proof = merkle_proof(records, leaf_index)
    leaf = content_hash(records[leaf_index])
    key_id = current_key_id()
    signature_hex = None
    status = "unsigned"
    if key_id:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private = Ed25519PrivateKey.from_private_bytes(_signing_keys()[key_id])
        signature_hex = private.sign(bytes.fromhex(root)).hex()
        status = "signed"
    return IntegritySeal(
        leaf_hash=leaf,
        merkle_root=root,
        leaf_index=leaf_index,
        proof=proof,
        key_id=key_id,
        signature_hex=signature_hex,
        signature_status=status,
    )


def verify_seal(leaf_payload: Any, seal: IntegritySeal) -> dict[str, Any]:
    """Fail closed when a proof or signature is present and does not check out."""
    inclusion_ok = verify_merkle_proof(leaf_payload, seal.proof, seal.merkle_root)
    hash_ok = content_hash(leaf_payload) == seal.leaf_hash
    signature_ok: Optional[bool] = None
    signature_error = None
    if seal.signature_status == "signed" or seal.signature_hex:
        signature_ok = False
        try:
            if not seal.key_id or not seal.signature_hex:
                signature_error = "Signed seal is missing a key id or signature."
            else:
                keys = _signing_keys()
                seed = keys.get(seal.key_id)
                if seed is None:
                    signature_error = "Signing key is not available. Verification failed closed."
                else:
                    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

                    public = Ed25519PrivateKey.from_private_bytes(seed).public_key()
                    public.verify(bytes.fromhex(seal.signature_hex), bytes.fromhex(seal.merkle_root))
                    signature_ok = True
                    signature_error = None
        except Exception as exc:
            signature_ok = False
            signature_error = signature_error or type(exc).__name__
    valid = inclusion_ok and hash_ok and signature_ok is not False
    return {
        "valid": valid,
        "inclusion_ok": inclusion_ok,
        "leaf_hash_ok": hash_ok,
        "signature_ok": signature_ok,
        "signature_error": signature_error,
        "proves": INTEGRITY_CLAIM,
        "limitation": NOT_A_CORRECTNESS_PROOF,
    }

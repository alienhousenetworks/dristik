"""Encrypt customer OAuth tokens and provider credentials at rest.

The ciphertext is Fernet (AES-128-CBC + HMAC). A raw passphrase is hashed
to a key. A url-safe Fernet key is used as-is. Plaintext is never stored.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken


class EncryptionKeyMissing(RuntimeError):
    """Raised when a credential would otherwise have to be stored in plaintext."""


def _fernet(key_material: str) -> Fernet:
    raw = (key_material or "").strip().encode("utf-8")
    if not raw:
        raise EncryptionKeyMissing(
            "EXTERNAL_INTEGRATION_ENCRYPTION_KEY is not configured. "
            "Credentials were not stored."
        )
    try:
        return Fernet(raw)
    except Exception:
        digest = hashlib.sha256(raw).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def require_key() -> str:
    from app.core.config import settings
    key = settings.EXTERNAL_INTEGRATION_ENCRYPTION_KEY
    if not key or not str(key).strip():
        raise EncryptionKeyMissing(
            "EXTERNAL_INTEGRATION_ENCRYPTION_KEY is not configured. "
            "Credentials were not stored."
        )
    return str(key).strip()


def encrypt_json(payload: Dict[str, Any], key_material: str | None = None) -> str:
    key = key_material or require_key()
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _fernet(key).encrypt(body).decode("ascii")


def decrypt_json(ciphertext: str, key_material: str | None = None) -> Dict[str, Any]:
    key = key_material or require_key()
    try:
        raw = _fernet(key).decrypt(ciphertext.encode("ascii"))
    except InvalidToken as exc:
        raise InvalidToken("stored credential could not be decrypted") from exc
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("stored credential payload is not an object")
    return data

"""Password hashing and opaque session / reset tokens."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Optional

from app.core.config import settings

PBKDF2_ITERATIONS = 210_000
SESSION_COOKIE = "dristik_session"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iters, salt_hex, digest_hex = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iters),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    material = f"{settings.AUTH_SECRET}:{token}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def password_errors(password: str) -> Optional[str]:
    if not password or len(password) < 8:
        return "Password must be at least 8 characters."
    if password.lower() == password or password.upper() == password:
        return "Password must include both upper and lower case letters."
    if not any(ch.isdigit() for ch in password):
        return "Password must include a number."
    return None

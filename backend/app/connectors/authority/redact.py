"""Remove credentials from payloads, errors, and logs."""
from __future__ import annotations

import logging
import re
from typing import Any

_SECRET_KEYS = {
    "access_token",
    "refresh_token",
    "id_token",
    "api_key",
    "apikey",
    "password",
    "client_secret",
    "private_key",
    "authorization",
    "app_password",
    "code_verifier",
    "secret",
}
_TOKEN_RE = re.compile(r"(ya29\.[A-Za-z0-9_\-]+|Bearer\s+[A-Za-z0-9._\-]+)", re.IGNORECASE)


def strip_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_KEYS:
                cleaned[key] = "[redacted]"
            else:
                cleaned[key] = strip_secrets(item)
        return cleaned
    if isinstance(value, list):
        return [strip_secrets(item) for item in value]
    if isinstance(value, str):
        return _TOKEN_RE.sub("[redacted]", value)
    return value


def safe_http_error(status: int, body: str) -> str:
    text = _TOKEN_RE.sub("[redacted]", body or "")
    text = text.replace("\n", " ")[:240]
    return f"HTTP {status}: {text}"


class _SecretLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        if _TOKEN_RE.search(message) or "access_token" in message or "refresh_token" in message:
            record.msg = "[external-authority] log line redacted"
            record.args = ()
        return True


def install_log_redaction() -> None:
    logger = logging.getLogger("app.external_authority")
    if not any(isinstance(item, _SecretLogFilter) for item in logger.filters):
        logger.addFilter(_SecretLogFilter())
    logger.setLevel(logging.INFO)

"""HTTP transport for provider calls.

Timeouts, 429s, and 5xx responses become typed errors. Authorization
headers are never included in those errors.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.connectors.authority.redact import safe_http_error


class ProviderError(Exception):
    retryable = False


class ProviderAuthError(ProviderError):
    retryable = False


class ProviderRateLimitError(ProviderError):
    retryable = True

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ProviderTransientError(ProviderError):
    retryable = True


class HttpResponse:
    def __init__(
        self,
        status_code: int,
        payload: Any = None,
        text: str = "",
        headers: Optional[Dict[str, str]] = None,
    ):
        self.status_code = status_code
        self.payload = payload
        self.text = text or ""
        self.headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}

    def json(self) -> Any:
        if self.payload is None:
            raise ValueError("response has no JSON body")
        return self.payload


def quota_status(headers: Dict[str, str]) -> Optional[str]:
    for key in ("x-ratelimit-remaining", "x-rate-limit-remaining", "x-ratelimit-limit"):
        if key in headers:
            limit = headers.get("x-ratelimit-limit") or headers.get("x-rate-limit-limit")
            remaining = headers.get("x-ratelimit-remaining") or headers.get("x-rate-limit-remaining")
            parts = []
            if remaining is not None:
                parts.append(f"remaining={remaining}")
            if limit is not None:
                parts.append(f"limit={limit}")
            return ", ".join(parts) or None
    return None


def _retry_after(headers: Dict[str, str]) -> Optional[float]:
    raw = headers.get("retry-after")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


class HttpxTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Any = None,
        data: Any = None,
        auth: Any = None,
        timeout: Optional[float] = None,
    ) -> HttpResponse:
        from app.core.config import settings
        timeout = timeout if timeout is not None else float(settings.EXTERNAL_PROVIDER_TIMEOUT_SECONDS)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    data=data,
                    auth=auth,
                )
        except httpx.TimeoutException as exc:
            raise ProviderTransientError("provider request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderTransientError("provider request failed") from exc

        text = response.text or ""
        payload = None
        content_type = response.headers.get("content-type", "")
        if "json" in content_type or text[:1] in "{[":
            try:
                payload = response.json()
            except Exception:
                payload = None
        header_map = {k: v for k, v in response.headers.items()}
        result = HttpResponse(response.status_code, payload, text[:4000], header_map)
        if response.status_code == 401:
            raise ProviderAuthError(safe_http_error(response.status_code, text))
        if response.status_code == 429:
            raise ProviderRateLimitError(
                safe_http_error(response.status_code, text),
                retry_after=_retry_after(result.headers),
            )
        if response.status_code >= 500:
            raise ProviderTransientError(safe_http_error(response.status_code, text))
        return result

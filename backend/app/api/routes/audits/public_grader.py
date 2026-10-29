"""Public grader routes.

The scan is unauthenticated, rate-limited, and cached. It returns a bounded
preliminary assessment, not a live AI visibility score.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.orchestration.public_grader import PublicGradeResult, normalize_public_domain, run_public_grade

router = APIRouter(prefix="/public", tags=["Public Grader"])

_WINDOW_SECONDS = 60.0
_MAX_REQUESTS = 8
_CACHE_TTL_SECONDS = 600.0
_CACHE_LIMIT = 200
_hits: dict[str, list[float]] = defaultdict(list)
_cache: dict[str, tuple[float, PublicGradeResult]] = {}
_domain_locks: dict[str, asyncio.Lock] = {}


class PublicGradeRequest(BaseModel):
    domain: str = Field(..., description="Public domain or homepage URL")


def _client_key(request: Request) -> str:
    """Use the socket address unless this process sits behind a trusted proxy.

    A client-supplied X-Forwarded-For header is not a quota key. TRUSTED_PROXY_HOPS
    is the number of proxies this process trusts, counted from the right.
    """
    from app.core.config import settings

    hops = int(getattr(settings, "TRUSTED_PROXY_HOPS", 0) or 0)
    if hops > 0:
        forwarded = request.headers.get("x-forwarded-for", "")
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        client_index = len(parts) - hops - 1
        if parts and client_index >= 0:
            return parts[client_index]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce_grade_quota(client_key: str, now: float | None = None) -> None:
    moment = time.monotonic() if now is None else now
    recent = [stamp for stamp in _hits[client_key] if moment - stamp < _WINDOW_SECONDS]
    if len(recent) >= _MAX_REQUESTS:
        _hits[client_key] = recent
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Public grader quota reached. Try again in a minute.",
        )
    recent.append(moment)
    _hits[client_key] = recent


def reset_public_grader_limits() -> None:
    _hits.clear()
    _cache.clear()
    _domain_locks.clear()


async def _grade(domain: str) -> PublicGradeResult:
    try:
        clean = normalize_public_domain(domain)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    cached = _cache.get(clean)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    lock = _domain_locks.setdefault(clean, asyncio.Lock())
    async with lock:
        cached = _cache.get(clean)
        if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]
        try:
            result = await run_public_grade(clean)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if len(_cache) >= _CACHE_LIMIT:
            oldest = min(_cache, key=lambda key: _cache[key][0])
            _cache.pop(oldest, None)
        _cache[clean] = (time.monotonic(), result)
        return result


@router.post("/grade", response_model=PublicGradeResult)
async def grade_public_website(req: PublicGradeRequest, request: Request):
    """Bounded homepage assessment. Live AI visibility is not measured."""
    enforce_grade_quota(_client_key(request))
    if not req.domain.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Domain is required.")
    return await _grade(req.domain)


@router.get("/grade", response_model=PublicGradeResult)
async def get_grade_public_website(request: Request, domain: str = Query(..., description="Public domain or homepage URL")):
    enforce_grade_quota(_client_key(request))
    if not domain.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Domain is required.")
    return await _grade(domain)


@router.get("/grade/{domain_slug}", response_model=PublicGradeResult)
async def get_cached_grade_by_slug(domain_slug: str, request: Request):
    enforce_grade_quota(_client_key(request))
    return await _grade(domain_slug)

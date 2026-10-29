"""Live HTTP routers.

app.main mounts these through app.api.router.mount_http, once under /api/v1
and once under /api. The modules left directly under app.api.v1 are not mounted.
"""
from fastapi import APIRouter

from app.api.router import _PREFIXED_ROUTERS

LIVE_ROUTERS = _PREFIXED_ROUTERS


def build_router(prefix: str = "/api/v1") -> APIRouter:
    mounted = APIRouter(prefix=prefix)
    for route in LIVE_ROUTERS:
        mounted.include_router(route)
    return mounted


__all__ = ["LIVE_ROUTERS", "build_router"]

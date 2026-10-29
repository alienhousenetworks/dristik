"""Live citation engines for the GEO pillar.

The catalog is the configured gateway list with secrets removed. An engine
with no successful response is not given a citation rate here.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.geo.buyer_surfaces import surfaces_not_queried

_SECRET_KEYS = {"api_key", "api_secret", "token", "authorization"}


def citation_catalog() -> List[Dict[str, Any]]:
    """Return configured engines without credentials."""
    from app.geo.citations.tracker import get_configured_ai_engines

    public: List[Dict[str, Any]] = []
    for engine in get_configured_ai_engines():
        public.append({key: value for key, value in engine.items() if key not in _SECRET_KEYS})
    return public


def active_engine_names() -> List[str]:
    return [str(engine.get("name") or engine.get("id")) for engine in citation_catalog() if engine.get("active")]


def unqueried_surfaces() -> List[str]:
    return surfaces_not_queried(active_engine_names())

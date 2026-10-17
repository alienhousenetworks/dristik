"""Choose the audit book for a section key.

SEO, GEO, AEO, and CRO each keep their own renderer.
"""
from __future__ import annotations

from typing import Any

from app.aeo.reporting import render_aeo_audit_book
from app.cro import render_cro_audit_book
from app.geo.reporting import render_geo_audit_book
from app.seo.reporting import render_seo_audit_book

_RENDERERS = {
    "seo": render_seo_audit_book,
    "geo": render_geo_audit_book,
    "aeo": render_aeo_audit_book,
    "cro": render_cro_audit_book,
}


def render_section_book(section: str, report: Any) -> str:
    renderer = _RENDERERS.get((section or "").strip().lower())
    if renderer is None:
        raise ValueError(f"No audit book is registered for section {section!r}.")
    return renderer(report)

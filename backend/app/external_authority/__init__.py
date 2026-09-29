"""External Authority & Entity Intelligence.

Backlinks, search performance, analytics, business profiles, and brand
mentions are a separate data pillar. They are never inferred from HTML
and never folded into a universal authority score.
"""

from app.external_authority.service import get_service, reset_service

__all__ = ["get_service", "reset_service"]

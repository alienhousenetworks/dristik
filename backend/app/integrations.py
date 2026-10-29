"""
Compatibility re-export package from app.connectors.
Third-party platform integrations are consolidated into backend/app/connectors/.
"""
from __future__ import annotations

import sys
from typing import Any

# Treat this single file module as a package for Python import resolution
__path__: list[str] = []

from app.connectors.google import google_api
from app.connectors.google import google_connectors
from app.connectors.google import google_report
from app.connectors.dataforseo import dataforseo_provider
from app.connectors.google import search_console
from app.connectors.google import analytics
from app.connectors.crux import pagespeed
from app.connectors import ai_engines

# Register compatibility submodules in sys.modules so patch() and direct imports work seamlessly
sys.modules["app.integrations.google_api"] = google_api
sys.modules["app.integrations.google_connectors"] = google_connectors
sys.modules["app.integrations.google_report"] = google_report
sys.modules["app.integrations.dataforseo_provider"] = dataforseo_provider
sys.modules["app.integrations.search_console"] = search_console
sys.modules["app.integrations.analytics"] = analytics
sys.modules["app.integrations.pagespeed"] = pagespeed
sys.modules["app.integrations.ai_engines"] = ai_engines

__all__ = [
    "google_api",
    "google_connectors",
    "google_report",
    "dataforseo_provider",
    "search_console",
    "analytics",
    "pagespeed",
    "ai_engines",
]

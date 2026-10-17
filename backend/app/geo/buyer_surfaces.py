"""Buyer-named answer surfaces that a model API must not impersonate.

Google AI Overviews, Google AI Mode, and Bing Copilot are consumer search
products. A ChatGPT, Gemini, Claude, or Perplexity API response is not one
of those products. The visibility card lists them as not queried unless an
engine row is explicitly that surface.
"""
from __future__ import annotations

from typing import Iterable, List

BUYER_ANSWER_SURFACES: tuple[str, ...] = (
    "Google AI Overviews",
    "Google AI Mode",
    "Bing Copilot",
)

_ALIASES = {
    "google ai overviews": "Google AI Overviews",
    "google aio": "Google AI Overviews",
    "google_aio": "Google AI Overviews",
    "ai overviews": "Google AI Overviews",
    "ai overview": "Google AI Overviews",
    "google ai mode": "Google AI Mode",
    "ai mode": "Google AI Mode",
    "bing copilot": "Bing Copilot",
    "copilot": "Bing Copilot",
    "microsoft copilot": "Bing Copilot",
}


def surfaces_not_queried(engine_names: Iterable[str]) -> List[str]:
    """Return the buyer surfaces that do not appear in the queried engine names."""
    queried = set()
    for name in engine_names:
        key = (name or "").strip().lower()
        if key in _ALIASES:
            queried.add(_ALIASES[key])
    return [surface for surface in BUYER_ANSWER_SURFACES if surface not in queried]

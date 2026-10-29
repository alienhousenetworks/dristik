"""Fit generated SERP copy without chopping a sentence and inventing a period."""
from __future__ import annotations

import re


def fit_serp_text(text: str, limit: int) -> str:
    """Return copy that fits the limit.

    A string that is already short enough is unchanged. A longer string keeps
    the last complete sentence that still uses at least 60% of the limit.
    Otherwise it keeps the last whole word when that word boundary keeps at
    least half the limit. It does not append a period to a fragment.
    """
    cleaned = " ".join((text or "").split())
    if limit <= 0 or len(cleaned) <= limit:
        return cleaned
    window = cleaned[:limit]
    sentence = ""
    for match in re.finditer(r"[.!?]", window):
        if match.end() >= int(limit * 0.6):
            sentence = window[: match.end()].strip()
    if sentence:
        return sentence
    truncated = window.rsplit(" ", 1)[0].strip()
    if truncated and len(truncated) >= int(limit * 0.5):
        return truncated
    return window.strip()

"""A patch suggestion counts only when the after answer states a new fact.

Restating the current page, or saying the fact still cannot be determined,
is the same answer. It does not raise the score or the citation gain.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple


_CITATION_WRAPPER = re.compile(
    r"\[[^\]]+\]|"
    r",?\s*as stated in (?:their|the|its) [^.]{0,80}|"
    r",?\s*according to (?:their|the|its) [^.]{0,80}",
    re.IGNORECASE,
)
_UNANSWERED = re.compile(
    r"cannot determine|cannot answer|not available|not explicitly stated|"
    r"not clearly stated|no direct statements|not stated on",
    re.IGNORECASE,
)
_EXISTING_PAGE = re.compile(
    r"as stated in (?:their|the|its) (?:meta description|title tag|title|homepage|h1)",
    re.IGNORECASE,
)
_PROMISED_NOT_STATED = re.compile(
    r"will be cited|will cite|grounded response will",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    cleaned = _CITATION_WRAPPER.sub(" ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned.strip(" .,;:")


def answers_unchanged(before: Optional[str], after: Optional[str]) -> bool:
    """True when the after text does not add a fact the before text lacked.

    Missing text is not judged here. The caller keeps a stored score when
    either side was never written down.
    """
    if not (before or "").strip() or not (after or "").strip():
        return False
    if _PROMISED_NOT_STATED.search(after or "") and not _EXISTING_PAGE.search(after or ""):
        return True
    if _EXISTING_PAGE.search(after or ""):
        return True
    if _UNANSWERED.search(before or "") and _UNANSWERED.search(after or ""):
        return True
    left = _norm(before or "")
    right = _norm(after or "")
    if not left or not right or left == right:
        return True
    if right.startswith(left) or left.startswith(right):
        extra = right[len(left):].strip(" .,;:") if right.startswith(left) else left[len(right):].strip(" .,;:")
        if not extra or _UNANSWERED.search(extra):
            return True
    return False


def settle_patch_scores(
    before_score: int,
    after_score: Optional[int],
    before_answer: Optional[str],
    after_answer: Optional[str],
    gain: Optional[float],
) -> Tuple[int, int, Optional[float]]:
    """Return after score, delta, and citation gain.

    An unchanged answer keeps the before score and drops the gain.
    """
    if answers_unchanged(before_answer, after_answer) or after_score is None:
        return before_score, 0, None
    delta = int(after_score) - int(before_score)
    if delta <= 0:
        return int(after_score), delta, None
    return int(after_score), delta, gain

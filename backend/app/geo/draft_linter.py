"""
Universal GEO/AEO Draft Fabrication-Risk Linter.

Adapted from GeoLook's MIT-licensed `generate.py:lint_draft` and extended for
Dristik's enterprise evidence contract:
- Rejects placeholder competitor/company names (Tool A, Acme, Competitor X, etc.)
- Flags unverified numerical claims not backed by verified brand facts (unless explicitly marked unconfirmed)
- Flags unsupported guarantees, clinical claims, and superlatives without fact backing
- Flags unconfirmed competitors referenced in customer-facing comparison copy
- Flags stale year references
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence
from pydantic import BaseModel, Field


_PLACEHOLDER_PATTERNS: List[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:acme|foobar|example\s+corp|competitor\s+[a-z0-9]|tool\s+[a-z])\b", re.I), "Placeholder brand or competitor name detected"),
    (re.compile(r"工具\s*[A-Z一二三四五六七八九十]\b"), "Placeholder CN competitor name detected"),
    (re.compile(r"某某|XX公司|xxx公司|示例公司"), "Placeholder CN company name detected"),
]

_GUARANTEE_OR_CLINICAL_RE = re.compile(
    r"\b(?:money-back guarantee|clinically\s+(?:proven|backed|validated)|clinical backing|"
    r"100%\s+guaranteed|fda\s+approved|#1\s+rated|industry[- ]leading|world[- ]leading)\b",
    re.I,
)

_NUMBER_UNIT_RE = re.compile(
    r"[^\n|]*?(\b\d[\d,\.]*\s*(?:%|percent|x\b|hours?|days?|months?|years?|users?|customers?|"
    r"million|billion|k\b|usd|inr|eur|gbp)|(?:\$|₹|€|£)\s*\d[\d,\.]*)[^\n|]*",
    re.I,
)

_UNCONFIRMED_MARKERS = (
    "[confirm_with_brand_facts",
    "[content_required",
    "unconfirmed",
    "tbd",
    "待确认",
    "待补",
)


class DraftLintIssue(BaseModel):
    severity: str  # critical | high | medium | low
    issue_type: str
    detail: str
    excerpt: str


class DraftLintReport(BaseModel):
    status: str  # passed | warnings | rejected
    total_issues: int = 0
    blocking_count: int = 0
    blocking_issues: List[DraftLintIssue] = Field(default_factory=list)
    warnings: List[DraftLintIssue] = Field(default_factory=list)


def lint_draft(
    text: str,
    *,
    verified_numbers: Optional[Iterable[str]] = None,
    verified_facts_text: str = "",
    unconfirmed_competitors: Optional[Sequence[str]] = None,
    current_year: Optional[int] = None,
) -> DraftLintReport:
    """Lint any generated GEO/AEO draft or patch before approval or publishing."""
    body = text or ""
    year = current_year or datetime.now(timezone.utc).year
    known_nums = {str(v).strip().lower() for v in (verified_numbers or []) if str(v).strip()}
    facts_low = (verified_facts_text or "").lower()

    issues: List[DraftLintIssue] = []

    # 1. Placeholder competitor / company names (critical — blocks publishing)
    for pat, desc in _PLACEHOLDER_PATTERNS:
        for m in pat.finditer(body):
            excerpt = body[max(0, m.start() - 30): m.end() + 30].replace("\n", " ").strip()
            issues.append(DraftLintIssue(severity="critical", issue_type="placeholder_entity", detail=desc, excerpt=excerpt))

    # 2. Unconfirmed competitors used in customer-facing drafts (critical)
    for comp in unconfirmed_competitors or []:
        c = (comp or "").strip()
        if not c:
            continue
        pat = re.compile(rf"(?<![A-Za-z0-9]){re.escape(c)}(?![A-Za-z0-9])", re.I)
        m = pat.search(body)
        if m:
            excerpt = body[max(0, m.start() - 30): m.end() + 30].replace("\n", " ").strip()
            issues.append(
                DraftLintIssue(
                    severity="critical",
                    issue_type="unconfirmed_competitor",
                    detail=f"Unconfirmed competitor '{c}' cannot appear in publishable comparison copy until sample-confirmed.",
                    excerpt=excerpt,
                )
            )

    # 3. Unsupported guarantees / clinical / superlative claims (critical if absent from verified facts)
    for m in _GUARANTEE_OR_CLINICAL_RE.finditer(body):
        phrase = m.group(0)
        seg = body[max(0, m.start() - 40): m.end() + 40].replace("\n", " ").strip()
        if any(mk in seg.lower() for mk in _UNCONFIRMED_MARKERS):
            continue
        if phrase.lower() not in facts_low:
            issues.append(
                DraftLintIssue(
                    severity="critical",
                    issue_type="unsupported_claim",
                    detail=f"Claim '{phrase}' has no supporting verified brand fact.",
                    excerpt=seg[:110],
                )
            )

    # 4. Unverified numerical claims (medium warning unless backed by verified_numbers or facts)
    for m in _NUMBER_UNIT_RE.finditer(body):
        seg, val = m.group(0).strip(), m.group(1).strip()
        seg_low = seg.lower()
        val_low = val.lower()
        if any(mk in seg_low for mk in _UNCONFIRMED_MARKERS):
            continue
        if val_low in facts_low or any(val_low in kn or kn in val_low for kn in known_nums):
            continue
        issues.append(
            DraftLintIssue(
                severity="medium",
                issue_type="unverified_number",
                detail=f"Metric '{val}' is not in verified brand facts and not marked unconfirmed.",
                excerpt=seg[:110],
            )
        )

    # 5. Stale year references (low warning for past years >= 2020)
    for m in re.finditer(r"\b(202\d)\b", body):
        found_year = int(m.group(1))
        if 2020 <= found_year < year:
            seg = body[max(0, m.start() - 25): m.end() + 25].replace("\n", " ").strip()
            issues.append(
                DraftLintIssue(
                    severity="low",
                    issue_type="stale_year",
                    detail=f"References past year {found_year} (current year is {year}).",
                    excerpt=seg[:100],
                )
            )

    # Deduplicate identical (issue_type, detail)
    seen: set[tuple[str, str]] = set()
    deduped: List[DraftLintIssue] = []
    for iss in issues:
        k = (iss.issue_type, iss.detail)
        if k not in seen:
            seen.add(k)
            deduped.append(iss)

    blocking = [i for i in deduped if i.severity in ("critical", "high")]
    warnings = [i for i in deduped if i.severity not in ("critical", "high")]
    status = "rejected" if blocking else ("warnings" if warnings else "passed")

    return DraftLintReport(
        status=status,
        total_issues=len(deduped),
        blocking_count=len(blocking),
        blocking_issues=blocking,
        warnings=warnings,
    )

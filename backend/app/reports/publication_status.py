"""
Canonical 6-Tier Publication Verification Standard for Dristik Reports.

Classifies every audit finding into one of six transparent verification states
so reports never claim "AI-Verified" unless 100% of published findings passed
both independent AI critic review and evidence validation.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


STATUS_AI_EVIDENCE_VERIFIED = "AI + evidence verified"
STATUS_AI_REVIEWED = "AI reviewed"
STATUS_RULE_VERIFIED = "Rule verified"
STATUS_INFERRED = "Inferred"
STATUS_PENDING_VERIFICATION = "Pending verification"
STATUS_UNAVAILABLE = "Unavailable"

ALL_PUBLICATION_STATUSES = (
    STATUS_AI_EVIDENCE_VERIFIED,
    STATUS_AI_REVIEWED,
    STATUS_RULE_VERIFIED,
    STATUS_INFERRED,
    STATUS_PENDING_VERIFICATION,
    STATUS_UNAVAILABLE,
)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def _has_evidence(finding: Any) -> bool:
    for field in ("evidence_refs", "evidence_urls", "affected_urls", "evidence", "raw_evidence"):
        val = _get(finding, field)
        if isinstance(val, (list, tuple, set)) and len(val) > 0:
            return True
        if isinstance(val, dict) and len(val) > 0:
            return True
        if isinstance(val, str) and val.strip():
            return True
    return False


def classify_finding_status(finding: Any) -> str:
    """Classify a single finding into the 6-tier publication verification taxonomy."""
    raw_st = _get(finding, "verification_status", "")
    st = str(getattr(raw_st, "value", raw_st) or "").strip().lower()
    notes = str(_get(finding, "verification_notes", "") or "").lower()
    adv_reviewed = bool(_get(finding, "adversarial_reviewed", False))
    ai_confirmed = adv_reviewed or ("[ai review: confirmed]" in notes) or ("[ai review: downgraded]" in notes)
    has_ev = _has_evidence(finding)

    if st in {"unavailable", "not_measured", "data_unavailable", "not_connected"}:
        return STATUS_UNAVAILABLE

    if st in {"pending_verification", "provisional", "single_source_unverified", "insufficient_evidence", "contested"}:
        return STATUS_PENDING_VERIFICATION

    if "not evaluated in critic pass" in notes or "remains pending verification" in notes:
        return STATUS_PENDING_VERIFICATION

    if st in {"inferred", "derived", "hypothesis"}:
        return STATUS_INFERRED

    if ai_confirmed:
        return STATUS_AI_EVIDENCE_VERIFIED if has_ev else STATUS_AI_REVIEWED

    if st in {"verified", "partially_verified", "sample_verified"}:
        return STATUS_RULE_VERIFIED if has_ev else STATUS_PENDING_VERIFICATION

    return STATUS_PENDING_VERIFICATION


@dataclass(frozen=True)
class PublicationVerificationSummary:
    total_findings: int
    counts: Dict[str, int]
    is_fully_ai_verified: bool
    publication_label: str
    disclosure_note: str


def summarize_publication_verification(findings: Iterable[Any]) -> PublicationVerificationSummary:
    """Aggregate findings into the 6-tier publication summary with strict AI-verified gating."""
    items = list(findings or [])
    counts: Dict[str, int] = {status: 0 for status in ALL_PUBLICATION_STATUSES}
    for f in items:
        counts[classify_finding_status(f)] += 1

    total = len(items)
    ai_ev = counts[STATUS_AI_EVIDENCE_VERIFIED]
    pending = counts[STATUS_PENDING_VERIFICATION]
    rule_ver = counts[STATUS_RULE_VERIFIED]

    if total > 0 and ai_ev == total:
        is_fully = True
        label = "AI + Evidence Verified"
        note = f"All {total} published findings passed independent AI critic review and evidence validation."
    elif total == 0:
        is_fully = False
        label = "No Findings Recorded"
        note = "No findings were recorded in this audit snapshot."
    else:
        is_fully = False
        parts: List[str] = []
        for st in ALL_PUBLICATION_STATUSES:
            if counts[st] > 0:
                parts.append(f"{counts[st]} {st}")
        label = "Mixed Verification — Exceptions Disclosed"
        note = (
            f"Not all findings completed independent AI critic verification ({ai_ev}/{total} AI + evidence verified; "
            f"{rule_ver} rule verified; {pending} pending verification). Breakdown: " + " · ".join(parts) + "."
        )

    return PublicationVerificationSummary(
        total_findings=total,
        counts=counts,
        is_fully_ai_verified=is_fully,
        publication_label=label,
        disclosure_note=note,
    )


def render_verification_standard_banner(
    findings: Iterable[Any],
    *,
    narrative_mode: Optional[str] = None,
) -> str:
    """Render a compact HTML verification governance panel for executive summaries."""
    summary = summarize_publication_verification(findings)
    badge_color = "#15803d" if summary.is_fully_ai_verified else "#b45309"
    narr_disp = str(narrative_mode or "unknown").strip()

    pill_colors = {
        STATUS_AI_EVIDENCE_VERIFIED: "#15803d",
        STATUS_AI_REVIEWED: "#0284c7",
        STATUS_RULE_VERIFIED: "#0f766e",
        STATUS_INFERRED: "#7c3aed",
        STATUS_PENDING_VERIFICATION: "#b45309",
        STATUS_UNAVAILABLE: "#64748b",
    }

    cells = []
    for st in ALL_PUBLICATION_STATUSES:
        c = pill_colors[st]
        cnt = summary.counts[st]
        cells.append(
            f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-top:2.5px solid {c};'
            f'border-radius:4px;padding:6px 8px;">'
            f'<div style="font-size:7pt;font-weight:700;color:#64748b;text-transform:uppercase;">{_esc(st)}</div>'
            f'<div style="font-size:12pt;font-weight:800;color:{c};margin-top:2px;">{cnt}</div>'
            f'</div>'
        )

    return (
        f'<div class="verification-standard-banner" style="background:#f8fafc;border:1px solid #cbd5e1;'
        f'border-left:4px solid {badge_color};border-radius:6px;padding:10px 14px;margin:10px 0 16px 0;break-inside:avoid;">'
        f'  <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:6px;">'
        f'    <span style="font-size:8.5pt;font-weight:800;letter-spacing:0.06em;color:#0f172a;text-transform:uppercase;">'
        f'      PUBLICATION VERIFICATION STANDARD // {_esc(summary.publication_label)}'
        f'    </span>'
        f'    <span style="font-family:ui-monospace,monospace;font-size:7.5pt;color:#475569;">'
        f'      NARRATIVE MODE: {_esc(narr_disp)}'
        f'    </span>'
        f'  </div>'
        f'  <p style="font-size:8pt;color:#334155;margin:0 0 8px 0;line-height:1.45;">{_esc(summary.disclosure_note)}</p>'
        f'  <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;">{"".join(cells)}</div>'
        f'</div>'
    )

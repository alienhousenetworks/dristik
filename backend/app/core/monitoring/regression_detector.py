"""
Continuous assurance across sealed audit runs.

Compares this crawl with earlier snapshots of the same domain.
Does not invent prior runs, scores, schema, or degradation items.
"""
from datetime import datetime, timezone
import hashlib
from typing import Dict, Any, List, Optional

from app.domain.models import (
    AuditSnapshot,
    RegressionItem,
    RegressionReport,
    Finding,
    OverallScoreResult,
)
from app.domain.enums import Category


# Canned chain previously injected when a domain had no history.
_DEMO_SEALS = {
    "sha256:7f3a8b291c4e09f",
    "sha256:9b1c4e820f17a32",
    "sha256:4d8e72f91a3c650",
}
_DEMO_RUNS = {("Sep 24", 27.0), ("Oct 02", 61.0)}

_CATEGORY_LABELS = {
    Category.AI_SEARCH.value: "AI answerability",
    Category.TECHNICAL_SEO.value: "Technical SEO",
    Category.CONTENT.value: "Content quality",
    Category.GEO.value: "GEO visibility",
    Category.SCHEMA.value: "Schema markup",
    Category.UX_CONVERSION.value: "UX & conversion",
    Category.ON_PAGE_SEO.value: "On-page SEO",
    Category.TRUST_AUTHORITY.value: "Trust authority",
}


def _parse_snapshot_day(date_str: str, now: datetime) -> Optional[datetime]:
    text = (date_str or "").strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        month_day = datetime.strptime(f"{text} {now.year}", "%b %d %Y")
    except ValueError:
        return None
    today = now.date()
    if month_day.date() > today and (month_day.date() - today).days > 120:
        return month_day.replace(year=now.year - 1)
    return month_day


def _is_simulated_snapshot(snap: AuditSnapshot, now: datetime) -> bool:
    """Drop the old demo chain and any snapshot dated after today."""
    if (snap.evidence_seal or "") in _DEMO_SEALS:
        return True
    try:
        score = float(snap.score)
    except (TypeError, ValueError):
        score = None
    if score is not None and (snap.date, score) in _DEMO_RUNS:
        return True
    parsed = _parse_snapshot_day(snap.date, now)
    if parsed is None:
        return False
    return parsed.date() > now.date()


def _schema_types_from_ledger(evidence_ledger: Dict[str, Any]) -> List[str]:
    """Schema.org types recorded by the schema analyzer. Body copy is not schema."""
    found: List[str] = []
    for item in evidence_ledger.values():
        if not isinstance(item, dict):
            continue
        analyzer = str(item.get("analyzer") or "")
        source = str(item.get("source_type") or "")
        if analyzer != "schema_analyzer" and source != "schema":
            continue
        value = item.get("value")
        if isinstance(value, dict) and isinstance(value.get("schema_types"), list):
            found.extend(str(t).strip() for t in value["schema_types"] if str(t).strip())
            continue
        text = str(item.get("text") or "")
        prefix = "Detected Schema.org Entity Types:"
        if text.startswith(prefix):
            found.extend(part.strip() for part in text[len(prefix):].split(",") if part.strip())
    unique: List[str] = []
    for name in found:
        if name not in unique:
            unique.append(name)
    return unique


def _evidence_seal(snapshot_id: str, domain: str, score: float) -> str:
    if snapshot_id.startswith(("snap_", "sha256:")):
        return snapshot_id
    if snapshot_id:
        digest = hashlib.sha256(snapshot_id.encode()).hexdigest()
        return f"sha256:{digest}"
    digest = hashlib.sha256(f"{domain}:{score}".encode()).hexdigest()
    return f"sha256:{digest}"


class RegressionDetector:
    """
    Compares the current sealed audit with prior sealed audits of the same domain.
    """

    def evaluate_audit_run(
        self,
        domain: str,
        current_scores: OverallScoreResult,
        findings: List[Finding],
        evidence_ledger: Dict[str, Any],
        snapshot_id: str,
        historical_snapshots: Optional[List[AuditSnapshot]] = None,
    ) -> RegressionReport:
        now = datetime.now(timezone.utc)
        current_score = round(float(current_scores.overall_score), 1) if current_scores and current_scores.overall_score is not None else 0.0

        current_cat_scores: Dict[str, float] = {}
        for key, value in (current_scores.category_scores or {}).items():
            if value and getattr(value, "score", None) is not None:
                current_cat_scores[key] = round(float(value.score), 1)
            else:
                current_cat_scores[key] = 0.0

        current_schema_types = _schema_types_from_ledger(evidence_ledger or {})
        timeline = [
            snap for snap in (historical_snapshots or [])
            if not _is_simulated_snapshot(snap, now)
        ]

        run_number = len(timeline) + 1
        current_snapshot = AuditSnapshot(
            snapshot_id=snapshot_id or f"snap_{domain}_{run_number:03d}",
            run_label=f"Run #{run_number:03d}",
            date=now.strftime("%b %d, %Y"),
            score=current_score,
            category_scores=current_cat_scores,
            evidence_seal=_evidence_seal(snapshot_id or "", domain, current_score),
            verified_schema_types=current_schema_types,
            findings_count=len(findings),
            status="HEALTHY",
        )

        regressions: List[RegressionItem] = []
        baseline_run: Optional[AuditSnapshot] = timeline[-1] if timeline else None
        score_delta = 0.0

        if baseline_run is not None:
            score_delta = round(current_score - baseline_run.score, 1)
            removed = [
                name for name in baseline_run.verified_schema_types
                if name not in current_schema_types
            ]
            for name in removed:
                regressions.append(
                    RegressionItem(
                        severity="HIGH",
                        title=f"{name} schema removed",
                        category="SCHEMA",
                        description=(
                            f"{name} JSON-LD was recorded on {baseline_run.run_label} "
                            f"({baseline_run.date}) and was not in this crawl."
                        ),
                    )
                )

            for cat_key, current_val in current_cat_scores.items():
                if cat_key not in baseline_run.category_scores:
                    continue
                base_val = baseline_run.category_scores[cat_key]
                delta = round(current_val - base_val, 1)
                if delta > -2.0:
                    continue
                label = _CATEGORY_LABELS.get(cat_key, cat_key.replace("_", " ").title())
                if delta <= -8.0:
                    severity = "CRITICAL"
                elif delta <= -5.0:
                    severity = "HIGH"
                else:
                    severity = "MEDIUM"
                regressions.append(
                    RegressionItem(
                        severity=severity,
                        title=f"{label} ↓ {abs(int(delta))}",
                        category=cat_key,
                        dimension_delta=delta,
                        description=(
                            f"{label} moved from {base_val:g} to {current_val:g} "
                            f"({delta:+.1f} pts) since {baseline_run.run_label}."
                        ),
                    )
                )

            if score_delta < 0:
                current_snapshot.status = "REGRESSION"
            elif score_delta > 0:
                current_snapshot.status = "IMPROVED"
            else:
                current_snapshot.status = "HEALTHY"

        has_regression = score_delta < 0 or len(regressions) > 0
        full_timeline = timeline + [current_snapshot]

        if baseline_run is None:
            summary = (
                "First sealed audit for this domain. "
                "No earlier snapshot was measured, so there is no regression to report."
            )
        elif has_regression:
            summary = (
                f"{len(regressions)} measured drop(s) since {baseline_run.run_label}. "
                f"Overall score {score_delta:+.1f} pts."
            )
        else:
            summary = (
                f"No measured drop since {baseline_run.run_label}. "
                f"Overall score {score_delta:+.1f} pts."
            )

        return RegressionReport(
            has_regression=has_regression,
            regression_count=len(regressions),
            score_delta=score_delta,
            baseline_run=baseline_run,
            current_run=current_snapshot,
            regressions=regressions,
            historical_timeline=full_timeline,
            summary=summary,
            detected_at=now.isoformat(),
        )


regression_detector = RegressionDetector()

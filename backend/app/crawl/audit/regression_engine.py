"""
Continuous Change Detection & Regression Engine.
Compares Audit N against baseline Audit N-1 to detect structural DOM drift,
schema drops, score regressions, and broken canonicals.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class RegressionAlert:
    alert_type: str  # SCORE_DROP, SCHEMA_DROPPED, TITLE_CHANGED, CANONICAL_DRIFT, HTTP_STATUS_CHANGED
    severity: str    # CRITICAL, HIGH, MEDIUM, LOW
    url: Optional[str]
    message: str
    previous_val: Any
    current_val: Any


@dataclass
class AuditComparisonResult:
    audit_n_id: str
    audit_baseline_id: str
    overall_score_delta: int
    category_deltas: Dict[str, int]
    pages_added: List[str]
    pages_removed: List[str]
    schema_types_dropped: List[str]
    schema_types_added: List[str]
    alerts: List[RegressionAlert] = field(default_factory=list)


class AuditRegressionEngine:
    """
    Analyzes differences between current audit data and historical baseline.
    """

    def compare_audits(
        self,
        current_audit: Dict[str, Any],
        baseline_audit: Dict[str, Any]
    ) -> AuditComparisonResult:
        c_score = current_audit.get("overall_score") or 0
        b_score = baseline_audit.get("overall_score") or 0
        overall_delta = c_score - b_score

        alerts: List[RegressionAlert] = []

        # 1. Overall Score Regression
        if overall_delta <= -5:
            alerts.append(RegressionAlert(
                alert_type="SCORE_DROP",
                severity="CRITICAL" if overall_delta <= -10 else "HIGH",
                url=None,
                message=f"Overall health score dropped by {abs(overall_delta)} points (from {b_score} to {c_score}).",
                previous_val=b_score,
                current_val=c_score,
            ))

        # 2. Category Deltas
        c_cats = current_audit.get("category_scores") or {}
        b_cats = baseline_audit.get("category_scores") or {}
        cat_deltas = {}
        for cat, c_val in c_cats.items():
            b_val = b_cats.get(cat, c_val)
            delta = c_val - b_val
            cat_deltas[cat] = delta
            if delta <= -8:
                alerts.append(RegressionAlert(
                    alert_type="CATEGORY_SCORE_DROP",
                    severity="HIGH",
                    url=None,
                    message=f"Category '{cat}' regressed by {abs(delta)} points.",
                    previous_val=b_val,
                    current_val=c_val,
                ))

        # 3. Page Differences
        c_pages = {p.get("url"): p for p in current_audit.get("pages", []) if p.get("url")}
        b_pages = {p.get("url"): p for p in baseline_audit.get("pages", []) if p.get("url")}

        pages_added = [u for u in c_pages if u not in b_pages]
        pages_removed = [u for u in b_pages if u not in c_pages]

        # 4. Page-level structural changes
        common_urls = set(c_pages.keys()).intersection(set(b_pages.keys()))
        for url in common_urls:
            c_p = c_pages[url]
            b_p = b_pages[url]

            # HTTP Status Changes
            if c_p.get("status_code") != b_p.get("status_code"):
                alerts.append(RegressionAlert(
                    alert_type="HTTP_STATUS_CHANGED",
                    severity="CRITICAL" if (c_p.get("status_code") or 200) >= 400 else "MEDIUM",
                    url=url,
                    message=f"Status code changed from {b_p.get('status_code')} to {c_p.get('status_code')}",
                    previous_val=b_p.get("status_code"),
                    current_val=c_p.get("status_code"),
                ))

            # Title Changes
            if c_p.get("title") != b_p.get("title") and b_p.get("title"):
                alerts.append(RegressionAlert(
                    alert_type="TITLE_CHANGED",
                    severity="LOW",
                    url=url,
                    message=f"Title updated on {url}",
                    previous_val=b_p.get("title"),
                    current_val=c_p.get("title"),
                ))

            # Canonical Drift
            if b_p.get("canonical") and not c_p.get("canonical"):
                alerts.append(RegressionAlert(
                    alert_type="CANONICAL_DRIFT",
                    severity="HIGH",
                    url=url,
                    message=f"Canonical link tag was removed from {url}",
                    previous_val=b_p.get("canonical"),
                    current_val=None,
                ))

        # 5. Schema Drift
        c_schemas = set(current_audit.get("schema_types") or [])
        b_schemas = set(baseline_audit.get("schema_types") or [])
        schema_types_dropped = list(b_schemas - c_schemas)
        schema_types_added = list(c_schemas - b_schemas)

        for dropped in schema_types_dropped:
            alerts.append(RegressionAlert(
                alert_type="SCHEMA_DROPPED",
                severity="HIGH",
                url=None,
                message=f"Structured schema '@type': '{dropped}' was present in baseline but missing in current audit.",
                previous_val=dropped,
                current_val=None,
            ))

        return AuditComparisonResult(
            audit_n_id=current_audit.get("audit_id", "current"),
            audit_baseline_id=baseline_audit.get("audit_id", "baseline"),
            overall_score_delta=overall_delta,
            category_deltas=cat_deltas,
            pages_added=pages_added,
            pages_removed=pages_removed,
            schema_types_dropped=schema_types_dropped,
            schema_types_added=schema_types_added,
            alerts=alerts,
        )


_global_regression_engine: Optional[AuditRegressionEngine] = None


def get_regression_engine() -> AuditRegressionEngine:
    global _global_regression_engine
    if _global_regression_engine is None:
        _global_regression_engine = AuditRegressionEngine()
    return _global_regression_engine

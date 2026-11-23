"""
Unified Cross-Pillar Root-Cause Correlator & 34-Criterion Enterprise Readiness Evaluator.

Links related defects across SEO, GEO, AEO, and CRO on shared URLs/entities into
one coordinated optimization plan with per-pillar acceptance criteria.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence
from urllib.parse import urlsplit
from pydantic import BaseModel, Field


class CoordinatedOptimizationPlan(BaseModel):
    plan_id: str
    shared_url: str
    pillars_involved: List[str]
    linked_finding_ids: List[str]
    root_cause_summary: str
    coordinated_action: str
    acceptance_criteria_by_pillar: Dict[str, List[str]] = Field(default_factory=dict)


def _norm_path(url: str) -> str:
    if not url:
        return "/"
    p = urlsplit(url.strip().lower()).path or "/"
    return p.rstrip("/") or "/"


class CrossPillarCorrelator:
    """Correlates SEO, GEO, AEO, and CRO findings sharing the same URL into coordinated plans."""

    @classmethod
    def correlate(cls, findings: Sequence[Dict[str, Any]]) -> List[CoordinatedOptimizationPlan]:
        by_path: Dict[str, List[Dict[str, Any]]] = {}
        for f in findings:
            urls = f.get("affected_urls") or ([f["url"]] if f.get("url") else [])
            for u in urls:
                by_path.setdefault(_norm_path(str(u)), []).append(f)

        plans: List[CoordinatedOptimizationPlan] = []
        idx = 1
        for path, group in sorted(by_path.items(), key=lambda kv: -len(kv[1])):
            pillars = sorted({str(g.get("pillar") or "SEO").upper() for g in group})
            if len(pillars) < 2:
                continue
            fids = [str(g.get("finding_id") or f"F-{i}") for i, g in enumerate(group, start=1)]
            criteria: Dict[str, List[str]] = {}
            for g in group:
                p = str(g.get("pillar") or "SEO").upper()
                ac = str(g.get("acceptance_criteria") or g.get("recommendation") or f"Verify {g.get('title', 'defect')} resolved.")
                criteria.setdefault(p, []).append(ac)

            titles = "; ".join(str(g.get("title") or "") for g in group[:4] if g.get("title"))
            plans.append(
                CoordinatedOptimizationPlan(
                    plan_id=f"XPLAN-{idx:03d}",
                    shared_url=path,
                    pillars_involved=pillars,
                    linked_finding_ids=fids,
                    root_cause_summary=f"Connected {', '.join(pillars)} defects on '{path}': {titles}",
                    coordinated_action=(
                        f"Execute one coordinated release on '{path}' addressing all {len(fids)} linked "
                        f"issues across {', '.join(pillars)}, then verify each pillar's acceptance criteria independently."
                    ),
                    acceptance_criteria_by_pillar=criteria,
                )
            )
            idx += 1
        return plans


ENTERPRISE_34_CRITERIA: List[Dict[str, str]] = [
    # 1. Data and measurement (6)
    {"id": "DM-01", "group": "Data and measurement", "label": "GSC and GA4 connected and tested"},
    {"id": "DM-02", "group": "Data and measurement", "label": "Backlink provider connected and tested"},
    {"id": "DM-03", "group": "Data and measurement", "label": "CRM and ecommerce revenue reconciliation"},
    {"id": "DM-04", "group": "Data and measurement", "label": "AI referral analytics operational"},
    {"id": "DM-05", "group": "Data and measurement", "label": "Consent-aware event ingestion"},
    {"id": "DM-06", "group": "Data and measurement", "label": "Historical data retention and freshness"},
    # 2. SEO, GEO and AEO (7)
    {"id": "SGA-01", "group": "SEO, GEO and AEO", "label": "Full-site crawl coverage reporting"},
    {"id": "SGA-02", "group": "SEO, GEO and AEO", "label": "Technical and structured-data validation"},
    {"id": "SGA-03", "group": "SEO, GEO and AEO", "label": "AI crawler access and rendering checks"},
    {"id": "SGA-04", "group": "SEO, GEO and AEO", "label": "Actual AI prompt execution"},
    {"id": "SGA-05", "group": "SEO, GEO and AEO", "label": "Citation and brand mention tracking"},
    {"id": "SGA-06", "group": "SEO, GEO and AEO", "label": "Competitor citation comparisons"},
    {"id": "SGA-07", "group": "SEO, GEO and AEO", "label": "Historical search and AI visibility"},
    # 3. CRO and experimentation (7)
    {"id": "CRO-01", "group": "CRO and experimentation", "label": "Session recordings operational"},
    {"id": "CRO-02", "group": "CRO and experimentation", "label": "Click and scroll heatmaps operational"},
    {"id": "CRO-03", "group": "CRO and experimentation", "label": "Behavioural funnel analysis"},
    {"id": "CRO-04", "group": "CRO and experimentation", "label": "Form abandonment analysis"},
    {"id": "CRO-05", "group": "CRO and experimentation", "label": "Revenue attribution"},
    {"id": "CRO-06", "group": "CRO and experimentation", "label": "Controlled A/B experiments"},
    {"id": "CRO-07", "group": "CRO and experimentation", "label": "Statistical validation and guardrails"},
    # 4. Execution and governance (8)
    {"id": "EG-01", "group": "Execution and governance", "label": "Evidence-backed remediation"},
    {"id": "EG-02", "group": "Execution and governance", "label": "Human approval and deployment tracking"},
    {"id": "EG-03", "group": "Execution and governance", "label": "Automated before/after verification"},
    {"id": "EG-04", "group": "Execution and governance", "label": "Regression detection"},
    {"id": "EG-05", "group": "Execution and governance", "label": "Finding lifecycle management"},
    {"id": "EG-06", "group": "Execution and governance", "label": "Historical audit comparisons"},
    {"id": "EG-07", "group": "Execution and governance", "label": "Tenant isolation and role permissions"},
    {"id": "EG-08", "group": "Execution and governance", "label": "Security, privacy and audit logging"},
    # 5. Reporting (6)
    {"id": "REP-01", "group": "Reporting", "label": "Transparent coverage and confidence"},
    {"id": "REP-02", "group": "Reporting", "label": "No fabricated or inferred measurements presented as facts"},
    {"id": "REP-03", "group": "Reporting", "label": "Consistent methodology and scoring"},
    {"id": "REP-04", "group": "Reporting", "label": "Cross-pillar intelligence"},
    {"id": "REP-05", "group": "Reporting", "label": "Executive and technical reporting"},
    {"id": "REP-06", "group": "Reporting", "label": "Actual versus expected business impact"},
]


def evaluate_34_readiness_tracker(passed_ids: Sequence[str]) -> Dict[str, Any]:
    passed_set = set(passed_ids)
    items = [
        {**item, "passed": item["id"] in passed_set}
        for item in ENTERPRISE_34_CRITERIA
    ]
    total = len(items)
    done = sum(1 for i in items if i["passed"])
    return {
        "total_criteria": total,
        "completed_criteria": done,
        "completion_pct": round((done / total) * 100.0, 1) if total else 0.0,
        "items": items,
        "note": "Implementation & acceptance readiness tracker — distinct from audited website health score.",
    }

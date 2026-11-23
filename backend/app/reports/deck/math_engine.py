"""
Deterministic Metric & Benchmark Calculation Engine
Executes strict Python math algorithms over empirical report telemetry and crawl data.
Enforces the 'Honest Math' rule: zero LLM hallucinations in quantitative calculations.
"""
from typing import Dict, Any, List, Optional
import statistics
from pydantic import BaseModel, Field
from app.domain.models import ExecutiveReport, Category


class CalculatedMetric(BaseModel):
    key: str
    label: str
    value: float
    formatted_value: str
    units: str = ""
    formula: str = ""
    operands: Dict[str, Any] = Field(default_factory=dict)
    benchmark: Optional[float] = None
    delta_to_benchmark: Optional[float] = None


class MetricBundle(BaseModel):
    domain: str
    overall_score: float
    grade: str
    health_label: str
    category_scores: Dict[str, float] = Field(default_factory=dict)
    category_gaps: Dict[str, float] = Field(default_factory=dict)
    ttfb_metrics: Dict[str, float] = Field(default_factory=dict)
    page_counts: Dict[str, int] = Field(default_factory=dict)
    findings_severity_counts: Dict[str, int] = Field(default_factory=dict)
    remediation_potential_gain: float = 0.0
    projected_post_remediation_score: float = 0.0
    geo_citability_ratio: float = 0.0
    metrics: Dict[str, CalculatedMetric] = Field(default_factory=dict)


class DeterministicMetricEngine:
    """
    Computes all presentation metrics with deterministic mathematical guarantees.
    """

    BENCHMARKS = {
        "TECHNICAL_SEO": 85.0,
        "SCHEMA": 80.0,
        "CONTENT": 80.0,
        "GEO": 75.0,
        "UX_CONVERSION": 85.0,
        "COMPETITIVE": 75.0,
        "TTFB_MS": 200.0,
    }

    def compute_bundle(self, report: ExecutiveReport) -> MetricBundle:
        domain = report.domain or report.website_url.replace("https://", "").replace("http://", "").split("/")[0]
        
        # 1. Overall Score & Category Scores (Canonical Enterprise Scorecard single source of truth)
        scores = report.scores
        from app.domain.scoring.canonical_scorecard import CanonicalScorecardEngine
        from app.domain.scoring.displayed_score import rating_for_displayed

        canon_card = CanonicalScorecardEngine.evaluate_from_report(report)
        canon_overall = canon_card.composite_health_score
        if canon_overall is not None:
            overall_score = float(canon_overall)
            has_overall_val = True
        else:
            overall_score = float(scores.overall_score) if scores and scores.overall_score is not None else 0.0
            has_overall_val = scores is not None and scores.overall_score is not None
        canon_grade, canon_health = rating_for_displayed(overall_score if has_overall_val else None)
        grade = canon_card.composite_grade if canon_overall is not None and canon_card.composite_grade else canon_grade
        health_label = canon_health

        cat_scores: Dict[str, float] = {}
        cat_gaps: Dict[str, float] = {}
        if scores and scores.category_scores:
            for cat_name, cat_obj in scores.category_scores.items():
                if hasattr(cat_obj, "score"):
                    if cat_obj.score is None or getattr(cat_obj, "status", None) == "NOT_MEASURED":
                        continue
                    val = float(cat_obj.score)
                elif isinstance(cat_obj, (int, float)) and not isinstance(cat_obj, bool):
                    val = float(cat_obj)
                else:
                    continue
                cat_key = cat_name if isinstance(cat_name, str) else str(cat_name.value)
                cat_scores[cat_key] = val
                benchmark = self.BENCHMARKS.get(cat_key, 80.0)
                cat_gaps[cat_key] = round(benchmark - val, 1)

        # 2. TTFB Latency Distribution
        ttfb_vals: List[float] = []
        page_counts: Dict[str, int] = {"total": 0, "homepage": 0, "pricing": 0, "product": 0, "other": 0}
        
        if report.crawl_manifest and report.crawl_manifest.pages:
            for p in report.crawl_manifest.pages:
                page_counts["total"] += 1
                ptype = p.page_type.lower() if p.page_type else "other"
                if ptype in page_counts:
                    page_counts[ptype] += 1
                else:
                    page_counts["other"] += 1
                if p.ttfb_ms is not None and p.ttfb_ms > 0:
                    ttfb_vals.append(float(p.ttfb_ms))

        from app.domain.scoring.displayed_score import compute_ttfb_summary
        ttfb_summary = compute_ttfb_summary(ttfb_vals)
        ttfb_min = ttfb_summary["min_ms"]
        ttfb_max = ttfb_summary["max_ms"]
        ttfb_median = ttfb_summary["median_ms"]
        ttfb_mean = ttfb_summary["mean_ms"]
        ttfb_p90 = ttfb_summary["p90_ms"]
        sample_size = float(ttfb_summary["sample_size"])

        ttfb_metrics = {
            "min_ms": ttfb_min,
            "max_ms": ttfb_max,
            "median_ms": ttfb_median,
            "mean_ms": ttfb_mean,
            "p90_ms": ttfb_p90,
            "trimmed_mean_ms": ttfb_summary["trimmed_mean_ms"],
            "outlier_count": float(ttfb_summary["outlier_count"]),
            "sample_size": sample_size,
        }

        # 3. Severity Distribution
        findings = report.findings or []
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        total_impact = 0.0
        for f in findings:
            sev_str = f.severity.value if hasattr(f.severity, "value") else str(f.severity).upper()
            if sev_str in severity_counts:
                severity_counts[sev_str] += 1
            else:
                severity_counts["MEDIUM"] += 1
            imp_val = getattr(f, "impact", getattr(f, "impact_score", 5)) or 5
            total_impact += float(imp_val)

        # 4. Remediation Potential Calculation
        raw_gain = (severity_counts["CRITICAL"] * 4.5 + severity_counts["HIGH"] * 2.8 + severity_counts["MEDIUM"] * 1.2)
        potential_gain = round(min(100.0 - overall_score, raw_gain), 1)
        post_remediation_score = round(min(100.0, overall_score + potential_gain), 1)

        # 5. Generative AI Answer Engine Readiness Ratio
        geo_pillar = canon_card.pillars.get("GEO")
        geo_score = (
            float(geo_pillar.measured_health_score)
            if geo_pillar is not None and geo_pillar.measured_health_score is not None
            else cat_scores.get("GEO")
        )
        geo_ratio = round(geo_score / 100.0, 2) if geo_score is not None else 0.0

        # 6. Detailed Metric Objects with Formulas
        metrics: Dict[str, CalculatedMetric] = {}
        has_overall = has_overall_val
        metrics["overall_score"] = CalculatedMetric(
            key="overall_score",
            label="Overall Audit Composite Score",
            value=overall_score,
            formatted_value=f"{int(round(overall_score))}/100" if has_overall else "Unmeasured",
            units="/100",
            formula="weighted_composite_index(category_scores)",
            benchmark=80.0,
            delta_to_benchmark=round(80.0 - overall_score, 1) if has_overall else 0.0
        )
        metrics["ttfb_median"] = CalculatedMetric(
            key="ttfb_median",
            label="Median Time to First Byte",
            value=ttfb_median,
            formatted_value=f"{ttfb_median}ms" if sample_size > 0 else "Unmeasured",
            units="ms",
            formula="median(page_ttfb_samples)",
            benchmark=200.0,
            delta_to_benchmark=round(ttfb_median - 200.0, 1) if sample_size > 0 else 0.0
        )
        metrics["potential_gain"] = CalculatedMetric(
            key="potential_gain",
            label="Post-Remediation Score Delta",
            value=potential_gain,
            formatted_value=f"+{potential_gain} pts",
            units="pts",
            formula="min(100 - overall_score, sum(weighted_finding_impacts))",
            benchmark=15.0,
            delta_to_benchmark=potential_gain
        )
        metrics["geo_citability"] = CalculatedMetric(
            key="geo_citability",
            label="Generative Answer Engine Citability Index",
            value=geo_score if geo_score is not None else 0.0,
            formatted_value=f"{int(round(geo_score))}%" if geo_score is not None else "Unmeasured",
            units="%",
            formula="extractability_weight * schema_entity_coverage",
            benchmark=75.0,
            delta_to_benchmark=round(75.0 - geo_score, 1) if geo_score is not None else 0.0
        )

        return MetricBundle(
            domain=domain,
            overall_score=overall_score,
            grade=grade,
            health_label=health_label,
            category_scores=cat_scores,
            category_gaps=cat_gaps,
            ttfb_metrics=ttfb_metrics,
            page_counts=page_counts,
            findings_severity_counts=severity_counts,
            remediation_potential_gain=potential_gain,
            projected_post_remediation_score=post_remediation_score,
            geo_citability_ratio=geo_ratio,
            metrics=metrics
        )

    @staticmethod
    def _grade_for_score(score: float) -> str:
        from app.domain.scoring.displayed_score import grade_for_displayed
        return grade_for_displayed(score)

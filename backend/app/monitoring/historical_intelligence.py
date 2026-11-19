"""Phase 10.4: Historical Intelligence and Trendline Engine.

Analyzes longitudinal shifts across audit runs:
- Technical score changes
- SEO improvements
- GEO visibility changes
- AEO answer coverage changes
- CRO experience changes
- Competitor displacement
- Citation changes
- Content freshness
- Verified remediation progress

Guards against confounding real performance shifts with crawl coverage variance or scoring methodology revisions.
"""
from __future__ import annotations

from typing import Any, Optional

from app.monitoring.models import (
    HistoricalDisciplineDelta,
    HistoricalIntelligenceReport,
    _utcnow,
)


class HistoricalIntelligenceEngine:
    """Computes evidence-backed historical trends distinguishing genuine progress from sampling variance."""

    def __init__(self, coverage_skew_threshold: float = 0.30):
        self.coverage_skew_threshold = coverage_skew_threshold

    def compare_audits(
        self,
        domain: str,
        baseline_audit: dict[str, Any],
        current_audit: dict[str, Any],
        verified_remediation_progress: float = 0.0,
    ) -> HistoricalIntelligenceReport:
        b_id = baseline_audit.get("audit_id", "baseline_audit")
        c_id = current_audit.get("audit_id", "current_audit")

        b_sample = baseline_audit.get("sample_size", baseline_audit.get("pages_crawled", 1))
        c_sample = current_audit.get("sample_size", current_audit.get("pages_crawled", 1))
        b_version = baseline_audit.get("scoring_methodology_version", "1.0")
        c_version = current_audit.get("scoring_methodology_version", "1.0")

        methodology_changed = b_version != c_version
        coverage_delta = (c_sample - b_sample) / float(max(b_sample, 1))
        has_coverage_skew = abs(coverage_delta) >= self.coverage_skew_threshold

        disciplines = [
            ("seo_score", "SEO Technical & Architecture Score"),
            ("geo_score", "GEO Entity & Search Visibility Score"),
            ("aeo_score", "AEO Answer Coverage & Completeness Score"),
            ("cro_score", "CRO Friction & Journey Quality Score"),
            ("tech_score", "Technical Infrastructure & Health Score"),
            ("citations_score", "Citation Frequency & Credibility Score"),
            ("competitor_displacement_score", "Competitor Displacement Index"),
        ]

        discipline_deltas: dict[str, HistoricalDisciplineDelta] = {}

        for key, name in disciplines:
            b_val = float(baseline_audit.get(key, 0.0))
            c_val = float(current_audit.get(key, 0.0))
            delta = round(c_val - b_val, 2)

            is_real = True
            explanations = []

            if methodology_changed:
                is_real = False
                explanations.append(f"Scoring methodology updated from v{b_version} to v{c_version}.")
            if has_coverage_skew:
                is_real = False
                direction = "expanded" if coverage_delta > 0 else "contracted"
                explanations.append(
                    f"Crawl sample size {direction} by {abs(coverage_delta)*100:.1f}% "
                    f"({b_sample} -> {c_sample} pages)."
                )

            if not explanations:
                explanations.append("Performance change reflects verified operational delta under consistent methodology.")

            discipline_deltas[key] = HistoricalDisciplineDelta(
                metric_name=name,
                baseline_score=b_val,
                current_score=c_val,
                delta=delta,
                crawl_coverage_delta=round(coverage_delta, 4),
                scoring_methodology_changed=methodology_changed,
                sample_size_baseline=b_sample,
                sample_size_current=c_sample,
                is_real_performance_change=is_real,
                explanation=" ".join(explanations),
            )

        seo_d = discipline_deltas["seo_score"].delta
        geo_d = discipline_deltas["geo_score"].delta
        aeo_d = discipline_deltas["aeo_score"].delta
        cro_d = discipline_deltas["cro_score"].delta
        tech_d = discipline_deltas["tech_score"].delta
        comp_d = discipline_deltas["competitor_displacement_score"].delta
        cite_d = discipline_deltas["citations_score"].delta

        content_freshness = float(current_audit.get("content_freshness_score", 100.0))

        return HistoricalIntelligenceReport(
            domain=domain,
            audit_id_baseline=b_id,
            audit_id_current=c_id,
            discipline_deltas=discipline_deltas,
            seo_delta=seo_d,
            geo_delta=geo_d,
            aeo_delta=aeo_d,
            cro_delta=cro_d,
            tech_delta=tech_d,
            competitor_displacement_delta=comp_d,
            citation_delta=cite_d,
            content_freshness_score=content_freshness,
            verified_remediation_progress=verified_remediation_progress,
            observation_timestamp=_utcnow(),
        )

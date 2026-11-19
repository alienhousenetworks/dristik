"""Phase 12.2: Scoring Governance & Mathematical Algorithm Specification.

Governs 6 orthogonal diagnostic dimensions without cross-dimensional contamination:
1. Technical Health
2. Content Readiness
3. Observed Visibility
4. User Experience
5. Business Performance
6. Competitive Positioning

Generates transparent, audit-ready mathematical scoring specifications explaining
exactly what every score, weight, penalty curve, and rating tier signifies.
"""
from __future__ import annotations

import math
from typing import Any, Optional

from app.governance.models import (
    ScoringAlgorithmSpecification,
    ScoringCategory,
)


RATING_TIERS: dict[str, str] = {
    "90-100": "EXEMPLARY (Industry Benchmark Leader — Robust, optimized architecture with zero critical blockers)",
    "80-89": "STRONG (Resilient Performance — High operational standard with minor localized tuning opportunities)",
    "65-79": "MODERATE (Remediation Required — Visible commercial or crawl drag requiring planned engineering intervention)",
    "50-64": "VULNERABLE (Structural Deficits Detected — Systemic friction impairing indexing, visibility, or conversion)",
    "<50": "CRITICAL (Systemic Operational Failure — Urgent live risk of severe organic traffic or transaction collapse)",
}

DEFAULT_CATEGORY_WEIGHTS: dict[ScoringCategory, dict[str, float]] = {
    ScoringCategory.TECHNICAL_HEALTH: {
        "SEO.TECH.001": 0.30,  # Canonical coverage
        "SEO.TECH.002": 0.20,  # Redirect chains
        "SEO.TECH.003": 0.25,  # TTFB latency
        "SEO.TECH.004": 0.15,  # AI crawler access
        "SEO.TECH.005": 0.10,  # Broken internal links
    },
    ScoringCategory.CONTENT_READINESS: {
        "AEO.CONT.001": 0.40,  # Direct answer extractability
        "AEO.CONT.002": 0.30,  # Semantic heading sequence
        "SEO.CONT.001": 0.30,  # Title tag compliance
    },
    ScoringCategory.OBSERVED_VISIBILITY: {
        "GEO.VIS.001": 0.50,  # AI engine appearance rate
        "GEO.VIS.002": 0.50,  # Citation domain authority
    },
    ScoringCategory.USER_EXPERIENCE: {
        "CRO.EXP.001": 0.40,  # CTA above fold
        "CRO.EXP.002": 0.40,  # Form input friction
        "CRO.EXP.003": 0.20,  # Mobile responsive layout
    },
    ScoringCategory.BUSINESS_PERFORMANCE: {
        "CRO.PERF.001": 0.70,  # Checkout funnel integrity
        "CRO.PERF.002": 0.30,  # Commercial inquiry completion
    },
    ScoringCategory.COMPETITIVE_POSITIONING: {
        "COMP.POS.001": 1.00,  # Competitor displacement index
    },
}

SEVERITY_PENALTIES: dict[str, float] = {
    "CRITICAL": 15.0,
    "HIGH": 8.0,
    "MEDIUM": 3.0,
    "LOW": 1.0,
    "INFO": 0.0,
}


class ScoringGovernanceEngine:
    """Computes transparent, decoupled multi-dimensional enterprise scores."""

    def __init__(self, category_weights: Optional[dict[ScoringCategory, dict[str, float]]] = None):
        self.weights = category_weights or DEFAULT_CATEGORY_WEIGHTS

    def evaluate_category_score(
        self,
        category: ScoringCategory,
        metric_values: dict[str, Optional[float]],
        findings: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Calculates dimension score strictly from relevant inputs, applying defect degradation curves."""
        findings = findings or []
        cat_weights = self.weights.get(category, {})

        # 1. Filter measured inputs
        measured_weights: dict[str, float] = {}
        weighted_sum = 0.0

        # Metrics where 0% defect rate is best
        lower_is_better_metrics = {"SEO.TECH.002", "SEO.TECH.005", "CRO.EXP.002"}

        for m_id, w in cat_weights.items():
            val = metric_values.get(m_id)
            if val is not None and not math.isnan(val):
                num_val = float(val)
                if m_id in lower_is_better_metrics and num_val <= 100.0:
                    clamped = max(0.0, min(100.0, 100.0 - num_val))
                else:
                    clamped = max(0.0, min(100.0, num_val))
                measured_weights[m_id] = w
                weighted_sum += clamped * w

        total_weight = sum(measured_weights.values())
        if total_weight <= 0.0:
            return {
                "category": category.value,
                "score": None,
                "status": "UNMEASURED",
                "rating_tier": "UNMEASURED (Insufficient telemetry or missing connector boundary)",
                "explanation": "Category unmeasured: Zero relevant metric data points collected in audit run.",
            }

        # Normalize raw base score
        base_score = weighted_sum / total_weight

        # 2. Defect penalty curve: P = min(35.0, sum(penalty * count))
        relevant_findings = [
            f for f in findings if str(f.get("category", "")).upper() in (category.value, "ALL")
        ]
        total_penalty = 0.0
        for f in relevant_findings:
            sev = str(f.get("severity", "MEDIUM")).upper()
            total_penalty += SEVERITY_PENALTIES.get(sev, 0.0)

        # Cap defect penalty at 35 points to avoid negative scores
        capped_penalty = min(35.0, total_penalty)
        final_score = round(max(0.0, min(100.0, base_score - capped_penalty)), 1)
        rating = self.classify_rating(final_score)

        return {
            "category": category.value,
            "score": final_score,
            "base_score": round(base_score, 1),
            "defect_penalty": round(capped_penalty, 1),
            "status": "MEASURED",
            "rating_tier": rating,
            "measured_metrics_count": len(measured_weights),
            "total_metrics_count": len(cat_weights),
            "explanation": (
                f"Base score {base_score:.1f} minus {capped_penalty:.1f} defect penalty across "
                f"{len(relevant_findings)} findings yields final score of {final_score:.1f} ({rating})."
            ),
        }

    @staticmethod
    def classify_rating(score: float) -> str:
        if score >= 90.0:
            return RATING_TIERS["90-100"]
        elif score >= 80.0:
            return RATING_TIERS["80-89"]
        elif score >= 65.0:
            return RATING_TIERS["65-79"]
        elif score >= 50.0:
            return RATING_TIERS["50-64"]
        else:
            return RATING_TIERS["<50"]

    def generate_scoring_algorithm_specification(self) -> ScoringAlgorithmSpecification:
        """Generates the dedicated in-depth mathematical scoring specification page."""
        lines = [
            "# Dristik Enterprise Scoring Algorithm & Rating Specification",
            "",
            "## 1. Architectural Philosophy",
            "Dristik operates under an **orthogonal dimensional scoring framework**. No single 'universal SEO score' "
            "is allowed to aggregate unrelated evidence. A website can achieve a 95/100 in Technical Health while "
            "scoring 30/100 in Observed Visibility. Collapsing these into a 62.5 composite creates false diagnosis; "
            "keeping them decoupled reveals that infrastructure is sound but entity discovery is absent.",
            "",
            "## 2. Six Canonical Diagnostic Dimensions",
            "1. **TECHNICAL_HEALTH**: HTTP hop hygiene, canonical clarity, latency (TTFB), crawler accessibility, broken link incidence.",
            "2. **CONTENT_READINESS**: Answer extractability for AI search, semantic heading hierarchy, metadata syntax.",
            "3. **OBSERVED_VISIBILITY**: Empirical brand mentions in LLM answer engines, domain citation authority.",
            "4. **USER_EXPERIENCE**: Visual CTA placement, form field input friction, responsive layout integrity.",
            "5. **BUSINESS_PERFORMANCE**: Transactional checkout reliability, commercial inquiry completion rates.",
            "6. **COMPETITIVE_POSITIONING**: Relative displacement index against approved benchmark competitors.",
            "",
            "## 3. Mathematical Formula & Weight Distribution",
            "For each dimension $d$, the score $S_d$ is computed in two deterministic steps:",
            "",
            "### Step 3.1: Weighted Raw Baseline Score ($S_{\\text{base}}$)",
            "$$S_{\\text{base}} = \\frac{\\sum_{i \\in M_d} w_i \\times m_i}{\\sum_{i \\in M_d} w_i}$$",
            "Where $m_i \\in [0, 100]$ is the measured value of metric $i$, and $w_i$ is its normalized category weight.",
            "",
            "| Category | Metric ID | Name | Weight |",
            "|---|---|---|---|",
        ]

        for cat, weights in self.weights.items():
            for m_id, w in weights.items():
                lines.append(f"| {cat.value} | `{m_id}` | Defined in Metric Registry | {w*100:.0f}% |")

        lines.extend([
            "",
            "### Step 3.2: Defect Penalty Curve ($P$)",
            "$$P = \\min\\left(35.0, \\sum_{j \\in F_d} \\text{penalty}(s_j)\\right)$$",
            "",
            "Penalty deductions per severity tier:",
            "- **CRITICAL**: $-15.0$ points per verified defect (e.g. fatal redirect loop, noindex on root)",
            "- **HIGH**: $-8.0$ points per defect (e.g. broken checkout button, missing primary H1)",
            "- **MEDIUM**: $-3.0$ points per defect (e.g. sub-optimal title length, minor script delay)",
            "- **LOW**: $-1.0$ point per defect (e.g. missing optional image alt)",
            "- **INFO**: $0.0$ points (advisory observation)",
            "",
            "### Step 3.3: Final Clamped Score ($S_d$)",
            "$$S_d = \\max\\left(0.0, \\min\\left(100.0, S_{\\text{base}} - P\\right)\\right)$$",
            "",
            "## 4. Rating Tier Definitions",
            "Every numerical score $S \\in [0, 100]$ maps to an explicit qualitative rating tier:",
            "",
        ])

        for tier, desc in RATING_TIERS.items():
            lines.append(f"- **Tier `{tier}`**: {desc}")

        lines.extend([
            "",
            "## 5. Unmeasured Data & Missing Connector Isolation",
            "- If a dimension lacks verified input evidence, its status is explicitly marked `UNMEASURED`.",
            "- An unmeasured category is **NEVER penalised as 0.0**; it is isolated from customer health ratings.",
            "- Missing third-party credentials (e.g. Google Search Console or Analytics) are reported as telemetry gaps rather than poor SEO health.",
        ])

        spec_markdown = "\n".join(lines)

        return ScoringAlgorithmSpecification(
            title="Enterprise Scoring Algorithm & Rating Specification",
            version="v12.0-Enterprise",
            scoring_categories=[c.value for c in ScoringCategory],
            rating_tiers=RATING_TIERS,
            weight_distribution={c.value: w for c, w in self.weights.items()},
            penalty_curve_formula="S_d = max(0, min(100, S_base - min(35.0, sum(severity_penalty))))",
            unmeasured_isolation_rules=[
                "Zero inputs -> UNMEASURED status",
                "Never penalize unmeasured telemetry as 0",
                "Isolate unmeasured dimensions from composite health ratings",
            ],
            markdown_documentation=spec_markdown,
        )

"""Phase 12.3: Statistical Reliability and Confidence Engine.

Enforces mathematical rigor on sampled diagnostic metrics:
- Stores numerator, denominator, sample size, population definition, and method.
- Calculates asymmetric Wilson score intervals for proportion metrics.
- Calculates standard error and finite population corrections where applicable.
- Replaces arbitrary AI confidence labels with empirical sampling rationales.
"""
from __future__ import annotations

import math
from typing import Any, Optional

from app.governance.models import SampledMetricRecord, _utcnow


class StatisticalReliabilityEngine:
    """Calculates empirical confidence intervals and honest uncertainty boundaries."""

    @staticmethod
    def calculate_proportion_confidence(
        metric_id: str,
        successes: int,
        total_sample: int,
        population_size: Optional[int] = None,
        population_definition: str = "All discoverable HTML pages within domain boundary",
        confidence_level: float = 0.95,
        sampling_method: str = "STRATIFIED_CRAWL",
    ) -> SampledMetricRecord:
        """Calculates Wilson score interval for proportion metrics."""
        now = _utcnow()
        if total_sample <= 0:
            return SampledMetricRecord(
                metric_id=metric_id,
                measured_value=0.0,
                numerator=0.0,
                denominator=0.0,
                sample_size=0,
                population_size=population_size,
                population_definition=population_definition,
                sampling_method=sampling_method,
                sampling_date=now,
                standard_error=None,
                ci_lower=None,
                ci_upper=None,
                confidence_rationale="Unmeasured: Zero observations collected in sample.",
            )

        p_hat = successes / float(total_sample)
        measured_pct = round(p_hat * 100.0, 2)

        # Case 1: Exhaustive census (Sample equals total population)
        if population_size is not None and total_sample >= population_size and population_size > 0:
            return SampledMetricRecord(
                metric_id=metric_id,
                measured_value=measured_pct,
                numerator=float(successes),
                denominator=float(total_sample),
                sample_size=total_sample,
                population_size=population_size,
                population_definition=population_definition,
                sampling_method="EXHAUSTIVE_CENSUS",
                sampling_date=now,
                standard_error=0.0,
                ci_lower=measured_pct,
                ci_upper=measured_pct,
                confidence_rationale=(
                    f"Exhaustive Census: 100% of population ({total_sample}/{population_size} pages) inspected. "
                    f"Measurement contains zero sampling variance."
                ),
            )

        # Case 2: Wilson Score Interval (z = 1.96 for 95% confidence)
        z = 1.95996 if abs(confidence_level - 0.95) < 0.01 else 2.576
        denom = 1.0 + (z**2) / total_sample
        center = p_hat + (z**2) / (2.0 * total_sample)
        radicand = (p_hat * (1.0 - p_hat) / total_sample) + ((z**2) / (4.0 * (total_sample**2)))
        margin = z * math.sqrt(max(0.0, radicand))

        ci_low = max(0.0, (center - margin) / denom) * 100.0
        ci_high = min(100.0, (center + margin) / denom) * 100.0
        se = math.sqrt(max(0.0, p_hat * (1.0 - p_hat) / total_sample))

        # Apply finite population correction if population is known and n > 5% of N
        if population_size and population_size > total_sample:
            fpc = math.sqrt((population_size - total_sample) / float(population_size - 1))
            se *= fpc

        # Rationale based on sample size
        if total_sample < 30:
            rationale = (
                f"Low-power exploratory sample (n={total_sample}). Wide uncertainty interval "
                f"[{ci_low:.1f}%, {ci_high:.1f}%] due to small sample size. Expand crawl to narrow bounds."
            )
        else:
            rationale = (
                f"Statistically reliable sample (n={total_sample}, 95% Wilson CI [{ci_low:.1f}%, {ci_high:.1f}%], "
                f"SE={se*100:.2f}%)."
            )

        return SampledMetricRecord(
            metric_id=metric_id,
            measured_value=measured_pct,
            numerator=float(successes),
            denominator=float(total_sample),
            sample_size=total_sample,
            population_size=population_size,
            population_definition=population_definition,
            sampling_method=sampling_method,
            sampling_date=now,
            standard_error=round(se * 100.0, 3),
            ci_lower=round(ci_low, 2),
            ci_upper=round(ci_high, 2),
            confidence_rationale=rationale,
        )

    @staticmethod
    def calculate_continuous_confidence(
        metric_id: str,
        values: list[float],
        population_size: Optional[int] = None,
        population_definition: str = "All inspected entry points",
    ) -> SampledMetricRecord:
        """Calculates mean, standard error, and confidence bounds for continuous observations (e.g. latency)."""
        now = _utcnow()
        if not values:
            return SampledMetricRecord(
                metric_id=metric_id,
                measured_value=0.0,
                sample_size=0,
                confidence_rationale="Unmeasured: Zero continuous values recorded.",
            )

        n = len(values)
        mean_val = sum(values) / float(n)
        variance = sum((x - mean_val) ** 2 for x in values) / float(n - 1) if n > 1 else 0.0
        std_dev = math.sqrt(variance)
        se = std_dev / math.sqrt(n) if n > 0 else 0.0

        z = 1.96
        ci_low = max(0.0, mean_val - z * se)
        ci_high = mean_val + z * se

        return SampledMetricRecord(
            metric_id=metric_id,
            measured_value=round(mean_val, 2),
            sample_size=n,
            population_size=population_size,
            population_definition=population_definition,
            sampling_method="SYSTEMATIC_SAMPLING",
            sampling_date=now,
            standard_error=round(se, 2),
            ci_lower=round(ci_low, 2),
            ci_upper=round(ci_high, 2),
            confidence_rationale=f"Continuous sample (n={n}, mean={mean_val:.1f}, 95% CI [{ci_low:.1f}, {ci_high:.1f}]).",
        )

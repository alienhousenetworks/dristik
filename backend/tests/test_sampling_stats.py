"""
Unit Tests for Statistical Reliability Layer & Confidence Intervals.
Tests:
1. Wilson score confidence interval correctness across nominal ranges and boundary cases (0% and 100%).
2. Student's t continuous confidence intervals for repeated run impression metrics.
3. Overlapping interval detection for trend suppression.
"""
import pytest
from app.intelligence.geo.metrics import (
    wilson_score_interval,
    continuous_confidence_interval,
    intervals_overlap,
    calculate_sample_variance,
)


def test_wilson_score_interval_nominal():
    # 5 out of 10 successes -> 50%
    ci = wilson_score_interval(successes=5, trials=10, confidence=0.95)
    assert ci is not None
    lower, upper = ci
    assert 0.0 < lower < 50.0
    assert 50.0 < upper < 100.0
    # Standard 10-trial Wilson 95% CI for p=0.5 is approx [23.7%, 76.3%]
    assert round(lower, 0) in (23.0, 24.0)
    assert round(upper, 0) in (76.0, 77.0)


def test_wilson_score_interval_boundaries():
    # 0 successes out of 5 runs -> lower bound must stay >= 0.0
    ci_zero = wilson_score_interval(successes=0, trials=5)
    assert ci_zero is not None
    assert ci_zero[0] == 0.0
    assert 0.0 < ci_zero[1] < 50.0

    # 5 successes out of 5 runs -> upper bound must stay <= 100.0
    ci_full = wilson_score_interval(successes=5, trials=5)
    assert ci_full is not None
    assert 50.0 < ci_full[0] < 100.0
    assert ci_full[1] == 100.0


def test_continuous_confidence_interval():
    # 5 runs with impression percentages
    runs = [30.0, 32.0, 28.0, 31.0, 29.0]
    ci = continuous_confidence_interval(runs, confidence=0.95)
    assert ci is not None
    lower, upper = ci
    mean = sum(runs) / len(runs)
    assert lower < mean < upper
    assert 20.0 <= lower <= 30.0
    assert 30.0 <= upper <= 40.0


def test_intervals_overlap_suppression():
    # Overlapping intervals: e.g. [25.0, 45.0] vs [35.0, 55.0]
    ci1 = (25.0, 45.0)
    ci2 = (35.0, 55.0)
    assert intervals_overlap(ci1, ci2) is True

    # Clearly separated intervals: e.g. [20.0, 30.0] vs [40.0, 50.0]
    ci3 = (20.0, 30.0)
    ci4 = (40.0, 50.0)
    assert intervals_overlap(ci3, ci4) is False


def test_sample_variance():
    values = [10.0, 12.0, 14.0]
    var = calculate_sample_variance(values)
    # Variance of [10, 12, 14] is 4.0
    assert abs(var - 4.0) < 1e-6

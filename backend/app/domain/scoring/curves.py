"""
Mathematical functions for Dristik Scoring Engine v5.0:
- Continuous log-normal metric curves (Lighthouse-style)
- Wilson 95% score confidence intervals for sampling rates
- Normal CDF using standard error function (erf)
"""
import math
from typing import Tuple


def phi(z: float) -> float:
    """Standard normal cumulative distribution function (CDF) using math.erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def log_normal_curve(
    x: float,
    p10: float,
    median: float,
    higher_is_better: bool = False
) -> float:
    """
    Calculates a continuous 0.0 - 1.0 score using a log-normal distribution curve.
    
    Anchored on:
      p10: published standard threshold that maps to score 0.90
      median: published poor/average threshold that maps to score 0.50
      
    sigma = (ln(median) - ln(p10)) / 1.2816
    score = 1 - Phi((ln(x) - ln(median)) / sigma)  (when lower is better, e.g. LCP, TTFB, INP)
    score = Phi((ln(x) - ln(median)) / sigma)      (when higher is better, e.g. information gain)
    """
    if x <= 0.0:
        return 1.0 if not higher_is_better else 0.0
    if p10 <= 0.0 or median <= 0.0 or p10 == median:
        return 0.5

    try:
        ln_x = math.log(x)
        ln_median = math.log(median)
        ln_p10 = math.log(p10)

        # Standard normal inverse at 0.90 is ~1.28155
        sigma = abs(ln_median - ln_p10) / 1.2815515655
        if sigma == 0:
            return 0.5

        z = (ln_x - ln_median) / sigma
        prob = phi(z)

        if higher_is_better:
            score = prob
        else:
            score = 1.0 - prob

        return max(0.0, min(1.0, float(score)))
    except (ValueError, OverflowError, ZeroDivisionError):
        return 0.5


def wilson_interval(
    successes: int,
    total: int,
    confidence: float = 0.95
) -> Tuple[float, float, float]:
    """
    Computes the Wilson score interval for a binomial proportion.
    Returns (center, lower_bound, upper_bound) in range [0.0, 1.0].
    
    For 95% confidence, z ~ 1.95996.
    """
    if total <= 0:
        return (0.0, 0.0, 0.0)

    successes = max(0, min(successes, total))
    p_hat = successes / total

    # z value for two-tailed confidence level
    if abs(confidence - 0.95) < 0.01:
        z = 1.959963984540054
    elif abs(confidence - 0.99) < 0.01:
        z = 2.5758293035489004
    elif abs(confidence - 0.90) < 0.01:
        z = 1.6448536269514722
    else:
        z = 1.959963984540054

    z2 = z * z
    denom = 1.0 + (z2 / total)
    center = (p_hat + (z2 / (2.0 * total))) / denom

    radicand = (p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total))
    half_width = z * math.sqrt(max(0.0, radicand)) / denom

    lower = max(0.0, center - half_width)
    upper = min(1.0, center + half_width)

    return (round(center, 4), round(lower, 4), round(upper, 4))


def audience_readability_score(
    flesch_score: float,
    audience: str = "b2b_technical"
) -> float:
    """
    Scores Flesch Reading Ease against target audience bands with gentle Gaussian decay outside.
    Consumer: optimal 60-80
    B2B Technical: optimal 30-60
    """
    if audience.lower() in ("consumer", "general"):
        min_opt, max_opt = 60.0, 80.0
    else:
        min_opt, max_opt = 30.0, 60.0

    if min_opt <= flesch_score <= max_opt:
        return 1.0

    if flesch_score < min_opt:
        delta = min_opt - flesch_score
        return max(0.1, math.exp(-0.5 * (delta / 15.0) ** 2))
    else:
        delta = flesch_score - max_opt
        return max(0.2, math.exp(-0.5 * (delta / 20.0) ** 2))

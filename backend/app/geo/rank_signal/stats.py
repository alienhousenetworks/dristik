"""
Rank Signal Bayesian statistics (zero third-party math dependencies).

Posterior: Beta(wins + 0.5, n - wins + 0.5) (Jeffreys prior), equal-tailed 95% CI.
Quantiles via bisection on the regularized incomplete beta I_x(a, b).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

StatVerdict = Literal["insufficient", "pending", "positive", "negative", "no_clear_effect"]

CHECKPOINTS = (20, 30, 40)
MAX_TRIALS = 40


@dataclass(frozen=True)
class Posterior:
    mean: float
    lo: float
    hi: float


def _betacf(x: float, a: float, b: float) -> float:
    """Continued fraction for I_x(a, b) (Lentz method)."""
    fpmin = 1e-300
    eps = 1e-15
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - (qab * x) / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, 301):
        m2 = 2 * m
        aa = (m * (b - m) * x) / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def beta_cdf(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_front = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    front = math.exp(ln_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return (front * _betacf(x, a, b)) / a
    return 1.0 - (front * _betacf(1.0 - x, b, a)) / b


def beta_quantile(p: float, a: float, b: float) -> float:
    """Inverse of I_x(a, b) by bisection on [0, 1] (100 iterations)."""
    if not (0.0 <= p <= 1.0):
        raise ValueError(f"p out of range: {p}")
    if not (a > 0.0 and b > 0.0):
        raise ValueError(f"invalid beta shape: a={a}, b={b}")
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) * 0.5
        if beta_cdf(mid, a, b) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) * 0.5


def posterior(wins: int, n: int) -> Posterior:
    """Jeffreys Beta(wins + 0.5, n - wins + 0.5) mean and equal-tailed 95% CI."""
    if wins < 0 or n < 0 or wins > n:
        raise ValueError(f"invalid counts: wins={wins}, n={n}")
    a = wins + 0.5
    b = (n - wins) + 0.5
    return Posterior(
        mean=round(a / (a + b), 4),
        lo=round(beta_quantile(0.025, a, b), 4),
        hi=round(beta_quantile(0.975, a, b), 4),
    )


def decide(n: int, lo: float, hi: float) -> StatVerdict:
    if n < 20:
        return "insufficient"
    if lo > 0.5:
        return "positive"
    if hi < 0.5:
        return "negative"
    if n >= 40:
        return "no_clear_effect"
    return "pending"


def verdict(wins: int, n: int) -> StatVerdict:
    if wins < 0 or n < 0 or wins > n:
        raise ValueError(f"invalid counts: wins={wins}, n={n}")
    if n < 20:
        return "insufficient"
    post = posterior(wins, n)
    return decide(n, post.lo, post.hi)

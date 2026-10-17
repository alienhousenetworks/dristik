"""
GEO Readiness Score Calculation.
"""
def calculate_geo_readiness(citation_rate: float, sentiment_score: float) -> float:
    return round((citation_rate * 0.7 + sentiment_score * 0.3) * 100, 1)

__all__ = ["calculate_geo_readiness"]

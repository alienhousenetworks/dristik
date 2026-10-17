from app.geo.scoring.geo_readiness import calculate_geo_readiness

def test_geo_readiness_calculation():
    score = calculate_geo_readiness(citation_rate=0.8, sentiment_score=0.9)
    assert score == 83.0

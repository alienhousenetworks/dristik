from app.seo.audit.scoring.score_engine import ScoreEngine

def test_score_engine_calculation():
    engine = ScoreEngine()
    pillars = {
        'technical': 90.0,
        'content': 80.0,
        'geo': 70.0,
        'authority': 85.0,
        'ux': 90.0,
        'conversion': 80.0
    }
    score = engine.calculate_overall_score(pillars)
    assert 70.0 <= score <= 100.0

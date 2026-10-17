class ScoreEngine:
    def calculate_overall_score(self, pillar_scores: dict) -> float:
        weights = {
            "technical": 0.25,
            "content": 0.20,
            "geo": 0.15,
            "authority": 0.15,
            "ux": 0.15,
            "conversion": 0.10
        }
        total = sum(pillar_scores.get(k, 70.0) * w for k, w in weights.items())
        return round(total, 1)

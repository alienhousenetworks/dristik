def score_evidence_confidence(provenance: str) -> float:
    weights = {
        "RAW_TELEMETRY": 1.0,
        "RENDERED_DOM": 0.95,
        "EXTRACTED_CONTENT": 0.9,
        "THIRD_PARTY_OBSERVATION": 0.85,
        "SYNTHESIZED_INFERENCE": 0.75
    }
    return weights.get(provenance, 0.7)

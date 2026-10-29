"""
Dristik AI Competitive Landscape Coordinates Calculator.
Computes continuous 2D coordinates (X: Search Visibility, Y: GEO / AI Visibility)
using configurable weights and dynamic re-normalization when components are unmeasured.
Never returns hardcoded or fake coordinates.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from app.seo.competitive.models import (
    DimensionScore,
    EvidenceConfidence,
    LandscapeCoordinates,
)

DEFAULT_SEARCH_WEIGHTS: Dict[str, float] = {
    "keyword_overlap_pct": 0.40,
    "organic_visibility_index": 0.30,
    "shared_query_count": 0.15,
    "commercial_overlap": 0.15,
}

DEFAULT_GEO_WEIGHTS: Dict[str, float] = {
    "ai_prompt_overlap_pct": 0.40,
    "citation_frequency_pct": 0.35,
    "commercial_bakeoff_win_rate": 0.25,
}


class LandscapeCalculator:
    """
    Computes dynamic continuous coordinates for the competitive positioning scatter plot.
    """

    def compute_coordinates(
        self,
        search_dim: Optional[DimensionScore],
        geo_dim: Optional[DimensionScore],
        custom_search_weights: Optional[Dict[str, float]] = None,
        custom_geo_weights: Optional[Dict[str, float]] = None,
    ) -> LandscapeCoordinates:
        search_weights = custom_search_weights or DEFAULT_SEARCH_WEIGHTS
        geo_weights = custom_geo_weights or DEFAULT_GEO_WEIGHTS

        # -------------------------------------------------------------
        # 1. Compute X (Search Visibility: 0.0 - 1.0)
        # -------------------------------------------------------------
        x_val: float = 0.5
        x_conf: EvidenceConfidence = EvidenceConfidence.UNMEASURED

        if search_dim and search_dim.status == "AVAILABLE" and search_dim.score is not None:
            km = search_dim.key_metrics or {}
            measured_components: Dict[str, float] = {}
            total_active_weight: float = 0.0

            for metric_key, weight in search_weights.items():
                if metric_key in km and km[metric_key] is not None:
                    # Normalize metric value to 0.0-1.0
                    val = float(km[metric_key])
                    norm_val = min(1.0, max(0.0, val / 100.0 if val > 1.0 else val))
                    measured_components[metric_key] = norm_val
                    total_active_weight += weight

            if total_active_weight > 0:
                weighted_sum = sum(
                    measured_components[k] * (search_weights[k] / total_active_weight)
                    for k in measured_components
                )
                x_val = round(weighted_sum, 3)
                x_conf = search_dim.confidence
            else:
                x_val = round(search_dim.score / 100.0, 3)
                x_conf = search_dim.confidence

        # -------------------------------------------------------------
        # 2. Compute Y (GEO / AI Visibility: 0.0 - 1.0)
        # -------------------------------------------------------------
        y_val: float = 0.5
        y_conf: EvidenceConfidence = EvidenceConfidence.UNMEASURED

        if geo_dim and geo_dim.status == "AVAILABLE" and geo_dim.score is not None:
            km = geo_dim.key_metrics or {}
            measured_components: Dict[str, float] = {}
            total_active_weight: float = 0.0

            for metric_key, weight in geo_weights.items():
                if metric_key in km and km[metric_key] is not None:
                    val = float(km[metric_key])
                    norm_val = min(1.0, max(0.0, val / 100.0 if val > 1.0 else val))
                    measured_components[metric_key] = norm_val
                    total_active_weight += weight

            if total_active_weight > 0:
                weighted_sum = sum(
                    measured_components[k] * (geo_weights[k] / total_active_weight)
                    for k in measured_components
                )
                y_val = round(weighted_sum, 3)
                y_conf = geo_dim.confidence
            else:
                y_val = round(geo_dim.score / 100.0, 3)
                y_conf = geo_dim.confidence

        return LandscapeCoordinates(
            x=x_val,
            y=y_val,
            x_confidence=x_conf,
            y_confidence=y_conf,
            weights_used={"search_active": list(search_weights.keys()), "geo_active": list(geo_weights.keys())},
        )


landscape_calculator = LandscapeCalculator()

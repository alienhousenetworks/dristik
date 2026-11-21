"""
Two-Layer GEO Scorecard — Phase 4.9

Computes versioned GEO scores with strict architectural separation between:
1. Layer 1: GEO Content Readiness (What the website is technically & semantically prepared to communicate)
2. Layer 2: Observed AI Visibility (What live answer systems actually retrieved and cited during testing)

STRICT FIREWALL GUARDRAIL:
Never merge these into an apparently comprehensive single score when live testing is unavailable.
If live connectors are absent, Observed AI Visibility explicitly reports NOT_MEASURED.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GeoScoreDimension(BaseModel):
    dimension_key: str
    dimension_name: str
    layer: str  # "LAYER_1_READINESS" or "LAYER_2_VISIBILITY"
    weight: float
    is_measured: bool
    score: Optional[float] = None
    grade: str = "N/A"
    measurement_notes: str = ""


class TwoLayerGeoScorecardReport(BaseModel):
    # Layer 1: Content Readiness
    layer_1_readiness_score: float
    layer_1_readiness_grade: str
    layer_1_status: str = "MEASURED"
    
    # Layer 2: Observed AI Visibility
    layer_2_visibility_score: Optional[float] = None
    layer_2_visibility_grade: str = "N/A"
    layer_2_status: str  # "MEASURED" or "NOT_MEASURED"
    
    # Synthesis & Firewall metadata
    is_visibility_measured: bool
    dimensions: List[GeoScoreDimension] = Field(default_factory=list)
    firewall_disclosure_statement: str


class GeoScorecardEngine:
    """
    Evaluates 8-dimension GEO scores, enforcing the strict firewall between Readiness and Visibility.
    """

    LAYER_1_DIMENSIONS: Dict[str, Dict[str, Any]] = {
        "entity_clarity": {"name": "Brand & Entity Clarity", "weight": 0.25},
        "content_extractability": {"name": "Passage Extractability & Structure", "weight": 0.25},
        "crawler_accessibility": {"name": "AI Crawler Accessibility", "weight": 0.20},
        "factual_grounding": {"name": "Factual Grounding & Declarations", "weight": 0.30},
    }

    LAYER_2_DIMENSIONS: Dict[str, Dict[str, Any]] = {
        "external_authority": {"name": "Independent External Corroboration", "weight": 0.25},
        "ai_mention_visibility": {"name": "AI Answer Mention Frequency", "weight": 0.25},
        "citation_visibility": {"name": "First-Party Citation Share", "weight": 0.25},
        "competitive_positioning": {"name": "Competitive Win Rate", "weight": 0.25},
    }

    @classmethod
    def _grade(cls, val: Optional[float]) -> str:
        if val is None:
            return "N/A"
        if val >= 85:
            return "A"
        elif val >= 70:
            return "B"
        elif val >= 55:
            return "C"
        elif val >= 40:
            return "D"
        else:
            return "F"

    @classmethod
    def calculate_two_layer_scorecard(
        cls,
        # Layer 1 Inputs (Crawl Evidence — None means unmeasured, never silently defaulted)
        entity_clarity_score: Optional[float] = None,
        content_extractability_score: Optional[float] = None,
        crawler_accessibility_score: Optional[float] = None,
        factual_grounding_score: Optional[float] = None,
        # Layer 2 Inputs (Live Telemetry - Optional)
        live_connectors_ran: bool = False,
        external_authority_score: Optional[float] = None,
        ai_mention_score: Optional[float] = None,
        citation_score: Optional[float] = None,
        competitive_score: Optional[float] = None,
    ) -> TwoLayerGeoScorecardReport:
        dim_list: List[GeoScoreDimension] = []

        # 1. Compute Layer 1: GEO Content Readiness (renormalize strictly over measured dimensions)
        l1_scores = {
            "entity_clarity": entity_clarity_score,
            "content_extractability": content_extractability_score,
            "crawler_accessibility": crawler_accessibility_score,
            "factual_grounding": factual_grounding_score,
        }

        l1_weighted = 0.0
        l1_weight_used = 0.0
        for k, meta in cls.LAYER_1_DIMENSIONS.items():
            sc = l1_scores.get(k)
            if sc is not None:
                l1_weighted += sc * meta["weight"]
                l1_weight_used += meta["weight"]
                dim_list.append(
                    GeoScoreDimension(
                        dimension_key=k,
                        dimension_name=meta["name"],
                        layer="LAYER_1_READINESS",
                        weight=meta["weight"],
                        is_measured=True,
                        score=round(sc, 1),
                        grade=cls._grade(sc),
                        measurement_notes="Computed deterministically from crawl and DOM evidence.",
                    )
                )
            else:
                dim_list.append(
                    GeoScoreDimension(
                        dimension_key=k,
                        dimension_name=meta["name"],
                        layer="LAYER_1_READINESS",
                        weight=meta["weight"],
                        is_measured=False,
                        score=None,
                        grade="N/A",
                        measurement_notes="Unmeasured: no crawl evidence supplied for this dimension.",
                    )
                )

        l1_composite = round(l1_weighted / l1_weight_used, 1) if l1_weight_used > 0 else 0.0
        l1_status = "MEASURED" if l1_weight_used > 0 else "NOT_MEASURED"

        # 2. Compute Layer 2: Observed AI Visibility (Guarded — partial dimensions supported honestly)
        l2_scores = {
            "external_authority": external_authority_score,
            "ai_mention_visibility": ai_mention_score,
            "citation_visibility": citation_score,
            "competitive_positioning": competitive_score,
        }
        measured_l2 = {k: v for k, v in l2_scores.items() if v is not None}
        if live_connectors_ran and measured_l2:
            l2_weighted = 0.0
            l2_weight_used = 0.0
            for k, meta in cls.LAYER_2_DIMENSIONS.items():
                sc = l2_scores.get(k)
                if sc is not None:
                    l2_weighted += sc * meta["weight"]
                    l2_weight_used += meta["weight"]
                    dim_list.append(
                        GeoScoreDimension(
                            dimension_key=k,
                            dimension_name=meta["name"],
                            layer="LAYER_2_VISIBILITY",
                            weight=meta["weight"],
                            is_measured=True,
                            score=round(sc, 1),
                            grade=cls._grade(sc),
                            measurement_notes="Verified via live AI search engine benchmarking.",
                        )
                    )
                else:
                    dim_list.append(
                        GeoScoreDimension(
                            dimension_key=k,
                            dimension_name=meta["name"],
                            layer="LAYER_2_VISIBILITY",
                            weight=meta["weight"],
                            is_measured=False,
                            score=None,
                            grade="N/A",
                            measurement_notes="Unmeasured for this run.",
                        )
                    )

            l2_composite = round(l2_weighted / l2_weight_used, 1) if l2_weight_used > 0 else None
            l2_status = "MEASURED" if len(measured_l2) == len(cls.LAYER_2_DIMENSIONS) else "PARTIAL"
            firewall_stmt = (
                f"Both layers assessed separately: Layer 1 Content Readiness ({l1_composite}/100) reflects site extractability; "
                f"Layer 2 Observed AI Visibility ({l2_composite}/100, {len(measured_l2)}/{len(cls.LAYER_2_DIMENSIONS)} dims) reflects verified live responses. "
                "The two layers are never merged into an artificial score."
            )
        else:
            # Firewall triggered: Layer 2 is strictly NOT_MEASURED
            for k, meta in cls.LAYER_2_DIMENSIONS.items():
                dim_list.append(
                    GeoScoreDimension(
                        dimension_key=k,
                        dimension_name=meta["name"],
                        layer="LAYER_2_VISIBILITY",
                        weight=meta["weight"],
                        is_measured=False,
                        score=None,
                        grade="N/A",
                        measurement_notes="Unmeasured: Live benchmark probing was not executed for this run.",
                    )
                )

            l2_composite = None
            l2_status = "NOT_MEASURED"
            firewall_stmt = (
                "Layer 1 Content Readiness is measured at "
                f"{l1_composite}/100 based on crawled first-party architecture. "
                "Layer 2 Observed AI Visibility is NOT_MEASURED because live answer probing was not executed. "
                "The two layers are never merged into an artificial score."
            )

        return TwoLayerGeoScorecardReport(
            layer_1_readiness_score=l1_composite,
            layer_1_readiness_grade=cls._grade(l1_composite) if l1_weight_used > 0 else "N/A",
            layer_1_status=l1_status,
            layer_2_visibility_score=l2_composite,
            layer_2_visibility_grade=cls._grade(l2_composite),
            layer_2_status=l2_status,
            is_visibility_measured=(l2_status in ("MEASURED", "PARTIAL")),
            dimensions=dim_list,
            firewall_disclosure_statement=firewall_stmt,
        )

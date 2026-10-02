"""
Dristik AI Competitive Intelligence Domain Models.
Defines evidence-grounded competitor representations, multi-signal classifications,
dimensional competition scores, dynamic landscape coordinates, and causal gap models.
Zero-fake policy: Absence of evidence is explicitly marked as UNMEASURED.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CompetitorType(str, Enum):
    DIRECT = "DIRECT"
    SEARCH = "SEARCH"
    GEO = "GEO"
    CONTENT = "CONTENT"
    COMMERCIAL = "COMMERCIAL"
    LOCAL = "LOCAL"
    INDIRECT = "INDIRECT"
    EMERGING = "EMERGING"


class EvidenceConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNMEASURED = "UNMEASURED"


class CompetitorEvidenceItem(BaseModel):
    id: str
    competitor_id: str
    evidence_type: str  # "technical" | "content" | "search" | "geo" | "authority" | "commercial"
    metric: str         # e.g., "keyword_overlap", "geo_visibility", "ttfb_ms", "schema_count"
    value: Optional[Any] = None
    unit: str = ""      # "%", "ms", "count", "score_0_100"
    source_url: Optional[str] = None
    source_type: str    # "live_crawl" | "serp_api" | "ai_simulator" | "search_console" | "manifest"
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: EvidenceConfidence = EvidenceConfidence.HIGH
    audit_id: Optional[str] = None
    query: Optional[str] = None
    notes: Optional[str] = None


CompetitiveEvidenceItem = CompetitorEvidenceItem


class CompetitorProfile(BaseModel):
    id: str
    canonical_domain: str
    company_name: str
    competitor_types: List[CompetitorType] = Field(default_factory=list)
    industry: Optional[str] = None
    geography: Optional[str] = "Global"
    discovery_sources: List[str] = Field(default_factory=list)
    discovery_confidence: float = 0.5
    evidence: List[CompetitorEvidenceItem] = Field(default_factory=list)


class DimensionScore(BaseModel):
    dimension: str        # "search" | "geo" | "content" | "authority" | "technical"
    score: Optional[int] = None  # 0-100 or None if unmeasured
    confidence: EvidenceConfidence = EvidenceConfidence.UNMEASURED
    status: str = "AVAILABLE"    # "AVAILABLE" | "UNMEASURED" | "INSUFFICIENT_EVIDENCE"
    evidence_count: int = 0
    key_metrics: Dict[str, Any] = Field(default_factory=dict)


class LandscapeCoordinates(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0, description="Weighted Search Visibility (0.0 to 1.0)")
    y: float = Field(..., ge=0.0, le=1.0, description="Weighted GEO / AI Visibility (0.0 to 1.0)")
    x_confidence: EvidenceConfidence = EvidenceConfidence.MEDIUM
    y_confidence: EvidenceConfidence = EvidenceConfidence.MEDIUM
    weights_used: Dict[str, Any] = Field(default_factory=dict)


class CompetitiveGapDimension(BaseModel):
    dimension_name: str
    dimension_key: str
    target_score: Optional[int] = None
    competitor_scores: Dict[str, Optional[int]] = Field(default_factory=dict)  # domain -> score
    deltas: Dict[str, Optional[int]] = Field(default_factory=dict)             # domain -> target - comp
    verdict: str


class CausalAdvantageExplanation(BaseModel):
    competitor_domain: str
    competitor_name: str
    reasons_they_outperform: List[str] = Field(default_factory=list)
    areas_target_wins: List[str] = Field(default_factory=list)


class CompetitiveEvidenceTableRow(BaseModel):
    dimension: str
    dimension_key: str
    target_value: Optional[str] = None
    competitor_values: Dict[str, Optional[str]] = Field(default_factory=dict)
    provenance_note: str = ""
    is_measured: bool = True


class DristikCompetitiveReport(BaseModel):
    target_domain: str
    target_brand: str
    market_niche: str
    competitors: List[CompetitorProfile] = Field(default_factory=list)
    dimension_scores: Dict[str, Dict[str, DimensionScore]] = Field(default_factory=dict)  # domain -> dim -> score
    landscape_coordinates: Dict[str, LandscapeCoordinates] = Field(default_factory=dict)   # domain -> coords
    gap_matrix: List[CompetitiveGapDimension] = Field(default_factory=list)
    causal_explanations: List[CausalAdvantageExplanation] = Field(default_factory=list)
    evidence_table: List[CompetitiveEvidenceTableRow] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

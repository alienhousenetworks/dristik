"""
Typed data models for 70+ slide executive presentation generation.
Enforces non-repetition, structured chart specs, and visual layouts.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class SlideLayoutType(str, Enum):
    COVER = "COVER"
    EXECUTIVE_SPLIT = "EXECUTIVE_SPLIT"
    METRIC_CARDS_4 = "METRIC_CARDS_4"
    METRIC_CARDS_3 = "METRIC_CARDS_3"
    CHART_WITH_ANALYSIS = "CHART_WITH_ANALYSIS"
    DUAL_CHART = "DUAL_CHART"
    TABLE_MATRIX = "TABLE_MATRIX"
    TIMELINE_PHASES = "TIMELINE_PHASES"
    FINDINGS_LEDGER = "FINDINGS_LEDGER"
    CODE_PATCH_DIFF = "CODE_PATCH_DIFF"
    GOVERNANCE_SEAL = "GOVERNANCE_SEAL"


class DeckChartType(str, Enum):
    COLUMN = "COLUMN"
    BAR = "BAR"
    DOUGHNUT = "DOUGHNUT"
    PIE = "PIE"
    RADAR_BAR = "RADAR_BAR"
    NONE = "NONE"


class ChartDataSpec(BaseModel):
    title: str
    chart_type: DeckChartType = DeckChartType.COLUMN
    categories: List[str] = Field(default_factory=list)
    series: List[Dict[str, Any]] = Field(default_factory=list)  # [{"name": "Score", "values": [...]}]
    units: str = ""
    target_value: Optional[float] = None


class CardSpec(BaseModel):
    kicker: str = ""
    title: str
    description: str
    metric_value: Optional[str] = None
    badge: Optional[str] = None
    badge_color: Optional[str] = None  # e.g. "sky", "emerald", "amber", "rose"


class SlideBlueprint(BaseModel):
    slide_id: str
    slide_number: int
    module_id: str
    module_title: str
    kicker: str
    title: str
    subtitle: str
    thematic_focus: str
    layout: SlideLayoutType
    chart: Optional[ChartDataSpec] = None
    secondary_chart: Optional[ChartDataSpec] = None
    cards: List[CardSpec] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)
    table_headers: List[str] = Field(default_factory=list)
    table_rows: List[List[str]] = Field(default_factory=list)
    evidence_citations: List[str] = Field(default_factory=list)
    footer_text: Optional[str] = None


class DeckBlueprint(BaseModel):
    domain: str
    total_slides: int
    modules: List[str]
    slides: List[SlideBlueprint]
    generated_at: str
    dedup_verification_token: str

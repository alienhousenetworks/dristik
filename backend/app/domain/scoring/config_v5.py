"""
Loader and schema models for Dristik Scoring Rubric v5.0 specification.
Loads categories, subsections, check definitions, gates, and sampling rules directly from JSON.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field


class CheckDef(BaseModel):
    check_id: str
    name: str
    check_type: Literal["binary", "graded", "curve"]
    weight: float
    p10: Optional[float] = None
    median: Optional[float] = None
    higher_is_better: bool = False
    unit: Optional[str] = None
    description: str = ""


class SubsectionDef(BaseModel):
    name: str
    budget_share: float
    checks: List[CheckDef] = Field(default_factory=list)


class GateDef(BaseModel):
    gate_id: str
    trigger_condition: str
    cap_score: Optional[float] = None
    action: Optional[str] = "CAP"  # CAP | MARK_NOT_MEASURED
    reason: str = ""


class CategoryDef(BaseModel):
    name: str
    baseline_weight: float
    gates: List[GateDef] = Field(default_factory=list)
    subsections: Dict[str, SubsectionDef] = Field(default_factory=dict)


class PlanSamplingDef(BaseModel):
    name: str
    default_scope_pages: int = 5
    ai_search_min_sample: int = 10
    ai_search_min_prompts: int = 10
    ai_search_repeats: int = 1


class CoverageRulesDef(BaseModel):
    measured_threshold: float = 0.60
    partial_threshold: float = 0.30
    unmeasured_threshold: float = 0.30
    semantics: Dict[str, str] = Field(default_factory=dict)


class ScoringRubricV5(BaseModel):
    methodology_version: str = "5.0"
    methodology_name: str = "Dristik Evidence-Based Check & Curve Scoring Architecture"
    last_updated: str = "October 2026"
    coverage_rules: CoverageRulesDef = Field(default_factory=CoverageRulesDef)
    plans: Dict[str, PlanSamplingDef] = Field(default_factory=dict)
    categories: Dict[str, CategoryDef] = Field(default_factory=dict)
    specialized_views: Dict[str, Any] = Field(default_factory=dict)


_CACHED_RUBRIC: Optional[ScoringRubricV5] = None


def load_scoring_rubric_v5(json_path: Optional[str] = None) -> ScoringRubricV5:
    """Loads and caches the v5.0 JSON scoring rubric."""
    global _CACHED_RUBRIC
    if _CACHED_RUBRIC is not None and json_path is None:
        return _CACHED_RUBRIC

    if json_path is None:
        target = Path(__file__).parent / "scoring_rubric_v5.json"
    else:
        target = Path(json_path)

    if not target.exists():
        raise FileNotFoundError(f"Scoring rubric file not found: {target}")

    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)

    rubric = ScoringRubricV5(**data)
    if json_path is None:
        _CACHED_RUBRIC = rubric
    return rubric

"""
Dristik AI Specialized Agent Schemas
Strict typed Pydantic output contracts for 70B-hardened workers and agents.
"""
from typing import Optional, List, Dict, Any, Literal, get_origin, get_args
from pydantic import BaseModel, Field, model_validator
from app.inference.schemas.shared import (
    Claim,
    CopyRewrite,
    EvidenceStatus,
    Severity,
    ImpactBand,
    ClarityBand,
)

class RobustSchemaModel(BaseModel):
    """
    Tolerant Pydantic model for LLM outputs.
    Automatically coerces [None] or null elements in list fields to valid lists,
    and strips out null, 'null', and 'none' strings that LLMs frequently emit.
    """
    @model_validator(mode="before")
    @classmethod
    def sanitize_null_in_lists(cls, data: Any) -> Any:
        if isinstance(data, dict):
            clean = {}
            for k, v in data.items():
                field_info = cls.model_fields.get(k)
                is_list_field = False
                if field_info:
                    origin = get_origin(field_info.annotation)
                    is_list_field = origin is list or (isinstance(origin, type) and issubclass(origin, list))
                if is_list_field:
                    if v is None:
                        clean[k] = []
                    elif isinstance(v, list):
                        clean[k] = [
                            str(x).strip()
                            for x in v
                            if x is not None and str(x).strip() and str(x).strip().lower() not in ("none", "null")
                        ]
                    elif isinstance(v, str):
                        s = v.strip()
                        clean[k] = [s] if s and s.lower() not in ("none", "null") else []
                    else:
                        clean[k] = []
                elif isinstance(v, list):
                    clean[k] = [
                        str(x).strip() if isinstance(x, str) else x
                        for x in v
                        if x is not None and (not isinstance(x, str) or (x.strip() and x.strip().lower() not in ("none", "null")))
                    ]
                else:
                    clean[k] = v
            return clean
        return data

# ---------------------------------------------------------
# 1. Business Intelligence (Split: Extract + Position)
# ---------------------------------------------------------

class BusinessExtractOutput(BaseModel):
    business_name: Optional[str] = None
    industry: Optional[str] = None
    niche: Optional[str] = None
    stated_audience_phrases: List[str] = Field(default_factory=list)
    stated_offer: Optional[str] = None
    primary_cta: Optional[str] = None
    secondary_cta: Optional[str] = None
    pricing_visible: bool = False
    motion_signals: Literal["self_serve", "sales_assisted", "hybrid", "unknown"] = "unknown"
    evidence_refs: List[str] = Field(default_factory=list)

class FiveSecondClarity(BaseModel):
    band: ClarityBand = "unknown"
    evidence_status: EvidenceStatus = "inferred"
    evidence_refs: List[str] = Field(default_factory=list)
    rationale: str = ""

class CacImpact(BaseModel):
    band: ImpactBand = "none"
    mechanism: str = ""
    numeric_estimate: Optional[float] = None

class BusinessCopyRewrite(BaseModel):
    before_hero_headline: Optional[str] = None
    after_hero_headline: Optional[str] = None
    before_subhead: Optional[str] = None
    after_subhead: Optional[str] = None

class BusinessPositionOutput(BaseModel):
    economic_buyer_title: Optional[str] = None
    target_org_scale: Literal["smb", "mid_market", "enterprise", "unknown"] = "unknown"
    operational_pain_points: List[str] = Field(default_factory=list)
    defensible_moat_type: Literal[
        "network_effects", "switching_costs", "scale_economies", "proprietary_ip", "weak", "unknown"
    ] = "unknown"
    business_model: Optional[str] = None
    monetization_motion: Literal["self_serve", "sales_assisted", "hybrid", "unknown"] = "unknown"
    value_proposition: Optional[str] = None
    five_second_clarity: FiveSecondClarity = Field(default_factory=FiveSecondClarity)
    cac_impact: CacImpact = Field(default_factory=CacImpact)
    copy_rewrite: BusinessCopyRewrite = Field(default_factory=BusinessCopyRewrite)
    claims: List[Claim] = Field(default_factory=list)

# ---------------------------------------------------------
# 2. GEO Agent
# ---------------------------------------------------------

class GeoAuditOutput(BaseModel):
    entity_clarity_band: ClarityBand = "adequate"
    knowledge_graph_readiness: Literal["High", "Moderate", "Low"] = "Moderate"
    direct_answer_density_score: Optional[int] = None
    information_gain: Literal["low", "medium", "high"] = "medium"
    information_gain_items: List[str] = Field(default_factory=list)
    schemas_detected: List[str] = Field(default_factory=list)
    schemas_missing: List[str] = Field(default_factory=list)
    sameas_bindings_detected: List[str] = Field(default_factory=list)
    sameas_recommended: List[str] = Field(default_factory=list)
    production_jsonld_patch: Dict[str, Any] = Field(default_factory=dict)
    claims: List[Claim] = Field(default_factory=list)

# ---------------------------------------------------------
# 3. AI Search Simulation
# ---------------------------------------------------------

class AiSearchQueryItem(BaseModel):
    query: str
    question_type: str
    evidence_quality: Literal["none", "weak", "moderate", "strong"] = "none"
    detected_answer: str = "cannot answer from site"
    gap_analysis: str = ""
    citation_readiness: Literal["low", "medium", "high"] = "low"
    hallucination_vulnerability: Literal["low", "medium", "high"] = "low"
    vulnerability_mechanism: str = ""
    recommended_remediation: str = ""
    evidence_refs: List[str] = Field(default_factory=list)

class AiSearchBatchOutput(BaseModel):
    evaluations: List[AiSearchQueryItem] = Field(default_factory=list)
    aggregate_citation_readiness: Literal["low", "medium", "high"] = "low"
    claims: List[Claim] = Field(default_factory=list)

# ---------------------------------------------------------
# 4. Critic Falsification
# ---------------------------------------------------------

class CriticResultItem(BaseModel):
    claim_id: str
    decision: Literal["supported", "contradicted", "unsupported", "severity_inflated"]
    calibrated_severity: Optional[Severity] = None
    rationale: str
    contradicting_ev: List[str] = Field(default_factory=list)

class CriticOutput(BaseModel):
    results: List[CriticResultItem] = Field(default_factory=list)

# ---------------------------------------------------------
# 5. Executive Synthesizer
# ---------------------------------------------------------

class SynthesizerFinancialImpact(BaseModel):
    cac_pressure: ImpactBand = "moderate"
    organic_pipeline_at_risk: Literal["low", "moderate", "high"] = "moderate"
    conversion_velocity_uplift: Literal["unknown", "low", "moderate", "high"] = "moderate"
    rationale: str = ""

class SynthesizerThreeWayComparison(BaseModel):
    human_visitor_perspective: str = ""
    search_engine_perspective: str = ""
    ai_answer_engine_perspective: str = ""

class SynthesizerOutput(BaseModel):
    story_summary: str
    what_site_gets_right: List[str] = Field(default_factory=list)
    what_is_holding_it_back: List[str] = Field(default_factory=list)
    primary_strategic_opportunity: str
    consultant_advice_what_to_ignore: str
    three_way_comparison: SynthesizerThreeWayComparison = Field(default_factory=SynthesizerThreeWayComparison)
    financial_impact_model: SynthesizerFinancialImpact = Field(default_factory=SynthesizerFinancialImpact)
    board_presentation_bullets: List[str] = Field(default_factory=list)

# ---------------------------------------------------------
# 6. Strategist
# ---------------------------------------------------------

class StrategistIceScore(BaseModel):
    impact: int = Field(default=5, ge=1, le=10)
    confidence: int = Field(default=5, ge=1, le=10)
    ease: int = Field(default=5, ge=1, le=10)
    basis: str = ""
    composite: Optional[float] = None

class StrategistOpportunity(BaseModel):
    title: str
    description: str
    strategic_value: Literal["High", "Moderate", "Low"] = "Moderate"
    effort: Literal["Low", "Medium", "High"] = "Medium"
    ice_score: StrategistIceScore = Field(default_factory=StrategistIceScore)
    expected_impact: str = ""

class StrategistRootCause(BaseModel):
    bottleneck: str
    causes_chain: List[str] = Field(default_factory=list)
    impact_explanation: str = ""

class StrategistOutput(BaseModel):
    primary_root_cause: StrategistRootCause = Field(default_factory=StrategistRootCause)
    growth_opportunities: List[StrategistOpportunity] = Field(default_factory=list)
    what_to_ignore: str = ""
    strategic_claims: List[Claim] = Field(default_factory=list)

# ---------------------------------------------------------
# 7. Specialized Business Understanding Intelligence Agents
# ---------------------------------------------------------

class AgentDiscoveryOutput(RobustSchemaModel):
    business_name: Optional[str] = None
    industry: str = "Unknown"
    sub_industry: Optional[str] = None
    what_company_does: str = ""
    who_it_serves: List[str] = Field(default_factory=list)
    what_it_sells: List[str] = Field(default_factory=list)
    how_it_makes_money: str = ""
    core_problem_solved: str = ""
    primary_business_objective: str = ""
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    evidence_excerpts: List[str] = Field(default_factory=list)

class AgentIntentJourneyOutput(RobustSchemaModel):
    primary_intent: str = "Unknown"
    secondary_intents: List[str] = Field(default_factory=list)
    journey_stages: List[str] = Field(default_factory=list)
    conversion_events: List[str] = Field(default_factory=list)
    entry_points: List[str] = Field(default_factory=list)
    decision_points: List[str] = Field(default_factory=list)
    exit_points: List[str] = Field(default_factory=list)
    friction_points: List[str] = Field(default_factory=list)
    missing_stages: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    evidence_excerpts: List[str] = Field(default_factory=list)

class AgentCategoryProductOutput(RobustSchemaModel):
    product_categories: List[str] = Field(default_factory=list)
    subcategories: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    service_categories: List[str] = Field(default_factory=list)
    product_families: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    audience_segments: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    evidence_excerpts: List[str] = Field(default_factory=list)

class AgentBusinessModelOutput(RobustSchemaModel):
    primary_model: str = "Unknown"
    secondary_model: Optional[str] = None
    commercial_motion: str = "unknown"
    conversion_model: str = ""
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    reasoning: str = ""
    evidence_excerpts: List[str] = Field(default_factory=list)

class AgentSemanticStrategistOutput(RobustSchemaModel):
    intent_alignment_analysis: str = ""
    architecture_supports_goal: bool = True
    value_proposition_clarity: str = ""
    machine_comprehension_assessment: str = ""
    contradictions_detected: List[str] = Field(default_factory=list)
    content_gaps: List[str] = Field(default_factory=list)
    strategic_hypotheses: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    evidence_excerpts: List[str] = Field(default_factory=list)

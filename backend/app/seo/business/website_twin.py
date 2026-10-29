"""
Dristik AI Website Digital Twin
Persistent, structured intelligence representation of each audited website.
Forms the long-term memory layer for historical tracking, simulation, and conversational inquiry.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.domain.models import BusinessProfile, PageEvidence, OverallScoreResult, Finding, CodePatch, AuditSnapshot

class ConversionPath(BaseModel):
    landing_url: str
    target_intent: str
    primary_cta: str
    friction_points: List[str] = Field(default_factory=list)
    has_clear_next_step: bool = False

class WebsiteDigitalTwin(BaseModel):
    twin_id: str
    domain: str
    base_url: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Core Architectural Dimensions
    business_profile: BusinessProfile = Field(default_factory=BusinessProfile)
    pages_count: int = 0
    pages_inventory: List[Dict[str, Any]] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    conversion_paths: List[ConversionPath] = Field(default_factory=list)

    # Health & Intelligence
    overall_health: Optional[OverallScoreResult] = None
    active_findings: List[Finding] = Field(default_factory=list)
    pending_patches: List[CodePatch] = Field(default_factory=list)
    ai_citation_readiness: Optional[float] = None
    historical_snapshots: List[AuditSnapshot] = Field(default_factory=list)

    def update_from_mission(
        self,
        business_profile: BusinessProfile,
        pages: List[PageEvidence],
        scores: Optional[OverallScoreResult],
        findings: List[Finding],
        patches: List[CodePatch]
    ):
        self.business_profile = business_profile
        self.pages_count = len(pages)
        self.pages_inventory = [
            {"url": p.url, "title": p.title, "type": p.page_type, "words": p.word_count, "schema": p.schema_types}
            for p in pages
        ]
        self.entities = list(set([st for p in pages for st in p.schema_types]))
        self.conversion_paths = [
            ConversionPath(
                landing_url=p.url,
                target_intent=p.page_type or "informational",
                primary_cta=business_profile.primary_cta or "",
                has_clear_next_step=bool(business_profile.primary_cta or p.ctas)
            )
            for p in pages[:5]
        ]
        self.overall_health = scores
        self.active_findings = findings
        self.pending_patches = patches
        self.last_updated = datetime.now().isoformat()

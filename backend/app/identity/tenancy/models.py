"""
Dristik AI Multi-Tenancy Hierarchy
Platform -> Organization -> Workspace -> Project -> Mission -> Evidence Graph Snapshot
"""
from typing import Optional, List, Dict, Any
import time
import uuid
from pydantic import BaseModel, Field
from app.domain.enums import DataResidency

class Organization(BaseModel):
    org_id: str = Field(default_factory=lambda: f"org_{uuid.uuid4().hex[:8]}")
    name: str
    slug: str
    plan: str = "enterprise"  # "starter", "professional", "business", "enterprise"
    data_residency: DataResidency = DataResidency.GLOBAL
    encryption_key_id: str = "kms_default_key"
    allowed_domains: List[str] = Field(default_factory=list)
    budget_limit_usd: float = 500.0
    budget_used_usd: float = 0.0
    max_concurrent_missions: int = 5
    created_at: float = Field(default_factory=time.time)
    is_active: bool = True
    is_legal_hold: bool = False
    deleted_at: Optional[float] = None

class Workspace(BaseModel):
    workspace_id: str = Field(default_factory=lambda: f"ws_{uuid.uuid4().hex[:8]}")
    org_id: str
    name: str
    slug: str
    created_at: float = Field(default_factory=time.time)
    is_active: bool = True
    deleted_at: Optional[float] = None

class Project(BaseModel):
    project_id: str = Field(default_factory=lambda: f"proj_{uuid.uuid4().hex[:8]}")
    workspace_id: str
    org_id: str
    name: str
    target_domains: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    deleted_at: Optional[float] = None

class MissionSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: f"snap_{uuid.uuid4().hex[:12]}")
    mission_id: str
    org_id: str
    workspace_id: str
    sealed_at: float = Field(default_factory=time.time)
    content_sha256_root: str
    pages_crawled_count: int
    findings_count: int
    s3_storage_uri: str
    immutable: bool = True

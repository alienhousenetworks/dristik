"""
Dristik AI Capability Registry & Matrix
Defines intelligence capabilities, dependencies, required connectors/evidence,
and honest machine-readable status evaluation (Zero Fake Results architecture).
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.domain.enums import CapabilityStatus, EvidenceOrigin

class CapabilityDeclaration(BaseModel):
    capability: str
    status: CapabilityStatus = CapabilityStatus.UNAVAILABLE
    required_connector: Optional[str] = None
    required_evidence: List[str] = Field(default_factory=list)
    description: str = ""

class ProvenanceItem(BaseModel):
    value: Any = None
    unit: Optional[str] = None
    source: str
    source_type: EvidenceOrigin
    evidence_refs: List[str] = Field(default_factory=list)
    observed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    calculation_method: Optional[str] = None
    verification_status: Optional[str] = None

class HonestResult(BaseModel):
    status: CapabilityStatus
    value: Optional[Any] = None
    message: str
    evidence_refs: List[str] = Field(default_factory=list)
    provenance: Optional[ProvenanceItem] = None

class CapabilityRegistry:
    def __init__(self):
        self._registry: Dict[str, CapabilityDeclaration] = {
            "google_search_console": CapabilityDeclaration(
                capability="google_search_console",
                status=CapabilityStatus.NOT_CONNECTED,
                required_connector="google_search_console",
                required_evidence=["verified_property", "search_analytics_response"],
                description="Google Search Console property impression & click telemetry"
            ),
            "search_volume": CapabilityDeclaration(
                capability="search_volume",
                status=CapabilityStatus.UNAVAILABLE,
                required_connector="keyword_volume_provider",
                required_evidence=["keyword_volume_response"],
                description="Live monthly keyword search volume instrument"
            ),
            "live_ai_citations": CapabilityDeclaration(
                capability="live_ai_citations",
                status=CapabilityStatus.UNAVAILABLE,
                required_connector="search_ai_provider",
                required_evidence=["live_engine_query_response"],
                description="Live web-grounded AI search citation testing"
            ),
            "competitor_discovery": CapabilityDeclaration(
                capability="competitor_discovery",
                status=CapabilityStatus.INSUFFICIENT_EVIDENCE,
                required_connector="serp_discovery_provider",
                required_evidence=["user_competitor_urls", "competitor_crawl_evidence"],
                description="Automated or user-supplied competitor discovery and benchmarking"
            ),
            "commercial_bakeoff": CapabilityDeclaration(
                capability="commercial_bakeoff",
                status=CapabilityStatus.INSUFFICIENT_EVIDENCE,
                required_connector=None,
                required_evidence=["competitor_crawl_evidence"],
                description="Side-by-side commercial buyer inquiry bake-off against rival"
            ),
            "revenue_attribution": CapabilityDeclaration(
                capability="revenue_attribution",
                status=CapabilityStatus.NOT_CONNECTED,
                required_connector="verified_revenue_analytics",
                required_evidence=["crm_or_analytics_conversion_data"],
                description="Attribution of search/AI visibility to actual commercial revenue"
            ),
            "patch_verification": CapabilityDeclaration(
                capability="patch_verification",
                status=CapabilityStatus.PENDING_VERIFICATION,
                required_connector=None,
                required_evidence=["post_patch_crawl_evidence"],
                description="Closed-loop verification of deployed patches via live re-crawl or CI checks"
            ),
            "shopify_connector": CapabilityDeclaration(
                capability="shopify_connector",
                status=CapabilityStatus.NOT_CONNECTED,
                required_connector="shopify",
                required_evidence=["shopify_admin_api_token", "shopify_store_auth"],
                description="Shopify Admin API for theme and metafield deployment"
            ),
            "wordpress_connector": CapabilityDeclaration(
                capability="wordpress_connector",
                status=CapabilityStatus.NOT_CONNECTED,
                required_connector="wordpress",
                required_evidence=["wordpress_auth_credentials"],
                description="WordPress REST API for Schema and metadata deployment"
            ),
            "github_connector": CapabilityDeclaration(
                capability="github_connector",
                status=CapabilityStatus.NOT_CONNECTED,
                required_connector="github",
                required_evidence=["github_token", "repo_write_access"],
                description="GitHub API for pull request creation and verification"
            ),
            "webflow_connector": CapabilityDeclaration(
                capability="webflow_connector",
                status=CapabilityStatus.NOT_CONNECTED,
                required_connector="webflow",
                required_evidence=["webflow_api_token"],
                description="Webflow API for custom code embed and collection updates"
            )
        }

    def is_declared(self, capability: str) -> bool:
        return capability in self._registry

    def get(self, capability: str) -> Optional[CapabilityDeclaration]:
        return self._registry.get(capability)

    def is_available(self, capability: str) -> bool:
        decl = self.get(capability)
        return decl is not None and decl.status == CapabilityStatus.AVAILABLE

    def create_unavailable_result(
        self,
        capability: str,
        reason_status: CapabilityStatus = CapabilityStatus.UNAVAILABLE,
        message: Optional[str] = None
    ) -> HonestResult:
        decl = self.get(capability)
        default_msg = message or (
            f"This capability is unavailable because required dependencies ({', '.join(decl.required_evidence) if decl else 'evidence'}) are not connected."
        )
        return HonestResult(
            status=reason_status,
            value=None,
            message=default_msg,
            evidence_refs=[]
        )

capability_registry = CapabilityRegistry()

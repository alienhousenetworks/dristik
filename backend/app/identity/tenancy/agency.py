"""
Dristik AI Agency Mode & Multi-Client Portfolio Workspace Engine
Allows digital marketing and SEO agencies to manage Client A, Client B, Client C, Client D, Client E
with white-label branding, automated monthly reporting, and client dashboards.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AgencyClientAccount(BaseModel):
    client_id: str
    client_name: str
    domain: str
    status: str # "ACTIVE", "AUDITING", "PENDING_AUDIT", "ATTENTION_REQUIRED"
    last_audit_date: Optional[str] = None
    human_score: Optional[int] = None
    google_score: Optional[int] = None
    ai_citation_score: Optional[int] = None
    overall_health: Optional[int] = None
    total_findings: int = 0
    monthly_budget_inr: float = 0.0
    white_label_enabled: bool = True
    org_id: str = ""

class AgencyBrandingSettings(BaseModel):
    agency_name: str = "My Agency Workspace"
    agency_logo_url: Optional[str] = None
    brand_primary_hex: str = "#0F766E"
    hide_dristik_branding: bool = True
    custom_cname: Optional[str] = None
    notification_webhook_url: Optional[str] = None

class AgencyWorkspaceSummary(BaseModel):
    agency_id: str
    agency_name: str
    plan_tier: str # "Agency Guard (₹14,999/mo)"
    total_managed_domains: int
    max_domain_allowance: int
    average_portfolio_citation_score: Optional[float] = None
    branding: AgencyBrandingSettings
    clients: List[AgencyClientAccount]
    monthly_report_schedule: str

class AgencyManager:
    """
    Manages multi-client agency portfolios and white-label asset generation.
    """

    def __init__(self):
        self._clients: List[AgencyClientAccount] = []
        self._branding = AgencyBrandingSettings()

    def _for_org(self, org_id: str) -> List[AgencyClientAccount]:
        return [client for client in self._clients if client.org_id == org_id]

    def get_workspace_summary(self, agency_id: str = "agency_default") -> AgencyWorkspaceSummary:
        clients = self._for_org(agency_id)
        measured_citations = [c.ai_citation_score for c in clients if c.ai_citation_score is not None]
        avg_citation = round(sum(measured_citations) / len(measured_citations), 1) if measured_citations else None

        return AgencyWorkspaceSummary(
            agency_id=agency_id,
            agency_name=self._branding.agency_name,
            plan_tier="Agency Multi-Domain Guard (₹14,999/mo)",
            total_managed_domains=len(clients),
            max_domain_allowance=10,
            average_portfolio_citation_score=avg_citation,
            branding=self._branding,
            clients=clients,
            monthly_report_schedule="1st of every calendar month (Automated Client PDF Delivery)"
        )

    def add_client(self, client_name: str, domain: str, org_id: str = "agency_default") -> AgencyClientAccount:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        new_client = AgencyClientAccount(
            client_id=f"cli_{uuid.uuid4().hex[:10]}",
            client_name=client_name,
            domain=domain,
            status="PENDING_AUDIT",
            last_audit_date=now_str,
            human_score=None,
            google_score=None,
            ai_citation_score=None,
            overall_health=None,
            total_findings=0,
            monthly_budget_inr=0.0,
            white_label_enabled=True,
            org_id=org_id,
        )
        self._clients.append(new_client)
        return new_client

    def remove_client(self, client_id: str, org_id: str = "agency_default") -> bool:
        initial_len = len(self._clients)
        self._clients = [
            client for client in self._clients
            if not (client.client_id == client_id and client.org_id == org_id)
        ]
        return len(self._clients) < initial_len

agency_manager = AgencyManager()

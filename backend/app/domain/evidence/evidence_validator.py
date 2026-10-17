"""
Dristik AI Evidence Gap Detector & Provenance Validator
Identifies unverified or unsupported marketing claims that lack backing technical documentation,
compliance certifications, or DOM evidence.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.domain.models import Claim, PageEvidence
from app.domain.evidence.store import EvidenceStore

class EvidenceGap(BaseModel):
    gap_id: str
    claim_id: str
    claim_statement: str
    domain: str
    missing_evidence_type: str
    recommended_evidence_source: str
    severity: str = "HIGH"
    description: str

class EvidenceGapDetector:
    """
    Scans claims against crawled pages to flag assertions that lack corroborating proof.
    """

    def detect_gaps(
        self,
        claims: List[Claim],
        evidence_store: EvidenceStore,
        pages: List[PageEvidence]
    ) -> List[EvidenceGap]:
        gaps: List[EvidenceGap] = []
        page_urls = [p.url.lower() for p in pages]
        has_security_page = any(any(k in u for k in ["security", "compliance", "trust", "soc2", "privacy"]) for u in page_urls)
        has_pricing_page = any(any(k in u for k in ["pricing", "price", "plans", "tier"]) for u in page_urls)
        has_docs_page = any(any(k in u for k in ["docs", "documentation", "api", "developer"]) for u in page_urls)

        gap_counter = 0

        for claim in claims:
            stmt = claim.statement.lower()

            # 1. Enterprise Security claim without dedicated documentation
            if any(k in stmt for k in ["enterprise-grade security", "soc 2", "soc2", "hipaa", "bank-grade", "iso 27001", "iso27001"]):
                if not has_security_page:
                    gap_counter += 1
                    gaps.append(EvidenceGap(
                        gap_id=f"gap_{gap_counter:03d}",
                        claim_id=claim.id,
                        claim_statement=claim.statement,
                        domain="SECURITY_COMPLIANCE",
                        missing_evidence_type="Security & Compliance Documentation / SOC2 Proof",
                        recommended_evidence_source="/security or /compliance page with verified badges",
                        severity="HIGH",
                        description="Website claims enterprise-grade security on marketing pages, but lacks verifiable security documentation or compliance certificates."
                    ))

            # 2. Transparent pricing claim without pricing page
            if any(k in stmt for k in ["transparent pricing", "starts at", "$", "affordable plans", "per month"]):
                if not has_pricing_page and len(claim.evidence_refs) == 0:
                    gap_counter += 1
                    gaps.append(EvidenceGap(
                        gap_id=f"gap_{gap_counter:03d}",
                        claim_id=claim.id,
                        claim_statement=claim.statement,
                        domain="COMMERCIAL_PRICING",
                        missing_evidence_type="Structured Pricing Table",
                        recommended_evidence_source="/pricing route with tier definitions",
                        severity="MEDIUM",
                        description="Pricing claims made without accessible pricing tables or transparent tier information."
                    ))

            # 3. Developer API claims without developer documentation
            if any(k in stmt for k in ["developer-first", "rest api", "sdk", "graphql", "webhooks"]):
                if not has_docs_page:
                    gap_counter += 1
                    gaps.append(EvidenceGap(
                        gap_id=f"gap_{gap_counter:03d}",
                        claim_id=claim.id,
                        claim_statement=claim.statement,
                        domain="DEVELOPER_EXPERIENCE",
                        missing_evidence_type="API Documentation / Developer Guides",
                        recommended_evidence_source="/docs or /developers section",
                        severity="MEDIUM",
                        description="Developer platform capabilities claimed without publicly discoverable API documentation."
                    ))

        return gaps

"""
Discovery Agent
Analyzes crawl manifest to organize site structure, key URL archetypes, and indexability posture.
"""
from typing import Dict, Any, List
from app.domain.models import CrawlManifest, Finding, FindingEvidence
from app.domain.enums import Category, Severity, EvidenceConfidence, VerificationStatus

class DiscoveryAgent:
    def __init__(self):
        self.agent_id = "discovery.v2"

    async def run(self, manifest: CrawlManifest) -> Dict[str, Any]:
        findings: List[Finding] = []

        # Check robots.txt
        if not manifest.robots_txt_found:
            findings.append(Finding(
                finding_id="DISC-101",
                category=Category.TECHNICAL_SEO,
                severity=Severity.MEDIUM,
                title="Missing robots.txt File",
                description="The website does not provide a robots.txt file, preventing explicit crawl governance for search engine bots and AI crawlers.",
                evidence=[FindingEvidence(
                    url=manifest.base_url,
                    element="robots.txt",
                    value="HTTP 404 / Not Found"
                )],
                rule_id="RULE_DISC_ROBOTS_TXT",
                confidence=1.0,
                confidence_label=EvidenceConfidence.CONFIRMED,
                impact=6,
                effort=1,
                priority=8,
                recommendation="Deploy a clean robots.txt at root containing Disallow rules for private paths and explicit Sitemap pointers.",
                verification_status=VerificationStatus.VERIFIED
            ))

        # Check sitemap
        if not manifest.sitemap_found:
            findings.append(Finding(
                finding_id="DISC-102",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title="Missing or Undiscoverable XML Sitemap",
                description="No XML sitemap was found at standard locations or referenced in robots.txt. Search engines and indexing agents may miss newly published or deep pages.",
                evidence=[FindingEvidence(
                    url=manifest.base_url,
                    element="sitemap.xml",
                    value="Missing in root /robots.txt"
                )],
                rule_id="RULE_DISC_SITEMAP_XML",
                confidence=0.95,
                confidence_label=EvidenceConfidence.CONFIRMED,
                impact=7,
                effort=2,
                priority=8,
                recommendation="Generate an automated XML sitemap (e.g., sitemap.xml) and declare its absolute URL in robots.txt.",
                verification_status=VerificationStatus.VERIFIED
            ))

        from app.cognition.finding_rubric import apply_rubric_to_finding
        for f in findings:
            if f.evidence and not f.evidence_refs:
                f.evidence_refs = [e.evidence_id for e in f.evidence if getattr(e, "evidence_id", None)]
            apply_rubric_to_finding(f)
        return {
            "agent_id": self.agent_id,
            "findings": [f.model_dump() for f in findings],
            "total_pages": len(manifest.pages),
            "status": "completed"
        }

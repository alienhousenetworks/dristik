"""
UX, Conversion Friction, and Trust Agent
Audits CTA hierarchy, conversion friction, contact accessibility, and trust signals.
"""
from typing import Dict, Any, List
from app.domain.models import CrawlManifest, BusinessProfile, Finding, FindingEvidence
from app.domain.enums import Category, Severity, EvidenceConfidence, VerificationStatus

class UxConversionAgent:
    def __init__(self):
        self.agent_id = "ux.conversion.v2"

    async def run(self, manifest: CrawlManifest, profile: BusinessProfile, global_signals: Dict[str, Any]) -> List[Finding]:
        findings: List[Finding] = []
        homepage = manifest.pages[0] if manifest.pages else None

        if not homepage:
            return findings

        trust_data = global_signals.get("trust", {})

        # 1. Contact / Reachability
        if not (trust_data.get("has_email_or_mailto") or trust_data.get("has_contact_page") or trust_data.get("has_phone_or_tel")):
            findings.append(Finding(
                finding_id="UX-601",
                category=Category.UX_CONVERSION,
                severity=Severity.HIGH,
                title="Missing Direct Contact or Inquiry Channel",
                description="The site does not expose a clear email, phone number, or dedicated contact page, significantly elevating conversion friction and hurting consumer trust.",
                evidence=[FindingEvidence(
                    url=homepage.url,
                    element="Footer / Header",
                    value="No mailto, tel, or /contact link detected"
                )],
                rule_id="RULE_UX_CONTACT_MISSING",
                confidence=0.95,
                confidence_label=EvidenceConfidence.CONFIRMED,
                impact=8,
                effort=1,
                priority=9,
                recommendation="Add a prominent 'Contact' link in the main navigation and embed a direct contact email in the footer.",
                verification_status=VerificationStatus.VERIFIED
            ))

        # 2. Social Proof / Authority Signals
        if trust_data.get("social_count", 0) == 0:
            findings.append(Finding(
                finding_id="UX-602",
                category=Category.TRUST_AUTHORITY,
                severity=Severity.LOW,
                title="No Verified Social Proof or External Profile Links",
                description="Zero social media profiles (LinkedIn, X/Twitter, GitHub, YouTube) were discovered. External social signals validate operational legitimacy for both users and search algorithms.",
                evidence=[FindingEvidence(
                    url=homepage.url,
                    element="Social links",
                    value="0 social links found"
                )],
                rule_id="RULE_UX_SOCIAL_PROOF",
                confidence=0.90,
                confidence_label=EvidenceConfidence.STRONG,
                impact=5,
                effort=1,
                priority=5,
                recommendation="Link verified company profiles (LinkedIn, X/Twitter) in the footer and include sameAs references in Schema.org.",
                verification_status=VerificationStatus.VERIFIED
            ))

        # 3. Privacy Policy & Compliance
        if not trust_data.get("has_privacy_policy"):
            findings.append(Finding(
                finding_id="UX-603",
                category=Category.TRUST_AUTHORITY,
                severity=Severity.MEDIUM,
                title="Missing Privacy Policy Link",
                description="No accessible Privacy Policy link detected. This is a baseline legal requirement for data collection, analytics tracking, and ad platforms.",
                evidence=[FindingEvidence(
                    url=homepage.url,
                    element="Footer",
                    value="No Privacy Policy link found"
                )],
                rule_id="RULE_UX_PRIVACY_MISSING",
                confidence=0.95,
                confidence_label=EvidenceConfidence.CONFIRMED,
                impact=6,
                effort=1,
                priority=7,
                recommendation="Publish a compliant Privacy Policy page and link it conspicuously in the footer.",
                verification_status=VerificationStatus.VERIFIED
            ))

        from app.cognition.finding_rubric import apply_rubric_to_finding
        for f in findings:
            if f.evidence and not f.evidence_refs:
                f.evidence_refs = [e.evidence_id for e in f.evidence if getattr(e, "evidence_id", None)]
            apply_rubric_to_finding(f)
        return findings

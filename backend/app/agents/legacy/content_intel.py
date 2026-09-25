"""
Content Intelligence Agent
Analyzes content depth, semantic completeness, user question coverage, and missing topical gaps.
"""
from typing import Dict, Any, List
from app.domain.models import CrawlManifest, BusinessProfile, Finding, FindingEvidence
from app.domain.enums import Category, Severity, EvidenceConfidence, VerificationStatus

class ContentIntelligenceAgent:
    def __init__(self):
        self.agent_id = "content.intel.v2"

    async def run(self, manifest: CrawlManifest, profile: BusinessProfile) -> List[Finding]:
        findings: List[Finding] = []
        homepage = manifest.pages[0] if manifest.pages else None

        if not homepage:
            return findings

        # 1. Thin Content Check
        if homepage.word_count < 250:
            findings.append(Finding(
                finding_id="CONT-301",
                category=Category.CONTENT,
                severity=Severity.HIGH,
                title="Thin Homepage Content Depth",
                description=f"The homepage contains only {homepage.word_count} words of indexable copy. Search engines require richer topical depth to establish domain authority and understand entity relationships.",
                evidence=[FindingEvidence(
                    url=homepage.url,
                    element="<body>",
                    value=f"Word count: {homepage.word_count} words"
                )],
                rule_id="RULE_CONT_THIN_CONTENT",
                confidence=1.0,
                confidence_label=EvidenceConfidence.CONFIRMED,
                impact=7,
                effort=4,
                priority=7,
                recommendation="Expand homepage copy to at least 600-800 words, including section breakdowns of primary features/services, client proof, and problem-solution context.",
                verification_status=VerificationStatus.VERIFIED
            ))

        # 2. Readability & Complexity
        if homepage.readability_score > 0 and homepage.readability_score < 40:
            findings.append(Finding(
                finding_id="CONT-302",
                category=Category.CONTENT,
                severity=Severity.MEDIUM,
                title="Low Content Readability (Overly Dense Copy)",
                description=f"The calculated Flesch Reading Ease is {homepage.readability_score}/100 (difficult/academic). High sentence complexity increases bounce rate and hampers casual skimmers.",
                evidence=[FindingEvidence(
                    url=homepage.url,
                    element="Text flow",
                    value=f"Flesch Reading Ease: {homepage.readability_score}/100"
                )],
                rule_id="RULE_CONT_READABILITY",
                confidence=0.88,
                confidence_label=EvidenceConfidence.STRONG,
                impact=5,
                effort=3,
                priority=5,
                recommendation="Break down complex sentences, use active voice, and aim for a reading ease score between 55-70.",
                verification_status=VerificationStatus.VERIFIED
            ))

        # 3. Missing FAQ / Question Coverage
        has_faq_page = any(p.page_type == "pricing" or "faq" in p.url.lower() for p in manifest.pages)
        has_faq_h2 = any("faq" in h.lower() or "question" in h.lower() for h in homepage.h2)
        if not (has_faq_page or has_faq_h2):
            findings.append(Finding(
                finding_id="CONT-303",
                category=Category.CONTENT,
                severity=Severity.MEDIUM,
                title="Missing Frequently Asked Questions (FAQ) Section",
                description="The website lacks structured FAQ content addressing common buyer objections, onboarding queries, and service parameters.",
                evidence=[FindingEvidence(
                    url=homepage.url,
                    element="Headings & Pages",
                    value="No FAQ section or FAQPage detected"
                )],
                rule_id="RULE_CONT_FAQ_MISSING",
                confidence=0.90,
                confidence_label=EvidenceConfidence.STRONG,
                impact=6,
                effort=2,
                priority=7,
                recommendation=f"Add a dedicated FAQ section to {homepage.url} addressing top customer questions regarding {profile.niche}.",
                verification_status=VerificationStatus.VERIFIED
            ))

        # 4. Missing Comparison / Alternatives Context
        if profile.primary_intent.value in ("saas", "agency"):
            has_comparison = any("vs" in p.url.lower() or "compare" in p.url.lower() or "alternative" in p.url.lower() for p in manifest.pages)
            if not has_comparison:
                findings.append(Finding(
                    finding_id="CONT-304",
                    category=Category.CONTENT,
                    severity=Severity.LOW,
                    title="Absence of Competitive Comparison / 'Alternative To' Content",
                    description="High-intent buyers frequently search for comparison queries (e.g. '[Brand] vs [Competitor]'). The site currently yields this search volume to third-party review directories.",
                    evidence=[FindingEvidence(
                        url=manifest.base_url,
                        element="Discovered URLs",
                        value="0 comparison or alternative pages found"
                    )],
                    rule_id="RULE_CONT_COMPARISON_PAGES",
                    confidence=0.85,
                    confidence_label=EvidenceConfidence.LIKELY,
                    impact=7,
                    effort=5,
                    priority=6,
                    recommendation="Publish transparent comparison guides detailing how your solution compares against legacy or market alternatives.",
                    verification_status=VerificationStatus.VERIFIED
                ))

        from app.cognition.finding_rubric import apply_rubric_to_finding
        for f in findings:
            if f.evidence and not f.evidence_refs:
                f.evidence_refs = [e.evidence_id for e in f.evidence if getattr(e, "evidence_id", None)]
            apply_rubric_to_finding(f)
        return findings

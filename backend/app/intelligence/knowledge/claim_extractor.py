"""
Dristik KIE — Phase 1: Atomic Claim Extractor
Deconstructs crawled page sentences into structured AtomicClaims with:
  - ClaimType classification (FACT, CAPABILITY, MARKETING, PROMISE, OPINION)
  - EvidenceState assignment
  - EvidenceStrength estimation
  - Source URL, section, and exact sentence attribution
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.domain.models import PageEvidence
from app.intelligence.knowledge.primitives import (
    AtomicClaim,
    KieClaimType,
    KieEvidence,
    KieEvidenceState,
    KieEvidenceStrength,
    KnowledgeSourceTier,
    PageRole,
)
from app.intelligence.knowledge.page_classifier import PageKnowledgeClassifier


# ─────────────────────────────────────────────────────────────────────────────
# Signal Libraries
# ─────────────────────────────────────────────────────────────────────────────

_FACT_SIGNALS = [
    # Verifiable certifications and credentials
    r"\bsoc\s*2\s*type\s*(i{1,2}|1|2)\b",
    r"\biso\s*27001\b",
    r"\bhipaa\b",
    r"\bgdpr\b",
    r"\bccpa\b",
    r"\bpci[- ]dss\b",
    r"\baes[- ]256\b",
    r"\btls\s*1\.[23]\b",
    # Concrete pricing with currency symbols
    r"[\$€£₹]\s*\d+",
    r"\d+\s*/\s*(?:month|mo|year|yr|user|seat|node|cluster)",
    # Specific technical facts
    r"\b(?:rest|graphql)\s+api\b",
    r"\b99\.?\d*%\s+uptime\b",
]

_CAPABILITY_SIGNALS = [
    r"\bautomati(?:c|on|cally)\b",
    r"\bintegrat(?:e|es|ion|ions)\b",
    r"\bsupport(?:s|ed|ing)\b",
    r"\bprovid(?:e|es|ing)\b",
    r"\benabl(?:e|es|ing)\b",
    r"\ballow(?:s|ing)\b",
    r"\bmonitor(?:s|ing)\b",
    r"\btrack(?:s|ing)\b",
    r"\bscal(?:e|es|able|ability)\b",
    r"\bdeploy(?:s|ed|ing|ment)\b",
    r"\bconnect(?:s|ing|or)\b",
    r"\banalyti(?:c|cs)\b",
    r"\bdashboard\b",
    r"\bworkflow\b",
]

_PROMISE_SIGNALS = [
    r"\bsla\b",
    r"\bguarantee\b",
    r"\bcommit\b",
    r"\bpromise\b",
    r"\buptime\b",
    r"\bresponse time\b",
    r"\bwithin\s+\d+\s+(?:hours?|days?|minutes?)\b",
    r"\bpenalty\b",
    r"\bcompensati(?:on|ons)\b",
]

_MARKETING_SIGNALS = [
    r"\b(?:world[- ]?class|industry[- ]?leading|best[- ]?in[- ]?class|cutting[- ]?edge)\b",
    r"\b(?:revolutionary|game[- ]?changer|disruptive|pioneering|unparalleled)\b",
    r"\b(?:seamless|effortless|powerful|robust|comprehensive)\b",
    r"\b(?:trusted by|loved by|relied on by)\b",
    r"\b(?:most|fastest|easiest|simplest|only)\s+(?:platform|solution|tool)\b",
]

_HIGH_STRENGTH_PATTERNS = [
    # Pricing page, security page with certified entities
    (PageRole.PRICING, [r"[\$€£₹]\s*\d+", r"per\s+(?:month|user|seat|node|cluster)"]),
    (PageRole.SECURITY, [r"\bsoc\s*2\b", r"\biso\s*27001\b", r"\bhipaa\b", r"\bgdpr\b"]),
    (PageRole.LEGAL, [r"\bterms\b", r"\bprivacy\b", r"\bdata\s+processing\b"]),
    (PageRole.DOCUMENTATION, [r"\bapi\b", r"\brest\b", r"\bwebhook\b"]),
]


# ─────────────────────────────────────────────────────────────────────────────
# Sentence Boundary Tokenizer
# ─────────────────────────────────────────────────────────────────────────────

def _split_sentences(text: str) -> List[str]:
    """
    Split body text into sentence-bounded units.
    Avoids mid-word truncation that caused inaccurate evidence snippets in the old engine.
    """
    # Protect common abbreviations before splitting
    protected = re.sub(r"\b(e\.g|i\.e|vs|etc|fig|dr|mr|ms|prof|no|vol|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\.", r"\1<PROT>", text, flags=re.IGNORECASE)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"])", protected)
    # Restore, strip, and filter short noise
    return [
        s.replace("<PROT>", ".").strip()
        for s in sentences
        if len(s.strip()) > 20
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Claim Extractor
# ─────────────────────────────────────────────────────────────────────────────

class AtomicClaimExtractor:
    """
    Phase 1 KIE component.
    Deconstructs crawled pages into structured AtomicClaim records.
    Uses sentence-boundary splitting (no arbitrary character windows)
    and signal-based claim type classification.
    """

    def __init__(self, brand: str, crawl_timestamp: Optional[str] = None):
        self.brand = brand.lower()
        self._timestamp = crawl_timestamp or ""

    def extract_from_pages(self, pages: List[PageEvidence]) -> List[AtomicClaim]:
        claims: List[AtomicClaim] = []
        classifications = PageKnowledgeClassifier.classify_all(pages)
        class_map = {c.url: c for c in classifications}

        for page in pages:
            classification = class_map.get(page.url)
            page_role = classification.page_role if classification else PageRole.UNKNOWN
            new_claims = self._extract_from_page(page, page_role)
            claims.extend(new_claims)

        return claims

    def _extract_from_page(
        self, page: PageEvidence, page_role: PageRole
    ) -> List[AtomicClaim]:
        claims: List[AtomicClaim] = []
        text_body = page.body_text or ""
        sentences = _split_sentences(text_body)

        # Also treat each h1/h2 heading as a standalone sentence
        for heading in (page.h1 or []) + (page.h2 or []):
            if heading and heading.strip() not in [s[:len(heading)] for s in sentences]:
                sentences.insert(0, heading.strip())

        for sentence in sentences:
            if len(sentence.strip()) < 20:
                continue
            claim = self._sentence_to_claim(sentence, page, page_role)
            if claim:
                claims.append(claim)

        return claims

    def _sentence_to_claim(
        self,
        sentence: str,
        page: PageEvidence,
        page_role: PageRole,
    ) -> Optional[AtomicClaim]:
        sl = sentence.lower()

        # Only extract sentences that appear to relate to the brand or its offerings
        brand_adjacent = (
            self.brand in sl or
            any(kw in sl for kw in ["we ", "our ", "the platform", "the product", "the service"])
        )
        if not brand_adjacent and len(sentence) < 60:
            return None

        claim_type = self._classify_claim_type(sl)
        evidence_strength = self._estimate_strength(sl, page_role)
        predicate, obj = self._extract_predicate_object(sentence)

        evidence = KieEvidence(
            evidence_id=f"EV_{uuid.uuid4().hex[:8].upper()}",
            url=page.url or "",
            page_role=page_role,
            section=self._infer_section(page, sentence),
            exact_sentence=sentence[:400],
            source_tier=KnowledgeSourceTier.FIRST_PARTY,
            strength=evidence_strength,
        )

        return AtomicClaim(
            claim_id=f"CLM_{uuid.uuid4().hex[:8].upper()}",
            subject=self.brand,
            predicate=predicate,
            object=obj,
            claim_type=claim_type,
            evidence_state=KieEvidenceState.SUPPORTED,
            evidence_strength=evidence_strength,
            confidence=self._estimate_confidence(claim_type, evidence_strength),
            evidence=evidence,
        )

    def _classify_claim_type(self, text_lower: str) -> KieClaimType:
        if any(re.search(p, text_lower) for p in _FACT_SIGNALS):
            return KieClaimType.FACT
        if any(re.search(p, text_lower) for p in _PROMISE_SIGNALS):
            return KieClaimType.PROMISE
        if any(re.search(p, text_lower) for p in _MARKETING_SIGNALS):
            return KieClaimType.MARKETING
        if any(re.search(p, text_lower) for p in _CAPABILITY_SIGNALS):
            return KieClaimType.CAPABILITY
        return KieClaimType.CAPABILITY  # Sensible default for product pages

    def _estimate_strength(self, text_lower: str, page_role: PageRole) -> KieEvidenceStrength:
        for role, patterns in _HIGH_STRENGTH_PATTERNS:
            if page_role == role and any(re.search(p, text_lower) for p in patterns):
                return KieEvidenceStrength.HIGH
        if page_role in (PageRole.PRICING, PageRole.SECURITY, PageRole.LEGAL, PageRole.DOCUMENTATION):
            return KieEvidenceStrength.HIGH
        if page_role in (PageRole.ABOUT, PageRole.PRODUCT, PageRole.SERVICES, PageRole.CASE_STUDY, PageRole.FAQ):
            return KieEvidenceStrength.MEDIUM
        return KieEvidenceStrength.LOW

    def _estimate_confidence(
        self, claim_type: KieClaimType, strength: KieEvidenceStrength
    ) -> float:
        base = {
            KieClaimType.FACT: 0.95,
            KieClaimType.PROMISE: 0.85,
            KieClaimType.CAPABILITY: 0.80,
            KieClaimType.OPINION: 0.60,
            KieClaimType.MARKETING: 0.55,
        }.get(claim_type, 0.70)
        strength_mod = {
            KieEvidenceStrength.HIGH: 0.0,
            KieEvidenceStrength.MEDIUM: -0.05,
            KieEvidenceStrength.LOW: -0.15,
        }.get(strength, 0.0)
        return round(max(0.30, base + strength_mod), 2)

    def _extract_predicate_object(self, sentence: str) -> Tuple[str, str]:
        """
        Simple heuristic predicate / object extractor.
        Returns (predicate_verb_phrase, object_noun_phrase).
        Good enough for Phase 1; the Query Planner uses the full sentence anyway.
        """
        # Pattern: "X provides/offers/supports Y"
        m = re.search(
            r"\b(?:provides?|offers?|supports?|delivers?|enables?|includes?|features?|builds?|"
            r"integrates?\s+with|is\s+certified\s+(?:for|by)|is\s+compliant\s+with|"
            r"uses?|runs?\s+on|powers?)\b(.{5,80}?)(?:[.,;!?]|$)",
            sentence, re.IGNORECASE
        )
        if m:
            verb_match = re.search(
                r"\b(provides?|offers?|supports?|delivers?|enables?|includes?|features?|builds?|"
                r"integrates?\s+with|is\s+certified|is\s+compliant|uses?|runs?\s+on|powers?)\b",
                sentence, re.IGNORECASE
            )
            predicate = verb_match.group(0).lower() if verb_match else "relates_to"
            obj = m.group(1).strip()[:120]
            return predicate, obj

        # Fallback: take the last noun phrase
        obj = re.sub(r"\s+", " ", sentence[:120]).strip()
        return "states", obj

    def _infer_section(self, page: PageEvidence, sentence: str) -> Optional[str]:
        """
        Guess which page section the sentence belongs to (heading proximity).
        """
        all_headings = (page.h1 or []) + (page.h2 or [])
        if all_headings:
            return all_headings[0][:80]
        return None

"""
Claim & Triple Extraction Pipeline.
Layer 1 Extractability: What Dristik can prove deterministically from the website itself.

Extracts factual claims as structured triples:
(Subject, Predicate, Object, Evidence URL, Specificity, Verifiability)

Evaluates:
- Claim Clarity: Can an AI extract the claim?
- Claim Specificity: Is it "We build innovative solutions" (vague) or
  "AlienHouse builds FastAPI-based AI applications for SaaS companies" (machine-citable)?
- Claim Evidence: Is the claim substantiated by metrics, case studies, or certifications?
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from app.domain.models import PageEvidence

ClaimType = Literal["service", "pricing", "leadership", "metric", "icp", "compliance", "geographic", "general"]

# Marketing fluff buzzwords that degrade AI machine extractability
FLUFF_TOKENS = {
    "revolutionize", "revolutionary", "empower", "empowering", "unprecedented",
    "cutting-edge", "seamless", "seamlessly", "next-generation", "next-gen",
    "unlock growth", "future of business", "game-changer", "gamechanger",
    "game-changing", "innovative solutions", "synergy", "reimagine",
    "all-in-one platform", "world-class", "best-in-class", "disrupt",
    "transform your", "magic", "limitless", "supercharge", "future-proof"
}

# Technical, architectural, and factual domain anchors
CONCRETE_TECH_ANCHORS = {
    "python", "fastapi", "react", "next.js", "vue", "angular", "node.js",
    "typescript", "javascript", "golang", "rust", "docker", "kubernetes",
    "aws", "gcp", "azure", "postgresql", "mongodb", "redis", "kafka",
    "graphql", "rest api", "llm", "langchain", "pytorch", "tensorflow",
    "tailwind", "supabase", "stripe", "openai", "claude", "gemini"
}

# Compliance and enterprise verification anchors
COMPLIANCE_ANCHORS = {
    "soc 2", "soc2", "iso 27001", "iso27001", "hipaa", "gdpr", "ccpa",
    "pci-dss", "pci dss", "fedramp", "sla", "uptime", "zero trust", "end-to-end encrypted"
}


class GeoClaim(BaseModel):
    claim_id: str
    subject: str          # e.g., "AlienHouse Networks"
    predicate: str        # e.g., "develops"
    object: str           # e.g., "FastAPI and GenAI web applications"
    source_url: str
    evidence_passage: str
    claim_type: ClaimType
    specificity_score: float   # 0.0 to 1.0 (vague vs concrete)
    verifiability_score: float # 0.0 to 1.0 (supported by stats/case studies vs fluff)
    is_fluff: bool = False
    fluff_terms: List[str] = Field(default_factory=list)
    anchors_detected: List[str] = Field(default_factory=list)
    machine_citable: bool = False


class ClaimsAnalysisResult(BaseModel):
    total_claims_extracted: int
    citable_claims_count: int
    fluff_claims_count: int
    aggregate_specificity_score: float   # 0 - 100
    aggregate_verifiability_score: float # 0 - 100
    claim_clarity_score: float          # 0 - 100
    claims: List[GeoClaim] = Field(default_factory=list)
    high_value_triples: List[Dict[str, str]] = Field(default_factory=list)
    summary: str = ""


class GeoClaimExtractor:
    """
    Extracts structured claims and knowledge triples directly from crawled pages.
    """

    def __init__(self, canonical_brand: str = ""):
        self.canonical_brand = canonical_brand

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _detect_claim_type(self, sentence: str) -> ClaimType:
        low = sentence.lower()
        if re.search(r"(\$|€|£|₹|\bfree\b|\bmonth\b|\byear\b|\bpricing\b|\btier\b|\bplan\b)", low):
            return "pricing"
        if any(c in low for c in COMPLIANCE_ANCHORS):
            return "compliance"
        if re.search(r"(\d+%\s*|\b\d+\+?\s*(?:users|clients|customers|ms|seconds|hours|deals)\b|\buptime\b)", low):
            return "metric"
        if re.search(r"(?:built for|designed for|for teams|for startups|for enterprises|for developers|target)", low):
            return "icp"
        if re.search(r"(?:founded in|founded by|headquartered|based in|team of|our mission)", low):
            return "leadership"
        if re.search(r"(?:located in|offices in|serving customers in|global operations)", low):
            return "geographic"
        if re.search(r"(?:provides|develops|builds|specializes|offers|delivers|automates|architects|integrates)", low):
            return "service"
        return "general"

    def _extract_triple(self, sentence: str, brand_name: str) -> Tuple[str, str, str]:
        """
        Extracts (subject, predicate, object) from a declarative sentence.
        Uses structured regex patterns for subject-verb-object detection.
        """
        brand = brand_name or "The company"
        s = self._clean_text(sentence)

        # Pattern 1: [Brand / We] [Predicate Verb] [Object]
        pred_patterns = [
            (r"^(?:we\s+|" + re.escape(brand) + r"\s+)?(provide[s]?|develop[s]?|build[s]?|specialize[s]?\s+in|offer[s]?|deliver[s]?|automate[s]?|architect[s]?|support[s]?)\s+(.+)$", "provides"),
            (r"^(?:we\s+|" + re.escape(brand) + r"\s+)?(help[s]?\s+[a-z\s]+\s+to)\s+(.+)$", "helps"),
            (r"^(?:we\s+|" + re.escape(brand) + r"\s+)?(is\s+a|are\s+a|is\s+an|are\s+an)\s+(.+)$", "is"),
            (r"^(?:we\s+|" + re.escape(brand) + r"\s+)?(operate[s]?\s+in|headquartered\s+in|based\s+in)\s+(.+)$", "based_in"),
            (r"^(?:pricing\s+starts\s+at|plans\s+start\s+at|cost[s]?)\s+(.+)$", "costs"),
        ]

        for pat, default_pred in pred_patterns:
            m = re.search(pat, s, re.IGNORECASE)
            if m:
                subj = brand
                if m.lastindex and m.lastindex >= 2:
                    pred = m.group(1).strip()
                    obj = m.group(2).strip()
                elif m.lastindex == 1:
                    pred = default_pred
                    obj = m.group(1).strip()
                else:
                    pred = default_pred
                    obj = s
                # Clean trailing periods
                obj = re.sub(r"[\.;,]$", "", obj)
                return subj, pred, obj

        # Fallback split
        words = s.split()
        if len(words) >= 6:
            subj = brand
            pred = "offers"
            obj = " ".join(words[2:])
            return subj, pred, obj

        return brand, "states", s

    def _score_claim(self, sentence: str, obj: str) -> Tuple[float, float, bool, List[str], List[str]]:
        low_sent = sentence.lower()
        low_obj = obj.lower()

        # Detect fluff buzzwords
        fluff_found = [tok for tok in FLUFF_TOKENS if tok in low_sent]
        is_fluff = len(fluff_found) > 0

        # Detect concrete anchors
        anchors_found = []
        for tech in CONCRETE_TECH_ANCHORS:
            if re.search(rf"\b{re.escape(tech)}\b", low_sent):
                anchors_found.append(tech)
        for comp in COMPLIANCE_ANCHORS:
            if comp in low_sent:
                anchors_found.append(comp)

        # Numbers, currencies, metrics
        metric_matches = re.findall(r"(?:\$|€|£|₹|\b\d+[\.,]?\d*\+?%?|\b\d+/\d+\b)", sentence)
        if metric_matches:
            anchors_found.extend(metric_matches[:2])

        # Specificity calculation (0.0 to 1.0)
        # Base: 0.50
        # +0.15 per concrete anchor (up to +0.35)
        # -0.20 per fluff token (down to -0.40)
        # +0.10 if word count is 8-25 words
        spec = 0.50
        spec += min(0.35, len(anchors_found) * 0.15)
        spec -= min(0.40, len(fluff_found) * 0.20)
        if 8 <= len(sentence.split()) <= 25:
            spec += 0.10
        spec = max(0.10, min(0.98, spec))

        # Verifiability calculation (0.0 to 1.0)
        # Higher if explicit metrics, compliance, pricing, or external anchors exist
        verif = 0.40
        if metric_matches:
            verif += 0.30
        if any(c in low_sent for c in COMPLIANCE_ANCHORS):
            verif += 0.30
        if len(anchors_found) >= 2:
            verif += 0.15
        if is_fluff:
            verif -= 0.25
        verif = max(0.10, min(0.99, verif))

        return round(spec, 2), round(verif, 2), is_fluff, fluff_found, anchors_found

    def extract_claims(
        self,
        pages: List[PageEvidence],
        brand_name: str = ""
    ) -> ClaimsAnalysisResult:
        brand = brand_name or self.canonical_brand or "The Company"
        claims: List[GeoClaim] = []
        high_value_triples: List[Dict[str, str]] = []
        seen_sentences: Set[str] = set()

        claim_idx = 1
        for p in pages:
            url = p.url or ""

            # Check headings first (H1, H2)
            candidate_lines = (p.h1 or []) + (p.h2 or [])

            # Add sentences from body text
            body = p.body_text or ""
            # Split by period, exclamation, or newline
            sentences = re.split(r"(?<=[.!?])\s+|\n+", body)
            for s in sentences:
                s_clean = self._clean_text(s)
                # Keep sentences between 30 and 220 chars that look declarative
                if 30 <= len(s_clean) <= 220 and len(s_clean.split()) >= 5:
                    candidate_lines.append(s_clean)

            for line in candidate_lines:
                clean_line = self._clean_text(line)
                if clean_line in seen_sentences or len(clean_line) < 25:
                    continue
                seen_sentences.add(clean_line)

                claim_type = self._detect_claim_type(clean_line)
                subj, pred, obj = self._extract_triple(clean_line, brand)
                spec, verif, is_fluff, fluff_found, anchors = self._score_claim(clean_line, obj)

                # Machine citable if specificity >= 0.70 and not pure fluff
                machine_citable = (spec >= 0.65 and not is_fluff) or (verif >= 0.70)

                cid = f"CLM-{claim_idx:03d}"
                claim_idx += 1

                claim_obj = GeoClaim(
                    claim_id=cid,
                    subject=subj,
                    predicate=pred,
                    object=obj,
                    source_url=url,
                    evidence_passage=clean_line,
                    claim_type=claim_type,
                    specificity_score=spec,
                    verifiability_score=verif,
                    is_fluff=is_fluff,
                    fluff_terms=fluff_found,
                    anchors_detected=anchors,
                    machine_citable=machine_citable,
                )
                claims.append(claim_obj)

                if machine_citable and len(high_value_triples) < 15:
                    high_value_triples.append({
                        "subject": subj,
                        "predicate": pred,
                        "object": obj,
                        "source_url": url,
                        "type": claim_type,
                        "specificity": f"{spec:.2f}"
                    })

                if len(claims) >= 35:
                    break
            if len(claims) >= 35:
                break

        if not claims:
            return ClaimsAnalysisResult(
                total_claims_extracted=0,
                citable_claims_count=0,
                fluff_claims_count=0,
                aggregate_specificity_score=50.0,
                aggregate_verifiability_score=40.0,
                claim_clarity_score=45.0,
                claims=[],
                high_value_triples=[],
                summary="No machine-extractable declarative claims identified on crawled pages.",
            )

        citable_count = sum(1 for c in claims if c.machine_citable)
        fluff_count = sum(1 for c in claims if c.is_fluff)
        avg_spec = sum(c.specificity_score for c in claims) / len(claims) * 100.0
        avg_verif = sum(c.verifiability_score for c in claims) / len(claims) * 100.0
        clarity_score = (avg_spec * 0.60) + (avg_verif * 0.40)

        summary = (
            f"Extracted {len(claims)} declarative claims across crawled pages. "
            f"{citable_count} are high-specificity machine-citable triples; "
            f"{fluff_count} rely on subjective marketing fluff. "
            f"Average claim specificity: {avg_spec:.1f}%, verifiability: {avg_verif:.1f}%."
        )

        return ClaimsAnalysisResult(
            total_claims_extracted=len(claims),
            citable_claims_count=citable_count,
            fluff_claims_count=fluff_count,
            aggregate_specificity_score=round(avg_spec, 1),
            aggregate_verifiability_score=round(avg_verif, 1),
            claim_clarity_score=round(clarity_score, 1),
            claims=claims,
            high_value_triples=high_value_triples,
            summary=summary,
        )


claim_extractor = GeoClaimExtractor()

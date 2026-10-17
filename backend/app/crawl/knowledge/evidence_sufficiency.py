"""
Dristik KIE — Evidence Sufficiency Evaluator
Evaluates whether retrieved first-party evidence is sufficient, partial,
conflicting, or entirely absent for a given buyer inquiry before synthesis.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.crawl.retrieval.hybrid_retriever import RetrievedEvidenceChunk, _tokenize


class EvidenceAssessment(BaseModel):
    status: str  # "SUFFICIENT" | "PARTIAL" | "INSUFFICIENT" | "CONFLICTING"
    coverage_ratio: float = 0.0  # 0.0 to 1.0
    evidence_count: int = 0
    supported_aspects: List[str] = Field(default_factory=list)
    missing_aspects: List[str] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class EvidenceSufficiencyEvaluator:
    """
    Evaluates evidence sufficiency across multi-aspect buyer inquiries.
    Enforces that having *some* evidence does not mean a question is fully answerable.
    """

    # Common multi-aspect conjunction markers
    _ASPECT_CONJUNCTIONS = re.compile(r"\b(?:and\s+what|and\s+how|and\s+who|and\s+their|and\s+its|as\s+well\s+as)\b", re.IGNORECASE)

    @classmethod
    def evaluate(
        cls,
        question: str,
        evidence_chunks: List[RetrievedEvidenceChunk],
        brand: str,
    ) -> EvidenceAssessment:
        if not evidence_chunks:
            return EvidenceAssessment(
                status="INSUFFICIENT",
                coverage_ratio=0.0,
                evidence_count=0,
                missing_aspects=[question.strip()],
                summary=f"No relevant first-party evidence found on {brand}'s crawled pages."
            )

        # Decompose compound questions into sub-aspects
        aspects = cls._extract_inquiry_aspects(question, brand)
        if not aspects:
            aspects = [question.strip()]

        combined_evidence_text = " ".join(
            f"{c.claim.predicate} {c.claim.object} {c.claim.evidence.exact_sentence if c.claim.evidence else ''}"
            for c in evidence_chunks
        ).lower()

        supported: List[str] = []
        missing: List[str] = []

        brand_tokens = set(_tokenize(brand))

        combined_evidence_tokens = set(_tokenize(combined_evidence_text))

        for aspect in aspects:
            asp_lower = aspect.lower()
            # If aspect is an identity question (e.g. "What is [Brand]"), check if evidence contains core offering claims
            is_identity_inquiry = any(k in asp_lower for k in ["what is", "who is", "what exactly is", "what does", "mission"])
            has_identity_evidence = any(
                c.claim.predicate in ("provides", "is", "delivers", "offers", "builds")
                for c in evidence_chunks
            )
            if is_identity_inquiry and has_identity_evidence:
                supported.append(aspect)
                continue

            asp_tokens = [t for t in _tokenize(aspect) if t not in brand_tokens]
            if not asp_tokens:
                # If only brand tokens existed (e.g. "What is Acme Observability"), it is supported if we have brand evidence
                if evidence_chunks:
                    supported.append(aspect)
                else:
                    missing.append(aspect)
                continue

            # Factual domain requirements:
            # 1. Pricing: If aspect asks about price/pricing/cost/tier, evidence must contain pricing markers
            if any(k in asp_lower for k in ["price", "pricing", "cost", "tier", "monthly", "subscription", "rate"]):
                has_pricing_signal = any(p in combined_evidence_text for p in ["$", "€", "£", "₹", "/mo", "per month", "pricing", "tier", "plan", "cost", "quote"])
                if not has_pricing_signal:
                    missing.append(aspect)
                    continue

            # 2. Security/Certifications: If aspect asks for certifications (SOC 2, ISO, HIPAA)
            if any(k in asp_lower for k in ["soc 2", "iso 27001", "hipaa", "gdpr", "certified", "certification"]):
                has_cert_signal = any(c in combined_evidence_text for c in ["soc 2", "iso 27001", "hipaa", "gdpr", "certified", "certification", "compliance"])
                if not has_cert_signal:
                    missing.append(aspect)
                    continue

            # 3. Customer Proof: If aspect asks for customer logos, case studies, or ROI
            if any(k in asp_lower for k in ["case study", "customer logo", "client logo", "quantified roi", "testimonial"]):
                has_proof_signal = any(p in combined_evidence_text for p in ["case study", "customer", "client", "testimonial", "roi", "reduction", "%", "saved"])
                if not has_proof_signal:
                    missing.append(aspect)
                    continue

            # 4. Competitive comparison: If aspect asks for comparison or alternatives
            if any(k in asp_lower for k in ["compare directly", "competing", "versus", "vs ", "alternative", "unlike"]):
                has_comp_signal = any(c in combined_evidence_text for c in ["unlike", "compared to", "alternative", "competitor", "differ", "versus"])
                if not has_comp_signal:
                    missing.append(aspect)
                    continue

            # 5. Support SLA: If aspect asks for SLA or response time
            if any(k in asp_lower for k in ["sla", "response time", "ticket response"]):
                has_sla_signal = any(s in combined_evidence_text for s in ["sla", "response time", "within", "hours", "minutes", "uptime"])
                if not has_sla_signal:
                    missing.append(aspect)
                    continue

            # Check overlap between aspect tokens and evidence tokens (exact or root prefix e.g. provide/provides)
            matched_tokens = []
            for t in asp_tokens:
                if t in combined_evidence_tokens or (len(t) >= 4 and any(ev_w.startswith(t[:4]) for ev_w in combined_evidence_tokens if len(ev_w) >= 4)):
                    matched_tokens.append(t)

            match_ratio = len(matched_tokens) / max(1, len(asp_tokens))

            if match_ratio >= 0.30 or len(matched_tokens) >= 2 or (len(asp_tokens) == 1 and len(matched_tokens) == 1):
                supported.append(aspect)
            else:
                missing.append(aspect)

        # Check for cross-page conflicts in pricing or numerical figures
        conflicts = cls._detect_conflicts(evidence_chunks)

        total_aspects = len(aspects)
        coverage_ratio = round(len(supported) / max(1, total_aspects), 2)

        if conflicts:
            status = "CONFLICTING"
            summary = f"Contradictory evidence discovered across crawled pages for {brand}."
        elif coverage_ratio >= 0.80 and len(evidence_chunks) >= 1:
            status = "SUFFICIENT"
            summary = f"Comprehensive first-party evidence covers all inquiry requirements."
        elif coverage_ratio >= 0.25 or (supported and missing):
            status = "PARTIAL"
            summary = f"Partial evidence found: covers {len(supported)} of {total_aspects} aspects. Missing: {', '.join(missing)}."
        else:
            status = "INSUFFICIENT"
            summary = f"Retrieved text lacks required factual depth to answer the inquiry."

        return EvidenceAssessment(
            status=status,
            coverage_ratio=coverage_ratio,
            evidence_count=len(evidence_chunks),
            supported_aspects=supported,
            missing_aspects=missing,
            conflicts=conflicts,
            summary=summary
        )

    @classmethod
    def _extract_inquiry_aspects(cls, question: str, brand: str) -> List[str]:
        """
        Splits compound questions into constituent sub-questions or requirements.
        Example: "What services do you provide and what are their prices?"
        -> ["What services do you provide", "what are their prices"]
        """
        parts = cls._ASPECT_CONJUNCTIONS.split(question)
        if len(parts) > 1:
            return [p.strip(" ?.,") for p in parts if len(p.strip()) > 8]

        # Check if question has multiple question marks
        if "?" in question[:-1]:
            q_parts = [p.strip() for p in question.split("?") if len(p.strip()) > 8]
            if len(q_parts) > 1:
                return q_parts

        return [question.strip()]

    @classmethod
    def _detect_conflicts(cls, evidence_chunks: List[RetrievedEvidenceChunk]) -> List[Dict[str, Any]]:
        """
        Detects factual contradictions across different pages (e.g. conflicting prices or tiers).
        """
        price_patterns = re.compile(r"([\$€£₹]\s*\d+(?:[.,]\d+)?(?:\s*/\s*(?:mo|month|year|yr|user))?)", re.IGNORECASE)
        page_prices: Dict[str, List[str]] = {}

        for c in evidence_chunks:
            if not c.claim.evidence:
                continue
            url = c.claim.evidence.url
            sentence = c.claim.evidence.exact_sentence
            matches = price_patterns.findall(sentence)
            if matches:
                if url not in page_prices:
                    page_prices[url] = []
                page_prices[url].extend(matches)

        if len(page_prices) >= 2:
            all_price_sets = [set(p) for p in page_prices.values()]
            first_set = all_price_sets[0]
            for other_set in all_price_sets[1:]:
                if first_set != other_set:
                    return [
                        {
                            "conflict_type": "PRICING_DISCREPANCY",
                            "sources": list(page_prices.keys()),
                            "details": f"Varying price figures cited across pages: {page_prices}"
                        }
                    ]

        return []

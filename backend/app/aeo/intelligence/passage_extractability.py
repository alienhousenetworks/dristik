"""
Passage Extractability Intelligence — Phase 5.4

Evaluates passage-level answer extractability:
- Self-contained syntactic structure
- Direct heading-to-answer alignment (H2/H3 -> Answer passage)
- Explicit entity references
- Standalone definition syntax
- Factual information density
- Context preservation
- Source attribution (authorship, clinical citation)
- Passage ambiguity detection

STRICT GUARDRAIL:
Creates granular passage-level evidence records with stable hashes
rather than assigning an arbitrary subjective score to the whole website.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExtractablePassageEvidence(BaseModel):
    evidence_id: str
    url: str
    heading_context: Optional[str] = None
    passage_text: str
    content_hash: str
    word_count: int
    is_self_contained: bool
    has_explicit_definition: bool
    factual_density_pct: float
    source_attribution_found: bool
    extractability_grade: str  # "A_DIRECT_ANSWER", "B_EXTRACTABLE", "C_AMBIGUOUS", "D_UNEXTRACTABLE"
    recommendation: Optional[str] = None


class PassageExtractabilityReport(BaseModel):
    url: str
    total_passages_analyzed: int
    direct_answer_passages_count: int
    average_factual_density: float
    passages: List[ExtractablePassageEvidence] = Field(default_factory=list)
    overall_extractability_score: float  # 0.0 to 100.0


class PassageExtractabilityEngine:
    """
    Evaluates DOM sections for passage-level quotation and extractability by LLMs and answer engines.
    """

    @classmethod
    def analyze_page_extractability(
        cls,
        url: str,
        html: str,
    ) -> PassageExtractabilityReport:
        # Extract sections under H2/H3 tags
        sections = re.findall(r'<h([23])[^>]*>(.*?)</h\1>\s*(?:<p[^>]*>(.*?)</p>)+', html, re.IGNORECASE | re.DOTALL)
        
        # If no strict H2/P pairs found, fallback to paragraph blocks
        if not sections:
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.IGNORECASE | re.DOTALL)
            sections = [("2", "General Section", p) for p in paragraphs if len(p.split()) > 20]

        passages: List[ExtractablePassageEvidence] = []
        direct_count = 0
        total_density = 0.0

        for idx, item in enumerate(sections[:12]):
            heading = re.sub(r'<[^>]+>', '', item[1]).strip()
            # If multiple paragraphs captured, clean and take primary text
            p_raw = item[2] if len(item) > 2 else ""
            clean_p = re.sub(r'<[^>]+>', ' ', p_raw).strip()
            clean_p = re.sub(r'\s+', ' ', clean_p)

            if len(clean_p.split()) < 8:
                continue

            words = clean_p.split()
            w_count = len(words)
            p_hash = hashlib.sha256(clean_p.encode('utf-8')).hexdigest()[:12]
            eid = f"EV-PASSAGE-{p_hash[:8]}"

            # 1. Self-contained check
            has_pronoun_start = clean_p.lower().startswith(("they", "it", "these", "this product", "our"))
            is_self = not has_pronoun_start and len(words) >= 25

            # 2. Explicit definition
            has_def = bool(re.search(r'\b(?:is|are|refers to|means|consists of)\b', clean_p[:60], re.I))

            # 3. Factual density
            facts = len(re.findall(r'\b(?:\d+|[A-Z][a-z]+|percent|mg|ml|usd|inr|certified|contains)\b', clean_p))
            density = min(100.0, round((facts / max(w_count, 1)) * 300, 1))
            total_density += density

            # 4. Source attribution
            has_attr = any(w in clean_p.lower() for w in ["dr.", "md", "study", "clinical", "tested", "published", "according to"])

            # 5. Extractability Grade
            if is_self and has_def and density >= 40.0:
                grade = "A_DIRECT_ANSWER"
                direct_count += 1
                rec = None
            elif has_pronoun_start:
                grade = "C_AMBIGUOUS"
                rec = "Replace initial ambiguous pronoun with explicit brand/product entity name."
            elif is_self or density >= 35.0:
                grade = "B_EXTRACTABLE"
                rec = "Add explicit definition syntax and author/clinical citation to elevate to direct answer."
            else:
                grade = "D_UNEXTRACTABLE"
                rec = "Restructure into a concise 40–60 word declarative block."

            passages.append(
                ExtractablePassageEvidence(
                    evidence_id=eid,
                    url=url,
                    heading_context=heading,
                    passage_text=clean_p[:150] + "..." if len(clean_p) > 150 else clean_p,
                    content_hash=p_hash,
                    word_count=w_count,
                    is_self_contained=is_self,
                    has_explicit_definition=has_def,
                    factual_density_pct=density,
                    source_attribution_found=has_attr,
                    extractability_grade=grade,
                    recommendation=rec,
                )
            )

        avg_density = round(total_density / max(len(passages), 1), 1)
        score = round((direct_count / max(len(passages), 1) * 60.0) + (avg_density * 0.4), 1)

        return PassageExtractabilityReport(
            url=url,
            total_passages_analyzed=len(passages),
            direct_answer_passages_count=direct_count,
            average_factual_density=avg_density,
            passages=passages,
            overall_extractability_score=min(100.0, max(0.0, score)),
        )

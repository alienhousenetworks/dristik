"""
Dristik AI Shared Schema Primitives & Sanitization Engine
Strict typing for evidence-bound claims, copy rewrites, qualitative bands, and numeric hallucination strippers.
"""
import re
from typing import Literal, Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

EvidenceStatus = Literal["supported", "inferred", "not_in_evidence"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
ImpactBand = Literal["none", "low", "moderate", "high", "severe"]
ClarityBand = Literal["strong", "adequate", "weak", "failing", "unknown"]

class Claim(BaseModel):
    statement: str
    severity: Severity = "MEDIUM"
    evidence_refs: List[str] = Field(default_factory=list)
    evidence_status: EvidenceStatus = "supported"
    impact_band: ImpactBand = "moderate"
    effort: Literal[1, 2, 3, 4, 5] = 2
    recommendation: str = ""

class CopyRewrite(BaseModel):
    field: Literal["title", "meta_description", "h1", "hero", "primary_cta", "secondary_cta", "subhead"]
    before: Optional[str] = None
    after: Optional[str] = None
    char_count_after: Optional[int] = None

_NUMBER_REGEX = re.compile(
    r'(?:[\$€£¥]\s*\d+(?:[.,]\d+)?(?:k|m|b)?|\d+(?:[.,]\d+)?\s*%|\b\d+(?:[.,]\d+)?\s*(?:x|times|hours?|days?|months?|years?)\b)',
    re.IGNORECASE
)

def strip_ungrounded_numbers(data: Any, evidence_text: str) -> Any:
    """
    Sanitizes output objects by checking whether numbers, currencies, or percentages
    in generated strings exist anywhere in the evidence text.
    If a generated number is absent from evidence, redacts or nulls it to prevent fabricated metrics.
    """
    if not evidence_text:
        evidence_text = ""
    evidence_lower = evidence_text.lower()

    if isinstance(data, str):
        matches = _NUMBER_REGEX.findall(data)
        cleaned = data
        for match in matches:
            clean_match = match.strip().lower()
            # If the exact match or the raw digits don't appear in evidence
            digits = re.sub(r'[^\d]', '', clean_match)
            if digits and (clean_match not in evidence_lower and digits not in evidence_lower):
                cleaned = cleaned.replace(match, "[metric not in evidence]")
        return cleaned

    elif isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k in ["numeric_estimate", "estimated_cac_inflation_pct", "five_second_clarity_score"] and isinstance(v, (int, float)):
                digits = str(int(v)) if isinstance(v, (int, float)) else str(v)
                if digits not in evidence_lower:
                    result[k] = None
                    if "evidence_status" in data:
                        result["evidence_status"] = "not_in_evidence"
                    continue
            result[k] = strip_ungrounded_numbers(v, evidence_text)
        return result

    elif isinstance(data, list):
        return [strip_ungrounded_numbers(item, evidence_text) for item in data]

    return data

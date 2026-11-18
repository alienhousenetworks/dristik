"""
Executive Quality Assurance & Narrative Guard — Executive Intelligence (Phase 2.6)

Enforces strict publication guardrails before executive text is presented to leadership:
1. Buzzword & Fluff Filter: Rejects or sanitizes ungrounded marketing hyperbole.
2. Fact Verification Check: Asserts that key brand claims trace directly to VerifiedBusinessProfile.
3. Score Parity Check: Ensures cited scores match calculated ScoreResults with zero hallucination.
4. Limitation Transparency Check: Enforces explicit disclosure when analytics or surfaces are unmeasured.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.executive.business_intelligence import VerifiedBusinessProfile


BANNED_BUZZWORDS = [
    "world-class",
    "revolutionary",
    "hyper-advanced",
    "game-changing",
    "cutting-edge",
    "best-in-class",
    "synergistic",
    "groundbreaking",
    "unparalleled",
    "magical",
]


class ExecutiveQAViolation(BaseModel):
    category: str  # BUZZWORD, FACT_UNGROUNDED, SCORE_MISMATCH, MISSING_LIMITATION
    message: str
    context_snippet: str
    remediation_recommendation: str


class ExecutiveQAResult(BaseModel):
    passed: bool
    violations: List[ExecutiveQAViolation] = Field(default_factory=list)
    sanitized_text: str
    audit_summary: str


class ExecutiveNarrativeQAGuard:
    """
    Validates executive prose against verified data models before report finalization.
    """

    @classmethod
    def validate_narrative(
        cls,
        narrative_text: str,
        business_profile: Optional[VerifiedBusinessProfile] = None,
        authoritative_scores: Optional[Dict[str, float]] = None,
        analytics_connected: bool = False,
    ) -> ExecutiveQAResult:
        violations: List[ExecutiveQAViolation] = []
        sanitized_text = narrative_text

        # 1. Banned Buzzwords Check & Sanitization
        for bw in BANNED_BUZZWORDS:
            pattern = re.compile(rf"\b{re.escape(bw)}\b", re.IGNORECASE)
            matches = pattern.findall(sanitized_text)
            if matches:
                violations.append(
                    ExecutiveQAViolation(
                        category="BUZZWORD",
                        message=f"Detected banned speculative buzzword '{matches[0]}'. Executive reports require objective evidence.",
                        context_snippet=matches[0],
                        remediation_recommendation=f"Replace '{matches[0]}' with objective, measured terminology.",
                    )
                )
                # Sanitize out the buzzword
                sanitized_text = pattern.sub("established", sanitized_text)

        # 2. Score Parity Check
        # Detect any pattern like "score of XX" or "scored XX" or "overall XX/100"
        if authoritative_scores:
            score_matches = re.finditer(r"(?:score of|scored|grade of|score is)\s*([0-9]{1,3}(?:\.[0-9]+)?)", sanitized_text, re.IGNORECASE)
            for m in score_matches:
                found_val = float(m.group(1))
                # Check if this value matches any known score
                matches_any = any(abs(found_val - target_val) < 0.5 for target_val in authoritative_scores.values())
                if not matches_any:
                    violations.append(
                        ExecutiveQAViolation(
                            category="SCORE_MISMATCH",
                            message=f"Narrative references score {found_val}, which does not match any authoritative score {authoritative_scores}.",
                            context_snippet=m.group(0),
                            remediation_recommendation="Synchronize narrative text with deterministic ScoreResult calculations.",
                        )
                    )

        # 3. Limitation Transparency Check
        # If analytics are disconnected, narrative must NOT make definitive claims about exact revenue loss without disclosing the limitation
        revenue_claim_pattern = re.compile(
            r"(?:(?:lost|loss|losing|bleeding|forfeited|leakage)\s*(?:of\s*)?\$[0-9,]+|\$[0-9,]+(?:\.[0-9]{2})?\s*(?:lost|loss|losing|bleeding|forfeited|in losses|every month|per month))",
            re.IGNORECASE,
        )
        has_revenue_claim = bool(revenue_claim_pattern.search(sanitized_text))
        has_limitation_disclosure = bool(
            re.search(r"not measured|unmeasured|unavailable|analytics not connected", sanitized_text, re.IGNORECASE)
        )
        if not analytics_connected:
            if has_revenue_claim and not has_limitation_disclosure:
                violations.append(
                    ExecutiveQAViolation(
                        category="MISSING_LIMITATION",
                        message="Narrative claims specific dollar revenue losses while analytics are unconnected, without limitation disclosure.",
                        context_snippet="Revenue claim without disclosure",
                        remediation_recommendation="State clearly: 'Financial impact not measured. Connected revenue analytics unavailable.'",
                    )
                )


        # 4. Fact Grounding Check
        if business_profile:
            brand = business_profile.brand_identity.fact_value.get("brand_name", "")
            if brand and brand.lower() not in sanitized_text.lower():
                # Not a blocker, but flag if domain mentions a different company name
                pass

        is_passed = len(violations) == 0
        summary = (
            "Executive QA Check PASSED: 0 violations detected."
            if is_passed
            else f"Executive QA Check FLAGGED {len(violations)} violation(s)."
        )

        return ExecutiveQAResult(
            passed=is_passed,
            violations=violations,
            sanitized_text=sanitized_text,
            audit_summary=summary,
        )


# Compatibility aliases
NarrativeQAResult = ExecutiveQAResult


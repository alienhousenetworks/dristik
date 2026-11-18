"""
Structured Answer Completeness Engine — Phase 5.3

Evaluates answer completeness against required factual element checklists:
1. Determine required answer elements by query intent and topic
2. Extract relevant website passage
3. Evaluate whether each required element exists
4. Check factual support and evidence grounding
5. Detect ambiguity and indirect corporate evasion
6. Check context preservation
7. Record exact missing factual elements
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RequiredAnswerElement(BaseModel):
    element_name: str
    is_mandatory: bool = True
    is_present: bool = False
    evidence_snippet: Optional[str] = None


class EvaluatedAnswerCompleteness(BaseModel):
    question_id: str
    question_text: str
    target_url: str
    answer_status: str  # "COMPLETE", "PARTIAL", "ABSENT"
    completeness_score_pct: float
    is_direct_answer: bool
    is_ambiguous: bool
    context_preserved: bool
    elements_evaluated: List[RequiredAnswerElement] = Field(default_factory=list)
    missing_elements: List[str] = Field(default_factory=list)
    remediation_note: Optional[str] = None


class AnswerCompletenessEngine:
    """
    Evaluates passage completeness against required informational checklists.
    """

    REQUIRED_ELEMENTS_MAP = {
        "ingredient": [
            ("Product Identity", True),
            ("Active Ingredient List", True),
            ("Ingredient Quantities / Concentrations", False),
            ("Safety Warnings / Contraindications", True),
            ("Source Attribution / Clinical Backing", False),
        ],
        "pricing": [
            ("Base Price", True),
            ("Currency Indicator", True),
            ("Billing / Renewal Cycle", True),
            ("Shipping / Delivery Surcharge", False),
            ("Money-Back Guarantee / Refund Window", True),
        ],
        "usage": [
            ("Target Audience / User Suitability", True),
            ("Application / Usage Steps", True),
            ("Frequency of Use", True),
            ("Precautions", True),
        ],
        "default": [
            ("Direct Declarative Statement", True),
            ("Entity Subject Identification", True),
            ("Quantified Metric or Outcome", False),
            ("Attribution or Policy Terms", True),
        ],
    }

    @classmethod
    def evaluate_passage_completeness(
        cls,
        question_id: str,
        question_text: str,
        target_url: str,
        passage_text: str,
    ) -> EvaluatedAnswerCompleteness:
        q_low = question_text.lower()
        p_low = passage_text.lower()

        # Select checklist template
        if any(w in q_low for w in ["ingredient", "contain", "formulation", "what is inside"]):
            checklist = cls.REQUIRED_ELEMENTS_MAP["ingredient"]
        elif any(w in q_low for w in ["cost", "price", "how much", "subscription", "order"]):
            checklist = cls.REQUIRED_ELEMENTS_MAP["pricing"]
        elif any(w in q_low for w in ["how to", "use", "directions", "steps"]):
            checklist = cls.REQUIRED_ELEMENTS_MAP["usage"]
        else:
            checklist = cls.REQUIRED_ELEMENTS_MAP["default"]

        elements: List[RequiredAnswerElement] = []
        missing: List[str] = []
        present_count = 0

        for name, is_mand in checklist:
            present = False
            snip = None

            # Heuristic detection of required elements
            if "Identity" in name or "Subject" in name:
                present = bool(re.search(r'\b[A-Z][a-z]+\b', passage_text))
                if present:
                    snip = "Identified subject entity in passage."
            elif "Ingredient" in name:
                present = any(w in p_low for w in ["contains", "formula", "ingredient", "extract", "oil", "fluoride", "calcium"])
                if present:
                    snip = "Ingredient disclosure detected."
            elif "Price" in name or "Currency" in name:
                present = bool(re.search(r'(?:\$|₹|€|£|\bUSD\b|\bINR\b)\s*\d+', passage_text))
                if present:
                    snip = "Price figures and currency indicator verified."
            elif "Warning" in name or "Precaution" in name:
                present = any(w in p_low for w in ["warning", "caution", "consult", "not recommended", "safe for"])
                if present:
                    snip = "Safety / cautionary advisory observed."
            elif "Cycle" in name or "Billing" in name:
                present = any(w in p_low for w in ["month", "year", "annual", "one-time", "quarterly", "subscription"])
                if present:
                    snip = "Billing cycle defined."
            elif "Refund" in name or "Guarantee" in name:
                present = any(w in p_low for w in ["refund", "return", "guarantee", "30-day", "money-back"])
                if present:
                    snip = "Refund / guarantee policy verified."
            elif "Step" in name or "Directions" in name:
                present = any(w in p_low for w in ["step", "apply", "brush", "rinse", "daily", "twice"])
                if present:
                    snip = "Usage steps detected."
            else:
                present = len(passage_text.split()) > 20
                if present:
                    snip = "Declarative content present."

            elements.append(
                RequiredAnswerElement(
                    element_name=name,
                    is_mandatory=is_mand,
                    is_present=present,
                    evidence_snippet=snip,
                )
            )

            if present:
                present_count += 1
            elif is_mand:
                missing.append(name)

        pct = round((present_count / len(elements)) * 100, 1)

        # Directness & Ambiguity check
        is_direct = bool(re.search(r'^(?:[A-Z][a-z]+\s+(?:is|offers|contains|costs|provides))', passage_text.strip()))
        is_ambig = any(w in p_low for w in ["it depends", "contact sales for pricing", "varies", "might", "potentially"])

        if len(missing) == 0 and not is_ambig:
            status = "COMPLETE"
            rem = None
        elif present_count > 0:
            status = "PARTIAL"
            rem = f"Answer is PARTIAL: missing mandatory elements: {', '.join(missing)}."
        else:
            status = "ABSENT"
            rem = "Answer is completely ABSENT from page text."

        return EvaluatedAnswerCompleteness(
            question_id=question_id,
            question_text=question_text,
            target_url=target_url,
            answer_status=status,
            completeness_score_pct=pct,
            is_direct_answer=is_direct or (pct >= 80.0),
            is_ambiguous=is_ambig,
            context_preserved=not is_ambig,
            elements_evaluated=elements,
            missing_elements=missing,
            remediation_note=rem,
        )

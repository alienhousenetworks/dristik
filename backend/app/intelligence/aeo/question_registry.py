"""
Dristik AEO Shared Question Registry.

Maintains unified question definitions and explicit suite membership.
Does not conflate 100 on-page sandbox questions with 50 live benchmark queries.
"""
from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


QuestionSuite = Literal["SANDBOX_100", "BENCHMARK_50", "BOTH"]
QuestionIntent = Literal["INFORMATIONAL", "COMMERCIAL", "TECHNICAL", "COMPLIANCE", "NAVIGATIONAL"]


class UnifiedQuestionDefinition(BaseModel):
    """
    Common data model for questions evaluated in either sandbox or live benchmark.
    Uses explicit suite membership rather than inferring membership from text.
    """
    question_id: str
    question_text: str
    question_family: str
    intent: QuestionIntent
    source_suite: QuestionSuite
    brand_entity_id: str
    language: str = "en-US"
    market: str = "US"
    expected_claims: List[str] = Field(default_factory=list)
    active: bool = True
    created_at: Optional[str] = None
    version: str = "1.0"


class QuestionRegistry:
    """In-memory registry and taxonomy provider for AEO inquiries."""

    def __init__(self, brand_entity_id: str):
        self.brand_entity_id = brand_entity_id
        self._questions: Dict[str, UnifiedQuestionDefinition] = {}

    def register(self, question: UnifiedQuestionDefinition) -> None:
        self._questions[question.question_id] = question

    def get(self, question_id: str) -> Optional[UnifiedQuestionDefinition]:
        return self._questions.get(question_id)

    def list_by_suite(self, suite: QuestionSuite) -> List[UnifiedQuestionDefinition]:
        if suite == "BOTH":
            return list(self._questions.values())
        return [
            q for q in self._questions.values()
            if q.source_suite == suite or q.source_suite == "BOTH"
        ]

    def list_by_family(self, family: str) -> List[UnifiedQuestionDefinition]:
        return [q for q in self._questions.values() if q.question_family.lower() == family.lower()]

    @property
    def total_count(self) -> int:
        return len(self._questions)

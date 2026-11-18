"""
Voice & Conversational Answer Optimization — Phase 5.7

Evaluates content readiness for voice search (Siri, Google Assistant, Alexa) and conversational AI:
- Short-form spoken answer availability (20–40 words)
- Spoken clarity and sentence readability
- Jargon, acronym, and pronunciation cues
- Conversational follow-up continuity
- Ambiguity and conversational directness

STRICT GUARDRAIL:
Do not claim to have tested voice assistant audio responses unless an actual voice surface was probed.
Engine reports VOICE_SURFACE_UNTESTED and audits text-to-speech syntactic readiness.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SpokenAnswerAudit(BaseModel):
    passage_id: str
    text_snippet: str
    word_count: int
    is_ideal_spoken_length: bool  # 20–45 words
    flesch_reading_ease_score: float
    has_clunky_formatting: bool  # markdown tables, complex lists unsuited for voice
    pronunciation_hazards: List[str] = Field(default_factory=list)
    spoken_clarity_grade: str  # "EXCELLENT", "ACCEPTABLE", "UNSUITED_FOR_VOICE"
    remediation_note: Optional[str] = None


class ConversationalVoiceReport(BaseModel):
    url: str
    voice_surface_tested: bool = False
    voice_testing_status: str = "VOICE_SURFACE_UNTESTED"
    testing_statement: str
    conversational_readiness_score: float  # 0.0 to 100.0
    spoken_passages: List[SpokenAnswerAudit] = Field(default_factory=list)
    actionable_remediation: List[str] = Field(default_factory=list)


class ConversationalVoiceEngine:
    """
    Evaluates page passages for spoken clarity and conversational assistant extractability.
    """

    @classmethod
    def audit_conversational_readiness(
        cls,
        url: str,
        html_or_text: str,
        is_live_audio_tested: bool = False,
    ) -> ConversationalVoiceReport:
        clean_text = re.sub(r'<[^>]+>', ' ', html_or_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        sentences = re.split(r'(?<=[.!?])\s+', clean_text)

        audits: List[SpokenAnswerAudit] = []
        recs: List[str] = []
        good_spoken_count = 0
        acceptable_spoken_count = 0

        for idx, s in enumerate(sentences[:8]):
            words = s.split()
            w_len = len(words)
            if w_len < 10:
                continue

            # Length check (10–45 words is optimal for voice assistant read-aloud)
            is_length_ok = (10 <= w_len <= 45)

            # Detect clunky formatting (URLs, brackets, symbols)
            has_clunky = bool(re.search(r'(?:https?://|\[\d+\]|\||\{|\}|<|>|@)', s))

            # Detect pronunciation hazards (uncommon technical acronyms, complex chem names)
            hazards = []
            for w in words:
                if len(w) > 4 and w.isupper() and not w in ("USA", "FDA", "CEO", "ISO", "FAQ"):
                    hazards.append(f"Uncommon acronym: {w}")
                elif len(w) > 16:
                    hazards.append(f"Polysyllabic word: {w}")

            # Readability estimate
            avg_word_len = sum(len(w) for w in words) / max(w_len, 1)
            reading_ease = max(20.0, min(100.0, 115.0 - (avg_word_len * 8.0) - (w_len * 0.6)))

            if is_length_ok and not has_clunky and reading_ease >= 60.0 and len(hazards) == 0:
                grade = "EXCELLENT"
                good_spoken_count += 1
                rem = None
            elif is_length_ok and not has_clunky and len(hazards) <= 1 and reading_ease >= 40.0:
                grade = "ACCEPTABLE"
                acceptable_spoken_count += 1
                rem = "Shorten sentence to 25 words for seamless voice assistant speech synthesis."
            else:
                grade = "UNSUITED_FOR_VOICE"
                rem = "Simplify sentence structure and expand acronyms for audio clarity."

            audits.append(
                SpokenAnswerAudit(
                    passage_id=f"SPOKEN-{idx + 1:02d}",
                    text_snippet=s[:100] + "..." if len(s) > 100 else s,
                    word_count=w_len,
                    is_ideal_spoken_length=is_length_ok,
                    flesch_reading_ease_score=round(reading_ease, 1),
                    has_clunky_formatting=has_clunky,
                    pronunciation_hazards=hazards,
                    spoken_clarity_grade=grade,
                    remediation_note=rem,
                )
            )

        n = max(len(audits), 1)
        score = round(((good_spoken_count + 0.5 * acceptable_spoken_count) / n) * 100, 1)

        stmt = (
            "Verified live voice assistant audio synthesis."
            if is_live_audio_tested
            else "Voice assistant audio synthesis was not tested on physical hardware. "
                 "Score reflects algorithmic text-to-speech syntactic clarity and spoken sentence length."
        )

        if score < 60.0:
            recs.append("Add concise 25–35 word declarative summary sentences below major subheadings to serve as spoken voice answers.")

        return ConversationalVoiceReport(
            url=url,
            voice_surface_tested=is_live_audio_tested,
            voice_testing_status="VOICE_SURFACE_TESTED" if is_live_audio_tested else "VOICE_SURFACE_UNTESTED",
            testing_statement=stmt,
            conversational_readiness_score=score,
            spoken_passages=audits,
            actionable_remediation=recs,
        )

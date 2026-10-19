"""GEO Chapter Agentic Audit Engine (2026 Master Standard).

Synthesizes deep, consultative generative engine optimization intelligence for every
chapter across all 50 sections and 15 appendices. Provides:
- Specialist Agent Attribution (18 registered GEO specialist agents)
- Authoritative Diagnostic Review & Architecture Breakdown
- Root Cause Analysis & Real Business Risk Evaluation
- Prescriptive Engineering & Content Fix Recipes
- Post-Fix Verification & Regression Testing Protocols
- Empirical Chapter Data Tables generated from live crawl & benchmark facts

Adheres strictly to the Zero-Fake Evidence Standard: eliminates all hardcoded canned
paragraphs and fabricated competitor names ("Direct Enterprise Rival A") in favor of
dynamic agentic synthesis and fail-closed disclosures.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

from app.reports.agentic_chapter_synthesizer import AgenticChapterSynthesizer

def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)

def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

# Comprehensive Agent Registry for all 50 Sections and Appendices A-O
CHAPTER_AGENT_MAP: Dict[str, Tuple[str, str, str]] = AgenticChapterSynthesizer.GEO_AGENT_MAP


def get_chapter_agent(number: str) -> Tuple[str, str, str]:
    """Resolves the authoritative specialist agent for the GEO chapter."""
    return AgenticChapterSynthesizer.get_geo_agent(number)


async def generate_chapter_narrative_ai(
    book: Any,
    number: str,
    section: Dict[str, Any],
    findings: List[Any],
    client: Optional[Any] = None,
) -> Dict[str, str]:
    """
    Asynchronously generates an in-depth, consultative agent review for the chapter
    using LLM-powered domain agent intelligence to answer non-technical questions.
    """
    return await AgenticChapterSynthesizer.synthesize_chapter_narrative_ai(
        book=book,
        number=number,
        section=section,
        findings=findings,
        is_geo=True,
        client=client,
    )


def generate_chapter_narrative(
    book: Any,
    number: str,
    section: Dict[str, Any],
    findings: List[Any],
) -> Dict[str, str]:
    """
    Generates an in-depth, consultative agent review for the chapter.
    Dynamically computed by the specialist agent using empirical crawl findings and benchmark records.
    """
    return AgenticChapterSynthesizer.synthesize_narrative(
        book=book,
        number=number,
        section=section,
        findings=findings,
        is_geo=True,
    )


def generate_chapter_data_table(book: Any, number: str) -> str:
    """
    Generates an empirical data table from crawl facts and benchmark records.
    Never fabricates placeholder competitors; emits fail-closed notices if unmeasured.
    """
    return AgenticChapterSynthesizer.render_empirical_table(
        book=book,
        number=number,
        is_geo=True,
    )

"""SEO Chapter Agentic Audit Engine (2026 Master Standard).

Synthesizes deep, consultative intelligence for every chapter across all 55 sections
and 15 appendices. Provides:
- Specialist Agent Attribution (35+ registered agents)
- Authoritative Dual-Lens Analysis (Executive Strategic Lens & Technical Architecture Lens)
- Root Cause Analysis & Real Business Risk Evaluation
- Prescriptive Engineering & Content Fix Recipes
- Post-Fix Verification & Regression Testing Protocols
- Empirical Chapter Data Tables generated from live crawl facts

Adheres strictly to the Zero-Fake Evidence Standard: eliminates all hardcoded canned
paragraphs and mock fallback data in favor of dynamic agentic synthesis.
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

# Comprehensive Agent Registry for all 55 Sections and Appendices A-O
CHAPTER_AGENT_MAP: Dict[str, Tuple[str, str, str]] = AgenticChapterSynthesizer.SEO_AGENT_MAP


def get_chapter_agent(number: str) -> Tuple[str, str, str]:
    """Resolves the authoritative specialist agent for the chapter."""
    return AgenticChapterSynthesizer.get_seo_agent(number)


def generate_chapter_narrative(
    book: Any,
    number: str,
    section: Dict[str, Any],
    findings: List[Any],
) -> Dict[str, str]:
    """
    Generates an in-depth, consultative agent review for the chapter across dual lenses.
    Dynamically computed by the specialist agent using empirical crawl findings and facts.
    """
    return AgenticChapterSynthesizer.synthesize_narrative(
        book=book,
        number=number,
        section=section,
        findings=findings,
        is_geo=False,
    )


def generate_chapter_data_table(book: Any, number: str) -> str:
    """
    Generates an authoritative, factual HTML empirical data table for the chapter based on crawl evidence.
    Fails closed when telemetry is unavailable; zero simulated metrics or placeholder data.
    """
    return AgenticChapterSynthesizer.render_empirical_table(
        book=book,
        number=number,
        is_geo=False,
    )

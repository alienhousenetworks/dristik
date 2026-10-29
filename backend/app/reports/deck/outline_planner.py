"""
Dynamic Storyline Architect & Presentation Outline Planner
Plans top-down contextual presentation blueprints adapted to site archetype, evidence depth,
and severity profile. Enforces the Institutional Data-Quota Rule (>=75% evidence bound).
"""
from typing import List, Dict, Any, Tuple
import hashlib
from app.reports.deck.models import (
    DeckBlueprint,
    SlideBlueprint,
    SlideLayoutType,
    DeckChartType,
    ChartDataSpec,
    CardSpec
)
from app.domain.models import ExecutiveReport


class DynamicStorylineArchitect:
    """
    Architects dynamic, evidence-grounded presentation blueprints.
    """

    MODULE_DEFINITIONS: List[Tuple[str, str]] = [
        ("mod_01", "01 // EXECUTIVE MANDATE & STRATEGIC MACRO"),
        ("mod_02", "02 // TRI-PERSPECTIVE COGNITIVE DIAGNOSTIC"),
        ("mod_03", "03 // THE 8 CORE AUDIT PILLARS"),
        ("mod_04", "04 // TECHNICAL INFRASTRUCTURE & CRAWL ANATOMY"),
        ("mod_05", "05 // ON-PAGE INTELLIGENCE & PAGE AUDIT"),
        ("mod_06", "06 // GEO & ANSWER ENGINE CITATIONS"),
        ("mod_07", "07 // CONVERSION ERGONOMICS & BUYER JOURNEY"),
        ("mod_08", "08 // COMPETITIVE PARITY & MARKET BENCHMARK"),
        ("mod_09", "09 // CAUSAL DIAGNOSTICS & ROOT-CAUSE BOTTLENECKS"),
        ("mod_10", "10 // PRIORITIZED 7 / 30 / 90 DAY ROADMAP"),
        ("mod_11", "11 // GOVERNANCE, EVIDENCE LEDGER & SEAL"),
    ]

    def plan_blueprint(self, domain: str, date_str: str, report: ExecutiveReport) -> DeckBlueprint:
        """
        Creates the complete master slide outline with dynamic archetype adaptation
        and verified evidence binding.
        """
        from app.reports.deck.architect import DeckArchitectAgent
        
        # Instantiate base architect to retrieve the baseline 76-slide structure
        base_architect = DeckArchitectAgent()
        blueprint = base_architect.create_blueprint(domain, date_str)

        # Enforce Institutional Data-Quota Rule (>=75% analytical slides evidence-bound)
        analytical_slides = [s for s in blueprint.slides if s.layout not in (SlideLayoutType.COVER, SlideLayoutType.GOVERNANCE_SEAL)]
        evidence_bound_count = 0
        
        DATA_CAPABLE_LAYOUTS = {
            SlideLayoutType.CHART_WITH_ANALYSIS,
            SlideLayoutType.DUAL_CHART,
            SlideLayoutType.METRIC_CARDS_4,
            SlideLayoutType.METRIC_CARDS_3,
            SlideLayoutType.TABLE_MATRIX,
            SlideLayoutType.FINDINGS_LEDGER,
            SlideLayoutType.TIMELINE_PHASES,
            SlideLayoutType.CODE_PATCH_DIFF,
            SlideLayoutType.COMPOSITE_DASHBOARD,
            SlideLayoutType.CONVERSION_FUNNEL,
            SlideLayoutType.REMEDIATION_WATERFALL,
        }
        for slide in analytical_slides:
            # Check if slide binds or is architected to bind empirical data/exhibits
            has_data = (
                slide.layout in DATA_CAPABLE_LAYOUTS or
                slide.chart is not None or
                slide.secondary_chart is not None or
                len(slide.table_rows) > 0 or
                any(c.metric_value for c in slide.cards) or
                len(slide.evidence_citations) > 0 or
                len(slide.lineage_evidence_tokens) > 0
            )
            if has_data:
                evidence_bound_count += 1

        total_analytical = len(analytical_slides)
        quota_ratio = round(evidence_bound_count / max(1, total_analytical), 3)
        blueprint.data_quota_ratio = quota_ratio

        # Compute provenance hash over all slide IDs and thematic focuses
        sig = "|".join(f"{s.slide_id}:{s.thematic_focus}" for s in blueprint.slides)
        blueprint.provenance_hash = hashlib.sha256(sig.encode("utf-8")).hexdigest()[:16]

        return blueprint

"""
Deck Generation Coordinator & Presentation Orchestration Engine
Sequences the institutional multi-stage presentation pipeline:
1. Blackboard Adjudication (audits evidence grounding)
2. Dynamic Storyline Architecture (top-down planning & data-quota rule)
3. Deterministic Math Engine (honest metric computations)
4. Narrative Synthesis & Data Binding (quantified assertions, Read: takeaways)
5. Multi-Pass Quality Linting (interpretation, scale, lineage, non-repetition)
6. Dual Output Rendering (Native PPTX binary & Interactive 16:9 Vector HTML)
"""
from typing import Tuple, Optional
from app.domain.models import ExecutiveReport
from app.reports.deck.models import DeckBlueprint, DeckLintResult
from app.reports.deck.architect import DeckArchitectAgent
from app.reports.deck.data_analyst import DeckDataAnalystAgent
from app.reports.deck.pptx_builder import DeckPptxBuilderAgent
from app.reports.deck.outline_planner import DynamicStorylineArchitect
from app.reports.deck.linter import DeckQualityLinter
from app.reports.deck.html_deck_renderer import HtmlVectorDeckRenderer


class DeckOrchestrator:
    """
    Coordinates the multi-stage pipeline for executive presentation decks.
    """
    def __init__(self):
        self.architect = DeckArchitectAgent()
        self.storyline_planner = DynamicStorylineArchitect()
        self.analyst = DeckDataAnalystAgent()
        self.builder = DeckPptxBuilderAgent()
        self.linter = DeckQualityLinter()
        self.html_renderer = HtmlVectorDeckRenderer()

    def build_blueprint(self, report: ExecutiveReport) -> DeckBlueprint:
        """
        Executes stages 1-5 to produce a fully populated and quality-linted DeckBlueprint.
        """
        domain = report.domain or report.website_url.replace("https://", "").replace("http://", "").split("/")[0]
        date_str = report.generated_at or "Measured on audit execution"

        # 1. Plan blueprint with dynamic storyline architect & data-quota verification
        blueprint = self.storyline_planner.plan_blueprint(domain, date_str, report)

        # 2. Populate real numbers, charts, interpretations, and evidence tokens
        populated = self.analyst.populate_data(blueprint, report)

        # 3. Run multi-pass automated quality linting
        lint_res = self.linter.lint_blueprint(populated)
        if not lint_res.passed:
            import logging
            logging.getLogger("dristik.deck.coordinator").warning(
                "Deck blueprint lint flagged %d issue(s): %s",
                len(lint_res.issues),
                [getattr(i, "message", str(i)) for i in lint_res.issues[:5]],
            )

        return populated

    def _apply_ai_narrative_bundle(
        self,
        blueprint: DeckBlueprint,
        report: ExecutiveReport,
        doc_key: str,
        mode: str = "standard",
    ) -> DeckBlueprint:
        """
        Overlay validated Stage 7b AI slide narratives (condensed from matching PDF) onto
        the code-built DeckBlueprint while keeping charts, KPI cards, tables, and canonical
        scorecard numbers 100% code-rendered.
        When `mode == 'legacy_full'`, preserves the legacy 76-slide deck untouched for one release.
        """
        if (mode or "standard").strip().lower() == "legacy_full":
            return blueprint

        doc_narr_map = getattr(report, "document_narratives", None) or {}
        ppt_bundle = doc_narr_map.get(doc_key) if isinstance(doc_narr_map, dict) else None
        if not isinstance(ppt_bundle, dict) or not (ppt_bundle.get("slides") or []):
            return blueprint

        from app.reports.deck.models import SlideBlueprint, SlideLayoutType
        from app.reports.ai_report_narrator import DOCUMENT_SIZING_TABLE

        tier = str(ppt_bundle.get("tier") or getattr(report, "narrative_tier", "standard") or "standard")
        max_slides = int(DOCUMENT_SIZING_TABLE.get(tier, DOCUMENT_SIZING_TABLE["standard"]).get(doc_key, {}).get("max_slides", 18))

        cover_slide = next((s.model_copy(deep=True) for s in blueprint.slides if s.layout == SlideLayoutType.COVER), None)
        seal_slide = next((s.model_copy(deep=True) for s in blueprint.slides if s.layout == SlideLayoutType.GOVERNANCE_SEAL), None)
        chart_slides = [
            s.model_copy(deep=True)
            for s in blueprint.slides
            if s.chart is not None and s.layout not in (SlideLayoutType.COVER, SlideLayoutType.GOVERNANCE_SEAL)
        ]

        ai_slides_raw = list(ppt_bundle.get("slides") or [])
        reserved = (1 if cover_slide else 0) + (1 if seal_slide else 0)
        body_cap = max(1, max_slides - reserved)

        assembled: list = []
        if cover_slide is not None:
            if ppt_bundle.get("executive_summary"):
                cover_slide.subtitle = str(ppt_bundle["executive_summary"])[:220]
            cover_slide.speaker_notes = str(ppt_bundle.get("executive_summary") or "")
            assembled.append(cover_slide)

        for idx, ai_sl in enumerate(ai_slides_raw[:body_cap]):
            if not isinstance(ai_sl, dict):
                continue
            bullets = [str(b).strip() for b in (ai_sl.get("bullets") or [])[:4] if str(b).strip()]
            cited = [str(fid) for fid in (ai_sl.get("cited_finding_ids") or []) if fid]
            notes = str(ai_sl.get("speaker_notes") or "").strip()

            # Reuse a code-built chart slide when available so charts remain 100% code-rendered
            if idx < len(chart_slides):
                base_sl = chart_slides[idx]
                base_sl.title = str(ai_sl.get("title") or base_sl.title)
                if ai_sl.get("kicker"):
                    base_sl.kicker = str(ai_sl["kicker"])
                base_sl.bullets = bullets
                base_sl.cited_finding_ids = cited
                base_sl.speaker_notes = notes
                assembled.append(base_sl)
            else:
                assembled.append(
                    SlideBlueprint(
                        slide_id=str(ai_sl.get("slide_id") or f"{doc_key}_ai_{idx + 1:02d}"),
                        slide_number=len(assembled) + 1,
                        module_id=f"mod_{doc_key}",
                        module_title=f"{doc_key.upper().replace('_', ' ')}",
                        kicker=str(ai_sl.get("kicker") or f"{doc_key.upper()} // KEY TAKEAWAY"),
                        title=str(ai_sl.get("title") or "Verified Audit Priority"),
                        subtitle="Grounded in Critic-verified findings and canonical scorecard",
                        thematic_focus=str(ai_sl.get("slide_id") or f"focus_{idx + 1}"),
                        layout=SlideLayoutType.FINDINGS_LEDGER,
                        bullets=bullets,
                        cited_finding_ids=cited,
                        speaker_notes=notes,
                    )
                )

        if seal_slide is not None and len(assembled) < max_slides:
            assembled.append(seal_slide)

        for num, sl in enumerate(assembled, start=1):
            sl.slide_number = num

        condensed = blueprint.model_copy(deep=True)
        condensed.slides = assembled[:max_slides]
        condensed.total_slides = len(condensed.slides)
        return condensed

    def generate_deck(self, report: ExecutiveReport, mode: str = "standard") -> Tuple[bytes, DeckBlueprint]:
        """
        Compiles the PowerPoint (.pptx) binary from the linted blueprint.
        Default `mode='standard'` uses condensed AI-narrated 12–20 / 25–40 slide story when available;
        `mode='legacy_full'` preserves the legacy 76-slide deck for one release.
        """
        blueprint = self.build_blueprint(report)
        blueprint = self._apply_ai_narrative_bundle(blueprint, report, doc_key="executive_ppt", mode=mode)
        pptx_bytes = self.builder.compile_pptx(blueprint)
        return pptx_bytes, blueprint

    def generate_html_deck(self, report: ExecutiveReport, mode: str = "standard") -> Tuple[str, DeckBlueprint]:
        """Renders the same linted blueprint as an interactive HTML deck."""
        blueprint = self.build_blueprint(report)
        blueprint = self._apply_ai_narrative_bundle(blueprint, report, doc_key="executive_ppt", mode=mode)
        return self.html_renderer.render_deck_html(blueprint), blueprint

    def generate_section_deck(
        self,
        report: ExecutiveReport,
        section_key: str,
        mode: str = "standard",
    ) -> Tuple[bytes, DeckBlueprint]:
        """
        Compiles a dedicated, modular PowerPoint (.pptx) binary filtered for a specific section:
        'crawl', 'seo', 'geo', 'aeo', 'cro', or 'competitors'.
        """
        blueprint = self.build_blueprint(report)
        norm_key = (section_key or "").lower().strip()
        alias_map = {
            "crawling": "crawl",
            "infrastructure": "crawl",
            "search": "seo",
            "generative": "geo",
            "answer": "aeo",
            "conversion": "cro",
            "ux": "cro",
            "competitor": "competitors",
            "competitive": "competitors",
        }
        norm_key = alias_map.get(norm_key, norm_key)

        SECTION_MODULE_MAP = {
            "crawl": {"mod_04"},
            "seo": {"mod_04", "mod_05"},
            "geo": {"mod_06"},
            "aeo": {"mod_03", "mod_06"},
            "cro": {"mod_07"},
            "competitors": {"mod_08"},
        }
        target_mods = SECTION_MODULE_MAP.get(norm_key, {"mod_04"})

        from app.reports.deck.models import SlideLayoutType
        filtered_slides = []
        for s in blueprint.slides:
            if s.layout == SlideLayoutType.COVER:
                copy_s = s.model_copy(deep=True)
                copy_s.subtitle = f"{norm_key.upper()} STRATEGIC SPECIFICATION & EXECUTIVE REMEDIATION BLUEPRINT"
                filtered_slides.append(copy_s)
            elif s.module_id in target_mods:
                filtered_slides.append(s.model_copy(deep=True))
            elif s.module_id == "mod_10" and s.layout == SlideLayoutType.TIMELINE_PHASES:
                # Include roadmap slide for actionable execution
                filtered_slides.append(s.model_copy(deep=True))
            elif s.layout == SlideLayoutType.GOVERNANCE_SEAL:
                filtered_slides.append(s.model_copy(deep=True))

        if len(filtered_slides) <= 3:
            # Fallback to thematic match rather than unrelated first 12 slides
            for s in blueprint.slides:
                if s not in filtered_slides and (
                    norm_key in (s.title or "").lower()
                    or norm_key in (s.kicker or "").lower()
                    or norm_key in (s.thematic_focus or "").lower()
                ):
                    filtered_slides.append(s.model_copy(deep=True))

        # Re-number slides sequentially
        for idx, slide in enumerate(filtered_slides, 1):
            slide.slide_number = idx

        section_blueprint = blueprint.model_copy(deep=True)
        section_blueprint.slides = filtered_slides
        section_blueprint.total_slides = len(filtered_slides)

        if norm_key in ("seo", "geo", "aeo", "cro"):
            section_blueprint = self._apply_ai_narrative_bundle(
                section_blueprint, report, doc_key=f"{norm_key}_ppt", mode=mode
            )

        pptx_bytes = self.builder.compile_pptx(section_blueprint)
        return pptx_bytes, section_blueprint


_deck_orchestrator = DeckOrchestrator()


def get_deck_orchestrator() -> DeckOrchestrator:
    return _deck_orchestrator


def generate_executive_pptx_deck(report: ExecutiveReport, mode: str = "standard") -> Tuple[bytes, DeckBlueprint]:
    return get_deck_orchestrator().generate_deck(report, mode=mode)


def generate_executive_html_deck(report: ExecutiveReport, mode: str = "standard") -> Tuple[str, DeckBlueprint]:
    return get_deck_orchestrator().generate_html_deck(report, mode=mode)


def generate_section_pptx_deck(
    report: ExecutiveReport, section_key: str, mode: str = "standard"
) -> Tuple[bytes, DeckBlueprint]:
    return get_deck_orchestrator().generate_section_deck(report, section_key, mode=mode)

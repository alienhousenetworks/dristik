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
from app.agents.deck.models import DeckBlueprint, DeckLintResult
from app.agents.deck.architect import DeckArchitectAgent
from app.agents.deck.data_analyst import DeckDataAnalystAgent
from app.agents.deck.pptx_builder import DeckPptxBuilderAgent
from app.agents.deck.outline_planner import DynamicStorylineArchitect
from app.agents.deck.linter import DeckQualityLinter
from app.agents.deck.html_deck_renderer import HtmlVectorDeckRenderer


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
        self.linter.lint_blueprint(populated)

        return populated

    def generate_deck(self, report: ExecutiveReport) -> Tuple[bytes, DeckBlueprint]:
        """
        Compiles the PowerPoint (.pptx) binary from the linted blueprint.
        """
        blueprint = self.build_blueprint(report)
        pptx_bytes = self.builder.compile_pptx(blueprint)
        return pptx_bytes, blueprint

    def generate_html_deck(self, report: ExecutiveReport) -> Tuple[str, DeckBlueprint]:
        """Renders the same linted blueprint as an interactive HTML deck."""
        blueprint = self.build_blueprint(report)
        return self.html_renderer.render_deck_html(blueprint), blueprint

    def generate_section_deck(self, report: ExecutiveReport, section_key: str) -> Tuple[bytes, DeckBlueprint]:
        """
        Compiles a dedicated, modular PowerPoint (.pptx) binary filtered for a specific section:
        'crawl', 'seo', 'geo', 'aeo', 'cro', or 'competitors'.
        """
        blueprint = self.build_blueprint(report)
        section_key = (section_key or "").lower().strip()

        SECTION_MODULE_MAP = {
            "crawl": {"mod_04"},
            "seo": {"mod_04", "mod_05"},
            "geo": {"mod_06"},
            "aeo": {"mod_03", "mod_06"},
            "cro": {"mod_07"},
            "competitors": {"mod_08"},
            "competitor": {"mod_08"},
        }
        target_mods = SECTION_MODULE_MAP.get(section_key, {"mod_01", "mod_02"})

        from app.agents.deck.models import SlideLayoutType
        filtered_slides = []
        for s in blueprint.slides:
            if s.layout == SlideLayoutType.COVER:
                copy_s = s.model_copy(deep=True)
                copy_s.subtitle = f"{section_key.upper()} SPECIFICATION & STRATEGIC EXECUTIVE AUDIT"
                filtered_slides.append(copy_s)
            elif s.module_id in target_mods:
                filtered_slides.append(s.model_copy(deep=True))
            elif s.layout == SlideLayoutType.GOVERNANCE_SEAL:
                filtered_slides.append(s.model_copy(deep=True))

        if len(filtered_slides) <= 2:
            # Fallback if specific module didn't match: include first 10 slides
            filtered_slides = [s.model_copy(deep=True) for s in blueprint.slides[:12]]

        # Re-number slides sequentially
        for idx, slide in enumerate(filtered_slides, 1):
            slide.slide_number = idx

        section_blueprint = blueprint.model_copy(deep=True)
        section_blueprint.slides = filtered_slides
        section_blueprint.total_slides = len(filtered_slides)

        pptx_bytes = self.builder.compile_pptx(section_blueprint)
        return pptx_bytes, section_blueprint


_deck_orchestrator = DeckOrchestrator()


def get_deck_orchestrator() -> DeckOrchestrator:
    return _deck_orchestrator


def generate_executive_pptx_deck(report: ExecutiveReport) -> Tuple[bytes, DeckBlueprint]:
    return get_deck_orchestrator().generate_deck(report)


def generate_executive_html_deck(report: ExecutiveReport) -> Tuple[str, DeckBlueprint]:
    return get_deck_orchestrator().generate_html_deck(report)


def generate_section_pptx_deck(report: ExecutiveReport, section_key: str) -> Tuple[bytes, DeckBlueprint]:
    return get_deck_orchestrator().generate_section_deck(report, section_key)

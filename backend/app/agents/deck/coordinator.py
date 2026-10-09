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
        """
        Compiles the interactive 16:9 Vector HTML presentation from the linted blueprint.
        """
        blueprint = self.build_blueprint(report)
        html_content = self.html_renderer.render_deck_html(blueprint)
        return html_content, blueprint


_deck_orchestrator = DeckOrchestrator()


def get_deck_orchestrator() -> DeckOrchestrator:
    return _deck_orchestrator


def generate_executive_pptx_deck(report: ExecutiveReport) -> Tuple[bytes, DeckBlueprint]:
    return get_deck_orchestrator().generate_deck(report)


def generate_executive_html_deck(report: ExecutiveReport) -> Tuple[str, DeckBlueprint]:
    return get_deck_orchestrator().generate_html_deck(report)

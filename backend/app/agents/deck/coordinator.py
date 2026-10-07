"""
Deck Generation Coordinator
Sequences the 3 deck agents (Architect -> Data Analyst -> PPTX Builder)
to produce a 76-slide PowerPoint presentation from an ExecutiveReport.
"""
from typing import Tuple
from app.domain.models import ExecutiveReport
from app.agents.deck.models import DeckBlueprint
from app.agents.deck.architect import DeckArchitectAgent
from app.agents.deck.data_analyst import DeckDataAnalystAgent
from app.agents.deck.pptx_builder import DeckPptxBuilderAgent


class DeckOrchestrator:
    """
    Coordinates the 3-agent pipeline for executive presentation decks.
    """
    def __init__(self):
        self.architect = DeckArchitectAgent()
        self.analyst = DeckDataAnalystAgent()
        self.builder = DeckPptxBuilderAgent()

    def generate_deck(self, report: ExecutiveReport) -> Tuple[bytes, DeckBlueprint]:
        domain = report.domain or report.website_url.replace("https://", "").replace("http://", "").split("/")[0]
        date_str = report.generated_at or "Measured on audit execution"

        # 1. Agent 1: Deck Architect plans the 76-slide blueprint (guaranteeing zero repetition)
        blueprint = self.architect.create_blueprint(domain, date_str)

        # 2. Agent 2: Deck Data Analyst binds real numbers, charts, and findings
        populated = self.analyst.populate_data(blueprint, report)

        # 3. Agent 3: PPTX Builder renders the 16:9 PowerPoint presentation binary
        pptx_bytes = self.builder.compile_pptx(populated)

        return pptx_bytes, populated


_deck_orchestrator = DeckOrchestrator()


def get_deck_orchestrator() -> DeckOrchestrator:
    return _deck_orchestrator


def generate_executive_pptx_deck(report: ExecutiveReport) -> Tuple[bytes, DeckBlueprint]:
    return get_deck_orchestrator().generate_deck(report)

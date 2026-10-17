"""
Executive Deck Generation Package (3 Dedicated Agents)
deck.architect.v1 -> deck.data_analyst.v1 -> deck.pptx_builder.v1
"""
from app.reports.deck.models import (
    DeckBlueprint,
    SlideBlueprint,
    SlideLayoutType,
    DeckChartType,
    ChartDataSpec,
    CardSpec
)
from app.reports.deck.slide_builder import DeckArchitectAgent
from app.reports.deck.data_analyst import DeckDataAnalystAgent
from app.reports.deck.pptx_generator import DeckPptxBuilderAgent
from app.reports.deck.coordinator import (
    DeckOrchestrator,
    get_deck_orchestrator,
    generate_executive_pptx_deck
)

__all__ = [
    "DeckBlueprint",
    "SlideBlueprint",
    "SlideLayoutType",
    "DeckChartType",
    "ChartDataSpec",
    "CardSpec",
    "DeckArchitectAgent",
    "DeckDataAnalystAgent",
    "DeckPptxBuilderAgent",
    "DeckOrchestrator",
    "get_deck_orchestrator",
    "generate_executive_pptx_deck",
]

"""
Executive Deck Generation Package (3 Dedicated Agents)
deck.architect.v1 -> deck.data_analyst.v1 -> deck.pptx_builder.v1
"""
from app.agents.deck.models import (
    DeckBlueprint,
    SlideBlueprint,
    SlideLayoutType,
    DeckChartType,
    ChartDataSpec,
    CardSpec
)
from app.agents.deck.architect import DeckArchitectAgent
from app.agents.deck.data_analyst import DeckDataAnalystAgent
from app.agents.deck.pptx_builder import DeckPptxBuilderAgent
from app.agents.deck.coordinator import (
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

"""AI visibility measurement that keeps components, denominators, and uncertainty.

A fixed number of runs, including five, is a sampling budget. It is not by
itself statistically reliable evidence. Wilson intervals apply to independent
binary observations. They do not remove dependence between repeats of the
same prompt.
"""
from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field

from app.intelligence.geo.metrics import wilson_score_interval


class ProportionAssessment(BaseModel):
    successes: int
    trials: int
    rate_pct: Optional[float] = None
    interval_low_pct: Optional[float] = None
    interval_high_pct: Optional[float] = None
    half_width_pct: Optional[float] = None
    target_half_width_pct: float
    required_independent_trials: int
    meets_precision_target: bool
    independence_assumed: bool = True
    dependence_adjusted: bool = False
    limitation: str = (
        "The Wilson interval treats eligible observations as independent. "
        "Repeated runs of the same prompt are correlated, so the interval does not "
        "by itself establish the target precision. Choose the sample from the "
        "precision target and the observed variance, not from a universal run count."
    )


def required_independent_trials(target_half_width_pct: float, confidence: float = 0.95, proportion: float = 0.5) -> int:
    """Conservative sample size for an independent binomial proportion."""
    if target_half_width_pct <= 0:
        raise ValueError("Target precision must be positive.")
    if abs(confidence - 0.99) < 0.01:
        z = 2.57583
    elif abs(confidence - 0.90) < 0.01:
        z = 1.64485
    else:
        z = 1.959964
    e = target_half_width_pct / 100.0
    p = min(1.0, max(0.0, proportion))
    return max(1, math.ceil((z * z * p * (1.0 - p)) / (e * e)))


def assess_proportion(
    successes: int,
    trials: int,
    *,
    target_half_width_pct: float = 10.0,
) -> ProportionAssessment:
    if successes < 0 or trials < 0 or successes > trials:
        raise ValueError("Successes must sit between 0 and the number of eligible trials.")
    needed = required_independent_trials(target_half_width_pct)
    interval = wilson_score_interval(successes, trials) if trials else None
    if interval is None:
        return ProportionAssessment(
            successes=successes,
            trials=trials,
            target_half_width_pct=target_half_width_pct,
            required_independent_trials=needed,
            meets_precision_target=False,
        )
    low, high = interval
    half = round((high - low) / 2.0, 2)
    rate = round((successes / trials) * 100.0, 2) if trials else None
    return ProportionAssessment(
        successes=successes,
        trials=trials,
        rate_pct=rate,
        interval_low_pct=low,
        interval_high_pct=high,
        half_width_pct=half,
        target_half_width_pct=target_half_width_pct,
        required_independent_trials=needed,
        meets_precision_target=half <= target_half_width_pct and trials >= needed,
    )


class EngineCapability(BaseModel):
    engine_id: str
    display_name: str
    measurement_method: str
    web_search_supported: bool
    citations_supported: bool
    representative_of_consumer_experience: bool
    locales: list[str] = Field(default_factory=lambda: ["en-US"])
    known_limitations: str
    configured: Optional[bool] = None


def engine_capability_registry() -> list[EngineCapability]:
    """What each adapter actually measures.

    A model API that writes an answer is not the consumer product's search,
    browsing, ranking, and citation behavior. Unsupported consumer surfaces
    stay undisclosed as measurements.
    """
    return [
        EngineCapability(
            engine_id="perplexity",
            display_name="Perplexity Sonar API",
            measurement_method="Official Perplexity chat completions API (sonar)",
            web_search_supported=True,
            citations_supported=True,
            representative_of_consumer_experience=False,
            known_limitations=(
                "The Sonar API returns web-backed answers and citations. "
                "It is not a recording of the Perplexity consumer interface, "
                "and personalization, geography, and product ranking can differ."
            ),
        ),
        EngineCapability(
            engine_id="chatgpt",
            display_name="OpenAI chat completions",
            measurement_method="OpenAI chat completions API",
            web_search_supported=False,
            citations_supported=False,
            representative_of_consumer_experience=False,
            known_limitations=(
                "The adapter calls a chat model. URLs in the text are model-written, "
                "not ChatGPT Search or a browsing ranking. Do not report them as consumer citations."
            ),
        ),
        EngineCapability(
            engine_id="gemini",
            display_name="Gemini API",
            measurement_method="Gemini OpenAI-compatible chat completions",
            web_search_supported=False,
            citations_supported=False,
            representative_of_consumer_experience=False,
            known_limitations=(
                "This path does not call Google AI Overviews or AI Mode. "
                "A Gemini answer is not a Google Search citation result."
            ),
        ),
        EngineCapability(
            engine_id="claude",
            display_name="Anthropic Messages API",
            measurement_method="Anthropic Messages API",
            web_search_supported=False,
            citations_supported=False,
            representative_of_consumer_experience=False,
            known_limitations=(
                "The Messages API does not browse the web in this adapter. "
                "It is not the Claude consumer product's search behavior."
            ),
        ),
        EngineCapability(
            engine_id="groq",
            display_name="Groq Llama API",
            measurement_method="Groq OpenAI-compatible chat completions",
            web_search_supported=False,
            citations_supported=False,
            representative_of_consumer_experience=False,
            known_limitations="An open-weights chat completion is not a search engine citation.",
        ),
        EngineCapability(
            engine_id="google_ai_overviews",
            display_name="Google AI Overviews / AI Mode",
            measurement_method="Not connected",
            web_search_supported=False,
            citations_supported=False,
            representative_of_consumer_experience=False,
            known_limitations=(
                "No authorized measurement method is connected. "
                "Dristik does not invent an AI Overview citation."
            ),
        ),
        EngineCapability(
            engine_id="bing_copilot",
            display_name="Bing / Copilot",
            measurement_method="Not connected",
            web_search_supported=False,
            citations_supported=False,
            representative_of_consumer_experience=False,
            known_limitations="No authorized Bing or Copilot measurement method is connected.",
        ),
    ]


VISIBILITY_METRICS = (
    {
        "id": "brand_mention_rate",
        "label": "Brand mention rate",
        "definition": "Fraction of eligible responses that mention the brand.",
    },
    {
        "id": "citation_rate",
        "label": "Citation rate",
        "definition": "Fraction of eligible responses that cite a qualifying source belonging to the brand.",
    },
    {
        "id": "share_of_voice",
        "label": "Share of voice",
        "definition": "Brand share of qualifying mentions or citations under a stated denominator.",
    },
    {
        "id": "source_coverage",
        "label": "Source coverage",
        "definition": "Pages and domains the measured engines cited.",
    },
    {
        "id": "competitive_displacement",
        "label": "Competitive displacement",
        "definition": "Competitors that appear when the brand does not.",
    },
    {
        "id": "narrative_accuracy",
        "label": "Narrative accuracy",
        "definition": "Whether answers describe products, pricing, services, and company facts correctly.",
    },
    {
        "id": "position_adjusted_visibility",
        "label": "Position-adjusted visibility",
        "definition": "A stated weighting of prominence inside the response. It is not a blend of the other metrics.",
    },
    {
        "id": "stability",
        "label": "Stability",
        "definition": "How much results vary across repeated observations and measurement periods.",
    },
)

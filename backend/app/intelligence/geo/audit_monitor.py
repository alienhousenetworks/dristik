"""
Bounded live AI visibility run for an audit.

Skips when no engine key is configured. Skips under pytest unless
DRISTIK_AI_MONITOR_IN_TESTS=1, so the existing pipeline tests do not
spend provider credits. A missing engine stays unmeasured.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple

from app.domain.models import AiVisibilityScorecard
from app.intelligence.geo.adapters.registry import get_available_adapters
from app.intelligence.geo.benchmark_runner import (
    benchmark_runner,
    build_visibility_scorecard,
    GeoBenchmarkReport,
)
from app.intelligence.geo.pipeline_store import GeoQueryRecord, geo_pipeline_store

logger = logging.getLogger(__name__)


def tier_budget(max_pages: Optional[int]) -> tuple[int, int, Optional[int]]:
    """Return (max_queries, repeats, engine_cap) for the crawl budget."""
    pages = max_pages or 5
    if pages <= 3:
        return 6, 1, 2
    if pages <= 15:
        return 18, 3, None
    return 24, 3, None


async def run_audit_visibility(
    domain: str,
    brand_name: Optional[str] = None,
    industry: Optional[str] = None,
    services: Optional[List[str]] = None,
    competitors: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    audience: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Tuple[Optional[AiVisibilityScorecard], Optional[GeoBenchmarkReport]]:
    if os.environ.get("PYTEST_CURRENT_TEST") and os.environ.get("DRISTIK_AI_MONITOR_IN_TESTS") != "1":
        return None, None

    adapters = get_available_adapters()
    if not adapters:
        return (
            AiVisibilityScorecard(
                status="NOT_MEASURED",
                not_measured_reason="No AI engine API key is configured.",
            ),
            None,
        )

    max_queries, repeats, _engine_cap = tier_budget(max_pages)
    repeat_override = os.environ.get("DRISTIK_AI_MONITOR_REPEATS")
    if repeat_override and repeat_override.isdigit():
        repeats = max(1, min(int(repeat_override), 5))
    # The configured model list is the measurement. A page budget does not drop engines.
    engine_ids = [ad.engine_id for ad in adapters]

    try:
        report = await benchmark_runner.execute_benchmark(
            domain=domain,
            brand_name=brand_name,
            industry=industry,
            services=services,
            competitors=competitors,
            locations=locations,
            mode="comprehensive",
            engines=engine_ids,
            repeats=repeats,
            max_queries=max_queries,
        )
    except Exception as exc:
        logger.warning("Live AI visibility monitor failed open: %s", exc)
        return (
            AiVisibilityScorecard(
                status="NOT_MEASURED",
                not_measured_reason=f"Live monitor failed: {exc}",
            ),
            None,
        )

    scorecard = build_visibility_scorecard(
        report,
        services=services,
        competitors=competitors,
        locations=locations,
        industry=industry,
        audience=audience,
        matrix_grounding=getattr(report, "matrix_grounding", None),
    )
    if scorecard.status != "MEASURED":
        return scorecard, report

    try:
        records = []
        for ev in report.evaluations:
            if ev.status != "SUCCESS":
                continue
            records.append(GeoQueryRecord(
                query_id=f"{ev.query_id}-r{ev.run_index}",
                buyer_query=ev.query_text,
                commercial_intent=ev.category,
                engine_id=ev.engine_id,
                engine_name=ev.engine_name,
                raw_response_text=ev.raw_response or "",
                was_mentioned=ev.was_mentioned,
                mention_position=ev.mention_position,
                was_cited=ev.was_first_party_cited,
                cited_urls=list(ev.citations or []),
                competitor_cited_instead=None,
                extractability_health="MEASURED",
            ))
        geo_pipeline_store.save_snapshot(
            snapshot_id=report.benchmark_id,
            domain=domain,
            brand_name=brand_name or domain,
            industry=industry or "",
            overall_score=int(round(scorecard.citation_rate_pct or 0)),
            engine_scores={
                eid: (agg.mention_rate_pct if agg.mention_rate_pct is not None else 0.0)
                for eid, agg in report.engine_aggregates.items()
                if agg.queries_succeeded > 0
            },
            critical_blindspots=report.critical_blindspots,
            query_results=records,
            engines_measured_count=scorecard.engines_measured,
        )
    except Exception as exc:
        logger.warning("Could not persist AI visibility snapshot: %s", exc)

    return scorecard, report

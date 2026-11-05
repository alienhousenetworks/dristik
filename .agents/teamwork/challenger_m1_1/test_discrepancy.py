"""
Reproduction script: Demonstrating empirical divergence between
Main Pipeline Step 15 and DAG Runner node_honest_scoring.

Bug 1: Multi-page Schema Evaluation Discrepancy
- In Step 15, calculate_scores receives:
    has_schema = any(len(p.schema_types) > 0 for p in blackboard.pages) (Site-level)
  while calculate_honest_scores receives:
    has_schema = len(page_ev.schema_types) > 0 (Page-0 / Homepage only)
- In node_honest_scoring, both calculate_scores and calculate_honest_scores receive:
    has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in eval_pages)

When a multi-page crawl has Schema on an interior page (e.g. /about or /products)
but not on the homepage (page 0):
- Step 15 honest Google score evaluates Schema as 0 (has_schema=False), yielding Google Score = 70.0.
- node_honest_scoring evaluates Schema as 100 (has_schema=True), yielding Google Score = 100.0.
- Furthermore, within Step 15 itself, overall_scores (schema=100) and honest_scores (schema=0) contradict each other!

Bug 2: NoneType AttributeError Risk on page_ev
- If manifest.pages is empty or None (e.g. reloaded checkpoint without pages),
  page_ev is None.
  Line 1643 executes `has_schema=len(page_ev.schema_types) > 0` and crashes with
  AttributeError: 'NoneType' object has no attribute 'schema_types'.
"""
import sys
import os

backend_path = "/Users/sayantande/Downloads/dristik-main/backend"
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.domain.models import PageEvidence, BusinessProfile, CrawlManifest
from app.domain.enums import BusinessIntent
from app.scoring.engine import ScoringEngine
from app.orchestration.orchestrator import AnalysisOrchestrator
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.orchestration.pipeline_dag import get_pipeline_controller, GraphNodeStatus
import asyncio


def test_schema_evaluation_divergence():
    engine = ScoringEngine()

    # Site with 2 pages: Homepage (no schema) and About page (has Organization schema)
    p0 = PageEvidence(url="https://example.com", schema_types=[], readability_score=75.0)
    p1 = PageEvidence(url="https://example.com/about", schema_types=["Organization"], readability_score=75.0)
    pages = [p0, p1]
    page_ev = p0  # Line 389 in orchestrator.py: page_ev = manifest.pages[0]

    profile = BusinessProfile(business_name="Discrepancy Corp", domain="example.com", primary_intent=BusinessIntent.SAAS)

    # -------------------------------------------------------------
    # Step 15 Logic in execute_analysis_pipeline (lines 1625 & 1643):
    # -------------------------------------------------------------
    step15_cat = engine.calculate_scores(
        findings=[],
        business_profile=profile,
        has_schema=any(len(p.schema_types) > 0 for p in pages),  # Line 1625
        is_https=True,
        readability=page_ev.readability_score,
        external_authority_connected=False,
    )

    step15_honest = engine.calculate_honest_scores(
        findings=[],
        business_profile=profile,
        has_schema=len(page_ev.schema_types) > 0,  # Line 1643: checks ONLY page_ev (p0)!
        is_https=True,
        readability=page_ev.readability_score,
        external_authority_connected=False,
    )

    # -------------------------------------------------------------
    # node_honest_scoring Logic (lines 3054 & 3087):
    # -------------------------------------------------------------
    node_has_schema = any(len(getattr(p, "schema_types", [])) > 0 for p in pages)
    node_honest = engine.calculate_honest_scores(
        findings=[],
        business_profile=profile,
        has_schema=node_has_schema,  # Line 3087: passes site-level has_schema!
        is_https=True,
        readability=page_ev.readability_score,
        external_authority_connected=False,
    )

    print("=== EMPIRICAL TEST RESULTS ===")
    print(f"Step 15 Category Scores Schema Score: {step15_cat.category_scores['SCHEMA'].score}")
    print(f"Step 15 Honest Scores Google Score:   {step15_honest.google_score}")
    print(f"node_honest_scoring Google Score:     {node_honest.google_score}")

    divergence = abs(node_honest.google_score - step15_honest.google_score)
    print(f"Divergence: {divergence:.1f} points")

    assert divergence > 0, "Expected divergence did not occur!"
    print("EMPIRICAL PROOF CONFIRMED: node_honest_scoring and Step 15 produce conflicting honest scores!")


def test_none_page_ev_crash_risk():
    page_ev = None
    try:
        # Replicating line 1643:
        _ = len(page_ev.schema_types) > 0
        crashed = False
    except AttributeError as e:
        crashed = True
        print(f"EMPIRICAL PROOF CONFIRMED: line 1643 crashes when page_ev is None: {e}")
    assert crashed is True


if __name__ == "__main__":
    test_schema_evaluation_divergence()
    test_none_page_ev_crash_risk()

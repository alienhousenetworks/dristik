"""Regression tests for P0/P1 evidence, scoring, registry, and tenant-isolation fixes."""
from types import SimpleNamespace

from app.domain.evidence.claim_ledger import ClaimLedgerBuilder
from app.domain.evidence.store import EvidenceStore
from app.orchestration.runtime.registry import (
    AGENT_REGISTRY,
    GEO_SPECIALISTS_V3,
    SPECIALIST_AGENTS_V3,
)
from app.seo.competitive.scoring.landscape_calculator import landscape_calculator


def test_claim_ledger_build_ledger_returns_ledger_not_none():
    store = EvidenceStore(run_id="run_test_ledger")
    report = SimpleNamespace(
        analysis_id="run_test_ledger",
        website_url="https://example.com",
        story_summary="The site has clear product headings on the homepage.",
        what_site_gets_right=[],
        what_is_holding_it_back=[],
        primary_strategic_opportunity="",
        findings=[],
    )
    builder = ClaimLedgerBuilder(run_id="run_test_ledger")
    ledger = builder.build_ledger(report=report, store=store)
    assert ledger is not None
    assert ledger.ledger_id == "LEDGER_run_test_ledger"
    assert ledger.rejected_unsupported_count == 0
    assert len(ledger.entries) == 1


def test_landscape_calculator_returns_none_for_unmeasured_dimensions():
    coords = landscape_calculator.compute_coordinates(search_dim=None, geo_dim=None)
    assert coords.x is None
    assert coords.y is None


def test_geo_registry_does_not_overwrite_specialist_agents():
    assert GEO_SPECIALISTS_V3["geo.extractability.v3"] is SPECIALIST_AGENTS_V3["geo.extractability.v3"]
    assert GEO_SPECIALISTS_V3["geo.information_gain.v3"] is SPECIALIST_AGENTS_V3["geo.information_gain.v3"]
    assert AGENT_REGISTRY["geo.extractability.v3"].agent_name == "Answer Extractability Agent"

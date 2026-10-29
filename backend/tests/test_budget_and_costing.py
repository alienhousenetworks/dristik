"""
Tests for BudgetManager, SubStepCostRecord, TelemetryTracker sub-step accounting,
and actual vs calculated token cost accuracy.
"""
import pytest
from app.domain.models import TelemetryData, StageCostRecord, SubStepCostRecord
from app.inference.budget_manager import BudgetManager, budget_manager
from app.inference.telemetry import TelemetryTracker
from app.inference.pricing import price_call


def test_sub_step_cost_record_model():
    sub = SubStepCostRecord(
        sub_step="brand_identity",
        display_name="Brand Identity Extraction",
        capability="business_understanding",
        calls_count=2,
        input_tokens=2500,
        output_tokens=700,
        total_tokens=3200,
        cost_usd=0.0048,
        latency_ms=850.5,
        models=["anthropic/claude-3-5-haiku"],
        is_actual=False,
        cost_basis="list_price",
        formula_rate="$0.80/1M in · $4.00/1M out",
    )
    assert sub.calls_count == 2
    assert sub.cost_usd == 0.0048
    assert sub.is_actual is False
    assert sub.formula_rate == "$0.80/1M in · $4.00/1M out"


def test_telemetry_sub_step_recording():
    telemetry = TelemetryTracker()
    telemetry.set_active_stage("business_understanding", "Business Identity Resolution")
    telemetry.set_active_sub_stage("brand_identity_extraction", "Brand Identity, ICP & Value Prop Resolution")

    # Record a call with known model (e.g. gemini-2.0-flash: $0.10 in / $0.40 out per 1M)
    telemetry.record_call(
        input_tokens=10000,
        output_tokens=2000,
        latency_ms=450.0,
        capability="business_understanding",
        model="gemini-2.0-flash",
        provider="gemini",
    )

    stage_rec = telemetry.telemetry.stage_costs.get("business_understanding")
    assert stage_rec is not None
    assert stage_rec.calls_count == 1
    assert stage_rec.input_tokens == 10000
    assert stage_rec.output_tokens == 2000

    # Expected: (10,000 / 1,000,000 * 0.10) + (2,000 / 1,000,000 * 0.40) = 0.0010 + 0.0008 = 0.0018
    assert round(stage_rec.cost_usd, 4) == 0.0018

    # Verify sub-step record
    assert "brand_identity_extraction" in stage_rec.sub_steps
    sub_rec = stage_rec.sub_steps["brand_identity_extraction"]
    assert sub_rec.calls_count == 1
    assert sub_rec.input_tokens == 10000
    assert sub_rec.output_tokens == 2000
    assert round(sub_rec.cost_usd, 4) == 0.0018
    assert sub_rec.is_actual is False
    assert sub_rec.cost_basis == "list_price"
    assert "$0.10" in (sub_rec.formula_rate or "")


def test_telemetry_actual_provider_billed():
    telemetry = TelemetryTracker()
    telemetry.set_active_stage("ai_visibility_monitor", "Live AI Citation & Search Visibility")
    telemetry.set_active_sub_stage("openrouter_inquiry", "OpenRouter Multi-Engine Call")

    # OpenRouter returns actual billed cost
    telemetry.record_call(
        input_tokens=1500,
        output_tokens=400,
        latency_ms=1200.0,
        capability="geo_query",
        model="anthropic/claude-3-5-sonnet",
        provider="openrouter",
        provider_cost_usd=0.003425,
    )

    stage_rec = telemetry.telemetry.stage_costs.get("ai_visibility_monitor")
    assert stage_rec is not None
    sub_rec = stage_rec.sub_steps["openrouter_inquiry"]
    assert sub_rec.is_actual is True
    assert sub_rec.cost_basis == "provider_billed"
    assert sub_rec.cost_usd == 0.003425
    assert telemetry.telemetry.actual_cost_usd == 0.003425
    assert telemetry.telemetry.has_actual_costs is True


def test_budget_manager_check_and_breakdown():
    bm = BudgetManager(max_budget_usd=1.00)
    t = TelemetryData(
        estimated_cost_usd=0.25,
        actual_cost_usd=0.10,
        calculated_cost_usd=0.15,
        total_tokens=45000,
        input_tokens=35000,
        output_tokens=10000,
        model_calls_count=12,
        total_latency_ms=8500.0,
        cost_basis="mixed",
    )
    status = bm.check_budget(t)
    assert status.is_exceeded is False
    assert status.utilization_pct == 25.0
    assert status.remaining_usd == 0.75

    breakdown = bm.generate_full_ledger_breakdown(t)
    assert breakdown["summary"]["total_cost_usd"] == 0.25
    assert breakdown["summary"]["actual_cost_usd"] == 0.10
    assert breakdown["summary"]["calculated_cost_usd"] == 0.15

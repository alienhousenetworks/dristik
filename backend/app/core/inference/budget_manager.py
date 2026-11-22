"""
Dristik AI Inference Budget Manager & Unit Economics Accounting
Manages per-stage, per-sub-step cost ledgers, enforces spend limits,
and generates granular zero-fake-data cost breakdowns.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

from app.domain.models import TelemetryData, StageCostRecord, SubStepCostRecord
from app.core.inference.pricing import _LIST_USD_PER_MILLION, canonical_provider

logger = logging.getLogger(__name__)


@dataclass
class AuditBudgetPlan:
    """Dynamic per-audit budget and token envelope scaled from pages_crawled (₹20–₹30/page target)."""
    pages_count: int
    depth_mode: str
    max_budget_usd: float
    max_budget_inr: float
    effective_per_page_usd: float
    effective_per_page_inr: float
    max_model_calls: int
    frontier_copy_page_cap: int
    per_page_token_cap: int


@dataclass
class BudgetStatus:
    max_budget_usd: float
    current_spent_usd: float
    actual_spent_usd: float
    calculated_spent_usd: float
    is_exceeded: bool
    utilization_pct: float
    remaining_usd: float


class BudgetManager:
    """
    Central manager for inference cost accounting, stage/sub-step ledger aggregation,
    and budget enforcement across autonomous audit runs and live GEO benchmarks.
    """

    def __init__(self, max_budget_usd: float = 2.50, warning_threshold_pct: float = 85.0):
        self.max_budget_usd = max_budget_usd
        self.warning_threshold_pct = warning_threshold_pct

    @staticmethod
    def compute_audit_budget(
        pages_count: int,
        depth_mode: Optional[str] = None,
    ) -> AuditBudgetPlan:
        """
        Computes a dynamic per-audit USD/INR budget & call envelope using a base + tiered
        per-page curve (~₹20–₹30/page):
          - Base site overhead covers Business Understanding, 100-Q AEO RAG, Critic, Remediation, Roadmap.
          - Pages 1..20   -> AUDIT_PER_PAGE_USD_TIER1 (~$0.30/pg ≈ ₹25.5/pg)
          - Pages 21..50  -> AUDIT_PER_PAGE_USD_TIER2 (~$0.24/pg ≈ ₹20.4/pg)
          - Pages 51+     -> AUDIT_PER_PAGE_USD_TIER3 (~$0.18/pg ≈ ₹15.3/pg volume taper)
        """
        from app.core.config import settings
        n = max(1, int(pages_count or 1))
        mode = (depth_mode or getattr(settings, "AI_DEPTH_MODE", "tiered_frontier") or "tiered_frontier").strip().lower()
        base_usd = float(getattr(settings, "AUDIT_BASE_BUDGET_USD", 0.45))
        r1 = float(getattr(settings, "AUDIT_PER_PAGE_USD_TIER1", 0.30))
        r2 = float(getattr(settings, "AUDIT_PER_PAGE_USD_TIER2", 0.24))
        r3 = float(getattr(settings, "AUDIT_PER_PAGE_USD_TIER3", 0.18))
        fx = float(getattr(settings, "USD_TO_INR_RATE", 85.0))

        t1 = min(n, 20)
        t2 = min(max(n - 20, 0), 30)
        t3 = max(n - 50, 0)
        total_usd = base_usd + (t1 * r1) + (t2 * r2) + (t3 * r3)
        if mode == "frontier_all":
            total_usd *= 1.45

        total_usd = round(total_usd, 4)
        per_page_usd = round(total_usd / n, 4)

        # Call cap scales cleanly: ~60 site-level specialist/AEO/critic/remediation calls + ~2 calls per page
        max_calls = max(80, min(600, 65 + (n * 2)))
        frontier_copy_cap = n if mode == "frontier_all" else min(n, 40)
        per_page_tokens = 12000 if n <= 20 else (8000 if n <= 50 else 5000)

        return AuditBudgetPlan(
            pages_count=n,
            depth_mode=mode,
            max_budget_usd=total_usd,
            max_budget_inr=round(total_usd * fx, 2),
            effective_per_page_usd=per_page_usd,
            effective_per_page_inr=round(per_page_usd * fx, 2),
            max_model_calls=max_calls,
            frontier_copy_page_cap=frontier_copy_cap,
            per_page_token_cap=per_page_tokens,
        )

    def check_budget(self, telemetry: TelemetryData) -> BudgetStatus:
        spent = telemetry.estimated_cost_usd or 0.0
        util_pct = (spent / self.max_budget_usd * 100.0) if self.max_budget_usd > 0 else 0.0
        is_exceeded = spent >= self.max_budget_usd
        remaining = max(0.0, self.max_budget_usd - spent)
        return BudgetStatus(
            max_budget_usd=self.max_budget_usd,
            current_spent_usd=round(spent, 6),
            actual_spent_usd=round(telemetry.actual_cost_usd or 0.0, 6),
            calculated_spent_usd=round(telemetry.calculated_cost_usd or 0.0, 6),
            is_exceeded=is_exceeded,
            utilization_pct=round(util_pct, 2),
            remaining_usd=round(remaining, 6),
        )

    @staticmethod
    def get_rate_card(provider: Optional[str], model: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
        """Returns (input_per_million, output_per_million) if known in official price table."""
        canon = canonical_provider(provider)
        m = (model or "").strip()
        rates = _LIST_USD_PER_MILLION.get((canon, m))
        if rates:
            return rates
        return None, None

    @staticmethod
    def format_rate_formula(provider: Optional[str], model: Optional[str]) -> str:
        """Returns human-readable pricing rate string, e.g. '$3.00/1M in · $15.00/1M out'."""
        in_rate, out_rate = BudgetManager.get_rate_card(provider, model)
        if in_rate is not None and out_rate is not None:
            return f"${in_rate:.2f}/1M in · ${out_rate:.2f}/1M out"
        return "List price / Dynamic"

    @staticmethod
    def generate_full_ledger_breakdown(telemetry: TelemetryData) -> Dict[str, Any]:
        """
        Builds a comprehensive hierarchical step and sub-step breakdown with exact
        math, token counts, and provider vs list price basis.
        """
        stages_ledger = []
        total_calls = telemetry.model_calls_count or 0
        total_in = telemetry.input_tokens or 0
        total_out = telemetry.output_tokens or 0
        total_cost = round(telemetry.estimated_cost_usd or 0.0, 6)
        actual_cost = round(telemetry.actual_cost_usd or 0.0, 6)
        calc_cost = round(telemetry.calculated_cost_usd or 0.0, 6)

        for stage_key, stage_rec in telemetry.stage_costs.items():
            sub_step_list = []
            for sub_key, sub_rec in stage_rec.sub_steps.items():
                primary_model = sub_rec.models[0] if sub_rec.models else "unknown"
                prov = primary_model.split("/")[0] if "/" in primary_model else "unknown"
                mod = primary_model.split("/")[1] if "/" in primary_model else primary_model
                formula = sub_rec.formula_rate or BudgetManager.format_rate_formula(prov, mod)

                sub_step_list.append({
                    "sub_step": sub_rec.sub_step,
                    "display_name": sub_rec.display_name,
                    "capability": sub_rec.capability,
                    "calls_count": sub_rec.calls_count,
                    "input_tokens": sub_rec.input_tokens,
                    "output_tokens": sub_rec.output_tokens,
                    "total_tokens": sub_rec.total_tokens,
                    "cost_usd": round(sub_rec.cost_usd, 6),
                    "latency_ms": round(sub_rec.latency_ms, 1),
                    "models": sub_rec.models,
                    "is_actual": sub_rec.is_actual,
                    "cost_basis": sub_rec.cost_basis,
                    "formula_rate": formula,
                })

            stages_ledger.append({
                "stage": stage_rec.stage,
                "display_name": stage_rec.display_name,
                "calls_count": stage_rec.calls_count,
                "input_tokens": stage_rec.input_tokens,
                "output_tokens": stage_rec.output_tokens,
                "total_tokens": stage_rec.total_tokens,
                "cost_usd": round(stage_rec.cost_usd, 6),
                "latency_ms": round(stage_rec.latency_ms, 1),
                "models": stage_rec.models,
                "sub_steps": sub_step_list,
            })

        from app.core.config import settings
        fx = float(getattr(settings, "USD_TO_INR_RATE", 85.0))
        return {
            "summary": {
                "total_cost_usd": total_cost,
                "total_cost_inr_est": round(total_cost * fx, 2),
                "actual_cost_usd": actual_cost,
                "calculated_cost_usd": calc_cost,
                "has_actual_costs": telemetry.has_actual_costs,
                "all_costs_actual": telemetry.all_costs_actual,
                "total_tokens": total_in + total_out,
                "input_tokens": total_in,
                "output_tokens": total_out,
                "model_calls_count": total_calls,
                "total_latency_ms": round(telemetry.total_latency_ms or 0.0, 1),
                "cost_basis": telemetry.cost_basis,
                "models_used": telemetry.models_used,
            },
            "stages": stages_ledger,
            "agent_calls_count": len(telemetry.agent_calls),
        }


budget_manager = BudgetManager()

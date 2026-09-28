"""
Dristik AI Inference Telemetry & Cost Accounting
Token counts, latency, and the USD cost of the provider and model that ran.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4
from app.domain.models import AgentCallRecord, StageCostRecord, SubStepCostRecord, TelemetryData
from app.inference.pricing import canonical_provider, price_call_from_settings


class TelemetryTracker:
    def __init__(self):
        self.telemetry = TelemetryData()
        self._bases: Set[str] = set()
        self.current_stage = "general"
        self.current_stage_display = "General Execution"
        self.current_sub_step = "default"
        self.current_sub_step_display = "Default Execution"

    def set_active_stage(self, stage: str, display_name: Optional[str] = None) -> None:
        self.current_stage = stage
        self.current_stage_display = display_name or stage.replace("_", " ").title()
        if stage not in self.telemetry.stage_costs:
            self.telemetry.stage_costs[stage] = StageCostRecord(
                stage=stage,
                display_name=self.current_stage_display,
            )

    def set_active_sub_stage(self, sub_step: str, display_name: Optional[str] = None) -> None:
        self.current_sub_step = sub_step
        self.current_sub_step_display = display_name or sub_step.replace("_", " ").title()
        # Ensure parent stage exists
        if self.current_stage not in self.telemetry.stage_costs:
            self.set_active_stage(self.current_stage)
        stage_rec = self.telemetry.stage_costs[self.current_stage]
        if sub_step not in stage_rec.sub_steps:
            stage_rec.sub_steps[sub_step] = SubStepCostRecord(
                sub_step=sub_step,
                display_name=self.current_sub_step_display,
            )

    def get_current_stage_cost(self) -> float:
        stage_rec = self.telemetry.stage_costs.get(self.current_stage)
        return stage_rec.cost_usd if stage_rec else 0.0

    def get_live_summary(self) -> Dict[str, Any]:
        return {
            "total_cost_usd": self.telemetry.estimated_cost_usd,
            "actual_cost_usd": self.telemetry.actual_cost_usd,
            "calculated_cost_usd": self.telemetry.calculated_cost_usd,
            "has_actual_costs": self.telemetry.has_actual_costs,
            "all_costs_actual": self.telemetry.all_costs_actual,
            "total_tokens": self.telemetry.total_tokens,
            "input_tokens": self.telemetry.input_tokens,
            "output_tokens": self.telemetry.output_tokens,
            "model_calls_count": self.telemetry.model_calls_count,
            "active_stage": self.current_stage,
            "active_stage_display": self.current_stage_display,
            "active_stage_cost_usd": self.get_current_stage_cost(),
            "stage_costs": [s.model_dump() for s in self.telemetry.stage_costs.values()],
        }

    def record_call(
        self,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        capability: str,
        is_reasoning: bool = False,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        prompt_sha256: Optional[str] = None,
        prompt_template_sha256: Optional[str] = None,
        agent_id: Optional[str] = None,
        provider_cost_usd: Optional[float] = None,
    ):
        del is_reasoning  # Pricing follows the model that ran, not the fast/reasoning bucket.
        self.telemetry.input_tokens += input_tokens
        self.telemetry.output_tokens += output_tokens
        self.telemetry.total_tokens += (input_tokens + output_tokens)
        self.telemetry.total_latency_ms += latency_ms
        self.telemetry.model_calls_count += 1

        served_model = (model or "").strip() or "unknown"
        served_provider = canonical_provider(provider)
        quote = price_call_from_settings(
            provider=served_provider,
            model=served_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_cost_usd=provider_cost_usd,
        )
        if quote.cost_usd is None:
            self.telemetry.unpriced_calls += 1
        else:
            self.telemetry.estimated_cost_usd = round(self.telemetry.estimated_cost_usd + quote.cost_usd, 6)
            if quote.is_actual:
                self.telemetry.actual_cost_usd = round(self.telemetry.actual_cost_usd + quote.cost_usd, 6)
            else:
                self.telemetry.calculated_cost_usd = round(self.telemetry.calculated_cost_usd + quote.cost_usd, 6)

        self._bases.add(quote.basis)

        label = f"{served_provider}/{served_model}"
        if label not in self.telemetry.models_used:
            self.telemetry.models_used.append(label)
        self._refresh_cost_basis()

        # Update stage-level cost breakdown
        if self.current_stage not in self.telemetry.stage_costs:
            self.telemetry.stage_costs[self.current_stage] = StageCostRecord(
                stage=self.current_stage,
                display_name=self.current_stage_display,
            )
        stage_rec = self.telemetry.stage_costs[self.current_stage]
        stage_rec.calls_count += 1
        stage_rec.input_tokens += input_tokens
        stage_rec.output_tokens += output_tokens
        stage_rec.total_tokens += (input_tokens + output_tokens)
        stage_rec.latency_ms = round(stage_rec.latency_ms + latency_ms, 1)
        if quote.cost_usd is not None:
            stage_rec.cost_usd = round(stage_rec.cost_usd + quote.cost_usd, 6)
        if label not in stage_rec.models:
            stage_rec.models.append(label)

        # Update sub-step level cost breakdown
        if self.current_sub_step not in stage_rec.sub_steps:
            stage_rec.sub_steps[self.current_sub_step] = SubStepCostRecord(
                sub_step=self.current_sub_step,
                display_name=self.current_sub_step_display,
                capability=capability,
            )
        sub_rec = stage_rec.sub_steps[self.current_sub_step]
        sub_rec.calls_count += 1
        sub_rec.input_tokens += input_tokens
        sub_rec.output_tokens += output_tokens
        sub_rec.total_tokens += (input_tokens + output_tokens)
        sub_rec.latency_ms = round(sub_rec.latency_ms + latency_ms, 1)
        if quote.cost_usd is not None:
            sub_rec.cost_usd = round(sub_rec.cost_usd + quote.cost_usd, 6)
        if label not in sub_rec.models:
            sub_rec.models.append(label)
        sub_rec.is_actual = quote.is_actual
        sub_rec.cost_basis = quote.basis
        if quote.is_actual:
            sub_rec.formula_rate = "Provider in-band billed"
        elif quote.cost_usd is not None:
            from app.inference.budget_manager import BudgetManager
            sub_rec.formula_rate = BudgetManager.format_rate_formula(served_provider, served_model)

        current_agent_time = self.telemetry.agent_timings.get(capability, 0.0)
        self.telemetry.agent_timings[capability] = round(current_agent_time + latency_ms, 1)

        actual_cost = quote.cost_usd if quote.is_actual else None
        calculated_cost = quote.cost_usd if (not quote.is_actual and quote.cost_usd is not None) else None

        self.telemetry.agent_calls.append(AgentCallRecord(
            call_id=f"call_{uuid4().hex[:12]}",
            capability=capability,
            agent_id=agent_id or capability,
            model=served_model,
            provider=served_provider,
            prompt_sha256=prompt_sha256 or "",
            prompt_template_sha256=prompt_template_sha256 or "",
            called_at=datetime.now(timezone.utc).isoformat(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=quote.cost_usd,
            cost_basis=quote.basis,
            is_actual=quote.is_actual,
            actual_cost_usd=actual_cost,
            calculated_cost_usd=calculated_cost,
        ))
        self.telemetry.has_actual_costs = any(c.is_actual for c in self.telemetry.agent_calls)
        self.telemetry.all_costs_actual = bool(
            self.telemetry.agent_calls and all(c.is_actual for c in self.telemetry.agent_calls)
        )

    def _refresh_cost_basis(self) -> None:
        priced = {basis for basis in self._bases if basis != "unpriced"}
        if self.telemetry.unpriced_calls:
            self.telemetry.cost_complete = False
            self.telemetry.cost_basis = "unpriced" if not priced else "mixed"
            return
        self.telemetry.cost_complete = True
        if len(priced) == 1:
            self.telemetry.cost_basis = next(iter(priced))
        elif priced:
            self.telemetry.cost_basis = "mixed"
        else:
            self.telemetry.cost_basis = "unpriced"

    def get_data(self) -> TelemetryData:
        return self.telemetry


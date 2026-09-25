"""
Dristik AI Inference Telemetry & Cost Accounting
Token counts, latency, and the USD cost of the provider and model that ran.
"""
from datetime import datetime, timezone
from typing import Optional, Set
from uuid import uuid4
from app.domain.models import AgentCallRecord, TelemetryData
from app.inference.pricing import canonical_provider, price_call_from_settings


class TelemetryTracker:
    def __init__(self):
        self.telemetry = TelemetryData()
        self._bases: Set[str] = set()

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
        self._bases.add(quote.basis)

        label = f"{served_provider}/{served_model}"
        if label not in self.telemetry.models_used:
            self.telemetry.models_used.append(label)
        self._refresh_cost_basis()

        current_agent_time = self.telemetry.agent_timings.get(capability, 0.0)
        self.telemetry.agent_timings[capability] = round(current_agent_time + latency_ms, 1)
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
        ))

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

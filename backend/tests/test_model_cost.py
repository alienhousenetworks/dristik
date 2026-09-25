"""Cost follows the provider and model that ran, or the rate the operator set."""
from app.inference.pricing import parse_operator_rates, price_call, provider_billed_usd
from app.inference.telemetry import TelemetryTracker


def test_list_price_uses_the_model_that_ran():
    haiku = price_call(
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        input_tokens=1_000_000,
        output_tokens=200_000,
    )
    groq = price_call(
        provider="groq",
        model="openai/gpt-oss-20b",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    assert haiku.basis == "list_price"
    assert haiku.cost_usd == 2.0  # $1 input + $5 * 0.2 output
    assert groq.basis == "list_price"
    assert groq.cost_usd == 0.375  # $0.075 + $0.30


def _clear_rates(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.LLM_MODEL_PRICES", None)
    monkeypatch.setattr("app.core.config.settings.LLM_COST_INPUT_PER_MILLION", None)
    monkeypatch.setattr("app.core.config.settings.LLM_COST_OUTPUT_PER_MILLION", None)


def test_reasoning_flag_does_not_reprice_another_model(monkeypatch):
    _clear_rates(monkeypatch)
    tracker = TelemetryTracker()
    tracker.record_call(
        input_tokens=1_000_000,
        output_tokens=0,
        latency_ms=10,
        capability="synthesizer",
        is_reasoning=True,
        model="claude-haiku-4-5-20251001",
        provider="anthropic",
    )
    data = tracker.get_data()
    assert data.estimated_cost_usd == 1.0
    assert data.cost_basis == "list_price"
    assert data.cost_complete is True
    assert data.models_used == ["anthropic/claude-haiku-4-5-20251001"]
    assert data.agent_calls[0].cost_usd == 1.0


def test_unknown_model_is_unpriced(monkeypatch):
    _clear_rates(monkeypatch)
    tracker = TelemetryTracker()
    tracker.record_call(
        input_tokens=500,
        output_tokens=100,
        latency_ms=4,
        capability="business_icp",
        model="some-new-model",
        provider="openrouter",
    )
    data = tracker.get_data()
    assert data.estimated_cost_usd == 0.0
    assert data.cost_complete is False
    assert data.unpriced_calls == 1
    assert data.cost_basis == "unpriced"
    assert data.agent_calls[0].cost_usd is None


def test_openrouter_gpt4o_is_not_priced_as_openai():
    quote = price_call(
        provider="openrouter",
        model="openai/gpt-4o",
        input_tokens=1_000_000,
        output_tokens=0,
    )
    assert quote.basis == "unpriced"
    assert quote.cost_usd is None


def test_provider_bill_wins_over_list_and_operator_rates():
    rates = parse_operator_rates(
        '{"anthropic/claude-haiku-4-5-20251001": {"input": 9, "output": 9}}'
    )
    quote = price_call(
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        input_tokens=1_000_000,
        output_tokens=0,
        provider_cost_usd=0.0042,
        operator_rates=rates,
        blanket_input_per_million=3,
        blanket_output_per_million=15,
    )
    assert quote.basis == "provider_billed"
    assert quote.cost_usd == 0.0042


def test_operator_model_rate_overrides_list_price():
    rates = parse_operator_rates(
        '{"groq/openai/gpt-oss-120b": {"input": 0.2, "output": 0.8}}'
    )
    quote = price_call(
        provider="groq",
        model="openai/gpt-oss-120b",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        operator_rates=rates,
        blanket_input_per_million=9,
        blanket_output_per_million=9,
    )
    assert quote.basis == "operator_rate"
    assert quote.cost_usd == 1.0


def test_blanket_rate_prices_whatever_model_ran():
    quote = price_call(
        provider="moonshot",
        model="moonshot-v1-8k",
        input_tokens=2_000_000,
        output_tokens=500_000,
        blanket_input_per_million=0.5,
        blanket_output_per_million=2.0,
    )
    assert quote.basis == "operator_rate"
    assert quote.cost_usd == 2.0


def test_tracker_sums_each_models_own_price(monkeypatch):
    _clear_rates(monkeypatch)
    tracker = TelemetryTracker()
    tracker.record_call(1_000_000, 0, 1, "a", model="claude-haiku-4-5-20251001", provider="claude")
    tracker.record_call(1_000_000, 1_000_000, 1, "b", model="openai/gpt-oss-20b", provider="groq", provider_cost_usd=0.01)
    data = tracker.get_data()
    assert data.agent_calls[0].provider == "anthropic"
    assert data.agent_calls[0].cost_basis == "list_price"
    assert data.agent_calls[1].cost_basis == "provider_billed"
    assert data.estimated_cost_usd == 1.01
    assert data.cost_basis == "mixed"
    assert data.cost_complete is True
    assert data.models_used == [
        "anthropic/claude-haiku-4-5-20251001",
        "groq/openai/gpt-oss-20b",
    ]


def test_known_plus_unknown_keeps_the_known_dollars(monkeypatch):
    _clear_rates(monkeypatch)
    tracker = TelemetryTracker()
    tracker.record_call(1_000_000, 0, 1, "a", model="gemini-2.0-flash", provider="google")
    tracker.record_call(100, 100, 1, "b", model="qwen/qwen3.6-27b", provider="groq")
    data = tracker.get_data()
    assert data.agent_calls[0].provider == "gemini"
    assert data.agent_calls[0].cost_usd == 0.1
    assert data.estimated_cost_usd == 0.1
    assert data.unpriced_calls == 1
    assert data.cost_complete is False
    assert data.cost_basis == "mixed"


def test_tracker_uses_the_rate_you_configured(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.LLM_MODEL_PRICES", None)
    monkeypatch.setattr("app.core.config.settings.LLM_COST_INPUT_PER_MILLION", 1.0)
    monkeypatch.setattr("app.core.config.settings.LLM_COST_OUTPUT_PER_MILLION", 2.0)
    tracker = TelemetryTracker()
    tracker.record_call(1_000_000, 1_000_000, 1, "a", model="any-model", provider="custom")
    data = tracker.get_data()
    assert data.estimated_cost_usd == 3.0
    assert data.cost_basis == "operator_rate"
    assert data.cost_complete is True
    assert data.models_used == ["custom/any-model"]


def test_provider_billed_usd_reads_openrouter_usage():
    assert provider_billed_usd({"cost": 0.0125, "prompt_tokens": 10}) == 0.0125
    assert provider_billed_usd({"cost_details": {"upstream_inference_cost": 0.2}}) == 0.2
    assert provider_billed_usd({"prompt_tokens": 10}) is None
    assert provider_billed_usd({"cost": -1}) is None


def test_operator_prices_accept_nested_and_pipe_keys():
    rates = parse_operator_rates(
        '{"anthropic": {"claude-sonnet-4-6": {"input": 3, "output": 15}},'
        '"xai|grok-2-latest": {"input": 2, "output": 10}}'
    )
    sonnet = price_call(
        provider="anthropic",
        model="claude-sonnet-4-6",
        input_tokens=1_000_000,
        output_tokens=0,
        operator_rates=rates,
    )
    grok = price_call(
        provider="xai",
        model="grok-2-latest",
        input_tokens=0,
        output_tokens=1_000_000,
        operator_rates=rates,
    )
    assert sonnet.cost_usd == 3.0
    assert grok.cost_usd == 10.0

"""Offline unit tests for Phase 3: Rank Signal stats, 15-signal catalog, and credit-native runner."""
from datetime import datetime, timezone
import pytest

from app.geo.rank_signal import (
    FEATURE_CATALOG,
    Passage,
    RankSignalRunner,
    SignalContext,
    check_pair,
    get_signal,
    posterior,
    verdict,
)


def test_jeffreys_posterior_and_verdicts():
    assert verdict(10, 19) == "insufficient"
    assert verdict(16, 20) == "positive"
    assert verdict(4, 20) == "negative"
    assert verdict(10, 20) == "pending"
    assert verdict(20, 40) == "no_clear_effect"

    p = posterior(16, 20)
    assert 0.75 < p.mean < 0.85
    assert p.lo > 0.5
    assert p.hi < 1.0


def test_catalog_has_15_signals_and_code_transforms_pass_guardrails():
    assert len(FEATURE_CATALOG) == 15
    ctx = SignalContext(keyword="best enterprise crm", now=datetime(2026, 11, 23, tzinfo=timezone.utc))
    sample = (
        "Acme CRM automates sales pipelines for mid-market teams across North America and Europe. "
        "Revenue teams track every deal stage, forecast quarterly bookings, and synchronize customer records "
        "in one shared workspace without relying on manual spreadsheets or disconnected email threads."
    )

    for sid in ("S05", "S06", "S12", "S13"):
        sig = get_signal(sid)
        assert sig is not None and sig.build == "code" and sig.transform is not None
        transformed = sig.transform(sample, ctx)
        assert transformed is not None
        ok, reason = check_pair(sig, transformed, sample, ctx)
        assert ok, f"{sid} failed check_pair: {reason}"


@pytest.mark.asyncio
async def test_runner_early_stopping_pair_cache_and_credit_refund():
    runner = RankSignalRunner()
    passages = [
        Passage(
            hash=f"h{i:03d}",
            origin="target" if i % 2 == 0 else "competitor",
            url=f"https://acme.com/p{i}",
            text=(
                f"Acme CRM workflow engine handles enterprise ticket batch {i} automatically across regional hubs. "
                "Sales operations teams reduce manual follow-up work, maintain clean pipeline attribution, "
                "and publish audit-ready quarterly forecasts for executive leadership."
            ),
        )
        for i in range(30)
    ]

    # Always prefer the passage that starts with "As of " (S06 freshness clause)
    async def _mock_judge(keyword: str, a: str, b: str, model: str):
        choice = "A" if a.startswith("As of ") else "B"
        return choice, 0.0005

    events = []
    async for ev_type, data in runner.run_stream(
        signal_id="S06",
        keyword="enterprise crm",
        target_url="https://acme.com",
        passages=passages,
        is_byok=False,
        judge_fn=_mock_judge,
    ):
        events.append((ev_type, data))

    done = [d for t, d in events if t == "signal_done"][0]
    assert done["n_valid"] == 20
    assert done["wins"] == 20
    assert done["verdict"] == "positive"
    assert done["end_reason"] == "verdict"
    # Stopped at n=20 instead of 40 -> 50% credit refund!
    assert done["credits"]["reserved_credits"] == 1.0
    assert done["credits"]["charged_credits"] == 0.5
    assert done["credits"]["refunded_credits"] == 0.5

    # Second run reuses cached A/B pairs (20 cache hits) and BYOK charges 0 credits
    events2 = []
    async for ev_type, data in runner.run_stream(
        signal_id="S06",
        keyword="enterprise crm",
        target_url="https://acme.com",
        passages=passages,
        is_byok=True,
        judge_fn=_mock_judge,
    ):
        events2.append((ev_type, data))
    done2 = [d for t, d in events2 if t == "signal_done"][0]
    assert done2["cache_hits"] == 20
    assert done2["credits"]["billing_mode"] == "byok"
    assert done2["credits"]["charged_credits"] == 0.0

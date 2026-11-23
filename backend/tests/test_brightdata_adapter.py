"""Offline unit tests for Phase 4: Bright Data consumer-UI adapter & country tracking."""
import pytest
from app.geo.adapters.brightdata import (
    BrightDataConsumerAdapter,
    filter_third_party_citations,
)
from app.geo.models import GEOTestingMode


def test_filter_third_party_citations_strips_noise():
    raw = [
        "https://acme.com/pricing",
        "https://chatgpt.com/c/12345",
        "https://cdn.jsdelivr.net/npm/pkg.js",
        "https://acme.com/logo.png",
        "https://g2.com/products/acme/reviews",
        "https://google-analytics.com/collect",
    ]
    cleaned = filter_third_party_citations(raw)
    assert cleaned == [
        "https://acme.com/pricing",
        "https://g2.com/products/acme/reviews",
    ]


@pytest.mark.asyncio
async def test_brightdata_adapter_fails_closed_without_key():
    adapter = BrightDataConsumerAdapter("google_ai_mode", api_key="")
    assert adapter.supports_geo_controls is True
    assert adapter.default_testing_mode == GEOTestingMode.LIVE_PRODUCT_TEST

    res = await adapter.execute_prompt({"prompt": "best crm for startups", "market": "GB"})
    assert res.is_live is False
    assert res.status_code == 401
    assert res.testing_mode == GEOTestingMode.LIVE_PRODUCT_TEST
    assert res.tool_use_metadata["country"] == "GB"

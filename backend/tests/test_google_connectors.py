import pytest
from app.integrations.google_connectors import (
    GoogleSearchConsoleConnector,
    GoogleAnalytics4Connector,
    gsc_connector,
    ga4_connector,
)
from app.domain.enums import MetricProvenanceState


def test_gsc_connector_unconfigured_fail_closed():
    """Unconnected GSC must never return fake fixture clicks or queries."""
    connector = GoogleSearchConsoleConnector(credentials_json=None)
    summary = connector.fetch_performance("https://acme-analytics.io", days=90)

    assert summary.domain == "acme-analytics.io"
    assert summary.connected is False
    assert summary.provenance == MetricProvenanceState.NOT_CONFIGURED
    assert summary.total_clicks == 0
    assert summary.total_impressions == 0
    assert summary.average_ctr == 0.0
    assert summary.average_position == 0.0
    assert len(summary.queries) == 0
    assert "not configured" in summary.status_notice.lower()


def test_ga4_connector_unconfigured_fail_closed():
    """Unconnected GA4 must never return fake sessions (18,450) or bounce rates."""
    connector = GoogleAnalytics4Connector(property_id=None)
    summary = connector.fetch_performance("https://acme-analytics.io")

    assert summary.domain == "acme-analytics.io"
    assert summary.connected is False
    assert summary.provenance == MetricProvenanceState.NOT_CONFIGURED
    assert summary.sessions_30d == 0
    assert summary.bounce_rate == 0.0
    assert summary.conversion_rate == 0.0
    assert summary.conversions_count == 0
    assert len(summary.top_landing_pages) == 0
    assert "not connected" in summary.status_notice.lower()


def test_integrations_api_router_zero_synthetic():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    status_resp = client.get("/api/v1/integrations/status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert "google_search_console" in data
    assert "google_analytics_4" in data
    assert "dataforseo_keyword_index" in data

    # Unconfigured GSC endpoint must return NOT_CONFIGURED and 0 clicks
    gsc_resp = client.get("/api/v1/integrations/gsc/performance?domain=example.com")
    assert gsc_resp.status_code == 200
    gsc_data = gsc_resp.json()
    assert gsc_data["domain"] == "example.com"
    assert gsc_data["connected"] is False
    assert gsc_data["provenance"] == "NOT_CONFIGURED"
    assert gsc_data["total_clicks"] == 0
    assert len(gsc_data["queries"]) == 0

    # Unconfigured GA4 endpoint must return NOT_CONFIGURED and 0 sessions
    ga4_resp = client.get("/api/v1/integrations/ga4/performance?domain=example.com")
    assert ga4_resp.status_code == 200
    ga4_data = ga4_resp.json()
    assert ga4_data["domain"] == "example.com"
    assert ga4_data["provenance"] == "NOT_CONFIGURED"
    assert ga4_data["sessions_30d"] == 0

    # Test connect validation fails-closed on invalid credentials
    invalid_gsc = client.post("/api/v1/integrations/gsc/connect", json={"credentials_json_path": "/nonexistent/path.json"})
    assert invalid_gsc.status_code == 400

    invalid_ga4 = client.post("/api/v1/integrations/ga4/connect", json={"property_id": "   "})
    assert invalid_ga4.status_code == 400

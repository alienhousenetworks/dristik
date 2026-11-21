import pytest
from app.connectors.seo_connector_manager import ConnectorManager

def test_connector_manager_listing():
    mgr = ConnectorManager()
    connectors = mgr.list_all_connectors()
    assert len(connectors) >= 6

    ids = [c.provider_id for c in connectors]
    assert "google_search_console" in ids
    assert "google_analytics_4" in ids
    assert "pagespeed_crux" in ids
    assert "backlink_provider" in ids
    assert "keyword_serp_provider" in ids
    assert "google_business_profile" in ids

def test_connector_handshake_and_disconnect():
    mgr = ConnectorManager()
    # Initial status
    status = mgr.get_connector_status("google_business_profile")
    assert status.status == "NOT_CONFIGURED"

    # Connect
    connected = mgr.connect_provider("google_business_profile", {"api_key": "test_key_123"})
    assert connected.status == "CONNECTED"
    assert mgr.is_agent_connector_active("agent_local_gbp") is True

    # Disconnect
    assert mgr.disconnect_provider("google_business_profile") is True
    assert mgr.get_connector_status("google_business_profile").status == "NOT_CONFIGURED"
    assert mgr.is_agent_connector_active("agent_local_gbp") is False

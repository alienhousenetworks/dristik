"""Citation catalog strips secrets and keeps buyer surfaces unqueried."""
from app.geo.citation_models import citation_catalog, unqueried_surfaces


def test_catalog_has_no_secrets_and_names_unqueried_surfaces():
    catalog = citation_catalog()
    assert catalog
    for engine in catalog:
        assert "api_key" not in engine
        assert "token" not in engine
    missing = unqueried_surfaces()
    assert "Google AI Overviews" in missing
    assert "Google AI Mode" in missing
    assert "Bing Copilot" in missing

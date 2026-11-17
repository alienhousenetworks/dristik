import pytest
from app.domain.models import PageEvidence, SchemaValidationReport
from app.seo.analyzers.schema_validator import analyze_schema_rich_results
from app.cro.reporting import CroReportGenerator
from app.cro.engine import build_cro_intelligence

def test_phase4_schema_canonical_inventory_and_organization_reconciliation():
    """Verify schema extraction produces canonical inventory and reconciles top-level vs embedded graph Organization."""
    # Test case 1: Page has @graph containing Organization and WebSite
    page_graph = PageEvidence(
        url="https://perforacare.com/",
        raw_schema=[{
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebSite", "@id": "https://perforacare.com/#website", "name": "Perfora"},
                {"@type": "Organization", "@id": "https://perforacare.com/#org", "name": "Perfora", "url": "https://perforacare.com"},
            ]
        }]
    )

    report = analyze_schema_rich_results([page_graph])
    assert "Organization" in report.detected_types
    assert "WebSite" in report.detected_types
    assert report.json_ld_blocks == 1
    assert report.has_graph_organization_reference is True
    # The canonical inventory records all dimensions without contradiction
    inv = report.canonical_inventory
    assert inv["syntax_valid"] is True
    assert inv["semantic_validation"] in ("PASS", "PARTIAL")
    assert inv["has_graph_organization_reference"] is True

def test_phase4_cro_false_assurance_prevention():
    """Verify CRO standalone generator cannot emit CERTIFIED when browser UX and forms are unmeasured."""
    intel = build_cro_intelligence(pages=[])
    gen = CroReportGenerator()
    cro_json = gen.render_json_report(
        intel,
        domain="perforacare.com",
        website_url="https://perforacare.com",
        analysis_id="RUN_AF865F8B",
        findings=[{"finding_id": "CRO_01", "title": "Missing trust badges in hero"}],
    )
    # Assurance checks
    assert cro_json["certification_status"] == "NOT_CERTIFIED"
    assert cro_json["assurance_status"] == "EVALUATED_WITH_LIMITATIONS"
    assert cro_json["test_groups"]["mobile_viewport_ux"] == "NOT_TESTED"
    assert cro_json["test_groups"]["interactive_forms"] == "NOT_TESTED"
    assert cro_json["test_groups"]["conversion_analytics"] == "UNAVAILABLE"
    # Canonical findings are preserved (not 0)
    assert len(cro_json["findings"]) == 1
    assert cro_json["findings"][0]["finding_id"] == "CRO_01"

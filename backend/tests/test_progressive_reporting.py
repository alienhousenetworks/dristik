"""
Comprehensive automated tests for Dristik AI Progressive Phase-wise PDF & Evidence Reporting System.
Verifies reporting contracts, SHA-256 sealing, storage atomicity, catalog querying, and API endpoints.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.reporting.contracts import (
    ConfidenceLevel,
    EvidenceTokenReference,
    ExecutionStatus,
    PhaseReportContract,
    ReportFinding,
    SubPhaseReportContract,
)
from app.reporting.engines import (
    PhaseConsolidator,
    ProgressivePDFRenderer,
    ReportRegistry,
    SubPhaseReportBuilder,
)
from app.reporting.storage import ReportStorage


@pytest.fixture
def temp_storage(tmp_path: Path) -> ReportStorage:
    return ReportStorage(base_dir=str(tmp_path / "runs"))


def test_subphase_contract_sealing():
    contract = SubPhaseReportContract(
        run_id="run_test_001",
        phase_id="phase_01_ingestion",
        phase_name="1. Ingestion & Multi-Page Crawl",
        subphase_id="1.1",
        subphase_title="SSRF Security & Host Preflight",
        objective="Inspect domain DNS resolution and redirect safety.",
        agent_id="security.ssrf_gate",
        agent_model="deterministic_kernel",
        execution_mode="deterministic",
        input_summary={"target_url": "https://example.com"},
        processing_steps=["Checked DNS", "Evaluated RFC1918"],
        structured_output={"url": "https://example.com", "safe": True},
        evidence_tokens=[
            EvidenceTokenReference(
                evidence_id="dns_01",
                token_type="dns_record",
                locator="https://example.com",
                excerpt="Resolved IP: 93.184.216.34",
            )
        ],
        findings=[],
        confidence=ConfidenceLevel.VERIFIED,
    )
    assert not contract.content_hash
    contract.seal()
    assert len(contract.content_hash) == 64  # SHA-256 length
    # Mutating a field changes the hash
    hash1 = contract.content_hash
    contract.duration_ms = 100
    assert contract.compute_hash() != hash1


def test_report_storage_atomic_operations(temp_storage: ReportStorage):
    contract = SubPhaseReportContract(
        run_id="run_storage_001",
        phase_id="phase_02_business",
        phase_name="2. Business Understanding",
        subphase_id="2.1",
        subphase_title="Canonical Entity Resolution",
        objective="Determine brand identity.",
        agent_id="business.discovery.v3",
        structured_output={"canonical_name": "Acme Corp"},
        confidence=ConfidenceLevel.VERIFIED,
    )
    json_path = temp_storage.save_subphase_json(contract)
    assert json_path.exists()
    assert json_path.suffix == ".json"

    loaded = temp_storage.load_subphase_json("run_storage_001", "phase_02_business", "2.1")
    assert loaded is not None
    assert loaded.run_id == "run_storage_001"
    assert loaded.structured_output["canonical_name"] == "Acme Corp"
    assert loaded.content_hash == contract.content_hash

    # Test PDF storage
    pdf_bytes = b"%PDF-1.4 simulated pdf stream"
    pdf_path = temp_storage.save_subphase_pdf(
        "run_storage_001", "phase_02_business", "2.1", pdf_bytes, "entity_resolution"
    )
    assert pdf_path.exists()
    assert pdf_path.read_bytes() == pdf_bytes

    retrieved_path = temp_storage.get_subphase_pdf_path("run_storage_001", "phase_02_business", "2.1")
    assert retrieved_path == pdf_path


def test_phase_consolidator():
    sub1 = SubPhaseReportContract(
        run_id="run_cons_001",
        phase_id="phase_01_ingestion",
        phase_name="1. Ingestion & Multi-Page Crawl",
        subphase_id="1.1",
        subphase_title="SSRF Security",
        objective="SSRF check",
        agent_id="security.ssrf_gate",
        status=ExecutionStatus.COMPLETED,
        findings=[],
    ).seal()

    sub2 = SubPhaseReportContract(
        run_id="run_cons_001",
        phase_id="phase_01_ingestion",
        phase_name="1. Ingestion & Multi-Page Crawl",
        subphase_id="1.2",
        subphase_title="Crawler Execution",
        objective="Crawl site",
        agent_id="crawler.service",
        status=ExecutionStatus.COMPLETED,
        findings=[
            ReportFinding(
                finding_id="CRAWL_SLOW",
                severity="low",
                title="Slow TTFB",
                description="Server took 1500ms to respond.",
            )
        ],
    ).seal()

    phase_report = PhaseConsolidator.consolidate_phase(
        run_id="run_cons_001",
        phase_id="phase_01_ingestion",
        subphase_reports=[sub1, sub2],
    )
    assert phase_report.run_id == "run_cons_001"
    assert phase_report.status == ExecutionStatus.COMPLETED
    assert len(phase_report.subphase_ids) == 2
    assert "1.1" in phase_report.subphase_hashes
    assert "1.2" in phase_report.subphase_hashes
    assert len(phase_report.reconciled_findings) == 1
    assert len(phase_report.content_hash) == 64


@pytest.mark.asyncio
async def test_report_registry_and_catalog(temp_storage: ReportStorage):
    registry = ReportRegistry(storage=temp_storage)

    contract = SubPhaseReportContract(
        run_id="run_reg_001",
        phase_id="phase_01_ingestion",
        phase_name="1. Ingestion & Multi-Page Crawl",
        subphase_id="1.1",
        subphase_title="SSRF Security",
        objective="Verify SSRF safety",
        agent_id="security.ssrf_gate",
        status=ExecutionStatus.COMPLETED,
        structured_output={"is_safe": True},
    )

    entry = await registry.register_and_generate_subphase(
        contract, filename_slug="ssrf_security", generate_pdf_now=False
    )
    assert entry["run_id"] == "run_reg_001"
    assert entry["subphase_id"] == "1.1"

    catalog = registry.get_catalog("run_reg_001")
    assert catalog["total_subphase_reports"] == 1
    assert catalog["subphases"][0]["subphase_id"] == "1.1"


def test_pdf_renderer_html_generation():
    contract = SubPhaseReportContract(
        run_id="run_render_001",
        phase_id="phase_02_business",
        phase_name="2. Business Understanding",
        subphase_id="2.1",
        subphase_title="Canonical Entity Resolution",
        objective="Resolve legal brand identity.",
        agent_id="business.discovery.v3",
        structured_output={"canonical_name": "Acme Innovations Ltd."},
        evidence_tokens=[
            EvidenceTokenReference(
                evidence_id="ev_01",
                token_type="dom_selector",
                locator="header h1",
                excerpt="Acme Innovations",
            )
        ],
        findings=[
            ReportFinding(
                finding_id="FIND_001",
                severity="high",
                title="Missing Legal Disclaimer",
                description="Footer lacks required terms.",
            )
        ],
        confidence=ConfidenceLevel.VERIFIED,
    ).seal()

    html_out = ProgressivePDFRenderer.render_subphase_html(contract)
    assert "<!DOCTYPE html>" in html_out
    assert "Acme Innovations Ltd." in html_out
    assert "Missing Legal Disclaimer" in html_out
    assert "ev_01" in html_out
    assert contract.content_hash in html_out


def test_string_and_claim_findings_coerce_into_report_findings():
    """Phase 3 used to pass claim statements as strings and crash SubPhaseReportContract."""

    class _Severity:
        value = "HIGH"

    class _Claim:
        id = "claim_alt"
        claim_id = "claim_alt"
        statement = "Detected 5 image(s) missing descriptive alt attributes."
        severity = _Severity()
        evidence_refs = ["img_1"]
        recommendation = "Add descriptive alt text to each image."
        why_it_matters = "Images stay invisible to search and assistive technology."
        impact = 5  # domain claims store a numeric score, not prose

    contract = SubPhaseReportBuilder.build_generic(
        run_id="run_coerce_001",
        phase_id="phase_03_pillars",
        phase_name="3. Four Strategic Pillars",
        subphase_id="3.1",
        subphase_title="Search Engine Optimization (SEO) Specialist Analysis",
        objective="Evaluate on-page content.",
        agent_id="seo.specialist_workforce",
        agent_model="multi_specialist_pool",
        execution_mode="hybrid",
        duration_ms=1200,
        status=ExecutionStatus.COMPLETED,
        input_summary={"active": True},
        processing_steps=["On-page audit"],
        structured_output={"pillar": "SEO"},
        evidence_tokens=[],
        findings=[
            "5 image(s) are missing alt text.",
            _Claim(),
        ],
        confidence=ConfidenceLevel.VERIFIED,
    )

    assert len(contract.findings) == 2
    assert all(isinstance(item, ReportFinding) for item in contract.findings)
    assert contract.findings[0].description == "5 image(s) are missing alt text."
    assert contract.findings[0].severity == "info"
    assert contract.findings[1].finding_id == "claim_alt"
    assert contract.findings[1].severity == "high"
    assert contract.findings[1].title.startswith("Detected 5 image")
    assert contract.findings[1].evidence_ids == ["img_1"]
    assert contract.findings[1].remediation_hint.startswith("Add descriptive alt")
    assert contract.findings[1].impact.startswith("Images stay invisible")
    assert len(contract.content_hash) == 64
    assert not hasattr(ConfidenceLevel, "LIKELY")
    assert ConfidenceLevel.INFERRED.value == "INFERRED"


def test_progressive_reports_api_endpoints():
    client = TestClient(app)

    # 1. Non-existent run catalog returns 404 or empty
    resp = client.get("/api/v1/analyses/run_non_existent_123/reports/catalog")
    assert resp.status_code in (404, 401, 403, 200)

    # 2. Check JSON endpoint path validation
    resp_json = client.get("/api/v1/analyses/run_test_001/phases/phase_01_ingestion/subphases/1.1/json")
    assert resp_json.status_code in (404, 401, 403)

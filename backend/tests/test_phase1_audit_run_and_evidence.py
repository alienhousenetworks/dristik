import pytest
from datetime import datetime, timezone
from app.domain.models import AuditRun
from app.domain.enums import PublicationStatus, CollectionStatus
from app.domain.evidence.models import Evidence
from app.domain.evidence.store import EvidenceStore

def test_phase1_audit_run_model():
    """Verify AuditRun record has all canonical execution fields."""
    run = AuditRun(
        id="RUN_TEST_001",
        tenant_id="tenant_acme",
        domain="perforacare.com",
        crawl_snapshot_id="snap_987",
        configuration_version="2026.1",
        agent_manifest_version="v2",
        evidence_registry_version="v1",
        status="completed",
        publication_status=PublicationStatus.INTERNAL_REVIEW,
    )
    assert run.id == "RUN_TEST_001"
    assert run.tenant_id == "tenant_acme"
    assert run.domain == "perforacare.com"
    assert run.crawl_snapshot_id == "snap_987"
    assert run.publication_status == PublicationStatus.INTERNAL_REVIEW

def test_phase1_evidence_model_canonical_interface():
    """Verify Evidence model supports canonical field aliases and immutable properties."""
    ev = Evidence(
        id="ev_canon_01",
        audit_run_id="RUN_TEST_001",
        url="https://perforacare.com/products/unwind",
        evidence_type="DOM",
        source="https://perforacare.com/products/unwind",
        capture_method="playwright_crawler",
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_uri="s3://evidence-store/snap_01",
        test_status="observed",
        metadata={"status_code": 200, "ttfb_ms": 36208},
    )
    assert ev.id == "ev_canon_01"
    assert ev.audit_run_id == "RUN_TEST_001"
    assert ev.url == "https://perforacare.com/products/unwind"
    assert ev.evidence_type == "DOM"
    assert ev.source == "https://perforacare.com/products/unwind"
    assert ev.capture_method == "playwright_crawler"
    assert ev.content_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert ev.storage_uri == "s3://evidence-store/snap_01"
    assert ev.test_status in ("observed", "SUCCESS", "success")
    assert ev.metadata["ttfb_ms"] == 36208

def test_phase1_evidence_store_binding_and_hashing():
    """Verify EvidenceStore binds all evidence to the single audit_run_id."""
    store = EvidenceStore(run_id="RUN_AF865F8B")
    item = store.add_evidence(
        source_type="HTTP",
        analyzer="network_tracer",
        url="https://perforacare.com/",
        text="TTFB: 345ms",
        value=345,
    )
    assert item.audit_run_id == "RUN_AF865F8B"
    assert item.id.startswith("ev_")
    assert item.hash is not None and len(item.hash) > 10

def test_phase1_missing_evidence_is_not_zero():
    """Missing evidence remains explicitly NOT_TESTED or UNAVAILABLE, never fabricated zero."""
    ev = Evidence(
        id="ev_missing_01",
        audit_run_id="RUN_TEST_001",
        source_type="external_api",
        collection_status=CollectionStatus.NOT_TESTED,
        analyzer="search_console",
        hash="unavailable_marker",
    )
    assert ev.collection_status == CollectionStatus.NOT_TESTED
    assert ev.test_status == "not_tested"

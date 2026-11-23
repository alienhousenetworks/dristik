"""Tests for Phase 7: Latency Metrics, Retry/DLQ Quarantine & Replay, Connector Health & Concurrent Load."""
from concurrent.futures import ThreadPoolExecutor
import pytest

from app.analytics.conversion_attribution import ConversionAttributionEngine
from app.ops.reliability import (
    DeadLetterQueueManager,
    LatencyMetricsCollector,
    get_connector_health_dashboard,
)


def test_latency_metrics_and_prometheus_output():
    col = LatencyMetricsCollector()
    for ms in (10, 20, 30, 40, 200):
        col.record("/api/v1/ingest/events", ms, 200)
    col.record("/api/v1/ingest/events", 500, 500)
    snap = col.snapshot()
    assert snap["total_requests"] == 6
    assert snap["total_errors_5xx"] == 1
    assert snap["routes"]["/api/v1/ingest/events"]["p95_ms"] >= 200
    prom = col.to_prometheus_text()
    assert "dristik_http_requests_total" in prom


def test_dlq_quarantine_and_rbac_replay(tmp_path):
    db = str(tmp_path / "ops.db")
    job_id = DeadLetterQueueManager.enqueue(
        org_id="org_1", job_type="backlink_sync", payload={"domain": "perforacare.com"}, max_attempts=2, db_path=db
    )

    def _always_fail(_payload):
        raise RuntimeError("Upstream 503")

    r1 = DeadLetterQueueManager.process_job(job_id=job_id, handler=_always_fail, db_path=db)
    assert r1["status"] == "RETRY_SCHEDULED"

    r2 = DeadLetterQueueManager.process_job(job_id=job_id, handler=_always_fail, db_path=db)
    assert r2["status"] == "DEAD_LETTERED"
    dlq_id = r2["dlq_id"]

    with pytest.raises(PermissionError):
        DeadLetterQueueManager.replay_dlq_job(org_id="org_1", dlq_id=dlq_id, actor_role="viewer", db_path=db)

    rep = DeadLetterQueueManager.replay_dlq_job(org_id="org_1", dlq_id=dlq_id, actor_role="developer", db_path=db)
    assert rep["status"] == "REPLAYED"


def test_connector_health_and_concurrent_ingestion_load(tmp_path):
    db = str(tmp_path / "load.db")
    health = get_connector_health_dashboard("org_1", db_path=db)
    assert health["total_connectors"] >= 16

    def _send(i: int):
        return ConversionAttributionEngine.ingest_event(
            org_id="org_1",
            domain="perforacare.com",
            payload={
                "event_id": f"burst_ev_{i}",
                "visitor_id": f"v_{i % 20}",
                "session_id": f"s_{i % 20}",
                "event_name": "page_view",
                "page_url": "/products/truthbrush",
                "device_category": "mobile",
            },
            db_path=db,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_send, range(60)))
    assert all(r["accepted"] for r in results)
    rep = ConversionAttributionEngine.compute_funnel_metrics(org_id="org_1", domain="perforacare.com", db_path=db)
    assert rep.eligible_visitors == 20

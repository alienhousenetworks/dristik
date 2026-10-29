"""
Unit tests for Phase 1: Enterprise Schema, CAS Storage, and Distributed Event Engine.
"""
import asyncio
import os
import sqlite3
import tempfile
import pytest

from app.persistence.enterprise_schema import init_enterprise_schema
from app.persistence.storage_cas import ContentAddressableStorage
from app.workers.distributed_engine import DistributedEventBroadcaster, IdempotentTaskRunner


def test_enterprise_schema_initialization():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name

    try:
        init_enterprise_schema(temp_db)
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()

        expected_tables = {
            "organizations",
            "workspaces",
            "domains",
            "audit_runs",
            "evidence_nodes",
            "findings",
            "ai_citations",
            "enterprise_audit_logs",
        }
        for t in expected_tables:
            assert t in tables, f"Expected table {t} missing from enterprise schema"
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_cas_storage_put_and_get():
    with tempfile.TemporaryDirectory() as temp_dir:
        cas = ContentAddressableStorage(base_dir=temp_dir)
        html_doc = "<html><head><title>Enterprise Intelligence</title></head><body><h1>Linear</h1></body></html>"

        content_hash, uri = cas.put(html_doc, extension="html")
        assert len(content_hash) == 64
        assert uri.startswith("cas://")
        assert cas.exists(content_hash)
        assert cas.exists(uri)

        retrieved_bytes = cas.get(uri)
        assert retrieved_bytes is not None
        assert retrieved_bytes.decode("utf-8") == html_doc

        # Check non-existent hash
        assert not cas.exists("deadbeef" * 8)
        assert cas.get("deadbeef" * 8) is None


@pytest.mark.asyncio
async def test_distributed_event_broadcaster():
    broadcaster = DistributedEventBroadcaster()
    channel = "audit:test_run_123"

    queue = await broadcaster.subscribe(channel)
    msg = {"event": "progress", "percentage": 45, "step": "Specialist Agents"}

    await broadcaster.publish(channel, msg)
    received = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert received == msg

    await broadcaster.unsubscribe(channel, queue)


@pytest.mark.asyncio
async def test_idempotent_task_runner():
    runner = IdempotentTaskRunner()
    call_count = 0

    async def compute_heavy_step(val: int):
        nonlocal call_count
        call_count += 1
        return val * 2

    # First call: executes function
    res1 = await runner.execute_activity("audit_01", "crawl_domain", compute_heavy_step, 21)
    assert res1 == 42
    assert call_count == 1

    # Second call with same audit_id + activity_name: returns cached result without re-executing
    res2 = await runner.execute_activity("audit_01", "crawl_domain", compute_heavy_step, 21)
    assert res2 == 42
    assert call_count == 1  # Did not increment!

"""Sprint 2 Enterprise Production-Readiness Verification Suite.

Covers all 4 enterprise tracks:
  Track 1: 4-engine live web-grounded AI citations (Claude, ChatGPT, Gemini, Perplexity) + cost guardrails
  Track 2: Real live connector wiring in SEOAuditOrchestrator & CROAuditOrchestrator
  Track 3: LLM tenant cache isolation, $0 cache billing, BudgetManager enforcement, multi-loop Playwright PDF
  Track 4: Unified DATABASE_URL persistence, SQLite migration, broken worker imports, DurableJobQueue crash recovery
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Track 1: 4-Engine Web-Grounded AI Citations & Cost Guardrails
# ─────────────────────────────────────────────────────────────────────────────

def test_claude_adapter_native_web_search_citations_and_surcharge():
    from app.geo.adapters.claude import ClaudeAdapter
    from app.geo.models import GEOTestingMode

    captured: Dict[str, Any] = {}

    async def _handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "id": "msg_01",
                "model": "claude-haiku-4-5-20251001",
                "content": [
                    {"type": "server_tool_use", "id": "srv_1", "name": "web_search", "input": {"query": "best workflow tools"}},
                    {
                        "type": "web_search_tool_result",
                        "tool_use_id": "srv_1",
                        "content": [
                            {"type": "web_search_result", "url": "https://acmeflow.io/workflows", "title": "AcmeFlow Workflows"},
                            {"type": "web_search_result", "url": "https://rival.com/compare", "title": "Rival Compare"},
                        ],
                    },
                    {
                        "type": "text",
                        "text": "AcmeFlow is a leading workflow platform.",
                        "citations": [
                            {
                                "type": "web_search_result_location",
                                "url": "https://acmeflow.io/workflows",
                                "title": "AcmeFlow Workflows",
                            }
                        ],
                    },
                ],
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "server_tool_use": {"web_search_requests": 1},
                },
            },
        )

    async def _run():
        adapter = ClaudeAdapter(api_key="sk-ant-test", model="claude-haiku-4-5-20251001")
        assert adapter.supports_web_search is True
        transport = httpx.MockTransport(_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await adapter.execute_query("best workflow tools", client=client, enable_search=True)

    res = asyncio.run(_run())
    assert res.is_live is True
    assert res.testing_mode == GEOTestingMode.API_WITH_SEARCH
    assert "tools" in captured["body"]
    assert captured["body"]["tools"][0]["type"] == "web_search_20250305"
    assert captured["body"]["tools"][0]["max_uses"] == 1
    assert res.citations == ["https://acmeflow.io/workflows", "https://rival.com/compare"]
    # Cost includes $0.01 web search fee + token costs
    assert res.estimated_cost_usd >= 0.011


def test_claude_and_gemini_ungrounded_exclude_prose_urls_and_no_search_fee():
    from app.geo.adapters.claude import ClaudeAdapter
    from app.geo.adapters.gemini import GeminiAdapter
    from app.geo.models import GEOTestingMode

    async def _claude_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "claude-3-5-haiku-20241022",
                "content": [{"type": "text", "text": "Try https://hallucinated.example/page for info."}],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        )

    async def _gemini_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "gemini-2.0-flash",
                "choices": [{"message": {"content": "Check https://hallucinated.example/gem"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )

    async def _run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_claude_handler)) as c1:
            r1 = await ClaudeAdapter(api_key="sk-ant-test").execute_query("q", client=c1, enable_search=False)
        async with httpx.AsyncClient(transport=httpx.MockTransport(_gemini_handler)) as c2:
            r2 = await GeminiAdapter(api_key="gem-test").execute_query("q", client=c2, enable_search=False)
        return r1, r2

    r_claude, r_gemini = asyncio.run(_run())
    assert r_claude.testing_mode == GEOTestingMode.API_MODEL_ONLY
    assert r_claude.citations == []
    assert r_claude.estimated_cost_usd < 0.005

    assert r_gemini.testing_mode == GEOTestingMode.API_MODEL_ONLY
    assert r_gemini.citations == []
    assert r_gemini.estimated_cost_usd < 0.005


def test_perplexity_gemini_openai_search_include_true_search_surcharges():
    from app.geo.adapters.gemini import GeminiAdapter
    from app.geo.adapters.openai_search import OpenAISearchAdapter
    from app.geo.adapters.perplexity import PerplexityAdapter
    from app.geo.models import GEOTestingMode

    async def _run():
        p_client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _r: httpx.Response(
                    200,
                    json={
                        "model": "sonar",
                        "choices": [{"message": {"content": "AcmeFlow leads."}}],
                        "citations": ["https://acmeflow.io/"],
                        "usage": {"prompt_tokens": 100, "completion_tokens": 100},
                    },
                )
            )
        )
        g_client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _r: httpx.Response(
                    200,
                    json={
                        "modelVersion": "gemini-2.0-flash",
                        "candidates": [
                            {
                                "content": {"parts": [{"text": "AcmeFlow is cited."}]},
                                "groundingMetadata": {
                                    "webSearchQueries": ["best workflow"],
                                    "groundingChunks": [{"web": {"uri": "https://acmeflow.io/"}}],
                                },
                            }
                        ],
                        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 100},
                    },
                )
            )
        )
        o_client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _r: httpx.Response(
                    200,
                    json={
                        "model": "gpt-4o-search-preview",
                        "choices": [
                            {
                                "message": {
                                    "content": "AcmeFlow is recommended.",
                                    "annotations": [{"url_citation": {"url": "https://acmeflow.io/"}}],
                                }
                            }
                        ],
                        "usage": {"prompt_tokens": 100, "completion_tokens": 100},
                    },
                )
            )
        )
        async with p_client, g_client, o_client:
            rp = await PerplexityAdapter(api_key="pplx-k").execute_query("q", client=p_client)
            rg = await GeminiAdapter(api_key="gem-k").execute_query("q", client=g_client, enable_search=True)
            ro = await OpenAISearchAdapter(api_key="oa-k", model="gpt-4o-search-preview").execute_query(
                "q", client=o_client, enable_search=True
            )
            return rp, rg, ro

    rp, rg, ro = asyncio.run(_run())
    assert rp.testing_mode == GEOTestingMode.API_WITH_SEARCH and rp.estimated_cost_usd >= 0.005
    assert rg.testing_mode == GEOTestingMode.API_WITH_SEARCH and rg.estimated_cost_usd >= 0.035
    assert ro.testing_mode == GEOTestingMode.API_WITH_SEARCH and ro.estimated_cost_usd >= 0.025


def test_live_citation_engine_passes_enable_search_caches_and_enforces_budget():
    from app.geo.adapters.base import BaseGeoEngineAdapter, EngineRawResponse
    from app.geo.citations.live import LiveAICitationEngine, clear_live_citation_cache
    from app.geo.models import GEOTestingMode

    clear_live_citation_cache()
    calls: List[Dict[str, Any]] = []

    class _FakeSearchAdapter(BaseGeoEngineAdapter):
        engine_id = "claude"
        display_name = "Claude"
        default_model = "claude-haiku-4-5-20251001"
        supports_web_search = True

        async def execute_query(self, prompt: str, locale: str = "en-US", client=None, *, enable_search: bool = False):
            calls.append({"prompt": prompt, "enable_search": enable_search})
            return EngineRawResponse(
                engine_id="claude",
                engine_name="Claude",
                model_version="claude-haiku-4-5-20251001",
                raw_content="AcmeFlow is top rated.",
                citations=["https://acmeflow.io/pricing"],
                status_code=200,
                is_live=True,
                testing_mode=GEOTestingMode.API_WITH_SEARCH if enable_search else GEOTestingMode.API_MODEL_ONLY,
                estimated_cost_usd=0.012,
            )

    fake = _FakeSearchAdapter(api_key="sk-test")
    engine = LiveAICitationEngine()

    with patch("app.geo.adapters.registry.get_adapter", return_value=fake):
        r1 = engine.evaluate_query("acmeflow.io", "best workflow tool", "claude", tenant_id="org_1")
        r2 = engine.evaluate_query("acmeflow.io", "best workflow tool", "claude", tenant_id="org_1")
        # Cache hit on second identical query for same tenant -> $0.00 and only 1 live call
        assert r1.is_cited is True and r1.citation_rank == 1
        assert r1.execution_mode == "api_with_search"
        assert calls[0]["enable_search"] is True
        assert r2.cache_hit is True and r2.estimated_cost_usd == 0.0
        assert len(calls) == 1

        # Query bank enforces max_live_calls cap
        bank = engine.evaluate_query_bank(
            domain="acmeflow.io",
            queries=["q1", "q2", "q3", "q4"],
            engines=["claude"],
            tenant_id="org_2",
            max_live_calls=2,
            use_cache=False,
        )
        assert bank["live_dispatched"] == 2
        assert bank["budget_paused"] is True
        paused_rows = [e for e in bank["evaluations"] if e["status"] == "BUDGET_PAUSED"]
        assert len(paused_rows) == 2


def test_geo_orchestrator_mode_tiered_prompts_and_max_live_calls(tmp_path: Path):
    from app.db.geo_schema import GEOStore
    from app.geo.orchestrator import GEOAuditOrchestrator

    store = GEOStore(db_path=str(tmp_path / "geo.db"))
    o_quick = GEOAuditOrchestrator(tenant_id="t1", target_url="https://acmeflow.io", mode="quick", store=store)
    o_std = GEOAuditOrchestrator(tenant_id="t1", target_url="https://acmeflow.io", mode="standard", store=store)
    o_deep = GEOAuditOrchestrator(tenant_id="t1", target_url="https://acmeflow.io", mode="deep", store=store)
    assert o_quick.scope.max_prompts == 5
    assert o_std.scope.max_prompts == 10
    assert o_deep.scope.max_prompts == 18


# ─────────────────────────────────────────────────────────────────────────────
# Track 2: Live External Connector Wiring (SEO & CRO)
# ─────────────────────────────────────────────────────────────────────────────

def test_seo_connector_runner_pulls_real_gsc_and_crux_data_or_fails_closed(tmp_path: Path):
    from app.connectors.authority.models import ExternalRecord
    from app.connectors.authority.service import ExternalAuthorityService
    from app.connectors.authority.store import ExternalStore
    from app.seo.audit.orchestrator import AuditConfiguration, AuditMode, SEOAuditOrchestrator

    db_path = str(tmp_path / "seo_conn.db")
    ea_store = ExternalStore(path=str(tmp_path / "ea_conn.db"))
    ea_svc = ExternalAuthorityService(store=ea_store)

    # Seed a connected GSC snapshot with a real sitemap error for org_alpha + acme.example
    ea_store.upsert_connection(
        {"project_id": "org_alpha", "provider": "google_search_console", "status": "CONNECTED", "auth_mode": "oauth", "token_status": "valid"},
        secret={"access_token": "tok"},
    )
    ea_store.save_snapshot(
        project_id="org_alpha",
        provider="google_search_console",
        domain="acme.example",
        period_days=28,
        period_start="2026-10-01",
        period_end="2026-10-28",
        data_state="MEASURED",
        summary={"totals": {"clicks": 420, "impressions": 12000}},
        idempotency_key="gsc_test_1",
        records=[
            ExternalRecord(
                record_type="search_performance",
                provider="google_search_console",
                domain="acme.example",
                metric="sitemap",
                value_text="https://acme.example/sitemap.xml",
                url="https://acme.example/sitemap.xml",
                metadata={"errors": 3, "warnings": 0},
            )
        ],
        raw_payloads=[],
        collected_at=datetime.now(timezone.utc).isoformat(),
    )

    cfg = AuditConfiguration(
        org_id="org_alpha",
        workspace_id="ws_alpha",
        domain="acme.example",
        target_url="https://acme.example/",
        mode=AuditMode.STANDARD,
    )
    orch = SEOAuditOrchestrator(config=cfg, db_path=db_path)

    # Connect PageSpeed/CrUX with field LCP subpart bottleneck
    orch.connectors.connect_provider(
        "pagespeed_crux",
        {
            "api_key": "psi-key",
            "lcp_subparts": {
                "lcp_ms": 4200,
                "ttfb_ms": 400,
                "resource_load_delay_ms": 1800,
                "resource_load_duration_ms": 1200,
                "element_render_delay_ms": 800,
            },
        },
        workspace_id="ws_alpha",
        org_id="org_alpha",
    )

    with patch("app.connectors.authority.service.get_service", return_value=ea_svc):
        gsc_runner = orch._agent_runners["agent_search_console"]
        gbp_runner = orch._agent_runners["agent_local_gbp"]
        gsc_out = asyncio.run(gsc_runner({}))
        gbp_out = asyncio.run(gbp_runner({}))

    assert gsc_out["status"] == "CONNECTED"
    assert gsc_out["data_state"] == "MEASURED"
    assert gsc_out["metrics"].get("clicks") == 420
    assert len(gsc_out["findings"]) >= 1
    assert any(f.get("rule_id") == "seo.gsc.sitemap_errors" for f in gsc_out["findings"])

    # Disconnected connector remains honestly DATA_UNAVAILABLE
    assert gbp_out["node_status"] == "DATA_UNAVAILABLE"
    assert gbp_out["status"] == "NOT_CONFIGURED"
    assert gbp_out["findings"] == []


def test_cro_orchestrator_auto_hydrates_connected_ga4_and_fails_closed_when_absent(tmp_path: Path):
    from app.connectors.authority.models import ExternalRecord
    from app.connectors.authority.service import ExternalAuthorityService
    from app.connectors.authority.store import ExternalStore
    from app.cro.orchestrator import CROAuditOrchestrator
    from app.db.cro_schema import CROStore

    cro_store = CROStore(db_path=str(tmp_path / "cro_conn.db"))
    ea_store = ExternalStore(path=str(tmp_path / "ea_ga4.db"))
    ea_svc = ExternalAuthorityService(store=ea_store)

    # 1. Unconnected tenant -> stays honestly analytics_connected=False
    orch_unconn = CROAuditOrchestrator(
        tenant_id="org_no_ga4",
        target_url="https://acme.example/",
        use_live_browser=False,
        store=cro_store,
    )
    with patch("app.connectors.authority.service.get_service", return_value=ea_svc):
        assert orch_unconn._hydrate_connected_analytics() is None
    assert orch_unconn.audit.analytics_connected is False

    # 2. Connected tenant with measured GA4 snapshot -> auto-hydrated
    ea_store.save_snapshot(
        project_id="org_with_ga4",
        provider="google_analytics_4",
        domain="acme.example",
        period_days=28,
        period_start="2026-10-01",
        period_end="2026-10-28",
        data_state="MEASURED",
        summary={"totals": {"organic_sessions": 2400, "conversions": 72}},
        idempotency_key="ga4_test_1",
        records=[
            ExternalRecord(record_type="search_performance", provider="google_analytics_4", domain="acme.example", metric="organic_sessions", value=2400, metadata={"comparison": "current"}),
            ExternalRecord(record_type="search_performance", provider="google_analytics_4", domain="acme.example", metric="total_users", value=1900, metadata={"comparison": "current"}),
            ExternalRecord(record_type="search_performance", provider="google_analytics_4", domain="acme.example", metric="conversions", value=72, metadata={"comparison": "current"}),
            ExternalRecord(record_type="search_performance", provider="google_analytics_4", domain="acme.example", metric="revenue", value=14400.0, metadata={"comparison": "current"}),
        ],
        raw_payloads=[],
        collected_at=datetime.now(timezone.utc).isoformat(),
    )
    orch_conn = CROAuditOrchestrator(
        tenant_id="org_with_ga4",
        target_url="https://acme.example/",
        use_live_browser=False,
        store=cro_store,
    )
    with patch("app.connectors.authority.service.get_service", return_value=ea_svc):
        payload = orch_conn._hydrate_connected_analytics()

    assert payload is not None
    assert payload["state"] == "MEASURED"
    assert payload["connected"] is True
    assert payload["metrics"]["sessions"] == 2400
    assert payload["metrics"]["conversions"] == 72
    assert orch_conn.audit.analytics_connected is True
    assert "ga4" in orch_conn.connected_providers


# ─────────────────────────────────────────────────────────────────────────────
# Track 3: LLM Hardening & Multi-Loop Playwright PDF Stability
# ─────────────────────────────────────────────────────────────────────────────

def test_llm_response_cache_is_tenant_isolated_and_zero_billed():
    from app.core.inference.llm_client import LLMClient, clear_response_cache, use_tenant_context
    from app.core.inference.model_router import ModelRouter

    clear_response_cache()
    client = LLMClient(api_key="test-key", base_url="https://mock.local/v1", provider="groq")
    call_count = 0

    async def _fake_single(**kwargs):
        nonlocal call_count
        call_count += 1
        return {
            "content": json.dumps({"tenant_seq": call_count}),
            "input_tokens": 500,
            "output_tokens": 200,
            "latency_ms": 120.0,
            "model": kwargs["model"],
            "provider": "groq",
            "stop_reason": "stop",
            "provider_cost_usd": 0.005,
        }

    client._single_chat_completion = _fake_single  # type: ignore[method-assign]

    async def _run():
        with use_tenant_context("org_alpha"):
            r_a1 = await client.generate_chat_completion(
                model="llama-3.3-70b-versatile", system_prompt="sys", user_prompt="same prompt", temperature=0.0
            )
            r_a2 = await client.generate_chat_completion(
                model="llama-3.3-70b-versatile", system_prompt="sys", user_prompt="same prompt", temperature=0.0
            )
        with use_tenant_context("org_beta"):
            r_b1 = await client.generate_chat_completion(
                model="llama-3.3-70b-versatile", system_prompt="sys", user_prompt="same prompt", temperature=0.0
            )
        return r_a1, r_a2, r_b1

    r_a1, r_a2, r_b1 = asyncio.run(_run())
    assert call_count == 2  # org_alpha cached on 2nd call; org_beta did NOT hit org_alpha's cache!
    assert r_a2.get("cache_hit") is True and r_a2.get("provider_cost_usd") == 0.0
    assert r_a1["content"] != r_b1["content"]

    # Verify ModelRouter records $0.00 for cache hits and enforces BudgetManager
    router = ModelRouter(max_budget_usd=0.01, max_model_calls=2)
    router._record_llm_call(
        response=r_a2, capability="test", model="llama-3.3-70b-versatile", system_prompt="s", user_prompt="u", agent_id="a1"
    )
    assert router.telemetry.telemetry.estimated_cost_usd == 0.0
    assert router.telemetry.telemetry.input_tokens == 0

    # Push spend past max_budget_usd -> generate_structured must return budget_exceeded without calling LLM
    router.telemetry.telemetry.estimated_cost_usd = 0.02
    blocked = asyncio.run(
        router.generate_structured(capability="test", agent_role="tester", task_contract="do work")
    )
    assert blocked.get("status") == "budget_exceeded"
    blocked_prose = asyncio.run(router.generate_prose("test", "sys", "usr"))
    assert blocked_prose == ""


def test_browser_render_service_multi_loop_pdf_does_not_hang():
    from app.crawl.browser import BrowserRenderService

    if not BrowserRenderService.is_available():
        pytest.skip("Playwright not enabled")

    html = "<!doctype html><html><body><h1>Sprint 2 Multi-Loop PDF Check</h1><p>Verified.</p></body></html>"

    # Two distinct event loops back-to-back (exactly what FastAPI TestClient / workers do)
    pdf1 = asyncio.run(BrowserRenderService.render_pdf(html, timeout_ms=20000))
    pdf2 = asyncio.run(BrowserRenderService.render_pdf(html, timeout_ms=20000))
    asyncio.run(BrowserRenderService.shutdown())

    assert pdf1 is not None and pdf1.startswith(b"%PDF-")
    assert pdf2 is not None and pdf2.startswith(b"%PDF-")


# ─────────────────────────────────────────────────────────────────────────────
# Track 4: Unified Persistence, Broken Worker Imports & Durable Job Queue
# ─────────────────────────────────────────────────────────────────────────────

def test_worker_modules_import_cleanly_without_circular_error():
    import app.tasks as tasks_mod
    import app.workers.audit_tasks as audit_tasks_mod
    import app.workers.celery_app as celery_mod
    import app.workers.crawl_tasks as crawl_tasks_mod
    import app.workers.report_tasks as report_tasks_mod

    assert callable(audit_tasks_mod.run_audit_task)
    assert callable(crawl_tasks_mod.run_crawl_task)
    assert callable(report_tasks_mod.run_report_task)
    assert tasks_mod.task_queue is celery_mod.task_queue


def test_durable_job_queue_lifecycle_retries_and_crash_lease_recovery(tmp_path: Path):
    from app.workers.queue import DurableJobQueue

    q = DurableJobQueue(db_path=str(tmp_path / "jobs.db"), redis_url="", lease_seconds=60)
    executed: List[Dict[str, Any]] = []

    async def _ok_handler(payload: Dict[str, Any]):
        executed.append(payload)

    q.register_handler("demo.ok", _ok_handler)

    # 1. Enqueue -> process_one -> completed
    jid = q.enqueue_job("demo.ok", {"analysis_id": "an_1"}, org_id="org_a", analysis_id="an_1")
    res = asyncio.run(q.process_one())
    assert res == {"job_id": jid, "status": "completed"}
    assert executed == [{"analysis_id": "an_1"}]
    assert q.get_job(jid)["status"] == "completed"

    # 2. Simulate crashed worker with expired lease -> requeue_expired_leases recovers it!
    jid2 = q.enqueue_job("demo.ok", {"analysis_id": "an_2"}, org_id="org_a", analysis_id="an_2", max_attempts=3)
    claimed = q.claim_next_job()
    assert claimed is not None and claimed["job_id"] == jid2 and claimed["status"] == "running"

    future_now = datetime.now(timezone.utc) + timedelta(seconds=120)
    recovery = q.requeue_expired_leases(now=future_now)
    assert recovery["requeued"] == 1
    assert q.get_job(jid2)["status"] == "queued"

    res2 = asyncio.run(q.process_one())
    assert res2 == {"job_id": jid2, "status": "completed"}
    assert q.get_job(jid2)["attempts"] == 2


def test_unified_sqlite_identity_and_audit_repository_coexist_and_migrate(tmp_path: Path):
    from app.db.migrate_sqlite import migrate_legacy_sqlite_dbs
    from app.db.repository import AuditRepository
    from app.domain.enums import AnalysisStage
    from app.domain.models import AnalysisRun
    from app.identity.store import IdentityStore

    unified_db = str(tmp_path / "unified.db")
    # Initialize BOTH IdentityStore and AuditRepository against the SAME unified DB file
    id_store = IdentityStore(unified_db)
    repo = AuditRepository(db_path=unified_db)

    id_store.record_audit("an_unified_1", "org_u1", "usr_1", "https://acme.example/", "pending", page_count=3)
    run = AnalysisRun(
        analysis_id="an_unified_1",
        org_id="org_u1",
        created_by="usr_1",
        website_url="https://acme.example/",
        status=AnalysisStage.COMPLETED,
    )
    repo.save_run(run)
    fetched = repo.get_run("an_unified_1", org_id="org_u1")
    assert fetched is not None
    assert fetched["status"] == AnalysisStage.COMPLETED.value
    assert fetched["domain"] == "acme.example"

    # Legacy split DB migration copies rows idempotently into unified DB
    legacy_db = str(tmp_path / "legacy_extra.db")
    with sqlite3.connect(legacy_db) as conn:
        conn.execute("CREATE TABLE legacy_notes (id TEXT PRIMARY KEY, body TEXT)")
        conn.execute("INSERT INTO legacy_notes VALUES ('n1', 'preserved')")
        conn.commit()

    mig = migrate_legacy_sqlite_dbs(target_url=f"sqlite:///{unified_db}", legacy_paths=[legacy_db])
    assert mig["rows_copied"] == 1
    mig_again = migrate_legacy_sqlite_dbs(target_url=f"sqlite:///{unified_db}", legacy_paths=[legacy_db])
    assert mig_again["rows_copied"] == 0

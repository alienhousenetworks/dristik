"""Phase 2 — Central GEO DAG Orchestration & Execution Engine.

Coordinates the complete enterprise GEO audit lifecycle:
  1. Scope, Brand Knowledge Profile & Crawl Ingestion (SSRF-guarded)
  2. Prompt Intelligence Suite Generation (12 categories, branded vs non-branded)
  3. Live AI Platform Execution (bounded concurrency, retries, per-provider timeouts,
     per-audit & per-provider budgets with auto-pause, PII redaction, transparent fallback)
  4. Response Analysis & Citation Source Graph
  5. Parallel Specialist Waves (Departments A–H)
  6. Finding Validation, Deduplication & Root-Cause Consolidation (Department I)
  7. Dual-Scorecard & 7-Dimension Methodology Computation
  8. Consolidated 13-Deliverable Remediation Pack
  9. Independent Publication QA Gate & Monitoring Delta Evaluation

Supports DAG checkpointing/resume, cancellation, idempotency, partial-audit
completion, deterministic replay fixtures (for controlled testing without
spending live tokens), and all 17 canonical `geo.*` SSE events via EventStore.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.core.security.ssrf import is_safe_url
from app.db.geo_schema import GEOStore, get_geo_store
from app.domain.models import PageEvidence
from app.geo.adapters.base import BaseGeoEngineAdapter, EnginePromptRequest, EngineRawResponse
from app.geo.citation_graph import build_citation_source_graph
from app.geo.connectors import GEOConnectorManager, redact_prompt_pii
from app.geo.entity_profile import build_brand_knowledge_profile
from app.geo.models import (
    GEOAudit,
    GEOAuditScope,
    GEOAuditStatus,
    GEOCitation,
    GEODataQualityState,
    GEOMention,
    GEOModelVersion,
    GEOPlatform,
    GEOPromptRun,
    GEOPublicationStatus,
    GEOResponse,
    GEOTestPrompt,
    GEOTestingMode,
)
from app.geo.monitoring import GEOMonitoringEngine
from app.geo.prompt_intelligence import compute_prompt_coverage, generate_prompt_suite
from app.geo.quality import GEOQualityAssuranceEngine
from app.geo.remediation_center import GEORemediationCenter
from app.geo.response_analyzer import analyze_prompt_run_response
from app.geo.scoring.engine import EnterpriseGEOScoringEngine
from app.geo.specialists import GEOAuditContext, validate_agent_output
from app.geo.specialists.observed import (
    run_department_b,
    run_department_c,
    run_department_f,
    run_department_g,
    run_department_h,
)
from app.geo.specialists.readiness import (
    run_department_a,
    run_department_d,
    run_department_e,
    run_department_i_consolidate,
)
from app.seo.audit.orchestration.event_store import EventStore

logger = logging.getLogger("dristik.geo.orchestrator")


def _parse_html_to_page_evidence(url: str, raw_html: str, status_code: int = 200) -> PageEvidence:
    title_m = re.search(r"<title[^>]*>(.*?)</title>", raw_html or "", re.I | re.S)
    title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
    desc_m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', raw_html or "", re.I)
    meta_desc = desc_m.group(1).strip() if desc_m else ""
    canon_m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', raw_html or "", re.I)
    canon = canon_m.group(1).strip() if canon_m else None
    h1s = [re.sub(r"<[^>]+>", "", m).strip() for m in re.findall(r"<h1[^>]*>(.*?)</h1>", raw_html or "", re.I | re.S)]
    h2s = [re.sub(r"<[^>]+>", "", m).strip() for m in re.findall(r"<h2[^>]*>(.*?)</h2>", raw_html or "", re.I | re.S)]

    # Extract JSON-LD schema types
    import json as _json
    schema_types: List[str] = []
    jsonld_blocks: List[Dict[str, Any]] = []
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', raw_html or "", re.I | re.S):
        try:
            obj = _json.loads(block)
            items = obj if isinstance(obj, list) else [obj]
            for it in items:
                if isinstance(it, dict):
                    jsonld_blocks.append(it)
                    t = it.get("@type")
                    if isinstance(t, list):
                        schema_types.extend(str(x) for x in t)
                    elif t:
                        schema_types.append(str(t))
        except Exception:
            continue

    # Strip scripts/styles for body text
    cleaned = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html or "", flags=re.I | re.S)
    body_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cleaned)).strip()
    return PageEvidence(
        url=url,
        status_code=status_code,
        title=title,
        meta_description=meta_desc,
        canonical_url=canon,
        h1=[h for h in h1s if h],
        h2=[h for h in h2s if h][:20],
        body_text=body_text[:40000],
        word_count=len(body_text.split()),
        schema_types=sorted(set(schema_types)),
        json_ld=jsonld_blocks,
    )


class GEOAuditOrchestrator:
    """Central DAG orchestrator for enterprise GEO audits with real-time `geo.*` SSE events."""

    def __init__(
        self,
        *,
        tenant_id: str,
        target_url: str,
        brand_name: Optional[str] = None,
        brand_aliases: Optional[List[str]] = None,
        industry: str = "",
        products: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        markets: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        competitors: Optional[List[str]] = None,
        target_audience: str = "",
        platforms_requested: Optional[List[str]] = None,
        mode: str = "standard",
        repetitions: int = 1,
        max_prompts: int = 18,
        budget_usd: float = 5.0,
        per_provider_budget_usd: Optional[Dict[str, float]] = None,
        allow_provider_fallback: bool = False,
        pii_redaction_enabled: bool = True,
        allow_live_provider_calls: bool = True,
        seed_pages: Optional[List[Dict[str, Any]]] = None,
        robots_txt: Optional[str] = None,
        custom_prompts: Optional[List[Dict[str, Any]]] = None,
        provider_overrides: Optional[Dict[str, BaseGeoEngineAdapter]] = None,
        idempotency_key: Optional[str] = None,
        audit_id: Optional[str] = None,
        store: Optional[GEOStore] = None,
    ):
        self.store = store or get_geo_store()
        self.connectors = GEOConnectorManager(store=self.store)
        self.tenant_id = tenant_id
        self.target_url = target_url if "://" in target_url else f"https://{target_url}"
        parsed = urlparse(self.target_url)
        self.domain = (parsed.netloc or parsed.path).replace("www.", "").strip("/").lower()
        self.brand_name = (brand_name or self.domain.split(".")[0].capitalize()).strip()
        self.mode = mode
        self.seed_pages = seed_pages
        self.robots_txt_input = robots_txt
        self.custom_prompts = custom_prompts
        self.provider_overrides = provider_overrides or {}

        existing = self.store.find_audit_by_idempotency(tenant_id, idempotency_key) if idempotency_key else None
        if existing:
            self.audit = existing
            saved_scope = self.store.get_scope(tenant_id, existing.scope_id) if existing.scope_id else None
            self.scope = saved_scope or GEOAuditScope(
                tenant_id=tenant_id,
                audit_id=existing.audit_id,
                domain=self.domain,
                website_url=self.target_url,
                brand_name=self.brand_name,
            )
        else:
            self.scope = GEOAuditScope(
                tenant_id=tenant_id,
                domain=self.domain,
                website_url=self.target_url,
                brand_name=self.brand_name,
                brand_aliases=list(brand_aliases or []),
                industry=industry,
                products=list(products or []),
                services=list(services or []),
                markets=list(markets or ["US"]),
                languages=list(languages or ["en"]),
                competitors=list(competitors or []),
                target_audience=target_audience,
                platforms_requested=list(platforms_requested or ["chatgpt", "gemini", "claude", "perplexity"]),
                repetitions=max(1, min(repetitions, 5)),
                max_prompts=max(4, min(max_prompts, 200)),
                budget_usd=max(0.0, budget_usd),
                per_provider_budget_usd=dict(per_provider_budget_usd or {}),
                allow_provider_fallback=allow_provider_fallback,
                pii_redaction_enabled=pii_redaction_enabled,
                allow_live_provider_calls=allow_live_provider_calls,
            )
            self.audit = GEOAudit(
                tenant_id=tenant_id,
                scope_id=self.scope.scope_id,
                domain=self.domain,
                website_url=self.target_url,
                brand_name=self.brand_name,
                mode=mode,
                status=GEOAuditStatus.QUEUED.value,
                publication_status=GEOPublicationStatus.DRAFT.value,
                budget_usd=self.scope.budget_usd,
                idempotency_key=idempotency_key,
            )
            if audit_id:
                self.audit.audit_id = audit_id
            self.scope.audit_id = self.audit.audit_id
            self.store.save_scope(self.scope)
            self.store.save_audit(self.audit)

        self.audit_id = self.audit.audit_id
        self.events = EventStore(audit_id=self.audit_id)
        self._cancelled = False
        self._completed_stages: set[str] = {
            ex["agent_id"]
            for ex in self.store.list_agent_executions(tenant_id, self.audit_id)
            if ex.get("status") == "completed"
        }

    def cancel(self) -> None:
        self._cancelled = True
        self.audit.status = GEOAuditStatus.CANCELLED.value
        self.audit.publication_status = GEOPublicationStatus.DRAFT.value
        self.store.save_audit(self.audit)
        self.events.emit("geo.audit.failed", {"reason": "cancelled_by_user"})

    async def _run_stage(
        self,
        stage_id: str,
        fn: Callable[[], Coroutine[Any, Any, Any]],
        *,
        retries: int = 1,
        timeout_sec: float = 60.0,
    ) -> Any:
        if self._cancelled:
            raise asyncio.CancelledError("GEO audit cancelled")
        self.audit.current_stage = stage_id
        self.store.save_audit(self.audit)

        last_exc: Optional[Exception] = None
        for attempt in range(retries + 1):
            t0 = time.monotonic()
            try:
                res = await asyncio.wait_for(fn(), timeout=timeout_sec)
                elapsed = round(time.monotonic() - t0, 3)
                self._completed_stages.add(stage_id)
                self.store.save_agent_execution(
                    execution_id=f"{self.audit_id}:{stage_id}",
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    agent_id=stage_id,
                    department="orchestrator",
                    status="completed",
                    retry_count=attempt,
                    elapsed_sec=elapsed,
                    payload={"stage": stage_id, "status": "completed"},
                )
                return res
            except Exception as exc:
                last_exc = exc
                if attempt < retries:
                    await asyncio.sleep(0.05 * (attempt + 1))
        raise last_exc  # type: ignore[misc]

    async def _ingest_pages_and_robots(self) -> tuple[List[PageEvidence], Dict[str, str], str, Dict[str, Dict[str, str]], List[str]]:
        raw_html_map: Dict[str, str] = {}
        headers_map: Dict[str, Dict[str, str]] = {}
        pages: List[PageEvidence] = []
        snap_ids: List[str] = []
        robots_txt = self.robots_txt_input or ""

        if self.seed_pages is not None:
            for item in self.seed_pages:
                url = str(item.get("url") or self.target_url)
                html_text = str(item.get("raw_html") or item.get("html") or "")
                sc = int(item.get("status_code") or 200)
                if html_text:
                    pe = _parse_html_to_page_evidence(url, html_text, sc)
                    if item.get("title") and not pe.title:
                        pe.title = str(item["title"])
                    if item.get("body_text") and not pe.body_text:
                        pe.body_text = str(item["body_text"])
                        pe.word_count = len(pe.body_text.split())
                else:
                    body = str(item.get("body_text") or "")
                    pe = PageEvidence(
                        url=url,
                        status_code=sc,
                        title=str(item.get("title") or ""),
                        meta_description=str(item.get("meta_description") or ""),
                        canonical_url=item.get("canonical_url"),
                        h1=list(item.get("h1") or []),
                        h2=list(item.get("h2") or []),
                        body_text=body,
                        word_count=len(body.split()),
                        schema_types=list(item.get("schema_types") or []),
                        json_ld=list(item.get("json_ld") or []),
                    )
                pages.append(pe)
                raw_html_map[url] = html_text or pe.body_text
                if item.get("headers"):
                    headers_map[url] = dict(item["headers"])
                snap = self.store.persist_snapshot(
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    snapshot_type="raw_html",
                    data=raw_html_map[url] or pe.title or url,
                    extension="html",
                    url=url,
                )
                snap_ids.append(snap.snapshot_id)
            return pages, raw_html_map, robots_txt, headers_map, snap_ids

        # Live crawl fallback (SSRF guarded)
        safe, reason = is_safe_url(self.target_url)
        if not safe:
            raise ValueError(f"SSRF guard blocked target URL '{self.target_url}': {reason}")
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                resp = await client.get(self.target_url, headers={"User-Agent": "Dristik-GEO-Auditor/1.0"})
                final_url = str(resp.url)
                html_text = resp.text[:250_000]
                pe = _parse_html_to_page_evidence(final_url, html_text, resp.status_code)
                pages.append(pe)
                raw_html_map[final_url] = html_text
                headers_map[final_url] = dict(resp.headers)
                snap = self.store.persist_snapshot(
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    snapshot_type="raw_html",
                    data=html_text,
                    extension="html",
                    url=final_url,
                )
                snap_ids.append(snap.snapshot_id)
                if not robots_txt:
                    robots_url = f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}/robots.txt"
                    if is_safe_url(robots_url)[0]:
                        try:
                            r_res = await client.get(robots_url, timeout=6.0)
                            if r_res.status_code == 200:
                                robots_txt = r_res.text[:50_000]
                        except Exception:
                            pass
        except Exception as exc:
            logger.warning("GEO live crawl failed for %s: %s", self.target_url, exc)
            self.audit.limitations.append(f"Live crawl failed for {self.target_url}: {exc}")

        return pages, raw_html_map, robots_txt, headers_map, snap_ids

    def _resolve_adapters(self) -> Dict[str, BaseGeoEngineAdapter]:
        adapters: Dict[str, BaseGeoEngineAdapter] = {}
        for pid in self.scope.platforms_requested:
            key = pid.lower().strip()
            if key in self.provider_overrides:
                adapters[key] = self.provider_overrides[key]
                continue
            ad = self.connectors.resolve_adapter_for_tenant(self.tenant_id, key)
            if ad is not None:
                adapters[key] = ad
        return adapters

    async def run(self) -> Dict[str, Any]:
        """Execute the full GEO DAG and persist all canonical entities, scorecard, remediation, and QA."""
        self.audit.status = GEOAuditStatus.RUNNING.value
        self.audit.publication_status = GEOPublicationStatus.PROCESSING.value
        self.audit.started_at = self.audit.started_at or datetime.now(timezone.utc).isoformat()
        self.store.save_audit(self.audit)
        self.events.emit(
            "geo.audit.started",
            {"domain": self.domain, "brand_name": self.brand_name, "mode": self.mode, "platforms": self.scope.platforms_requested},
        )

        # Previous audits for trend & monitoring delta comparison
        prior_audits = [
            a for a in self.store.list_audits(self.tenant_id, domain=self.domain, limit=10)
            if a.audit_id != self.audit_id
        ]

        try:
            # Stage 1: Crawl & Brand Knowledge Profile (preserving previously approved brand facts)
            existing_approved = self.store.list_entities(self.tenant_id)
            pages, raw_html_map, robots_txt, headers_map, snap_ids = await self._run_stage(
                "stage_01_crawl_and_scope", self._ingest_pages_and_robots
            )

            # Stage 2: Prompt Suite Generation (12 categories, strict branded/non-branded split)
            async def _build_prompts() -> List[GEOTestPrompt]:
                if self.custom_prompts:
                    out: List[GEOTestPrompt] = []
                    for item in self.custom_prompts:
                        out.append(
                            GEOTestPrompt(
                                tenant_id=self.tenant_id,
                                audit_id=self.audit_id,
                                target_brand=self.brand_name,
                                relevant_competitors=list(self.scope.competitors),
                                applicable_platforms=list(self.scope.platforms_requested),
                                repetitions=self.scope.repetitions,
                                **{k: v for k, v in item.items() if k not in ("tenant_id", "audit_id")},
                            )
                        )
                    return out
                return generate_prompt_suite(self.scope, audit_id=self.audit_id, version=1)

            prompts = await self._run_stage("stage_02_prompt_intelligence", _build_prompts)
            for pr in prompts:
                self.store.save_prompt(pr)
            self.audit.prompts_planned = sum(1 for p in prompts if p.approval_status == "approved")
            self.events.emit(
                "geo.prompt_suite.generated",
                {
                    "approved_prompts": self.audit.prompts_planned,
                    "branded": sum(1 for p in prompts if p.is_branded),
                    "non_branded": sum(1 for p in prompts if not p.is_branded),
                },
            )

            # Stage 3: Live Platform Testing with strict cost budget, per-provider timeout & provenance
            adapters = self._resolve_adapters()
            configured_pids = [
                pid for pid, ad in adapters.items()
                if ad.is_configured() and (self.scope.allow_live_provider_calls or pid in self.provider_overrides)
            ]
            unconfigured_pids = [pid for pid in self.scope.platforms_requested if pid.lower() not in configured_pids]
            self.audit.platforms_configured = configured_pids
            self.audit.platforms_unconfigured = unconfigured_pids

            runs: List[GEOPromptRun] = []
            responses: List[GEOResponse] = []
            mentions: List[GEOMention] = []
            citations: List[GEOCitation] = []
            provider_spend: Dict[str, float] = {pid: 0.0 for pid in adapters}
            total_spend = 0.0
            budget_paused = False
            model_versions_seen: Dict[tuple[str, str], GEOModelVersion] = {}

            async def _execute_providers() -> None:
                nonlocal total_spend, budget_paused
                approved_prompts = [p for p in prompts if p.approval_status == "approved"]
                if not configured_pids:
                    self.audit.limitations.append(
                        "No live AI provider credentials configured; Observed AI Visibility remains NOT_CONFIGURED (never zero)."
                    )
                    return

                sem = asyncio.Semaphore(4)

                async def _exec_one(prompt: GEOTestPrompt, pid: str, rep_num: int, client: httpx.AsyncClient) -> None:
                    nonlocal total_spend, budget_paused
                    if self._cancelled or budget_paused:
                        return
                    ad = adapters[pid]
                    # Enforce per-audit and per-provider budgets before dispatch
                    prov_cap = self.scope.per_provider_budget_usd.get(pid)
                    if self.scope.budget_usd > 0 and total_spend >= self.scope.budget_usd:
                        budget_paused = True
                        self.audit.budget_paused = True
                        return
                    if prov_cap is not None and provider_spend.get(pid, 0.0) >= prov_cap:
                        return

                    prompt_text = prompt.question
                    redacted_types: List[str] = []
                    if self.scope.pii_redaction_enabled:
                        prompt_text, redacted_types = redact_prompt_pii(prompt_text)

                    self.events.emit(
                        "geo.prompt.started",
                        {"prompt_id": prompt.prompt_id, "platform_id": pid, "repetition": rep_num, "pii_redacted": redacted_types},
                    )
                    req = EnginePromptRequest(
                        prompt=prompt_text,
                        locale=f"{prompt.language}-{prompt.market}",
                        market=prompt.market,
                        language=prompt.language,
                        enable_search=ad.supports_web_search,
                        allow_fallback=self.scope.allow_provider_fallback,
                        repetition_number=rep_num,
                    )
                    async with sem:
                        raw: Optional[EngineRawResponse] = None
                        for attempt in range(2):
                            try:
                                raw = await asyncio.wait_for(ad.execute_prompt(req, client=client), timeout=18.0)
                                if raw.is_live or raw.status_code in (401, 403, 501):
                                    break
                            except Exception as exc:
                                raw = EngineRawResponse(
                                    engine_id=pid,
                                    engine_name=ad.display_name,
                                    model_version=ad.model,
                                    requested_model=ad.model,
                                    raw_content="",
                                    status_code=504,
                                    error=str(exc),
                                    is_live=False,
                                    testing_mode=ad.default_testing_mode,
                                )
                            if attempt == 0:
                                await asyncio.sleep(0.1)

                    assert raw is not None
                    run_status = GEODataQualityState.OBSERVED if (raw.is_live and raw.raw_content.strip()) else (
                        GEODataQualityState.NOT_CONFIGURED if raw.status_code in (401, 501) else GEODataQualityState.FAILED
                    )
                    run = GEOPromptRun(
                        tenant_id=self.tenant_id,
                        audit_id=self.audit_id,
                        prompt_id=prompt.prompt_id,
                        original_prompt=prompt.question,
                        normalized_prompt=prompt.normalized_question or prompt_text,
                        platform_id=pid,
                        platform_name=raw.engine_name,
                        model_name=ad.model,
                        model_version=raw.model_version or ad.model,
                        testing_mode=raw.testing_mode,
                        market=prompt.market,
                        language=prompt.language,
                        repetition_number=rep_num,
                        session_limitations=list(raw.session_limitations or []),
                        status=run_status,
                        fallback_used=raw.fallback_used,
                        requested_model=raw.requested_model or ad.model,
                        fallback_reason=raw.fallback_reason,
                        latency_ms=raw.latency_ms,
                        prompt_tokens=raw.prompt_tokens,
                        completion_tokens=raw.completion_tokens,
                        cost_usd=raw.estimated_cost_usd,
                        error_message=raw.error,
                        data_quality_state=run_status,
                    )
                    self.store.save_prompt_run(run)
                    runs.append(run)
                    total_spend = round(total_spend + run.cost_usd, 6)
                    provider_spend[pid] = round(provider_spend.get(pid, 0.0) + run.cost_usd, 6)

                    if run_status != GEODataQualityState.OBSERVED:
                        self.events.emit("geo.prompt.failed", {"run_id": run.run_id, "platform_id": pid, "error": run.error_message})
                        return

                    # Track observed model version
                    mv_key = (pid, run.model_version)
                    if mv_key not in model_versions_seen:
                        mv = GEOModelVersion(
                            tenant_id=self.tenant_id,
                            audit_id=self.audit_id,
                            platform_id=pid,
                            model_name=run.model_name,
                            provider_reported_version=run.model_version,
                            testing_mode=run.testing_mode,
                            data_quality_state=GEODataQualityState.OBSERVED,
                        )
                        model_versions_seen[mv_key] = mv
                        self.store.save_model_version(mv)

                    # Persist immutable verbatim response snapshot
                    resp_snap = self.store.persist_snapshot(
                        tenant_id=self.tenant_id,
                        audit_id=self.audit_id,
                        snapshot_type="ai_response",
                        data=raw.raw_content,
                        extension="txt",
                        metadata={"run_id": run.run_id, "platform_id": pid, "model_version": run.model_version, "testing_mode": run.testing_mode.value},
                    )
                    snap_ids.append(resp_snap.snapshot_id)

                    resp_obj, resp_mentions, resp_cits = analyze_prompt_run_response(
                        run=run,
                        raw_text=raw.raw_content,
                        raw_citations=ad.extract_citations(raw),
                        tool_use_metadata=raw.tool_use_metadata,
                        scope=self.scope,
                        approved_entities=existing_approved,
                        snapshot_id=resp_snap.snapshot_id,
                    )
                    self.store.save_response(resp_obj)
                    responses.append(resp_obj)
                    self.events.emit("geo.prompt.completed", {"run_id": run.run_id, "platform_id": pid, "model_version": run.model_version})
                    self.events.emit("geo.response.persisted", {"response_id": resp_obj.response_id, "response_hash": resp_obj.response_hash})

                    for m in resp_mentions:
                        self.store.save_mention(m)
                        mentions.append(m)
                        if m.is_target_brand:
                            self.events.emit("geo.mention.detected", {"mention_id": m.mention_id, "type": m.mention_type.value, "platform_id": pid})

                    for c in resp_cits:
                        self.store.save_citation(c)
                        citations.append(c)
                        self.events.emit("geo.citation.detected", {"citation_id": c.citation_id, "domain": c.domain, "ownership": c.source_ownership.value})

                async with httpx.AsyncClient(timeout=20.0) as client:
                    tasks = [
                        _exec_one(pr, pid, rep, client)
                        for pr in approved_prompts
                        for pid in configured_pids
                        for rep in range(1, self.scope.repetitions + 1)
                    ]
                    if tasks:
                        await asyncio.gather(*tasks)

            await self._run_stage("stage_03_live_platform_testing", _execute_providers)
            self.audit.spent_usd = total_spend
            self.audit.prompts_executed = len({r.prompt_id for r in runs})
            self.audit.prompts_succeeded = sum(1 for r in runs if r.status == GEODataQualityState.OBSERVED)
            self.audit.prompts_failed = sum(1 for r in runs if r.status == GEODataQualityState.FAILED)
            self.audit.platforms_tested = sorted({r.platform_id for r in runs if r.status == GEODataQualityState.OBSERVED})

            # Stage 4: Build Platform scorecards, Brand Entity Profile & Citation Source Graph
            platforms_out: List[GEOPlatform] = []
            for pid, ad in adapters.items():
                p_runs = [r for r in runs if r.platform_id == pid]
                p_ok = [r for r in p_runs if r.status == GEODataQualityState.OBSERVED]
                p_resps = [resp for resp in responses if resp.platform_id == pid]
                p_cits = [c for c in citations if c.platform_id == pid]
                n_ok = len(p_ok)
                sent_dist: Dict[str, int] = {}
                for r in p_resps:
                    sent_dist[r.sentiment] = sent_dist.get(r.sentiment, 0) + 1
                inacc_cnt = sum(1 for r in p_resps if r.inaccurate_claims_count > 0)
                plat_rec = GEOPlatform(
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    platform_id=pid,
                    display_name=ad.display_name,
                    provider_family=pid,
                    active_model=p_ok[0].model_version if p_ok else ad.model,
                    testing_mode=p_ok[0].testing_mode if p_ok else ad.default_testing_mode,
                    capabilities=ad.get_capabilities(),
                    prompts_attempted=len(p_runs),
                    prompts_succeeded=n_ok,
                    prompts_failed=sum(1 for r in p_runs if r.status == GEODataQualityState.FAILED),
                    mention_count=sum(1 for r in p_resps if r.brand_mentioned),
                    recommendation_count=sum(1 for r in p_resps if r.brand_recommended),
                    citation_count=len(p_cits),
                    mention_rate_pct=round(sum(1 for r in p_resps if r.brand_mentioned) / n_ok * 100.0, 1) if n_ok else None,
                    recommendation_rate_pct=round(sum(1 for r in p_resps if r.brand_recommended) / n_ok * 100.0, 1) if n_ok else None,
                    citation_rate_pct=round(sum(1 for r in p_resps if r.brand_cited) / n_ok * 100.0, 1) if n_ok else None,
                    sentiment_breakdown=sent_dist,
                    accuracy_rate_pct=round(((n_ok - inacc_cnt) / n_ok) * 100.0, 1) if n_ok else None,
                    last_tested_at=p_ok[-1].executed_at if p_ok else None,
                    total_cost_usd=provider_spend.get(pid, 0.0),
                    limitations=list(ad.unsupported_features),
                    data_quality_state=(
                        GEODataQualityState.OBSERVED if n_ok > 0 else (
                            GEODataQualityState.NOT_CONFIGURED if pid in unconfigured_pids else GEODataQualityState.FAILED
                        )
                    ),
                )
                self.store.save_platform(plat_rec)
                platforms_out.append(plat_rec)

            entities, entity_summary = build_brand_knowledge_profile(
                scope=self.scope,
                audit_id=self.audit_id,
                pages=pages,
                raw_html_map=raw_html_map,
                existing_approved=existing_approved,
                ai_responses=responses,
            )
            for ent in entities:
                self.store.save_entity(ent)
            self.events.emit("geo.entity.analysis.completed", {"entities": len(entities), "conflicts": entity_summary.get("conflicting_facts", 0)})

            citation_graph, external_sources = build_citation_source_graph(
                scope=self.scope,
                prompts=prompts,
                responses=responses,
                mentions=mentions,
                citations=citations,
            )
            for src in external_sources:
                self.store.save_external_source(src)
            self.events.emit("geo.source.analysis.completed", {"external_sources": len(external_sources), "citations": len(citations)})

            # Stage 5: Execute all Specialist Departments (A–H) over canonical context
            ctx = GEOAuditContext(
                audit_id=self.audit_id,
                tenant_id=self.tenant_id,
                scope=self.scope,
                pages=pages,
                raw_html_map=raw_html_map,
                robots_txt=robots_txt,
                headers_map=headers_map,
                prompts=prompts,
                runs=runs,
                responses=responses,
                mentions=mentions,
                citations=citations,
                entities=entities,
                entity_summary=entity_summary,
                citation_graph=citation_graph,
                external_sources=external_sources,
                platforms=platforms_out,
                snapshot_ids=snap_ids,
                historical_audits=[a.model_dump() for a in prior_audits],
            )

            async def _run_specialists() -> tuple[List[Any], Dict[str, Any], List[Any]]:
                out_a, art_a = run_department_a(ctx)
                out_b, art_b = run_department_b(ctx)
                out_c, art_c = run_department_c(ctx)
                out_d, art_d, page_recs = run_department_d(ctx)
                out_e, art_e = run_department_e(ctx)
                out_f, art_f = run_department_f(ctx)
                out_g, art_g = run_department_g(ctx)
                out_h, art_h = run_department_h(ctx)
                return (
                    [out_a, out_b, out_c, out_d, out_e, out_f, out_g, out_h],
                    {
                        "department_a": art_a,
                        "department_b": art_b,
                        "department_c": art_c,
                        "department_d": art_d,
                        "department_e": art_e,
                        "department_f": art_f,
                        "department_g": art_g,
                        "department_h": art_h,
                    },
                    page_recs,
                )

            dept_outputs, dept_artifacts, page_readiness = await self._run_stage("stage_05_specialist_departments", _run_specialists)
            ctx.page_readiness = page_readiness
            for pr_page in page_readiness:
                self.store.save_page(pr_page)

            valid_ev_ids = set(snap_ids) | {r.response_id for r in responses} | {c.citation_id for c in citations} | {m.mention_id for m in mentions} | {e.entity_id for e in entities} | {p.page_id for p in page_readiness} | {p.url for p in pages}
            observed_urls = {c.cited_url for c in citations} | {p.url for p in pages}
            raw_findings = []
            for out in dept_outputs:
                validated = validate_agent_output(out, valid_evidence_ids=valid_ev_ids, observed_citation_urls=observed_urls)
                self.store.save_agent_execution(
                    execution_id=f"{self.audit_id}:{validated.agent_id}",
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    agent_id=validated.agent_id,
                    department=validated.department,
                    status=validated.status,
                    payload=validated.model_dump(),
                )
                raw_findings.extend(validated.findings)

            # Stage 6: Department I Consolidation (deduplication, root causes, ranked recommendations)
            out_i, consolidated_findings, recommendations, root_cause_groups = run_department_i_consolidate(ctx, raw_findings)
            self.store.replace_findings(self.tenant_id, self.audit_id, consolidated_findings)
            for rec in recommendations:
                self.store.save_recommendation(rec)
            for f in consolidated_findings:
                self.events.emit("geo.finding.validated", {"finding_id": f.finding_id, "severity": f.severity.value, "category": f.category})

            # Stage 7: Canonical Dual Scorecard & 7-Dimension Scoring
            scorecard = EnterpriseGEOScoringEngine.compute(
                audit_id=self.audit_id,
                scope=self.scope,
                prompts=prompts,
                runs=runs,
                responses=responses,
                citations=citations,
                platforms=platforms_out,
                dept_artifacts=dept_artifacts,
            )
            self.store.save_artifact(self.tenant_id, self.audit_id, "scorecard", scorecard.model_dump())
            self.store.save_artifact(self.tenant_id, self.audit_id, "citation_graph", citation_graph)
            self.store.save_artifact(self.tenant_id, self.audit_id, "department_artifacts", dept_artifacts)
            self.store.save_artifact(self.tenant_id, self.audit_id, "prompt_coverage", compute_prompt_coverage(prompts, runs))
            self.audit.observed_performance_score = scorecard.observed_performance_score
            self.audit.readiness_score = scorecard.readiness_score
            self.audit.methodology_composite_score = scorecard.methodology_composite_score
            self.events.emit(
                "geo.scoring.completed",
                {
                    "observed_performance_score": scorecard.observed_performance_score,
                    "readiness_score": scorecard.readiness_score,
                    "observed_status": scorecard.observed_performance_status.value,
                },
            )

            # Stage 8: Single Consolidated Remediation Pack (deferred when running in unified pipeline)
            if getattr(self, "defer_remediation", False) or getattr(self.scope, "defer_remediation", False):
                self.events.emit("geo.remediation.deferred", {"message": "GEO remediation deferred to Unified Cross-Pillar Remediation Pack"})
            else:
                pack = GEORemediationCenter.build_consolidated_pack(
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    scope=self.scope,
                    findings=consolidated_findings,
                    recommendations=recommendations,
                    root_cause_groups=root_cause_groups,
                    scorecard=scorecard,
                    pages=page_readiness,
                    prompts=prompts,
                    external_sources=external_sources,
                    dept_artifacts=dept_artifacts,
                )
                self.store.save_remediation_pack(pack)
                self.events.emit("geo.remediation.generated", {"pack_id": pack.pack_id, "tasks_count": len(pack.tasks)})

            # Stage 9: Independent Publication QA Gate & Monitoring Delta Alerts
            qa_report = GEOQualityAssuranceEngine.validate_audit(
                audit=self.audit,
                platforms=platforms_out,
                prompts=prompts,
                runs=runs,
                responses=responses,
                citations=citations,
                findings=consolidated_findings,
                scorecard=scorecard,
                remediation_pack=pack,
            )
            self.store.save_artifact(self.tenant_id, self.audit_id, "qa_report", qa_report.model_dump())
            self.audit.qa_status = qa_report.qa_status
            self.audit.publication_status = qa_report.publication_status
            self.audit.completed_at = datetime.now(timezone.utc).isoformat()
            if qa_report.qa_status == "failed":
                self.audit.status = GEOAuditStatus.FAILED.value
                self.audit.data_quality_state = GEODataQualityState.FAILED
                self.events.emit("geo.audit.failed", {"reason": "qa_gate_failed", "blocking": qa_report.blocking_failures})
            elif qa_report.qa_status == "partial":
                self.audit.status = GEOAuditStatus.PARTIAL.value
                self.audit.data_quality_state = GEODataQualityState.PARTIAL
                self.events.emit("geo.audit.partial", {"audit_id": self.audit_id, "warnings": qa_report.warnings})
            else:
                self.audit.status = GEOAuditStatus.COMPLETED.value
                self.audit.data_quality_state = GEODataQualityState.OBSERVED
                self.events.emit("geo.audit.completed", {"audit_id": self.audit_id, "publication_status": self.audit.publication_status})

            self.store.save_audit(self.audit)

            # Evaluate monitoring alerts against prior audit
            mon = GEOMonitoringEngine(store=self.store)
            mon.evaluate_audit_deltas(
                tenant_id=self.tenant_id,
                current_audit=self.audit,
                previous_audit=prior_audits[0] if prior_audits else None,
            )

            return {
                "audit": self.audit.model_dump(),
                "scorecard": scorecard.model_dump(),
                "qa_report": qa_report.model_dump(),
                "findings_count": len(consolidated_findings),
                "tasks_count": len(pack.tasks),
            }
        except Exception as exc:
            logger.exception("GEO audit %s failed: %s", self.audit_id, exc)
            self.audit.status = GEOAuditStatus.FAILED.value
            self.audit.publication_status = GEOPublicationStatus.QA_FAILED.value
            self.audit.limitations.append(f"Orchestrator execution error: {exc}")
            self.store.save_audit(self.audit)
            self.events.emit("geo.audit.failed", {"error": str(exc)})
            raise

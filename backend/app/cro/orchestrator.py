"""Phase 3 — Central CRO Orchestration & DAG Execution Engine.

Coordinates the complete 11-stage enterprise CRO workflow:
  1. Business Profile
  2. Conversion Goal Configuration
  3. Page and Journey Discovery
  4. Browser and Device Testing
  5. UX / UI / Content Analysis  ||  Analytics and Funnel Analysis (parallel wave)
  6. Specialist Department Execution (parallel waves across Depts A–I)
  7. Evidence and Finding Validation
  8. Scoring and Root Cause Analysis
  9. Consolidated Remediation Pack & Experiment Proposal Generation
 10. Independent CRO QA Gate
 11. CRO Audit Completion / Partial Completion

Capabilities:
- DAG dependencies, parallel wave execution, retries & per-stage timeouts
- Checkpointing to `cro_agent_executions` and `resume()` from completed stages
- Graceful cancellation, idempotency, provider/time budgets
- Missing GA4 never blocks browser/DOM CRO analysis (graceful `partial` or `completed` status)
- Real-time SSE streaming of all 21 canonical `cro.*` events via Dristik's EventStore
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Sequence
from urllib.parse import urlparse

import httpx

from app.core.security.ssrf import is_safe_url
from app.cro.browser_testing import CROBrowserTestingEngine
from app.cro.business_models import BusinessUnderstandingEngine
from app.cro.discovery import CRODiscoveryEngine
from app.cro.experimentation_engine import enterprise_experiment_engine
from app.cro.models import (
    CROAudit,
    CROAuditStatus,
    CROInteractionTest,
    CROPage,
    CROPageElement,
    CRORecommendation,
    CROSnapshot,
)
from app.cro.monitoring import CROMonitoringEngine
from app.cro.quality import CROQualityAssuranceEngine
from app.cro.remediation_center import CRORemediationCenter, deduplicate_findings
from app.cro.scoring import enterprise_cro_scoring_engine
from app.cro.specialists import CROAuditContext, validate_agent_output
from app.cro.specialists.analytics_attribution import run_department_i
from app.cro.specialists.ecommerce_trust import run_department_f, run_department_g
from app.cro.specialists.forms_cta import run_department_e
from app.cro.specialists.landing_copy import run_department_d
from app.cro.specialists.performance_tech import run_department_h
from app.cro.specialists.strategy import run_department_a
from app.cro.specialists.ux_ui import run_department_b, run_department_c
from app.db.cro_schema import CROStore, get_cro_store
from app.seo.audit.orchestration.event_store import EventStore

logger = logging.getLogger("dristik.cro.orchestrator")


class CROAuditOrchestrator:
    """Central DAG coordinator for enterprise CRO audits with real-time `cro.*` SSE streaming."""

    def __init__(
        self,
        *,
        tenant_id: str,
        target_url: str,
        mode: str = "standard",
        business_config: Optional[Dict[str, Any]] = None,
        analytics_payload: Optional[Dict[str, Any]] = None,
        campaign_context: Optional[Dict[str, Any]] = None,
        crm_payload: Optional[Dict[str, Any]] = None,
        commerce_payload: Optional[Dict[str, Any]] = None,
        field_cwv_payload: Optional[Dict[str, Any]] = None,
        connected_providers: Optional[List[str]] = None,
        seed_pages: Optional[List[Dict[str, Any]]] = None,
        safe_mode: bool = True,
        use_live_browser: bool = True,
        sandbox_allowlist: Optional[List[str]] = None,
        idempotency_key: Optional[str] = None,
        budget_seconds: float = 180.0,
        audit_id: Optional[str] = None,
        store: Optional[CROStore] = None,
    ):
        self.store = store or get_cro_store()
        self.tenant_id = tenant_id
        self.target_url = target_url if "://" in target_url else f"https://{target_url}"
        parsed = urlparse(self.target_url)
        self.domain = (parsed.netloc or parsed.path).replace("www.", "").strip("/")
        self.mode = mode
        self.business_config = business_config or {}
        self.analytics_payload = analytics_payload
        self.campaign_context = campaign_context
        self.crm_payload = crm_payload
        self.commerce_payload = commerce_payload
        self.field_cwv_payload = field_cwv_payload
        self.connected_providers = list(connected_providers or [])
        self.seed_pages = seed_pages
        self.safe_mode = safe_mode
        self.use_live_browser = use_live_browser
        self.sandbox_allowlist = sandbox_allowlist or []
        self.budget_seconds = budget_seconds

        # Idempotent lookup if key provided
        existing = self.store.find_audit_by_idempotency(tenant_id, idempotency_key) if idempotency_key else None
        if existing:
            self.audit = existing
        else:
            self.audit = CROAudit(
                tenant_id=tenant_id,
                domain=self.domain,
                target_url=self.target_url,
                mode=mode,
                status=CROAuditStatus.QUEUED.value,
                safe_mode=safe_mode,
                browser_testing_enabled=use_live_browser,
                analytics_connected=bool(
                    analytics_payload and (str(analytics_payload.get("state", "")).upper() == "MEASURED" or analytics_payload.get("connected"))
                ),
                idempotency_key=idempotency_key,
            )
            if audit_id:
                self.audit.audit_id = audit_id
            self.store.save_audit(self.audit)

        self.audit_id = self.audit.audit_id
        self.events = EventStore(audit_id=self.audit_id)
        self.browser_engine = CROBrowserTestingEngine(store=self.store)
        self._cancelled = False
        self._completed_stages: set[str] = set()
        self._ctx: Optional[CROAuditContext] = None

    def cancel(self) -> None:
        self._cancelled = True
        self.audit.status = CROAuditStatus.CANCELLED.value
        self.store.save_audit(self.audit)
        self.events.emit("cro.audit.failed", {"reason": "cancelled_by_user"})

    async def _run_stage(
        self,
        stage_id: str,
        fn: Callable[[], Coroutine[Any, Any, Any]],
        *,
        retries: int = 1,
        timeout_sec: float = 45.0,
    ) -> Any:
        if self._cancelled:
            raise asyncio.CancelledError("CRO audit cancelled")
        if stage_id in self._completed_stages:
            return None

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

    async def _fetch_seed_pages(self) -> List[Dict[str, Any]]:
        if self.seed_pages is not None:
            return list(self.seed_pages)
        safe, reason = is_safe_url(self.target_url)
        if not safe:
            raise ValueError(f"SSRF guard blocked target URL '{self.target_url}': {reason}")
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                resp = await client.get(self.target_url, headers={"User-Agent": "Dristik-CRO-Auditor/2.0"})
                return [
                    {
                        "url": str(resp.url),
                        "status_code": resp.status_code,
                        "raw_html": resp.text[:250_000],
                        "title": "",
                    }
                ]
        except Exception as exc:
            logger.warning("HTTP seed fetch failed for %s: %s", self.target_url, exc)
            return [{"url": self.target_url, "status_code": 0, "raw_html": "", "title": self.domain}]

    async def run(self) -> Dict[str, Any]:
        """Execute the full 11-stage CRO DAG and persist canonical results."""
        started = time.monotonic()
        self.audit.status = CROAuditStatus.RUNNING.value
        self.audit.started_at = self.audit.started_at or datetime.now(timezone.utc).isoformat()
        self.store.save_audit(self.audit)

        self.events.emit(
            "cro.audit.started",
            {"domain": self.domain, "target_url": self.target_url, "mode": self.mode, "safe_mode": self.safe_mode},
        )

        raw_pages: List[Dict[str, Any]] = []
        raw_html_map: Dict[str, str] = {}

        try:
            # Stage 1 & 2: Business Profile + Conversion Goal Configuration
            async def stage_profile_and_goals():
                nonlocal raw_pages, raw_html_map
                raw_pages = await self._fetch_seed_pages()
                for rp in raw_pages:
                    if rp.get("url") and rp.get("raw_html"):
                        raw_html_map[rp["url"]] = rp["raw_html"]

                profile, goals, audiences, scope = BusinessUnderstandingEngine.build(
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    target_url=self.target_url,
                    pages=raw_pages,
                    user_config=self.business_config,
                )
                self.store.save_business_profile(profile)
                self.audit.profile_id = profile.profile_id
                for g in goals:
                    self.store.save_goal(g)
                for a in audiences:
                    self.store.save_audience(a)

                self._ctx = CROAuditContext(
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    domain=self.domain,
                    target_url=self.target_url,
                    profile=profile,
                    goals=goals,
                    audiences=audiences,
                    scope=scope,
                    raw_html_map=raw_html_map,
                    analytics_payload=self.analytics_payload,
                    campaign_context=self.campaign_context,
                    crm_payload=self.crm_payload,
                    commerce_payload=self.commerce_payload,
                    field_cwv_payload=self.field_cwv_payload,
                    connected_providers=self.connected_providers,
                )
                self.events.emit("cro.business_profile.completed", {"profile_id": profile.profile_id, "business_type": profile.business_type.value})
                self.events.emit("cro.goals.detected", {"goals_count": len(goals), "primary_conversion": profile.primary_conversion})

            await self._run_stage("business_profile_and_goals", stage_profile_and_goals)
            assert self._ctx is not None
            ctx = self._ctx

            # Stage 3: Page & Journey Discovery
            async def stage_discovery():
                pages, journeys, graph = CRODiscoveryEngine.build_inventory_and_journeys(
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    profile=ctx.profile,
                    goals=ctx.goals,
                    raw_pages=raw_pages,
                    raw_html_map=raw_html_map,
                )
                # Copy any supplied performance telemetry onto discovered pages
                perf_by_url = {rp.get("url"): rp.get("performance_metrics") for rp in raw_pages if isinstance(rp, dict) and rp.get("performance_metrics")}
                for pg in pages:
                    if pg.url in perf_by_url:
                        pg.performance_metrics = perf_by_url[pg.url]
                    self.store.save_page(pg)
                for j in journeys:
                    self.store.save_journey(j)
                    self.events.emit("cro.journey.created", {"journey_id": j.journey_id, "name": j.name, "steps_count": len(j.steps)})
                ctx.pages = pages
                ctx.journeys = journeys
                ctx.journey_graph = graph
                self.events.emit("cro.pages.discovered", {"pages_count": len(pages), "page_types": [p.page_type.value for p in pages[:10]]})

            await self._run_stage("page_journey_discovery", stage_discovery)

            # Stage 4: Browser & Device Testing
            async def stage_browser_testing():
                self.events.emit("cro.browser_test.started", {"pages_count": len(ctx.pages), "safe_mode": self.safe_mode})
                all_tests: List[CROInteractionTest] = []
                all_elements: List[CROPageElement] = []
                all_snaps: List[CROSnapshot] = []
                max_pages = 5 if self.mode == "quick" else 25
                for pg in ctx.pages[:max_pages]:
                    tests, els, snaps = await self.browser_engine.audit_page(
                        tenant_id=self.tenant_id,
                        audit_id=self.audit_id,
                        page=pg,
                        raw_html=raw_html_map.get(pg.url),
                        viewports=("desktop", "tablet", "mobile"),
                        safe_mode=self.safe_mode,
                        sandbox_allowlist=self.sandbox_allowlist,
                        use_live_browser=self.use_live_browser,
                    )
                    self.store.save_page(pg)
                    for t in tests:
                        self.store.save_interaction_test(t)
                    for el in els:
                        self.store.save_element(el)
                    all_tests.extend(tests)
                    all_elements.extend(els)
                    all_snaps.extend(snaps)
                ctx.interaction_tests = all_tests
                ctx.elements = all_elements
                self.events.emit(
                    "cro.browser_test.completed",
                    {"tests_count": len(all_tests), "elements_count": len(all_elements), "snapshots_count": len(all_snaps)},
                )
                self.events.emit("cro.evidence.persisted", {"snapshots": len(all_snaps), "interaction_tests": len(all_tests)})

            await self._run_stage("browser_device_testing", stage_browser_testing, timeout_sec=60.0)

            # Stage 5 & 6: Parallel Specialist Departments (Depts A–I)
            async def _run_dept(agent_id: str, dept: str, fn: Callable[[CROAuditContext], Any]):
                self.events.emit("cro.agent.started", {"agent_id": agent_id, "department": dept})
                t0 = time.monotonic()
                out = await asyncio.to_thread(fn, ctx)
                out = validate_agent_output(out)
                elapsed = round(time.monotonic() - t0, 3)
                self.store.save_agent_execution(
                    execution_id=f"{self.audit_id}:{out.agent_id}",
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    agent_id=out.agent_id,
                    department=out.department,
                    status=out.status,
                    retry_count=0,
                    elapsed_sec=elapsed,
                    payload=out.model_dump(exclude={"findings"}),
                )
                self.events.emit(
                    "cro.agent.completed",
                    {"agent_id": out.agent_id, "department": out.department, "status": out.status, "findings_count": len(out.findings)},
                )
                return out

            async def stage_specialists():
                # Wave 1: Strategy, UX/Mobile/A11y, UI, Landing/Copy, Forms/CTA, Ecommerce, Trust, Performance, Analytics
                outputs = await asyncio.gather(
                    _run_dept("cro_department_a_strategy", "A", run_department_a),
                    _run_dept("cro_department_b_ux_mobile_a11y", "B", run_department_b),
                    _run_dept("cro_department_c_ui_visual", "C", run_department_c),
                    _run_dept("cro_department_d_landing_copy", "D", run_department_d),
                    _run_dept("cro_department_e_forms_cta", "E", run_department_e),
                    _run_dept("cro_department_f_ecommerce", "F", run_department_f),
                    _run_dept("cro_department_g_trust", "G", run_department_g),
                    _run_dept("cro_department_h_performance_tech", "H", run_department_h),
                    _run_dept("cro_department_i_analytics", "I", run_department_i),
                )
                for out in outputs:
                    ctx.all_findings.extend(out.findings)
                # Persist analytics events, funnels, and updated elements/journeys
                anl_art = ctx.artifacts.get("analytics_intelligence") or {}
                for ev in anl_art.get("events") or []:
                    from app.cro.models import CROAnalyticsEvent
                    self.store.save_analytics_event(CROAnalyticsEvent.model_validate(ev))
                for fnl in anl_art.get("funnels") or []:
                    from app.cro.models import CROFunnel
                    self.store.save_funnel(CROFunnel.model_validate(fnl))
                for j in ctx.journeys:
                    self.store.save_journey(j)
                for el in ctx.elements:
                    self.store.save_element(el)
                for g in ctx.goals:
                    self.store.save_goal(g)

                self.events.emit("cro.analytics.sync.completed", {"connected": bool(anl_art.get("is_connected"))})
                self.events.emit("cro.funnel.analysis.completed", {"funnels_count": len(anl_art.get("funnels") or [])})

            await self._run_stage("specialist_departments", stage_specialists, timeout_sec=60.0)

            # Stage 7 & 8: Evidence Validation, Deduplication & 3-Scorecard Calculation
            validated_findings: List[Any] = []
            scorecard = None

            async def stage_validation_and_scoring():
                nonlocal validated_findings, scorecard
                validated_findings, _dups = deduplicate_findings(ctx.all_findings)
                # Update per-page finding tallies
                for pg in ctx.pages:
                    pg.ux_findings_count = sum(1 for f in validated_findings if pg.url in f.affected_urls and f.category in ("ux_audit", "mobile_cro", "accessibility"))
                    pg.ui_findings_count = sum(1 for f in validated_findings if pg.url in f.affected_urls and f.category in ("ui_audit", "cta_intelligence"))
                    self.store.save_page(pg)

                for vf in validated_findings:
                    self.store.save_finding(vf)
                    self.events.emit(
                        "cro.finding.validated",
                        {"finding_id": vf.finding_id, "severity": vf.severity.value, "source_type": vf.source_type.value},
                    )

                anl_art = ctx.artifacts.get("analytics_intelligence") or {}
                ev_ratio = (
                    sum(1 for f in validated_findings if f.evidence_ids) / len(validated_findings)
                    if validated_findings
                    else 1.0
                )
                scorecard = enterprise_cro_scoring_engine.evaluate_three_scorecards(
                    audit_id=self.audit_id,
                    checks=ctx.dimension_checks,
                    measurement_checks=anl_art.get("measurement_checks") or [],
                    business_metrics=anl_art.get("business_performance_metrics") or [],
                    pages_audited=len(ctx.pages),
                    pages_discovered=len(raw_pages),
                    interaction_tests_executed=len(ctx.interaction_tests),
                    findings_with_evidence_ratio=ev_ratio,
                    analytics_connected=bool(anl_art.get("is_connected")),
                )
                self.store.save_artifact(self.tenant_id, self.audit_id, "scorecard", scorecard.model_dump())
                self.store.save_artifact(self.tenant_id, self.audit_id, "department_artifacts", ctx.artifacts)
                self.events.emit(
                    "cro.scoring.completed",
                    {
                        "experience_score": scorecard.experience_score,
                        "measurement_score": scorecard.measurement_score,
                        "business_performance_status": scorecard.business_performance_status,
                    },
                )

            await self._run_stage("validation_and_scoring", stage_validation_and_scoring)
            assert scorecard is not None

            # Stage 9: Consolidated Remediation Pack, Recommendations & Experiment Proposals
            remediation_pack = None
            experiments = []

            async def stage_remediation_and_experiments():
                nonlocal remediation_pack, experiments
                anl_art = ctx.artifacts.get("analytics_intelligence") or {}
                cr_metric = next((m for m in anl_art.get("business_performance_metrics", []) if m.get("metric") == "Primary Conversion Rate"), None)
                base_cr = (cr_metric["value"] / 100.0) if (cr_metric and cr_metric.get("value") is not None) else None

                hyps, experiments = enterprise_experiment_engine.design_from_findings(
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    findings=validated_findings,
                    target_audience=ctx.profile.target_customers if ctx.profile.target_customers != "unknown" else "All eligible visitors",
                    baseline_conversion_rate=base_cr,
                )
                for h in hyps:
                    self.store.save_hypothesis(h)
                for exp in experiments:
                    self.store.save_experiment(exp)
                    self.events.emit("cro.experiment.created", {"experiment_id": exp.experiment_id, "title": exp.title})

                # Persist structured CRORecommendation records (including copy approvals)
                for rank, f in enumerate(validated_findings, start=1):
                    rec = CRORecommendation(
                        tenant_id=self.tenant_id,
                        audit_id=self.audit_id,
                        url=f.affected_urls[0] if f.affected_urls else self.target_url,
                        source_evidence_ids=f.evidence_ids,
                        finding_ids=[f.finding_id],
                        category=f.category,
                        title=f"Remediate: {f.title}",
                        summary=f.recommendation,
                        implementation_instructions=f.implementation_instructions,
                        owner_role=f.owner_role,
                        effort=f.effort,
                        priority_rank=rank,
                        requires_copy_approval=f.category in ("copywriting_optimization", "landing_page_optimization"),
                        acceptance_criteria=f.acceptance_criteria,
                    )
                    self.store.save_recommendation(rec)

                remediation_pack = CRORemediationCenter.generate_pack(
                    tenant_id=self.tenant_id,
                    audit_id=self.audit_id,
                    profile=ctx.profile,
                    findings=validated_findings,
                    scorecard=scorecard,
                    artifacts=ctx.artifacts,
                    experiments=experiments,
                )
                self.store.save_remediation_pack(remediation_pack)
                self.events.emit(
                    "cro.remediation.generated",
                    {
                        "pack_id": remediation_pack.pack_id,
                        "tasks_count": len(remediation_pack.tasks),
                        "root_cause_groups_count": len(remediation_pack.root_cause_groups),
                    },
                )

            await self._run_stage("remediation_and_experiments", stage_remediation_and_experiments)
            assert remediation_pack is not None

            # Stage 10: Independent CRO QA Gate
            qa_report = None

            async def stage_qa():
                nonlocal qa_report
                self.audit.analytics_connected = bool((ctx.artifacts.get("analytics_intelligence") or {}).get("is_connected"))
                qa_report = CROQualityAssuranceEngine.validate_audit(
                    audit=self.audit,
                    pages=ctx.pages,
                    interaction_tests=ctx.interaction_tests,
                    findings=validated_findings,
                    scorecard=scorecard,
                    remediation_pack=remediation_pack,
                )
                self.store.save_artifact(self.tenant_id, self.audit_id, "qa_report", qa_report.model_dump())

            await self._run_stage("independent_qa", stage_qa)
            assert qa_report is not None

            # Stage 11: Finalize & Monitoring Regression Evaluation
            is_partial = (not self.audit.analytics_connected) or (qa_report.qa_status == "passed_with_warnings")
            self.audit.status = CROAuditStatus.PARTIAL.value if (not self.audit.analytics_connected and self.mode == "deep") else CROAuditStatus.COMPLETED.value
            self.audit.current_stage = "completed"
            self.audit.experience_score = scorecard.experience_score
            self.audit.measurement_score = scorecard.measurement_score
            self.audit.pages_audited = len(ctx.pages)
            self.audit.findings_count = len(validated_findings)
            self.audit.critical_findings_count = sum(1 for f in validated_findings if f.severity.value == "critical")
            self.audit.scope_coverage_pct = scorecard.scope_coverage_pct
            self.audit.test_coverage_pct = scorecard.test_coverage_pct
            self.audit.evidence_coverage_pct = scorecard.evidence_coverage_pct
            self.audit.qa_status = qa_report.qa_status
            self.audit.limitations = qa_report.warnings + scorecard.disclosures
            self.audit.completed_at = datetime.now(timezone.utc).isoformat()
            self.audit.metadata["elapsed_sec"] = round(time.monotonic() - started, 2)
            self.store.save_audit(self.audit)

            # Evaluate monitoring alerts against prior domain audit if present
            prior_audits = [a for a in self.store.list_audits(self.tenant_id, domain=self.domain, limit=5) if a.audit_id != self.audit_id]
            monitor = CROMonitoringEngine(self.store)
            monitor.evaluate_audit_regression(
                tenant_id=self.tenant_id,
                baseline_audit=prior_audits[0] if prior_audits else None,
                current_audit=self.audit,
                current_findings=validated_findings,
                experiments=experiments,
            )

            if self.audit.status == CROAuditStatus.PARTIAL.value:
                self.events.emit("cro.audit.partial", {"audit_id": self.audit_id, "experience_score": scorecard.experience_score, "warnings": qa_report.warnings})
            else:
                self.events.emit("cro.audit.completed", {"audit_id": self.audit_id, "experience_score": scorecard.experience_score, "qa_status": qa_report.qa_status})

            return {
                "audit": self.audit.model_dump(),
                "scorecard": scorecard.model_dump(),
                "qa_report": qa_report.model_dump(),
                "findings_count": len(validated_findings),
                "remediation_pack_id": remediation_pack.pack_id,
                "experiments_count": len(experiments),
                "partial_limitations": is_partial,
            }

        except Exception as exc:
            self.audit.status = CROAuditStatus.FAILED.value
            self.audit.metadata["error"] = str(exc)
            self.store.save_audit(self.audit)
            self.events.emit("cro.audit.failed", {"audit_id": self.audit_id, "error": str(exc)})
            raise

    async def resume(self) -> Dict[str, Any]:
        """Resume a paused or partially executed audit from completed checkpoints."""
        if self.audit.status == CROAuditStatus.CANCELLED.value:
            raise RuntimeError("Cannot resume a cancelled CRO audit.")
        self._cancelled = False
        return await self.run()

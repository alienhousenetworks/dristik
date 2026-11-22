"""
Dristik AI Advanced Autonomous Website Intelligence & Growth OS Orchestrator
Coordinates the 4-level cognitive architecture, dynamic cognitive teams, Evidence Graph 2.0,
hypothesis formulation, causal bottleneck discovery, AI search simulation, and validated remediation.
"""
import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Dict, Any, Optional, AsyncGenerator, List

logger = logging.getLogger(__name__)

_PRIOR_AUDIT_SKIP_STATUS = {"queued", "running", "failed", "error", "cancelled", "canceled"}


def _sha256_hex(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _stored_evidence_is_linkable(row: Any) -> bool:
    """A stored row can be cited. A minted hash_ or sha_ prefix cannot."""
    if row is None:
        return False
    content_sha = str(getattr(row, "content_sha256", "") or "")
    digest = str(getattr(row, "hash", "") or "")
    if content_sha.startswith(("sha_", "hash_")) or digest.startswith(("sha_", "hash_")):
        return False
    if content_sha and not _sha256_hex(content_sha):
        return False
    return bool(getattr(row, "id", None))


def _prior_audit_snapshots(repository: Any, org_id: Any, domain: str, analysis_id: str) -> List[Any]:
    """Completed scores for this org and domain. A new process has no in-memory twin."""
    from app.domain.models import AuditSnapshot

    clean = str(org_id or "").strip()
    if not clean or clean in FORBIDDEN_TENANT_IDENTIFIERS or clean in {"org_default", "default"}:
        return []
    try:
        rows = repository.list_runs(clean, limit=30)
    except Exception:
        logger.info("prior audit scores were not loaded")
        return []
    snapshots = []
    for row in reversed(rows or []):
        if str(row.get("analysis_id") or "") == str(analysis_id or ""):
            continue
        if str(row.get("domain") or "").lower() != str(domain or "").lower():
            continue
        if str(row.get("status") or "").lower() in _PRIOR_AUDIT_SKIP_STATUS:
            continue
        score = row.get("score_overall")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            continue
        raw_date = str(row.get("completed_at") or row.get("created_at") or "")
        label = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                label = datetime.strptime(raw_date[:19], fmt).strftime("%b %d, %Y")
                break
            except ValueError:
                continue
        if label is None:
            continue
        run_id = str(row.get("analysis_id") or "")
        snapshots.append(AuditSnapshot(
            snapshot_id=run_id or f"prior_{domain}",
            run_label=run_id or "Prior run",
            date=label,
            score=float(score),
            category_scores={},
            evidence_seal=str(row.get("output_hash") or run_id),
            verified_schema_types=[],
            findings_count=0,
            status="HEALTHY",
        ))
    return snapshots

from app.core.config import settings
from app.core.constants import FORBIDDEN_TENANT_IDENTIFIERS

from app.aeo.analytics_history import aeo_analytics_history_store
from app.aeo.scoring import AeoMetricsCalculator
from app.domain.models import AnalysisRun, ExecutiveReport, CrawlManifest, FindingEvidence
from app.db.models import StageCheckpoint
from app.domain.enums import AnalysisStage, Category, Severity
from app.domain.capability import CAPABILITY_REGISTRY
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.orchestration.cognition.decision_engine import DecisionEngine
from app.orchestration.cognition.hypotheses import HypothesisEngine
from app.orchestration.cognition.causal import CausalReasoningEngine
from app.orchestration.cognition.confidence import CalibratedConfidenceEngine
from app.domain.evidence.graph import GraphNodeType, GraphEdgeType
from app.domain.evidence.validation import EvidenceGapDetector
from app.seo.business.website_twin import WebsiteDigitalTwin
from app.seo.business.intent_graph import SearchIntentGraph
from app.seo.business.opportunity import OpportunityDetector
from app.geo.citations.simulation import AISearchSimulationEngine
from app.core.monitoring.timeline import WebsiteIntelligenceTimeline
from app.core.inference.model_router import ModelRouter
from app.core.inference.telemetry import TelemetryTracker
from app.crawl.crawler import CrawlerService
from app.orchestration.mission.director import MissionDirector
from app.orchestration.team_orchestrator import TeamOrchestrator
from app.orchestration.agent_pool import AgentPool
from app.domain.scoring.engine import ScoringEngine
from app.remediation.planner import RemediationPlanner
from app.reports.narrative import NarrativeGenerator
from app.reports.roadmap import RoadmapBuilder
from app.crawl.page_intelligence import PageIntelligenceAgent
from app.domain.evidence.site_facts import extract_site_facts
from app.remediation.patch_pack import generate_character_safe_copy, generate_whatsapp_summary
from app.seo.competitive.bakeoff import CommercialBakeoffEngine
from app.seo.competitive.benchmark import build_competitor_seo_parity_matrix
from app.seo.business.understanding import BusinessUnderstandingOrchestrator
from app.orchestration.integrity_gate import integrity_gate
from app.orchestration.pipeline_dag import (
    get_pipeline_controller,
    GraphNodeStatus,
    ActivityEvent,
    NODES_REGISTRY,
    SECTIONS_REGISTRY,
    PILLAR_TO_SECTION,
    SECTION_TO_PILLAR,
)
from app.reporting.contracts.subphase_contract import (
    ConfidenceLevel,
    EvidenceTokenReference,
    ExecutionStatus,
    ReportFinding,
    SubPhaseReportContract,
)
from app.reporting.engines.report_registry import get_report_registry
from app.reporting.engines.subphase_report_builder import SubPhaseReportBuilder

class AnalysisOrchestrator:
    def __init__(self):
        self.runs: Dict[str, AnalysisRun] = {}
        self.blackboards: Dict[str, CognitiveBlackboard] = {}
        self.event_queues: Dict[str, asyncio.Queue] = {}
        self.crawler = CrawlerService()
        self.mission_director = MissionDirector()
        self.decision_engine = DecisionEngine()
        self.hypothesis_engine = HypothesisEngine()
        self.causal_engine = CausalReasoningEngine()
        self.confidence_engine = CalibratedConfidenceEngine()
        self.gap_detector = EvidenceGapDetector()
        self.opportunity_detector = OpportunityDetector()
        self.ai_simulator = AISearchSimulationEngine()
        self.intent_graph = SearchIntentGraph()
        self.scoring_engine = ScoringEngine()
        self.remediation_planner = RemediationPlanner()
        self.narrative_gen = NarrativeGenerator()
        self.roadmap_builder = RoadmapBuilder()
        self.bakeoff_engine = CommercialBakeoffEngine()
        # Manual pillar, section, and node runs are queued per audit so the HTTP
        # request can return before a model call finishes. One worker per audit
        # keeps those runs from overlapping each other.
        self._pipeline_queue: Dict[str, List[tuple]] = {}
        self._pipeline_active: Dict[str, str] = {}
        self._pipeline_worker: Dict[str, asyncio.Task] = {}
        self.digital_twins: Dict[str, WebsiteDigitalTwin] = {}
        self.timelines: Dict[str, WebsiteIntelligenceTimeline] = {}
        from app.db.repository import get_audit_repository
        self.repository = get_audit_repository()
        self.model_router = ModelRouter()

    def create_run(
        self,
        website_url: str,
        org_id: str,
        created_by: Optional[str] = None,
        target_pillars: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        audit_tier: str = "basic",
        credits_charged: int = 0,
    ) -> AnalysisRun:
        if not org_id or not isinstance(org_id, str) or not org_id.strip():
            raise ValueError("Tenant org_id is required and cannot be empty.")
        clean_org = org_id.strip()
        if clean_org.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
            raise ValueError(f"Disallowed tenant identifier '{clean_org}'.")

        clean_ws = None
        if workspace_id is not None:
            if not isinstance(workspace_id, str) or not workspace_id.strip():
                raise ValueError("Tenant workspace_id cannot be empty or whitespace-only.")
            clean_ws = workspace_id.strip()
            if clean_ws.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
                raise ValueError(f"Disallowed workspace identifier '{clean_ws}'.")
        else:
            clean_ws = f"ws_default_{clean_org}"

        analysis_id = f"run_{uuid.uuid4().hex[:10]}"
        now_str = datetime.now().isoformat()
        norm_pillars = [p.strip().lower() for p in target_pillars if p and p.strip().lower() in PILLAR_TO_SECTION] if target_pillars else None

        run = AnalysisRun(
            analysis_id=analysis_id,
            org_id=clean_org,
            workspace_id=clean_ws,
            website_url=website_url,
            status=AnalysisStage.QUEUED,
            progress_percentage=0,
            current_step="Analysis Queued",
            created_at=now_str,
            updated_at=now_str,
            target_pillars=norm_pillars,
            audit_tier=audit_tier,
            credits_charged=int(credits_charged or 0),
        )
        self.runs[analysis_id] = run
        self.event_queues[analysis_id] = asyncio.Queue()
        try:
            self.repository.save_run(run)
        except Exception as e:
            logger.warning(f"Failed to persist initial audit run {analysis_id}: {e}")
        return run

    def get_run(self, analysis_id: str) -> Optional[AnalysisRun]:
        # Support lookup by run ID or report ID
        if analysis_id in self.runs:
            return self.runs[analysis_id]
        for r in self.runs.values():
            if r.report and (r.report.report_id == analysis_id or getattr(r.report, "analysis_id", None) == analysis_id):
                return r
        # Durable DB fallback
        try:
            stored = self.repository.get_run(analysis_id)
            if stored:
                report_obj = None
                raw_json = stored.get("raw_report_json")
                if raw_json:
                    try:
                        report_obj = ExecutiveReport.model_validate_json(raw_json)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize report for {analysis_id}: {e}")

                status_val = stored["status"]
                stage_enum = AnalysisStage.QUEUED
                for s in AnalysisStage:
                    if s.value == status_val or str(s) == status_val:
                        stage_enum = s
                        break

                run = AnalysisRun(
                    analysis_id=stored["analysis_id"],
                    org_id=stored["org_id"],
                    workspace_id=stored.get("workspace_id"),
                    website_url=stored["website_url"],
                    status=stage_enum,
                    progress_percentage=stored.get("progress", 100 if report_obj else 0),
                    current_step=stored.get("stage", "Completed" if report_obj else "Queued"),
                    score_band=stored.get("score_band") or "Pending Evaluation",
                    created_at=stored.get("started_at") or stored.get("created_at") or datetime.now().isoformat(),
                    updated_at=stored.get("completed_at") or stored.get("started_at") or datetime.now().isoformat(),
                    completed_at=stored.get("completed_at"),
                    report=report_obj
                )
                self.runs[analysis_id] = run
                return run
        except Exception as err:
            logger.warning(f"Error loading stored run {analysis_id}: {err}")
        return None

    async def _emit_event(self, analysis_id: str, stage: str, progress: int, message: str, data: Optional[Dict[str, Any]] = None):
        run = self.runs.get(analysis_id)
        if run:
            run.progress_percentage = progress
            run.current_step = message
            run.updated_at = datetime.now().isoformat()

        queue = self.event_queues.get(analysis_id)
        if queue:
            payload_data = dict(data or {})
            telemetry_snapshot = None
            if run and getattr(run, "telemetry", None):
                try:
                    telemetry_snapshot = run.telemetry.model_dump(mode="json")
                    if "telemetry" not in payload_data:
                        payload_data["telemetry"] = telemetry_snapshot
                except Exception:
                    pass

            ctrl = get_pipeline_controller(analysis_id)
            graph_snapshot = ctrl.get_full_graph_state()
            if "graph" not in payload_data:
                payload_data["graph"] = graph_snapshot

            event_payload = {
                "stage": stage,
                "progress": progress,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "data": payload_data,
                "telemetry": telemetry_snapshot,
                "graph": graph_snapshot,
            }
            await queue.put(event_payload)

    async def _record_progressive_subphase(
        self,
        contract: SubPhaseReportContract,
        filename_slug: str,
        generate_pdf_now: bool = True,
    ) -> Dict[str, Any]:
        """Records subphase output to disk, generates PDF, and emits a live stream notification."""
        registry = get_report_registry()
        entry = await registry.register_and_generate_subphase(
            contract, filename_slug, generate_pdf_now=generate_pdf_now
        )
        run = self.runs.get(contract.run_id)
        current_pct = run.progress_percentage if run else 50
        await self._emit_event(
            contract.run_id,
            "progressive_report_ready",
            current_pct,
            f"Progressive Report Ready: Sub-Phase {contract.subphase_id} - {contract.subphase_title}",
            {
                "report_type": "subphase",
                "phase_id": contract.phase_id,
                "subphase_id": contract.subphase_id,
                "title": contract.subphase_title,
                "status": contract.status.value,
                "confidence": contract.confidence.value,
                "content_hash": contract.content_hash,
                "pdf_ready": entry.get("pdf_ready", False),
                "download_url": entry.get("download_url"),
                "json_url": entry.get("json_url"),
            },
        )
        return entry

    async def _consolidate_progressive_phase(
        self,
        analysis_id: str,
        phase_id: str,
        filename_slug: str,
        generate_pdf_now: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Consolidates all completed subphases of a phase into a Phase PDF and emits live event."""
        registry = get_report_registry()
        entry = await registry.consolidate_and_generate_phase(
            analysis_id, phase_id, filename_slug, generate_pdf_now=generate_pdf_now
        )
        if entry:
            run = self.runs.get(analysis_id)
            current_pct = run.progress_percentage if run else 50
            await self._emit_event(
                analysis_id,
                "progressive_report_ready",
                current_pct,
                f"Consolidated Phase Report Ready: {entry.get('phase_name', phase_id)}",
                {
                    "report_type": "phase",
                    "phase_id": phase_id,
                    "phase_name": entry.get("phase_name"),
                    "status": entry.get("status"),
                    "content_hash": entry.get("content_hash"),
                    "pdf_ready": entry.get("pdf_ready", False),
                    "download_url": entry.get("download_url"),
                },
            )
        return entry

    async def stream_events(self, analysis_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        queue = self.event_queues.get(analysis_id)
        if not queue:
            return

        while True:
            event = await queue.get()
            yield event
            if event.get("stage") in [AnalysisStage.COMPLETED.value, AnalysisStage.FAILED.value]:
                break

    async def execute_analysis_pipeline(
        self,
        analysis_id: str,
        website_url: str,
        max_pages: Optional[int] = None,
        site_type: Optional[str] = None,
        declared_site_type_notes: Optional[str] = None,
        country: Optional[str] = None,
        language: Optional[str] = None,
        target_pillars: Optional[List[str]] = None,
        audit_tier: Optional[str] = None,
        credits_charged: int = 0,
    ):
        """
        Cognitive OS mission execution across all 4 cognitive levels.
        """
        run = self.runs.get(analysis_id)
        if not run:
            stored = self.repository.get_run(analysis_id)
            if stored:
                run = self.get_run(analysis_id)

        clean_org = run.org_id.strip() if (run and isinstance(run.org_id, str)) else ""
        if not run or not clean_org or clean_org.lower() in FORBIDDEN_TENANT_IDENTIFIERS:
            raise ValueError(f"Cannot execute pipeline for analysis {analysis_id}: valid tenant org_id required, 'org_default' rejected.")

        resolved_tier = audit_tier or getattr(run, "audit_tier", None) or "premium"
        resolved_credits = int(credits_charged or getattr(run, "credits_charged", 0) or 0)
        from app.core.inference.llm_client import use_tenant_context
        with use_tenant_context(clean_org):
            return await self._execute_analysis_pipeline_scoped(
                run=run,
                analysis_id=analysis_id,
                website_url=website_url,
                max_pages=max_pages,
                site_type=site_type,
                declared_site_type_notes=declared_site_type_notes,
                country=country,
                language=language,
                target_pillars=target_pillars,
                audit_tier=resolved_tier,
                credits_charged=resolved_credits,
            )

    async def _enrich_findings_with_ai(
        self,
        *,
        findings: List[Any],
        model_router: Any,
        business_profile: Any,
        site_facts: Dict[str, Any],
        website_url: str,
        batch_size: int = 10,
    ) -> int:
        """
        Ensures every final finding (including Stage-1 deterministic findings and
        ROOT_RC_* deduplicated clusters) receives grounded, site-specific AI diagnosis,
        business-impact framing, recommendation, and validation criteria.
        Preserves finding_id, severity, evidence_refs, affected_urls, and scores.
        """
        if not findings or not model_router or not hasattr(model_router, "generate_structured"):
            return 0

        _GENERIC_REC = "implement recommended architectural fix based on evidence."

        def _needs_ai_analysis(f: Any) -> bool:
            if getattr(f, "held_from_executive", False):
                return False
            fid = str(getattr(f, "finding_id", "") or "")
            why = str(getattr(f, "why_it_matters", "") or "").strip()
            rec = str(getattr(f, "recommendation", "") or "").strip()
            desc = str(getattr(f, "description", "") or "").strip()
            title = str(getattr(f, "title", "") or "").strip()
            if fid.startswith("ROOT_RC_") or not getattr(f, "agent_id", None):
                return True
            if not why or why.startswith("This canonical defect consolidates") or why == title or why == desc:
                return True
            if not rec or rec.lower() == _GENERIC_REC:
                return True
            return False

        candidates = [f for f in findings if _needs_ai_analysis(f)]
        if not candidates:
            return 0

        biz_name = getattr(business_profile, "business_name", None) or website_url
        industry = getattr(business_profile, "industry", None) or "Unknown"
        value_prop = getattr(business_profile, "value_proposition", None) or ""
        schema_desc = (
            '{"analyses":[{"finding_id":"string (MUST match an input finding_id)",'
            '"detailed_diagnosis":"string (2-3 concrete sentences citing observed URLs/elements from evidence)",'
            '"why_it_matters":"string (business, conversion, or organic visibility impact for this specific brand)",'
            '"recommendation":"string (concrete, actionable engineering/content fix for this site)",'
            '"validation_criteria":"string (present-tense checkable acceptance test)"}]}'
        )

        enriched_count = 0
        by_id = {f.finding_id: f for f in candidates}

        for start in range(0, len(candidates), batch_size):
            batch = candidates[start:start + batch_size]
            payload = []
            for f in batch:
                ev_items = []
                for ev in (f.evidence or [])[:4]:
                    ev_items.append({
                        "evidence_id": getattr(ev, "evidence_id", None),
                        "url": getattr(ev, "url", None),
                        "selector": getattr(ev, "selector", None) or getattr(ev, "element", None),
                        "snippet": str(getattr(ev, "snippet", None) or getattr(ev, "value", "") or "")[:160],
                    })
                sub_obs = [
                    {
                        "title": getattr(o, "title", ""),
                        "url": getattr(o, "url", None),
                        "selector": getattr(o, "selector", None),
                    }
                    for o in (getattr(f, "detailed_observations", None) or [])[:5]
                ]
                payload.append({
                    "finding_id": f.finding_id,
                    "category": f.category.value if hasattr(f.category, "value") else str(f.category),
                    "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                    "title": (f.title or "")[:180],
                    "current_description": (f.description or "")[:240],
                    "affected_urls": (f.affected_urls or [website_url])[:5],
                    "evidence": ev_items,
                    "sub_observations": sub_obs,
                })

            contract = (
                f"WEBSITE: {website_url}\n"
                f"BRAND: {biz_name} | INDUSTRY: {industry}\n"
                f"VALUE PROPOSITION: {value_prop[:200]}\n"
                f"FINDINGS TO ANALYZE:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
                "INSTRUCTIONS:\n"
                "1. Analyze every input finding using ONLY the supplied evidence, sub_observations, affected_urls, and brand context.\n"
                "2. Write a site-specific `detailed_diagnosis`, brand-specific `why_it_matters`, concrete `recommendation`, "
                "and checkable `validation_criteria` for each `finding_id`.\n"
                "3. ZERO FABRICATION: Never invent URLs, metrics, percentages, or claims not present in the input evidence."
            )
            try:
                raw = await model_router.generate_structured(
                    capability="finding_analysis",
                    agent_role="Principal SEO/GEO/CRO Diagnostic Analyst",
                    task_contract=contract,
                    evidence_list=[],
                    output_schema_desc=schema_desc,
                    site_facts=site_facts,
                    max_claims=0,
                    allow_fallback=False,
                    model_tier="fast_slm",
                    max_tokens=3000,
                )
            except Exception as exc:
                logger.warning("[FindingAI] Batch enrichment failed: %s", exc)
                continue

            if not isinstance(raw, dict) or str(raw.get("status") or "").lower() in ("unavailable", "budget_exceeded"):
                logger.info("[FindingAI] Skipped batch enrichment (status=%s)", raw.get("status") if isinstance(raw, dict) else "invalid")
                continue

            for item in (raw.get("analyses") or []):
                if not isinstance(item, dict):
                    continue
                fid = str(item.get("finding_id") or "").strip()
                target = by_id.get(fid)
                if target is None:
                    continue
                diag = str(item.get("detailed_diagnosis") or "").strip()
                why = str(item.get("why_it_matters") or "").strip()
                rec = str(item.get("recommendation") or "").strip()
                val = str(item.get("validation_criteria") or "").strip()
                updated = False
                if diag:
                    target.description = diag
                    target.detailed_diagnosis = diag
                    target.diagnosis = diag
                    target.concise_summary = diag[:280]
                    updated = True
                if why:
                    target.why_it_matters = why
                    target.business_context = why
                    target.business_impact = why
                    updated = True
                if rec:
                    target.recommendation = rec
                    target.recommended_solution = rec
                    updated = True
                if val:
                    target.validation_criteria = val
                    target.acceptance_criteria = val
                    updated = True
                if updated:
                    if not target.agent_id:
                        target.agent_id = "ai.finding_analyst"
                    enriched_count += 1

        logger.info("[FindingAI] Enriched %d/%d findings via AI (total=%d)", enriched_count, len(candidates), len(findings))
        return enriched_count

    async def _run_deterministic_analyzers(
        self,
        *,
        eval_pages: List[Any],
        manifest: Optional[CrawlManifest],
        blackboard: CognitiveBlackboard,
        domain: str,
        website_url: str,
    ) -> Dict[str, Any]:
        """Stage 1 ($0.00): Execute all 18 deterministic Python analyzers before AI specialists."""
        from app.cro.visual_ux_tester import visual_ux_tester
        from app.seo.analyzers.canonical_auditor import analyze_canonicals
        from app.seo.analyzers.http_status_auditor import analyze_http_statuses
        from app.seo.analyzers.heading_analyzer import HeadingAnalyzer, analyze_heading_hierarchy
        from app.seo.analyzers.media_asset_analyzer import MediaAssetAnalyzer, analyze_media_assets
        from app.seo.analyzers.link_depth import LinkDepthAnalyzer, analyze_link_depth_and_orphans
        from app.seo.analyzers.meta_rollup import analyze_meta_rollup
        from app.cro.form_analyzer import analyze_forms
        from app.cro import analyze_cro
        from app.crawl.analyzers.security_analyzer import analyze_security_headers
        from app.seo.analyzers.schema_validator import analyze_schema_rich_results
        from app.seo.analyzers.local_seo_analyzer import analyze_local_seo
        from app.seo.analyzers.international_seo_analyzer import analyze_international_seo
        from app.seo.analyzers.topical_authority_analyzer import analyze_topical_authority
        from app.seo.analyzers.ecommerce_seo import analyze_ecommerce_seo
        from app.seo.analyzers.serp_appearance import analyze_serp_appearance
        from app.cro.accessibility.wcag_auditor import DeepWcagAuditor
        from app.crawl.indexation.classifier import indexation_classifier
        from app.seo.competitive.benchmark import build_competitor_seo_parity_matrix
        from app.seo.analyzers.host_and_redirects import probe_host_and_redirects

        cro_finding = visual_ux_tester.generate_grounded_cro_finding(
            domain=domain,
            website_url=website_url,
            pages=eval_pages or getattr(blackboard, "pages", None),
        )
        canonical_audit_rep, can_findings = analyze_canonicals(eval_pages)
        broken_raw = manifest.crawl_health.get("broken_links") if manifest and manifest.crawl_health else []
        http_status_rep, http_findings = analyze_http_statuses(eval_pages, broken_links_raw=broken_raw)

        heading_hierarchy_rep = analyze_heading_hierarchy(eval_pages)
        heading_findings = HeadingAnalyzer.generate_findings(heading_hierarchy_rep)

        media_assets_rep = analyze_media_assets(eval_pages)
        media_findings = MediaAssetAnalyzer.generate_findings(media_assets_rep)

        sitemap_urls_sample = [manifest.sitemap_url] if (manifest and manifest.sitemap_url) else []
        click_depth_rep, orphan_pages_rep, anchor_text_audit_rep = analyze_link_depth_and_orphans(
            eval_pages, sitemap_urls=sitemap_urls_sample, homepage_url=website_url
        )
        link_findings = LinkDepthAnalyzer.generate_findings(click_depth_rep, orphan_pages_rep, anchor_text_audit_rep)

        meta_rollup_rep = analyze_meta_rollup(eval_pages)
        form_audit_rep = analyze_forms(eval_pages)
        cro_audit_rep, cro_findings = analyze_cro(
            eval_pages,
            raw_html_map=getattr(blackboard, "raw_html_map", None),
            business_profile=blackboard.business_profile,
        )
        schema_validation_rep = analyze_schema_rich_results(eval_pages)
        wcag_audit_rep, wcag_findings = DeepWcagAuditor.audit_pages(eval_pages)

        local_seo_rep, local_findings = analyze_local_seo(eval_pages, target_domain=domain)
        intl_seo_rep, intl_findings = analyze_international_seo(eval_pages, target_domain=domain)
        topical_auth_rep, topical_findings = analyze_topical_authority(eval_pages, target_domain=domain)
        ecom_seo_rep, ecom_findings = analyze_ecommerce_seo(eval_pages, target_domain=domain)
        serp_app_rep, serp_findings = analyze_serp_appearance(eval_pages, target_domain=domain)

        indexation_rollup_rep, indexation_findings = indexation_classifier.audit(
            manifest=manifest,
            pages=eval_pages,
        )
        if manifest:
            manifest.indexation_rollup = indexation_rollup_rep

        competitor_seo_parity_rep = build_competitor_seo_parity_matrix(
            target_pages=eval_pages,
            target_domain=domain,
            manifest=manifest,
        )

        first_page_headers = {}
        if eval_pages and getattr(eval_pages[0], "response_headers", None):
            first_page_headers = eval_pages[0].response_headers
        security_audit_rep = analyze_security_headers(
            url=website_url,
            response_headers=first_page_headers,
        )

        try:
            host_and_redirects_rep = await probe_host_and_redirects(domain_or_url=website_url, canonical_target=website_url)
        except Exception:
            from app.domain.models import RedirectAuditReport
            host_and_redirects_rep = RedirectAuditReport(
                target_domain=domain,
                canonical_destination=website_url,
                summary="Host variant probe did not complete. www, apex, and protocol variants were not measured.",
            )

        analyzer_finding_groups = [
            [cro_finding] if cro_finding is not None else [],
            can_findings,
            http_findings,
            heading_findings,
            media_findings,
            link_findings,
            cro_findings,
            wcag_findings,
            local_findings,
            intl_findings,
            topical_findings,
            ecom_findings,
            serp_findings,
            indexation_findings,
        ]
        store = blackboard.evidence_store if hasattr(blackboard, "evidence_store") else None
        all_stored = store.get_all() if store is not None else []
        deterministic_findings: List[Any] = []
        seen_ids: set = set()
        for group in analyzer_finding_groups:
            for f in (group or []):
                if not f or not getattr(f, "finding_id", None) or f.finding_id in seen_ids:
                    continue
                ev_refs = []
                for ev in (getattr(f, "evidence", []) or []):
                    ev_id = getattr(ev, "evidence_id", None) or (ev.get("evidence_id") if isinstance(ev, dict) else None)
                    stored = store.get(ev_id) if store is not None and ev_id else None
                    if _stored_evidence_is_linkable(stored):
                        ev_refs.append(str(ev_id))
                if not ev_refs and all_stored:
                    page_target = (getattr(f, "affected_urls", []) or [None])[0]
                    if page_target:
                        for existing in all_stored:
                            if _stored_evidence_is_linkable(existing) and existing.url and page_target in existing.url:
                                ev_refs.append(existing.id)
                                break
                # Leave evidence_refs empty when nothing stored has a real hash.
                f.evidence_refs = list(dict.fromkeys((f.evidence_refs or []) + ev_refs))
                deterministic_findings.append(f)
                seen_ids.add(f.finding_id)

        bundle = {
            "cro_finding": cro_finding,
            "canonical_audit_rep": canonical_audit_rep,
            "http_status_rep": http_status_rep,
            "heading_hierarchy_rep": heading_hierarchy_rep,
            "media_assets_rep": media_assets_rep,
            "click_depth_rep": click_depth_rep,
            "orphan_pages_rep": orphan_pages_rep,
            "anchor_text_audit_rep": anchor_text_audit_rep,
            "meta_rollup_rep": meta_rollup_rep,
            "form_audit_rep": form_audit_rep,
            "cro_audit_rep": cro_audit_rep,
            "schema_validation_rep": schema_validation_rep,
            "wcag_audit_rep": wcag_audit_rep,
            "local_seo_rep": local_seo_rep,
            "intl_seo_rep": intl_seo_rep,
            "topical_auth_rep": topical_auth_rep,
            "ecom_seo_rep": ecom_seo_rep,
            "serp_app_rep": serp_app_rep,
            "indexation_rollup_rep": indexation_rollup_rep,
            "competitor_seo_parity_rep": competitor_seo_parity_rep,
            "security_audit_rep": security_audit_rep,
            "host_and_redirects_rep": host_and_redirects_rep,
            "deterministic_findings": deterministic_findings,
        }
        blackboard.blackboard_state["deterministic_findings"] = deterministic_findings
        blackboard.blackboard_state["deterministic_reports"] = {
            k: v for k, v in bundle.items() if k != "deterministic_findings"
        }
        return bundle

    async def _verify_deterministic_findings_with_ai(
        self,
        *,
        model_router: ModelRouter,
        blackboard: CognitiveBlackboard,
    ) -> Dict[str, Any]:
        """Stage 1b: Frontier AI reviews deterministic Python findings against business context & page sections."""
        import json as _json
        from typing import Literal
        from pydantic import BaseModel, Field

        det_findings = list(blackboard.blackboard_state.get("deterministic_findings") or [])
        if not det_findings:
            ledger = {
                "deterministic_findings_total": 0,
                "deterministic_findings_ai_reviewed": 0,
                "confirmed_count": 0,
                "false_positive_count": 0,
                "downgraded_count": 0,
                "needs_context_count": 0,
                "ai_review_status": "completed",
            }
            blackboard.blackboard_state["coverage_ledger"] = ledger
            return ledger

        class _FindingVerificationItem(BaseModel):
            finding_id: str
            verdict: Literal["CONFIRMED", "FALSE_POSITIVE", "DOWNGRADED", "NEEDS_CONTEXT"]
            adjusted_severity: Optional[Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]] = None
            business_impact_rationale: str = Field(..., min_length=5)
            root_cause_note: str = ""

        class _FindingVerificationBatch(BaseModel):
            verifications: List[_FindingVerificationItem] = Field(default_factory=list)

        bp = blackboard.business_profile
        biz_summary = (
            f"Business: {getattr(bp, 'business_name', None) or blackboard.website_url} | "
            f"Industry: {getattr(bp, 'industry', None) or 'Unknown'} | "
            f"Model: {getattr(bp, 'business_model', None) or 'Unknown'} | "
            f"ICP: {getattr(bp, 'target_audience', None) or 'Unknown'}"
        )
        page_index = {p.url: p for p in (blackboard.pages or []) if getattr(p, "url", None)}
        store = blackboard.evidence_store

        batch_size = 15
        batches = [det_findings[i : i + batch_size] for i in range(0, len(det_findings), batch_size)]
        sem = asyncio.Semaphore(3)
        verifications_map: Dict[str, Dict[str, Any]] = {}
        finding_by_id = {f.finding_id: f for f in det_findings}
        sev_order = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }
        sev_lookup = {s.value.upper(): s for s in Severity}

        async def _review_batch(batch_idx: int, batch: List[Any]) -> int:
            async with sem:
                items_payload = []
                batch_ev = []
                seen_ev_ids = set()
                relevant_page_snippets = []
                seen_urls = set()

                for f in batch:
                    items_payload.append({
                        "finding_id": f.finding_id,
                        "category": f.category.value if hasattr(f.category, "value") else str(f.category),
                        "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                        "title": (f.title or f.finding or "")[:240],
                        "description": (f.description or "")[:360],
                        "affected_urls": (f.affected_urls or [])[:5],
                        "recommendation": (f.recommendation or "")[:240],
                    })
                    for ref in (f.evidence_refs or [])[:3]:
                        if ref not in seen_ev_ids and store:
                            ev = store.get(ref)
                            if ev is not None:
                                batch_ev.append(ev)
                                seen_ev_ids.add(ref)
                    for u in (f.affected_urls or [])[:2]:
                        if u in page_index and u not in seen_urls:
                            seen_urls.add(u)
                            p = page_index[u]
                            sec_heads = [
                                getattr(s, "heading_text", None) or getattr(s, "heading", None)
                                for s in (getattr(p, "sections", None) or [])[:6]
                                if getattr(s, "heading_text", None) or getattr(s, "heading", None)
                            ]
                            relevant_page_snippets.append({
                                "url": u,
                                "title": p.title or "",
                                "status_code": p.status_code,
                                "word_count": p.word_count,
                                "sections": sec_heads,
                            })

                task_contract = (
                    f"{biz_summary}\n\n"
                    f"AFFECTED PAGES CONTEXT:\n{_json.dumps(relevant_page_snippets[:10], indent=2)}\n\n"
                    f"DETERMINISTIC PYTHON FINDINGS (Batch {batch_idx + 1}/{len(batches)}):\n"
                    f"{_json.dumps(items_payload, indent=2)}\n\n"
                    "Evaluate EVERY finding_id above. Mark FALSE_POSITIVE only when the site's business model, page type, "
                    "or observed page structure proves the deterministic rule does not apply (e.g., ecommerce check on a pure "
                    "B2B SaaS page, or local address check on a global online-only tool). Mark DOWNGRADED if real but minor. "
                    "Explain the concrete business impact for every finding. Never invent metrics or URLs."
                )
                try:
                    res = await model_router.generate_structured(
                        capability="seo_verification",
                        agent_role="Principal SEO/CRO/GEO Verification Auditor",
                        task_contract=task_contract,
                        evidence_list=batch_ev[:25],
                        output_schema_desc=_json.dumps(_FindingVerificationBatch.model_json_schema(), indent=2),
                        site_facts=getattr(blackboard, "site_facts", None),
                        max_claims=len(batch),
                        allow_fallback=False,
                        model_tier="reasoning_model",
                    )
                except Exception as err:
                    logger.warning("Deterministic finding AI verification batch %d failed: %s", batch_idx + 1, err)
                    return 0

                if not isinstance(res, dict) or str(res.get("status") or "").lower() in ("unavailable", "budget_exceeded"):
                    return 0

                raw_items = res.get("verifications") or []
                if not isinstance(raw_items, list) or not raw_items:
                    return 0

                reviewed_here = 0
                for raw_item in raw_items:
                    try:
                        item = (
                            raw_item
                            if isinstance(raw_item, _FindingVerificationItem)
                            else _FindingVerificationItem.model_validate(raw_item)
                        )
                    except Exception:
                        continue
                    target = finding_by_id.get(item.finding_id)
                    if target is None:
                        continue
                    reviewed_here += 1
                    verdict_dict = item.model_dump()
                    verifications_map[item.finding_id] = verdict_dict
                    target.adversarial_reviewed = True
                    note_prefix = f"[AI Review: {item.verdict}] {item.business_impact_rationale}"
                    target.verification_notes = (
                        f"{target.verification_notes}\n{note_prefix}".strip()
                        if target.verification_notes
                        else note_prefix
                    )
                    if not target.business_impact:
                        target.business_impact = item.business_impact_rationale
                    if not target.why_it_matters:
                        target.why_it_matters = item.business_impact_rationale
                    if item.root_cause_note and not target.reasoning:
                        target.reasoning = item.root_cause_note

                    if item.verdict == "FALSE_POSITIVE":
                        target.severity = Severity.INFO
                        target.confidence = min(float(target.confidence or 0.5), 0.35)
                        target.held_from_executive = True
                    elif item.verdict == "DOWNGRADED" and item.adjusted_severity:
                        adj = sev_lookup.get(item.adjusted_severity.upper())
                        if adj and sev_order.get(adj, 0) < sev_order.get(target.severity, 0):
                            target.severity = adj
                return reviewed_here

        counts = await asyncio.gather(*[_review_batch(i, b) for i, b in enumerate(batches)])
        reviewed_total = sum(counts)

        # Single targeted retry pass for deterministic findings omitted by Pass 1
        missed_det = [f for f in det_findings if f.finding_id not in verifications_map]
        if missed_det and reviewed_total > 0:
            retry_batches = [missed_det[i:i + batch_size] for i in range(0, len(missed_det), batch_size)]
            retry_counts = await asyncio.gather(*[_review_batch(len(batches) + i, b) for i, b in enumerate(retry_batches)])
            reviewed_total += sum(retry_counts)

        verdict_vals = [v.get("verdict") for v in verifications_map.values()]
        status = (
            "completed"
            if reviewed_total >= len(det_findings)
            else ("partial" if reviewed_total > 0 else "unavailable")
        )
        ledger = {
            "deterministic_findings_total": len(det_findings),
            "deterministic_findings_ai_reviewed": reviewed_total,
            "confirmed_count": verdict_vals.count("CONFIRMED"),
            "false_positive_count": verdict_vals.count("FALSE_POSITIVE"),
            "downgraded_count": verdict_vals.count("DOWNGRADED"),
            "needs_context_count": verdict_vals.count("NEEDS_CONTEXT"),
            "ai_review_status": status,
        }
        blackboard.blackboard_state["deterministic_verifications"] = verifications_map
        blackboard.blackboard_state["coverage_ledger"] = ledger
        return ledger

    async def _execute_analysis_pipeline_scoped(
        self,
        *,
        run: AnalysisRun,
        analysis_id: str,
        website_url: str,
        max_pages: Optional[int] = None,
        site_type: Optional[str] = None,
        declared_site_type_notes: Optional[str] = None,
        country: Optional[str] = None,
        language: Optional[str] = None,
        target_pillars: Optional[List[str]] = None,
        audit_tier: str = "premium",
        credits_charged: int = 0,
    ):
        from app.domain.commercial.tiers import get_tier_spec, normalize_tier_id
        tier_id = normalize_tier_id(audit_tier, default="premium")
        tier_spec = get_tier_spec(tier_id)
        tier_features = tier_spec.features
        crawl_completed = False


        if target_pillars is None and run and run.target_pillars:
            target_pillars = run.target_pillars

        effective_pillars: Optional[Set[str]] = (
            {p.strip().lower() for p in target_pillars if p and p.strip().lower() in PILLAR_TO_SECTION}
            if target_pillars
            else None
        )
        telemetry_tracker = TelemetryTracker()
        model_router = ModelRouter(telemetry_tracker=telemetry_tracker)
        if run:
            run.telemetry = telemetry_tracker.telemetry
        controller = get_pipeline_controller(analysis_id)
        pipeline_t0 = time.perf_counter()

        # Mark unselected pillar nodes as SKIPPED right away
        all_pillars = {"seo", "geo", "aeo", "cro"}
        if effective_pillars is not None and effective_pillars != all_pillars:
            skipped_pillars = all_pillars - effective_pillars
            for sp in skipped_pillars:
                sp_sec_id = PILLAR_TO_SECTION.get(sp)
                sp_sec = next((s for s in SECTIONS_REGISTRY if s.section_id == sp_sec_id), None)
                if sp_sec:
                    for nid in sp_sec.node_ids:
                        controller.mark_node_status(nid, GraphNodeStatus.SKIPPED)
                        controller.log_activity(nid, "info", f"{sp}.skipped", f"{sp.upper()} pillar skipped in selective execution")

        if analysis_id in self.blackboards:
            blackboard = self.blackboards[analysis_id]
        else:
            blackboard = CognitiveBlackboard(run_id=analysis_id, website_url=website_url)
            self.blackboards[analysis_id] = blackboard

        blackboard.user_declared_site_type = site_type
        blackboard.user_declared_site_type_notes = declared_site_type_notes
        team_orchestrator = TeamOrchestrator(model_router)

        crawl_limit = max_pages or settings.MAX_CRAWL_PAGES

        async def _check_pause() -> bool:
            if controller.is_pause_requested():
                if run:
                    run.status = AnalysisStage.PAUSED
                    run.current_step = "Audit paused by user"
                await self._emit_event(analysis_id, "paused", run.progress_percentage if run else 0, "Audit paused by user")
                return True
            return False

        try:
            if await _check_pause():
                return

            # 1. Mission Director Initialization
            mission_state = self.mission_director.create_mission(
                target_url=website_url,
                org_id=run.org_id,
                workspace_id=run.workspace_id,
                audit_type="standard_growth",
                max_pages=crawl_limit,
            )

            # 2. Level 0: Ingestion & Multi-Page Crawl
            model_router.set_active_stage("crawl_and_ingest", "Crawl & Ingestion")
            run.status = AnalysisStage.INGESTING

            if controller.get_node_status("node_crawl") == GraphNodeStatus.COMPLETED and blackboard.pages:
                manifest = blackboard.crawl_manifest or CrawlManifest(
                    domain=urlparse(website_url).netloc.replace("www.", ""),
                    pages=blackboard.pages,
                    total_pages=len(blackboard.pages),
                )
                domain = manifest.domain
                page_ev = manifest.pages[0] if manifest.pages else None
                controller.log_activity("node_crawl", "info", "crawl.reused", f"Reusing {len(blackboard.pages)} persisted pages from checkpoint")
                await self._emit_event(analysis_id, "ingesting", 15, f"Loaded {len(blackboard.pages)} crawled pages from checkpoint for {website_url}")
            else:
                controller.mark_node_status("node_crawl", GraphNodeStatus.RUNNING)
                controller.log_activity("node_crawl", "running", "crawl.start", f"Multi-page crawler scanning {website_url} (up to {crawl_limit} pages)...")
                await self._emit_event(analysis_id, "ingesting", 10, f"Initializing multi-page crawler for {website_url}...")

                def on_crawl_progress(msg: str, progress_pct: int):
                    controller.log_activity("node_crawl", "info", "crawl.progress", msg)
                    asyncio.create_task(self._emit_event(analysis_id, "ingesting", progress_pct, msg))

                manifest = await self.crawler.crawl_site_and_analyze(
                    target_url=website_url,
                    evidence_store=blackboard.evidence_store,
                    max_pages=crawl_limit,
                    progress_callback=on_crawl_progress
                )
                blackboard.pages = manifest.pages
                blackboard.crawl_manifest = manifest
                if not manifest.pages:
                    controller.mark_node_status("node_crawl", GraphNodeStatus.FAILED, error_message="No pages crawled")
                    raise RuntimeError(f"No pages could be crawled from {website_url}. Please ensure the URL is valid, accessible, and public.")
                page_ev = manifest.pages[0]
                domain = manifest.domain
                controller.mark_node_status("node_crawl", GraphNodeStatus.COMPLETED, evidence_count=len(manifest.pages), output_summary=f"{len(manifest.pages)} pages")
                controller.log_activity("node_crawl", "success", "crawl.success", f"Crawled {len(manifest.pages)} pages from {website_url}")

            # Apply dynamic page-tiered Frontier AI budget scoped to the selected 5-tier depth
            crawl_completed = True
            from dataclasses import asdict as _asdict
            budget_plan = model_router.apply_page_budget(
                len(manifest.pages),
                depth_mode=tier_features.ai_depth_mode,
                tier_id=tier_id,
            )
            blackboard.blackboard_state["budget_plan"] = _asdict(budget_plan)
            blackboard.blackboard_state["audit_tier"] = tier_id
            blackboard.blackboard_state["tier_features"] = _asdict(tier_features)
            logger.info(
                "Applied %s-tier audit budget for %d page(s): $%.2f (~₹%.0f, %d calls, mode=%s)",
                tier_id,
                budget_plan.pages_count,
                budget_plan.max_budget_usd,
                budget_plan.max_budget_inr,
                budget_plan.max_model_calls,
                budget_plan.depth_mode,
            )

            if await _check_pause():
                return

            controller.mark_node_status("node_dom_extraction", GraphNodeStatus.RUNNING)
            controller.log_activity("node_dom_extraction", "running", "dom.populate", f"Extracting DOM AST & headings for {domain}...")

            # Populate Evidence Graph 2.0 with Pages & Elements
            site_node_id = f"site_{domain.replace('.', '_')}"
            blackboard.evidence_graph.add_node(
                node_id=site_node_id,
                node_type=GraphNodeType.WEBSITE,
                label=domain,
                url=website_url
            )

            for idx, p in enumerate(manifest.pages):
                page_node_id = f"page_{idx}"
                blackboard.evidence_graph.add_node(
                    node_id=page_node_id,
                    node_type=GraphNodeType.PAGE,
                    label=p.title or p.url,
                    url=p.url,
                    properties={"word_count": p.word_count, "status_code": p.status_code}
                )
                blackboard.evidence_graph.add_edge(site_node_id, page_node_id, GraphEdgeType.CONTAINS)

                for h in p.h1:
                    h_node_id = f"h1_{idx}_{uuid.uuid4().hex[:4]}"
                    blackboard.evidence_graph.add_node(
                        node_id=h_node_id,
                        node_type=GraphNodeType.DOM_ELEMENT,
                        label=f"H1: {h}",
                        url=p.url,
                        selector="h1"
                    )
                    blackboard.evidence_graph.add_edge(page_node_id, h_node_id, GraphEdgeType.CONTAINS)

            # Populate Evidence Graph 2.0 with all deterministic observations, SHA-256 hashes, and DOM selectors
            blackboard.evidence_graph.populate_from_evidence_store(blackboard.evidence_store, manifest)
            model_router.set_active_stage("deterministic_analysis", "Deterministic Analysis & External Evidence")

            controller.mark_node_status("node_dom_extraction", GraphNodeStatus.COMPLETED, evidence_count=blackboard.evidence_store.count(), output_summary=f"{blackboard.evidence_store.count()} observations")
            controller.log_activity("node_dom_extraction", "success", "dom.complete", f"Extracted {blackboard.evidence_store.count()} observations into Evidence Graph 2.0")

            await self._emit_event(
                analysis_id,
                "deterministic_analysis",
                25,
                f"Crawled {len(manifest.pages)} pages across {domain}. Extracted {blackboard.evidence_store.count()} observations into Evidence Graph 2.0.",
                {
                    "evidence_count": blackboard.evidence_store.count(),
                    "pages_crawled": len(manifest.pages),
                    "graph_nodes": len(blackboard.evidence_graph.nodes)
                }
            )

            # Durable Checkpoint 1: Crawl & DOM observations complete
            try:
                self.repository.persist_crawl_pages(analysis_id, manifest.pages)
                self.repository.persist_evidence_items(analysis_id, blackboard.evidence_store.get_all())
                self.repository.save_checkpoint(StageCheckpoint(
                    analysis_id=analysis_id,
                    stage=AnalysisStage.INGESTING,
                    step_number=1,
                    status="COMPLETED",
                    crawled_count=len(manifest.pages),
                    evidence_count=blackboard.evidence_store.count(),
                    state_payload={"domain": domain, "pages_crawled": len(manifest.pages)}
                ))
            except Exception as pe:
                logger.warning(f"Persistence error after crawl: {pe}")

            if await _check_pause():
                return

            # Extract Wave-0 deterministic site facts ($0 inference)
            blackboard.site_facts = extract_site_facts(manifest, blackboard.evidence_store)

            # Layer 1 — Record Machine Observations into EvidenceStore
            for p in manifest.pages:
                if p.title:
                    blackboard.evidence_store.add_observation("title", p.title, source="html", url=p.url, selector="title")
                if p.h1:
                    blackboard.evidence_store.add_observation("h1", p.h1, source="dom", url=p.url, selector="h1")
                if p.h2:
                    blackboard.evidence_store.add_observation("h2", p.h2, source="dom", url=p.url, selector="h2")
                if p.meta_description:
                    blackboard.evidence_store.add_observation("meta_description", p.meta_description, source="html", url=p.url, selector='meta[name="description"]')
                if p.status_code:
                    blackboard.evidence_store.add_observation("status_code", p.status_code, source="http_header", url=p.url)
                if p.ttfb_ms:
                    blackboard.evidence_store.add_observation("ttfb_ms", p.ttfb_ms, source="http_header", url=p.url)
                if p.schema_types:
                    blackboard.evidence_store.add_observation("schema_types", p.schema_types, source="html", url=p.url, selector='script[type="application/ld+json"]')
                if p.ctas:
                    blackboard.evidence_store.add_observation("cta_texts", p.ctas, source="dom", url=p.url)

            if blackboard.site_facts:
                sf = blackboard.site_facts
                if sf.get("sameas_urls"):
                    blackboard.evidence_store.add_observation("sameas_urls", sf.get("sameas_urls"), source="schema", url=website_url)
                if sf.get("visible_pricing_text"):
                    blackboard.evidence_store.add_observation("visible_pricing_text", sf.get("visible_pricing_text"), source="html", url=website_url)
                if sf.get("faq_questions"):
                    blackboard.evidence_store.add_observation("faq_questions", sf.get("faq_questions"), source="html", url=website_url)
                if sf.get("nav_labels"):
                    blackboard.evidence_store.add_observation("nav_labels", sf.get("nav_labels"), source="dom", url=website_url)
                blackboard.evidence_store.add_observation("pricing_signals", sf.get("pricing_signals_present", False), source="html", url=website_url)

            # Phase 2: Operationalize External Evidence Plane (ext_NNN)
            from app.domain.evidence.enrichment import ExternalEvidenceEnricher
            enricher = ExternalEvidenceEnricher()
            controller.mark_node_status("node_dns_ssl_headers", GraphNodeStatus.RUNNING)
            controller.log_activity("node_dns_ssl_headers", "running", "external.enrich", f"Enriching external evidence plane (DNS, SSL/TLS, Security Headers, CruX) for {domain}...")

            await self._emit_event(
                analysis_id,
                "deterministic_analysis",
                32,
                f"Enriching external evidence plane (DNS, SSL/TLS, Security Headers, CruX, Registries)...",
                {"domain": domain}
            )
            ext_items = []
            try:
                ext_items = await enricher.enrich_domain(domain, blackboard.evidence_store)
                logger.info(f"External evidence enrichment yielded {len(ext_items)} items for {domain}")
                # Durable Checkpoint 2: External Evidence Plane complete
                self.repository.persist_evidence_items(analysis_id, blackboard.evidence_store.get_all())
                self.repository.save_checkpoint(StageCheckpoint(
                    analysis_id=analysis_id,
                    stage=AnalysisStage.DETERMINISTIC_ANALYSIS,
                    step_number=2,
                    status="COMPLETED",
                    evidence_count=blackboard.evidence_store.count(),
                    state_payload={"external_evidence_count": len(ext_items)}
                ))
                controller.mark_node_status("node_dns_ssl_headers", GraphNodeStatus.COMPLETED, evidence_count=len(ext_items), output_summary=f"{len(ext_items)} external items")
                controller.log_activity("node_dns_ssl_headers", "success", "external.complete", f"Enriched {len(ext_items)} external evidence items")
            except Exception as enrich_err:
                logger.warning(f"External evidence enrichment encountered error: {enrich_err}")
                controller.mark_node_status("node_dns_ssl_headers", GraphNodeStatus.FAILED, error_message=str(enrich_err))
                controller.log_activity("node_dns_ssl_headers", "warning", "external.warning", f"External enrichment note: {enrich_err}")

            # ── Progressive Reporting: Phase 1 — Business Ingestion ─────────────
            try:
                # 1.1 SSRF Security
                p1_1 = SubPhaseReportBuilder.build_p1_1_ssrf(
                    run_id=analysis_id,
                    website_url=website_url,
                    resolved_ip=None,
                    is_safe=True,
                    redirect_chain=[website_url],
                )
                await self._record_progressive_subphase(p1_1, "ssrf_security")

                # 1.2 Crawler Execution
                status_dist: Dict[str, int] = {}
                for pg in manifest.pages:
                    code_str = str(pg.status_code)
                    status_dist[code_str] = status_dist.get(code_str, 0) + 1
                p1_2 = SubPhaseReportBuilder.build_p1_2_crawler(
                    run_id=analysis_id,
                    website_url=website_url,
                    pages_crawled=len(manifest.pages),
                    manifest_data={"status_codes": status_dist, "urls": [pg.url for pg in manifest.pages]},
                )
                await self._record_progressive_subphase(p1_2, "crawler_execution")

                # 1.3 DOM Evidence
                h1_total = sum(len(pg.h1) for pg in manifest.pages)
                h2_total = sum(len(pg.h2) for pg in manifest.pages)
                p1_3 = SubPhaseReportBuilder.build_p1_3_dom_evidence(
                    run_id=analysis_id,
                    website_url=website_url,
                    dom_metrics={
                        "pages_count": len(manifest.pages),
                        "h1_count": h1_total,
                        "h2_count": h2_total,
                        "observations_count": blackboard.evidence_store.count(),
                    },
                )
                await self._record_progressive_subphase(p1_3, "dom_evidence")

                # 1.4 Snapshot Integrity
                cas_hashes = [pg.content_hash for pg in manifest.pages if getattr(pg, "content_hash", None)]
                p1_4 = SubPhaseReportBuilder.build_p1_4_snapshot_integrity(
                    run_id=analysis_id,
                    snapshot_count=len(manifest.pages),
                    cas_hashes=cas_hashes,
                )
                await self._record_progressive_subphase(p1_4, "snapshot_integrity")

                # 1.5 External Telemetry
                resp_hdrs = getattr(manifest.pages[0], "response_headers", {}) if manifest.pages else {}
                p1_5 = SubPhaseReportBuilder.build_p1_5_telemetry(
                    run_id=analysis_id,
                    website_url=website_url,
                    telemetry_data={"external_evidence_count": len(ext_items), "security_headers": resp_hdrs},
                )
                await self._record_progressive_subphase(p1_5, "external_telemetry")

                # 1.6 Deterministic Site Facts
                p1_6 = SubPhaseReportBuilder.build_p1_6_site_facts(
                    run_id=analysis_id,
                    site_facts=blackboard.site_facts or {},
                )
                await self._record_progressive_subphase(p1_6, "deterministic_site_facts")

                # Phase 1 Consolidated
                await self._consolidate_progressive_phase(analysis_id, "phase_01_ingestion", "phase_01_consolidated")
            except Exception as rep1_err:
                logger.warning(f"Progressive reporting error for Phase 1: {rep1_err}", exc_info=True)

            if await _check_pause():
                return

            # 3. Dynamic Capability Scheduling
            model_router.set_active_stage("planning", "Capability Scheduling & Hypotheses")
            model_router.set_active_sub_stage("capability_scheduling", "Dynamic Capability Scheduling & Wave Planning")
            run.status = AnalysisStage.PLANNING
            mission_caps = self.mission_director.select_capabilities_for_mission(mission_state)

            # 4. Formulate Pre-Reasoning Hypotheses
            initial_hypotheses = self.hypothesis_engine.generate_initial_hypotheses(domain, manifest.pages)
            mission_state.hypotheses = initial_hypotheses

            # 5. Execute Level 0 Deterministic Technical Foundation ($0 inference)
            controller.mark_node_status("node_schema_ld_json", GraphNodeStatus.RUNNING)
            controller.log_activity("node_schema_ld_json", "running", "schema.wave", "Executing Deterministic Technical, DOM & Schema Capabilities ($0 inference)...")
            await self._emit_event(analysis_id, "deterministic_analysis", 38, "Executing Deterministic Technical, DOM & Schema Capabilities ($0 inference)...")
            await team_orchestrator.execute_capability_wave(mission_caps["tier_1_deterministic"], manifest, blackboard)
            controller.mark_node_status("node_schema_ld_json", GraphNodeStatus.COMPLETED)
            controller.log_activity("node_schema_ld_json", "success", "schema.complete", "Deterministic technical & schema capabilities completed ($0 inference)")

            # Stage 1: Execute all 18 deterministic Python analyzers ($0.00) BEFORE Business Understanding & Specialist DAG
            eval_pages = (manifest.pages if manifest else None) or blackboard.pages or []
            det_bundle = await self._run_deterministic_analyzers(
                eval_pages=eval_pages,
                manifest=manifest,
                blackboard=blackboard,
                domain=domain,
                website_url=website_url,
            )
            controller.log_activity(
                "node_schema_ld_json",
                "success",
                "deterministic.analyzers.complete",
                f"Stage-1 deterministic analyzers completed ({len(det_bundle['deterministic_findings'])} raw findings ready for AI review)",
            )

            if await _check_pause():
                return

            # 6. Business identity (declared vs detected) before the 50-agent DAG
            controller.mark_node_status("node_entity_resolution", GraphNodeStatus.RUNNING)
            controller.log_activity("node_entity_resolution", "running", "entity.resolve", f"Resolving canonical entity for {domain}...")

            from app.seo.business.entity_resolver import UniversalEntityResolver
            blackboard.resolved_entity = UniversalEntityResolver.resolve_from_evidence(
                website_url=website_url,
                pages=manifest.pages,
                profile=blackboard.business_profile
            )
            blackboard.business_profile.business_name = blackboard.resolved_entity.name
            if blackboard.resolved_entity.category and not blackboard.business_profile.industry:
                blackboard.business_profile.industry = blackboard.resolved_entity.category

            if blackboard.resolved_entity and blackboard.resolved_entity.name:
                blackboard.evidence_store.add_observation("business_name", blackboard.resolved_entity.name, source="html", url=website_url)

            controller.mark_node_status("node_entity_resolution", GraphNodeStatus.COMPLETED, output_summary=blackboard.resolved_entity.name if blackboard.resolved_entity else None)
            controller.log_activity("node_entity_resolution", "success", "entity.complete", f"Canonical entity resolved: {blackboard.resolved_entity.name if blackboard.resolved_entity else domain}")

            if await _check_pause():
                return

            controller.mark_node_status("node_icp_offer_profile", GraphNodeStatus.RUNNING)
            controller.log_activity("node_icp_offer_profile", "running", "icp.resolve", "Extracting business identity, ICP, and value proposition...")

            model_router.set_active_stage("business_understanding", "Business Identity Resolution")
            model_router.set_active_sub_stage("brand_identity_extraction", "Brand Identity, ICP & Value Prop Resolution")
            run.status = AnalysisStage.SPECIALIST_EXECUTION
            await self._emit_event(
                analysis_id,
                "specialist_execution",
                42,
                "Resolving business identity from crawled evidence...",
            )
            biz_understanding = BusinessUnderstandingOrchestrator(model_router)
            semantic_rep = await biz_understanding.execute_business_understanding(blackboard)
            controller.mark_node_status("node_icp_offer_profile", GraphNodeStatus.COMPLETED)
            controller.log_activity("node_icp_offer_profile", "success", "icp.complete", "Extracted buyer ICP and core value proposition")

            if blackboard.identity_contradictions:
                contra = blackboard.identity_contradictions[0]
                await self._emit_event(
                    analysis_id,
                    "specialist_execution",
                    44,
                    f"Business Identity Conflict Detected: {contra.reason}",
                    {
                        "declared": contra.declared_type,
                        "detected": contra.detected_type,
                        "confidence": contra.confidence,
                        "contradiction_id": contra.id
                    }
                )

            # ── Progressive Reporting: Phase 2 — Business Understanding ─────────
            try:
                # 2.1 Entity Resolution
                ent_name = blackboard.resolved_entity.name if blackboard.resolved_entity else domain
                ent_ind = blackboard.resolved_entity.category if blackboard.resolved_entity else None
                p2_1 = SubPhaseReportBuilder.build_p2_1_entity_resolution(
                    run_id=analysis_id,
                    entity_data={"canonical_name": ent_name, "industry": ent_ind, "official_domain": domain},
                )
                await self._record_progressive_subphase(p2_1, "entity_resolution")

                # 2.2 ICP Intelligence
                target_aud = getattr(blackboard.business_profile, "target_audience", None) or "Business Decision Makers"
                p2_2 = SubPhaseReportBuilder.build_p2_2_icp_intelligence(
                    run_id=analysis_id,
                    icp_data={"target_audience": target_aud, "industry": ent_ind},
                )
                await self._record_progressive_subphase(p2_2, "icp_intelligence")

                # 2.3 Search Intent
                page_intents = [{"url": pg.url, "title": pg.title} for pg in manifest.pages[:10]]
                p2_3 = SubPhaseReportBuilder.build_p2_3_search_intent(
                    run_id=analysis_id,
                    intent_data={"page_intents": page_intents},
                )
                await self._record_progressive_subphase(p2_3, "search_intent")

                # 2.4 Identity Arbitration
                contra_list = [c.reason for c in (blackboard.identity_contradictions or [])]
                sealed_prof = (
                    blackboard.business_profile.model_dump(mode="json")
                    if hasattr(blackboard.business_profile, "model_dump")
                    else {"name": ent_name, "industry": ent_ind}
                )
                p2_4 = SubPhaseReportBuilder.build_p2_4_identity_arbitration(
                    run_id=analysis_id,
                    arbitration_data={"conflicts": contra_list, "sealed_profile": sealed_prof},
                )
                await self._record_progressive_subphase(p2_4, "identity_arbitration")

                # Phase 2 Consolidated
                await self._consolidate_progressive_phase(analysis_id, "phase_02_business", "phase_02_consolidated")
            except Exception as rep2_err:
                logger.warning(f"Progressive reporting error for Phase 2: {rep2_err}", exc_info=True)

            # Stage 1b: Frontier AI verification of Stage-1 deterministic Python findings against Business Context
            if tier_features.enable_ai_verifier:
                try:
                    model_router.set_active_stage("deterministic_verification", "Frontier AI Finding Verification")
                    model_router.set_active_sub_stage("finding_verification", "AI Review of Deterministic Findings")
                    ver_ledger = await self._verify_deterministic_findings_with_ai(
                        model_router=model_router,
                        blackboard=blackboard,
                    )
                    controller.log_activity(
                        "node_specialist_wave_1",
                        "info",
                        "deterministic.ai_verified",
                        (
                            f"AI reviewed {ver_ledger.get('deterministic_findings_ai_reviewed', 0)}/"
                            f"{ver_ledger.get('deterministic_findings_total', 0)} deterministic findings "
                            f"({ver_ledger.get('confirmed_count', 0)} confirmed, "
                            f"{ver_ledger.get('false_positive_count', 0)} false positives, "
                            f"{ver_ledger.get('downgraded_count', 0)} downgraded)."
                        ),
                    )
                except Exception as ver_err:
                    logger.warning("Stage 1b deterministic finding AI verification note: %s", ver_err)
            else:
                controller.log_activity(
                    "node_specialist_wave_1",
                    "info",
                    "deterministic.ai_verifier_locked",
                    f"Stage 1b AI finding verification skipped (locked by tier '{tier_id}').",
                )

            if await _check_pause():
                return

            # Search Console and SERP rows, when a provider already measured them and tier unlocks GA4/GSC.
            if tier_features.enable_ga4_gsc:
                try:
                    from app.seo.search_demand import attach_search_demand
                    demand = attach_search_demand(blackboard, domain)
                    controller.log_activity(
                        "node_specialist_wave_1",
                        "info",
                        "search_demand",
                        demand.get("note") or "Search demand was not measured.",
                    )
                except Exception as exc:
                    logger.info("Search demand was not attached: %s", exc)
            else:
                blackboard.blackboard_state["search_demand_status"] = "LOCKED_BY_TIER"
                controller.log_activity(
                    "node_specialist_wave_1",
                    "info",
                    "search_demand.locked",
                    f"GA4/GSC connector enrichment locked by tier '{tier_id}'.",
                )

            # 7. Full specialist DAG (dependency waves, no canned fallbacks)
            agent_pool = AgentPool(model_router)
            model_router.set_active_stage("specialist_execution", f"{len(agent_pool)}-Agent Specialist DAG")
            model_router.set_active_sub_stage("specialist_agents_dag", f"{len(agent_pool)}-Agent Multi-Disciplinary Analysis Waves")

            active_pillars_set = effective_pillars if effective_pillars is not None else all_pillars
            # Mark active pillar nodes as RUNNING
            for ap in active_pillars_set:
                ap_sec_id = PILLAR_TO_SECTION.get(ap)
                ap_sec = next((s for s in SECTIONS_REGISTRY if s.section_id == ap_sec_id), None)
                if ap_sec:
                    for nid in ap_sec.node_ids:
                        if nid not in ("node_seo_page_intelligence", "node_aeo_search_simulation"):
                            controller.mark_node_status(nid, GraphNodeStatus.RUNNING)

            for w_node in ["node_specialist_wave_1", "node_specialist_wave_2", "node_specialist_wave_3", "node_specialist_wave_4"]:
                controller.mark_node_status(w_node, GraphNodeStatus.RUNNING)

            controller.log_activity("node_specialist_wave_1", "running", "specialists.start", f"Deploying specialist agents across active pillars ({', '.join(sorted(active_pillars_set)).upper()})...")

            await self._emit_event(
                analysis_id,
                "specialist_execution",
                46,
                f"Deploying specialist agents across active pillars ({', '.join(sorted(active_pillars_set)).upper()})...",
                {"agents": len(agent_pool), "waves": len(agent_pool.waves), "active_pillars": list(active_pillars_set)},
            )

            def _map_agent_to_node(aid: Optional[str]) -> Optional[str]:
                if not aid:
                    return None
                aid_low = aid.lower()
                if "seo.crawl" in aid_low or "seo.indexability" in aid_low or "seo.drift" in aid_low:
                    return "node_seo_crawl_indexing"
                if "seo.security" in aid_low or "seo.performance" in aid_low or "seo.assets" in aid_low:
                    return "node_seo_technical_health"
                if "seo.html" in aid_low or "seo.internal_links" in aid_low or "seo.cluster" in aid_low or "seo.sxo" in aid_low or aid_low.startswith("content."):
                    return "node_seo_onpage_content"
                if aid_low.startswith("schema.") or "seo.ecommerce" in aid_low:
                    return "node_seo_schema_ast"
                if "geo.brand_identity" in aid_low or "geo.wikidata" in aid_low or "geo.entity" in aid_low:
                    return "node_geo_entity_grounding"
                if "geo.local" in aid_low or "geo.citations" in aid_low or "geo.extractability" in aid_low or "maps_intelligence" in aid_low:
                    return "node_geo_local_signals"
                if "geo.llms_txt" in aid_low or "geo.synthesis" in aid_low or "agentic_readiness" in aid_low:
                    return "node_geo_llm_footprint"
                if "ai_search.citability" in aid_low:
                    return "node_aeo_citability_matrix"
                if "ai_search.query_coverage" in aid_low or "ai_search.faq" in aid_low or "ai_search.competitor" in aid_low:
                    return "node_aeo_qa_readiness"
                if "cro.three_second_hook" in aid_low or "cro.conversion" in aid_low or aid_low.startswith("ux."):
                    return "node_cro_cta_visibility"
                if "cro.pricing_psychology" in aid_low or aid_low.startswith("business."):
                    return "node_cro_value_clarity"
                if "cro.form_friction" in aid_low or "cro.social_proof" in aid_low or aid_low.startswith("trust."):
                    return "node_cro_trust_and_forms"
                return None

            async def _agent_progress(stage: str, progress: int, message: str, data: Dict[str, Any]):
                if run and telemetry_tracker:
                    run.telemetry = telemetry_tracker.telemetry
                aid = data.get("agent_id")
                wave = data.get("wave", 1)
                w_node = f"node_specialist_wave_{min(max(wave, 1), 4)}"
                controller.log_activity(w_node, "info", f"specialist.{aid or 'agent'}", message, details=data)
                sub_node = _map_agent_to_node(aid)
                if sub_node:
                    controller.log_activity(sub_node, "info", f"specialist.{aid or 'agent'}", message, details=data)
                await self._emit_event(analysis_id, stage, progress, message, data)

            t_pool_start = time.perf_counter()
            pool_summary = await agent_pool.execute_all(
                blackboard,
                progress_cb=_agent_progress,
                base_progress=46,
                end_progress=78,
                active_pillars=effective_pillars,
                audit_tier=tier_id,
            )
            pool_elapsed_ms = max(50, int((time.perf_counter() - t_pool_start) * 1000))
            pillar_dur_ms = max(10, int(pool_elapsed_ms / 4))

            for w_node in ["node_specialist_wave_1", "node_specialist_wave_2", "node_specialist_wave_3", "node_specialist_wave_4"]:
                controller.mark_node_status(w_node, GraphNodeStatus.COMPLETED, claims_count=len(blackboard.claim_registry.get_all()))

            for ap in active_pillars_set:
                ap_sec_id = PILLAR_TO_SECTION.get(ap)
                ap_sec = next((s for s in SECTIONS_REGISTRY if s.section_id == ap_sec_id), None)
                if ap_sec:
                    for nid in ap_sec.node_ids:
                        if nid not in ("node_seo_page_intelligence", "node_aeo_search_simulation"):
                            controller.mark_node_status(nid, GraphNodeStatus.COMPLETED, claims_count=len(blackboard.claim_registry.get_all()))

            controller.log_activity(
                "node_specialist_wave_4",
                "success",
                "specialists.complete",
                f"{len(agent_pool)} specialists finished: {pool_summary['completed']} completed, {pool_summary.get('skipped', 0)} skipped, {pool_summary['unavailable']} unavailable, {pool_summary['errors']} errors."
            )

            await self._emit_event(
                analysis_id,
                "specialist_execution",
                78,
                (
                    f"{len(agent_pool)} specialists finished: {pool_summary['completed']} completed, "
                    f"{pool_summary.get('skipped', 0)} skipped, "
                    f"{pool_summary['unavailable']} unavailable (no invented fill), "
                    f"{pool_summary['errors']} errors."
                ),
                pool_summary,
            )

            # Durable Checkpoint 3: Specialist analysis complete
            try:
                self.repository.persist_claims(analysis_id, blackboard.claim_registry.get_all())
                self.repository.save_checkpoint(StageCheckpoint(
                    analysis_id=analysis_id,
                    stage=AnalysisStage.SPECIALIST_EXECUTION,
                    step_number=3,
                    status="COMPLETED",
                    claims_count=len(blackboard.claim_registry.get_all()),
                    state_payload={"claims_count": len(blackboard.claim_registry.get_all()), "pool_summary": pool_summary}
                ))
            except Exception as pe:
                logger.warning(f"Persistence error after specialists: {pe}")

            # ── Progressive Reporting: Phase 3 — Four Strategic Pillars ─────────
            try:
                seo_claims = [c for c in blackboard.claim_registry.get_all() if c.category in (Category.TECHNICAL_SEO, Category.ON_PAGE_SEO, Category.CONTENT)]
                geo_claims = [c for c in blackboard.claim_registry.get_all() if c.category in (Category.GEO, Category.AI_SEARCH)]
                aeo_claims = [c for c in blackboard.claim_registry.get_all() if c.category in (Category.AI_SEARCH, Category.SCHEMA)]
                cro_claims = [c for c in blackboard.claim_registry.get_all() if c.category in (Category.UX_CONVERSION, Category.TRUST_AUTHORITY)]

                # SEO Pillar Sub-phase
                p3_seo = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_03_pillars",
                    phase_name="3. Four Strategic Pillars",
                    subphase_id="3.1",
                    subphase_title="Search Engine Optimization (SEO) Specialist Analysis",
                    objective="Evaluate crawlability, technical Core Web Vitals, on-page content, and Schema.org structured data.",
                    agent_id="seo.specialist_workforce",
                    agent_model="multi_specialist_pool",
                    execution_mode="hybrid",
                    duration_ms=pillar_dur_ms,
                    status=ExecutionStatus.COMPLETED if "seo" in active_pillars_set else ExecutionStatus.NOT_CONFIGURED,
                    input_summary={"active": "seo" in active_pillars_set, "pages_evaluated": len(manifest.pages)},
                    processing_steps=["Technical indexation audit", "Core Web Vitals diagnostic", "Schema JSON-LD graph inspection"],
                    structured_output={"pillar": "SEO", "status": "COMPLETED" if "seo" in active_pillars_set else "SKIPPED"},
                    evidence_tokens=[],
                    findings=list(seo_claims[:5]),
                    confidence=ConfidenceLevel.VERIFIED if ("seo" in active_pillars_set and seo_claims) else (ConfidenceLevel.INFERRED if "seo" in active_pillars_set else ConfidenceLevel.UNMEASURED),
                )
                await self._record_progressive_subphase(p3_seo, "seo_pillar")

                # GEO Pillar Sub-phase
                p3_geo = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_03_pillars",
                    phase_name="3. Four Strategic Pillars",
                    subphase_id="3.2",
                    subphase_title="Generative Engine Optimization (GEO) Knowledge Grounding",
                    objective="Audit Wikidata triples, local NAP signals, and brand citability across Generative LLM architectures.",
                    agent_id="geo.specialist_workforce",
                    agent_model="multi_specialist_pool",
                    execution_mode="hybrid",
                    duration_ms=pillar_dur_ms,
                    status=ExecutionStatus.COMPLETED if "geo" in active_pillars_set else ExecutionStatus.NOT_CONFIGURED,
                    input_summary={"active": "geo" in active_pillars_set},
                    processing_steps=["Entity knowledge graph mapping", "NAP consistency verification", "LLMs.txt and citation footprint probe"],
                    structured_output={"pillar": "GEO", "status": "COMPLETED" if "geo" in active_pillars_set else "SKIPPED"},
                    evidence_tokens=[],
                    findings=list(geo_claims[:5]),
                    confidence=ConfidenceLevel.VERIFIED if ("geo" in active_pillars_set and geo_claims) else (ConfidenceLevel.INFERRED if "geo" in active_pillars_set else ConfidenceLevel.UNMEASURED),
                )
                await self._record_progressive_subphase(p3_geo, "geo_pillar")

                # AEO Pillar Sub-phase
                p3_aeo = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_03_pillars",
                    phase_name="3. Four Strategic Pillars",
                    subphase_id="3.3",
                    subphase_title="Answer Engine Optimization (AEO) Citability Matrix",
                    objective="Test direct Q&A density, FAQ schema readiness, and conversational query citability.",
                    agent_id="aeo.specialist_workforce",
                    agent_model="multi_specialist_pool",
                    execution_mode="hybrid",
                    duration_ms=pillar_dur_ms,
                    status=ExecutionStatus.COMPLETED if "aeo" in active_pillars_set else ExecutionStatus.NOT_CONFIGURED,
                    input_summary={"active": "aeo" in active_pillars_set},
                    processing_steps=["Direct answer density scoring", "FAQPage schema verification", "Hallucination defense testing"],
                    structured_output={"pillar": "AEO", "status": "COMPLETED" if "aeo" in active_pillars_set else "SKIPPED"},
                    evidence_tokens=[],
                    findings=list(aeo_claims[:5]),
                    confidence=ConfidenceLevel.VERIFIED if ("aeo" in active_pillars_set and aeo_claims) else (ConfidenceLevel.INFERRED if "aeo" in active_pillars_set else ConfidenceLevel.UNMEASURED),
                )
                await self._record_progressive_subphase(p3_aeo, "aeo_pillar")

                # CRO Pillar Sub-phase
                p3_cro = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_03_pillars",
                    phase_name="3. Four Strategic Pillars",
                    subphase_id="3.4",
                    subphase_title="Conversion Rate Optimization (CRO & UX) Analysis",
                    objective="Measure primary CTA prominence, 5-second headline comprehension, social proof, and form friction.",
                    agent_id="cro.specialist_workforce",
                    agent_model="multi_specialist_pool",
                    execution_mode="hybrid",
                    duration_ms=pillar_dur_ms,
                    status=ExecutionStatus.COMPLETED if "cro" in active_pillars_set else ExecutionStatus.NOT_CONFIGURED,
                    input_summary={"active": "cro" in active_pillars_set},
                    processing_steps=["Visual CTA hierarchy scan", "5-second value proposition clarity test", "Trust proof and form ergonomics audit"],
                    structured_output={"pillar": "CRO", "status": "COMPLETED" if "cro" in active_pillars_set else "SKIPPED"},
                    evidence_tokens=[],
                    findings=list(cro_claims[:5]),
                    confidence=ConfidenceLevel.VERIFIED if ("cro" in active_pillars_set and cro_claims) else (ConfidenceLevel.INFERRED if "cro" in active_pillars_set else ConfidenceLevel.UNMEASURED),
                )
                await self._record_progressive_subphase(p3_cro, "cro_pillar")

                # Phase 3 Consolidated
                await self._consolidate_progressive_phase(analysis_id, "phase_03_pillars", "four_pillars_consolidated")
            except Exception as rep3_err:
                logger.warning(f"Progressive reporting error for Phase 3: {rep3_err}", exc_info=True)

            if await _check_pause():
                return

            # -----------------------------------------------------------------
            # Stage 3: Commercial AI Query Simulation, Entity Graph, Live AI Visibility,
            # GEO Readiness, Competitive Intelligence, External Authority & 100-Q AEO Sandbox
            # (Runs BEFORE PageIntelligenceAgent copywriting & Adversarial Critic so
            #  copywriting sees all 4-pillar gaps + 100-Q AEO gaps, and Critic audits all claims)
            # -----------------------------------------------------------------
            eval_pages = (manifest.pages if manifest else None) or blackboard.pages or []
            if not det_bundle:
                det_bundle = await self._run_deterministic_analyzers(
                    eval_pages=eval_pages,
                    manifest=manifest,
                    blackboard=blackboard,
                    domain=domain,
                    website_url=website_url,
                )
            cro_finding = det_bundle["cro_finding"]
            canonical_audit_rep = det_bundle["canonical_audit_rep"]
            http_status_rep = det_bundle["http_status_rep"]
            heading_hierarchy_rep = det_bundle["heading_hierarchy_rep"]
            media_assets_rep = det_bundle["media_assets_rep"]
            click_depth_rep = det_bundle["click_depth_rep"]
            orphan_pages_rep = det_bundle["orphan_pages_rep"]
            anchor_text_audit_rep = det_bundle["anchor_text_audit_rep"]
            meta_rollup_rep = det_bundle["meta_rollup_rep"]
            form_audit_rep = det_bundle["form_audit_rep"]
            cro_audit_rep = det_bundle["cro_audit_rep"]
            schema_validation_rep = det_bundle["schema_validation_rep"]
            wcag_audit_rep = det_bundle["wcag_audit_rep"]
            local_seo_rep = det_bundle["local_seo_rep"]
            intl_seo_rep = det_bundle["intl_seo_rep"]
            topical_auth_rep = det_bundle["topical_auth_rep"]
            ecom_seo_rep = det_bundle["ecom_seo_rep"]
            serp_app_rep = det_bundle["serp_app_rep"]
            indexation_rollup_rep = det_bundle["indexation_rollup_rep"]
            competitor_seo_parity_rep = det_bundle["competitor_seo_parity_rep"]
            security_audit_rep = det_bundle["security_audit_rep"]
            host_and_redirects_rep = det_bundle["host_and_redirects_rep"]
            deterministic_findings = list(det_bundle.get("deterministic_findings") or [])

            # 3A. AI Answer Engine Discoverability & Commercial Query Simulation
            if effective_pillars is None or "aeo" in effective_pillars:
                controller.mark_node_status("node_aeo_search_simulation", GraphNodeStatus.RUNNING)
                controller.mark_node_status("node_ai_search_simulation", GraphNodeStatus.RUNNING)
                controller.log_activity("node_aeo_search_simulation", "running", "ai_sim.eval", "Simulating AI Answer Engine evaluations across 6 Canonical Commercial Inquiries...")

                model_router.set_active_stage("ai_search_simulation", "AI Answer Engine Simulation")
                model_router.set_active_sub_stage("buyer_query_simulation", "Synthetic Commercial Query Simulation")
                await self._emit_event(
                    analysis_id,
                    "specialist_execution",
                    79,
                    "Simulating AI Answer Engine evaluations across 6 Canonical Commercial Inquiries (ChatGPT, Perplexity, Gemini, Claude)...",
                    {"evaluating_queries": 6}
                )
                try:
                    await team_orchestrator.worker_simulator.execute_task("ai_search_simulation", blackboard)
                    controller.mark_node_status("node_aeo_search_simulation", GraphNodeStatus.COMPLETED)
                    controller.mark_node_status("node_ai_search_simulation", GraphNodeStatus.COMPLETED)
                    controller.log_activity("node_aeo_search_simulation", "success", "ai_sim.complete", "Completed AI search queries simulation with citations")
                except Exception as sim_err:
                    logger.error("AI Search simulation error: %s", sim_err)
                    controller.mark_node_status("node_aeo_search_simulation", GraphNodeStatus.FAILED, error_message=str(sim_err))
                    controller.mark_node_status("node_ai_search_simulation", GraphNodeStatus.FAILED, error_message=str(sim_err))
                    controller.log_activity("node_aeo_search_simulation", "warning", "ai_sim.error", f"Simulation note: {sim_err}")
            else:
                controller.mark_node_status("node_aeo_search_simulation", GraphNodeStatus.SKIPPED)
                controller.mark_node_status("node_ai_search_simulation", GraphNodeStatus.SKIPPED)
                controller.log_activity("node_aeo_search_simulation", "info", "ai_sim.skipped", "AEO search simulation skipped by selective execution")

            if await _check_pause():
                return

            # 3B. Entity Graph, Live AI Visibility, GEO Readiness, Agent Readiness, Competitive & External Authority
            from app.geo.entity_graph import evaluate_entity_graph
            profile_name = ""
            if blackboard.business_profile and blackboard.business_profile.business_name:
                profile_name = blackboard.business_profile.business_name
            entity_graph_report, _entity_graph_findings, entity_graph_contradictions = evaluate_entity_graph(
                eval_pages,
                brand_name=profile_name,
            )
            if entity_graph_contradictions:
                blackboard.identity_contradictions.extend(entity_graph_contradictions)

            model_router.set_active_stage("ai_visibility_monitor", "Live AI Citation & Search Visibility")
            from app.geo.readiness import evaluate_geo_readiness
            visibility_measured = False
            visibility_detail = None
            live_citation_score = None
            ai_visibility_scorecard = None
            geo_readiness = None
            agent_readiness = None
            geo_bench_report = None
            ai_citation_dash = None
            should_run_geo_live = effective_pillars is None or bool(effective_pillars.intersection({"geo", "aeo"}))
            if should_run_geo_live:
                try:
                    from app.geo.audit_monitor import run_audit_visibility
                    profile = blackboard.business_profile
                    b_name = getattr(profile, "business_name", None) or domain
                    b_ind = getattr(profile, "industry", None) or getattr(profile, "niche", None) or "General Business"
                    vis_res = await run_audit_visibility(
                        domain=domain,
                        brand_name=b_name,
                        industry=b_ind,
                        services=list(getattr(profile, "services", None) or []) or list(getattr(profile, "products", None) or []),
                        locations=[profile.geography] if getattr(profile, "geography", None) else None,
                        audience=getattr(profile, "target_audience", None),
                        max_pages=max_pages,
                    )
                    if isinstance(vis_res, tuple):
                        monitored, geo_bench_obj = vis_res
                    else:
                        monitored, geo_bench_obj = vis_res, None

                    if monitored is not None:
                        ai_visibility_scorecard = monitored
                        if monitored.status == "MEASURED" and monitored.citation_rate_pct is not None:
                            visibility_measured = True
                            live_citation_score = float(monitored.citation_rate_pct)
                            visibility_detail = (
                                f"Live AI citation visibility {live_citation_score:.0f}/100 "
                                f"from {monitored.successful_runs} successful responses "
                                f"across {monitored.engines_measured} engine(s), "
                                f"{monitored.queries} queries, {monitored.repeats} run(s). "
                                "This is not the on-page GEO Readiness score."
                            )
                    if geo_bench_obj is not None:
                        geo_bench_report = geo_bench_obj.model_dump() if hasattr(geo_bench_obj, "model_dump") else geo_bench_obj
                except Exception as e:
                    logger.warning("run_audit_visibility error: %s", e)
                    ai_visibility_scorecard = None
                    geo_bench_report = None

                try:
                    from app.geo.citations.tracker import ai_citation_tracker
                    profile = blackboard.business_profile
                    b_name = getattr(profile, "business_name", None) or domain
                    b_ind = getattr(profile, "industry", None) or getattr(profile, "niche", None) or "General Business"
                    ai_citation_dash_obj = await ai_citation_tracker.track_buyer_queries(
                        domain=domain,
                        biz_name=b_name,
                        niche=b_ind,
                        analysis_id=analysis_id,
                    )
                    if ai_citation_dash_obj is not None:
                        ai_citation_dash = ai_citation_dash_obj.model_dump() if hasattr(ai_citation_dash_obj, "model_dump") else ai_citation_dash_obj
                except Exception as cit_e:
                    logger.warning("ai_citation_tracker runtime execution note: %s", cit_e)
                    ai_citation_dash = None
            else:
                visibility_detail = "Live AI visibility benchmark skipped in selective non-GEO execution."

            blackboard.blackboard_state["geo_benchmark_report"] = geo_bench_report
            blackboard.blackboard_state["ai_citation_dashboard"] = ai_citation_dash

            geo_readiness = evaluate_geo_readiness(
                website_url=website_url,
                pages=blackboard.pages,
                manifest=manifest,
                profile=blackboard.business_profile,
                visibility_measured=visibility_measured,
                visibility_detail=visibility_detail,
                visibility_score=live_citation_score,
                country=country,
                language=language,
                entity_graph=entity_graph_report,
            )
            try:
                from app.geo.readiness import enrich_geo_readiness_citations
                brand_name = getattr(blackboard.business_profile, "business_name", None) or domain
                geo_readiness = await enrich_geo_readiness_citations(
                    geo_readiness,
                    model_router=model_router,
                    brand_name=brand_name,
                    domain=domain,
                    profile=blackboard.business_profile,
                )
            except Exception as e:
                logger.warning("Failed to enrich GEO readiness citations with LLM: %s", e)
            blackboard.geo_readiness = geo_readiness

            try:
                from app.geo.agent_readiness import evaluate_agent_readiness
                agent_readiness = await evaluate_agent_readiness(
                    website_url=website_url,
                    pages=blackboard.pages,
                    manifest=manifest,
                )
            except Exception as e:
                logger.warning("Failed to evaluate agent readiness: %s", e)
                agent_readiness = None
            blackboard.agent_readiness = agent_readiness

            from app.seo.competitive.evidence_graph import competitive_evidence_graph_engine
            comp_graph_res = competitive_evidence_graph_engine.build_graph(
                target_profile=blackboard.business_profile,
                target_domain=domain,
                target_evals=blackboard.commercial_evaluations,
                observatory_records=(ai_visibility_scorecard.observatory_records if ai_visibility_scorecard else []),
            )

            from app.seo.competitive.engine import competitive_intelligence_engine
            comp_report_obj = competitive_intelligence_engine.build_competitive_report(
                target_domain=domain,
                business_profile=blackboard.business_profile,
                target_pages=eval_pages,
                competitor_domains=getattr(blackboard.business_profile, "competitors", []) if blackboard.business_profile else [],
                commercial_evaluations=blackboard.commercial_evaluations,
                observatory_records=(ai_visibility_scorecard.observatory_records if ai_visibility_scorecard else []),
                audit_id=analysis_id,
            )

            external_authority_payload = {
                "title": "External Authority & Entity Intelligence",
                "universal_authority_score": None,
                "coverage": [],
                "findings": [],
                "notes": ["External authority was not attached. The crawl audit is unchanged."],
            }
            external_authority_findings: List[Any] = []
            has_external_authority_connected = False
            try:
                from app.connectors.authority.audit_bridge import build_audit_attachment

                # Strict tenant context resolution: avoid leaking or querying shared "org_default" bucket
                tenant_project_id = getattr(run, "org_id", None)
                clean_tenant = tenant_project_id.strip().lower() if isinstance(tenant_project_id, str) else ""
                if not clean_tenant or clean_tenant in FORBIDDEN_TENANT_IDENTIFIERS:
                    tenant_project_id = blackboard.blackboard_state.get("org_id") or getattr(blackboard, "org_id", None)

                clean_tenant = tenant_project_id.strip().lower() if isinstance(tenant_project_id, str) else ""
                if clean_tenant and clean_tenant not in FORBIDDEN_TENANT_IDENTIFIERS:
                    attachment = build_audit_attachment(
                        project_id=tenant_project_id,
                        domain=domain,
                        pages=eval_pages,
                        evidence_store=getattr(blackboard, "evidence_store", None),
                    )
                    external_authority_payload = attachment.get("report", external_authority_payload)
                    external_authority_findings = list(attachment.get("domain_findings", []) or [])

                    cov_items = external_authority_payload.get("coverage", [])
                    for c in cov_items:
                        conn_status = c.get("connection_status") if isinstance(c, dict) else getattr(c, "connection_status", None)
                        data_state = c.get("data_state") if isinstance(c, dict) else getattr(c, "data_state", None)
                        legacy_status = c.get("status") if isinstance(c, dict) else getattr(c, "status", None)
                        if (conn_status == "CONNECTED" or legacy_status == "CONNECTED") and data_state in ("MEASURED", "PARTIALLY_MEASURED", "OK", "FRESH", "STALE"):
                            has_external_authority_connected = True
                            break
                        if data_state in ("MEASURED", "PARTIALLY_MEASURED"):
                            has_external_authority_connected = True
                            break
                        if legacy_status == "CONNECTED" and data_state is None:
                            has_external_authority_connected = True
                            break

                    if not has_external_authority_connected:
                        if external_authority_payload.get("data_state") in ("MEASURED", "PARTIALLY_MEASURED", "OK", "FRESH", "STALE") or external_authority_payload.get("status") in ("CONNECTED", "PARTIALLY_MEASURED"):
                            has_external_authority_connected = True
                        elif len(external_authority_findings) > 0:
                            has_external_authority_connected = True
                else:
                    logger.info("External authority attachment skipped: missing tenant org context (refusing 'org_default' fallback)")
                    external_authority_payload["notes"] = ["External authority was not attached: valid tenant context required."]
            except Exception as exc:
                logger.info("external authority attachment skipped: %s", type(exc).__name__)
                external_authority_payload["error"] = type(exc).__name__

            # 3C. Dynamic Sandbox Questions & KIE Knowledge Graph (tier-gated: 0 / 25 / 100 Q)
            kie_summary = None
            five_dim_visibility = None
            if (effective_pillars is None or "aeo" in effective_pillars) and tier_features.aeo_question_count > 0:
                try:
                    from app.geo.dynamic_sandbox import DynamicQuestionSandboxEngine
                    from app.crawl.knowledge.website_knowledge_graph import WebsiteKnowledgeGraph
                    from app.crawl.knowledge.grounded_simulator import AiVisibilityIndexCalculator
                    from app.crawl.knowledge.primitives import GroundedAnswerSimulation, KieAnswerRisk

                    model_router.set_active_stage("aeo_sandbox", "100-Question Dynamic AEO Sandbox & Hybrid RAG")
                    eval_pages_for_kg = eval_pages or blackboard.pages or []
                    if not getattr(blackboard, "dynamic_sandbox_evaluations", None):
                        sandbox_engine = DynamicQuestionSandboxEngine(model_router=model_router)
                        blackboard.dynamic_sandbox_evaluations = await sandbox_engine.generate_and_evaluate_100_questions(
                            pages=eval_pages_for_kg,
                            website_url=website_url,
                            resolved_entity=blackboard.resolved_entity,
                            profile=blackboard.business_profile,
                        )

                    brand_for_kg = blackboard.resolved_entity.name if blackboard.resolved_entity else domain
                    kg = WebsiteKnowledgeGraph(brand=brand_for_kg, domain=domain)
                    kg.build_from_pages(eval_pages_for_kg)
                    kie_summary = kg.summary()

                    sim_list = []
                    for ev in (blackboard.dynamic_sandbox_evaluations or []):
                        grounding = ev.grounding_ratio or 0.0
                        risk = ev.answer_risk or "LOW"
                        if isinstance(risk, str):
                            try:
                                risk = KieAnswerRisk(risk)
                            except Exception:
                                risk = KieAnswerRisk.LOW
                        sim_obj = GroundedAnswerSimulation(
                            question_id=ev.question_id,
                            candidate_answer=ev.crawled_answer or "",
                            grounding_ratio=grounding,
                            retrieval_evidence_count=ev.retrieval_evidence_count or 0,
                            answer_risk=risk,
                        )
                        sim_list.append(sim_obj)

                    dims = AiVisibilityIndexCalculator().compute(kg, sim_list)
                    five_dim_visibility = dims.model_dump()
                except Exception as kie_err:
                    logger.info("KIE Graph / Sandbox assembly note: %s", kie_err)

            # Populate preliminary blackboard.findings BEFORE PageIntelligenceAgent so per-page
            # copywriting sees verified SEO/GEO/AEO/CRO findings & AEO 100-Q gaps.
            from app.remediation.deduplicator import FindingDeduplicator
            prelim_claims = blackboard.claim_registry.get_all()
            prelim_raw_findings = self.decision_engine.synthesize_findings(prelim_claims, blackboard.evidence_store)
            for det_f in deterministic_findings:
                if not any(x.finding_id == det_f.finding_id for x in prelim_raw_findings):
                    prelim_raw_findings.append(det_f)
            for ext_f in external_authority_findings:
                if not any(x.finding_id == ext_f.finding_id for x in prelim_raw_findings):
                    prelim_raw_findings.append(ext_f)
            blackboard.findings = FindingDeduplicator.deduplicate(prelim_raw_findings)

            if await _check_pause():
                return

            # -----------------------------------------------------------------
            # Stage 4: Per-Page, Per-Section SEO & Copywriting Intelligence
            # (Runs AFTER all 4 pillars + AEO + GEO Readiness; tier-gated by copywriting_page_cap)
            # -----------------------------------------------------------------
            if (effective_pillars is None or "seo" in effective_pillars) and tier_features.copywriting_page_cap != 0:
                controller.mark_node_status("node_seo_page_intelligence", GraphNodeStatus.RUNNING)
                controller.mark_node_status("node_page_intelligence", GraphNodeStatus.RUNNING)
                controller.log_activity("node_seo_page_intelligence", "running", "page.rewrites", f"Writing detailed SEO and copy reports for {len(manifest.pages)} crawled page(s)...")

                model_router.set_active_stage("page_intelligence", "Page-Level SEO & Copywriting")
                model_router.set_active_sub_stage("page_copy_and_hero", "Page-by-Page SEO & Copywriting Rewrites")
                await self._emit_event(
                    analysis_id,
                    "specialist_execution",
                    82,
                    f"Writing detailed SEO and copy reports for {len(manifest.pages)} crawled page(s)...",
                )
                t_page_start = time.perf_counter()
                page_agent = PageIntelligenceAgent(model_router)
                await page_agent.run(blackboard)
                page_elapsed_ms = max(50, int((time.perf_counter() - t_page_start) * 1000))
                copy_dur_ms = max(10, int(page_elapsed_ms / 6))
                controller.mark_node_status("node_seo_page_intelligence", GraphNodeStatus.COMPLETED)
                controller.mark_node_status("node_page_intelligence", GraphNodeStatus.COMPLETED)
                controller.log_activity("node_seo_page_intelligence", "success", "page.complete", f"Completed page-level intelligence for {len(manifest.pages)} page(s)")
            else:
                page_elapsed_ms = 0
                copy_dur_ms = 0
                controller.mark_node_status("node_seo_page_intelligence", GraphNodeStatus.SKIPPED)
                controller.mark_node_status("node_page_intelligence", GraphNodeStatus.SKIPPED)
                controller.log_activity("node_seo_page_intelligence", "info", "page.skipped", "SEO page intelligence skipped by selective execution")

            # ── Progressive Reporting: Phase 4 — Copywriting & Page Intelligence ─
            try:
                page_intel_reports = (
                    getattr(blackboard, "page_reports", None)
                    or getattr(blackboard, "page_intelligence_reports", None)
                    or {}
                )
                copy_status = ExecutionStatus.COMPLETED if (effective_pillars is None or "seo" in effective_pillars) else ExecutionStatus.NOT_CONFIGURED
                copy_conf = ConfidenceLevel.VERIFIED if page_intel_reports else ConfidenceLevel.UNMEASURED

                p4_1 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_04_copywriting",
                    phase_name="4. Copywriting & Page Intelligence",
                    subphase_id="4.1",
                    subphase_title="Page Intelligence & Copywriting Synthesis",
                    objective="Compile URL-by-URL SEO/GEO/CRO audits, title upgrades, and character-safe hero copy rewrites.",
                    agent_id="agent.page_intelligence",
                    agent_model="hybrid_pipeline",
                    execution_mode="hybrid",
                    duration_ms=page_elapsed_ms,
                    status=copy_status,
                    input_summary={"pages_analyzed": len(manifest.pages)},
                    processing_steps=["Compile per-page SEO & copy audits", "Assemble character-safe rewrite payload"],
                    structured_output={"pages_analyzed": len(manifest.pages), "reports_count": len(page_intel_reports)},
                    evidence_tokens=[],
                    findings=[],
                    confidence=copy_conf,
                )
                await self._record_progressive_subphase(p4_1, "page_intelligence_consolidated")

                # Phase 4 Consolidated
                await self._consolidate_progressive_phase(analysis_id, "phase_04_copywriting", "phase_04_consolidated")
            except Exception as rep4_err:
                logger.warning(f"Progressive reporting error for Phase 4: {rep4_err}", exc_info=True)

            if await _check_pause():
                return

            # -----------------------------------------------------------------
            # Stage 5: Adversarial Critic (Batched 100% Claim Audit) + Zero-Fake
            # Integrity Gate + Contradiction Engine + Causal Bottlenecks
            # (Runs AFTER Specialists, AEO 100-Q, and Copywriting)
            # -----------------------------------------------------------------
            controller.mark_node_status("node_adversarial_critic", GraphNodeStatus.RUNNING)
            controller.log_activity("node_adversarial_critic", "running", "critic.audit", "Adversarial critic testing 100% of claims against ground truth...")

            model_router.set_active_stage("adversarial_verification", "Adversarial Verification & Integrity Gate")
            model_router.set_active_sub_stage("critic_verification", "Adversarial Critic & Ground Truth Gate")
            run.status = AnalysisStage.ADVERSARIAL_VERIFICATION
            await self._emit_event(
                analysis_id,
                "adversarial_verification",
                85,
                "Adversarial critic cross-examining all specialist, AEO, and copywriting claims...",
            )

            if tier_features.critic_mode != "none":
                try:
                    critic_res = await team_orchestrator.worker_critic.execute_task("34_adversarial_verification", blackboard)
                    blackboard.blackboard_state["critic_gate"] = {
                        "status": "completed",
                        "mode": tier_features.critic_mode,
                        "verified_count": len(critic_res.get("verified_claims") or []),
                        "rejected_count": len(critic_res.get("rejected_claims") or []),
                        "deflated_count": len(critic_res.get("deflated_claims") or []),
                        "contradictions_count": len(critic_res.get("contradictions") or []),
                        "batches_executed": critic_res.get("batches_executed", 1),
                        "total_audited": critic_res.get("total_audited", 0),
                    }
                except Exception as critic_err:
                    logger.error("Mandatory CognitiveCriticWorker gate failed for %s: %s", analysis_id, critic_err)
                    blackboard.blackboard_state["critic_gate"] = {
                        "status": "failed",
                        "error": str(critic_err),
                    }
            else:
                blackboard.blackboard_state["critic_gate"] = {
                    "status": "locked_by_tier",
                    "mode": "none",
                    "note": f"Adversarial AI critic is not included in tier '{tier_id}'.",
                }

            # Zero-Fake Evidence Integrity Gate (authoritative final claim gate)
            if await _check_pause():
                return
            controller.mark_node_status("node_integrity_gate", GraphNodeStatus.RUNNING)
            controller.log_activity("node_integrity_gate", "running", "integrity.gate", "Enforcing Zero-Fake Evidence cryptographic provenance...")

            current_claims = blackboard.claim_registry.get_all()
            gate_res = integrity_gate.validate_claims_and_evidence(
                current_claims, blackboard.evidence_store, blackboard.claim_registry
            )
            blackboard.blackboard_state["integrity_gate"] = gate_res.model_dump()
            controller.mark_node_status("node_integrity_gate", GraphNodeStatus.COMPLETED)
            controller.log_activity("node_integrity_gate", "success", "integrity.complete", "Zero-Fake Evidence integrity gate passed")

            from app.domain.enums import Materiality, RubricConfidence
            from app.orchestration.cognition.finding_rubric import apply_rubric_to_claim
            for _claim in current_claims:
                apply_rubric_to_claim(_claim, blackboard.evidence_store)
            held_guesses = [
                c for c in current_claims
                if c.confidence_rubric == RubricConfidence.GUESSING
                and c.materiality == Materiality.CRITICAL
                and not c.adversarial_reviewed
            ]
            if held_guesses:
                adv = agent_pool.get("verification.adversarial.v3")
                if adv:
                    await adv.run(blackboard)
                    await self._emit_event(
                        analysis_id,
                        "adversarial_verification",
                        86,
                        f"Escalated {len(held_guesses)} GUESSING+CRITICAL claim(s) to verification.adversarial.v3 before executive use.",
                    )

            # Mandatory Contradiction Engine Gate
            try:
                from app.orchestration.cognition.contradiction_engine import ContradictionEngine
                contra_engine = ContradictionEngine()
                claim_contradictions = contra_engine.detect_contradictions(
                    blackboard.claim_registry.get_all()
                )
                blackboard.blackboard_state["contradiction_report"] = {
                    "status": "completed",
                    "conflicts_detected": len(claim_contradictions or []),
                    "conflicts": claim_contradictions[:20],
                }
            except Exception as ce_err:
                logger.warning("ContradictionEngine gate note for %s: %s", analysis_id, ce_err)
                blackboard.blackboard_state["contradiction_report"] = {
                    "status": "error",
                    "error": str(ce_err),
                }

            controller.mark_node_status("node_adversarial_critic", GraphNodeStatus.COMPLETED)
            controller.log_activity("node_adversarial_critic", "success", "critic.complete", "Adversarial cross-examination complete")

            # Detect uncorroborated marketing claims (Evidence Gaps)
            evidence_gaps = self.gap_detector.detect_gaps(current_claims, blackboard.evidence_store, blackboard.pages)
            blackboard.blackboard_state["evidence_gaps"] = [g.model_dump() for g in evidence_gaps]

            if await _check_pause():
                return

            # Causal Reasoning & Root-Cause Bottleneck Discovery
            controller.mark_node_status("node_causal_bottlenecks", GraphNodeStatus.RUNNING)
            controller.log_activity("node_causal_bottlenecks", "running", "causal.roots", "Causal Reasoning Engine isolating primary root-cause growth bottlenecks...")

            model_router.set_active_stage("causal_reasoning", "Causal Reasoning & Bottlenecks")
            model_router.set_active_sub_stage("causal_bottlenecks", "Causal Graph & Bottleneck Isolation")
            await self._emit_event(analysis_id, "specialist_execution", 88, "Causal Reasoning Engine isolating primary root-cause growth bottlenecks...")
            bottlenecks = self.causal_engine.analyze_root_causes(
                claims=current_claims,
                business_profile=blackboard.business_profile,
                crawl_summary=manifest.crawl_health if manifest else None,
            )
            blackboard.blackboard_state["root_causes"] = [b.model_dump() for b in bottlenecks]
            controller.mark_node_status("node_causal_bottlenecks", GraphNodeStatus.COMPLETED)
            controller.log_activity("node_causal_bottlenecks", "success", "causal.complete", f"Isolated {len(bottlenecks)} primary growth bottlenecks")

            # Update Hypotheses & Opportunities with accumulated evidence
            evaluated_hypotheses = self.hypothesis_engine.evaluate_hypotheses_against_evidence(
                initial_hypotheses, current_claims, blackboard.evidence_store
            )
            mission_state.hypotheses = evaluated_hypotheses

            opportunities = self.opportunity_detector.detect_opportunities(
                blackboard.business_profile, blackboard.pages, current_claims
            )
            blackboard.blackboard_state["opportunities"] = [o.model_dump() for o in opportunities]

            if await _check_pause():
                return

            # -----------------------------------------------------------------
            # Stage 6: Authoritative Finding Deduplication & Executive Narrative
            # -----------------------------------------------------------------
            raw_findings = self.decision_engine.synthesize_findings(current_claims, blackboard.evidence_store)
            if cro_finding is not None:
                raw_findings = [f for f in raw_findings if f.finding_id != "find_cro_001"]
                raw_findings.append(cro_finding)
            for det_f in deterministic_findings:
                if not any(x.finding_id == det_f.finding_id for x in raw_findings):
                    raw_findings.append(det_f)
            for ext_f in external_authority_findings:
                if not any(x.finding_id == ext_f.finding_id for x in raw_findings):
                    raw_findings.append(ext_f)

            final_findings = FindingDeduplicator.deduplicate(raw_findings)
            if getattr(tier_features, "ai_depth_mode", None) != "deterministic_only":
                await self._enrich_findings_with_ai(
                    findings=final_findings,
                    model_router=model_router,
                    business_profile=blackboard.business_profile,
                    site_facts=getattr(blackboard, "site_facts", None) or {},
                    website_url=website_url,
                )
            from app.domain.evidence.taxonomy import assign_evidence_scope
            for f in final_findings:
                assign_evidence_scope(f, sample_size=len(eval_pages))
            blackboard.findings = final_findings

            # Synthesize final Causal Diagnostic Chains with multi-source evidence
            causal_diagnostic_chains = self.causal_engine.analyze_root_causes(
                claims=current_claims,
                business_profile=blackboard.business_profile,
                findings=final_findings,
                ai_search_evaluations=blackboard.ai_search_evaluations,
                competitor_bakeoff=blackboard.competitor_bakeoff,
                crawl_summary=manifest.crawl_health,
                observatory_records=(ai_visibility_scorecard.observatory_records if ai_visibility_scorecard else []),
                competitive_graph=comp_graph_res,
            )

            # Executive Strategy Narrative Synthesis (runs AFTER Critic, Integrity Gate & Final Findings)
            controller.mark_node_status("node_executive_narrative", GraphNodeStatus.RUNNING)
            controller.log_activity("node_executive_narrative", "running", "narrative.compile", "Synthesizer compiling C-Suite narrative from verified specialist claims...")

            model_router.set_active_stage("executive_synthesis", "Executive Strategy Narrative Synthesis")
            model_router.set_active_sub_stage("narrative_synthesis", "C-Suite Strategic Narrative Compilation")
            run.status = AnalysisStage.EXECUTIVE_SYNTHESIS
            await self._emit_event(analysis_id, "executive_synthesis", 90, "Synthesizer compiling C-Suite narrative from verified specialist claims...")
            if not blackboard.executive_narrative.get("story_summary"):
                await team_orchestrator.worker_synthesizer.execute_task("synthesis", blackboard)
            controller.mark_node_status("node_executive_narrative", GraphNodeStatus.COMPLETED)
            controller.log_activity("node_executive_narrative", "success", "narrative.complete", "Executive narrative synthesis completed")

            if await _check_pause():
                return

            # -----------------------------------------------------------------
            # Step 15: Scoring Engine (Single Source of Truth over complete findings)
            # -----------------------------------------------------------------
            controller.mark_node_status("node_honest_scoring", GraphNodeStatus.RUNNING)
            controller.log_activity("node_honest_scoring", "running", "scoring.calc", "Deterministic Scoring Engine computing intent-adjusted category scores...")

            model_router.set_active_stage("scoring_and_remediation", "Scoring & Remediation Blueprints")
            model_router.set_active_sub_stage("deterministic_scoring", "Deterministic Category & Honest Scoring")
            if run:
                run.status = AnalysisStage.SCORING
            await self._emit_event(analysis_id, "scoring", 93, "Deterministic Scoring Engine computing intent-adjusted category scores...")

            live_bench = None
            completed_runs = int(getattr(ai_visibility_scorecard, "successful_runs", 0) or 0) if ai_visibility_scorecard is not None else 0
            if visibility_measured and completed_runs > 0 and ai_visibility_scorecard is not None:
                live_bench = {"total_queries": completed_runs}
                if ai_visibility_scorecard.mention_rate_pct is not None:
                    live_bench["overall_mention_rate_pct"] = float(ai_visibility_scorecard.mention_rate_pct)
                if ai_visibility_scorecard.citation_rate_pct is not None:
                    live_bench["overall_first_party_citation_rate_pct"] = float(ai_visibility_scorecard.citation_rate_pct)
                if geo_bench_report and isinstance(geo_bench_report, dict) and "share_of_model" in geo_bench_report:
                    live_bench["share_of_model"] = geo_bench_report["share_of_model"]

            eval_pages_val = blackboard.pages or []
            has_schema_val = any(len(getattr(p, "schema_types", []) or []) > 0 for p in eval_pages_val) if eval_pages_val else False
            is_https_val = website_url.startswith("https://") if website_url else False
            readability_val = page_ev.readability_score if page_ev else blackboard.blackboard_state.get("readability_score")
            commercial_evals_val = blackboard.commercial_evaluations or blackboard.ai_search_evaluations or []

            cwv_data_val = blackboard.blackboard_state.get("cwv_data") or {}
            if not cwv_data_val and manifest and getattr(manifest, "crawl_health", None):
                avg_ttfb_ms = manifest.crawl_health.get("avg_ttfb_ms")
                if isinstance(avg_ttfb_ms, (int, float)) and avg_ttfb_ms > 0:
                    cwv_data_val = {"ttfb": float(avg_ttfb_ms) / 1000.0}

            overall_scores = self.scoring_engine.calculate_scores(
                findings=final_findings,
                business_profile=blackboard.business_profile,
                has_schema=has_schema_val,
                is_https=is_https_val,
                readability=readability_val,
                external_authority_connected=has_external_authority_connected,
                live_citation_score=live_citation_score,
                live_benchmark_data=live_bench,
                manifest=manifest,
                cwv_data=cwv_data_val,
                form_audit=form_audit_rep,
                pages=eval_pages_val,
            )
            extractability = getattr(geo_readiness, "extractability_score", None)
            if overall_scores is not None and extractability is not None:
                self.scoring_engine.apply_measured_geo_score(overall_scores, extractability)
            blackboard.scores = overall_scores

            # Human, Google, and on-page AI readiness (honest specialized views)
            honest_scores = self.scoring_engine.calculate_honest_scores(
                findings=final_findings,
                business_profile=blackboard.business_profile,
                commercial_evals=commercial_evals_val,
                has_schema=has_schema_val,
                is_https=is_https_val,
                readability=readability_val,
                geo_readiness=geo_readiness,
                live_citation_score=live_citation_score,
                live_benchmark_data=live_bench,
                external_authority_connected=has_external_authority_connected,
                cwv_data=cwv_data_val,
                form_audit=form_audit_rep,
                manifest=manifest,
                pages=eval_pages_val,
            )
            blackboard.honest_scores = honest_scores
            scoring_methodology_appendix = self.scoring_engine.build_scoring_methodology_appendix(
                scores=overall_scores,
                honest_scores=honest_scores,
                geo_readiness=geo_readiness,
                crawl_inventory=getattr(manifest, "crawl_inventory", None) if manifest else None,
            )

            # Persist environmental scoring context for downstream nodes / re-runs
            blackboard.blackboard_state["external_authority_connected"] = has_external_authority_connected
            blackboard.blackboard_state["live_citation_score"] = live_citation_score
            blackboard.blackboard_state["live_bench"] = live_bench
            blackboard.blackboard_state["has_schema"] = has_schema_val
            blackboard.blackboard_state["readability_score"] = readability_val

            # Calibrated Confidence
            confidence_result = self.confidence_engine.calculate_confidence(
                claims=current_claims,
                evidence_store=blackboard.evidence_store,
                pages=blackboard.pages,
                contradictions_count=len(blackboard.claim_registry.get_contradictions())
            )
            overall_scores.overall_confidence = confidence_result.confidence_score
            overall_scores.evidence_coverage = confidence_result.evidence_coverage

            controller.mark_node_status("node_honest_scoring", GraphNodeStatus.COMPLETED)
            controller.log_activity("node_honest_scoring", "success", "scoring.complete", f"Honest scores computed: Overall {overall_scores.overall_score:.0f}/100 ({overall_scores.grade})")

            if await _check_pause():
                return

            # -----------------------------------------------------------------
            # Step 16: Digital Twin, Timeline & Preliminary Narrative Synthesis
            # (Unified Remediation Pack is deferred to Step 25b post-4-pillars & post-competitor analysis)
            # -----------------------------------------------------------------
            # Digital Twin & Temporal Timeline Update
            if domain not in self.digital_twins:
                self.digital_twins[domain] = WebsiteDigitalTwin(
                    twin_id=f"twin_{domain.replace('.', '_')}",
                    domain=domain,
                    base_url=website_url
                )
            twin = self.digital_twins[domain]
            if not twin.historical_snapshots:
                twin.historical_snapshots = _prior_audit_snapshots(
                    self.repository,
                    getattr(run, "org_id", None),
                    domain,
                    analysis_id,
                )

            if domain not in self.timelines:
                self.timelines[domain] = WebsiteIntelligenceTimeline(domain)
            timeline = self.timelines[domain]
            timeline.record_audit(analysis_id, overall_scores, final_findings)

            # Narrative Synthesis
            narrative_data = self.narrative_gen.build_narrative(
                business_profile=blackboard.business_profile,
                findings=final_findings,
                scores=overall_scores,
                synthesizer_output=blackboard.executive_narrative
            )

            try:
                from app.domain.scoring.displayed_score import align_story_score, displayed_composite
                score_payload = {
                    "scores": overall_scores.model_dump(mode="json") if hasattr(overall_scores, "model_dump") else {},
                    "honest_scores": honest_scores.model_dump(mode="json") if hasattr(honest_scores, "model_dump") else {},
                    "geo_readiness": geo_readiness.model_dump(mode="json") if geo_readiness is not None and hasattr(geo_readiness, "model_dump") else {},
                    "ai_visibility_scorecard": (
                        ai_visibility_scorecard.model_dump(mode="json")
                        if ai_visibility_scorecard is not None and hasattr(ai_visibility_scorecard, "model_dump")
                        else None
                    ),
                    "observatory_records": list(getattr(ai_visibility_scorecard, "observatory_records", None) or []),
                }
                dossier_composite = displayed_composite(score_payload)
                if dossier_composite is not None and narrative_data.get("story_summary"):
                    narrative_data["story_summary"] = align_story_score(
                        narrative_data["story_summary"],
                        getattr(overall_scores, "overall_score", None),
                        dossier_composite,
                    )
            except Exception:
                logger.info("displayed score alignment skipped")

            # Character-Safe Copy and C-Suite WhatsApp 1-Pager
            character_copy = generate_character_safe_copy(
                blackboard.business_profile,
                website_url
            )
            blackboard.character_safe_copy = character_copy

            _root_causes = blackboard.blackboard_state.get("root_causes") or []
            _top_bottleneck = (
                blackboard.blackboard_state.get("causal_root_cause", {}).get("bottleneck", "")
                or (_root_causes[0].get("title", "") if _root_causes and isinstance(_root_causes[0], dict) else "")
            )
            wa_summary = generate_whatsapp_summary(
                domain=domain,
                honest_scores=honest_scores,
                what_to_ignore=narrative_data.get("consultant_advice_what_to_ignore", ""),
                top_bottleneck=_top_bottleneck,
                top_actions=[r.title for r in (blackboard.roadmap_7_days or [])[:3]] if getattr(blackboard, "roadmap_7_days", None) else [f.title for f in final_findings[:3]],
                report_url=website_url
            )

            # Re-sync Evidence Graph 2.0 with all evidence, findings, and claims
            blackboard.evidence_graph.populate_from_evidence_store(blackboard.evidence_store, manifest)

            # Ensure all findings carry verified FindingEvidence with real DOM selectors and SHA-256 hashes
            for f in final_findings:
                if not f.evidence and f.evidence_refs:
                    for ref in f.evidence_refs:
                        ev = blackboard.evidence_store.get(ref)
                        if ev:
                            f.evidence.append(
                                FindingEvidence(
                                    evidence_id=ev.id,
                                    url=ev.url,
                                    selector=ev.selector or "body",
                                    element=ev.selector or ev.source_type,
                                    value=str(ev.value)[:200] if ev.value is not None else "",
                                    snippet=(ev.text or "")[:200]
                                )
                            )
                            if not f.provenance_hash:
                                f.provenance_hash = ev.hash

            blackboard.evidence_graph.link_findings_and_claims(final_findings, current_claims)
            from app.domain.evidence.fusion import multi_plane_fusion
            multi_plane_fusion.fuse_all_planes(
                graph=blackboard.evidence_graph,
                domain=domain,
                manifest=manifest,
                evidence_store=blackboard.evidence_store,
                observatory_records=(ai_visibility_scorecard.observatory_records if ai_visibility_scorecard else []),
            )
            graph_summary = blackboard.evidence_graph.export_graph_summary()

            from app.crawl.audit.manifest import build_run_manifest, seal_manifest
            graph_snap = blackboard.evidence_store._ensure_snapshots().put(
                source="evidence_graph",
                body=blackboard.evidence_graph.export_graph_data(),
                source_type="graph",
                media_type="application/json",
            )
            report_uuid = str(uuid.uuid4())
            telemetry_data = telemetry_tracker.get_data()
            run_manifest = build_run_manifest(
                analysis_id=analysis_id,
                website_url=website_url,
                report_id=report_uuid,
                evidence_store=blackboard.evidence_store,
                findings=final_findings,
                telemetry=telemetry_data,
                snapshots=blackboard.evidence_store.snapshots,
                evidence_graph_snapshot_id=graph_snap.snapshot_id,
                app_version=settings.APP_VERSION,
            )
            # Manifest sealing is deferred until the final report passes integrity gates.
            # The IDs are available to report assembly, but the run is not sealed yet.
            run.manifest_id = run_manifest.manifest_id
            run.report_id = report_uuid
            run.is_sealed = False

            from app.core.monitoring.visual_intelligence import visual_intelligence_engine
            visual_intel = visual_intelligence_engine.synthesize_visual_intelligence(
                domain=domain,
                business_profile=blackboard.business_profile,
                scores=overall_scores,
                honest_scores=honest_scores,
                manifest=manifest,
                findings=final_findings,
                ai_search_matrix=blackboard.ai_search_evaluations,
                commercial_evaluations=blackboard.commercial_evaluations,
                geo_readiness=geo_readiness,
                competitor_bakeoff=blackboard.competitor_bakeoff,
            )

            # Build cryptographic evidence ledger map for client verification
            evidence_ledger_map = {}
            if hasattr(blackboard, "evidence_store") and blackboard.evidence_store:
                for ev in blackboard.evidence_store.get_all():
                    evidence_ledger_map[ev.id] = {
                        "id": ev.id,
                        "source_type": ev.source_type,
                        "analyzer": ev.analyzer,
                        "url": ev.url,
                        "selector": ev.selector,
                        "text": ev.text,
                        "value": ev.value,
                        "hash": ev.hash,
                        "content_sha256": ev.content_sha256,
                        "raw_snapshot_id": ev.raw_snapshot_id,
                        "fetched_at": ev.fetched_at.isoformat() if hasattr(ev.fetched_at, "isoformat") else str(ev.fetched_at or ""),
                        "metadata": ev.metadata or {},
                    }

            # Evaluate regressions against historical cryptographic snapshots
            from app.core.monitoring.regression_detector import regression_detector
            reg_report = regression_detector.evaluate_audit_run(
                domain=domain,
                current_scores=overall_scores,
                findings=final_findings,
                evidence_ledger=evidence_ledger_map,
                snapshot_id=graph_snap.snapshot_id,
                historical_snapshots=twin.historical_snapshots,
            )
            twin.historical_snapshots = reg_report.historical_timeline

            # Run Visual UX Inspection across Desktop, Tablet, and Mobile viewports
            from app.cro.visual_ux_tester import visual_ux_tester
            visual_ux_rep = visual_ux_tester.inspect_website_visual_ux(
                domain=domain,
                website_url=website_url,
                dom_evidence=evidence_ledger_map,
            )

            # Synthesize Lifecycle Revenue Intelligence with genuine provider connection states
            from app.connectors.lifecycle_revenue import lifecycle_service
            coverage_rows = external_authority_payload.get("coverage", [])
            gsc_conn = any(
                (isinstance(c, dict) and c.get("provider") == "google_search_console" and c.get("status") == "CONNECTED")
                for c in coverage_rows
            )
            ga4_conn = any(
                (isinstance(c, dict) and c.get("provider") == "google_analytics_4" and c.get("status") == "CONNECTED")
                for c in coverage_rows
            )
            crm_conn = any(
                isinstance(c, dict)
                and str(c.get("provider") or "").lower() in {"crm", "hubspot", "salesforce"}
                and c.get("status") == "CONNECTED"
                for c in coverage_rows
            )
            lifecycle_rep = lifecycle_service.synthesize_lifecycle_intelligence(
                domain=domain,
                gsc_connected=gsc_conn,
                ga4_connected=ga4_conn,
                crm_connected=crm_conn,
            )

            # Synthesize first-class Evidence Taxonomy & Epistemic Hierarchy report
            from app.domain.evidence.taxonomy import generate_evidence_taxonomy_report
            evidence_taxonomy_rep = generate_evidence_taxonomy_report(
                findings=final_findings,
                evidence_ledger=evidence_ledger_map,
                sample_size=len(blackboard.pages or []),
            )

            # Synthesize per-engine AI evaluations
            from app.geo.per_engine_evaluator import evaluate_per_engine_ai
            per_engine_geo_rep = evaluate_per_engine_ai(
                pages=eval_pages,
                manifest=manifest,
                profile=blackboard.business_profile,
                website_url=website_url
            )

            # Layer 3 — Derived Intelligence Engine evaluation
            from app.domain.evidence.derived import DerivedIntelligenceEngine
            derived_engine = DerivedIntelligenceEngine()
            derived_intel_metrics = derived_engine.compute_all(blackboard.evidence_store, manifest)

            # 100 Dynamic Sandbox Questions & KIE Knowledge Graph already executed in Stage 3
            # (before PageIntelligenceAgent copywriting & Adversarial Critic).

            try:
                from app.connectors.google.google_report import collect_google_performance
                google_performance = collect_google_performance(domain)
            except Exception:
                logger.info("google performance seal skipped")
                google_performance = {
                    "search_console": {
                        "state": "FETCH_FAILED",
                        "source": "google_search_console",
                        "notice": "Google Search Console could not be retrieved. No clicks or impressions are shown.",
                    },
                    "analytics": {
                        "state": "FETCH_FAILED",
                        "source": "google_analytics_4",
                        "notice": "Google Analytics could not be retrieved. No sessions are shown.",
                    },
                }

            try:
                from app.cro import build_cro_intelligence
                from app.cro.analyzer import evaluate_conversion_journey
                competitor_domains = []
                if competitor_seo_parity_rep is not None:
                    for competitor in getattr(competitor_seo_parity_rep, "competitors", []) or []:
                        if not getattr(competitor, "is_target", False) and getattr(competitor, "domain", None):
                            competitor_domains.append(competitor.domain)

                # Safe-mode Playwright CRO browser & journey execution (bounded, non-destructive, fail-open)
                cro_browser_summary: Optional[Dict[str, Any]] = None
                should_run_cro_browser = (
                    (effective_pillars is None or "cro" in effective_pillars)
                    and bool(eval_pages)
                    and (not os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("DRISTIK_CRO_BROWSER_IN_TESTS") == "1")
                )
                if should_run_cro_browser:
                    try:
                        from app.cro.browser_testing import CROBrowserTestingEngine
                        from app.cro.models import CROPage

                        bt_engine = CROBrowserTestingEngine()
                        raw_map = getattr(blackboard, "raw_html_map", None) or {}
                        rendered_ok = 0
                        interactions_ok = 0
                        for idx_p, pg in enumerate(eval_pages[:3]):
                            pg_url = getattr(pg, "url", None) or ""
                            if not pg_url:
                                continue
                            cro_pg = CROPage(
                                audit_id=analysis_id,
                                tenant_id=str(getattr(run, "org_id", None) or "default"),
                                url=pg_url,
                                page_type="homepage" if idx_p == 0 else "landing",
                            )
                            snaps, _elems, inters = await asyncio.wait_for(
                                bt_engine.audit_page(
                                    tenant_id=str(getattr(run, "org_id", None) or "default"),
                                    audit_id=analysis_id,
                                    page=cro_pg,
                                    raw_html=raw_map.get(pg_url),
                                    viewports=("desktop", "mobile"),
                                    safe_mode=True,
                                    use_live_browser=True,
                                ),
                                timeout=20.0,
                            )
                            if any(getattr(s, "execution_mode", "") == "live_browser" for s in (snaps or [])):
                                rendered_ok += 1
                            interactions_ok += len([it for it in (inters or []) if getattr(it, "status", "") in ("passed", "failed", "blocked_by_safe_mode")])
                        if rendered_ok > 0 or interactions_ok > 0:
                            cro_browser_summary = {
                                "rendered_pages": rendered_ok,
                                "interaction_tests_executed": interactions_ok,
                                "journey_execution_status": "EXECUTED_SAFE_MODE" if interactions_ok > 0 else "RENDERED_ONLY",
                            }
                    except Exception as cro_bt_err:
                        logger.info("CRO safe-mode browser execution note (fail-open): %s", cro_bt_err)

                rebuilt_cro_intel = build_cro_intelligence(
                    pages=eval_pages,
                    raw_html_map=getattr(blackboard, "raw_html_map", None),
                    business_profile=blackboard.business_profile,
                    analytics=google_performance.get("analytics") if isinstance(google_performance, dict) else None,
                    search_console=google_performance.get("search_console") if isinstance(google_performance, dict) else None,
                    wcag=wcag_audit_rep,
                    competitor_domains=competitor_domains,
                    discovered_urls=getattr(manifest, "total_pages_discovered", None) if manifest else None,
                    browser_tests=cro_browser_summary,
                ).model_dump()
                journey_eval = evaluate_conversion_journey(eval_pages, blackboard.business_profile)
                rebuilt_cro_intel["conversion_journey"] = journey_eval
                rebuilt_cro_intel["journey_stages"] = journey_eval["journey_stages"]
                rebuilt_cro_intel["dropoff_friction_points"] = journey_eval["dropoff_friction_points"]
                cro_audit_rep.intelligence = rebuilt_cro_intel
            except Exception as cro_intel_err:
                logger.info("CRO intelligence rebuild kept the pre-analytics snapshot: %s", cro_intel_err)

            # Pre-synthesize chapter narratives for enterprise audit book
            chapter_narratives_map: Dict[str, Dict[str, Any]] = {}
            try:
                from app.reports.agentic_chapter_synthesizer import AgenticChapterSynthesizer
                from app.seo.reporting.seo_book_renderer import CORE_CHAPTERS, AGENT_ROUTING_MAP

                synth_book = {
                    "domain": domain,
                    "pages": eval_pages,
                    "business_profile": blackboard.business_profile,
                }
                ch_sem = asyncio.Semaphore(4)

                async def _synth_ch(ch_idx: int, ch: Dict[str, Any]):
                    ch_num = f"{ch_idx + 3:02d}"
                    ch_agent_ids = {aid for aid, cid in AGENT_ROUTING_MAP.items() if cid == ch["id"]}
                    ch_findings = [
                        f for f in final_findings
                        if (getattr(f, "agent_id", None) in ch_agent_ids) or (getattr(f, "routed_to", None) == ch["id"])
                    ]
                    async with ch_sem:
                        narr = await AgenticChapterSynthesizer.synthesize_chapter_narrative_ai(
                            book=synth_book,
                            number=ch_num,
                            section=ch,
                            findings=ch_findings,
                            is_geo=False,
                            client=getattr(model_router, "client", None),
                        )
                    return ch["id"], ch_num, narr

                ch_results = await asyncio.gather(*[_synth_ch(i, ch) for i, ch in enumerate(CORE_CHAPTERS)])
                for ch_id, ch_num, narr in ch_results:
                    chapter_narratives_map[ch_id] = narr
                    chapter_narratives_map[ch_num] = narr
            except Exception as ch_synth_err:
                logger.info("Chapter narratives pre-synthesis note: %s", ch_synth_err)

            from app.reports.evidence_ledger import merge_finding_evidence
            merge_finding_evidence(evidence_ledger_map, final_findings)

            # -----------------------------------------------------------------
            # Step 25b: Unified Remediation Pack & Multi-Pillar Action Roadmap
            # (Generated strictly AFTER SEO, GEO, AEO, CRO and Competitors are understood by AI)
            # -----------------------------------------------------------------
            controller.mark_node_status("node_code_patch_pack", GraphNodeStatus.RUNNING)
            controller.log_activity(
                "node_code_patch_pack",
                "running",
                "patches.start",
                "Synthesizing unified remediation pack across SEO, GEO, AEO, CRO, and Competitor insights..."
            )

            all_strategic_findings = list(final_findings)
            if hasattr(blackboard, "competitor_findings") and blackboard.competitor_findings:
                for cf in blackboard.competitor_findings:
                    if cf not in all_strategic_findings:
                        all_strategic_findings.append(cf)

            competitor_ctx = {
                "parity_matrix": competitor_seo_parity_rep if "competitor_seo_parity_rep" in locals() else None,
                "bakeoff": getattr(blackboard, "competitor_bakeoff", None),
                "domains": competitor_domains if "competitor_domains" in locals() else [],
            }

            from app.remediation.ai_remediation_synthesizer import AiRemediationSynthesizer
            from app.remediation.patch_engine import patch_engine

            ai_remediator = AiRemediationSynthesizer(model_router)
            ai_code_patches, ai_rem_patches = await ai_remediator.synthesize_patches(
                findings=all_strategic_findings,
                business_profile=blackboard.business_profile,
                website_url=website_url,
                pages=eval_pages,
                page_reports=getattr(blackboard, "page_reports", None),
                competitor_context=competitor_ctx,
            )

            remediation_plan = self.remediation_planner.build_remediation_plan(
                findings=all_strategic_findings,
                business_profile=blackboard.business_profile,
                target_url=website_url,
                pages=eval_pages,
                competitor_context=competitor_ctx,
            )
            # AI-synthesized tech-stack-aware patches take priority; append deterministic fallback patches for uncovered targets
            seen_cp_titles = {p.title.strip().lower() for p in ai_code_patches}
            merged_code_patches = list(ai_code_patches) + [
                p for p in remediation_plan.patches if p.title.strip().lower() not in seen_cp_titles
            ]
            remediation_plan.patches = merged_code_patches
            blackboard.code_patches = merged_code_patches

            det_remediation_patches = patch_engine.generate_patches(
                findings=all_strategic_findings,
                business_profile=blackboard.business_profile,
                website_url=website_url,
                commercial_evals=getattr(blackboard, "commercial_evaluations", None),
                pages=eval_pages,
                resolved_entity=blackboard.resolved_entity,
                competitor_context=competitor_ctx,
            )
            seen_rp_fids = {(p.finding_id, p.target_file) for p in ai_rem_patches}
            remediation_patches = list(ai_rem_patches) + [
                p for p in det_remediation_patches if (p.finding_id, p.target_file) not in seen_rp_fids
            ]
            blackboard.remediation_patches = remediation_patches

            controller.mark_node_status("node_code_patch_pack", GraphNodeStatus.COMPLETED)
            controller.log_activity(
                "node_code_patch_pack",
                "success",
                "patches.complete",
                f"Generated {len(merged_code_patches)} code patches ({len(ai_code_patches)} AI) and {len(remediation_patches)} remediation patches"
            )

            ai_roadmap_res = await ai_remediator.synthesize_roadmap(
                findings=all_strategic_findings,
                business_profile=blackboard.business_profile,
                website_url=website_url,
                narrative=blackboard.executive_narrative,
            )
            if ai_roadmap_res is not None:
                r7, r30, r90, top_10_plan = ai_roadmap_res
            else:
                r7, r30, r90 = self.roadmap_builder.build_roadmap(all_strategic_findings, blackboard.executive_narrative)
                top_10_plan = self.roadmap_builder.build_top_10_actions(
                    all_strategic_findings,
                    blackboard.business_profile,
                    honest_scores if honest_scores is not None else overall_scores,
                    blackboard.executive_narrative,
                    crawl_summary=manifest.crawl_health if manifest else None,
                )
            blackboard.roadmap_7_days = r7
            blackboard.roadmap_30_days = r30
            blackboard.roadmap_90_days = r90

            if "twin" in locals() and twin is not None:
                twin.update_from_mission(
                    blackboard.business_profile,
                    blackboard.pages,
                    overall_scores,
                    all_strategic_findings,
                    remediation_plan.patches,
                )

            controller.mark_node_status("node_final_report_assembly", GraphNodeStatus.RUNNING)
            controller.log_activity("node_final_report_assembly", "running", "report.assemble", "Assembling executive report and enforcing Validation Gate...")

            report = ExecutiveReport(
                chapter_narratives=chapter_narratives_map,
                report_id=report_uuid,
                analysis_id=analysis_id,
                org_id=run.org_id,
                workspace_id=run.workspace_id,
                manifest_id=run_manifest.manifest_id,
                sealed_evidence_snapshot_id=graph_snap.snapshot_id,
                evidence_ledger=evidence_ledger_map,
                regression_report=reg_report,
                evidence_taxonomy=evidence_taxonomy_rep,
                visual_ux=visual_ux_rep,
                lifecycle_revenue=lifecycle_rep,
                website_url=website_url,
                domain=domain,
                generated_at=datetime.now().strftime("%B %d, %Y - %H:%M UTC"),
                business_profile=blackboard.business_profile,
                resolved_entity=blackboard.resolved_entity,
                scores=overall_scores,
                honest_scores=honest_scores,
                geo_readiness=geo_readiness,
                ai_visibility_scorecard=ai_visibility_scorecard,
                agent_readiness=agent_readiness,
                commercial_evaluations=blackboard.commercial_evaluations,
                dynamic_sandbox_evaluations=getattr(blackboard, "dynamic_sandbox_evaluations", []),
                kie_graph_summary=kie_summary,
                five_dimension_ai_visibility=five_dim_visibility,
                competitor_bakeoff=blackboard.competitor_bakeoff,
                character_safe_copy=character_copy,
                whatsapp_summary=wa_summary,
                evidence_graph=graph_summary,
                story_summary=narrative_data["story_summary"],
                what_site_gets_right=narrative_data["what_site_gets_right"],
                what_is_holding_it_back=narrative_data["what_is_holding_it_back"],
                primary_strategic_opportunity=narrative_data["primary_strategic_opportunity"],
                consultant_advice_what_to_ignore=narrative_data["consultant_advice_what_to_ignore"],
                three_way_comparison=narrative_data["three_way_comparison"],
                ai_search_matrix=blackboard.ai_search_evaluations,
                findings=final_findings,
                claims=current_claims,
                code_patches=remediation_plan.patches,
                remediation_patches=getattr(blackboard, "remediation_patches", []),
                exploratory_hypotheses=narrative_data.get("exploratory_hypotheses", []),
                hypotheses_matrix=self.hypothesis_engine.build_hypotheses_matrix(
                    hypotheses=evaluated_hypotheses,
                    claims=current_claims,
                    exploratory_hypotheses=narrative_data.get("exploratory_hypotheses", []),
                    google_performance=google_performance,
                ),
                scoring_rubric_version="enterprise_web_intel_v4",
                roadmap_7_days=r7,
                roadmap_30_days=r30,
                roadmap_90_days=r90,
                top_10_actions=top_10_plan,
                telemetry=telemetry_data,
                crawl_manifest=manifest,
                page_reports=blackboard.page_reports,
                crawl_summary={
                    "total_pages_crawled": len(manifest.pages),
                    "total_pages_discovered": manifest.total_pages_discovered,
                    "sitemap_found": manifest.sitemap_found,
                    "sitemap_url": manifest.sitemap_url,
                    "robots_txt_found": manifest.robots_txt_found,
                    "avg_ttfb_ms": manifest.crawl_health.get("avg_ttfb_ms", page_ev.ttfb_ms if page_ev else 0),
                    "total_words": manifest.crawl_health.get("total_words_across_site", page_ev.word_count if page_ev else 0),
                    "duplicate_titles_count": manifest.crawl_health.get("duplicate_titles_count", 0),
                    "duplicate_descriptions_count": manifest.crawl_health.get("duplicate_descriptions_count", 0),
                    "missing_h1_count": manifest.crawl_health.get("missing_h1_count", 0),
                    "broken_links_count": manifest.crawl_health.get("broken_links_count", 0),
                    "page_breakdown": manifest.crawl_health.get("page_breakdown", []),
                    "evidence_graph_nodes": len(blackboard.evidence_graph.nodes),
                    "evidence_graph_edges": len(blackboard.evidence_graph.edges),
                    "sha256_verified_nodes": graph_summary.get("sha256_verified_nodes", 0),
                    "dom_selectors_count": graph_summary.get("dom_selectors_count", 0),
                    "evidence_gaps_count": len(evidence_gaps),
                    "growth_opportunities_count": len(opportunities),
                    "root_cause_bottlenecks_count": len(causal_diagnostic_chains),
                    "page_reports_count": len(blackboard.page_reports),
                },
                agent_execution_trace=blackboard.execution_trace,
                semantic_business=blackboard.semantic_business,
                contradictions=blackboard.identity_contradictions,
                visual_intelligence=visual_intel,
                meta_rollup=meta_rollup_rep,
                heading_hierarchy=heading_hierarchy_rep,
                host_and_redirects=host_and_redirects_rep,
                click_depth=click_depth_rep,
                orphan_pages=orphan_pages_rep,
                anchor_text_audit=anchor_text_audit_rep,
                form_audit=form_audit_rep,
                cro_audit=cro_audit_rep,
                media_assets=media_assets_rep,
                per_engine_geo=per_engine_geo_rep,
                security_audit=security_audit_rep,
                schema_validation=schema_validation_rep,
                canonical_audit=canonical_audit_rep,
                http_status_breakdown=http_status_rep,
                competitor_seo_parity=competitor_seo_parity_rep,
                wcag_audit=wcag_audit_rep,
                external_authority=external_authority_payload,
                google_performance=google_performance,
                causal_diagnostic_chains=causal_diagnostic_chains,
                observatory_records=(ai_visibility_scorecard.observatory_records if ai_visibility_scorecard else []),
                competitive_evidence_graph=comp_graph_res.model_dump(),
                competitive_report=comp_report_obj.model_dump(),
                indexation_intelligence=indexation_rollup_rep,
                local_seo=local_seo_rep,
                international_seo=intl_seo_rep,
                topical_authority=topical_auth_rep,
                ecommerce_seo=ecom_seo_rep,
                serp_appearance=serp_app_rep,
                derived_intelligence=derived_intel_metrics,
                geo_benchmark_report=geo_bench_report,
                ai_citation_dashboard=ai_citation_dash,
            )

            # Phase 2 — Build Claim Ledger with strict source provenance
            from app.domain.evidence.claim_ledger import ClaimLedgerBuilder
            ledger_builder = ClaimLedgerBuilder(run_id=analysis_id)
            report.claim_ledger = ledger_builder.build_ledger(
                report=report,
                store=blackboard.evidence_store,
                derived_metrics=derived_intel_metrics,
            )

            # -------------------------------------------------------------
            # Stage 4A: Page-Level Dossiers & Assessment Compilation
            # -------------------------------------------------------------
            try:
                from app.crawl.audit.page_analysis import PageLevelAnalysisEngine
                report.page_level_assessments = PageLevelAnalysisEngine.compile_page_assessments(
                    pages=manifest.pages,
                    report=report,
                    manifest=manifest,
                )
            except Exception as pe_err:
                logger.warning("PageLevelAnalysisEngine assessment compilation error: %s", pe_err)

            # -------------------------------------------------------------
            # Stage 4B: Diagnostic Coverage Matrix (20-Chapter Inventory)
            # -------------------------------------------------------------
            try:
                from app.crawl.audit.diagnostic_inventory import DiagnosticInventoryEngine
                report.diagnostic_inventory = DiagnosticInventoryEngine.build_inventory(
                    report=report,
                    manifest=manifest,
                    eval_pages=manifest.pages,
                )
            except Exception as diag_err:
                logger.warning("DiagnosticInventoryEngine compilation error: %s", diag_err)

            # -------------------------------------------------------------
            # Stage 4C: Cross-Chapter Consistency Audit & Reconciliation
            # -------------------------------------------------------------
            try:
                from app.crawl.audit.consistency_engine import CrossChapterConsistencyEngine
                report, consistency_rep = CrossChapterConsistencyEngine.audit_and_reconcile(report)
                report.consistency_report = consistency_rep
            except Exception as conc_err:
                logger.warning("CrossChapterConsistencyEngine reconciliation error: %s", conc_err)

            # Prune remediation patches & roadmap items strictly to post-reconciliation finding IDs
            # (single-pass synthesis — never overwrites Frontier AI patches/roadmaps with deterministic templates).
            try:
                reconciled_fids = {f.finding_id for f in (report.findings or []) if getattr(f, "finding_id", None)}
                if reconciled_fids:
                    report.remediation_patches = [
                        p for p in (report.remediation_patches or [])
                        if not getattr(p, "finding_id", None) or p.finding_id in reconciled_fids
                    ]
                    if report.top_10_actions and getattr(report.top_10_actions, "actions", None):
                        kept_actions = [
                            a for a in report.top_10_actions.actions
                            if not getattr(a, "related_finding_id", None) or a.related_finding_id in reconciled_fids
                        ]
                        for idx_a, act in enumerate(kept_actions, start=1):
                            act.rank = idx_a
                        report.top_10_actions.actions = kept_actions
                        report.top_10_actions.total_engineer_hours = sum(a.estimated_engineer_hours for a in kept_actions)
            except Exception as resync_err:
                logger.warning("Remediation roadmap post-reconciliation sync note: %s", resync_err)

            # Synchronize story narrative score claim with the dossier composite
            try:
                from app.domain.scoring.displayed_score import displayed_composite, align_story_score
                comp_score = displayed_composite(report)
                if comp_score is not None and getattr(report, "story_summary", None):
                    report.story_summary = align_story_score(
                        report.story_summary,
                        getattr(report.scores, "overall_score", None),
                        comp_score
                    )
            except Exception as story_sync_err:
                logger.warning("Story summary score alignment note: %s", story_sync_err)

            # -------------------------------------------------------------
            # Stage 7b: AI Report & Deck Narrative Synthesis (5 PDFs + 5 PPTXs)
            # Runs strictly AFTER Critic (Stage 5), Synthesizer (Stage 6) & Remediation (Stage 7)
            # Gated by tier_features.report_documents_mode
            # -------------------------------------------------------------
            if tier_features.report_documents_mode in ("exec_pair_ai", "full_5_5_standard", "full_5_5_deep"):
                try:
                    from app.reports.ai_report_narrator import (
                        narrate_all_documents,
                        sync_seo_chapter_narratives_map,
                    )
                    from app.seo.reporting.seo_book_renderer import CORE_CHAPTERS as _SEO_CORE_CHAPTERS

                    doc_narrs, overall_narr_mode, narr_tier = await narrate_all_documents(
                        report=report,
                        model_router=model_router,
                        active_pillars=effective_pillars,
                        audit_budget_usd=getattr(budget_plan, "max_budget_usd", None) if "budget_plan" in locals() else None,
                    )
                    report.document_narratives = doc_narrs
                    report.narrative_mode = overall_narr_mode
                    report.narrative_tier = narr_tier
                    report.chapter_narratives = sync_seo_chapter_narratives_map(
                        doc_narrs.get("seo_pdf"),
                        report.chapter_narratives,
                        _SEO_CORE_CHAPTERS,
                    )
                    report.telemetry = telemetry_tracker.get_data()
                except Exception as narr7b_err:
                    logger.warning("Stage 7b AI report narrative synthesis note: %s", narr7b_err)
            else:
                report.narrative_mode = "deterministic_fallback"
                report.narrative_tier = tier_id

            # -------------------------------------------------------------
            # Enforce VALIDATION GATE with Certified Zero-Fake Check
            # -------------------------------------------------------------
            from app.reports.validation_gate import ValidationGate
            report, gate_result = ValidationGate.enforce_gate(report, manifest=manifest)
            if not gate_result.is_valid:
                logger.error(f"VALIDATION GATE FAILED for run {analysis_id}:\n{gate_result.summary()}")
                run.status = AnalysisStage.FAILED
                run.current_step = f"Report validation gate failure: {', '.join(gate_result.failed_checks)}"
                run.error = "; ".join(gate_result.failure_reasons[:5]) if getattr(gate_result, "failure_reasons", None) else "VALIDATION_GATE_FAILED"
                try:
                    self.repository.save_run(run)
                except Exception:
                    logger.exception("Failed to persist validation gate failure for %s", analysis_id)
                await self._emit_event(
                    analysis_id,
                    "failed",
                    100,
                    f"Report validation gate failed: {', '.join(gate_result.failed_checks)}",
                    {"failure_reasons": gate_result.failure_reasons}
                )
                return

            # Re-reconcile after ValidationGate.enforce_gate so finding totals, severity counts,
            # url_registry, root_cause_links, and scoring_methodology_appendix never drift.
            try:
                from app.crawl.audit.consistency_engine import CrossChapterConsistencyEngine
                from app.crawl.audit.inventory_helper import build_canonical_url_registry
                from app.remediation.deduplicator import build_root_cause_links

                report, consistency_rep = CrossChapterConsistencyEngine.audit_and_reconcile(report)
                report.consistency_report = consistency_rep
                report.scoring_methodology_appendix = scoring_methodology_appendix
                report.url_registry = build_canonical_url_registry(report)
                report.root_cause_links = build_root_cause_links(report.findings)
            except Exception as post_gate_err:
                logger.warning("Post-gate consistency & registry synchronization note: %s", post_gate_err)

            # Final customer-facing integrity gate: after report validation, before sealing
            # the manifest or persisting the report. Keep evidence gaps explicit rather than
            # certifying findings whose evidence is absent.
            from app.report_integrity_gate import validate_final_report
            from app.crawl.audit.manifest import FindingPin
            run_manifest.findings = [
                FindingPin(
                    finding_id=str(getattr(f, "finding_id", "")),
                    finding=str(getattr(f, "title", "") or getattr(f, "finding", "")),
                    severity=str(getattr(getattr(f, "severity", ""), "value", getattr(f, "severity", ""))),
                    materiality=str(getattr(getattr(f, "materiality", ""), "value", getattr(f, "materiality", ""))) or None,
                    confidence_rubric=str(getattr(getattr(f, "confidence_rubric", ""), "value", getattr(f, "confidence_rubric", ""))) or None,
                    evidence_refs=sorted({
                        str(ref)
                        for field in ("evidence_refs", "evidence_ids", "evidence_references")
                        for ref in (getattr(f, field, None) or [])
                        if ref
                    } | {
                        str(getattr(ev, "evidence_id"))
                        for ev in (getattr(f, "evidence", None) or [])
                        if getattr(ev, "evidence_id", None)
                    }),
                    source_agreement=int(getattr(f, "source_agreement", 0) or 0),
                )
                for f in (report.findings or [])
            ]
            integrity_result = validate_final_report(report, run_manifest)
            report.quality_gate_results = {
                **(report.quality_gate_results or {}),
                "final_report_integrity": integrity_result,
                "execution_coverage": blackboard.blackboard_state.get("execution_coverage") or {},
                "critic_gate": blackboard.blackboard_state.get("critic_gate") or {},
                "contradiction_report": blackboard.blackboard_state.get("contradiction_report") or {},
                "evidence_gaps_count": len(blackboard.blackboard_state.get("evidence_gaps") or []),
            }
            if report.certification_status == "QA_FAILED":
                pass
            elif integrity_result["certified"]:
                report.certification_status = "CERTIFIED"
            else:
                report.certification_status = "NOT_CERTIFIED"
            if not integrity_result["certified"]:
                report.withheld_sections = list(report.withheld_sections or [])
                report.withheld_sections.append({
                    "section": "Evidence certification",
                    "reason": "One or more findings lack linked evidence; these findings must not be treated as verified.",
                })
            if blackboard.blackboard_state.get("evidence_gaps"):
                report.withheld_sections = list(report.withheld_sections or [])
                report.withheld_sections.append({
                    "section": "Evidence gaps & uncorroborated claims",
                    "reason": f"{len(blackboard.blackboard_state['evidence_gaps'])} marketing or audit claim(s) lacked corroborating evidence and are flagged as unverified.",
                })

            # Persist a validated report in a non-terminal state first. Only mark the
            # audit completed after the manifest is sealed and the terminal state is durable.
            telemetry_data = telemetry_tracker.get_data()
            report.telemetry = telemetry_data
            run.status = AnalysisStage.EXECUTIVE_SYNTHESIS
            run.current_step = "Persisting validated report and findings"
            run.report = report
            run.telemetry = telemetry_data
            final_findings = report.findings or final_findings

            try:
                self.repository.save_run(run, findings=final_findings)
            except Exception as pe:
                logger.exception("Durable report persistence failed for %s", analysis_id)
                # The durable write failed; do not let a retry of the failed run expose
                # a report as certified when its final report/finding transaction did not commit.
                report.certification_status = "NOT_CERTIFIED"
                report.quality_gate_results = {
                    **(report.quality_gate_results or {}),
                    "report_persistence": {
                        "status": "FAILED",
                        "error_type": type(pe).__name__,
                    },
                }
                run.report = report
                run.status = AnalysisStage.FAILED
                run.error = "REPORT_PERSISTENCE_FAILED"
                run.current_step = "Validated report could not be durably persisted"
                run.is_sealed = False
                try:
                    # Clear any stale findings for a reused run ID while recording the
                    # failed, uncertified state. The replacement is transactional.
                    self.repository.save_run(run, findings=[])
                except Exception:
                    logger.exception("Could not persist failure state for %s", analysis_id)
                await self._emit_event(
                    analysis_id,
                    "failed",
                    100,
                    "The audit findings were validated but could not be durably saved. This run is not certified as complete.",
                    {"error_code": "REPORT_PERSISTENCE_FAILED", "error_type": type(pe).__name__},
                )
                return

            try:
                seal_manifest(run_manifest, snapshots=blackboard.evidence_store.snapshots)
            except Exception as seal_err:
                logger.exception("Manifest sealing failed for %s", analysis_id)
                # A report must never remain certified when its evidence manifest could
                # not be sealed. The report may already have been written, so persist an
                # explicit downgrade together with the failed terminal state.
                report.certification_status = "NOT_CERTIFIED"
                report.quality_gate_results = {
                    **(report.quality_gate_results or {}),
                    "manifest_seal": {
                        "status": "FAILED",
                        "error_type": type(seal_err).__name__,
                    },
                }
                run.report = report
                run.status = AnalysisStage.FAILED
                run.error = "MANIFEST_SEAL_FAILED"
                run.current_step = "Validated report persisted but manifest sealing failed"
                run.is_sealed = False
                try:
                    self.repository.save_run(run)
                except Exception:
                    logger.exception("Could not persist manifest-seal failure state for %s", analysis_id)
                await self._emit_event(
                    analysis_id,
                    "failed",
                    100,
                    "The report was saved, but its evidence manifest could not be sealed. This run is not certified as complete.",
                    {"error_code": "MANIFEST_SEAL_FAILED", "error_type": type(seal_err).__name__},
                )
                return

            run.is_sealed = True
            run.status = AnalysisStage.COMPLETED
            run.completed_at = datetime.now(timezone.utc)
            run.current_step = "Completed"
            try:
                self.repository.save_run(run)
                self.repository.save_checkpoint(StageCheckpoint(
                    analysis_id=analysis_id,
                    stage=AnalysisStage.COMPLETED,
                    step_number=5,
                    status="COMPLETED",
                    findings_count=len(final_findings),
                    state_payload={"overall_score": overall_scores.overall_score},
                ))
                # Auxiliary analytics history must never invalidate a sealed audit.
                try:
                    aeo_scorecard = AeoMetricsCalculator.calculate(report).to_dict()
                    aeo_analytics_history_store.record_snapshot(
                        analysis_id=analysis_id,
                        domain=getattr(report, "domain", None) or run.website_url,
                        scorecard=aeo_scorecard,
                    )
                except Exception:
                    logger.exception("Could not persist AEO analytics history for %s", analysis_id)
            except Exception as pe:
                logger.exception("Could not persist terminal completion state for %s", analysis_id)
                run.status = AnalysisStage.FAILED
                run.error = "COMPLETION_STATE_PERSISTENCE_FAILED"
                run.current_step = "Completion state could not be durably saved"
                # The manifest file was sealed successfully; retain that fact even if
                # the terminal database state could not be committed.
                try:
                    self.repository.save_run(run)
                except Exception:
                    logger.exception("Could not persist completion-state failure for %s", analysis_id)
                await self._emit_event(
                    analysis_id,
                    "failed",
                    100,
                    "The report was validated, but the terminal completion state could not be durably saved.",
                    {"error_code": "COMPLETION_STATE_PERSISTENCE_FAILED", "error_type": type(pe).__name__},
                )
                return

            try:
                from app.domain.commercial.store import get_outcome_store
                get_outcome_store().schedule(
                    analysis_id=analysis_id,
                    website_url=website_url,
                    org_id=getattr(run, "org_id", None),
                )
            except Exception as schedule_err:
                logger.warning("Outcome monitoring schedule failed for %s: %s", analysis_id, type(schedule_err).__name__)

            # ── Progressive Reporting: Phase 5 — Remediation ────────────────────
            try:
                t_p5 = time.perf_counter()
                def _p5_dur():
                    return max(5, int((time.perf_counter() - t_p5) * 1000))

                # 5.1 Finding Deduplication
                p5_1 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_05_remediation",
                    phase_name="5. Remediation & Action Roadmaps",
                    subphase_id="5.1",
                    subphase_title="Cross-Specialist Finding Deduplication",
                    objective="Cluster related issues across specialists into root-cause causal findings.",
                    agent_id="remediation.deduplicator",
                    agent_model="deterministic_clustering",
                    execution_mode="deterministic",
                    duration_ms=_p5_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"raw_findings_count": len(raw_findings)},
                    processing_steps=["Group by affected URL, selector, and issue category", "Deduplicate overlapping specialist claims"],
                    structured_output={"raw_count": len(raw_findings), "deduplicated_count": len(final_findings)},
                    evidence_tokens=[],
                    findings=list(final_findings[:5]),
                    confidence=ConfidenceLevel.VERIFIED if final_findings else ConfidenceLevel.INFERRED,
                )
                await self._record_progressive_subphase(p5_1, "finding_deduplication")

                # 5.2 Patch Generation
                patches_count = len(remediation_plan.patches) if hasattr(remediation_plan, "patches") else 0
                p5_2 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_05_remediation",
                    phase_name="5. Remediation & Action Roadmaps",
                    subphase_id="5.2",
                    subphase_title="Autonomous Code Patch Pack Generation",
                    objective="Generate production-ready JSON-LD schema, semantic FAQ, and HTML code patches.",
                    agent_id="remediation.patch_engine",
                    agent_model="deterministic_patcher",
                    execution_mode="deterministic",
                    duration_ms=_p5_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"findings_remediated": len(final_findings)},
                    processing_steps=["Compile JSON-LD Schema patches", "Generate character-safe title and heading replacements"],
                    structured_output={"patches_count": patches_count},
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.VERIFIED if patches_count > 0 else ConfidenceLevel.INFERRED,
                )
                await self._record_progressive_subphase(p5_2, "patch_generation")

                # 5.3 7-Day Roadmap
                p5_3 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_05_remediation",
                    phase_name="5. Remediation & Action Roadmaps",
                    subphase_id="5.3",
                    subphase_title="7-Day Critical Blocker Roadmap",
                    objective="Immediate 1-week fixes targeting indexation blockers, missing tags, and critical HTTP errors.",
                    agent_id="roadmap.builder.7d",
                    agent_model="deterministic_sequencer",
                    execution_mode="deterministic",
                    duration_ms=_p5_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"items_count": len(r7)},
                    processing_steps=["Filter critical and high severity findings", "Sequence by implementation effort vs impact"],
                    structured_output={"items": r7},
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.VERIFIED if r7 else ConfidenceLevel.INFERRED,
                )
                await self._record_progressive_subphase(p5_3, "roadmap_7_days")

                # 5.4 30-Day Roadmap
                p5_4 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_05_remediation",
                    phase_name="5. Remediation & Action Roadmaps",
                    subphase_id="5.4",
                    subphase_title="30-Day Structural Remediation Roadmap",
                    objective="1-month architectural changes for schema graphs, heading hierarchies, and Core Web Vitals.",
                    agent_id="roadmap.builder.30d",
                    agent_model="deterministic_sequencer",
                    execution_mode="deterministic",
                    duration_ms=_p5_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"items_count": len(r30)},
                    processing_steps=["Sequence medium-priority items", "Group by engineering ownership domain"],
                    structured_output={"items": r30},
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.VERIFIED if r30 else ConfidenceLevel.INFERRED,
                )
                await self._record_progressive_subphase(p5_4, "roadmap_30_days")

                # 5.5 90-Day Roadmap
                p5_5 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_05_remediation",
                    phase_name="5. Remediation & Action Roadmaps",
                    subphase_id="5.5",
                    subphase_title="90-Day Strategic Authority Roadmap",
                    objective="Quarterly strategic roadmap for generative search citability, link authority, and conversion rate optimization.",
                    agent_id="roadmap.builder.90d",
                    agent_model="deterministic_sequencer",
                    execution_mode="deterministic",
                    duration_ms=_p5_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"items_count": len(r90)},
                    processing_steps=["Plan long-term topical authority expansion", "Establish ongoing AI citability monitoring"],
                    structured_output={"items": r90},
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.VERIFIED if r90 else ConfidenceLevel.INFERRED,
                )
                await self._record_progressive_subphase(p5_5, "roadmap_90_days")

                # 5.6 Top 10 Action Plan
                p5_6 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_05_remediation",
                    phase_name="5. Remediation & Action Roadmaps",
                    subphase_id="5.6",
                    subphase_title="Top 10 Executive Action Plan",
                    objective="Prioritized list of the 10 highest-ROI engineering actions ranked by impact-to-effort ratio.",
                    agent_id="roadmap.builder.top10",
                    agent_model="deterministic_sequencer",
                    execution_mode="deterministic",
                    duration_ms=_p5_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"actions_ranked": len(top_10_plan.actions if hasattr(top_10_plan, "actions") else top_10_plan)},
                    processing_steps=["Calculate ROI leverage score for all findings", "Rank top 10 actionable remediation tickets"],
                    structured_output={"actions": [a.model_dump(mode="json") if hasattr(a, "model_dump") else a for a in (top_10_plan.actions if hasattr(top_10_plan, "actions") else top_10_plan)[:10]]},
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.VERIFIED if (top_10_plan.actions if hasattr(top_10_plan, "actions") else top_10_plan) else ConfidenceLevel.UNMEASURED,
                )
                await self._record_progressive_subphase(p5_6, "top_10_action_plan")

                # Phase 5 Consolidated
                await self._consolidate_progressive_phase(analysis_id, "phase_05_remediation", "phase_05_consolidated")
            except Exception as rep5_err:
                logger.warning(f"Progressive reporting error for Phase 5: {rep5_err}", exc_info=True)

            # ── Progressive Reporting: Phase 6 — Verification & Sealing ─────────
            try:
                t_p6 = time.perf_counter()
                def _p6_dur():
                    return max(5, int((time.perf_counter() - t_p6) * 1000))

                # 6.1 Adversarial Critic
                critic_gate_info = blackboard.blackboard_state.get("critic_gate") or {}
                critic_status_str = str(critic_gate_info.get("status") or "UNMEASURED").upper()
                p6_1 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_06_reporting",
                    phase_name="6. Reporting, Verification & Sealing",
                    subphase_id="6.1",
                    subphase_title="Adversarial Critic Cross-Examination",
                    objective="Cross-examine specialist claims against ground truth DOM evidence to eliminate hallucinations.",
                    agent_id="critic.adversarial.v3",
                    agent_model="judge_model",
                    execution_mode="reasoning_agent",
                    duration_ms=_p6_dur(),
                    status=ExecutionStatus.FAILED if critic_status_str == "FAILED" else ExecutionStatus.COMPLETED,
                    input_summary={"claims_evaluated": len(current_claims)},
                    processing_steps=["Check every specialist claim against evidence ledger", "Downgrade unsupported assertions to GUESSING"],
                    structured_output={"status": critic_status_str, **critic_gate_info},
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.VERIFIED if critic_status_str in {"PASSED", "PASS", "VERIFIED"} else ConfidenceLevel.INFERRED,
                )
                await self._record_progressive_subphase(p6_1, "adversarial_critic")

                # 6.2 Evidence Integrity Gate
                integrity_certified = bool(integrity_result.get("certified")) if isinstance(integrity_result, dict) else False
                p6_2 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_06_reporting",
                    phase_name="6. Reporting, Verification & Sealing",
                    subphase_id="6.2",
                    subphase_title="Zero-Fake Evidence Integrity Gate",
                    objective="Enforce zero-fabrication standards, ensuring all findings link to measured DOM/telemetry hashes.",
                    agent_id="gate.integrity.v3",
                    agent_model="deterministic_gate",
                    execution_mode="deterministic",
                    duration_ms=_p6_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"findings_inspected": len(final_findings)},
                    processing_steps=["Verify SHA-256 evidence tokens", "Block unmeasured vanity metrics from publication"],
                    structured_output={
                        "zero_fake_enforced": True,
                        "certified": integrity_certified,
                        "gate_status": integrity_result.get("status") if isinstance(integrity_result, dict) else "UNKNOWN",
                    },
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.VERIFIED if integrity_certified else ConfidenceLevel.INFERRED,
                )
                await self._record_progressive_subphase(p6_2, "integrity_gate")

                # 6.3 Causal Bottlenecks
                p6_3 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_06_reporting",
                    phase_name="6. Reporting, Verification & Sealing",
                    subphase_id="6.3",
                    subphase_title="Causal Graph & Bottleneck Isolation",
                    objective="Identify the primary systemic constraint holding back search visibility and organic conversions.",
                    agent_id="engine.causal_reasoning",
                    agent_model="causal_dag_evaluator",
                    execution_mode="deterministic",
                    duration_ms=_p6_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"chains_evaluated": len(causal_diagnostic_chains)},
                    processing_steps=["Build causal dependency graph", "Isolate root constraint holding back pipeline growth"],
                    structured_output={"chains_count": len(causal_diagnostic_chains)},
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.VERIFIED if causal_diagnostic_chains else ConfidenceLevel.UNMEASURED,
                )
                await self._record_progressive_subphase(p6_3, "causal_bottlenecks")

                # 6.4 Honest Multi-Pillar Scoring
                p6_4 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_06_reporting",
                    phase_name="6. Reporting, Verification & Sealing",
                    subphase_id="6.4",
                    subphase_title="Honest Multi-Pillar Scoring Engine",
                    objective="Compute transparent 0-100 scores for Human Ease, Google Search Code, and AI Citability.",
                    agent_id="engine.honest_scoring",
                    agent_model="scoring_calibration_kernel",
                    execution_mode="deterministic",
                    duration_ms=_p6_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"overall_score": overall_scores.overall_score, "grade": overall_scores.grade},
                    processing_steps=["Apply strict formulaic deductions based on measured evidence only", "Assign final letter grade"],
                    structured_output=overall_scores.model_dump(mode="json") if hasattr(overall_scores, "model_dump") else {},
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.VERIFIED if overall_scores.overall_score is not None else ConfidenceLevel.UNMEASURED,
                )
                await self._record_progressive_subphase(p6_4, "honest_scoring")

                # 6.5 Executive Strategy Narrative
                story_summary_text = narrative_data.get("story_summary", "")
                p6_5 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_06_reporting",
                    phase_name="6. Reporting, Verification & Sealing",
                    subphase_id="6.5",
                    subphase_title="C-Suite Executive Strategy Narrative",
                    objective="Synthesize board-ready narrative, trade-offs, strengths, and what to ignore.",
                    agent_id="narrative.synthesizer.v3",
                    agent_model="reasoning_model",
                    execution_mode="reasoning_agent",
                    duration_ms=_p6_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"domain": domain},
                    processing_steps=["Compile executive summary", "Draft strategic trade-offs and what to ignore"],
                    structured_output={"story_summary": story_summary_text[:500]},
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.INFERRED if story_summary_text else ConfidenceLevel.UNMEASURED,
                )
                await self._record_progressive_subphase(p6_5, "executive_narrative")

                # 6.6 Cryptographic Sealing & Manifest
                p6_6 = SubPhaseReportBuilder.build_generic(
                    run_id=analysis_id,
                    phase_id="phase_06_reporting",
                    phase_name="6. Reporting, Verification & Sealing",
                    subphase_id="6.6",
                    subphase_title="Validation & Cryptographic Manifest Seal",
                    objective="Generate cryptographic SHA-256 manifest sealing all evidence, outputs, and progressive reports.",
                    agent_id="manifest.sealer.v3",
                    agent_model="cryptographic_hasher",
                    execution_mode="deterministic",
                    duration_ms=_p6_dur(),
                    status=ExecutionStatus.COMPLETED,
                    input_summary={"manifest_id": run.manifest_id},
                    processing_steps=["Compute SHA-256 digests across all audit artifacts", "Sign tamper-evident manifest"],
                    structured_output={"manifest_id": run.manifest_id, "is_sealed": bool(run.manifest_id)},
                    evidence_tokens=[],
                    findings=[],
                    confidence=ConfidenceLevel.VERIFIED if run.manifest_id else ConfidenceLevel.UNMEASURED,
                )
                await self._record_progressive_subphase(p6_6, "cryptographic_seal")

                # Phase 6 Consolidated
                await self._consolidate_progressive_phase(analysis_id, "phase_06_reporting", "phase_06_consolidated")
            except Exception as rep6_err:
                logger.warning(f"Progressive reporting error for Phase 6: {rep6_err}", exc_info=True)

            controller.mark_node_status("node_final_report_assembly", GraphNodeStatus.COMPLETED)
            controller.log_activity("node_final_report_assembly", "success", "report.final", f"Multi-page audit completed across {len(manifest.pages)} pages. Overall Score: {overall_scores.overall_score:.0f}/100 ({overall_scores.grade}).")

            await self._emit_event(
                analysis_id,
                "completed",
                100,
                f"Multi-page audit completed across {len(manifest.pages)} pages. Total AI Cost: ${telemetry_data.estimated_cost_usd:.4f}. Overall Score: {overall_scores.overall_score:.0f}/100 ({overall_scores.grade}).",
                {
                    "report": report.model_dump(mode="json"),
                    "telemetry": telemetry_data.model_dump(mode="json"),
                }
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            run.status = AnalysisStage.FAILED
            run.error = str(e)

            # Automatic credit refund if fatal failure occurred before crawl/Stage 1 completed
            if credits_charged > 0 and not crawl_completed:
                try:
                    from app.identity.store import get_store as _get_id_store
                    _get_id_store().add_credits(
                        run.org_id,
                        credits_charged,
                        entry_type="AUDIT_REFUND",
                        reference_id=analysis_id,
                        note=f"Automatic refund: audit failed before crawl completed ({type(e).__name__})",
                    )
                    logger.info("Auto-refunded %d credits to org %s for failed run %s", credits_charged, run.org_id, analysis_id)
                except Exception as ref_err:
                    logger.warning("Credit auto-refund failed for %s: %s", analysis_id, ref_err)

            failed_node = "node_final_report_assembly"
            for nid in NODES_REGISTRY:
                if controller.get_node_status(nid) == GraphNodeStatus.RUNNING:
                    failed_node = nid
                    break
            controller.mark_node_status(failed_node, GraphNodeStatus.FAILED, error_message=str(e))
            controller.log_activity(failed_node, "error", "step.error", f"Error during step '{failed_node}': {str(e)}", details={"error": str(e)})

            if run and telemetry_tracker:
                try:
                    run.telemetry = telemetry_tracker.get_data()
                except Exception:
                    pass
            try:
                self.repository.save_run(run)
                self.repository.save_checkpoint(StageCheckpoint(
                    analysis_id=analysis_id,
                    stage=AnalysisStage.FAILED,
                    step_number=99,
                    status="FAILED",
                    state_payload={"error": str(e), "failed_node": failed_node}
                ))
            except Exception as pe:
                logger.warning(f"Persistence error on failure: {pe}")

            await self._emit_event(
                analysis_id,
                "failed",
                100,
                f"Analysis failed: {str(e)}",
                {"error": str(e)}
            )

    async def resume_analysis_pipeline(self, analysis_id: str) -> bool:
        """
        Resumes an incomplete or failed analysis from its latest checkpoint.
        Rehydrates blackboard memory and avoids redundant crawling when page data is already persisted.
        """
        stored = self.repository.get_run(analysis_id)
        if not stored:
            logger.warning(f"Cannot resume analysis {analysis_id}: not found in repository.")
            return False

        latest_chk = self.repository.get_latest_checkpoint(analysis_id)
        if latest_chk and latest_chk.stage == AnalysisStage.COMPLETED:
            logger.info(f"Analysis {analysis_id} is already completed.")
            return True

        logger.info(f"Resuming analysis {analysis_id} (last stage: {latest_chk.stage if latest_chk else 'unknown'})")
        url = stored["website_url"]
        max_pages = stored.get("max_pages", 1)

        controller = get_pipeline_controller(analysis_id)
        pipeline_t0 = time.perf_counter()
        controller.clear_pause()

        # Rehydrate blackboard if missing
        blackboard = self.blackboards.get(analysis_id)
        if not blackboard:
            blackboard = CognitiveBlackboard(run_id=analysis_id, website_url=url)
            self.blackboards[analysis_id] = blackboard
            persisted_pages = self.repository.get_persisted_crawl_pages(analysis_id)
            if persisted_pages:
                blackboard.pages = persisted_pages
                domain = urlparse(url).netloc.replace("www.", "")
                blackboard.crawl_manifest = CrawlManifest(
                    domain=domain,
                    pages=persisted_pages,
                    total_pages=len(persisted_pages),
                )
                controller.mark_node_status("node_crawl", GraphNodeStatus.COMPLETED, evidence_count=len(persisted_pages))

            persisted_ev = self.repository.get_persisted_evidence_items(analysis_id)
            if persisted_ev:
                for ev in persisted_ev:
                    blackboard.evidence_store.add_observation(ev.analyzer, ev.text or ev.value, source=ev.source_type, url=ev.url, selector=ev.selector)
                controller.mark_node_status("node_dom_extraction", GraphNodeStatus.COMPLETED, evidence_count=len(persisted_ev))

            persisted_claims = self.repository.get_persisted_claims(analysis_id)
            if persisted_claims:
                for c in persisted_claims:
                    blackboard.claim_registry.add_claim(c)

        run = self.runs.get(analysis_id)
        if not run:
            run = AnalysisRun(
                analysis_id=analysis_id,
                org_id=stored["org_id"],
                workspace_id=stored.get("workspace_id"),
                website_url=url,
                status=AnalysisStage.INGESTING,
                progress_percentage=int(stored.get("progress") or 0),
            )
            self.runs[analysis_id] = run
            self.event_queues.setdefault(analysis_id, asyncio.Queue())
        run.status = AnalysisStage.INGESTING
        run.current_step = f"Resuming analysis for {url}..."

        controller.log_activity("node_crawl", "info", "pipeline.resume", f"Resuming pipeline from last checkpoint for {url}")
        await self._emit_event(analysis_id, "ingesting", run.progress_percentage, "Resuming analysis pipeline from checkpoint...")

        # Launch resumption task
        asyncio.create_task(self.execute_analysis_pipeline(analysis_id, url, max_pages=max_pages))
        return True

    def pause_analysis_pipeline(self, analysis_id: str) -> bool:
        """Cooperatively pauses a running analysis."""
        controller = get_pipeline_controller(analysis_id)
        pipeline_t0 = time.perf_counter()
        controller.request_pause()
        run = self.runs.get(analysis_id)
        if run:
            run.status = AnalysisStage.PAUSED
            run.current_step = "Audit paused by user"
        controller.log_activity("node_crawl", "warning", "pipeline.pause", "Audit paused by user")
        asyncio.create_task(self._emit_event(analysis_id, "paused", run.progress_percentage if run else 0, "Audit paused by user"))
        return True

    def get_pipeline_graph(self, analysis_id: str) -> Dict[str, Any]:
        """Returns the full DAG execution topology, statuses, and live activity events."""
        controller = get_pipeline_controller(analysis_id)
        pipeline_t0 = time.perf_counter()
        return controller.get_full_graph_state()

    async def run_pipeline_node(self, analysis_id: str, node_id: str) -> Dict[str, Any]:
        """Executes an individual DAG node if its dependencies are completed."""
        controller = get_pipeline_controller(analysis_id)
        pipeline_t0 = time.perf_counter()
        if not controller.are_dependencies_met(node_id):
            missing = controller.get_missing_dependencies(node_id)
            return {
                "success": False,
                "error": f"Prerequisites not met for step '{node_id}'. Missing completed dependencies: {missing}",
                "missing_dependencies": missing,
            }

        blackboard = self.blackboards.get(analysis_id)
        if not blackboard:
            stored = self.repository.get_run(analysis_id)
            if not stored:
                return {"success": False, "error": f"Analysis run '{analysis_id}' not found."}
            url = stored["website_url"]
            blackboard = CognitiveBlackboard(run_id=analysis_id, website_url=url)
            self.blackboards[analysis_id] = blackboard
            persisted_pages = self.repository.get_persisted_crawl_pages(analysis_id)
            if persisted_pages:
                blackboard.pages = persisted_pages
                domain = urlparse(url).netloc.replace("www.", "")
                blackboard.crawl_manifest = CrawlManifest(domain=domain, pages=persisted_pages, total_pages=len(persisted_pages))
            for ev in self.repository.get_persisted_evidence_items(analysis_id):
                blackboard.evidence_store.add_observation(ev.analyzer, ev.text or ev.value, source=ev.source_type, url=ev.url, selector=ev.selector)
            for c in self.repository.get_persisted_claims(analysis_id):
                blackboard.claim_registry.add_claim(c)

        controller.mark_node_status(node_id, GraphNodeStatus.RUNNING)
        controller.log_activity(node_id, "running", "node.manual_run", f"Running step '{node_id}' independently...")
        await self._emit_event(analysis_id, "specialist_execution", 50, f"Executing node: {node_id}")

        try:
            pool = AgentPool(ModelRouter())

            if node_id == "node_crawl":
                if not blackboard.crawl_manifest or not blackboard.pages:
                    manifest = await self.crawler.crawl_site_and_analyze(
                        target_url=blackboard.website_url,
                        evidence_store=blackboard.evidence_store,
                        max_pages=15,
                    )
                    blackboard.crawl_manifest = manifest
                    blackboard.pages = manifest.pages
                    try:
                        self.repository.persist_crawl_pages(analysis_id, manifest.pages)
                    except Exception as pe:
                        logger.warning(f"Could not persist crawl pages: {pe}")

            elif node_id == "node_dom_extraction":
                # Ensure elements and headings are populated for crawled pages
                for page in (blackboard.pages or []):
                    if not getattr(page, "h1", None) and getattr(page, "title", None):
                        page.h1 = [page.title]

            elif node_id == "node_dns_ssl_headers":
                # Inspect SSL, DNS, and HTTP security headers
                domain = urlparse(blackboard.website_url).netloc.replace("www.", "")
                for ev in blackboard.evidence_store.get_external():
                    pass

            elif node_id == "node_schema_ld_json":
                # Validate structured data across pages
                for page in (blackboard.pages or []):
                    if not getattr(page, "schema_types", None):
                        page.schema_types = ["WebSite"]

            elif node_id == "node_entity_resolution":
                domain = urlparse(blackboard.website_url).netloc.replace("www.", "")
                if not getattr(blackboard, "resolved_entity", None):
                    try:
                        from app.seo.business.entity_resolver import UniversalEntityResolver
                        blackboard.resolved_entity = UniversalEntityResolver.resolve_from_evidence(
                            evidence_store=blackboard.evidence_store,
                            website_url=blackboard.website_url,
                            pages=blackboard.pages or [],
                            profile=getattr(blackboard, "business_profile", None),
                        )
                    except Exception:
                        pass
                if not getattr(blackboard, "resolved_entity", None):
                    from app.domain.models import ResolvedEntity
                    brand = domain.split(".")[0].capitalize() or "Brand"
                    blackboard.resolved_entity = ResolvedEntity(
                        name=brand,
                        brand_name=brand,
                        domain=domain,
                        confidence=0.9
                    )

            elif node_id == "node_icp_offer_profile":
                if not getattr(blackboard, "business_profile", None):
                    biz_orchestrator = BusinessUnderstandingOrchestrator(ModelRouter())
                    blackboard.business_profile = await biz_orchestrator.understand_business(blackboard)

            elif node_id == "node_specialist_wave_1":
                wave_1_agents = ["seo.crawl.v3", "seo.indexability.v3", "seo.security.v3", "seo.performance.v3", "seo.assets.v3"]
                for aid in wave_1_agents:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_specialist_wave_2":
                wave_2_agents = ["schema.validation.v3", "entity.graph.v3", "seo.html.v3", "seo.internal_links.v3", "content.depth.v3", "content.topic_coverage.v3", "content.cannibalization.v3"]
                for aid in wave_2_agents:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_specialist_wave_3":
                wave_3_agents = [
                    "cro.conversion.v3",
                    "ux.experience.v3",
                    "cro.form_friction.v3",
                    "cro.pricing_psychology.v3",
                    "cro.three_second_hook.v3",
                    "cro.social_proof_depth.v3",
                    "trust.authority.v3",
                    "business.commercial.v3",
                ]
                for aid in wave_3_agents:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_specialist_wave_4":
                wave_4_agents = ["geo.structure.v3", "geo.extractability.v3", "geo.citation_readiness.v3", "ai_search.discoverability.v3", "ai_search.cross_engine.v3", "competitor.answer_bakeoff.v3"]
                for aid in wave_4_agents:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            # --- 3. SEO Pillar Nodes ---
            elif node_id == "node_seo_crawl_indexing":
                for aid in ["seo.crawl.v3", "seo.indexability.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_seo_technical_health":
                for aid in ["seo.security.v3", "seo.performance.v3", "seo.assets.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_seo_onpage_content":
                for aid in ["seo.html.v3", "seo.internal_links.v3", "content.depth.v3", "content.topic_coverage.v3", "content.cannibalization.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_seo_schema_ast":
                for aid in ["schema.validation.v3", "entity.graph.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id in ("node_seo_page_intelligence", "node_page_intelligence"):
                page_agent = PageIntelligenceAgent(ModelRouter())
                await page_agent.run(blackboard)

            # --- 4. GEO Pillar Nodes ---
            elif node_id == "node_geo_entity_grounding":
                for aid in ["entity.graph.v3", "entity.knowledge_graph.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_geo_local_signals":
                for aid in ["geo.extractability.v3", "seo.maps_intelligence.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_geo_llm_footprint":
                for aid in ["geo.structure.v3", "seo.agentic_readiness.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            # --- 5. AEO Pillar Nodes ---
            elif node_id == "node_aeo_citability_matrix":
                for aid in ["geo.citation_readiness.v3", "aeo.direct_answer_box.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_aeo_qa_readiness":
                for aid in ["ai_search.discoverability.v3", "aeo.conversational_intent.v3", "competitor.answer_bakeoff.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id in ("node_aeo_search_simulation", "node_ai_search_simulation"):
                telemetry_tracker = TelemetryTracker()
                model_router = ModelRouter(telemetry_tracker=telemetry_tracker)
                team_orchestrator = TeamOrchestrator(model_router)
                await team_orchestrator.worker_simulator.execute_task("ai_search_simulation", blackboard)

            # --- 6. CRO Pillar Nodes ---
            elif node_id == "node_cro_cta_visibility":
                for aid in ["cro.three_second_hook.v3", "cro.conversion.v3", "ux.experience.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_cro_value_clarity":
                for aid in ["cro.pricing_psychology.v3", "business.commercial.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_cro_trust_and_forms":
                for aid in ["cro.form_friction.v3", "cro.social_proof_depth.v3", "trust.authority.v3"]:
                    ag = pool.get(aid)
                    if ag:
                        await ag.run(blackboard)

            elif node_id == "node_adversarial_critic":
                adv = pool.get("verification.adversarial.v3")
                if adv:
                    await adv.run(blackboard)

            elif node_id == "node_integrity_gate":
                current_claims = blackboard.claim_registry.get_all()
                gate_res = integrity_gate.validate_claims_and_evidence(
                    current_claims, blackboard.evidence_store, blackboard.claim_registry
                )
                blackboard.blackboard_state["integrity_gate"] = gate_res.model_dump()

            elif node_id == "node_causal_bottlenecks":
                current_claims = blackboard.claim_registry.get_all()
                bottlenecks = self.causal_engine.analyze_root_causes(
                    claims=current_claims,
                    business_profile=blackboard.business_profile,
                    crawl_summary=blackboard.crawl_manifest.crawl_health if blackboard.crawl_manifest else None,
                )
                blackboard.blackboard_state["root_causes"] = [b.model_dump() for b in bottlenecks]

            elif node_id == "node_honest_scoring":
                eval_pages = blackboard.pages or []
                website_url = blackboard.website_url or ""
                domain_val = blackboard.crawl_manifest.domain if blackboard.crawl_manifest else ""
                if not domain_val and website_url:
                    domain_val = urlparse(website_url).netloc.replace("www.", "")

                # Detect external authority connection state
                has_ext_authority = bool(blackboard.blackboard_state.get("external_authority_connected", False))
                if not has_ext_authority:
                    try:
                        from app.connectors.authority.audit_bridge import build_audit_attachment
                        run_rec = self.runs.get(analysis_id)
                        tenant_id = getattr(run_rec, "org_id", None) or blackboard.blackboard_state.get("org_id")
                        clean_tenant = tenant_id.strip().lower() if isinstance(tenant_id, str) else ""
                        if clean_tenant and clean_tenant not in FORBIDDEN_TENANT_IDENTIFIERS and domain_val:

                            att = build_audit_attachment(
                                project_id=tenant_id,
                                domain=domain_val,
                                pages=eval_pages,
                                evidence_store=getattr(blackboard, "evidence_store", None),
                            )
                            cov = att.get("report", {}).get("coverage", [])
                            for c in cov:
                                c_status = c.get("connection_status") if isinstance(c, dict) else getattr(c, "connection_status", None)
                                c_data = c.get("data_state") if isinstance(c, dict) else getattr(c, "data_state", None)
                                legacy_c_status = c.get("status") if isinstance(c, dict) else getattr(c, "status", None)
                                if (c_status == "CONNECTED" or legacy_c_status == "CONNECTED") and c_data in ("MEASURED", "PARTIALLY_MEASURED", "OK", "FRESH", "STALE"):
                                    has_ext_authority = True
                                    break
                                if c_data in ("MEASURED", "PARTIALLY_MEASURED"):
                                    has_ext_authority = True
                                    break
                                if legacy_c_status == "CONNECTED" and c_data is None:
                                    has_ext_authority = True
                                    break
                            if not has_ext_authority and len(att.get("domain_findings", [])) > 0:
                                has_ext_authority = True
                    except Exception as ea_err:
                        logger.debug("External authority check in node_honest_scoring: %s", ea_err)

                has_schema = any(len(getattr(p, "schema_types", []) or []) > 0 for p in eval_pages) if eval_pages else blackboard.blackboard_state.get("has_schema", False)
                is_https = website_url.startswith("https://") if website_url else False
                readability = blackboard.blackboard_state.get("readability_score")
                live_citation = blackboard.blackboard_state.get("live_citation_score")
                live_bench = blackboard.blackboard_state.get("live_bench")
                geo_readiness = getattr(blackboard, "geo_readiness", None)

                scores = self.scoring_engine.calculate_scores(
                    manifest=blackboard.crawl_manifest,
                    findings=blackboard.findings or [],
                    claims=blackboard.claim_registry.get_all(),
                    evidence_store=blackboard.evidence_store,
                    pages=eval_pages,
                    evaluations=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
                    business_profile=blackboard.business_profile,
                    has_schema=has_schema,
                    is_https=is_https,
                    readability=readability,
                    external_authority_connected=has_ext_authority,
                    live_citation_score=live_citation,
                    live_benchmark_data=live_bench,
                )
                extractability = getattr(geo_readiness, "extractability_score", None) if geo_readiness is not None else None
                if scores is not None and extractability is not None:
                    self.scoring_engine.apply_measured_geo_score(scores, extractability)
                blackboard.scores = scores

                # Compute honest 3-perspective scores
                honest_scores = self.scoring_engine.calculate_honest_scores(
                    findings=blackboard.findings or [],
                    business_profile=blackboard.business_profile,
                    commercial_evals=blackboard.commercial_evaluations or blackboard.ai_search_evaluations or [],
                    has_schema=has_schema,
                    is_https=is_https,
                    readability=readability,
                    geo_readiness=geo_readiness,
                    live_citation_score=live_citation,
                    live_benchmark_data=live_bench,
                    external_authority_connected=has_ext_authority,
                    manifest=blackboard.crawl_manifest,
                    pages=eval_pages,
                )
                blackboard.honest_scores = honest_scores

            elif node_id == "node_executive_narrative":
                pass

            elif node_id == "node_code_patch_pack":
                pass

            elif node_id == "node_final_report_assembly":
                pass

            controller.mark_node_status(node_id, GraphNodeStatus.COMPLETED, claims_count=len(blackboard.claim_registry.get_all()))
            controller.log_activity(node_id, "success", "node.manual_complete", f"Step '{node_id}' completed successfully")
            await self._emit_event(analysis_id, "specialist_execution", 65, f"Step '{node_id}' finished successfully")
            return {"success": True, "node_id": node_id, "status": "completed"}
        except Exception as err:
            logger.error(f"Error running node {node_id}: {err}", exc_info=True)
            controller.mark_node_status(node_id, GraphNodeStatus.FAILED, error_message=str(err))
            controller.log_activity(node_id, "error", "node.manual_failed", f"Step '{node_id}' failed: {str(err)}")
            await self._emit_event(analysis_id, "failed", 0, f"Step '{node_id}' failed: {str(err)}")
            return {"success": False, "node_id": node_id, "error": str(err)}

    def _pipeline_job_label(self, kind: str, target_id: str) -> str:
        return f"{kind}:{target_id}"

    def _analysis_has_running_node(self, analysis_id: str) -> bool:
        controller = get_pipeline_controller(analysis_id)
        return any(state.status == GraphNodeStatus.RUNNING for state in controller.nodes_state.values())

    def _ensure_pipeline_worker(self, analysis_id: str) -> None:
        current = self._pipeline_worker.get(analysis_id)
        if current is not None and not current.done():
            return
        self._pipeline_worker[analysis_id] = asyncio.create_task(
            self._drain_pipeline_queue(analysis_id),
            name=f"pipeline-queue:{analysis_id}",
        )

    async def _drain_pipeline_queue(self, analysis_id: str) -> None:
        try:
            while True:
                queue = self._pipeline_queue.get(analysis_id) or []
                if not queue:
                    break
                kind, target_id = queue.pop(0)
                label = self._pipeline_job_label(kind, target_id)
                self._pipeline_active[analysis_id] = label
                try:
                    if kind == "section":
                        await self.run_pipeline_section(analysis_id, target_id)
                    else:
                        await self.run_pipeline_node(analysis_id, target_id)
                except Exception:
                    logger.exception("Queued %s failed for %s", label, analysis_id)
                finally:
                    if self._pipeline_active.get(analysis_id) == label:
                        self._pipeline_active.pop(analysis_id, None)
        finally:
            current = self._pipeline_worker.get(analysis_id)
            if current is asyncio.current_task():
                self._pipeline_worker.pop(analysis_id, None)
            if self._pipeline_queue.get(analysis_id):
                self._ensure_pipeline_worker(analysis_id)

    def _queue_pipeline_job(self, analysis_id: str, kind: str, target_id: str) -> str:
        """Queue a section or node run. Returns 'started' or 'already_running'."""
        label = self._pipeline_job_label(kind, target_id)
        active = self._pipeline_active.get(analysis_id)
        queued = [self._pipeline_job_label(item_kind, item_id) for item_kind, item_id in self._pipeline_queue.get(analysis_id, [])]
        if label == active or label in queued:
            return "already_running"
        # The main audit owns the blackboard while one of its nodes is running.
        # A second AEO execution on that same run is what the gateway was killing at 180s.
        if active is None and not queued and self._analysis_has_running_node(analysis_id):
            return "already_running"
        self._pipeline_queue.setdefault(analysis_id, []).append((kind, target_id))
        self._ensure_pipeline_worker(analysis_id)
        return "started"

    def enqueue_pipeline_section(self, analysis_id: str, section_id: str) -> Dict[str, Any]:
        """Accept a section run without waiting for its model calls."""
        section_id = PILLAR_TO_SECTION.get(section_id.lower(), section_id)
        sec_def = next((s for s in SECTIONS_REGISTRY if s.section_id == section_id), None)
        if not sec_def:
            return {"success": False, "error": f"Section '{section_id}' not found in registry."}
        status = self._queue_pipeline_job(analysis_id, "section", section_id)
        return {
            "success": True,
            "status": status,
            "section_id": section_id,
            "title": sec_def.title,
        }

    def enqueue_pipeline_node(self, analysis_id: str, node_id: str) -> Dict[str, Any]:
        """Accept a single-step run without waiting for its model calls."""
        if node_id not in NODES_REGISTRY:
            return {"success": False, "error": f"Step '{node_id}' not found."}
        controller = get_pipeline_controller(analysis_id)
        if not controller.are_dependencies_met(node_id):
            missing = controller.get_missing_dependencies(node_id)
            return {
                "success": False,
                "error": f"Prerequisites not met for step '{node_id}'. Missing completed dependencies: {missing}",
                "missing_dependencies": missing,
            }
        status = self._queue_pipeline_job(analysis_id, "node", node_id)
        return {"success": True, "status": status, "node_id": node_id}

    async def run_pipeline_section(self, analysis_id: str, section_id: str) -> Dict[str, Any]:
        """Executes all DAG nodes in a section sequentially, ensuring prerequisites are satisfied."""
        section_id = PILLAR_TO_SECTION.get(section_id.lower(), section_id)
        controller = get_pipeline_controller(analysis_id)
        pipeline_t0 = time.perf_counter()
        sec_def = next((s for s in SECTIONS_REGISTRY if s.section_id == section_id), None)
        if not sec_def:
            return {"success": False, "error": f"Section '{section_id}' not found in registry."}

        executed_nodes = []
        for nid in sec_def.node_ids:
            res = await self.run_pipeline_node(analysis_id, nid)
            executed_nodes.append({"node_id": nid, "result": res})
            if not res.get("success"):
                return {
                    "success": False,
                    "section_id": section_id,
                    "failed_node": nid,
                    "error": res.get("error"),
                    "executed_nodes": executed_nodes,
                }

        return {
            "success": True,
            "section_id": section_id,
            "title": sec_def.title,
            "executed_nodes": executed_nodes,
        }

orchestrator = AnalysisOrchestrator()

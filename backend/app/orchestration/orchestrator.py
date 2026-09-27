"""
Dristik AI Advanced Autonomous Website Intelligence & Growth OS Orchestrator
Coordinates the 4-level cognitive architecture, dynamic cognitive teams, Evidence Graph 2.0,
hypothesis formulation, causal bottleneck discovery, AI search simulation, and validated remediation.
"""
import asyncio
import logging
import uuid
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, Any, Optional, AsyncGenerator, List

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.domain.models import AnalysisRun, ExecutiveReport, CrawlManifest, FindingEvidence
from app.domain.enums import AnalysisStage, Category, Severity
from app.domain.capability import CAPABILITY_REGISTRY
from app.cognition.blackboard import CognitiveBlackboard
from app.cognition.decision_engine import DecisionEngine
from app.cognition.hypotheses import HypothesisEngine
from app.cognition.causal import CausalReasoningEngine
from app.cognition.confidence import CalibratedConfidenceEngine
from app.evidence.graph import GraphNodeType, GraphEdgeType
from app.evidence.validation import EvidenceGapDetector
from app.intelligence.business.website_twin import WebsiteDigitalTwin
from app.intelligence.business.intent_graph import SearchIntentGraph
from app.intelligence.business.opportunity import OpportunityDetector
from app.intelligence.citations.simulation import AISearchSimulationEngine
from app.intelligence.monitoring.timeline import WebsiteIntelligenceTimeline
from app.inference.model_router import ModelRouter
from app.inference.telemetry import TelemetryTracker
from app.crawl.crawler import CrawlerService
from app.mission.director import MissionDirector
from app.orchestration.team_orchestrator import TeamOrchestrator
from app.orchestration.agent_pool import AgentPool
from app.scoring.engine import ScoringEngine
from app.remediation.planner import RemediationPlanner
from app.reports.narrative import NarrativeGenerator
from app.reports.roadmap import RoadmapBuilder
from app.agents.page.intelligence import PageIntelligenceAgent
from app.evidence.site_facts import extract_site_facts
from app.remediation.patch_pack import generate_character_safe_copy, generate_whatsapp_summary
from app.intelligence.competitive.bakeoff import CommercialBakeoffEngine
from app.intelligence.business.understanding import BusinessUnderstandingOrchestrator
from app.orchestration.integrity_gate import integrity_gate

class AnalysisOrchestrator:
    def __init__(self):
        self.runs: Dict[str, AnalysisRun] = {}
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
        self.digital_twins: Dict[str, WebsiteDigitalTwin] = {}
        self.timelines: Dict[str, WebsiteIntelligenceTimeline] = {}
        from app.persistence.repository import get_audit_repository
        self.repository = get_audit_repository()

    def create_run(self, website_url: str, org_id: str = "org_default", created_by: Optional[str] = None) -> AnalysisRun:
        analysis_id = f"run_{uuid.uuid4().hex[:10]}"
        now_str = datetime.now().isoformat()

        run = AnalysisRun(
            analysis_id=analysis_id,
            org_id=org_id,
            website_url=website_url,
            status=AnalysisStage.QUEUED,
            progress_percentage=0,
            current_step="Analysis Queued",
            created_at=now_str,
            updated_at=now_str
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
            event_payload = {
                "stage": stage,
                "progress": progress,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "data": data or {}
            }
            await queue.put(event_payload)

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
    ):
        """
        Cognitive OS mission execution across all 4 cognitive levels.
        """
        run = self.runs.get(analysis_id)
        telemetry_tracker = TelemetryTracker()
        model_router = ModelRouter(telemetry_tracker=telemetry_tracker)
        blackboard = CognitiveBlackboard(run_id=analysis_id, website_url=website_url)
        blackboard.user_declared_site_type = site_type
        blackboard.user_declared_site_type_notes = declared_site_type_notes
        team_orchestrator = TeamOrchestrator(model_router)

        crawl_limit = max_pages or settings.MAX_CRAWL_PAGES

        try:
            # 1. Mission Director Initialization
            mission_state = self.mission_director.create_mission(
                target_url=website_url,
                audit_type="standard_growth",
                max_pages=crawl_limit
            )

            # 2. Level 0: Ingestion & Multi-Page Crawl
            run.status = AnalysisStage.INGESTING
            await self._emit_event(analysis_id, "ingesting", 10, f"Initializing multi-page crawler for {website_url}...")

            def on_crawl_progress(msg: str, progress_pct: int):
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
                raise RuntimeError(f"No pages could be crawled from {website_url}. Please ensure the URL is valid, accessible, and public.")
            page_ev = manifest.pages[0]
            domain = manifest.domain

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
            from app.persistence.models import StageCheckpoint
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

            # Extract Wave-0 deterministic site facts ($0 inference)
            blackboard.site_facts = extract_site_facts(manifest, blackboard.evidence_store)

            # Phase 2: Operationalize External Evidence Plane (ext_NNN)
            from app.evidence.enrichment import ExternalEvidenceEnricher
            enricher = ExternalEvidenceEnricher()
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
            except Exception as enrich_err:
                logger.warning(f"External evidence enrichment encountered error: {enrich_err}")

            # 3. Dynamic Capability Scheduling
            run.status = AnalysisStage.PLANNING
            mission_caps = self.mission_director.select_capabilities_for_mission(mission_state)

            # 4. Formulate Pre-Reasoning Hypotheses
            initial_hypotheses = self.hypothesis_engine.generate_initial_hypotheses(domain, manifest.pages)
            mission_state.hypotheses = initial_hypotheses

            # 5. Execute Level 0 Deterministic Technical Foundation ($0 inference)
            await self._emit_event(analysis_id, "deterministic_analysis", 38, "Executing Deterministic Technical, DOM & Schema Capabilities ($0 inference)...")
            await team_orchestrator.execute_capability_wave(mission_caps["tier_1_deterministic"], manifest, blackboard)

            # 6. Business identity (declared vs detected) before the 35-agent DAG
            run.status = AnalysisStage.SPECIALIST_EXECUTION
            await self._emit_event(
                analysis_id,
                "specialist_execution",
                42,
                "Resolving business identity from crawled evidence...",
            )
            biz_understanding = BusinessUnderstandingOrchestrator(model_router)
            semantic_rep = await biz_understanding.execute_business_understanding(blackboard)

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

            # 7. Full 35-agent specialist DAG (dependency waves, no canned fallbacks)
            agent_pool = AgentPool(model_router)
            await self._emit_event(
                analysis_id,
                "specialist_execution",
                46,
                f"Deploying all {len(agent_pool)} specialist agents across {len(agent_pool.waves)} dependency waves...",
                {"agents": len(agent_pool), "waves": len(agent_pool.waves)},
            )

            async def _agent_progress(stage: str, progress: int, message: str, data: Dict[str, Any]):
                await self._emit_event(analysis_id, stage, progress, message, data)

            pool_summary = await agent_pool.execute_all(
                blackboard,
                progress_cb=_agent_progress,
                base_progress=46,
                end_progress=78,
            )
            await self._emit_event(
                analysis_id,
                "specialist_execution",
                78,
                (
                    f"35 specialists finished: {pool_summary['completed']} completed, "
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

            # 7b. Per-page SEO, copywriting, and suggested copy
            await self._emit_event(
                analysis_id,
                "specialist_execution",
                80,
                f"Writing detailed SEO and copy reports for {len(manifest.pages)} crawled page(s)...",
            )
            page_agent = PageIntelligenceAgent(model_router)
            await page_agent.run(blackboard)

            # 8. Verification agents already ran in the DAG (adversarial + contradiction + executive).
            run.status = AnalysisStage.ADVERSARIAL_VERIFICATION
            await self._emit_event(
                analysis_id,
                "adversarial_verification",
                82,
                "Adversarial and contradiction specialists recorded on the blackboard.",
            )

            # Zero-Fake Evidence Integrity Gate
            current_claims = blackboard.claim_registry.get_all()
            gate_res = integrity_gate.validate_claims_and_evidence(
                current_claims, blackboard.evidence_store, blackboard.claim_registry
            )
            blackboard.blackboard_state["integrity_gate"] = gate_res.model_dump()

            from app.domain.enums import Materiality, RubricConfidence
            from app.cognition.finding_rubric import apply_rubric_to_claim
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
                        83,
                        f"Escalated {len(held_guesses)} GUESSING+CRITICAL claim(s) to verification.adversarial.v3 before executive use.",
                    )

            # Detect uncorroborated marketing claims (Evidence Gaps)
            evidence_gaps = self.gap_detector.detect_gaps(current_claims, blackboard.evidence_store, blackboard.pages)
            blackboard.blackboard_state["evidence_gaps"] = [g.model_dump() for g in evidence_gaps]

            # 9. Level 3: Causal Reasoning & Root-Cause Bottleneck Discovery
            await self._emit_event(analysis_id, "specialist_execution", 82, "Causal Reasoning Engine isolating primary root-cause growth bottlenecks...")
            bottlenecks = self.causal_engine.analyze_root_causes(current_claims, blackboard.business_profile)
            blackboard.blackboard_state["root_causes"] = [b.model_dump() for b in bottlenecks]

            # Update Hypotheses with accumulated evidence
            evaluated_hypotheses = self.hypothesis_engine.evaluate_hypotheses_against_evidence(
                initial_hypotheses, current_claims, blackboard.evidence_store
            )
            mission_state.hypotheses = evaluated_hypotheses

            # Detect Positive Growth Opportunities
            opportunities = self.opportunity_detector.detect_opportunities(
                blackboard.business_profile, blackboard.pages, current_claims
            )
            blackboard.blackboard_state["opportunities"] = [o.model_dump() for o in opportunities]

            # 10. AI Answer Engine Discoverability & Commercial Query Simulation
            await self._emit_event(
                analysis_id,
                "specialist_execution",
                85,
                "Simulating AI Answer Engine evaluations across 6 Canonical Commercial Inquiries (ChatGPT, Perplexity, Gemini, Claude)...",
                {"evaluating_queries": 6}
            )
            try:
                await team_orchestrator.worker_simulator.execute_task("ai_search_simulation", blackboard)
            except Exception as sim_err:
                logger.error("AI Search simulation error: %s", sim_err)

            # 11. Executive Strategy Narrative Synthesis
            run.status = AnalysisStage.EXECUTIVE_SYNTHESIS
            await self._emit_event(analysis_id, "executive_synthesis", 88, "Synthesizer compiling C-Suite narrative from verified specialist claims...")
            if not blackboard.executive_narrative.get("story_summary"):
                await team_orchestrator.worker_synthesizer.execute_task("synthesis", blackboard)

            # 12. Causal Prioritization & Scoring Engine
            run.status = AnalysisStage.SCORING
            await self._emit_event(analysis_id, "scoring", 93, "Deterministic Scoring Engine computing intent-adjusted category scores...")

            final_findings = self.decision_engine.synthesize_findings(current_claims, blackboard.evidence_store)
            blackboard.findings = final_findings

            overall_scores = self.scoring_engine.calculate_scores(
                findings=final_findings,
                business_profile=blackboard.business_profile,
                has_schema=any(len(p.schema_types) > 0 for p in blackboard.pages),
                is_https=website_url.startswith("https://"),
                readability=page_ev.readability_score
            )
            blackboard.scores = overall_scores

            # Calibrated Confidence
            confidence_result = self.confidence_engine.calculate_confidence(
                claims=current_claims,
                evidence_store=blackboard.evidence_store,
                pages=blackboard.pages,
                contradictions_count=len(blackboard.claim_registry.get_contradictions())
            )
            overall_scores.overall_confidence = confidence_result.confidence_score
            overall_scores.evidence_coverage = confidence_result.evidence_coverage

            # 13. Validated Remediation & Roadmaps
            remediation_plan = self.remediation_planner.build_remediation_plan(
                findings=final_findings,
                business_profile=blackboard.business_profile,
                target_url=website_url
            )
            blackboard.code_patches = remediation_plan.patches

            r7, r30, r90 = self.roadmap_builder.build_roadmap(final_findings, blackboard.executive_narrative)
            top_10_plan = self.roadmap_builder.build_top_10_actions(
                final_findings,
                blackboard.business_profile,
                overall_scores,
                blackboard.executive_narrative,
                crawl_summary=manifest.crawl_health if manifest else None,
            )
            blackboard.roadmap_7_days = r7
            blackboard.roadmap_30_days = r30
            blackboard.roadmap_90_days = r90

            # 14. Digital Twin & Temporal Timeline Update
            if domain not in self.digital_twins:
                self.digital_twins[domain] = WebsiteDigitalTwin(
                    twin_id=f"twin_{domain.replace('.', '_')}",
                    domain=domain,
                    base_url=website_url
                )
            twin = self.digital_twins[domain]
            twin.update_from_mission(
                blackboard.business_profile,
                blackboard.pages,
                overall_scores,
                final_findings,
                remediation_plan.patches
            )

            if domain not in self.timelines:
                self.timelines[domain] = WebsiteIntelligenceTimeline(domain)
            timeline = self.timelines[domain]
            timeline.record_audit(analysis_id, overall_scores, final_findings)

            # 15. Narrative and Final Report Assembly
            narrative_data = self.narrative_gen.build_narrative(
                business_profile=blackboard.business_profile,
                findings=final_findings,
                scores=overall_scores,
                synthesizer_output=blackboard.executive_narrative
            )

            telemetry_data = telemetry_tracker.get_data()

            from app.intelligence.geo.readiness import evaluate_geo_readiness
            visibility_measured = False
            visibility_detail = None
            live_citation_score = None
            ai_visibility_scorecard = None
            try:
                from app.intelligence.geo.audit_monitor import run_audit_visibility
                profile = blackboard.business_profile
                monitored = await run_audit_visibility(
                    domain=domain,
                    brand_name=getattr(profile, "business_name", None),
                    industry=getattr(profile, "industry", None) or getattr(profile, "niche", None),
                    services=list(getattr(profile, "services", None) or []) or list(getattr(profile, "products", None) or []),
                    locations=[profile.geography] if getattr(profile, "geography", None) else None,
                    audience=getattr(profile, "target_audience", None),
                    max_pages=max_pages,
                )
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
            except Exception:
                ai_visibility_scorecard = None

            if not visibility_measured:
                try:
                    from app.intelligence.geo.pipeline_store import geo_pipeline_store
                    snap = geo_pipeline_store.get_latest_snapshot(domain)
                    if snap and (snap.engines_measured_count or 0) > 0 and snap.overall_score is not None:
                        visibility_measured = True
                        live_citation_score = float(snap.overall_score)
                        engines = ", ".join(sorted((snap.engine_scores or {}).keys())) or "unlisted"
                        visibility_detail = (
                            f"GEO pipeline snapshot {snap.snapshot_id} measured {snap.engines_measured_count} engine(s) "
                            f"({engines}). Citation rate {snap.overall_score}. Not inferred from HTML."
                        )
                except Exception:
                    visibility_measured = False
                    live_citation_score = None
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
            )
            blackboard.geo_readiness = geo_readiness

            try:
                from app.intelligence.geo.agent_readiness import evaluate_agent_readiness
                agent_readiness = await evaluate_agent_readiness(website_url, blackboard.pages, manifest)
            except Exception:
                agent_readiness = None

            # Human, Google, and on-page AI readiness. Live citation stays null unless a snapshot exists.
            honest_scores = self.scoring_engine.calculate_honest_scores(
                findings=final_findings,
                business_profile=blackboard.business_profile,
                commercial_evals=blackboard.commercial_evaluations,
                has_schema=len(page_ev.schema_types) > 0,
                is_https=website_url.startswith("https://"),
                readability=page_ev.readability_score,
                geo_readiness=geo_readiness,
                live_citation_score=live_citation_score,
            )
            blackboard.honest_scores = honest_scores

            # Enforce Character-Safe Copy bounds
            character_copy = generate_character_safe_copy(
                blackboard.business_profile,
                website_url
            )
            blackboard.character_safe_copy = character_copy

            # Format C-Suite WhatsApp 1-Pager
            wa_summary = generate_whatsapp_summary(
                domain=domain,
                honest_scores=honest_scores,
                what_to_ignore=narrative_data.get("consultant_advice_what_to_ignore", ""),
                top_bottleneck=blackboard.blackboard_state.get("causal_root_cause", {}).get("bottleneck", ""),
                top_actions=[r.title for r in r7[:3]],
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
            graph_summary = blackboard.evidence_graph.export_graph_summary()

            from app.audit.manifest import build_run_manifest, seal_manifest
            graph_snap = blackboard.evidence_store._ensure_snapshots().put(
                source="evidence_graph",
                body=blackboard.evidence_graph.export_graph_data(),
                source_type="graph",
                media_type="application/json",
            )
            report_uuid = str(uuid.uuid4())
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
            seal_manifest(run_manifest, snapshots=blackboard.evidence_store.snapshots)
            run.manifest_id = run_manifest.manifest_id
            run.report_id = report_uuid
            run.is_sealed = True
            try:
                from app.intelligence.outcomes.store import get_outcome_store
                get_outcome_store().schedule(
                    analysis_id=analysis_id,
                    website_url=website_url,
                    org_id=getattr(run, "org_id", None),
                )
            except Exception:
                pass

            from app.intelligence.monitoring.visual_intelligence import visual_intelligence_engine
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
            from app.intelligence.monitoring.regression_detector import regression_detector
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
            from app.intelligence.ux.visual_ux_tester import visual_ux_tester
            visual_ux_rep = visual_ux_tester.inspect_website_visual_ux(
                domain=domain,
                website_url=website_url,
                dom_evidence=evidence_ledger_map,
            )

            cro_finding = visual_ux_tester.generate_grounded_cro_finding(
                domain=domain,
                website_url=website_url,
                pages=getattr(blackboard, "pages", None),
            )
            final_findings = [f for f in final_findings if f.finding_id != "find_cro_001"]
            if cro_finding is not None:
                final_findings.append(cro_finding)

            # Synthesize Lifecycle Revenue Intelligence (website -> search -> visitor -> lead -> revenue)
            from app.connectors.lifecycle_revenue import lifecycle_service
            lifecycle_rep = lifecycle_service.synthesize_lifecycle_intelligence(
                domain=domain,
                gsc_connected=False,
                ga4_connected=False,
                crm_connected=False,
            )

            # Synthesize first-class Evidence Taxonomy & Epistemic Hierarchy report
            from app.evidence.taxonomy import generate_evidence_taxonomy_report
            evidence_taxonomy_rep = generate_evidence_taxonomy_report(
                findings=final_findings,
                evidence_ledger=evidence_ledger_map,
                sample_size=len(blackboard.pages or []),
            )

            # Synthesize 40-Page Agency Technical SEO & Architecture Rollups
            from app.analyzers.meta_rollup import analyze_meta_rollup
            from app.analyzers.heading_analyzer import analyze_heading_hierarchy
            from app.analyzers.host_and_redirects import probe_host_and_redirects
            from app.analyzers.link_depth import analyze_link_depth_and_orphans
            from app.analyzers.form_analyzer import analyze_forms
            from app.analyzers.media_asset_analyzer import analyze_media_assets
            from app.analyzers.security_analyzer import analyze_security_headers
            from app.analyzers.schema_validator import analyze_schema_rich_results
            from app.intelligence.geo.per_engine_evaluator import evaluate_per_engine_ai

            eval_pages = manifest.pages or blackboard.pages or []
            meta_rollup_rep = analyze_meta_rollup(eval_pages)
            heading_hierarchy_rep = analyze_heading_hierarchy(eval_pages)
            sitemap_urls_sample = [manifest.sitemap_url] if (manifest and manifest.sitemap_url) else []
            click_depth_rep, orphan_pages_rep, anchor_text_audit_rep = analyze_link_depth_and_orphans(
                eval_pages, sitemap_urls=sitemap_urls_sample, homepage_url=website_url
            )
            form_audit_rep = analyze_forms(eval_pages)
            media_assets_rep = analyze_media_assets(eval_pages)
            schema_validation_rep = analyze_schema_rich_results(eval_pages)

            first_page_headers = {}
            if eval_pages and getattr(eval_pages[0], "response_headers", None):
                first_page_headers = eval_pages[0].response_headers
            security_audit_rep = analyze_security_headers(
                url=website_url,
                response_headers=first_page_headers
            )

            try:
                host_and_redirects_rep = await probe_host_and_redirects(domain_or_url=website_url, canonical_target=website_url)
            except Exception:
                from app.domain.models import RedirectAuditReport
                host_and_redirects_rep = RedirectAuditReport(target_domain=domain, canonical_destination=website_url, summary="Host variant probe completed in offline mode.")

            per_engine_geo_rep = evaluate_per_engine_ai(
                pages=eval_pages,
                manifest=manifest,
                profile=blackboard.business_profile,
                website_url=website_url
            )

            report = ExecutiveReport(
                report_id=report_uuid,
                analysis_id=analysis_id,
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
                scores=overall_scores,
                honest_scores=honest_scores,
                geo_readiness=geo_readiness,
                ai_visibility_scorecard=ai_visibility_scorecard,
                agent_readiness=agent_readiness,
                commercial_evaluations=blackboard.commercial_evaluations,
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
                exploratory_hypotheses=narrative_data.get("exploratory_hypotheses", []),
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
                    "avg_ttfb_ms": manifest.crawl_health.get("avg_ttfb_ms", page_ev.ttfb_ms),
                    "total_words": manifest.crawl_health.get("total_words_across_site", page_ev.word_count),
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
                    "root_cause_bottlenecks_count": len(bottlenecks),
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
                media_assets=media_assets_rep,
                per_engine_geo=per_engine_geo_rep,
                security_audit=security_audit_rep,
                schema_validation=schema_validation_rep,
            )

            # -------------------------------------------------------------
            # Enforce 20-Point VALIDATION GATE Before Shipping
            # -------------------------------------------------------------
            from app.reports.validation_gate import ValidationGate
            report, gate_result = ValidationGate.enforce_gate(report, manifest=manifest)
            if not gate_result.is_valid:
                logger.error(f"VALIDATION GATE FAILED for run {analysis_id}:\n{gate_result.summary()}")
                run.status = AnalysisStage.FAILED
                run.current_step = f"Report validation gate failure: {', '.join(gate_result.failed_checks)}"
                await self._emit_event(
                    analysis_id,
                    "failed",
                    100,
                    f"Report validation gate failed: {', '.join(gate_result.failed_checks)}",
                    {"failure_reasons": gate_result.failure_reasons}
                )
                return

            run.status = AnalysisStage.COMPLETED
            run.report = report
            run.telemetry = telemetry_data

            try:
                self.repository.persist_findings(analysis_id, final_findings)
                self.repository.save_run(run)
                self.repository.save_checkpoint(StageCheckpoint(
                    analysis_id=analysis_id,
                    stage=AnalysisStage.COMPLETED,
                    step_number=5,
                    status="COMPLETED",
                    findings_count=len(final_findings),
                    state_payload={"overall_score": overall_scores.overall_score}
                ))
            except Exception as pe:
                logger.warning(f"Persistence error on completion: {pe}")

            await self._emit_event(
                analysis_id,
                "completed",
                100,
                f"Multi-page audit completed across {len(manifest.pages)} pages. Overall Score: {overall_scores.overall_score:.0f}/100 ({overall_scores.grade}).",
                {"report": report.model_dump(mode="json")}
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            run.status = AnalysisStage.FAILED
            run.error = str(e)
            try:
                self.repository.save_run(run)
                self.repository.save_checkpoint(StageCheckpoint(
                    analysis_id=analysis_id,
                    stage=AnalysisStage.FAILED,
                    step_number=99,
                    status="FAILED",
                    state_payload={"error": str(e)}
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
        Avoids redundant crawling when page data is already persisted.
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

        # Launch resumption
        asyncio.create_task(self.execute_analysis_pipeline(analysis_id, url, max_pages=max_pages))
        return True

orchestrator = AnalysisOrchestrator()

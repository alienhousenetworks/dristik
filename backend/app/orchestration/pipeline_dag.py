"""
Dristik Modular DAG Execution Engine & Activity Streamer
Defines formal Sections and Sub-sections (Nodes), resolves dependency prerequisites,
supports independent node execution, cooperative pause/stop, durable step-level resumption,
and structured real-time semantic activity logging.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from app.cognition.blackboard import CognitiveBlackboard

logger = logging.getLogger("dristik.pipeline_dag")


class GraphNodeStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    SKIPPED = "skipped"


class ActivityEvent:
    def __init__(
        self,
        section_id: str,
        section_title: str,
        node_id: str,
        node_title: str,
        agent_name: str,
        status: str,
        action: str,
        summary: str,
        details: Optional[Dict[str, Any]] = None,
        cost_delta_usd: float = 0.0,
        evidence_count: int = 0,
    ):
        self.id = f"act_{uuid.uuid4().hex[:8]}"
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.section_id = section_id
        self.section_title = section_title
        self.node_id = node_id
        self.node_title = node_title
        self.agent_name = agent_name
        self.status = status  # running | success | warning | error | info
        self.action = action
        self.summary = summary
        self.details = details or {}
        self.cost_delta_usd = cost_delta_usd
        self.evidence_count = evidence_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "node_id": self.node_id,
            "node_title": self.node_title,
            "agent_name": self.agent_name,
            "status": self.status,
            "action": self.action,
            "summary": self.summary,
            "details": self.details,
            "cost_delta_usd": self.cost_delta_usd,
            "evidence_count": self.evidence_count,
        }


class DAGNode:
    def __init__(
        self,
        node_id: str,
        section_id: str,
        section_title: str,
        title: str,
        description: str,
        agent_name: str,
        dependencies: Optional[List[str]] = None,
    ):
        self.node_id = node_id
        self.section_id = section_id
        self.section_title = section_title
        self.title = title
        self.description = description
        self.agent_name = agent_name
        self.dependencies = dependencies or []


class GraphSectionDef:
    def __init__(self, section_id: str, title: str, description: str, order: int, node_ids: List[str]):
        self.section_id = section_id
        self.title = title
        self.description = description
        self.order = order
        self.node_ids = node_ids

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "description": self.description,
            "order": self.order,
            "node_ids": self.node_ids,
        }


# Canonical registry of all 7 sections and ~18 sub-sections
SECTIONS_REGISTRY: List[GraphSectionDef] = [
    GraphSectionDef(
        section_id="sec_ingestion",
        title="1. Ingestion & Multi-Page Crawl",
        description="Crawls the target domain, extracts clean HTML, and populates raw DOM evidence.",
        order=1,
        node_ids=["node_crawl", "node_dom_extraction"],
    ),
    GraphSectionDef(
        section_id="sec_deterministic",
        title="2. Deterministic Evidence & External Plane",
        description="Extracts Schema AST, verifies DNS/SSL, TLS, security headers, and CruX performance metrics.",
        order=2,
        node_ids=["node_dns_ssl_headers", "node_schema_ld_json"],
    ),
    GraphSectionDef(
        section_id="sec_business_identity",
        title="3. Business Understanding & Entity Grounding",
        description="Resolves canonical entity, industry classification, ICP, and value proposition.",
        order=3,
        node_ids=["node_entity_resolution", "node_icp_offer_profile"],
    ),
    GraphSectionDef(
        section_id="sec_specialist_waves",
        title="4. Specialist Workforce Waves",
        description="Executes topological specialist workforce across technical, content, CRO, and citability domains.",
        order=4,
        node_ids=[
            "node_specialist_wave_1",
            "node_specialist_wave_2",
            "node_specialist_wave_3",
            "node_specialist_wave_4",
            "node_page_intelligence",
        ],
    ),
    GraphSectionDef(
        section_id="sec_verification",
        title="5. Adversarial Verification & Integrity Gate",
        description="Applies multi-agent adversarial cross-examination and Zero-Fake Evidence integrity gate.",
        order=5,
        node_ids=["node_adversarial_critic", "node_integrity_gate"],
    ),
    GraphSectionDef(
        section_id="sec_causal_sim",
        title="6. Causal Bottlenecks & AI Search Simulation",
        description="Isolates primary root-cause bottlenecks and tests commercial buyer queries across AI answer engines.",
        order=6,
        node_ids=["node_causal_bottlenecks", "node_ai_search_simulation"],
    ),
    GraphSectionDef(
        section_id="sec_synthesis",
        title="7. Executive Synthesis, Scoring & Patches",
        description="Computes honest 3-pillar scores, synthesizes C-suite narrative, and builds production code patch pack.",
        order=7,
        node_ids=[
            "node_honest_scoring",
            "node_executive_narrative",
            "node_code_patch_pack",
            "node_final_report_assembly",
        ],
    ),
]

NODES_REGISTRY: Dict[str, DAGNode] = {
    "node_crawl": DAGNode(
        node_id="node_crawl",
        section_id="sec_ingestion",
        section_title="1. Ingestion & Multi-Page Crawl",
        title="Multi-Page HTTP Crawler",
        description="Fetches target domain pages, checks status codes, TTFB, and response headers.",
        agent_name="CrawlerService",
        dependencies=[],
    ),
    "node_dom_extraction": DAGNode(
        node_id="node_dom_extraction",
        section_id="sec_ingestion",
        section_title="1. Ingestion & Multi-Page Crawl",
        title="DOM AST & Element Ingestion",
        description="Parses HTML structure, headings (H1/H2), word counts, CTAs, and internal/external link graphs.",
        agent_name="DomExtractor",
        dependencies=["node_crawl"],
    ),
    "node_dns_ssl_headers": DAGNode(
        node_id="node_dns_ssl_headers",
        section_id="sec_deterministic",
        section_title="2. Deterministic Evidence & External Plane",
        title="DNS, SSL/TLS & Security Headers",
        description="Inspects A/AAAA DNS records, SSL certificate issuer, HSTS, CSP, and transport security.",
        agent_name="ExternalEvidenceEnricher",
        dependencies=["node_dom_extraction"],
    ),
    "node_schema_ld_json": DAGNode(
        node_id="node_schema_ld_json",
        section_id="sec_deterministic",
        section_title="2. Deterministic Evidence & External Plane",
        title="Schema.org JSON-LD Parser",
        description="Extracts JSON-LD script blocks, parses Schema AST, and validates entity types.",
        agent_name="SchemaAstValidator",
        dependencies=["node_dom_extraction"],
    ),
    "node_entity_resolution": DAGNode(
        node_id="node_entity_resolution",
        section_id="sec_business_identity",
        section_title="3. Business Understanding & Entity Grounding",
        title="Brand & Canonical Entity Resolver",
        description="Resolves legal and commercial brand identity, official domain, and industry category.",
        agent_name="UniversalEntityResolver",
        dependencies=["node_dom_extraction"],
    ),
    "node_icp_offer_profile": DAGNode(
        node_id="node_icp_offer_profile",
        section_id="sec_business_identity",
        section_title="3. Business Understanding & Entity Grounding",
        title="ICP & Value Proposition Profiler",
        description="Identifies target audience, core buyer pain points, and commercial value propositions.",
        agent_name="BusinessUnderstandingOrchestrator",
        dependencies=["node_entity_resolution"],
    ),
    "node_specialist_wave_1": DAGNode(
        node_id="node_specialist_wave_1",
        section_id="sec_specialist_waves",
        section_title="4. Specialist Workforce Waves",
        title="Technical SEO & Crawlability (Wave 1)",
        description="Audits robots.txt, sitemaps, canonicals, status codes, and indexation hygiene.",
        agent_name="TechnicalSeoSpecialists",
        dependencies=["node_schema_ld_json", "node_icp_offer_profile"],
    ),
    "node_specialist_wave_2": DAGNode(
        node_id="node_specialist_wave_2",
        section_id="sec_specialist_waves",
        section_title="4. Specialist Workforce Waves",
        title="Schema AST & On-Page Content (Wave 2)",
        description="Audits structured data depth, heading hierarchy, meta tags, and content depth.",
        agent_name="OnPageSchemaSpecialists",
        dependencies=["node_specialist_wave_1"],
    ),
    "node_specialist_wave_3": DAGNode(
        node_id="node_specialist_wave_3",
        section_id="sec_specialist_waves",
        section_title="4. Specialist Workforce Waves",
        title="CRO, UX Conversion & Trust Proof (Wave 3)",
        description="Evaluates primary CTA visibility, trust badges, pricing transparency, and form accessibility.",
        agent_name="CroExperienceSpecialists",
        dependencies=["node_specialist_wave_2"],
    ),
    "node_specialist_wave_4": DAGNode(
        node_id="node_specialist_wave_4",
        section_id="sec_specialist_waves",
        section_title="4. Specialist Workforce Waves",
        title="GEO & Answer Engine Citability (Wave 4)",
        description="Evaluates LLM citability, entity clarity, and conversational search readiness.",
        agent_name="GeoAeoSpecialists",
        dependencies=["node_specialist_wave_3"],
    ),
    "node_page_intelligence": DAGNode(
        node_id="node_page_intelligence",
        section_id="sec_specialist_waves",
        section_title="4. Specialist Workforce Waves",
        title="Page-by-Page SEO & Copywriting Rewrites",
        description="Generates per-URL action reports, title tag upgrades, and character-safe hero copy rewrites.",
        agent_name="PageIntelligenceAgent",
        dependencies=["node_specialist_wave_4"],
    ),
    "node_adversarial_critic": DAGNode(
        node_id="node_adversarial_critic",
        section_id="sec_verification",
        section_title="5. Adversarial Verification & Integrity Gate",
        title="Adversarial Critic & Contradiction Detection",
        description="Cross-examines specialist claims against ground truth DOM evidence and flags unbacked assertions.",
        agent_name="CriticAgent",
        dependencies=["node_specialist_wave_4"],
    ),
    "node_integrity_gate": DAGNode(
        node_id="node_integrity_gate",
        section_id="sec_verification",
        section_title="5. Adversarial Verification & Integrity Gate",
        title="Zero-Fake Evidence Integrity Gate",
        description="Verifies that all claims link to measured cryptographic evidence hashes and enforces strict provenance.",
        agent_name="IntegrityGate",
        dependencies=["node_adversarial_critic"],
    ),
    "node_causal_bottlenecks": DAGNode(
        node_id="node_causal_bottlenecks",
        section_id="sec_causal_sim",
        section_title="6. Causal Bottlenecks & AI Search Simulation",
        title="Causal Graph & Bottleneck Isolation",
        description="Identifies the single highest-leverage growth blocker holding back organic traffic and conversions.",
        agent_name="CausalReasoningEngine",
        dependencies=["node_integrity_gate"],
    ),
    "node_ai_search_simulation": DAGNode(
        node_id="node_ai_search_simulation",
        section_id="sec_causal_sim",
        section_title="6. Causal Bottlenecks & AI Search Simulation",
        title="Synthetic Commercial Query Simulation",
        description="Simulates realistic commercial buyer inquiries across ChatGPT, Perplexity, Claude, and Gemini.",
        agent_name="AISearchSimulationEngine",
        dependencies=["node_icp_offer_profile", "node_integrity_gate"],
    ),
    "node_honest_scoring": DAGNode(
        node_id="node_honest_scoring",
        section_id="sec_synthesis",
        section_title="7. Executive Synthesis, Scoring & Patches",
        title="Honest 3-Pillar Scoring Engine",
        description="Computes 0-100 scores for Human Ease of Use, Google Search Code, and AI Citability Readiness.",
        agent_name="ScoringEngine",
        dependencies=["node_causal_bottlenecks", "node_ai_search_simulation"],
    ),
    "node_executive_narrative": DAGNode(
        node_id="node_executive_narrative",
        section_id="sec_synthesis",
        section_title="7. Executive Synthesis, Scoring & Patches",
        title="C-Suite Executive Narrative Synthesis",
        description="Compiles high-level strategic narrative, trade-offs, strengths, blockers, and what to ignore.",
        agent_name="NarrativeGenerator",
        dependencies=["node_honest_scoring"],
    ),
    "node_code_patch_pack": DAGNode(
        node_id="node_code_patch_pack",
        section_id="sec_synthesis",
        section_title="7. Executive Synthesis, Scoring & Patches",
        title="Ready-to-Install Code Patch Pack",
        description="Generates production schema.jsonld, semantic FAQ code, and drop-in developer copy patches.",
        agent_name="PatchPackGenerator",
        dependencies=["node_honest_scoring"],
    ),
    "node_final_report_assembly": DAGNode(
        node_id="node_final_report_assembly",
        section_id="sec_synthesis",
        section_title="7. Executive Synthesis, Scoring & Patches",
        title="Report Packaging & Validation Gate",
        description="Assembles executive report, validates integrity schema, and finalizes audit state.",
        agent_name="ValidationGate",
        dependencies=["node_executive_narrative", "node_code_patch_pack"],
    ),
}


class NodeExecutionState:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.status = GraphNodeStatus.PENDING
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.duration_ms: float = 0.0
        self.error_message: Optional[str] = None
        self.evidence_count: int = 0
        self.claims_count: int = 0
        self.findings_count: int = 0
        self.output_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "evidence_count": self.evidence_count,
            "claims_count": self.claims_count,
            "findings_count": self.findings_count,
            "output_summary": self.output_summary,
        }


class PipelineExecutionController:
    """Controls lifecycle (run, pause, stop, resume, run-single-node) for an analysis run."""

    def __init__(self, analysis_id: str):
        self.analysis_id = analysis_id
        self.nodes_state: Dict[str, NodeExecutionState] = {
            node_id: NodeExecutionState(node_id) for node_id in NODES_REGISTRY
        }
        self.activity_log: List[ActivityEvent] = []
        self._pause_requested = False
        self._stop_requested = False
        self._lock = asyncio.Lock()

    def request_pause(self) -> None:
        self._pause_requested = True

    def request_stop(self) -> None:
        self._stop_requested = True
        self._pause_requested = True

    def clear_pause(self) -> None:
        self._pause_requested = False
        self._stop_requested = False

    def is_pause_requested(self) -> bool:
        return self._pause_requested

    def is_stop_requested(self) -> bool:
        return self._stop_requested

    def log_activity(
        self,
        node_id: str,
        status: str,
        action: str,
        summary: str,
        details: Optional[Dict[str, Any]] = None,
        cost_delta_usd: float = 0.0,
        evidence_count: int = 0,
    ) -> ActivityEvent:
        node = NODES_REGISTRY.get(node_id)
        sec_id = node.section_id if node else "sec_unknown"
        sec_title = node.section_title if node else "Unknown Section"
        n_title = node.title if node else node_id
        agent = node.agent_name if node else "Agent"

        event = ActivityEvent(
            section_id=sec_id,
            section_title=sec_title,
            node_id=node_id,
            node_title=n_title,
            agent_name=agent,
            status=status,
            action=action,
            summary=summary,
            details=details,
            cost_delta_usd=cost_delta_usd,
            evidence_count=evidence_count,
        )
        self.activity_log.append(event)
        # Limit in-memory rolling buffer to 250 items
        if len(self.activity_log) > 250:
            self.activity_log = self.activity_log[-250:]
        return event

    def get_node_status(self, node_id: str) -> GraphNodeStatus:
        st = self.nodes_state.get(node_id)
        return st.status if st else GraphNodeStatus.PENDING

    def mark_node_status(
        self,
        node_id: str,
        status: GraphNodeStatus,
        error_message: Optional[str] = None,
        output_summary: Optional[str] = None,
        evidence_count: int = 0,
        claims_count: int = 0,
        findings_count: int = 0,
    ) -> None:
        st = self.nodes_state.setdefault(node_id, NodeExecutionState(node_id))
        st.status = status
        now_iso = datetime.now(timezone.utc).isoformat()
        if status == GraphNodeStatus.RUNNING:
            st.started_at = now_iso
            st.error_message = None
        elif status in (GraphNodeStatus.COMPLETED, GraphNodeStatus.FAILED, GraphNodeStatus.PAUSED):
            st.completed_at = now_iso
            if st.started_at:
                try:
                    s_dt = datetime.fromisoformat(st.started_at)
                    c_dt = datetime.fromisoformat(st.completed_at)
                    st.duration_ms = max(0.0, (c_dt - s_dt).total_seconds() * 1000.0)
                except Exception:
                    pass
            if error_message:
                st.error_message = error_message
            if output_summary:
                st.output_summary = output_summary
            if evidence_count:
                st.evidence_count = evidence_count
            if claims_count:
                st.claims_count = claims_count
            if findings_count:
                st.findings_count = findings_count

    def are_dependencies_met(self, node_id: str) -> bool:
        """Returns True if every required dependency for node_id is in COMPLETED state."""
        node = NODES_REGISTRY.get(node_id)
        if not node:
            return False
        for dep_id in node.dependencies:
            dep_st = self.nodes_state.get(dep_id)
            if not dep_st or dep_st.status != GraphNodeStatus.COMPLETED:
                return False
        return True

    def get_missing_dependencies(self, node_id: str) -> List[str]:
        node = NODES_REGISTRY.get(node_id)
        if not node:
            return []
        missing = []
        for dep_id in node.dependencies:
            dep_st = self.nodes_state.get(dep_id)
            if not dep_st or dep_st.status != GraphNodeStatus.COMPLETED:
                missing.append(dep_id)
        return missing

    def get_full_graph_state(self) -> Dict[str, Any]:
        """Returns complete serializable graph topology, statuses, and recent activity events."""
        nodes_dict: Dict[str, Any] = {}
        for nid, node in NODES_REGISTRY.items():
            st = self.nodes_state.get(nid, NodeExecutionState(nid))
            can_run = self.are_dependencies_met(nid)
            missing = self.get_missing_dependencies(nid)
            nodes_dict[nid] = {
                "node_id": node.node_id,
                "section_id": node.section_id,
                "section_title": node.section_title,
                "title": node.title,
                "description": node.description,
                "agent_name": node.agent_name,
                "dependencies": node.dependencies,
                "status": st.status.value,
                "can_run_separately": can_run and st.status != GraphNodeStatus.RUNNING,
                "missing_dependencies": missing,
                "started_at": st.started_at,
                "completed_at": st.completed_at,
                "duration_ms": st.duration_ms,
                "error_message": st.error_message,
                "evidence_count": st.evidence_count,
                "claims_count": st.claims_count,
                "findings_count": st.findings_count,
                "output_summary": st.output_summary,
            }

        sections_list = [s.to_dict() for s in SECTIONS_REGISTRY]
        # Calculate completion percentage
        completed_count = sum(1 for n in self.nodes_state.values() if n.status == GraphNodeStatus.COMPLETED)
        total_count = len(NODES_REGISTRY)
        progress_pct = int((completed_count / total_count) * 100) if total_count > 0 else 0

        return {
            "analysis_id": self.analysis_id,
            "progress_percentage": progress_pct,
            "completed_nodes": completed_count,
            "total_nodes": total_count,
            "is_paused": self._pause_requested,
            "sections": sections_list,
            "nodes": nodes_dict,
            "activity_events": [e.to_dict() for e in self.activity_log[-60:]],
        }


# Process-wide store of controllers
_controllers: Dict[str, PipelineExecutionController] = {}


def get_pipeline_controller(analysis_id: str) -> PipelineExecutionController:
    if analysis_id not in _controllers:
        _controllers[analysis_id] = PipelineExecutionController(analysis_id)
    return _controllers[analysis_id]


def remove_pipeline_controller(analysis_id: str) -> None:
    _controllers.pop(analysis_id, None)

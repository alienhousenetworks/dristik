"""
Directed Acyclic Graph (DAG) and Dependency Engine for the SEO Orchestrator.
Constructs topological execution waves for parallel agent scheduling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
from app.seo.audit.orchestration.execution_state import AuditMode


class DAGStage(str, Enum):
    STAGE_1_CONFIG_DISCOVERY = "STAGE_1_CONFIG_DISCOVERY"
    STAGE_2_URL_INVENTORY = "STAGE_2_URL_INVENTORY"
    STAGE_3_CRAWL_AND_RENDER = "STAGE_3_CRAWL_AND_RENDER"
    STAGE_4_EVIDENCE_EXTRACTION = "STAGE_4_EVIDENCE_EXTRACTION"
    STAGE_5_PARALLEL_AGENTS = "STAGE_5_PARALLEL_AGENTS"
    STAGE_6_NORMALIZATION = "STAGE_6_NORMALIZATION"
    STAGE_7_DEDUPLICATION = "STAGE_7_DEDUPLICATION"
    STAGE_8_SCORING = "STAGE_8_SCORING"
    STAGE_9_REMEDIATION = "STAGE_9_REMEDIATION"
    STAGE_10_VALIDATION_GATE = "STAGE_10_VALIDATION_GATE"
    STAGE_11_PUBLICATION = "STAGE_11_PUBLICATION"


@dataclass
class DAGNode:
    agent_id: str
    agent_name: str
    stage: DAGStage
    dependencies: List[str] = field(default_factory=list)
    timeout_sec: float = 60.0
    retry_limit: int = 2
    is_optional: bool = False
    description: str = ""


class AuditDAG:
    """
    Constructs and verifies the execution DAG, generating parallel execution waves.
    """

    def __init__(self, mode: AuditMode = AuditMode.STANDARD):
        self.mode = mode
        self.nodes: Dict[str, DAGNode] = {}
        self._build_dag()
        self.validate()

    def add_node(self, node: DAGNode):
        self.nodes[node.agent_id] = node

    def _build_dag(self):
        # 1. Foundation: Discovery & Inventory
        self.add_node(DAGNode(
            agent_id="discovery_sitemap",
            agent_name="Sitemap & Host Discovery",
            stage=DAGStage.STAGE_1_CONFIG_DISCOVERY,
            dependencies=[],
            timeout_sec=30.0,
        ))
        self.add_node(DAGNode(
            agent_id="url_inventory",
            agent_name="6-Tier URL Inventory Builder",
            stage=DAGStage.STAGE_2_URL_INVENTORY,
            dependencies=["discovery_sitemap"],
            timeout_sec=30.0,
        ))

        # 2. Crawl & Evidence Snapshots
        self.add_node(DAGNode(
            agent_id="crawler_engine",
            agent_name="HTTP & Headless DOM Crawler",
            stage=DAGStage.STAGE_3_CRAWL_AND_RENDER,
            dependencies=["url_inventory"],
            timeout_sec=180.0 if self.mode == AuditMode.DEEP else 60.0,
        ))
        self.add_node(DAGNode(
            agent_id="evidence_extractor",
            agent_name="DOM & HTTP Evidence Extractor",
            stage=DAGStage.STAGE_4_EVIDENCE_EXTRACTION,
            dependencies=["crawler_engine"],
            timeout_sec=45.0,
        ))

        # 3. Parallel Specialist Agents (Stage 5)
        # Technical Group
        self.add_node(DAGNode(
            agent_id="agent_technical_http",
            agent_name="HTTP Status & Redirect Auditor",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_technical_canonical",
            agent_name="Canonical & Indexability Auditor",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_technical_cwv",
            agent_name="Core Web Vitals & Performance Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_technical_rendering",
            agent_name="JavaScript Rendering Disparity Auditor",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_technical_robots",
            agent_name="Robots.txt & X-Robots Directives Auditor",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_technical_ssl",
            agent_name="SSL Protocol & Mixed Content Security Auditor",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_technical_redirects",
            agent_name="Redirect Chain & Canonical Loop Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_technical_dom_size",
            agent_name="DOM Tree Size & Complexity Auditor",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))

        # On-Page Group
        self.add_node(DAGNode(
            agent_id="agent_onpage_metadata",
            agent_name="Metadata & Title Quality Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_onpage_headings",
            agent_name="Heading Hierarchy & Outline Auditor",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_onpage_media",
            agent_name="Media Asset & Image Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_onpage_linking",
            agent_name="Click Depth & Internal Linking Auditor",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))

        # Content & Authority Group
        self.add_node(DAGNode(
            agent_id="agent_content_quality",
            agent_name="Content Quality & Thin Text Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_content_intent",
            agent_name="Search Intent & Commercial Query Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_content_cannibalization",
            agent_name="Keyword & Content Cannibalization Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_content_depth",
            agent_name="Topical Depth & Entity Coverage Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))
        self.add_node(DAGNode(
            agent_id="agent_authority_backlinks",
            agent_name="Backlink Quality & Referring Domains Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
            is_optional=True,
        ))
        self.add_node(DAGNode(
            agent_id="agent_authority_trust",
            agent_name="Brand Trust & Entity Consistency Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))

        # Structured Data Group
        self.add_node(DAGNode(
            agent_id="agent_schema_validator",
            agent_name="Schema.org & Rich Results Validator",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
        ))

        # Specialized Extensions (Optional based on site characteristics)
        self.add_node(DAGNode(
            agent_id="agent_specialist_local",
            agent_name="Local SEO & NAP Consistency Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
            is_optional=True,
        ))
        self.add_node(DAGNode(
            agent_id="agent_specialist_ecommerce",
            agent_name="Ecommerce Product Architecture Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
            is_optional=True,
        ))
        self.add_node(DAGNode(
            agent_id="agent_specialist_international",
            agent_name="International Hreflang & Geotargeting Specialist",
            stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
            dependencies=["evidence_extractor"],
            is_optional=True,
        ))

        # 4. Aggregation, Deduplication, and Scoring
        all_agent_ids = [
            "agent_technical_http",
            "agent_technical_canonical",
            "agent_technical_cwv",
            "agent_technical_rendering",
            "agent_technical_robots",
            "agent_technical_ssl",
            "agent_technical_redirects",
            "agent_technical_dom_size",
            "agent_onpage_metadata",
            "agent_onpage_headings",
            "agent_onpage_media",
            "agent_onpage_linking",
            "agent_content_quality",
            "agent_content_intent",
            "agent_content_cannibalization",
            "agent_content_depth",
            "agent_schema_validator",
            "agent_authority_backlinks",
            "agent_authority_trust",
            "agent_specialist_local",
            "agent_specialist_ecommerce",
            "agent_specialist_international",
        ]

        self.add_node(DAGNode(
            agent_id="output_normalizer",
            agent_name="Agent Output Normalizer & Evidence Binder",
            stage=DAGStage.STAGE_6_NORMALIZATION,
            dependencies=all_agent_ids,
            timeout_sec=30.0,
        ))
        self.add_node(DAGNode(
            agent_id="finding_deduplicator",
            agent_name="Deterministic Finding Deduplicator",
            stage=DAGStage.STAGE_7_DEDUPLICATION,
            dependencies=["output_normalizer"],
            timeout_sec=30.0,
        ))
        self.add_node(DAGNode(
            agent_id="scoring_engine",
            agent_name="Deterministic Evidence-Aware Score Engine",
            stage=DAGStage.STAGE_8_SCORING,
            dependencies=["finding_deduplicator"],
            timeout_sec=30.0,
        ))
        self.add_node(DAGNode(
            agent_id="remediation_planner",
            agent_name="Remediation & Patch Pack Generator",
            stage=DAGStage.STAGE_9_REMEDIATION,
            dependencies=["scoring_engine"],
            timeout_sec=30.0,
        ))
        self.add_node(DAGNode(
            agent_id="validation_gate",
            agent_name="Independent Publication Quality Gate",
            stage=DAGStage.STAGE_10_VALIDATION_GATE,
            dependencies=["remediation_planner"],
            timeout_sec=30.0,
        ))
        self.add_node(DAGNode(
            agent_id="canonical_publisher",
            agent_name="Canonical Assessment Publisher",
            stage=DAGStage.STAGE_11_PUBLICATION,
            dependencies=["validation_gate"],
            timeout_sec=30.0,
        ))

    def validate(self) -> None:
        """Ensures the graph has no cycles and all dependencies exist."""
        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(f"DAG dependency error: Node '{node_id}' depends on non-existent node '{dep}'")

        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def _has_cycle(v: str) -> bool:
            visited.add(v)
            rec_stack.add(v)
            for neighbor in self.nodes[v].dependencies:
                if neighbor not in visited:
                    if _has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(v)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if _has_cycle(node_id):
                    raise ValueError("DAG validation error: Cycle detected in audit execution graph")

    def get_waves(self) -> List[List[DAGNode]]:
        """
        Calculates topological execution waves.
        All nodes in a wave can be executed concurrently in parallel.
        """
        in_degree: Dict[str, int] = {node_id: len(node.dependencies) for node_id, node in self.nodes.items()}
        # reverse graph: dep -> set of nodes waiting on dep
        dependents: Dict[str, List[str]] = {node_id: [] for node_id in self.nodes}
        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                dependents[dep].append(node_id)

        waves: List[List[DAGNode]] = []
        current_wave = [self.nodes[nid] for nid, deg in in_degree.items() if deg == 0]

        while current_wave:
            waves.append(current_wave)
            next_wave: List[DAGNode] = []
            for node in current_wave:
                for dependent_id in dependents[node.agent_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        next_wave.append(self.nodes[dependent_id])
            current_wave = next_wave

        return waves

    def get_ready_nodes(self, completed_ids: Set[str], failed_ids: Optional[Set[str]] = None) -> List[DAGNode]:
        """Returns all nodes whose dependencies have been completed."""
        failed_ids = failed_ids or set()
        ready = []
        for node_id, node in self.nodes.items():
            if node_id not in completed_ids and node_id not in failed_ids:
                if all(dep in completed_ids for dep in node.dependencies):
                    ready.append(node)
        return ready

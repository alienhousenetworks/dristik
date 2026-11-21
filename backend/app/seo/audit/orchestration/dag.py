"""
Directed Acyclic Graph (DAG) and Dependency Engine for the SEO Orchestrator.
Defines all 40 enterprise SEO specialist roles across 10 functional departments
plus the core crawl, extraction, normalization, deduplication, scoring,
remediation, QA validation, and canonical publication stages.
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
    department: str = "pipeline"
    execution_mode: str = "deterministic"  # deterministic | ai_assisted | connector_gated
    required_connector: Optional[str] = None
    timeout_sec: float = 60.0
    retry_limit: int = 2
    is_optional: bool = False
    is_conditional: bool = False
    is_specialist: bool = False
    description: str = ""


class AuditDAG:
    """
    Constructs and verifies the 40-specialist enterprise execution DAG,
    generating topological parallel execution waves.
    """

    def __init__(self, mode: AuditMode = AuditMode.STANDARD):
        self.mode = mode
        self.nodes: Dict[str, DAGNode] = {}
        self._build_dag()
        self.validate()

    def add_node(self, node: DAGNode) -> None:
        self.nodes[node.agent_id] = node

    @property
    def specialist_nodes(self) -> List[DAGNode]:
        return [n for n in self.nodes.values() if n.is_specialist]

    def _build_dag(self) -> None:
        # =====================================================================
        # Department A — Discovery and Crawling (4 Specialists + Core Crawl)
        # =====================================================================
        self.add_node(DAGNode(
            agent_id="discovery_sitemap",  # Role 1 & 3 anchor (kept for compat)
            agent_name="SEO Discovery & Sitemap Agent",
            stage=DAGStage.STAGE_1_CONFIG_DISCOVERY,
            dependencies=[],
            department="A_discovery_crawling",
            execution_mode="deterministic",
            timeout_sec=30.0,
            is_specialist=True,
            description="Domain/host discovery, CMS/tech detection, robots.txt & XML sitemap validation.",
        ))
        self.add_node(DAGNode(
            agent_id="agent_sitemap_validator",  # Role 3: Sitemap Agent
            agent_name="XML Sitemap Validator Agent",
            stage=DAGStage.STAGE_1_CONFIG_DISCOVERY,
            dependencies=["discovery_sitemap"],
            department="A_discovery_crawling",
            execution_mode="deterministic",
            timeout_sec=30.0,
            is_specialist=True,
            description="Validates sitemap indexes, nested sitemaps, lastmod accuracy, and canonical inclusion.",
        ))
        self.add_node(DAGNode(
            agent_id="url_inventory",  # Role 2: URL Intelligence Agent
            agent_name="URL Intelligence & 6-Tier Inventory Agent",
            stage=DAGStage.STAGE_2_URL_INVENTORY,
            dependencies=["discovery_sitemap", "agent_sitemap_validator"],
            department="A_discovery_crawling",
            execution_mode="deterministic",
            timeout_sec=30.0,
            is_specialist=True,
            description="URL enumeration, normalization, parameter/trailing-slash patterns, and 6-tier inventory.",
        ))
        self.add_node(DAGNode(
            agent_id="agent_crawl_strategy",  # Role 4: Crawl Strategy Agent
            agent_name="Crawl Strategy & Budget Planner Agent",
            stage=DAGStage.STAGE_2_URL_INVENTORY,
            dependencies=["url_inventory"],
            department="A_discovery_crawling",
            execution_mode="deterministic",
            timeout_sec=30.0,
            is_specialist=True,
            description="Prioritizes commercial URLs, enforces crawl budgets, detects traps and orphan candidates.",
        ))

        # Core Crawl & Evidence Snapshot Infrastructure
        self.add_node(DAGNode(
            agent_id="crawler_engine",
            agent_name="HTTP & Headless DOM Crawler",
            stage=DAGStage.STAGE_3_CRAWL_AND_RENDER,
            dependencies=["agent_crawl_strategy"],
            department="infrastructure",
            execution_mode="deterministic",
            timeout_sec=180.0 if self.mode == AuditMode.DEEP else 60.0,
        ))
        self.add_node(DAGNode(
            agent_id="evidence_extractor",
            agent_name="DOM & HTTP Evidence Extractor",
            stage=DAGStage.STAGE_4_EVIDENCE_EXTRACTION,
            dependencies=["crawler_engine"],
            department="infrastructure",
            execution_mode="deterministic",
            timeout_sec=45.0,
        ))

        # =====================================================================
        # Stage 5 — Parallel Specialist Workforce (Departments B–I)
        # =====================================================================
        stage5_specs = [
            # Department B — Technical SEO (6 Specialists: Roles 5–10)
            DAGNode(
                agent_id="agent_technical_http",
                agent_name="HTTP Status & Redirects Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="B_technical_seo",
                is_specialist=True,
                description="2xx/3xx/4xx/5xx classification, redirect loops/chains, soft 404s, broken links.",
            ),
            DAGNode(
                agent_id="agent_technical_indexability",
                agent_name="Indexability & Robots Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="B_technical_seo",
                is_specialist=True,
                description="Robots.txt, meta robots, X-Robots-Tag, indexability and sitemap conflicts.",
            ),
            DAGNode(
                agent_id="agent_technical_canonical",
                agent_name="Canonicalization Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="B_technical_seo",
                is_specialist=True,
                description="Self-referencing/cross-domain canonicals, canonical-vs-redirect, protocol/host consistency.",
            ),
            DAGNode(
                agent_id="agent_technical_rendering",
                agent_name="JavaScript SEO & Rendering Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="B_technical_seo",
                is_specialist=True,
                description="Raw HTML vs rendered DOM parity, hydration failures, JS-only links/content.",
            ),
            DAGNode(
                agent_id="agent_technical_cwv",
                agent_name="Core Web Vitals & Performance Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="B_technical_seo",
                is_specialist=True,
                description="Separate lab & field LCP, INP, CLS, FCP, TTFB measurements.",
            ),
            DAGNode(
                agent_id="agent_technical_mobile",
                agent_name="Mobile SEO & Usability Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="B_technical_seo",
                is_specialist=True,
                description="Responsive viewport, overflow, touch targets, mobile rendering parity.",
            ),

            # Department C — On-Page SEO (5 Specialists: Roles 11–15)
            DAGNode(
                agent_id="agent_onpage_metadata",
                agent_name="Metadata & Snippets Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="C_on_page_seo",
                is_specialist=True,
                description="Missing/duplicate/generic titles and meta descriptions, pixel truncation diagnostics.",
            ),
            DAGNode(
                agent_id="agent_onpage_headings",
                agent_name="Heading Hierarchy Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="C_on_page_seo",
                is_specialist=True,
                description="H1–H6 structure, missing/multiple H1s, semantic hierarchy.",
            ),
            DAGNode(
                agent_id="agent_onpage_media",
                agent_name="Image & Media SEO Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="C_on_page_seo",
                is_specialist=True,
                description="Alt attributes, explicit dimensions, modern formats, lazy loading.",
            ),
            DAGNode(
                agent_id="agent_onpage_linking",
                agent_name="Internal Linking & Link Graph Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="C_on_page_seo",
                is_specialist=True,
                description="Directed link graph, BFS click depth, PageRank equity, orphans, anchors.",
            ),
            DAGNode(
                agent_id="agent_onpage_url_optimization",
                agent_name="URL Optimization Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="C_on_page_seo",
                is_specialist=True,
                description="URL structure, readability, parameter duplication, case & trailing-slash consistency.",
            ),

            # Department D — Content & Semantic Intelligence (5 Specialists: Roles 16–20)
            DAGNode(
                agent_id="agent_content_quality",
                agent_name="Content Quality Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="D_content_semantic",
                execution_mode="ai_assisted",
                is_specialist=True,
                description="Thin content, duplicate/near-duplicate content, content depth & freshness.",
            ),
            DAGNode(
                agent_id="agent_content_intent",
                agent_name="Search Intent Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="D_content_semantic",
                execution_mode="ai_assisted",
                is_specialist=True,
                description="Informational/commercial/transactional/navigational/local intent alignment.",
            ),
            DAGNode(
                agent_id="agent_content_semantic",
                agent_name="Semantic SEO & Entity Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="D_content_semantic",
                execution_mode="ai_assisted",
                is_specialist=True,
                description="Entities, concepts, and topical relationship density grounded in page text.",
            ),
            DAGNode(
                agent_id="agent_content_topical_authority",
                agent_name="Topical Authority & Clusters Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="D_content_semantic",
                is_specialist=True,
                description="Topic clusters, pillar/spoke cohesion, cannibalization detection.",
            ),
            DAGNode(
                agent_id="agent_content_gap",
                agent_name="Content Gap & Refresh Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="D_content_semantic",
                execution_mode="ai_assisted",
                is_specialist=True,
                description="Missing subtopics, refresh opportunities, and commercial content coverage gaps.",
            ),

            # Department E — Structured Data & Entities (4 Specialists: Roles 21–24)
            DAGNode(
                agent_id="agent_schema_detection",
                agent_name="Schema Detection Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="E_structured_data",
                is_specialist=True,
                description="Detects JSON-LD, Microdata, and RDFa blocks across crawled pages.",
            ),
            DAGNode(
                agent_id="agent_schema_validator",
                agent_name="Schema Validation Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="E_structured_data",
                is_specialist=True,
                description="Validates Schema.org syntax, required/recommended properties, and types.",
            ),
            DAGNode(
                agent_id="agent_entity_graph",
                agent_name="Entity Graph Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="E_structured_data",
                is_specialist=True,
                description="Resolves Organization/Brand/Person/Product entity relationships and sameAs links.",
            ),
            DAGNode(
                agent_id="agent_rich_results",
                agent_name="Rich Results Eligibility Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="E_structured_data",
                is_specialist=True,
                description="Separates schema validity from rich-result eligibility and observed SERP appearance.",
            ),

            # Department F — Authority & Trust (4 Specialists: Roles 25–28)
            DAGNode(
                agent_id="agent_authority_backlinks",
                agent_name="Backlink Intelligence Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="F_authority_trust",
                execution_mode="connector_gated",
                required_connector="backlink_provider",
                is_optional=True,
                is_specialist=True,
                description="Backlink profile analysis (returns DATA_UNAVAILABLE without connected provider).",
            ),
            DAGNode(
                agent_id="agent_authority_referring_domains",
                agent_name="Referring Domain Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="F_authority_trust",
                execution_mode="connector_gated",
                required_connector="backlink_provider",
                is_optional=True,
                is_specialist=True,
                description="Referring domain distribution & quality (connector-gated).",
            ),
            DAGNode(
                agent_id="agent_authority_eeat",
                agent_name="E-E-A-T & Observable Trust Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="F_authority_trust",
                is_specialist=True,
                description="Observable experience, expertise, authorship, editorial, and policy trust signals.",
            ),
            DAGNode(
                agent_id="agent_authority_trust",
                agent_name="Brand Entity & Security Trust Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="F_authority_trust",
                is_specialist=True,
                description="Brand identity consistency, HTTPS/TLS, HSTS, and mixed-content trust checks.",
            ),

            # Department G — Local & International SEO (4 Specialists: Roles 29–32)
            DAGNode(
                agent_id="agent_specialist_local",
                agent_name="Local SEO & NAP Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="G_local_international",
                is_optional=True,
                is_conditional=True,
                is_specialist=True,
                description="NAP consistency, LocalBusiness schema, location landing pages.",
            ),
            DAGNode(
                agent_id="agent_local_gbp",
                agent_name="Google Business Profile Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="G_local_international",
                execution_mode="connector_gated",
                required_connector="google_business_profile",
                is_optional=True,
                is_conditional=True,
                is_specialist=True,
                description="Google Business Profile verification and local entity sync (connector-gated).",
            ),
            DAGNode(
                agent_id="agent_specialist_international",
                agent_name="International SEO Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="G_local_international",
                is_optional=True,
                is_conditional=True,
                is_specialist=True,
                description="Language and regional URL architecture and localized metadata.",
            ),
            DAGNode(
                agent_id="agent_international_hreflang",
                agent_name="Hreflang Reciprocity Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="G_local_international",
                is_optional=True,
                is_conditional=True,
                is_specialist=True,
                description="Hreflang syntax, ISO codes, x-default, reciprocity, canonical alignment.",
            ),

            # Department H — Ecommerce SEO (3 Conditional Specialists: Roles 33–35)
            DAGNode(
                agent_id="agent_ecommerce_product",
                agent_name="Product SEO Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="H_ecommerce_seo",
                is_optional=True,
                is_conditional=True,
                is_specialist=True,
                description="Product schema, pricing/availability consistency, variant indexing, OOS handling.",
            ),
            DAGNode(
                agent_id="agent_ecommerce_category",
                agent_name="Category & Collection SEO Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="H_ecommerce_seo",
                is_optional=True,
                is_conditional=True,
                is_specialist=True,
                description="Collection hierarchy, category copy depth, internal product discovery.",
            ),
            DAGNode(
                agent_id="agent_specialist_ecommerce",
                agent_name="Ecommerce Architecture & Facets Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="H_ecommerce_seo",
                is_optional=True,
                is_conditional=True,
                is_specialist=True,
                description="Faceted navigation, filter URLs, pagination, and product duplication control.",
            ),

            # Department I — Search Performance & Competitors (3 Specialists: Roles 36–38)
            DAGNode(
                agent_id="agent_search_console",
                agent_name="GSC Intelligence Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="I_performance_competitors",
                execution_mode="connector_gated",
                required_connector="google_search_console",
                is_optional=True,
                is_specialist=True,
                description="Clicks, impressions, CTR, average position, decay, cannibalization (GSC-gated).",
            ),
            DAGNode(
                agent_id="agent_ga4_analytics",
                agent_name="GA4 Organic Intelligence Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="I_performance_competitors",
                execution_mode="connector_gated",
                required_connector="google_analytics_4",
                is_optional=True,
                is_specialist=True,
                description="Organic sessions, landing-page engagement, key events, conversions (GA4-gated).",
            ),
            DAGNode(
                agent_id="agent_competitor_seo",
                agent_name="Competitor SEO Agent",
                stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
                dependencies=["evidence_extractor"],
                department="I_performance_competitors",
                execution_mode="connector_gated",
                required_connector="keyword_serp_provider",
                is_optional=True,
                is_specialist=True,
                description="Competitor SERP/keyword overlap and parity (strictly source-grounded).",
            ),
        ]

        for spec in stage5_specs:
            self.add_node(spec)

        stage5_ids = [s.agent_id for s in stage5_specs]

        # =====================================================================
        # Stages 6–11 — Normalization, Deduplication, Scoring, Dept J (Roles 39–40) & Publication
        # =====================================================================
        self.add_node(DAGNode(
            agent_id="output_normalizer",
            agent_name="Agent Output Normalizer & Evidence Binder",
            stage=DAGStage.STAGE_6_NORMALIZATION,
            dependencies=stage5_ids,
            department="infrastructure",
            timeout_sec=30.0,
        ))
        self.add_node(DAGNode(
            agent_id="finding_deduplicator",
            agent_name="Root-Cause & Finding Deduplicator",
            stage=DAGStage.STAGE_7_DEDUPLICATION,
            dependencies=["output_normalizer"],
            department="infrastructure",
            timeout_sec=30.0,
        ))
        self.add_node(DAGNode(
            agent_id="scoring_engine",
            agent_name="9-Dimension Mathematical Score Engine",
            stage=DAGStage.STAGE_8_SCORING,
            dependencies=["finding_deduplicator"],
            department="infrastructure",
            timeout_sec=30.0,
        ))
        self.add_node(DAGNode(
            agent_id="remediation_planner",  # Role 40: SEO Strategy & Remediation Agent
            agent_name="SEO Strategy & Remediation Agent",
            stage=DAGStage.STAGE_9_REMEDIATION,
            dependencies=["scoring_engine"],
            department="J_qa_strategy",
            execution_mode="deterministic",
            timeout_sec=30.0,
            is_specialist=True,
            description="Transforms verified findings into stack-aware fixes, roadmaps, and acceptance criteria.",
        ))
        self.add_node(DAGNode(
            agent_id="validation_gate",  # Role 39: Independent SEO Quality Assurance Agent
            agent_name="SEO Quality Assurance & Fail-Closed Gate Agent",
            stage=DAGStage.STAGE_10_VALIDATION_GATE,
            dependencies=["remediation_planner"],
            department="J_qa_strategy",
            execution_mode="deterministic",
            timeout_sec=30.0,
            is_specialist=True,
            description="Independently validates all 10 QA matrix gates before allowing publication.",
        ))
        self.add_node(DAGNode(
            agent_id="canonical_publisher",
            agent_name="Canonical SEO Audit Publisher",
            stage=DAGStage.STAGE_11_PUBLICATION,
            dependencies=["validation_gate"],
            department="infrastructure",
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
        """Calculates topological execution waves for concurrent execution."""
        in_degree: Dict[str, int] = {node_id: len(node.dependencies) for node_id, node in self.nodes.items()}
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

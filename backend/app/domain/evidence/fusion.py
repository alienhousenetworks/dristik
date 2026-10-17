"""
Dristik Multi-Plane Evidence Fusion Layer.
Unifies all 6 digital intelligence planes into a single relational graph:
1. FIRST-PARTY: Crawl, DOM, Structured Schema, Sitemap, Robots, Lab Performance.
2. SEARCH: Google Search Console, SERPs, Indexation, Query CTRs.
3. ANALYTICS: GA4, Conversion Funnels, Landing Page Drop-off.
4. AUTHORITY: Backlinks, Referring Domains, SameAs, Business Directories.
5. AI RETRIEVAL: Answer Engines (Perplexity, ChatGPT, Claude, Gemini, Google AIO).
6. COMPETITIVE: Crawled Competitors, Co-citations, Structural Feature Parity.

Enforces zero-fake fail-closed semantics: Unconnected external sources register
as immutable CONNECTOR_STATUS nodes without synthetic placeholder values.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.evidence.graph import EvidenceGraph, GraphNodeType, GraphEdgeType
from app.domain.evidence.store import EvidenceStore

logger = logging.getLogger(__name__)


class EvidencePlane(str, Enum):
    FIRST_PARTY = "FIRST_PARTY"
    SEARCH = "SEARCH"
    ANALYTICS = "ANALYTICS"
    AUTHORITY = "AUTHORITY"
    AI_RETRIEVAL = "AI_RETRIEVAL"
    COMPETITIVE = "COMPETITIVE"


class ConnectorStatus(BaseModel):
    plane: EvidencePlane
    connector_id: str
    is_connected: bool
    status_label: str  # "CONNECTED" | "NOT_CONFIGURED" | "RATE_LIMITED" | "ERROR"
    details: Optional[str] = None


class MultiPlaneFusionSummary(BaseModel):
    domain: str
    total_nodes: int
    plane_node_counts: Dict[str, int] = Field(default_factory=dict)
    active_planes: List[str] = Field(default_factory=list)
    connector_statuses: List[ConnectorStatus] = Field(default_factory=list)
    cross_plane_corroborations_count: int = 0


class MultiPlaneEvidenceFusion:
    """
    Fuses multi-source evidence across all 6 planes into EvidenceGraph 2.0.
    """

    @classmethod
    def fuse_all_planes(
        cls,
        graph: EvidenceGraph,
        domain: str,
        manifest: Optional[Any] = None,
        evidence_store: Optional[EvidenceStore] = None,
        external_authority: Optional[Dict[str, Any]] = None,
        gsc_data: Optional[Dict[str, Any]] = None,
        ga4_data: Optional[Dict[str, Any]] = None,
        observatory_records: Optional[List[Any]] = None,
        competitive_graph: Optional[Any] = None,
    ) -> MultiPlaneFusionSummary:
        plane_counts: Dict[str, int] = {p.value: 0 for p in EvidencePlane}
        connectors: List[ConnectorStatus] = []
        site_node_id = f"site_{domain.replace('.', '_')}"

        # -------------------------------------------------------------
        # Plane 1: First-Party
        # -------------------------------------------------------------
        pages = getattr(manifest, "pages", []) or []
        plane_counts[EvidencePlane.FIRST_PARTY.value] += len(pages)
        if evidence_store:
            plane_counts[EvidencePlane.FIRST_PARTY.value] += evidence_store.count()

        # -------------------------------------------------------------
        # Plane 2: Search (Google Search Console / SERPs)
        # -------------------------------------------------------------
        if gsc_data and gsc_data.get("connected"):
            search_node_id = f"plane_search_{domain.replace('.', '_')}"
            graph.add_node(
                node_id=search_node_id,
                node_type="SEARCH_SOURCE",
                label="Google Search Console",
                properties={"queries_tracked": len(gsc_data.get("queries", [])), "plane": EvidencePlane.SEARCH.value}
            )
            graph.add_edge(site_node_id, search_node_id, GraphEdgeType.MEASURED_BY)
            plane_counts[EvidencePlane.SEARCH.value] += 1
            connectors.append(ConnectorStatus(
                plane=EvidencePlane.SEARCH,
                connector_id="google_search_console",
                is_connected=True,
                status_label="CONNECTED"
            ))
        else:
            connectors.append(ConnectorStatus(
                plane=EvidencePlane.SEARCH,
                connector_id="google_search_console",
                is_connected=False,
                status_label="NOT_CONFIGURED",
                details="GSC connector OAuth not authenticated. GSC search queries remain unmeasured."
            ))

        # -------------------------------------------------------------
        # Plane 3: Analytics (GA4 Conversions / Engagement)
        # -------------------------------------------------------------
        if ga4_data and ga4_data.get("connected"):
            analytics_node_id = f"plane_analytics_{domain.replace('.', '_')}"
            graph.add_node(
                node_id=analytics_node_id,
                node_type="ANALYTICS_SOURCE",
                label="Google Analytics 4",
                properties={"conversions_tracked": len(ga4_data.get("events", [])), "plane": EvidencePlane.ANALYTICS.value}
            )
            graph.add_edge(site_node_id, analytics_node_id, GraphEdgeType.MEASURED_BY)
            plane_counts[EvidencePlane.ANALYTICS.value] += 1
            connectors.append(ConnectorStatus(
                plane=EvidencePlane.ANALYTICS,
                connector_id="google_analytics_4",
                is_connected=True,
                status_label="CONNECTED"
            ))
        else:
            connectors.append(ConnectorStatus(
                plane=EvidencePlane.ANALYTICS,
                connector_id="google_analytics_4",
                is_connected=False,
                status_label="NOT_CONFIGURED",
                details="GA4 Data API not authenticated. Funnel conversion drop-off remains qualitative."
            ))

        # -------------------------------------------------------------
        # Plane 4: Authority (Backlinks / SameAs / Registries)
        # -------------------------------------------------------------
        has_real_backlinks = bool(external_authority and external_authority.get("connected") and external_authority.get("backlinks"))
        if has_real_backlinks:
            auth_node_id = f"plane_auth_{domain.replace('.', '_')}"
            graph.add_node(
                node_id=auth_node_id,
                node_type="AUTHORITY_SOURCE",
                label="External Backlink & Domain Authority",
                properties={"referring_domains": external_authority.get("referring_domains"), "plane": EvidencePlane.AUTHORITY.value}
            )
            graph.add_edge(site_node_id, auth_node_id, GraphEdgeType.MEASURED_BY)
            plane_counts[EvidencePlane.AUTHORITY.value] += 1
            connectors.append(ConnectorStatus(
                plane=EvidencePlane.AUTHORITY,
                connector_id="backlink_authority_provider",
                is_connected=True,
                status_label="CONNECTED"
            ))
        else:
            connectors.append(ConnectorStatus(
                plane=EvidencePlane.AUTHORITY,
                connector_id="backlink_authority_provider",
                is_connected=False,
                status_label="NOT_CONFIGURED",
                details="External backlink API not configured. Off-page authority marked provisional."
            ))

        # -------------------------------------------------------------
        # Plane 5: AI Retrieval (Answer Engines)
        # -------------------------------------------------------------
        if observatory_records:
            for obs in observatory_records:
                obs_node_id = f"ai_obs_{getattr(obs, 'query_id', 'q')}_{getattr(obs, 'engine_id', 'eng')}"
                graph.add_node(
                    node_id=obs_node_id,
                    node_type=GraphNodeType.AI_ANSWER,
                    label=f"AI [{getattr(obs, 'engine_name', 'AI')}]: {getattr(obs, 'query_text', '')[:40]}",
                    properties={
                        "plane": EvidencePlane.AI_RETRIEVAL.value,
                        "brand_cited": getattr(obs, "brand_cited", False),
                        "brand_mentioned": getattr(obs, "brand_mentioned", False),
                        "prominence": getattr(obs, "position_prominence", "ABSENT"),
                    }
                )
                graph.add_edge(site_node_id, obs_node_id, GraphEdgeType.MEASURED_BY)
                plane_counts[EvidencePlane.AI_RETRIEVAL.value] += 1

        # -------------------------------------------------------------
        # Plane 6: Competitive
        # -------------------------------------------------------------
        if competitive_graph and hasattr(competitive_graph, "matrix_rows"):
            for row in competitive_graph.matrix_rows:
                comp_node_id = f"comp_row_{row.question_key}"
                graph.add_node(
                    node_id=comp_node_id,
                    node_type=GraphNodeType.COMPETITOR,
                    label=f"Comp: {row.intent_category}",
                    properties={
                        "plane": EvidencePlane.COMPETITIVE.value,
                        "target_status": row.target_status,
                        "winning_entity": row.winning_entity,
                        "why_won": row.why_winner_won,
                    }
                )
                graph.add_edge(site_node_id, comp_node_id, GraphEdgeType.COMPETES_WITH)
                plane_counts[EvidencePlane.COMPETITIVE.value] += 1

        active = [p for p, cnt in plane_counts.items() if cnt > 0]

        return MultiPlaneFusionSummary(
            domain=domain,
            total_nodes=len(graph.nodes),
            plane_node_counts=plane_counts,
            active_planes=active,
            connector_statuses=connectors,
            cross_plane_corroborations_count=sum(1 for c in connectors if c.is_connected)
        )


multi_plane_fusion = MultiPlaneEvidenceFusion()

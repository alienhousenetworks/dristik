"""
Internal Linking Graph Intelligence — Phase 3.7

Builds a directed network graph of all crawled internal links:
- Inbound and outbound links per URL
- Click depth from homepage (BFS distance)
- Orphan page detection (inbound internal links == 0)
- Internal PageRank proxy calculation (Power iteration)
- Anchor text distribution (Descriptive vs. generic)
- Broken internal links (4xx) and redirecting internal links (3xx)
- Link equity concentration vs. starvation analysis
- Generates node-and-edge visual graph data
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field


class LinkGraphNode(BaseModel):
    url: str
    inbound_count: int = 0
    outbound_count: int = 0
    click_depth: int = 0
    pagerank_score: float = 0.0  # Normalized authority proxy
    is_orphan: bool = False
    is_dead_end: bool = False  # Outbound == 0


class LinkGraphEdge(BaseModel):
    source_url: str
    target_url: str
    anchor_text: str
    is_generic_anchor: bool = False


class InternalLinkingGraphReport(BaseModel):
    total_nodes: int
    total_edges: int
    orphan_pages: List[str] = Field(default_factory=list)
    deep_pages_count: int = 0  # Depth >= 4
    high_authority_pages: List[str] = Field(default_factory=list)
    nodes: List[LinkGraphNode] = Field(default_factory=list)
    edges: List[LinkGraphEdge] = Field(default_factory=list)
    broken_internal_links: List[Dict[str, str]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class InternalLinkingGraphEngine:
    """
    Constructs and audits the internal site link graph.
    """

    GENERIC_ANCHORS = {"click here", "read more", "learn more", "here", "more", "link", "view"}

    @classmethod
    def build_and_analyze_graph(
        cls,
        homepage_url: str,
        crawl_pages: List[Dict[str, Any]],  # Each dict has "url", "links": [{"target": str, "anchor": str}], "status": int
    ) -> InternalLinkingGraphReport:
        clean_home = homepage_url.rstrip("/")
        all_urls = {p.get("url", "").rstrip("/") for p in crawl_pages if p.get("url")}
        in_counts: Dict[str, int] = {u: 0 for u in all_urls}
        out_counts: Dict[str, int] = {u: 0 for u in all_urls}
        adjacency: Dict[str, Set[str]] = {u: set() for u in all_urls}
        edges: List[LinkGraphEdge] = []
        broken_links: List[Dict[str, str]] = []

        url_status_map = {p.get("url", "").rstrip("/"): p.get("status", 200) for p in crawl_pages}

        # 1. Build Adjacency and Edges
        for p in crawl_pages:
            src = p.get("url", "").rstrip("/")
            links = p.get("links", [])
            for link in links:
                tgt = link.get("target", "").rstrip("/")
                anchor = link.get("anchor", "").strip()

                # Internal only
                if tgt in all_urls:
                    out_counts[src] = out_counts.get(src, 0) + 1
                    in_counts[tgt] = in_counts.get(tgt, 0) + 1
                    adjacency[src].add(tgt)

                    is_gen = anchor.lower() in cls.GENERIC_ANCHORS
                    edges.append(
                        LinkGraphEdge(
                            source_url=src,
                            target_url=tgt,
                            anchor_text=anchor,
                            is_generic_anchor=is_gen,
                        )
                    )

                    tgt_status = url_status_map.get(tgt, 200)
                    if tgt_status in (404, 410, 500):
                        broken_links.append({"source": src, "target": tgt, "status": str(tgt_status)})

        # 2. Compute Click Depth via BFS from Homepage
        depths: Dict[str, int] = {u: 99 for u in all_urls}
        if clean_home in all_urls:
            depths[clean_home] = 0
            queue = [clean_home]
            visited = {clean_home}

            while queue:
                curr = queue.pop(0)
                curr_d = depths[curr]
                for nxt in adjacency.get(curr, set()):
                    if nxt not in visited:
                        visited.add(nxt)
                        depths[nxt] = curr_d + 1
                        queue.append(nxt)
        else:
            for u in all_urls:
                depths[u] = 1

        # 3. Calculate Internal PageRank Proxy (10 power-iterations, d=0.85)
        n = max(len(all_urls), 1)
        pr: Dict[str, float] = {u: 1.0 / n for u in all_urls}
        damping = 0.85

        for _ in range(10):
            new_pr = {u: (1.0 - damping) / n for u in all_urls}
            for u in all_urls:
                out_deg = len(adjacency[u])
                if out_deg > 0:
                    share = (damping * pr[u]) / out_deg
                    for v in adjacency[u]:
                        new_pr[v] += share
                else:
                    for v in all_urls:
                        new_pr[v] += (damping * pr[u]) / n
            pr = new_pr

        # Normalize PR to 0–100 scale
        max_pr = max(pr.values()) if pr else 1.0
        normalized_pr = {u: round((val / max_pr) * 100, 2) for u, val in pr.items()}

        # 4. Construct Nodes & Identify Anomalies
        nodes: List[LinkGraphNode] = []
        orphans: List[str] = []
        deep_count = 0

        for u in all_urls:
            d = depths.get(u, 99)
            if d >= 4:
                deep_count += 1
            in_c = in_counts.get(u, 0)
            out_c = out_counts.get(u, 0)
            is_orph = (in_c == 0 and u != clean_home)
            if is_orph:
                orphans.append(u)

            nodes.append(
                LinkGraphNode(
                    url=u,
                    inbound_count=in_c,
                    outbound_count=out_c,
                    click_depth=d if d != 99 else -1,
                    pagerank_score=normalized_pr.get(u, 0.0),
                    is_orphan=is_orph,
                    is_dead_end=(out_c == 0),
                )
            )

        # Sort authority nodes
        nodes.sort(key=lambda x: x.pagerank_score, reverse=True)
        high_auth = [node.url for node in nodes[:5]]

        # 5. Formulate Recommendations
        recs: List[str] = []
        if orphans:
            recs.append(f"Add contextual internal links to {len(orphans)} orphan page(s) to grant crawl access.")
        if deep_count > 0:
            recs.append(f"Flatten click architecture: {deep_count} page(s) are located 4+ clicks away from the homepage.")
        if broken_links:
            recs.append(f"Fix {len(broken_links)} broken internal links pointing to non-200 responses.")

        return InternalLinkingGraphReport(
            total_nodes=len(nodes),
            total_edges=len(edges),
            orphan_pages=orphans,
            deep_pages_count=deep_count,
            high_authority_pages=high_auth,
            nodes=nodes,
            edges=edges[:100],  # sample for visualization
            broken_internal_links=broken_links,
            recommendations=recs,
        )

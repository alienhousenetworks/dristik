"""
Internal Link Graph & Architecture Engine
Calculates directed link graph, BFS click depth, PageRank link equity,
orphan pages, deep pages, weak internal links, broken links, and intra-cluster link suggestions.
"""
from typing import Dict, Any, List, Set, Optional, Tuple
from urllib.parse import urlparse
import re
from collections import deque

def classify_page_type(url: str, title: str = "", schemas: Optional[List[str]] = None) -> str:
    """Classifies a page into semantic taxonomy."""
    path = urlparse(url).path.lower().strip("/")
    schemas = schemas or []

    if not path or path == "":
        return "homepage"

    # Schema-based cues
    if any(s.lower() in ("product", "individualproduct") for s in schemas):
        return "product"
    if any(s.lower() in ("article", "blogposting", "newsarticle") for s in schemas):
        return "article"
    if any(s.lower() in ("service", "financialproduct") for s in schemas):
        return "service"

    # Check utility first
    if re.search(r"\b(privacy|terms|legal|cookie|contact|about|support|login|register)\b", path):
        return "utility"

    # Path slug patterns
    first_segment = path.split("/")[0]
    if re.search(r"\b(category|categories|collection|collections|catalog|shop|topics)\b", first_segment):
        return "category"
    if re.search(r"\b(product|products|item|items|sku)\b|^p$", first_segment):
        return "product"
    if re.search(r"\b(service|services|solutions|features)\b", first_segment):
        return "service"
    if re.search(r"\b(blog|articles|article|posts|post|guide|news|learn|resources)\b", first_segment):
        return "article"

    # Depth & title cues
    if "/" in path:
        return "product" if len(path.split("/")) > 2 else "category"
    return "service"

def assign_topic_cluster(url: str, page_type: str) -> str:
    """Assigns an architectural topic cluster based on path hierarchy."""
    path = urlparse(url).path.strip("/").lower()
    if not path:
        return "Core Brand & Home"
    
    segments = path.split("/")
    primary = segments[0].replace("-", " ").replace("_", " ").title()
    if page_type == "utility":
        return "Corporate & Legal"
    if page_type == "product" and len(segments) > 1:
        return f"{primary} Catalog"
    return f"{primary} Hub"

def compute_pagerank(
    nodes: List[str],
    adj_list: Dict[str, List[str]],
    damping: float = 0.85,
    max_iter: int = 20,
    tol: float = 1e-4
) -> Dict[str, float]:
    """Computes PageRank link equity via power iteration."""
    n = len(nodes)
    if n == 0:
        return {}
    if n == 1:
        return {nodes[0]: 100.0}

    # Initial uniform probability
    ranks = {node: 1.0 / n for node in nodes}
    out_degree = {node: len(adj_list.get(node, [])) for node in nodes}

    for _ in range(max_iter):
        new_ranks = {node: (1.0 - damping) / n for node in nodes}
        dangling_sum = sum(ranks[node] for node in nodes if out_degree[node] == 0)

        for node in nodes:
            targets = adj_list.get(node, [])
            if targets:
                share = (damping * ranks[node]) / len(targets)
                for t in targets:
                    if t in new_ranks:
                        new_ranks[t] += share

        dangling_share = (damping * dangling_sum) / n
        for node in nodes:
            new_ranks[node] += dangling_share

        # Convergence check
        diff = sum(abs(new_ranks[node] - ranks[node]) for node in nodes)
        ranks = new_ranks
        if diff < tol:
            break

    # Normalize to 0 - 100 scale
    max_rank = max(ranks.values()) if ranks else 1.0
    return {
        node: round((score / max_rank) * 100.0, 1) if max_rank > 0 else 50.0
        for node, score in ranks.items()
    }

def build_internal_link_graph(
    pages: List[Dict[str, Any]],
    domain: str,
    homepage_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Builds the complete internal link graph representation.
    """
    clean_domain = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
    if not homepage_url:
        homepage_url = f"https://{clean_domain}/"

    # 1. Normalize page inventory
    page_map: Dict[str, Dict[str, Any]] = {}
    for p in pages:
        raw_url = str(p.get("url") or "").strip()
        if not raw_url:
            continue
        parsed = urlparse(raw_url)
        clean_url = f"{parsed.scheme or 'https'}://{parsed.netloc or clean_domain}{parsed.path or '/'}"
        if parsed.query:
            clean_url += f"?{parsed.query}"
        page_map[clean_url] = p

    # Ensure homepage exists
    if homepage_url not in page_map and f"https://{clean_domain}" in page_map:
        homepage_url = f"https://{clean_domain}"
    elif homepage_url not in page_map:
        page_map[homepage_url] = {
            "url": homepage_url,
            "title": f"{clean_domain} Official Site",
            "status_code": 200,
            "word_count": 500,
        }

    all_node_urls = list(page_map.keys())

    # 2. Extract directed edges and adjacency list
    adj_list: Dict[str, List[str]] = {u: [] for u in all_node_urls}
    incoming_edges: Dict[str, List[Dict[str, Any]]] = {u: [] for u in all_node_urls}
    outgoing_edges: Dict[str, List[Dict[str, Any]]] = {u: [] for u in all_node_urls}
    broken_links: List[Dict[str, Any]] = []
    edges_list: List[Dict[str, Any]] = []

    for src_url, pdata in page_map.items():
        # Get internal links from page data
        raw_links = pdata.get("internal_links") or pdata.get("unique_internal_links") or []
        anchors = pdata.get("sample_anchors") or []
        anchor_map: Dict[str, str] = {
            a.get("target"): a.get("text", "Link") for a in anchors if isinstance(a, dict)
        }

        seen_targets = set()
        for raw_target in raw_links:
            target_str = str(raw_target).strip()
            if not target_str:
                continue
            parsed_t = urlparse(target_str)
            target_clean = f"{parsed_t.scheme or 'https'}://{parsed_t.netloc or clean_domain}{parsed_t.path or '/'}"
            if parsed_t.query:
                target_clean += f"?{parsed_t.query}"

            # Skip self-links
            if target_clean == src_url or target_clean in seen_targets:
                continue
            seen_targets.add(target_clean)

            # Check target status
            target_data = page_map.get(target_clean)
            target_status = target_data.get("status_code", 200) if target_data else 200
            is_broken = target_status >= 400

            anchor_text = anchor_map.get(target_clean) or pdata.get("title") or "Explore Page"
            edge_id = f"{src_url}->{target_clean}"

            edge_obj = {
                "id": edge_id,
                "source": src_url,
                "target": target_clean,
                "anchor_text": anchor_text,
                "link_context": "body",
                "is_broken": is_broken,
                "is_nofollow": False,
                "status_code": target_status,
            }

            edges_list.append(edge_obj)
            adj_list[src_url].append(target_clean)
            outgoing_edges[src_url].append(edge_obj)

            if target_clean in incoming_edges:
                incoming_edges[target_clean].append(edge_obj)

            if is_broken:
                broken_links.append({
                    "source_url": src_url,
                    "target_url": target_clean,
                    "anchor_text": anchor_text,
                    "status_code": target_status,
                    "error_detail": f"HTTP {target_status} Dead Link",
                })

    # 3. Compute BFS Click Depth from Homepage
    depths: Dict[str, int] = {u: 999 for u in all_node_urls}
    if homepage_url in depths:
        depths[homepage_url] = 0
        queue = deque([homepage_url])
        while queue:
            curr = queue.popleft()
            curr_depth = depths[curr]
            for neighbor in adj_list.get(curr, []):
                if neighbor in depths and depths[neighbor] > curr_depth + 1:
                    depths[neighbor] = curr_depth + 1
                    queue.append(neighbor)

    # 4. Compute PageRank Link Equity
    page_ranks = compute_pagerank(all_node_urls, adj_list)

    # 5. Build Nodes & Classify Taxonomy & Health
    nodes_list: List[Dict[str, Any]] = []
    orphan_count = 0
    deep_count = 0
    weak_count = 0

    clusters_map: Dict[str, int] = {}

    for url, pdata in page_map.items():
        title = str(pdata.get("title") or "Untitled")
        schemas = pdata.get("schema_types") or []
        ptype = classify_page_type(url, title, schemas)
        cluster = assign_topic_cluster(url, ptype)
        clusters_map[cluster] = clusters_map.get(cluster, 0) + 1

        in_deg = len(incoming_edges.get(url, []))
        out_deg = len(outgoing_edges.get(url, []))
        click_depth = depths.get(url, 999)
        if click_depth == 999:
            click_depth = 4  # Unconnected / Orphan

        equity = page_ranks.get(url, 10.0)

        # Health status evaluation
        if in_deg == 0 and url != homepage_url:
            status = "orphan"
            orphan_count += 1
        elif click_depth >= 4:
            status = "deep"
            deep_count += 1
        elif in_deg <= 2 and url != homepage_url:
            status = "weak"
            weak_count += 1
        else:
            status = "healthy"

        has_broken_out = any(e.get("is_broken") for e in outgoing_edges.get(url, []))

        nodes_list.append({
            "id": url,
            "url": url,
            "title": title,
            "page_type": ptype,
            "topic_cluster": cluster,
            "click_depth": click_depth,
            "in_degree": in_deg,
            "out_degree": out_deg,
            "equity_score": equity,
            "status": status,
            "has_broken_outlinks": has_broken_out,
            "word_count": int(pdata.get("word_count") or 450),
            "http_status": int(pdata.get("status_code") or 200),
        })

    # 6. Generate Intra-Cluster Link Suggestions
    suggested_links: List[Dict[str, Any]] = []
    for node in nodes_list:
        if node["status"] in ("orphan", "weak"):
            # Find a healthy sibling node in the same topic cluster or category
            cluster = node["topic_cluster"]
            candidates = [
                n for n in nodes_list
                if n["topic_cluster"] == cluster and n["id"] != node["id"] and n["equity_score"] >= 30.0
            ]
            if not candidates:
                candidates = [n for n in nodes_list if n["page_type"] == "homepage"]

            if candidates:
                best_source = max(candidates, key=lambda c: c["equity_score"])
                suggested_links.append({
                    "source_url": best_source["url"],
                    "target_url": node["url"],
                    "source_title": best_source["title"],
                    "target_title": node["title"],
                    "recommended_anchor": node["title"][:40] if node["title"] != "Untitled" else "Explore Feature",
                    "reason": f"Resolve {node['status']} status: link from high-equity cluster sibling ({best_source['equity_score']}% equity).",
                    "equity_gain_est": "HIGH" if node["status"] == "orphan" else "MEDIUM",
                })

    # Summary metrics
    total_pages = len(nodes_list)
    total_links = len(edges_list)
    avg_inlinks = round(total_links / max(total_pages, 1), 1)

    clusters_list = [
        {"cluster_id": k.lower().replace(" ", "_"), "name": k, "node_count": v}
        for k, v in clusters_map.items()
    ]

    return {
        "domain": clean_domain,
        "homepage_url": homepage_url,
        "nodes": nodes_list,
        "edges": edges_list,
        "clusters": clusters_list,
        "suggested_links": suggested_links[:25],
        "broken_links": broken_links,
        "summary": {
            "total_pages": total_pages,
            "total_internal_links": total_links,
            "orphan_count": orphan_count,
            "deep_count": deep_count,
            "weak_count": weak_count,
            "broken_count": len(broken_links),
            "max_click_depth": max((n["click_depth"] for n in nodes_list if n["click_depth"] < 900), default=0),
            "avg_inlinks_per_page": avg_inlinks,
        }
    }

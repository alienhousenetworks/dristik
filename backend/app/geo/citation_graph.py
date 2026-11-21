"""Phase 7 — Citation Intelligence & Multi-Entity Source Graph Engine.

Builds a canonical graph connecting:
Brands, Products, Prompts, AI Platforms, Responses, Cited URLs, Domains,
Publishers, Claims, and Competitors.

Preserves distinct attributes (citation frequency, relevance, independence,
factual support, freshness) without equating citation count with authority,
and detects ethical, evidence-backed citation opportunities.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.geo.citation_gap import classify_authority_domain
from app.geo.models import (
    GEOAuditScope,
    GEOCitation,
    GEODataQualityState,
    GEOExternalSource,
    GEOMention,
    GEOResponse,
    GEOSourceOwnership,
    GEOTestPrompt,
)

CATEGORY_LABEL_MAP = {
    "peer_review": "product_review",
    "tech_media": "editorial",
    "community_discussion": "community",
    "official_standard": "research",
    "vendor_self_hosted": "profile",
    "general_web": "editorial",
}


def build_citation_source_graph(
    *,
    scope: GEOAuditScope,
    prompts: List[GEOTestPrompt],
    responses: List[GEOResponse],
    mentions: List[GEOMention],
    citations: List[GEOCitation],
) -> Tuple[Dict[str, Any], List[GEOExternalSource]]:
    """Construct the canonical Citation Graph and independent external source opportunity records."""
    prompt_map = {p.prompt_id: p for p in prompts}
    resp_map = {r.response_id: r for r in responses}
    target_brand = scope.brand_name
    competitors = list(scope.competitors or [])

    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    def _add_node(nid: str, ntype: str, label: str, meta: Optional[Dict[str, Any]] = None) -> None:
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, "label": label, "metadata": meta or {}}

    brand_node = f"brand:{target_brand.lower()}"
    _add_node(brand_node, "brand", target_brand, {"domain": scope.domain})
    for prod in (scope.products or []) + (scope.services or []):
        pid = f"product:{prod.lower()}"
        _add_node(pid, "product", prod)
        edges.append({"source": brand_node, "target": pid, "relation": "OFFERS"})

    domain_stats: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "urls": set(),
            "platforms": set(),
            "prompts": set(),
            "competitors": set(),
            "claims": [],
            "count": 0,
            "ownership": GEOSourceOwnership.UNKNOWN.value,
            "category": "editorial",
            "brand_present": False,
        }
    )

    ownership_counts: Dict[str, int] = defaultdict(int)
    platform_citation_counts: Dict[str, int] = defaultdict(int)

    for cit in citations:
        auth_cat = classify_authority_domain(cit.cited_url, scope.domain, competitors)
        cit.source_category = CATEGORY_LABEL_MAP.get(auth_cat.value, "editorial")
        ownership_counts[cit.source_ownership.value] += 1
        platform_citation_counts[cit.platform_id] += 1

        p_obj = prompt_map.get(cit.prompt_id)
        r_obj = resp_map.get(cit.response_id)

        p_node = f"prompt:{cit.prompt_id}"
        plat_node = f"platform:{cit.platform_id}"
        resp_node = f"response:{cit.response_id}"
        dom_node = f"domain:{cit.domain}"
        url_node = f"url:{cit.cited_url}"

        _add_node(p_node, "prompt", (p_obj.question[:80] if p_obj else cit.prompt_id), {"is_branded": p_obj.is_branded if p_obj else False})
        _add_node(plat_node, "platform", cit.platform_id)
        _add_node(resp_node, "response", cit.response_id, {"brand_mentioned": r_obj.brand_mentioned if r_obj else False})
        _add_node(dom_node, "domain", cit.domain, {"ownership": cit.source_ownership.value, "category": cit.source_category})
        _add_node(url_node, "url", cit.cited_url, {"domain": cit.domain, "ownership": cit.source_ownership.value})

        edges.append({"source": p_node, "target": resp_node, "relation": "PRODUCED"})
        edges.append({"source": plat_node, "target": resp_node, "relation": "GENERATED"})
        edges.append({"source": resp_node, "target": url_node, "relation": "CITED"})
        edges.append({"source": url_node, "target": dom_node, "relation": "HOSTED_ON"})
        if cit.source_ownership == GEOSourceOwnership.OWNED:
            edges.append({"source": dom_node, "target": brand_node, "relation": "OWNED_BY"})
        if cit.associated_claim:
            claim_node = f"claim:{cit.citation_id}"
            _add_node(claim_node, "claim", cit.associated_claim[:120])
            edges.append({"source": url_node, "target": claim_node, "relation": "ASSOCIATED_CLAIM"})

        st = domain_stats[cit.domain]
        st["urls"].add(cit.cited_url)
        st["platforms"].add(cit.platform_id)
        st["prompts"].add(cit.prompt_id)
        st["count"] += 1
        st["ownership"] = cit.source_ownership.value
        st["category"] = cit.source_category
        if cit.associated_claim:
            st["claims"].append(cit.associated_claim)
        if cit.source_ownership == GEOSourceOwnership.OWNED or (r_obj and r_obj.brand_mentioned):
            st["brand_present"] = True
        for comp in cit.competitors_associated:
            st["competitors"].add(comp)
            comp_node = f"competitor:{comp.lower()}"
            _add_node(comp_node, "competitor", comp)
            edges.append({"source": dom_node, "target": comp_node, "relation": "MENTIONS_COMPETITOR"})

    # Also link competitor mentions in responses to cited independent domains (competitor citation gap)
    comp_by_resp: Dict[str, List[str]] = defaultdict(list)
    for m in mentions:
        if m.entity_kind == "competitor":
            comp_by_resp[m.response_id].append(m.entity_name)
    for cit in citations:
        if cit.source_ownership == GEOSourceOwnership.INDEPENDENT:
            for comp in comp_by_resp.get(cit.response_id, []):
                domain_stats[cit.domain]["competitors"].add(comp)

    # Build external source & opportunity records (excluding owned target domain)
    external_sources: List[GEOExternalSource] = []
    opportunities: List[Dict[str, Any]] = []
    for dom, st in sorted(domain_stats.items(), key=lambda kv: kv[1]["count"], reverse=True):
        if st["ownership"] == GEOSourceOwnership.OWNED.value:
            continue
        is_independent = st["ownership"] in (GEOSourceOwnership.INDEPENDENT.value, GEOSourceOwnership.EARNED.value)
        cites_comps = bool(st["competitors"])
        sample_url = sorted(st["urls"])[0] if st["urls"] else f"https://{dom}"
        opportunity_reason = (
            f"Cited {st['count']}x across {', '.join(sorted(st['platforms']))} in category responses"
            + (f" featuring competitors ({', '.join(sorted(st['competitors']))}) without verified brand representation." if cites_comps and not st["brand_present"] else ".")
        )
        src = GEOExternalSource(
            tenant_id=scope.tenant_id,
            audit_id=scope.audit_id,
            domain=dom,
            url=sample_url,
            publisher=dom.split(".")[0].capitalize(),
            title=f"Observed AI Citation Source: {dom}",
            subject=", ".join(sorted({prompt_map[pid].topic for pid in st["prompts"] if pid in prompt_map}))[:120],
            source_category=st["category"],
            is_relevant=True,
            is_independent=is_independent,
            publisher_identifiable=True,
            accurately_describes_brand=None,
            discusses_products=bool(st["brand_present"]),
            supports_claims=st["claims"][:3],
            cited_in_ai_responses=True,
            citation_count=st["count"],
            cites_competitors=cites_comps,
            competitors_present=sorted(st["competitors"]),
            brand_present=st["brand_present"],
            evidence_of_relevance=opportunity_reason,
            potential_contribution=(
                "Provide verifiable product documentation, original benchmarks, or legitimate editorial/profile factual corrections."
                if is_independent else "Analyze competitor documentation structure and publish superior first-party evidence."
            ),
            outreach_strategy=(
                "Editorial pitching, verified customer review solicitation (compliant with platform rules), or factual profile update."
                if is_independent else "Publish direct factual comparison & technical documentation on owned domain."
            ),
            restrictions_and_risks="Never purchase deceptive mentions, astroturf reviews, or manipulate independent editorial sources.",
            opportunity_status="prioritized" if (is_independent and cites_comps and not st["brand_present"]) else "identified",
            data_quality_state=GEODataQualityState.OBSERVED,
            source_refs=sorted(st["prompts"]),
        )
        external_sources.append(src)
        if is_independent and (cites_comps or not st["brand_present"]):
            opportunities.append({
                "source_id": src.source_id,
                "domain": dom,
                "url": sample_url,
                "category": st["category"],
                "citation_count": st["count"],
                "platforms": sorted(st["platforms"]),
                "competitors_present": sorted(st["competitors"]),
                "brand_present": st["brand_present"],
                "why_it_matters": opportunity_reason,
                "recommended_action": src.potential_contribution,
            })

    total_cites = len(citations)
    owned_count = ownership_counts.get(GEOSourceOwnership.OWNED.value, 0)
    indep_count = ownership_counts.get(GEOSourceOwnership.INDEPENDENT.value, 0) + ownership_counts.get(GEOSourceOwnership.EARNED.value, 0)
    comp_count = ownership_counts.get(GEOSourceOwnership.COMPETITOR.value, 0)

    graph = {
        "status": GEODataQualityState.OBSERVED.value if total_cites > 0 else GEODataQualityState.NOT_OBSERVED.value,
        "summary": {
            "total_citations": total_cites,
            "unique_domains": len(domain_stats),
            "owned_citations": owned_count,
            "independent_citations": indep_count,
            "competitor_citations": comp_count,
            "owned_share_pct": round((owned_count / total_cites) * 100.0, 1) if total_cites else None,
            "independent_share_pct": round((indep_count / total_cites) * 100.0, 1) if total_cites else None,
            "platform_distribution": dict(platform_citation_counts),
            "ownership_distribution": dict(ownership_counts),
        },
        "nodes": list(nodes.values()),
        "edges": edges,
        "top_domains": [
            {
                "domain": dom,
                "citation_count": st["count"],
                "ownership": st["ownership"],
                "category": st["category"],
                "platforms": sorted(st["platforms"]),
                "competitors_present": sorted(st["competitors"]),
                "brand_present": st["brand_present"],
                "sample_urls": sorted(st["urls"])[:3],
            }
            for dom, st in sorted(domain_stats.items(), key=lambda kv: kv[1]["count"], reverse=True)[:25]
        ],
        "opportunities": opportunities[:25],
        "methodology_note": (
            "Citation frequency, source independence, relevance, claim support, and freshness are tracked separately; "
            "high citation frequency alone does not establish authority."
        ),
    }
    return graph, external_sources

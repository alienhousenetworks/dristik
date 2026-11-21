"""Phase 8 — Brand Entity Knowledge Profile & Consistency Engine.

Combines Dristik's existing `entity_graph.py` and `entity_consistency.py`
analyzers with a persistent, user-approvable Brand Knowledge Profile (`GEOEntity`).

Strict protection guardrail:
AI-generated statements are NEVER automatically promoted into official brand
facts and NEVER overwrite user-confirmed `GEOEntity` records. Discrepancies
between official pages, external profiles, and AI responses are logged as
evidence-backed conflicts.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.domain.models import PageEvidence
from app.geo.entity_consistency import entity_consistency_analyzer
from app.geo.entity_graph import evaluate_entity_graph
from app.geo.models import (
    GEOAuditScope,
    GEODataQualityState,
    GEOEntity,
    GEOEntityFactStatus,
    GEOResponse,
)


def _extract_same_as_links(html: str) -> List[str]:
    socials = []
    for host in ("linkedin.com", "x.com", "twitter.com", "github.com", "youtube.com", "instagram.com", "facebook.com", "wikidata.org", "wikipedia.org"):
        for m in re.finditer(rf'href=["\'](https?://(?:www\.)?{re.escape(host)}/[^"\']+)["\']', html or "", re.I):
            u = m.group(1).strip()
            if u not in socials:
                socials.append(u)
    return socials


def build_brand_knowledge_profile(
    *,
    scope: GEOAuditScope,
    audit_id: str,
    pages: List[PageEvidence],
    raw_html_map: Optional[Dict[str, str]] = None,
    existing_approved: Optional[List[GEOEntity]] = None,
    ai_responses: Optional[List[GEOResponse]] = None,
) -> Tuple[List[GEOEntity], Dict[str, Any]]:
    """Build or refresh canonical GEOEntity records while strictly preserving approved facts."""
    html_map = raw_html_map or {}
    approved_by_key: Dict[Tuple[str, str], GEOEntity] = {}
    for ent in existing_approved or []:
        if ent.fact_status == GEOEntityFactStatus.CONFIRMED and ent.locked_from_ai_overwrite:
            approved_by_key[(ent.entity_type.lower(), ent.attribute.lower())] = ent

    # Reuse Dristik's existing deep entity analyzers
    eg_report, _eg_findings, eg_contradictions = evaluate_entity_graph(pages, brand_name=scope.brand_name)
    consistency_res = entity_consistency_analyzer.analyze(pages, website_url=scope.website_url)

    first_html = next(iter(html_map.values()), "")
    socials = _extract_same_as_links(first_html)
    for p in pages:
        for url in socials:
            pass
    schema_types = sorted({t for p in pages for t in (p.schema_types or []) if t})
    descriptions = [
        (p.url, (p.meta_description or "").strip())
        for p in pages
        if getattr(p, "meta_description", None) and (p.meta_description or "").strip()
    ]
    primary_desc = descriptions[0][1] if descriptions else ""

    candidate_facts: List[Tuple[str, str, str, Any, str, Optional[str], float, GEOEntityFactStatus]] = [
        ("brand", scope.brand_name, "official_name", scope.brand_name, "audit_scope_and_crawl", scope.website_url, 0.98, GEOEntityFactStatus.CONFIRMED),
        ("brand", scope.brand_name, "official_website", scope.website_url, "website_crawl", scope.website_url, 1.0, GEOEntityFactStatus.CONFIRMED),
        ("brand", scope.brand_name, "alternate_names", list(scope.brand_aliases or []), "audit_scope", scope.website_url, 0.90 if scope.brand_aliases else 0.50, GEOEntityFactStatus.CONFIRMED if scope.brand_aliases else GEOEntityFactStatus.UNKNOWN),
        ("organization", scope.brand_name, "industry_classification", scope.industry or "Unspecified", "audit_scope", scope.website_url, 0.90 if scope.industry else 0.40, GEOEntityFactStatus.CONFIRMED if scope.industry else GEOEntityFactStatus.UNKNOWN),
        ("organization", scope.brand_name, "organization_description", primary_desc or "Missing canonical meta/about description", "website_crawl", descriptions[0][0] if descriptions else scope.website_url, 0.85 if primary_desc else 0.30, GEOEntityFactStatus.CONFIRMED if primary_desc else GEOEntityFactStatus.UNKNOWN),
        ("organization", scope.brand_name, "markets_and_locations", list(scope.markets or []), "audit_scope", scope.website_url, 0.90, GEOEntityFactStatus.CONFIRMED),
        ("organization", scope.brand_name, "languages", list(scope.languages or []), "audit_scope", scope.website_url, 0.90, GEOEntityFactStatus.CONFIRMED),
        ("social_profile", scope.brand_name, "official_profiles", socials, "website_crawl", scope.website_url, 0.92 if socials else 0.40, GEOEntityFactStatus.CONFIRMED if socials else GEOEntityFactStatus.UNKNOWN),
        ("organization", scope.brand_name, "schema_types_observed", schema_types, "schema_jsonld", scope.website_url, 0.95 if schema_types else 0.40, GEOEntityFactStatus.CONFIRMED if schema_types else GEOEntityFactStatus.UNKNOWN),
    ]

    for prod in (scope.products or []):
        candidate_facts.append(("product", prod, "product_name", prod, "audit_scope", scope.website_url, 0.95, GEOEntityFactStatus.CONFIRMED))
    for svc in (scope.services or []):
        candidate_facts.append(("service", svc, "service_name", svc, "audit_scope", scope.website_url, 0.95, GEOEntityFactStatus.CONFIRMED))

    entities: List[GEOEntity] = []
    for etype, ename, attr, val, src, src_url, conf, fstatus in candidate_facts:
        key = (etype.lower(), attr.lower())
        if key in approved_by_key:
            # Preserve user-approved official fact without overwriting
            kept = approved_by_key[key].model_copy(update={"audit_id": audit_id})
            entities.append(kept)
            continue
        entities.append(
            GEOEntity(
                tenant_id=scope.tenant_id,
                audit_id=audit_id,
                entity_type=etype,
                entity_name=ename,
                attribute=attr,
                value=val,
                source=src,
                source_url=src_url,
                source_ownership="owned",
                confidence=conf,
                last_verified=datetime.now(timezone.utc).isoformat() if fstatus == GEOEntityFactStatus.CONFIRMED else None,
                fact_status=fstatus,
                locked_from_ai_overwrite=True,
                data_quality_state=GEODataQualityState.OBSERVED if pages else GEODataQualityState.PARTIAL,
                source_refs=[src_url] if src_url else [],
            )
        )

    # Also retain any extra user-approved custom facts (e.g. founding year, headquarters, pricing policy)
    emitted_keys = {(e.entity_type.lower(), e.attribute.lower()) for e in entities}
    for key, ent in approved_by_key.items():
        if key not in emitted_keys:
            entities.append(ent.model_copy(update={"audit_id": audit_id}))

    # Collect discrepancies from on-page entity graph, consistency analyzer, and AI responses
    inconsistencies: List[Dict[str, Any]] = []
    for c in eg_contradictions or []:
        inconsistencies.append({
            "source": "entity_graph",
            "title": getattr(c, "title", None) or getattr(c, "contradiction_type", "Entity conflict"),
            "detail": getattr(c, "description", None) or str(c),
            "severity": "high",
        })
    for d in getattr(consistency_res, "discrepancies", []) or []:
        inconsistencies.append({
            "source": "entity_consistency",
            "title": getattr(d, "field", "Inconsistent entity attribute"),
            "detail": getattr(d, "explanation", str(d)),
            "severity": str(getattr(d, "severity", "medium")).lower(),
        })

    # Attach AI response observations as separate non-overwriting records when inaccurate claims exist
    ai_conflicts: List[Dict[str, Any]] = []
    for resp in ai_responses or []:
        if resp.inaccurate_claims_count > 0:
            ai_conflicts.append({
                "response_id": resp.response_id,
                "platform_id": resp.platform_id,
                "inaccurate_claims_count": resp.inaccurate_claims_count,
                "note": "AI-generated statement conflicted with confirmed brand facts; official knowledge profile was NOT overwritten.",
            })

    # Entity consistency score derived from real crawl/entity_graph/consistency results
    eg_score = getattr(eg_report, "score", None)
    cons_score = getattr(consistency_res, "consistency_score", None)
    numeric_parts = [float(x) for x in (eg_score, cons_score) if isinstance(x, (int, float))]
    consistency_score = round(sum(numeric_parts) / len(numeric_parts), 1) if numeric_parts else None
    if consistency_score is not None and inconsistencies:
        consistency_score = max(15.0, round(consistency_score - min(30.0, len(inconsistencies) * 6.0), 1))

    summary = {
        "brand_name": scope.brand_name,
        "total_facts": len(entities),
        "confirmed_facts": sum(1 for e in entities if e.fact_status == GEOEntityFactStatus.CONFIRMED),
        "conflicting_facts": len(inconsistencies) + len(ai_conflicts),
        "consistency_score": consistency_score,
        "schema_types": schema_types,
        "inconsistencies": inconsistencies,
        "ai_conflicts": ai_conflicts,
        "entity_graph_summary": getattr(eg_report, "summary", ""),
        "relationships": [
            {"from": scope.brand_name, "relation": "OPERATES", "to": scope.domain},
            *[{"from": scope.brand_name, "relation": "OFFERS_PRODUCT", "to": p} for p in (scope.products or [])],
            *[{"from": scope.brand_name, "relation": "OFFERS_SERVICE", "to": s} for s in (scope.services or [])],
            *[{"from": scope.brand_name, "relation": "HAS_PROFILE", "to": u} for u in socials[:6]],
        ],
    }
    return entities, summary


def approve_brand_fact(
    entity: GEOEntity,
    *,
    new_value: Any,
    approved_by: str,
    source: str = "authorized_brand_owner",
) -> GEOEntity:
    """Explicit human approval of an official brand fact, locking it from AI overwrite."""
    now = datetime.now(timezone.utc).isoformat()
    entity.value = new_value
    entity.source = source
    entity.source_ownership = "owned"
    entity.fact_status = GEOEntityFactStatus.CONFIRMED
    entity.approved_by = approved_by
    entity.approved_at = now
    entity.last_verified = now
    entity.confidence = 1.0
    entity.locked_from_ai_overwrite = True
    entity.data_quality_state = GEODataQualityState.VERIFIED
    entity.updated_at = now
    return entity

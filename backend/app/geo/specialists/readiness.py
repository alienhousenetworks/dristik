"""Departments A, D, E, and I — Brand/Entity, Content Quality, Technical Retrieval, and Quality/Strategy."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from app.geo.citation_passages import passage_analyzer
from app.geo.claim_extractor import claim_extractor
from app.geo.intelligence.crawler_accessibility import CrawlerAccessibilityEngine
from app.geo.models import (
    GEOAgentOutput,
    GEODataQualityState,
    GEOFinding,
    GEOFindingSeverity,
    GEOPageReadiness,
    GEORecommendation,
)
from app.geo.specialists import GEOAuditContext

PAGE_TYPE_PATTERNS = (
    ("pricing", ("/pricing", "/plans", "/cost")),
    ("about", ("/about", "/company", "/team")),
    ("comparison", ("/vs", "/compare", "/comparison", "/alternative")),
    ("case_study", ("/case-stud", "/customer", "/stories")),
    ("docs", ("/docs", "/documentation", "/api", "/guide", "/help")),
    ("faq", ("/faq", "/questions")),
    ("contact", ("/contact", "/support", "/demo")),
    ("legal", ("/privacy", "/terms", "/legal", "/security", "/compliance")),
    ("product", ("/product", "/solution", "/feature", "/platform")),
    ("service", ("/service", "/consulting", "/agency")),
    ("category", ("/category", "/collection", "/solutions")),
    ("editorial", ("/blog", "/article", "/insights", "/news", "/resources")),
)


def classify_page_type(url: str, index: int) -> str:
    low = (url or "").lower().rstrip("/")
    if index == 0 and low.count("/") <= 2:
        return "homepage"
    for ptype, needles in PAGE_TYPE_PATTERNS:
        if any(n in low for n in needles):
            return ptype
    return "homepage" if low.count("/") <= 2 else "general"


def run_department_a(ctx: GEOAuditContext) -> Tuple[GEOAgentOutput, Dict[str, Any]]:
    """Department A: Brand & Entity Intelligence."""
    findings: List[GEOFinding] = []
    ev_ids = list(ctx.snapshot_ids[:3]) + [e.entity_id for e in ctx.entities[:5]]
    summary = ctx.entity_summary or {}
    inconsistencies = summary.get("inconsistencies", [])
    ai_conflicts = summary.get("ai_conflicts", [])
    schema_types = summary.get("schema_types", [])

    if not ctx.pages:
        return (
            GEOAgentOutput(
                agent_id="geo_department_a_brand_entity",
                department="A",
                status="partial",
                audit_id=ctx.audit_id,
                findings=[],
                evidence_ids=ev_ids,
                confidence=0.40,
                limitations=["No website pages were crawled; entity profile reflects scope configuration only."],
                execution_metadata={"agents_executed": 6, "entities_tracked": len(ctx.entities)},
            ),
            summary,
        )

    if "Organization" not in schema_types and "Corporation" not in schema_types:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="entity_consistency",
                department="A",
                agent_id="geo_brand_entity",
                title="Missing Organization entity schema on primary brand pages",
                description=f"Crawled pages for {ctx.scope.brand_name} do not declare a Schema.org Organization entity with canonical name, URL, and sameAs references.",
                root_cause="Structured entity markup is absent from site templates.",
                root_cause_group="entity_schema_gap",
                affected_entities=[ctx.scope.brand_name],
                affected_urls=[ctx.pages[0].url],
                evidence_ids=ev_ids[:3],
                severity=GEOFindingSeverity.MEDIUM,
                confidence=0.92,
                business_impact="Increases entity ambiguity when retrieval pipelines disambiguate brand facts (schema supports technical readiness, not guaranteed AI inclusion).",
                recommendation="Publish verified Organization JSON-LD with official name, URL, description, and confirmed sameAs profile URLs.",
                acceptance_criteria=[
                    "Homepage emits valid Organization JSON-LD matching approved Brand Knowledge Profile.",
                    "sameAs links point only to active, official brand profiles.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    if inconsistencies:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="entity_consistency",
                department="A",
                agent_id="geo_entity_consistency",
                title=f"Inconsistent brand/entity descriptions across {len(inconsistencies)} check(s)",
                description="; ".join(str(i.get("detail", i.get("title", "")))[:140] for i in inconsistencies[:3]),
                root_cause="Divergent brand naming, descriptions, or attributes across site pages and structured markup.",
                root_cause_group="entity_inconsistency",
                affected_entities=[ctx.scope.brand_name],
                affected_urls=[p.url for p in ctx.pages[:4]],
                evidence_ids=ev_ids[:4],
                severity=GEOFindingSeverity.HIGH,
                confidence=0.88,
                business_impact="Conflicting official descriptions undermine factual consistency across search and generative systems.",
                recommendation="Reconcile official name, product names, and descriptions against the approved Brand Knowledge Profile.",
                acceptance_criteria=[
                    "All core pages match the approved official brand name and product descriptions.",
                    "Zero unresolved entity conflicts on re-crawl.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    if ai_conflicts:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="entity_consistency",
                department="A",
                agent_id="geo_organization_knowledge",
                title=f"AI responses misstated verified brand facts in {len(ai_conflicts)} captured answer(s)",
                description="Live AI answers contradicted confirmed facts in the Brand Knowledge Profile (official profile was protected and not overwritten).",
                root_cause="Missing or ambiguous authoritative public facts on official pages and independent profiles.",
                root_cause_group="brand_misinformation",
                affected_entities=[ctx.scope.brand_name],
                affected_platforms=sorted({c["platform_id"] for c in ai_conflicts}),
                evidence_ids=[c["response_id"] for c in ai_conflicts],
                severity=GEOFindingSeverity.CRITICAL,
                confidence=0.90,
                business_impact="Material brand misinformation can mislead buyers evaluating pricing, status, or capabilities.",
                recommendation="Publish an explicit, factual About / Facts / Pricing reference page and update verifiable third-party profiles.",
                acceptance_criteria=[
                    "Official facts page publishes unambiguous statements for every disputed attribute.",
                    "Follow-up retest documents whether AI representation improved.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    return (
        GEOAgentOutput(
            agent_id="geo_department_a_brand_entity",
            department="A",
            status="completed",
            audit_id=ctx.audit_id,
            findings=findings,
            evidence_ids=ev_ids,
            confidence=0.88,
            limitations=["External knowledge graph verification requires live external search/API access when not observed in citations."],
            execution_metadata={"agents_executed": 6, "entities_count": len(ctx.entities), "inconsistencies": len(inconsistencies)},
        ),
        summary,
    )


def run_department_d(ctx: GEOAuditContext) -> Tuple[GEOAgentOutput, Dict[str, Any], List[GEOPageReadiness]]:
    """Department D: Content & Information Quality (reuses citation_passages + claim_extractor)."""
    if not ctx.pages:
        return (
            GEOAgentOutput(
                agent_id="geo_department_d_content_quality",
                department="D",
                status="not_tested",
                audit_id=ctx.audit_id,
                limitations=["No crawled pages available for content readiness evaluation."],
                execution_metadata={"agents_executed": 8, "pages_analyzed": 0},
            ),
            {"status": GEODataQualityState.NOT_TESTED.value, "content_quality_score": None, "pages_analyzed": 0},
            [],
        )

    passage_res = passage_analyzer.analyze(ctx.pages, brand_name=ctx.scope.brand_name)
    claims_res = claim_extractor.extract_claims(ctx.pages, brand_name=ctx.scope.brand_name)

    page_records: List[GEOPageReadiness] = []
    weak_pages: List[str] = []
    missing_pricing = True
    missing_comparison = True
    missing_faq = True
    missing_freshness = True

    brand_low = ctx.scope.brand_name.lower()
    for idx, p in enumerate(ctx.pages):
        body = (p.body_text or "").strip()
        low = body.lower()
        words = len(body.split())
        ptype = classify_page_type(p.url, idx)
        has_def = bool(re.search(r"\b(?:is a|is an|provides|automates|helps|offers|designed for)\b", low))
        has_pricing = bool(re.search(r"(?:\$|€|£|₹|\bUSD\b|\bEUR\b)\s*\d+|\bpricing\b|\bplans?\b", low))
        has_table = "<table" in (ctx.raw_html_map.get(p.url, "").lower()) or ("|" in body and body.count("|") >= 4)
        has_comp = ptype == "comparison" or any(k in low for k in ("compared to", "comparison", "versus", " vs "))
        has_faq = ptype == "faq" or "frequently asked" in low or "FAQPage" in (p.schema_types or []) or body.count("?") >= 3
        has_author = bool(re.search(r"\b(?:written by|reviewed by|author|editorial team)\b", low))
        has_date = bool(re.search(r"\b(?:updated|published|last reviewed)\s*:?\s*(?:202\d|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", low))
        has_evidence = bool(re.search(r"\b(?:\d+%|\d+\s*(?:ms|sec|hours|days|customers|users)|study|benchmark|source|iso\s*27001|soc\s*2)\b", low))
        has_fluff = len(re.findall(r"\b(?:best-in-class|revolutionary|world-class|unparalleled|game-changing|synergy)\b", low))

        if has_pricing:
            missing_pricing = False
        if has_comp:
            missing_comparison = False
        if has_faq:
            missing_faq = False
        if has_date:
            missing_freshness = False

        clarity = round(min(100.0, (45.0 if has_def else 20.0) + (25.0 if brand_low in low else 0.0) + (20.0 if words >= 180 else 10.0) - min(20.0, has_fluff * 5.0)), 1)
        completeness = round(min(100.0, (30.0 if words >= 300 else 15.0) + (20.0 if has_faq else 0.0) + (20.0 if has_pricing else 0.0) + (15.0 if has_table else 0.0) + (15.0 if has_evidence else 0.0)), 1)
        specificity = round(min(100.0, (45.0 if has_evidence else 20.0) + (25.0 if has_table else 0.0) + (20.0 if any(pr.lower() in low for pr in (ctx.scope.products or ctx.scope.services or [])) else 10.0)), 1)
        structure = round(min(100.0, (35.0 if (p.h1 or []) else 10.0) + (25.0 if (p.h2 or []) else 10.0) + (20.0 if has_table or has_faq else 10.0) + (20.0 if (p.meta_description or "").strip() else 0.0)), 1)
        extractability = round((clarity * 0.35 + structure * 0.35 + specificity * 0.30), 1)
        freshness = 85.0 if has_date else 40.0
        trust = round(min(100.0, (35.0 if has_author else 15.0) + (35.0 if has_evidence else 15.0) + (30.0 if (p.schema_types or []) else 10.0)), 1)
        overall = round((clarity + completeness + specificity + structure + extractability + freshness + trust) / 7.0, 1)

        issues: List[str] = []
        recs: List[str] = []
        missing_qs: List[str] = []
        if not has_def:
            issues.append("Missing clear factual definition of product/service.")
            recs.append("Add a factual 40–60 word opening definition stating what the product does, who it serves, and documented scope.")
            missing_qs.append(f"What does {ctx.scope.brand_name} do on {ptype}?")
        if not has_evidence:
            issues.append("Key claims lack supporting metrics, documentation, or verifiable evidence.")
            recs.append("Support capability claims with documented specifications, limitations, or verifiable customer proof.")
        if has_fluff >= 2:
            issues.append("Marketing superlatives dilute factual specificity.")
            recs.append("Replace vague superlatives with concrete feature/limitation statements.")
        if not has_date:
            issues.append("No visible last-updated or publication date.")
            recs.append("Display truthful last-updated dates on documentation, pricing, and editorial pages.")

        if overall < 55.0:
            weak_pages.append(p.url)

        page_records.append(
            GEOPageReadiness(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                url=p.url,
                page_type=ptype,
                http_status=getattr(p, "status_code", 200),
                title=p.title or "",
                main_topic=(p.h1[0] if getattr(p, "h1", None) else p.title or ptype)[:100],
                relevant_audience=ctx.scope.target_audience or "Evaluators and buyers",
                word_count=words,
                clarity_score=clarity,
                completeness_score=completeness,
                specificity_score=specificity,
                accuracy_score=trust,
                structure_score=structure,
                extractability_score=extractability,
                differentiation_score=specificity,
                freshness_score=freshness,
                trust_score=trust,
                consistency_score=ctx.entity_summary.get("consistency_score"),
                overall_readiness_score=overall,
                entity_coverage=[e for e in ([ctx.scope.brand_name] + list(ctx.scope.products or [])) if e and e.lower() in low],
                schema_types=list(p.schema_types or []),
                missing_questions=missing_qs,
                content_issues=issues,
                recommendations=recs,
                has_definitions=has_def,
                has_feature_table=has_table,
                has_comparison_table=has_comp,
                has_pricing_info=has_pricing,
                has_faq_section=has_faq,
                has_author_attribution=has_author,
                has_updated_date=has_date,
                extracted_text_preview=body[:400],
                data_quality_state=GEODataQualityState.OBSERVED,
                source_refs=[p.url],
            )
        )

    avg_score = round(sum(r.overall_readiness_score or 0.0 for r in page_records) / len(page_records), 1)
    ev_ids = list(ctx.snapshot_ids[:2]) + [r.page_id for r in page_records[:4]]
    findings: List[GEOFinding] = []

    if weak_pages:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="content_quality",
                department="D",
                agent_id="geo_content_extractability",
                title=f"{len(weak_pages)} core page(s) score below content extractability threshold (<55/100)",
                description=f"Evaluated {len(page_records)} crawled page(s); average content readiness is {avg_score}/100. Low clarity, missing factual specifications, or vague copy limits extractability.",
                root_cause="Pages rely on promotional copy rather than structured factual definitions, feature tables, and documented limitations.",
                root_cause_group="content_extractability_deficit",
                affected_entities=[ctx.scope.brand_name],
                affected_urls=weak_pages[:10],
                evidence_ids=ev_ids[:4],
                severity=GEOFindingSeverity.HIGH if len(weak_pages) >= max(1, len(page_records) // 2) else GEOFindingSeverity.MEDIUM,
                confidence=0.86,
                business_impact="Weak factual clarity reduces the likelihood that human readers and retrieval systems extract accurate product answers.",
                recommendation="Add verified factual definitions, feature/limitation tables, and evidence-backed answers derived strictly from approved brand facts.",
                acceptance_criteria=[
                    "All affected pages include clear factual definitions and documented capabilities.",
                    "Re-crawl content readiness score reaches >=70/100 without invented claims.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    missing_info_areas = []
    if missing_pricing:
        missing_info_areas.append("pricing / engagement model")
    if missing_comparison:
        missing_info_areas.append("factual comparison criteria")
    if missing_faq:
        missing_info_areas.append("customer Q&A / FAQ coverage")
    if missing_freshness:
        missing_info_areas.append("visible content update dates")

    if missing_info_areas:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="content_quality",
                department="D",
                agent_id="geo_answer_completeness",
                title=f"Missing high-value buyer information across crawled pages ({', '.join(missing_info_areas)})",
                description=f"None of the {len(page_records)} crawled pages explicitly cover: {', '.join(missing_info_areas)}.",
                root_cause="Incomplete buyer-research documentation on owned pages.",
                root_cause_group="topical_coverage_gap",
                affected_entities=[ctx.scope.brand_name],
                affected_urls=[p.url for p in ctx.pages[:5]],
                evidence_ids=ev_ids[:3],
                severity=GEOFindingSeverity.MEDIUM,
                confidence=0.85,
                business_impact="Unanswered buyer questions force generative engines to rely solely on third-party sites or omit details.",
                recommendation="Publish dedicated, verifiable sections covering pricing ranges/models, objective comparison criteria, FAQs, and update dates.",
                acceptance_criteria=[
                    "Each missing information area is published on an accessible owned URL.",
                    "Facts match the approved Brand Knowledge Profile.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    artifact = {
        "status": GEODataQualityState.OBSERVED.value,
        "content_quality_score": avg_score,
        "pages_analyzed": len(page_records),
        "weak_pages_count": len(weak_pages),
        "missing_information_matrix": {
            "pricing_documented": not missing_pricing,
            "comparison_documented": not missing_comparison,
            "faq_documented": not missing_faq,
            "freshness_dates_present": not missing_freshness,
        },
        "claims_extracted_count": len(getattr(claims_res, "claims", []) or []),
        "passages_analyzed_count": len(getattr(passage_res, "passages", []) or []),
    }
    return (
        GEOAgentOutput(
            agent_id="geo_department_d_content_quality",
            department="D",
            status="completed",
            audit_id=ctx.audit_id,
            findings=findings,
            evidence_ids=ev_ids,
            confidence=0.86,
            limitations=[
                "Content readiness evaluates crawled pages only and does not prove retrieval by any specific AI model."
            ],
            execution_metadata={"agents_executed": 8, "pages_analyzed": len(page_records)},
        ),
        artifact,
        page_records,
    )


def run_department_e(ctx: GEOAuditContext) -> Tuple[GEOAgentOutput, Dict[str, Any]]:
    """Department E: Website Retrieval & Technical Readiness (reuses CrawlerAccessibilityEngine)."""
    first_headers = next(iter(ctx.headers_map.values()), {}) if ctx.headers_map else {}
    low_word_pages = [p for p in ctx.pages if len((p.body_text or "").split()) < 40]
    js_wall = bool(ctx.pages) and len(low_word_pages) == len(ctx.pages)

    crawler_rep = CrawlerAccessibilityEngine.evaluate_crawler_access(
        robots_txt=ctx.robots_txt,
        headers=first_headers,
        is_client_rendered_only=js_wall,
    )
    blocked_search = [c.bot_name for c in crawler_rep.crawlers_evaluated if not c.is_allowed and c.purpose.value in ("SEARCH_RETRIEVAL", "GENERAL_WEB_INDEX")]
    blocked_training = [c.bot_name for c in crawler_rep.crawlers_evaluated if not c.is_allowed and c.purpose.value == "MODEL_TRAINING"]

    non_200 = [p.url for p in ctx.pages if getattr(p, "status_code", 200) and int(getattr(p, "status_code", 200)) >= 400]
    missing_canon = [p.url for p in ctx.pages if not getattr(p, "canonical_url", None)]
    has_schema = any(bool(p.schema_types) for p in ctx.pages)

    score = 100.0
    if blocked_search:
        score -= 35.0
    if js_wall:
        score -= 25.0
    if non_200:
        score -= min(20.0, len(non_200) * 10.0)
    if not has_schema:
        score -= 10.0
    if missing_canon and ctx.pages:
        score -= 5.0
    score = max(0.0, round(score, 1)) if ctx.pages or ctx.robots_txt else None

    ev_ids = list(ctx.snapshot_ids[:2]) + [p.url for p in ctx.pages[:3]]
    findings: List[GEOFinding] = []

    if blocked_search:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="technical_readiness",
                department="E",
                agent_id="geo_robots_policy",
                title=f"AI search retrieval crawler(s) blocked in robots.txt: {', '.join(blocked_search)}",
                description=f"robots.txt disallows {', '.join(blocked_search)}, which restricts search-grounded retrieval access (kept separate from model-training bots: {', '.join(blocked_training) or 'none blocked'}).",
                root_cause="Restrictive robots.txt Disallow rules apply to retrieval crawlers.",
                root_cause_group="crawler_access_blocked",
                affected_urls=[f"https://{ctx.scope.domain}/robots.txt"],
                evidence_ids=ev_ids[:2],
                severity=GEOFindingSeverity.HIGH,
                confidence=0.95,
                business_impact="Blocking retrieval crawlers prevents search-grounded AI systems from reading updated pages (allowing them establishes technical readiness, not guaranteed citation).",
                recommendation=f"Allow retrieval bots ({', '.join(blocked_search)}) in robots.txt while maintaining your chosen policy for training crawlers.",
                acceptance_criteria=[
                    f"robots.txt permits {', '.join(blocked_search)} on public brand/product paths.",
                    "Re-crawl confirms HTTP 200 access to target URLs.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    if js_wall:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="technical_readiness",
                department="E",
                agent_id="geo_rendering_parity",
                title="Critical content appears gated behind client-side JavaScript rendering",
                description="Crawled raw HTML contains fewer than 40 extractable words across audited pages.",
                root_cause="Primary copy is absent from initial server-rendered HTML.",
                root_cause_group="js_rendering_dependency",
                affected_urls=[p.url for p in low_word_pages[:5]],
                evidence_ids=ev_ids[:3],
                severity=GEOFindingSeverity.HIGH,
                confidence=0.84,
                business_impact="Lightweight fetchers that do not execute full JavaScript bundles may fail to extract key brand and product facts.",
                recommendation="Serve core product definitions, headings, pricing, and structured data in server-rendered HTML (SSR/SSG).",
                acceptance_criteria=[
                    "Raw HTML response includes full product headings and core copy without JS execution.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    artifact = {
        "status": GEODataQualityState.OBSERVED.value if score is not None else GEODataQualityState.NOT_TESTED.value,
        "technical_readiness_score": score,
        "search_retrieval_allowed": crawler_rep.search_retrieval_allowed,
        "user_fetch_allowed": crawler_rep.user_fetch_allowed,
        "model_training_allowed": crawler_rep.model_training_allowed,
        "blocked_search_bots": blocked_search,
        "blocked_training_bots": blocked_training,
        "js_rendering_wall_detected": js_wall,
        "http_error_urls": non_200,
        "crawlers_evaluated": [c.model_dump() for c in crawler_rep.crawlers_evaluated],
        "disclaimer": "Technical readiness verifies website accessibility and markup quality; it does not prove retrieval or ranking by any specific AI platform.",
    }
    return (
        GEOAgentOutput(
            agent_id="geo_department_e_technical_readiness",
            department="E",
            status="completed" if score is not None else "not_tested",
            audit_id=ctx.audit_id,
            findings=findings,
            evidence_ids=ev_ids,
            confidence=0.92 if score is not None else None,
            limitations=[artifact["disclaimer"]],
            execution_metadata={"agents_executed": 8, "pages_checked": len(ctx.pages)},
        ),
        artifact,
    )


def run_department_i_consolidate(
    ctx: GEOAuditContext,
    raw_findings: List[GEOFinding],
) -> Tuple[GEOAgentOutput, List[GEOFinding], List[GEORecommendation], List[Dict[str, Any]]]:
    """Department I: Validate, deduplicate findings, cluster root causes, and rank strategic recommendations."""
    sev_order = {
        GEOFindingSeverity.CRITICAL: 0,
        GEOFindingSeverity.HIGH: 1,
        GEOFindingSeverity.MEDIUM: 2,
        GEOFindingSeverity.LOW: 3,
        GEOFindingSeverity.INFORMATIONAL: 4,
    }
    dedup: Dict[str, GEOFinding] = {}
    for f in raw_findings:
        key = f"{f.category}:{f.root_cause_group or f.title.lower().strip()[:60]}"
        if key not in dedup:
            dedup[key] = f
        else:
            existing = dedup[key]
            existing.affected_urls = list(dict.fromkeys(existing.affected_urls + f.affected_urls))
            existing.affected_prompts = list(dict.fromkeys(existing.affected_prompts + f.affected_prompts))
            existing.affected_platforms = list(dict.fromkeys(existing.affected_platforms + f.affected_platforms))
            existing.evidence_ids = list(dict.fromkeys(existing.evidence_ids + f.evidence_ids))
            if sev_order[f.severity] < sev_order[existing.severity]:
                existing.severity = f.severity

    consolidated = sorted(dedup.values(), key=lambda x: (sev_order[x.severity], x.category, x.title))
    for idx, f in enumerate(consolidated, start=1):
        f.finding_id = f"GEO-{idx:03d}"

    # Group by root_cause_group
    groups_map: Dict[str, List[GEOFinding]] = {}
    for f in consolidated:
        grp = f.root_cause_group or f.category
        groups_map.setdefault(grp, []).append(f)

    root_cause_groups: List[Dict[str, Any]] = []
    recommendations: List[GEORecommendation] = []
    dept_owner_map = {
        "ai_visibility": "GEO & Brand Strategy",
        "citation_intelligence": "Content & Digital PR",
        "entity_consistency": "Brand & Engineering",
        "content_quality": "Content & Product Marketing",
        "technical_readiness": "Web Engineering",
        "external_reputation": "PR & Community",
        "competitive_intelligence": "Product Marketing & Strategy",
        "market_intent": "Localization & Growth",
    }
    sev_priority = {
        GEOFindingSeverity.CRITICAL: 95.0,
        GEOFindingSeverity.HIGH: 82.0,
        GEOFindingSeverity.MEDIUM: 65.0,
        GEOFindingSeverity.LOW: 42.0,
        GEOFindingSeverity.INFORMATIONAL: 25.0,
    }

    for grp, members in groups_map.items():
        top = members[0]
        root_cause_groups.append({
            "group_id": grp,
            "root_cause": top.root_cause or top.title,
            "finding_ids": [m.finding_id for m in members],
            "highest_severity": top.severity.value,
            "affected_categories": sorted({m.category for m in members}),
        })
        recommendations.append(
            GEORecommendation(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_ids=[m.finding_id for m in members],
                dimension=top.category,
                title=f"Resolve {grp.replace('_', ' ').title()}: {top.title}",
                rationale=top.business_impact or top.description,
                expected_impact="high" if top.severity in (GEOFindingSeverity.CRITICAL, GEOFindingSeverity.HIGH) else "medium",
                effort="low" if top.category in ("technical_readiness", "entity_consistency") else "medium",
                confidence=top.confidence,
                priority_score=sev_priority[top.severity],
                owner_department=dept_owner_map.get(top.category, "GEO Strategy"),
                action_steps=[m.recommendation for m in members if m.recommendation][:4],
                risks=["Improving readiness factors does not guarantee immediate AI response changes; validate via controlled retesting."],
                data_quality_state=top.data_quality_state,
                source_refs=top.evidence_ids[:5],
            )
        )

    recommendations.sort(key=lambda r: r.priority_score, reverse=True)
    out = GEOAgentOutput(
        agent_id="geo_department_i_strategy_qa",
        department="I",
        status="completed",
        audit_id=ctx.audit_id,
        findings=consolidated,
        evidence_ids=list({eid for f in consolidated for eid in f.evidence_ids})[:20],
        confidence=0.90,
        limitations=[],
        execution_metadata={
            "agents_executed": 8,
            "raw_findings_count": len(raw_findings),
            "consolidated_findings_count": len(consolidated),
            "root_cause_groups_count": len(root_cause_groups),
        },
    )
    return out, consolidated, recommendations, root_cause_groups

"""Departments B, C, F, G, and H — AI Visibility, Citations, Reputation, Competitive & Market/Intent."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from app.geo.models import (
    GEOAgentOutput,
    GEODataQualityState,
    GEOFinding,
    GEOFindingSeverity,
    GEOMentionType,
    GEOSourceOwnership,
)
from app.geo.response_analyzer import summarize_repeat_variation
from app.geo.specialists import GEOAuditContext


def run_department_b(ctx: GEOAuditContext) -> Tuple[GEOAgentOutput, Dict[str, Any]]:
    """Department B: AI Visibility Intelligence (strictly from observed live responses)."""
    ok_runs = [r for r in ctx.runs if r.status == GEODataQualityState.OBSERVED]
    resp_by_run = {r.run_id: r for r in ctx.responses}
    prompt_by_id = {p.prompt_id: p for p in ctx.prompts}

    if not ok_runs:
        artifact = {
            "status": GEODataQualityState.NOT_CONFIGURED.value,
            "tested_runs": 0,
            "branded": {"runs": 0, "mention_rate_pct": None, "recommendation_rate_pct": None, "citation_rate_pct": None},
            "non_branded": {"runs": 0, "mention_rate_pct": None, "recommendation_rate_pct": None, "citation_rate_pct": None},
            "repeat_summary": summarize_repeat_variation(ctx.runs, ctx.responses),
            "by_platform": {},
            "by_category": {},
            "absent_topics": [],
        }
        return (
            GEOAgentOutput(
                agent_id="geo_department_b_ai_visibility",
                department="B",
                status="not_tested",
                audit_id=ctx.audit_id,
                findings=[],
                evidence_ids=[],
                confidence=None,
                limitations=[
                    "No live AI provider executions succeeded. AI visibility is NOT_CONFIGURED / unmeasured, never zero."
                ],
                execution_metadata={"agents_executed": 8, "observed_runs": 0},
            ),
            artifact,
        )

    def _rates(subset_runs: List[Any]) -> Dict[str, Any]:
        n = len(subset_runs)
        if n == 0:
            return {"runs": 0, "mentions": 0, "recommendations": 0, "shortlists": 0, "citations": 0, "mention_rate_pct": None, "recommendation_rate_pct": None, "shortlist_rate_pct": None, "citation_rate_pct": None}
        m = sum(1 for r in subset_runs if resp_by_run.get(r.run_id) and resp_by_run[r.run_id].brand_mentioned)
        rec = sum(1 for r in subset_runs if resp_by_run.get(r.run_id) and resp_by_run[r.run_id].brand_recommended)
        sh = sum(1 for r in subset_runs if resp_by_run.get(r.run_id) and resp_by_run[r.run_id].is_shortlisted)
        cit = sum(1 for r in subset_runs if resp_by_run.get(r.run_id) and resp_by_run[r.run_id].brand_cited)
        return {
            "runs": n,
            "mentions": m,
            "recommendations": rec,
            "shortlists": sh,
            "citations": cit,
            "mention_rate_pct": round(m / n * 100.0, 1),
            "recommendation_rate_pct": round(rec / n * 100.0, 1),
            "shortlist_rate_pct": round(sh / n * 100.0, 1),
            "citation_rate_pct": round(cit / n * 100.0, 1),
        }

    branded_runs = [r for r in ok_runs if prompt_by_id.get(r.prompt_id) and prompt_by_id[r.prompt_id].is_branded]
    non_branded_runs = [r for r in ok_runs if prompt_by_id.get(r.prompt_id) and not prompt_by_id[r.prompt_id].is_branded]
    overall = _rates(ok_runs)
    branded = _rates(branded_runs)
    non_branded = _rates(non_branded_runs)

    by_platform: Dict[str, Any] = {}
    for pid in sorted({r.platform_id for r in ok_runs}):
        by_platform[pid] = _rates([r for r in ok_runs if r.platform_id == pid])

    by_category: Dict[str, Any] = {}
    absent_topics: List[str] = []
    for cat in sorted({prompt_by_id[r.prompt_id].category.value for r in ok_runs if r.prompt_id in prompt_by_id}):
        cat_runs = [r for r in ok_runs if r.prompt_id in prompt_by_id and prompt_by_id[r.prompt_id].category.value == cat]
        cr = _rates(cat_runs)
        by_category[cat] = cr
        if cr["mentions"] == 0:
            absent_topics.append(cat)

    findings: List[GEOFinding] = []
    ev_ids = [resp_by_run[r.run_id].response_id for r in ok_runs[:6] if r.run_id in resp_by_run]

    if non_branded["runs"] > 0 and (non_branded["mention_rate_pct"] or 0.0) < 35.0:
        missing_pids = [
            r.prompt_id for r in non_branded_runs
            if resp_by_run.get(r.run_id) and not resp_by_run[r.run_id].brand_mentioned
        ]
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="ai_visibility",
                department="B",
                agent_id="geo_ai_visibility",
                title=f"Low observed non-branded AI discovery visibility ({non_branded['mention_rate_pct']}% across {non_branded['runs']} run(s))",
                description=f"{ctx.scope.brand_name} was mentioned in {non_branded['mentions']}/{non_branded['runs']} non-branded discovery runs and recommended in {non_branded['recommendations']}/{non_branded['runs']} runs.",
                root_cause="Insufficient authoritative category coverage, product clarity, and independent third-party corroboration for non-branded queries.",
                root_cause_group="low_non_branded_visibility",
                affected_entities=[ctx.scope.brand_name],
                affected_prompts=list(dict.fromkeys(missing_pids))[:10],
                affected_platforms=sorted(by_platform.keys()),
                evidence_ids=ev_ids[:5],
                severity=GEOFindingSeverity.HIGH,
                confidence=0.90,
                business_impact="Prospective buyers asking unbranded category or recommendation prompts rarely encounter the brand in tested platforms.",
                recommendation="Strengthen non-branded category/use-case documentation, factual comparison content, and legitimate independent publication coverage.",
                acceptance_criteria=[
                    "Target content and external source updates are independently verified.",
                    "Matched non-branded prompt suite is re-run on identical platforms and testing modes.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    if overall["mentions"] > 0 and overall["recommendations"] == 0:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="ai_visibility",
                department="B",
                agent_id="geo_recommendation_analysis",
                title="Brand is mentioned in tested responses but not explicitly recommended",
                description=f"Observed {overall['mentions']} mention(s) across {overall['runs']} successful runs, but 0 explicit recommendations.",
                root_cause="Brand differentiation, ideal-customer fit, and verifiable customer proof are under-specified compared to recommended alternatives.",
                root_cause_group="mention_without_recommendation",
                affected_entities=[ctx.scope.brand_name],
                affected_platforms=sorted(by_platform.keys()),
                evidence_ids=ev_ids[:4],
                severity=GEOFindingSeverity.MEDIUM,
                confidence=0.85,
                business_impact="Awareness mentions without recommendation rationale convert poorly in shortlist evaluation prompts.",
                recommendation="Publish concrete differentiation criteria, documented use-case fit, and verifiable case studies.",
                acceptance_criteria=[
                    "Differentiation and use-case evidence blocks published on primary product pages.",
                    "Retest tracks recommendation inclusion separately from simple mentions.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    artifact = {
        "status": GEODataQualityState.OBSERVED.value,
        "tested_runs": len(ok_runs),
        "overall": overall,
        "branded": branded,
        "non_branded": non_branded,
        "by_platform": by_platform,
        "by_category": by_category,
        "absent_topics": absent_topics,
        "repeat_summary": summarize_repeat_variation(ctx.runs, ctx.responses),
        "historical_trend": [
            {
                "audit_id": h.get("audit_id"),
                "created_at": h.get("created_at"),
                "observed_performance_score": h.get("observed_performance_score"),
            }
            for h in ctx.historical_audits[-10:]
        ],
    }
    return (
        GEOAgentOutput(
            agent_id="geo_department_b_ai_visibility",
            department="B",
            status="completed",
            audit_id=ctx.audit_id,
            findings=findings,
            evidence_ids=ev_ids,
            confidence=0.90,
            limitations=[
                "Observed results reflect tested prompt runs and configured testing modes, not universal market share."
            ],
            execution_metadata={"agents_executed": 8, "observed_runs": len(ok_runs)},
        ),
        artifact,
    )


def run_department_c(ctx: GEOAuditContext) -> Tuple[GEOAgentOutput, Dict[str, Any]]:
    """Department C: Citation & Source Intelligence."""
    graph = ctx.citation_graph or {}
    summary = graph.get("summary") or {}
    total = int(summary.get("total_citations") or 0)
    ok_runs = [r for r in ctx.runs if r.status == GEODataQualityState.OBSERVED]
    if not ok_runs:
        return (
            GEOAgentOutput(
                agent_id="geo_department_c_citations",
                department="C",
                status="not_tested",
                audit_id=ctx.audit_id,
                limitations=["No live provider executions available to observe citations."],
                execution_metadata={"agents_executed": 8, "citations_observed": 0},
            ),
            graph,
        )

    findings: List[GEOFinding] = []
    ev_ids = [c.citation_id for c in ctx.citations[:6]] or [r.response_id for r in ctx.responses[:4]]
    owned_cites = int(summary.get("owned_citations") or 0)
    indep_cites = int(summary.get("independent_citations") or 0)
    opportunities = graph.get("opportunities") or []

    if total > 0 and owned_cites == 0:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="citation_intelligence",
                department="C",
                agent_id="geo_citation_ownership",
                title=f"Owned domain ({ctx.scope.domain}) received 0 of {total} observed AI citations",
                description=f"Across {len(ok_runs)} successful response(s), {total} source URL(s) were cited, none from {ctx.scope.domain}.",
                root_cause="Owned pages lack reference-grade factual documentation or are out-cited by third-party and competitor pages.",
                root_cause_group="zero_owned_citations",
                affected_entities=[ctx.scope.brand_name],
                affected_urls=[ctx.scope.website_url],
                affected_platforms=sorted(summary.get("platform_distribution", {}).keys()),
                evidence_ids=ev_ids[:5],
                severity=GEOFindingSeverity.HIGH,
                confidence=0.90,
                business_impact="AI platforms attribute product/category claims to external or competitor URLs instead of official documentation.",
                recommendation="Upgrade official product, pricing, and specification pages with citable factual data and verify retrieval crawler access.",
                acceptance_criteria=[
                    "Official documentation and definition blocks published and verified.",
                    "Retest on citation-capable search-grounded providers tracks owned citation share.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    if opportunities:
        top_domains = [o["domain"] for o in opportunities[:5]]
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="citation_intelligence",
                department="C",
                agent_id="geo_citation_gap",
                title=f"Relevant independent sources cite competitors or omit brand ({len(opportunities)} source gap(s))",
                description=f"Frequently cited independent sources omitting or under-representing {ctx.scope.brand_name}: {', '.join(top_domains)}.",
                root_cause="Missing verifiable brand/product presence in independent publications, review portals, or industry references.",
                root_cause_group="citation_source_gap",
                affected_entities=[ctx.scope.brand_name],
                affected_urls=[o["url"] for o in opportunities[:5] if o.get("url")],
                competitor_references=sorted({c for o in opportunities for c in o.get("competitors_present", [])})[:6],
                evidence_ids=ev_ids[:5],
                severity=GEOFindingSeverity.MEDIUM,
                confidence=0.85,
                business_impact="Independent sources repeatedly selected by generative platforms shape shortlist inclusion and brand framing.",
                recommendation="Pursue legitimate editorial coverage, accurate directory/profile updates, and compliant customer review programs—never paid or fabricated mentions.",
                acceptance_criteria=[
                    "Outreach or factual correction plans executed for top prioritized independent domains.",
                    "Independent source presence documented with provenance dates.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    return (
        GEOAgentOutput(
            agent_id="geo_department_c_citations",
            department="C",
            status="completed",
            audit_id=ctx.audit_id,
            findings=findings,
            evidence_ids=ev_ids,
            confidence=0.88,
            limitations=[
                "API_MODEL_ONLY platforms without web search grounding rarely emit native citation metadata; missing citation metadata is tracked as unavailable rather than zero authority."
            ],
            execution_metadata={"agents_executed": 8, "citations_observed": total, "opportunities": len(opportunities)},
        ),
        graph,
    )


def run_department_f(ctx: GEOAuditContext) -> Tuple[GEOAgentOutput, Dict[str, Any]]:
    """Department F: Reputation & Independent Authority."""
    indep_sources = [s for s in ctx.external_sources if s.is_independent]
    neg_mentions = [m for m in ctx.mentions if m.is_target_brand and m.mention_type in (GEOMentionType.NEGATIVE_MENTION, GEOMentionType.INCORRECT_REPRESENTATION)]
    ev_ids = [s.source_id for s in indep_sources[:5]] + [m.mention_id for m in neg_mentions[:5]]
    findings: List[GEOFinding] = []

    if neg_mentions:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="external_reputation",
                department="F",
                agent_id="geo_negative_representation",
                title=f"Negative or inaccurate brand representation detected in {len(neg_mentions)} AI observation(s)",
                description="; ".join((m.inaccuracy_note or m.context_snippet)[:120] for m in neg_mentions[:3]),
                root_cause="Unaddressed negative public commentary, outdated third-party profiles, or ambiguous official documentation.",
                root_cause_group="negative_brand_representation",
                affected_entities=[ctx.scope.brand_name],
                affected_prompts=sorted({m.prompt_id for m in neg_mentions}),
                affected_platforms=sorted({m.platform_id for m in neg_mentions}),
                evidence_ids=[m.mention_id for m in neg_mentions[:5]],
                severity=GEOFindingSeverity.CRITICAL if any(m.mention_type == GEOMentionType.INCORRECT_REPRESENTATION for m in neg_mentions) else GEOFindingSeverity.HIGH,
                confidence=0.87,
                business_impact="Negative or inaccurate descriptions during buyer trust queries directly erode conversion confidence.",
                recommendation="Investigate underlying public claims, publish transparent factual documentation, and request legitimate factual corrections on third-party listings.",
                acceptance_criteria=[
                    "Verified clarification published for every inaccurate claim.",
                    "Retest on trust/reputation prompts evaluates representation change.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    brand_present_indep = [s for s in indep_sources if s.brand_present]
    rep_score = None
    if ctx.runs and any(r.status == GEODataQualityState.OBSERVED for r in ctx.runs):
        base = min(100.0, len(brand_present_indep) * 20.0 + (25.0 if len(indep_sources) >= 2 else 10.0))
        penalty = min(40.0, len(neg_mentions) * 15.0)
        rep_score = max(0.0, round(base - penalty, 1))
    elif indep_sources:
        rep_score = round(min(80.0, len(brand_present_indep) * 20.0), 1)

    if rep_score is not None and len(brand_present_indep) == 0:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="external_reputation",
                department="F",
                agent_id="geo_external_brand_coverage",
                title="Limited observed independent third-party brand corroboration",
                description="Observed AI citations contain no verified independent third-party publications or reviews confirming the brand's claims.",
                root_cause="Third-party industry publications, reviews, and reference profiles do not yet cover the brand.",
                root_cause_group="thin_independent_authority",
                affected_entities=[ctx.scope.brand_name],
                evidence_ids=ev_ids[:3] or [r.response_id for r in ctx.responses[:3]],
                severity=GEOFindingSeverity.MEDIUM,
                confidence=0.80,
                business_impact="Generative engines rely heavily on independent corroboration to validate vendor claims.",
                recommendation="Build legitimate third-party presence via industry research contributions, verified customer reviews, and independent press/associations.",
                acceptance_criteria=[
                    "Target independent publications/directories cataloged with ethical contribution strategy.",
                    "At least 2 independent third-party references documented and tracked.",
                ],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    artifact = {
        "status": GEODataQualityState.OBSERVED.value if rep_score is not None else GEODataQualityState.NOT_TESTED.value,
        "reputation_score": rep_score,
        "independent_sources_total": len(indep_sources),
        "independent_sources_with_brand": len(brand_present_indep),
        "negative_or_inaccurate_mentions": len(neg_mentions),
        "by_category": {
            cat: sum(1 for s in indep_sources if s.source_category == cat)
            for cat in sorted({s.source_category for s in indep_sources})
        },
        "note": "Directory count or backlink volume is never converted into an artificial GEO authority score.",
    }
    return (
        GEOAgentOutput(
            agent_id="geo_department_f_reputation",
            department="F",
            status="completed" if rep_score is not None else "not_tested",
            audit_id=ctx.audit_id,
            findings=findings,
            evidence_ids=ev_ids,
            confidence=0.82 if rep_score is not None else None,
            limitations=["Only independent sources observed in captured responses or connected feeds are counted; unqueried external databases remain unmeasured."],
            execution_metadata={"agents_executed": 8, "independent_sources": len(indep_sources)},
        ),
        artifact,
    )


def run_department_g(ctx: GEOAuditContext) -> Tuple[GEOAgentOutput, Dict[str, Any]]:
    """Department G: Competitive GEO Intelligence (strictly under shared prompt suite)."""
    ok_runs = [r for r in ctx.runs if r.status == GEODataQualityState.OBSERVED]
    competitors = [c for c in (ctx.scope.competitors or []) if c]
    if not ok_runs:
        return (
            GEOAgentOutput(
                agent_id="geo_department_g_competitive",
                department="G",
                status="not_tested",
                audit_id=ctx.audit_id,
                limitations=["Competitive visibility requires captured responses from a common tested prompt suite."],
                execution_metadata={"agents_executed": 7, "competitors": len(competitors)},
            ),
            {"status": GEODataQualityState.NOT_TESTED.value, "tested_responses": 0, "comparison_table": [], "competitive_score": None},
        )

    resp_by_id = {r.response_id: r for r in ctx.responses}
    n = len(ok_runs)
    # Build uniform brand vs competitor comparison table
    entities = [ctx.scope.brand_name] + competitors
    rows: List[Dict[str, Any]] = []
    mentions_by_resp: Dict[str, List[Any]] = defaultdict(list)
    for m in ctx.mentions:
        mentions_by_resp[m.response_id].append(m)
    cites_by_resp: Dict[str, List[Any]] = defaultdict(list)
    for c in ctx.citations:
        cites_by_resp[c.response_id].append(c)

    target_row: Dict[str, Any] = {}
    for ent in entities:
        is_target = ent == ctx.scope.brand_name
        ment_resps = set()
        rec_resps = set()
        short_resps = set()
        cit_resps = set()
        indep_cit_resps = set()
        sent_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for run in ok_runs:
            resp = next((r for r in ctx.responses if r.run_id == run.run_id), None)
            if not resp:
                continue
            if is_target:
                if resp.brand_mentioned:
                    ment_resps.add(resp.response_id)
                if resp.brand_recommended:
                    rec_resps.add(resp.response_id)
                if resp.is_shortlisted:
                    short_resps.add(resp.response_id)
                if resp.brand_cited:
                    cit_resps.add(resp.response_id)
                if resp.sentiment in sent_counts:
                    sent_counts[resp.sentiment] += 1
                if any(c.source_ownership == GEOSourceOwnership.INDEPENDENT for c in cites_by_resp.get(resp.response_id, [])) and resp.brand_mentioned:
                    indep_cit_resps.add(resp.response_id)
            else:
                ent_low = ent.lower()
                ms = [m for m in mentions_by_resp.get(resp.response_id, []) if m.entity_name.lower() == ent_low]
                if ms:
                    ment_resps.add(resp.response_id)
                    if any(m.mention_type == GEOMentionType.RECOMMENDATION for m in ms):
                        rec_resps.add(resp.response_id)
                    s_val = ms[0].sentiment
                    if s_val in sent_counts:
                        sent_counts[s_val] += 1
                cs = cites_by_resp.get(resp.response_id, [])
                if any(ent_low in [x.lower() for x in c.competitors_associated] for c in cs):
                    cit_resps.add(resp.response_id)
                if ms and any(c.source_ownership == GEOSourceOwnership.INDEPENDENT for c in cs):
                    indep_cit_resps.add(resp.response_id)

        row = {
            "entity_name": ent,
            "is_target_brand": is_target,
            "tested_responses": n,
            "mentioned_responses": len(ment_resps),
            "mention_rate_pct": round(len(ment_resps) / n * 100.0, 1),
            "recommendations": len(rec_resps),
            "recommendation_rate_pct": round(len(rec_resps) / n * 100.0, 1),
            "shortlist_inclusions": len(short_resps),
            "cited_responses": len(cit_resps),
            "citation_rate_pct": round(len(cit_resps) / n * 100.0, 1),
            "independent_sources_cited": len(indep_cit_resps),
            "sentiment": sent_counts,
            "evidence_response_ids": sorted(ment_resps)[:10],
        }
        rows.append(row)
        if is_target:
            target_row = row

    rows.sort(key=lambda r: (r["recommendation_rate_pct"], r["mention_rate_pct"], r["citation_rate_pct"]), reverse=True)
    target_rank = next((i + 1 for i, r in enumerate(rows) if r["is_target_brand"]), len(rows))
    leader = rows[0] if rows else {}

    total_all_mentions = sum(r["mentioned_responses"] for r in rows)
    share_of_mentions = (
        round((target_row.get("mentioned_responses", 0) / total_all_mentions) * 100.0, 1)
        if total_all_mentions > 0 else None
    )
    comp_score = None
    if competitors and total_all_mentions > 0:
        comp_score = round(min(100.0, (share_of_mentions or 0.0) * 1.4), 1)
    elif target_row:
        comp_score = round(target_row.get("mention_rate_pct", 0.0), 1)

    findings: List[GEOFinding] = []
    ev_ids = [r.response_id for r in ctx.responses[:6]]
    if competitors and target_rank > 1 and leader:
        findings.append(
            GEOFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                category="competitive_intelligence",
                department="G",
                agent_id="geo_competitor_recommendation",
                title=f"Competitor '{leader['entity_name']}' leads tested AI responses (#{target_rank} for {ctx.scope.brand_name})",
                description=(
                    f"Across {n} shared prompt run(s), {leader['entity_name']} was mentioned in {leader['mentioned_responses']}/{n} "
                    f"({leader['recommendations']} recommendations) vs {ctx.scope.brand_name} in {target_row['mentioned_responses']}/{n} "
                    f"({target_row['recommendations']} recommendations)."
                ),
                root_cause="Competitors hold broader citation source coverage and clearer comparative differentiation on tested prompts.",
                root_cause_group="competitor_recommendation_gap",
                affected_entities=[ctx.scope.brand_name],
                competitor_references=[r["entity_name"] for r in rows if not r["is_target_brand"]][:5],
                evidence_ids=ev_ids[:5],
                severity=GEOFindingSeverity.HIGH,
                confidence=0.88,
                business_impact="Competitors capture shortlist preference in commercial and recommendation queries.",
                recommendation="Close topic coverage gaps, publish objective comparison pages with verifiable criteria, and build coverage in competitor-cited independent publications.",
                acceptance_criteria=[
                    "Objective comparison content published without unsubstantiated claims.",
                    "Retest on identical shared prompt suite compares brand vs competitor share.",
                ],
                limitations=["Observed competitor visibility is not proof that any single competitor optimization caused it."],
                data_quality_state=GEODataQualityState.OBSERVED,
            )
        )

    artifact = {
        "status": GEODataQualityState.OBSERVED.value,
        "tested_responses": n,
        "target_rank": target_rank,
        "leader_entity": leader.get("entity_name"),
        "target_mention_share_pct": share_of_mentions,
        "competitive_score": comp_score,
        "comparison_table": rows,
        "disclaimer": "All entities were evaluated on the identical captured prompt suite. Competitor visibility is an observation, not proof of causation.",
    }
    return (
        GEOAgentOutput(
            agent_id="geo_department_g_competitive",
            department="G",
            status="completed",
            audit_id=ctx.audit_id,
            findings=findings,
            evidence_ids=ev_ids,
            confidence=0.88,
            limitations=[artifact["disclaimer"]],
            execution_metadata={"agents_executed": 7, "competitors_compared": len(competitors)},
        ),
        artifact,
    )


def run_department_h(ctx: GEOAuditContext) -> Tuple[GEOAgentOutput, Dict[str, Any]]:
    """Department H: Market, Language, and Intent Intelligence."""
    prompt_by_id = {p.prompt_id: p for p in ctx.prompts}
    resp_by_run = {r.run_id: r for r in ctx.responses}
    ok_runs = [r for r in ctx.runs if r.status == GEODataQualityState.OBSERVED]

    by_market: Dict[str, Dict[str, Any]] = {}
    by_language: Dict[str, Dict[str, Any]] = {}
    by_intent: Dict[str, Dict[str, Any]] = {}

    def _bucket(key_fn) -> Dict[str, Dict[str, Any]]:
        buckets: Dict[str, List[Any]] = defaultdict(list)
        for run in ok_runs:
            p = prompt_by_id.get(run.prompt_id)
            if p:
                buckets[key_fn(p)].append(run)
        out: Dict[str, Dict[str, Any]] = {}
        for k, sub in sorted(buckets.items()):
            n = len(sub)
            m = sum(1 for r in sub if resp_by_run.get(r.run_id) and resp_by_run[r.run_id].brand_mentioned)
            rec = sum(1 for r in sub if resp_by_run.get(r.run_id) and resp_by_run[r.run_id].brand_recommended)
            cit = sum(1 for r in sub if resp_by_run.get(r.run_id) and resp_by_run[r.run_id].brand_cited)
            out[k] = {
                "runs": n,
                "mention_rate_pct": round(m / n * 100.0, 1) if n else None,
                "recommendation_rate_pct": round(rec / n * 100.0, 1) if n else None,
                "citation_rate_pct": round(cit / n * 100.0, 1) if n else None,
            }
        return out

    by_market = _bucket(lambda p: p.market)
    by_language = _bucket(lambda p: p.language)
    by_intent = _bucket(lambda p: p.intent)

    artifact = {
        "status": GEODataQualityState.OBSERVED.value if ok_runs else GEODataQualityState.NOT_TESTED.value,
        "configured_markets": list(ctx.scope.markets or []),
        "configured_languages": list(ctx.scope.languages or []),
        "by_market": by_market,
        "by_language": by_language,
        "by_intent": by_intent,
    }
    return (
        GEOAgentOutput(
            agent_id="geo_department_h_market_intent",
            department="H",
            status="completed" if ok_runs else "not_tested",
            audit_id=ctx.audit_id,
            findings=[],
            evidence_ids=[r.response_id for r in ctx.responses[:4]],
            confidence=0.85 if ok_runs else None,
            limitations=["Geographic & multilingual observations depend on prompts executed for each configured market and language."],
            execution_metadata={"agents_executed": 6, "markets": len(ctx.scope.markets), "languages": len(ctx.scope.languages)},
        ),
        artifact,
    )

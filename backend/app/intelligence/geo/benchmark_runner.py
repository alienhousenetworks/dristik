"""
GEO Benchmark Execution Engine & Immutable Evidence Store (Layer 2).
Executes standardized benchmark suites across live AI answer engines (ChatGPT, Perplexity, Gemini, Claude, Groq).
Stores verbatim raw responses, citations, ordinal positions, source classification, and computes reproducible scores.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel, Field

from app.intelligence.geo.adapters.base import BaseGeoEngineAdapter, EngineRawResponse
from app.intelligence.geo.adapters.registry import get_available_adapters, get_adapter
from app.intelligence.geo.benchmark_generator import BenchmarkQuery, BenchmarkSuite, benchmark_generator
from app.intelligence.geo.pipeline_store import geo_pipeline_store

logger = logging.getLogger(__name__)

SourceQuality = Literal["first_party", "third_party", "social_directory", "unsourced"]


class EvaluatedQueryRun(BaseModel):
    query_id: str
    category: str
    query_text: str
    engine_id: str
    engine_name: str
    model_version: str
    timestamp: str
    locale: str = "en-US"
    latency_ms: float = 0.0
    raw_response: str
    citations: List[str] = Field(default_factory=list)
    was_mentioned: bool = False
    mention_position: Optional[int] = None
    was_first_party_cited: bool = False
    source_domains: List[str] = Field(default_factory=list)
    source_quality: SourceQuality = "unsourced"
    status: str = "SUCCESS"  # SUCCESS | KEY_MISSING | TIMEOUT | ERROR
    error_message: Optional[str] = None
    run_index: int = 1


class EngineBenchmarkAggregate(BaseModel):
    engine_id: str
    engine_name: str
    model_version: str
    queries_tested: int = 0
    queries_succeeded: int = 0
    mention_count: int = 0
    mention_rate_pct: Optional[float] = None
    first_party_citation_count: int = 0
    first_party_citation_rate_pct: Optional[float] = None
    average_latency_ms: float = 0.0
    is_live: bool = False
    status: str = "AVAILABLE"  # AVAILABLE | UNAVAILABLE | RATE_LIMITED | KEY_MISSING


class ShareOfModelMetric(BaseModel):
    """
    Enterprise Share of Model (SoM) and Competitor Displacement metrics,
    benchmarking brand presence vs rivals across AI answer engines with buyer funnel weighting.
    """
    target_domain: str
    brand_name: str
    total_evaluated_queries: int
    share_of_model_pct: float
    funnel_weighted_som_pct: float = 0.0
    first_party_citation_share_pct: float
    recommendation_rank_score: float  # 0 to 100 based on position weighting
    ordinal_distribution: Dict[str, int] = Field(default_factory=dict)  # rank_1, rank_2_3, rank_4_plus, unranked
    stage_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # awareness, consideration, decision
    competitor_shares: Dict[str, float] = Field(default_factory=dict)
    competitor_displacements: List[Dict[str, Any]] = Field(default_factory=list)


class GeoBenchmarkReport(BaseModel):
    benchmark_id: str
    target_domain: str
    brand_name: str
    locale: str = "en-US"
    run_date: str
    total_queries: int
    engines_tested: List[str] = Field(default_factory=list)
    engine_aggregates: Dict[str, EngineBenchmarkAggregate] = Field(default_factory=dict)
    overall_mention_rate_pct: Optional[float] = None
    overall_first_party_citation_rate_pct: Optional[float] = None
    share_of_model: Optional[ShareOfModelMetric] = None
    repeats: int = 1
    failed_runs: int = 0
    matrix_grounding: Optional[str] = None
    evaluations: List[EvaluatedQueryRun] = Field(default_factory=list)
    critical_blindspots: List[str] = Field(default_factory=list)
    reproducibility_hash: str
    is_live_measurement: bool = True
    summary: str = ""
    sentiment_audit: Optional[Dict[str, Any]] = None
    offpage_citation_summary: Optional[Dict[str, Any]] = None


class GeoBenchmarkRunner:
    """
    Orchestrates live benchmark execution across configured AI engines.
    """

    def __init__(self):
        self.store = geo_pipeline_store

    def _classify_sources(self, citations: List[str], raw_text: str, target_domain: str) -> Tuple[List[str], SourceQuality, bool]:
        low_domain = target_domain.lower()
        extracted_domains = set()

        for c in citations:
            try:
                netloc = urlparse(str(c)).netloc.lower()
                if netloc:
                    extracted_domains.add(netloc.replace("www.", ""))
            except Exception:
                pass

        for match in re.finditer(r"https?://([a-zA-Z0-9\.\-]+)", raw_text):
            extracted_domains.add(match.group(1).lower().replace("www.", ""))

        domain_list = sorted(list(extracted_domains))
        was_first_party = any(low_domain in d for d in domain_list)

        if was_first_party:
            quality: SourceQuality = "first_party"
        elif any(any(soc in d for soc in ["linkedin", "twitter", "x.com", "crunchbase", "github", "clutch", "g2"]) for d in domain_list):
            quality = "social_directory"
        elif len(domain_list) > 0:
            quality = "third_party"
        else:
            quality = "unsourced"

        return domain_list, quality, was_first_party

    def _detect_mention_and_position(self, raw_text: str, brand: str, domain: str) -> Tuple[bool, Optional[int]]:
        low_text = (raw_text or "").lower()
        low_brand = (brand or "").lower().strip()
        low_domain = (domain or "").lower().strip()

        if not low_text or raw_text.startswith("API Error") or "Missing API key" in raw_text:
            return False, None

        has_mention = bool(
            (low_brand and low_brand in low_text) or
            (low_domain and low_domain in low_text)
        )

        position = None
        if has_mention:
            # Check ordinal rankings in recommendation lists
            lines = raw_text.split("\n")
            for line in lines:
                low_line = line.lower()
                if (low_brand and low_brand in low_line) or (low_domain and low_domain in low_line):
                    m_hash = re.search(r"#([0-9]+)", line)
                    if m_hash:
                        position = int(m_hash.group(1))
                        break
                    m_num = re.match(r"^\s*([0-9]+)[\.\)]", line)
                    if m_num:
                        position = int(m_num.group(1))
                        break

            if position is None:
                if re.search(rf"(?:1\.|#1|first|top choice|primary).*?{re.escape(low_brand)}", low_text):
                    position = 1
                elif re.search(rf"(?:2\.|#2|second).*?{re.escape(low_brand)}", low_text):
                    position = 2
                elif re.search(rf"(?:3\.|#3|third).*?{re.escape(low_brand)}", low_text):
                    position = 3

        return has_mention, position

    async def execute_benchmark(
        self,
        domain: str,
        brand_name: Optional[str] = None,
        industry: Optional[str] = None,
        services: Optional[List[str]] = None,
        competitors: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        locale: str = "en-US",
        mode: Literal["comprehensive", "concise"] = "concise",
        engines: Optional[List[str]] = None,
        suite_override: Optional[BenchmarkSuite] = None,
        repeats: int = 1,
        max_queries: Optional[int] = None,
    ) -> GeoBenchmarkReport:
        clean_domain = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
        brand = brand_name or clean_domain.split(".")[0].capitalize()

        # 1. Resolve Suite
        suite = suite_override or benchmark_generator.generate_suite(
            domain=clean_domain,
            brand_name=brand,
            industry=industry,
            services=services,
            competitors=competitors,
            locations=locations,
            mode=mode,
        )
        repeat_count = max(1, min(int(repeats or 1), 5))
        if max_queries and max_queries > 0:
            suite.queries = suite.queries[:max_queries]
            suite.total_queries = len(suite.queries)

        # 2. Resolve Engine Adapters
        active_adapters: List[BaseGeoEngineAdapter] = []
        if engines:
            for eid in engines:
                ad = get_adapter(eid)
                if ad:
                    active_adapters.append(ad)
        else:
            active_adapters = get_available_adapters()

        if not active_adapters:
            # Fallback to default adapters even if keys unconfigured to produce fail-closed report
            from app.intelligence.geo.adapters.registry import get_all_adapters
            active_adapters = get_all_adapters()[:3]

        benchmark_id = f"GEO-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{suite.suite_id[-4:]}"
        evaluations: List[EvaluatedQueryRun] = []
        engine_stats_map: Dict[str, Dict[str, Any]] = {
            ad.engine_id: {
                "name": ad.display_name,
                "model": ad.model,
                "tested": 0,
                "succeeded": 0,
                "mentions": 0,
                "first_party_citations": 0,
                "latencies": [],
                "is_live": ad.is_configured(),
                "status": "AVAILABLE" if ad.is_configured() else "KEY_MISSING"
            }
            for ad in active_adapters
        }

        # 3. Concurrently Dispatch Queries
        sem = asyncio.Semaphore(5)  # Max 5 concurrent external engine calls

        async def _run_single(
            ad: BaseGeoEngineAdapter,
            q: BenchmarkQuery,
            client: httpx.AsyncClient,
            run_index: int,
        ) -> EvaluatedQueryRun:
            async with sem:
                resp = await ad.execute_query(q.query_text, locale=locale, client=client)
                has_mention, pos = self._detect_mention_and_position(resp.raw_content, brand, clean_domain)
                sources, quality, is_1p = self._classify_sources(resp.citations, resp.raw_content, clean_domain)

                status = "SUCCESS"
                if resp.status_code == 401 or "Missing" in (resp.error or ""):
                    status = "KEY_MISSING"
                elif resp.status_code == 504:
                    status = "TIMEOUT"
                elif resp.error:
                    status = "ERROR"

                return EvaluatedQueryRun(
                    query_id=q.query_id,
                    category=q.category,
                    query_text=q.query_text,
                    engine_id=ad.engine_id,
                    engine_name=ad.display_name,
                    model_version=ad.model,
                    timestamp=resp.queried_at,
                    locale=locale,
                    latency_ms=resp.latency_ms,
                    raw_response=resp.raw_content,
                    citations=resp.citations,
                    was_mentioned=has_mention,
                    mention_position=pos,
                    was_first_party_cited=is_1p,
                    source_domains=sources,
                    source_quality=quality,
                    status=status,
                    error_message=resp.error,
                    run_index=run_index,
                )

        tasks = []
        async with httpx.AsyncClient(timeout=18.0) as client:
            for run_index in range(1, repeat_count + 1):
                for q in suite.queries:
                    for ad in active_adapters:
                        tasks.append(_run_single(ad, q, client, run_index))

            evaluations = list(await asyncio.gather(*tasks))

        # 4. Aggregate Metrics
        for ev in evaluations:
            st = engine_stats_map.get(ev.engine_id)
            if not st:
                continue
            st["tested"] += 1
            if ev.status == "SUCCESS":
                st["succeeded"] += 1
                if ev.latency_ms > 0:
                    st["latencies"].append(ev.latency_ms)
                if ev.was_mentioned:
                    st["mentions"] += 1
                if ev.was_first_party_cited:
                    st["first_party_citations"] += 1

        engine_aggregates: Dict[str, EngineBenchmarkAggregate] = {}
        total_mentions = 0
        total_1p_citations = 0
        total_succeeded = 0

        for eid, st in engine_stats_map.items():
            t_cnt = st["tested"]
            m_cnt = st["mentions"]
            c_cnt = st["first_party_citations"]
            s_cnt = st["succeeded"]
            total_mentions += m_cnt
            total_1p_citations += c_cnt
            total_succeeded += s_cnt

            avg_lat = round(sum(st["latencies"]) / len(st["latencies"]), 1) if st["latencies"] else 0.0
            m_rate = round((m_cnt / s_cnt) * 100.0, 1) if s_cnt > 0 else None
            c_rate = round((c_cnt / s_cnt) * 100.0, 1) if s_cnt > 0 else None

            engine_aggregates[eid] = EngineBenchmarkAggregate(
                engine_id=eid,
                engine_name=st["name"],
                model_version=st["model"],
                queries_tested=t_cnt,
                queries_succeeded=s_cnt,
                mention_count=m_cnt,
                mention_rate_pct=m_rate,
                first_party_citation_count=c_cnt,
                first_party_citation_rate_pct=c_rate,
                average_latency_ms=avg_lat,
                is_live=st["is_live"],
                status=st["status"],
            )

        overall_mention_rate = round((total_mentions / total_succeeded) * 100.0, 1) if total_succeeded > 0 else None
        overall_1p_citation_rate = round((total_1p_citations / total_succeeded) * 100.0, 1) if total_succeeded > 0 else None
        failed_runs = sum(1 for ev in evaluations if ev.status != "SUCCESS")

        # Blindspots only when a successful response omitted the brand. Errors are not omissions.
        blindspots: List[str] = []
        for q in suite.queries:
            success_runs = [e for e in evaluations if e.query_id == q.query_id and e.status == "SUCCESS"]
            if success_runs and not any(r.was_mentioned for r in success_runs):
                blindspots.append(f"{q.category_label}: '{q.query_text}'")

        # Reproducibility hash
        hash_input = f"{benchmark_id}|{clean_domain}|{len(evaluations)}|{overall_mention_rate}|{overall_1p_citation_rate}"
        reproducibility_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        mention_text = f"{overall_mention_rate:.1f}%" if overall_mention_rate is not None else "not measured"
        citation_text = f"{overall_1p_citation_rate:.1f}%" if overall_1p_citation_rate is not None else "not measured"
        summary = (
            f"Live AI Retrieval Benchmark ({benchmark_id}): {len(suite.queries)} queries, "
            f"{repeat_count} run(s) each, across {len(active_adapters)} engines. "
            f"Brand mention rate {mention_text}, first-party citation rate {citation_text}, "
            f"over {total_succeeded} successful responses ({failed_runs} errors excluded). "
            f"{len(blindspots)} category blindspots identified."
        )

        # Compute Share of Model (SoM) and Competitor Displacement
        som_metric = self.calculate_share_of_model(
            evaluations=evaluations,
            target_domain=clean_domain,
            brand_name=brand,
            competitors=competitors,
        )

        # Compute sentiment & hallucination audit
        sentiment_audit_dict = None
        try:
            from app.intelligence.geo.sentiment_engine import geo_sentiment_engine
            sentiment_audit_dict = geo_sentiment_engine.generate_audit_report(
                evaluations=evaluations,
                brand_name=brand,
            ).model_dump()
        except Exception as exc:
            logger.debug("[BenchmarkRunner] Sentiment audit skipped: %s", exc)

        # Compute off-page citation authority network
        offpage_dict = None
        try:
            from app.intelligence.geo.offpage_network import offpage_network_analyzer
            offpage_dict = offpage_network_analyzer.analyze_citation_network(
                evaluations=evaluations,
                target_domain=clean_domain,
                brand_name=brand,
                competitors=competitors,
            ).model_dump()
        except Exception as exc:
            logger.debug("[BenchmarkRunner] Offpage network skipped: %s", exc)

        return GeoBenchmarkReport(
            benchmark_id=benchmark_id,
            target_domain=clean_domain,
            brand_name=brand,
            locale=locale,
            run_date=datetime.now(timezone.utc).isoformat(),
            total_queries=len(suite.queries),
            engines_tested=[ad.display_name for ad in active_adapters],
            engine_aggregates=engine_aggregates,
            overall_mention_rate_pct=overall_mention_rate,
            overall_first_party_citation_rate_pct=overall_1p_citation_rate,
            share_of_model=som_metric,
            evaluations=evaluations,
            critical_blindspots=blindspots[:8],
            reproducibility_hash=reproducibility_hash,
            is_live_measurement=total_succeeded > 0,
            summary=summary,
            repeats=repeat_count,
            failed_runs=failed_runs,
            sentiment_audit=sentiment_audit_dict,
            offpage_citation_summary=offpage_dict,
        )

    def calculate_share_of_model(
        self,
        evaluations: List[EvaluatedQueryRun],
        target_domain: str,
        brand_name: str,
        competitors: Optional[List[str]] = None,
    ) -> ShareOfModelMetric:
        """
        Calculates enterprise Share of Model (SoM), ordinal position distributions,
        and competitor displacement instances where rivals stole top recommendations.
        """
        clean_domain = (target_domain or "").lower().replace("https://", "").replace("http://", "").split("/")[0]
        brand = (brand_name or clean_domain.split(".")[0]).lower().strip()
        comp_list = [c.lower().strip() for c in (competitors or []) if c and c.strip()]

        successes = [e for e in evaluations if e.status == "SUCCESS"]
        total = len(successes)
        if total == 0:
            return ShareOfModelMetric(
                target_domain=clean_domain,
                brand_name=brand_name,
                total_evaluated_queries=0,
                share_of_model_pct=0.0,
                first_party_citation_share_pct=0.0,
                recommendation_rank_score=0.0,
                ordinal_distribution={"rank_1": 0, "rank_2_3": 0, "rank_4_plus": 0, "unranked": 0},
                competitor_shares={},
                competitor_displacements=[],
            )

        target_mentions = 0
        target_first_party_citations = 0
        rank_1 = 0
        rank_2_3 = 0
        rank_4_plus = 0
        unranked = 0
        position_weight_sum = 0.0

        for ev in successes:
            if ev.was_mentioned:
                target_mentions += 1
                pos = ev.mention_position
                if pos == 1:
                    rank_1 += 1
                    position_weight_sum += 1.0
                elif pos in (2, 3):
                    rank_2_3 += 1
                    position_weight_sum += 0.75
                elif pos and pos >= 4:
                    rank_4_plus += 1
                    position_weight_sum += 0.40
                else:
                    unranked += 1
                    position_weight_sum += 0.50
            else:
                unranked += 1

            if ev.was_first_party_cited:
                target_first_party_citations += 1

        # Competitor shares & displacements
        competitor_shares: Dict[str, float] = {}
        displacements: List[Dict[str, Any]] = []

        for comp in comp_list:
            comp_mentions = 0
            for ev in successes:
                raw_lower = (ev.raw_response or "").lower()
                c_hit = comp in raw_lower or any(comp in s for s in ev.source_domains)
                if c_hit:
                    comp_mentions += 1
                    if not ev.was_mentioned:
                        displacements.append({
                            "query_id": ev.query_id,
                            "query_text": ev.query_text,
                            "engine": ev.engine_name,
                            "displacing_competitor": comp,
                            "target_mentioned": False,
                            "reason": f"Competitor '{comp}' was recommended while '{brand_name}' was omitted from the answer.",
                        })
                    elif ev.mention_position and ev.mention_position > 1:
                        displacements.append({
                            "query_id": ev.query_id,
                            "query_text": ev.query_text,
                            "engine": ev.engine_name,
                            "displacing_competitor": comp,
                            "target_mentioned": True,
                            "target_position": ev.mention_position,
                            "reason": f"Competitor '{comp}' led the recommendation list while '{brand_name}' was ranked #{ev.mention_position}.",
                        })

            competitor_shares[comp] = round((comp_mentions / total) * 100.0, 1)

        som_pct = round((target_mentions / total) * 100.0, 1)
        cit_share_pct = round((target_first_party_citations / total) * 100.0, 1)
        rank_score = round((position_weight_sum / total) * 100.0, 1)

        # Stage-weighted metrics
        # Decision: commercial, comparative, high_intent (weight 4.0)
        # Consideration: services, problem (weight 2.5)
        # Awareness: entity, audience, geographic, other (weight 1.0)
        stages = {
            "awareness": {"total": 0, "mentions": 0, "weight": 1.0},
            "consideration": {"total": 0, "mentions": 0, "weight": 2.5},
            "decision": {"total": 0, "mentions": 0, "weight": 4.0},
        }

        weighted_mentions = 0.0
        weighted_total = 0.0

        for ev in successes:
            cat = (getattr(ev, "category", "") or "").lower()
            if cat in ("commercial", "comparative", "high_intent"):
                stage_key = "decision"
            elif cat in ("services", "problem"):
                stage_key = "consideration"
            else:
                stage_key = "awareness"

            st = stages[stage_key]
            st["total"] += 1
            w = st["weight"]
            weighted_total += w

            if ev.was_mentioned:
                st["mentions"] += 1
                weighted_mentions += w

        stage_breakdown: Dict[str, Dict[str, Any]] = {}
        for s_name, s_data in stages.items():
            s_tot = s_data["total"]
            s_men = s_data["mentions"]
            rate = round((s_men / max(1, s_tot)) * 100.0, 1) if s_tot > 0 else None
            stage_breakdown[s_name] = {
                "total_queries": s_tot,
                "mentions": s_men,
                "mention_rate_pct": rate,
                "commercial_weight": s_data["weight"],
            }

        funnel_som = round((weighted_mentions / max(0.1, weighted_total)) * 100.0, 1) if weighted_total > 0 else som_pct

        return ShareOfModelMetric(
            target_domain=clean_domain,
            brand_name=brand_name,
            total_evaluated_queries=total,
            share_of_model_pct=som_pct,
            funnel_weighted_som_pct=funnel_som,
            first_party_citation_share_pct=cit_share_pct,
            recommendation_rank_score=rank_score,
            ordinal_distribution={
                "rank_1": rank_1,
                "rank_2_3": rank_2_3,
                "rank_4_plus": rank_4_plus,
                "unranked": unranked,
            },
            stage_breakdown=stage_breakdown,
            competitor_shares=competitor_shares,
            competitor_displacements=displacements[:30],
        )


def _pct(hits: int, total: int) -> Optional[float]:
    if total <= 0:
        return None
    return round((hits / total) * 100.0, 1)


def build_visibility_scorecard(
    report: GeoBenchmarkReport,
    services: Optional[List[str]] = None,
    competitors: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    industry: Optional[str] = None,
    audience: Optional[str] = None,
    matrix_grounding: Optional[str] = None,
):
    """Rates over successful responses only. Unchecked rates stay null."""
    from app.domain.models import AiVisibilityScorecard

    successes = [ev for ev in report.evaluations if ev.status == "SUCCESS"]
    failures = [ev for ev in report.evaluations if ev.status != "SUCCESS"]
    if not successes:
        return AiVisibilityScorecard(
            status="NOT_MEASURED",
            engines_requested=len(report.engines_tested),
            queries=report.total_queries,
            repeats=report.repeats,
            failed_runs=len(failures),
            not_measured_reason="No successful engine responses. Errors are excluded rather than scored as omissions.",
            matrix_grounding=matrix_grounding,
        )

    brand = (report.brand_name or "").lower()
    service_terms = [s.lower() for s in (services or []) if s]
    competitor_terms = [c.lower() for c in (competitors or []) if c and "leading competitors" not in c.lower()]
    location_terms = [loc.lower() for loc in (locations or []) if loc]
    industry_term = (industry or "").lower().strip()
    audience_term = (audience or "").lower().strip()

    entity_hits = 0
    entity_slots = 0
    service_hits = 0
    service_total = 0
    pricing_hits = 0
    pricing_total = 0
    icp_hits = 0
    icp_total = 0
    competitor_hits = 0

    for ev in successes:
        text = (ev.raw_response or "").lower()
        slots = []
        if brand:
            slots.append(brand in text)
        if service_terms:
            slots.append(any(term in text for term in service_terms))
        if location_terms:
            slots.append(any(term in text for term in location_terms))
        if industry_term and industry_term not in ("this category",):
            slots.append(industry_term in text)
        if audience_term:
            slots.append(audience_term in text)
        if slots:
            entity_slots += len(slots)
            entity_hits += sum(1 for ok in slots if ok)

        if ev.category == "services" and service_terms:
            service_total += 1
            if any(term in text for term in service_terms):
                service_hits += 1
        if ev.category in ("high_intent", "commercial") and "pric" in (ev.query_text or "").lower():
            pricing_total += 1
            if brand and brand in text:
                pricing_hits += 1
        if ev.category == "audience" and (audience_term or brand):
            icp_total += 1
            if (audience_term and audience_term in text) or (brand and brand in text):
                icp_hits += 1
        if competitor_terms and any(term in text for term in competitor_terms):
            competitor_hits += 1

    source_consistency = None
    if report.repeats >= 2:
        by_query: Dict[str, List[EvaluatedQueryRun]] = {}
        for ev in successes:
            by_query.setdefault(ev.query_id, []).append(ev)
        stable = 0
        seen = 0
        for runs in by_query.values():
            domain_counts: Dict[str, int] = {}
            for ev in runs:
                for domain in ev.source_domains:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
            for count in domain_counts.values():
                seen += 1
                if count >= 2:
                    stable += 1
        source_consistency = _pct(stable, seen)

    engines_live = sum(1 for agg in report.engine_aggregates.values() if agg.queries_succeeded > 0)
    return AiVisibilityScorecard(
        status="MEASURED",
        engines_measured=engines_live,
        engines_requested=len(report.engines_tested),
        queries=report.total_queries,
        repeats=report.repeats,
        successful_runs=len(successes),
        failed_runs=len(failures),
        mention_rate_pct=report.overall_mention_rate_pct,
        citation_rate_pct=report.overall_first_party_citation_rate_pct,
        citation_accuracy_pct=None,
        entity_accuracy_pct=_pct(entity_hits, entity_slots),
        service_recognition_pct=_pct(service_hits, service_total),
        icp_recognition_pct=_pct(icp_hits, icp_total),
        pricing_recognition_pct=_pct(pricing_hits, pricing_total),
        competitor_visibility_pct=_pct(competitor_hits, len(successes)) if competitor_terms else None,
        hallucination_rate_pct=None,
        source_consistency_pct=source_consistency,
        matrix_grounding=matrix_grounding,
    )


benchmark_runner = GeoBenchmarkRunner()

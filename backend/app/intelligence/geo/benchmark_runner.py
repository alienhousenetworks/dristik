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


class EngineBenchmarkAggregate(BaseModel):
    engine_id: str
    engine_name: str
    model_version: str
    queries_tested: int = 0
    queries_succeeded: int = 0
    mention_count: int = 0
    mention_rate_pct: float = 0.0
    first_party_citation_count: int = 0
    first_party_citation_rate_pct: float = 0.0
    average_latency_ms: float = 0.0
    is_live: bool = False
    status: str = "AVAILABLE"  # AVAILABLE | UNAVAILABLE | RATE_LIMITED | KEY_MISSING


class GeoBenchmarkReport(BaseModel):
    benchmark_id: str
    target_domain: str
    brand_name: str
    locale: str = "en-US"
    run_date: str
    total_queries: int
    engines_tested: List[str] = Field(default_factory=list)
    engine_aggregates: Dict[str, EngineBenchmarkAggregate] = Field(default_factory=dict)
    overall_mention_rate_pct: float = 0.0
    overall_first_party_citation_rate_pct: float = 0.0
    evaluations: List[EvaluatedQueryRun] = Field(default_factory=list)
    critical_blindspots: List[str] = Field(default_factory=list)
    reproducibility_hash: str
    is_live_measurement: bool = True
    summary: str = ""


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

        async def _run_single(ad: BaseGeoEngineAdapter, q: BenchmarkQuery, client: httpx.AsyncClient) -> EvaluatedQueryRun:
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
                )

        tasks = []
        async with httpx.AsyncClient(timeout=18.0) as client:
            for q in suite.queries:
                for ad in active_adapters:
                    tasks.append(_run_single(ad, q, client))

            evaluations = await asyncio.gather(*tasks)

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
            m_rate = round((m_cnt / max(1, s_cnt)) * 100.0, 1) if s_cnt > 0 else 0.0
            c_rate = round((c_cnt / max(1, s_cnt)) * 100.0, 1) if s_cnt > 0 else 0.0

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

        overall_mention_rate = round((total_mentions / max(1, total_succeeded)) * 100.0, 1) if total_succeeded > 0 else 0.0
        overall_1p_citation_rate = round((total_1p_citations / max(1, total_succeeded)) * 100.0, 1) if total_succeeded > 0 else 0.0

        # Critical blindspots detection (queries where target company was completely omitted across all engines)
        blindspots: List[str] = []
        for q in suite.queries:
            q_runs = [e for e in evaluations if e.query_id == q.query_id]
            if q_runs and not any(r.was_mentioned for r in q_runs if r.status == "SUCCESS"):
                blindspots.append(f"{q.category_label}: '{q.query_text}'")

        # Reproducibility hash
        hash_input = f"{benchmark_id}|{clean_domain}|{len(evaluations)}|{overall_mention_rate}|{overall_1p_citation_rate}"
        reproducibility_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        summary = (
            f"Live AI Retrieval Benchmark ({benchmark_id}): {len(suite.queries)} queries tested across "
            f"{len(active_adapters)} engines. Overall Brand Mention Rate: {overall_mention_rate:.1f}%, "
            f"First-Party Citation Rate: {overall_1p_citation_rate:.1f}%. "
            f"{len(blindspots)} category blindspots identified."
        )

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
            evaluations=evaluations,
            critical_blindspots=blindspots[:8],
            reproducibility_hash=reproducibility_hash,
            is_live_measurement=any(a.is_live for a in engine_aggregates.values()),
            summary=summary,
        )


benchmark_runner = GeoBenchmarkRunner()

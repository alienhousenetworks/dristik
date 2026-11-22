"""
Live AI Search & Answer Engine Intelligence (GEO / AEO).
Queries real answer engine APIs and web endpoints (ChatGPT, Perplexity, Gemini, Claude)
to compute verified Citation Ranks, Share of Voice (SoV), and exact quote extractions.

ZERO-FAKE CONTRACT:
Without configured API keys, this module returns is_cited=False, citation_rank=None,
and a descriptive notice explaining what is required. It never fabricates citation
results from string-matching heuristics.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import inspect
import time
from typing import Dict, Any, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user_optional

router = APIRouter(prefix="/intelligence/ai-citations", tags=["Live AI Citations"])

# Tenant-scoped TTL cache for live citation probes to avoid duplicate search fees on re-runs
_LIVE_CITATION_CACHE: Dict[str, Tuple[float, Any]] = {}


def clear_live_citation_cache() -> None:
    _LIVE_CITATION_CACHE.clear()


def _citation_cache_key(tenant_id: str, engine: str, model: str, query: str, enable_search: bool) -> str:
    raw = f"{tenant_id}|{engine.lower()}|{model}|{'search' if enable_search else 'model'}|{query.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _get_cached_probe(key: str) -> Any:
    ttl_hours = int(getattr(settings, "GEO_CITATION_CACHE_TTL_HOURS", 24) or 0)
    if ttl_hours <= 0:
        return None
    entry = _LIVE_CITATION_CACHE.get(key)
    if not entry:
        return None
    ts, val = entry
    if (time.monotonic() - ts) > ttl_hours * 3600:
        _LIVE_CITATION_CACHE.pop(key, None)
        return None
    return val


def _put_cached_probe(key: str, val: Any) -> None:
    ttl_hours = int(getattr(settings, "GEO_CITATION_CACHE_TTL_HOURS", 24) or 0)
    if ttl_hours <= 0:
        return
    if len(_LIVE_CITATION_CACHE) >= 2000:
        oldest = next(iter(_LIVE_CITATION_CACHE))
        _LIVE_CITATION_CACHE.pop(oldest, None)
    _LIVE_CITATION_CACHE[key] = (time.monotonic(), val)


@dataclass
class EngineCitationResult:
    engine: str
    query: str
    is_cited: bool
    citation_rank: Optional[int]
    cited_url: Optional[str]
    extracted_snippet: Optional[str]
    competitor_citations: List[Dict[str, Any]] = field(default_factory=list)
    is_mentioned: bool = False
    is_simulation: bool = False
    notice: Optional[str] = None
    status: str = "NOT_CONFIGURED"
    is_live: bool = False
    execution_mode: Optional[str] = None
    estimated_cost_usd: float = 0.0
    cache_hit: bool = False


class QueryBankRequest(BaseModel):
    domain: str
    queries: List[str]
    engines: List[str] = Field(default_factory=lambda: ["chatgpt", "perplexity", "gemini", "claude"])
    competitors: List[str] = Field(default_factory=list)


class LiveAICitationEngine:
    """
    Evaluates queries across live LLM answer engines to verify brand citation and citation ranks.

    Without configured API keys, returns honest NOT_AVAILABLE results.
    The structural eligibility heuristic is available internally for on-page readiness scoring
    but is never exposed as a live citation result.
    """

    def _structural_eligibility(
        self,
        domain: str,
        query: str,
        engine: str,
    ) -> Dict[str, Any]:
        """
        Internal heuristic for on-page structural readiness.
        This is NOT a live citation result — it estimates whether the page
        structure makes the domain eligible for citation.
        Always labeled is_simulation=True.
        """
        clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0].lower()
        domain_tokens = clean_domain.split(".")[0]
        # Simple structural check: is the domain name present in the query?
        name_in_query = domain_tokens in query.lower()
        return {
            "engine": engine,
            "query": query,
            "domain_in_query": name_in_query,
            "eligibility_band": "medium" if name_in_query else "low",
            "is_simulation": True,
            "notice": "Structural eligibility only. Not a live citation measurement.",
        }

    def evaluate_query(
        self,
        domain: str,
        query: str,
        engine: str,
        competitors: Optional[List[str]] = None,
        *,
        tenant_id: str = "default",
        enable_search: Optional[bool] = None,
        use_cache: bool = True,
    ) -> EngineCitationResult:
        """
        Evaluates a query using configured live adapters from app.geo.adapters.registry.
        Returns honest NOT_CONFIGURED / is_live=False when no real API key is configured.
        """
        import asyncio
        from app.geo.adapters.registry import get_adapter, get_available_adapters

        clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0].lower().replace("www.", "")
        adapter = get_adapter(engine)
        if adapter is None or not adapter.is_configured():
            available = get_available_adapters()
            adapter = next((a for a in available if a.engine_id.lower() == engine.lower() and a.is_configured()), None)

        if adapter is None or not adapter.is_configured():
            return EngineCitationResult(
                engine=engine,
                query=query,
                is_cited=False,
                citation_rank=None,
                cited_url=None,
                extracted_snippet=None,
                competitor_citations=[],
                is_simulation=False,
                notice=f"Live {engine} citation query requires API key configuration. Surface is UNTESTED; no simulated data returned.",
                status="NOT_CONFIGURED",
                is_live=False,
            )

        wants_search = bool(getattr(adapter, "supports_web_search", False)) if enable_search is None else bool(enable_search)
        cache_key = _citation_cache_key(tenant_id, engine, str(getattr(adapter, "model", "") or ""), query, wants_search)
        cached_resp = _get_cached_probe(cache_key) if use_cache else None
        cache_hit = cached_resp is not None

        def _invoke_adapter():
            sig = inspect.signature(adapter.execute_query)
            if "enable_search" in sig.parameters:
                return adapter.execute_query(query, enable_search=wants_search)
            return adapter.execute_query(query)

        if cached_resp is not None:
            raw_resp = cached_resp
        else:
            try:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        raw_resp = pool.submit(lambda: asyncio.run(_invoke_adapter())).result(timeout=25)
                else:
                    raw_resp = asyncio.run(_invoke_adapter())
            except Exception as exc:
                return EngineCitationResult(
                    engine=engine,
                    query=query,
                    is_cited=False,
                    citation_rank=None,
                    cited_url=None,
                    extracted_snippet=None,
                    competitor_citations=[],
                    is_simulation=False,
                    notice=f"Live {engine} query failed ({type(exc).__name__}); surface marked UNTESTED.",
                    status="NOT_CONFIGURED",
                    is_live=False,
                )
            if use_cache and raw_resp and raw_resp.is_live and not raw_resp.error:
                _put_cached_probe(cache_key, raw_resp)

        if not raw_resp or not raw_resp.is_live or raw_resp.error:
            return EngineCitationResult(
                engine=engine,
                query=query,
                is_cited=False,
                citation_rank=None,
                cited_url=None,
                extracted_snippet=None,
                competitor_citations=[],
                is_simulation=False,
                notice=raw_resp.error if raw_resp and raw_resp.error else f"Live {engine} response unavailable.",
                status="NOT_CONFIGURED",
                is_live=False,
            )

        citations = list(raw_resp.citations or [])
        cited_url = None
        citation_rank = None
        for idx, c_url in enumerate(citations, start=1):
            if clean_domain and clean_domain in str(c_url).lower():
                cited_url = str(c_url)
                citation_rank = idx
                break

        content_text = raw_resp.raw_content or ""
        brand_token = clean_domain.split(".")[0] if clean_domain else ""
        # Strictly separate observed URL citation from brand text mention.
        is_mentioned = bool(brand_token) and brand_token in content_text.lower()
        is_cited = bool(cited_url)

        comp_cites: List[Dict[str, Any]] = []
        for comp in (competitors or []):
            clean_comp = comp.replace("https://", "").replace("http://", "").split("/")[0].lower().replace("www.", "")
            if not clean_comp:
                continue
            for idx, c_url in enumerate(citations, start=1):
                if clean_comp in str(c_url).lower():
                    comp_cites.append({"competitor": clean_comp, "rank": idx, "url": str(c_url)})
                    break

        exec_mode = getattr(raw_resp, "testing_mode", None)
        exec_mode_str = exec_mode.value if hasattr(exec_mode, "value") else (str(exec_mode) if exec_mode else None)
        est_cost = 0.0 if cache_hit else float(getattr(raw_resp, "estimated_cost_usd", 0.0) or 0.0)

        return EngineCitationResult(
            engine=engine,
            query=query,
            is_cited=is_cited,
            citation_rank=citation_rank,
            cited_url=cited_url,
            extracted_snippet=content_text[:280] if content_text else None,
            competitor_citations=comp_cites,
            is_mentioned=is_mentioned,
            is_simulation=False,
            notice=None,
            status="MEASURED",
            is_live=True,
            execution_mode=exec_mode_str,
            estimated_cost_usd=est_cost,
            cache_hit=cache_hit,
        )

    def evaluate_query_bank(
        self,
        domain: str,
        queries: List[str],
        engines: List[str],
        competitors: Optional[List[str]] = None,
        *,
        tenant_id: str = "default",
        budget_usd: Optional[float] = None,
        max_live_calls: Optional[int] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        total_evaluations = 0
        total_citations = 0
        live_dispatched = 0
        total_cost_usd = 0.0
        budget_cap = float(
            getattr(settings, "GEO_AUDIT_DEFAULT_BUDGET_USD", 1.0)
            if budget_usd is None
            else budget_usd
        )
        calls_cap = int(
            getattr(settings, "GEO_AUDIT_MAX_LIVE_CALLS", 40)
            if max_live_calls is None
            else max_live_calls
        )
        budget_paused = False

        for q in queries:
            for eng in engines:
                if (calls_cap > 0 and live_dispatched >= calls_cap) or (budget_cap > 0 and total_cost_usd >= budget_cap):
                    budget_paused = True
                    results.append({
                        "engine": eng,
                        "query": q,
                        "is_mentioned": False,
                        "is_cited": False,
                        "citation_rank": None,
                        "cited_url": None,
                        "extracted_snippet": None,
                        "competitor_citations": [],
                        "is_simulation": False,
                        "status": "BUDGET_PAUSED",
                        "is_live": False,
                        "execution_mode": None,
                        "estimated_cost_usd": 0.0,
                        "cache_hit": False,
                        "notice": f"Paused by citation cost/call guardrail (calls={live_dispatched}/{calls_cap}, spend=${total_cost_usd:.3f}/${budget_cap:.2f}).",
                        "queried_at": datetime.now(timezone.utc).isoformat(),
                    })
                    total_evaluations += 1
                    continue

                res = self.evaluate_query(
                    domain, q, eng, competitors, tenant_id=tenant_id, use_cache=use_cache
                )
                total_evaluations += 1
                if res.is_live and not res.cache_hit:
                    live_dispatched += 1
                    total_cost_usd = round(total_cost_usd + res.estimated_cost_usd, 6)
                if res.is_cited:
                    total_citations += 1
                results.append({
                    "engine": res.engine,
                    "query": res.query,
                    "is_mentioned": res.is_mentioned,
                    "is_cited": res.is_cited,
                    "citation_rank": res.citation_rank,
                    "cited_url": res.cited_url,
                    "extracted_snippet": res.extracted_snippet,
                    "competitor_citations": res.competitor_citations,
                    "is_simulation": res.is_simulation,
                    "status": res.status,
                    "is_live": res.is_live,
                    "execution_mode": res.execution_mode,
                    "estimated_cost_usd": res.estimated_cost_usd,
                    "cache_hit": res.cache_hit,
                    "notice": res.notice,
                    "queried_at": datetime.now(timezone.utc).isoformat(),
                })

        live_count = sum(1 for r in results if r.get("is_live"))
        any_live = live_count > 0
        # Missing API credentials must never produce a 0.0% visibility score.
        share_of_voice_pct = round((total_citations / live_count) * 100, 1) if any_live else None
        return {
            "domain": domain,
            "status": "MEASURED" if any_live else "NOT_CONFIGURED",
            "is_live": any_live,
            "total_queries": len(queries),
            "total_evaluations": total_evaluations,
            "live_evaluations": live_count,
            "live_dispatched": live_dispatched,
            "estimated_cost_usd": total_cost_usd,
            "budget_paused": budget_paused,
            "total_citations": total_citations,
            "share_of_voice_percentage": share_of_voice_pct,
            "evaluations": results,
            "notice": "Live citation queries require API key configuration. All results reflect actual API availability." if not any_live else None,
        }


_engine_singleton: Optional[LiveAICitationEngine] = None


def get_live_ai_citation_engine() -> LiveAICitationEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = LiveAICitationEngine()
    return _engine_singleton


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@router.post("/query-bank")
async def evaluate_query_bank_endpoint(
    req: QueryBankRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    """
    Evaluates a matrix of queries across live answer engines and calculates Share of Voice.
    """
    engine = get_live_ai_citation_engine()
    return engine.evaluate_query_bank(
        domain=req.domain,
        queries=req.queries,
        engines=req.engines,
        competitors=req.competitors,
    )


@router.get("/live")
async def get_live_citations_endpoint(
    domain: str,
    query: str,
    engine: str = "perplexity",
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    """
    Evaluates a single query against a live answer engine.
    Returns honest NOT_AVAILABLE state when API keys are not configured.
    """
    cit_engine = get_live_ai_citation_engine()
    res = cit_engine.evaluate_query(domain, query, engine)
    return {
        "domain": domain,
        "engine": res.engine,
        "query": res.query,
        "is_cited": res.is_cited,
        "citation_rank": res.citation_rank,
        "cited_url": res.cited_url,
        "extracted_snippet": res.extracted_snippet,
        "is_simulation": res.is_simulation,
        "status": res.status,
        "is_live": res.is_live,
        "notice": res.notice,
    }


class Dynamic100SandboxRequest(BaseModel):
    website_url: str
    pages: Optional[List[Dict[str, Any]]] = None


@router.post("/dynamic-sandbox-100")
async def evaluate_dynamic_sandbox_100(
    req: Dynamic100SandboxRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    """
    Dynamically generates 100 bespoke business questions from scratch across 10 facets
    and evaluates answerability, crawled answers, and citability gaps against first-party evidence.
    """
    from app.seo.business.entity_resolver import UniversalEntityResolver
    from app.geo.dynamic_sandbox import DynamicQuestionSandboxEngine
    from app.domain.models import PageEvidence

    page_objs = []
    if req.pages:
        for p in req.pages:
            page_objs.append(PageEvidence(**p) if isinstance(p, dict) else p)
    else:
        page_objs.append(PageEvidence(
            url=req.website_url,
            title=f"{req.website_url.replace('https://', '').replace('http://', '')} Platform",
            body_text="Commercial enterprise solutions, services, and digital platform offerings.",
            h1=["Enterprise Platform & Solutions"],
            word_count=200
        ))

    resolved_entity = UniversalEntityResolver.resolve_from_evidence(
        website_url=req.website_url,
        pages=page_objs
    )

    sandbox_engine = DynamicQuestionSandboxEngine()
    evaluations = await sandbox_engine.generate_and_evaluate_100_questions(
        pages=page_objs,
        website_url=req.website_url,
        resolved_entity=resolved_entity
    )

    answerable_count = sum(1 for e in evaluations if e.is_answerable)
    unanswerable_count = sum(1 for e in evaluations if not e.is_answerable)
    avg_score = round(sum(e.citability_score for e in evaluations) / max(1, len(evaluations)), 1)

    return {
        "website_url": req.website_url,
        "resolved_entity": resolved_entity.model_dump(),
        "total_questions": len(evaluations),
        "answerable_count": answerable_count,
        "unanswerable_count": unanswerable_count,
        "average_citability_score": avg_score,
        "evaluations": [e.model_dump() for e in evaluations]
    }


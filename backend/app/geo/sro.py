"""
Provider-Independent Selection Rate Optimization (SRO) Engine for Dristik.

Architectural Principles:
1. Provider-agnostic: Gemini Search Grounding is ONE optional grounding provider,
   not the foundation. SRO runs cleanly with any configured search-grounded adapter
   (Perplexity, OpenAI Web Search, Claude, Gemini, Bright Data consumer UIs).
2. Channel separation: AI search grounding and organic SERP tracking are strictly
   separate measurement channels — an AI answer is never described as an organic SERP rank.
3. Explicit stage states: COMPLETED | PARTIAL | NOT_CONFIGURED | FAILED | SKIPPED.
   Missing provider keys report NOT_CONFIGURED rather than 0% visibility.
4. Provider-specific metrics: Never merges Gemini grounding word-budget share with
   Perplexity/Claude/OpenAI citation rates; reports each provider independently plus
   an explicit cross-platform aggregate with methodology and sample_size.
5. Measured evidence vs AI interpretation: ModelRouter synthesis receives normalized
   evidence and produces recommendations/gaps, but can NEVER overwrite measured metrics.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from app.core.security.ssrf import is_safe_url
from app.geo.adapters.gemini import compute_selection_rate
from app.geo.adapters.registry import get_adapter, get_available_adapters


class SROStageStatus(str, Enum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class SROStageResult(BaseModel):
    stage: str
    status: SROStageStatus
    provider_used: Optional[str] = None
    sample_size: int = 0
    note: Optional[str] = None
    error: Optional[str] = None


class SRORecommendation(BaseModel):
    category: str = "strategy"  # content | structure | technical | strategy
    priority: str = "medium"    # high | medium | low
    title: str
    description: str
    action_items: List[str] = Field(default_factory=list)


class ProviderSelectionMetrics(BaseModel):
    """Provider-specific measured metrics — never conflated across providers."""
    provider_id: str
    provider_name: str
    channel: str = "ai_citation"  # ai_search_grounding | ai_citation | consumer_ui
    status: SROStageStatus = SROStageStatus.NOT_CONFIGURED
    testing_mode: Optional[str] = None
    domain_cited: bool = False
    brand_mentioned: Optional[bool] = None
    source_included: bool = False
    grounding_word_share_pct: Optional[float] = None
    target_grounding_words: Optional[int] = None
    total_grounding_words: Optional[int] = None
    total_citations: int = 0
    cited_urls: List[str] = Field(default_factory=list)
    target_snippets: List[str] = Field(default_factory=list)
    observed_search_queries: List[str] = Field(
        default_factory=list,
        description="Observed grounding metadata queries; not Google's internal retrieval fan-out.",
    )
    error: Optional[str] = None


class SROOrganicSerpChannel(BaseModel):
    """Strictly separate organic SERP channel (never conflated with AI grounding)."""
    status: SROStageStatus = SROStageStatus.NOT_CONFIGURED
    provider: Optional[str] = None
    target_rank: Optional[int] = None
    top_competitor_urls: List[str] = Field(default_factory=list)
    note: str = "Organic SERP channel is measured independently from AI search grounding."


class SROPageSnapshot(BaseModel):
    url: str
    title: str = ""
    word_count: int = 0
    headings: List[str] = Field(default_factory=list)
    content_preview: str = ""
    error: Optional[str] = None


class SROGroundingAttribution(BaseModel):
    """Backward-compatible primary grounding summary (populated by any configured grounding provider)."""
    status: str = "NOT_CONFIGURED"
    provider_id: Optional[str] = None
    target_url_found: bool = False
    selection_rate: Optional[float] = None
    selection_rate_pct: Optional[float] = None
    target_grounding_words: int = 0
    total_grounding_words: int = 0
    target_chunk_indices: List[int] = Field(default_factory=list)
    target_snippets: List[str] = Field(default_factory=list)
    web_search_queries: List[str] = Field(default_factory=list)
    sources_count: int = 0
    error: Optional[str] = None


class SROPlatformCitation(BaseModel):
    """Backward-compatible per-platform citation view."""
    engine_id: str
    engine_name: str
    status: str  # CITED | NOT_CITED | NOT_CONFIGURED | ERROR
    target_url_cited: bool = False
    total_citations: int = 0
    cited_urls: List[str] = Field(default_factory=list)
    testing_mode: Optional[str] = None
    error: Optional[str] = None


class SROSynthesisPayload(BaseModel):
    """Schema-validated LLM interpretation payload (cannot overwrite measured metrics)."""
    summary: str
    recommendations: List[SRORecommendation] = Field(default_factory=list)
    content_gaps: List[str] = Field(default_factory=list)
    competitor_insights: List[str] = Field(default_factory=list)


class SROAnalysisResult(BaseModel):
    target_url: str
    keyword: str
    country: str = "US"
    brand_name: Optional[str] = None
    analyzed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Measured Evidence (never overwritten by LLM synthesis)
    overall_score: Optional[float] = None
    selection_rate: Optional[float] = None
    cross_platform_selection_rate_pct: Optional[float] = None
    cross_platform_methodology: str = (
        "Share of COMPLETED AI providers where target domain was cited or included as a source; "
        "NOT_CONFIGURED and FAILED providers are excluded from the denominator."
    )
    sample_size: int = 0
    confidence: Optional[float] = None
    data_quality_state: str = "NOT_CONFIGURED"  # COMPLETED | PARTIAL | NOT_CONFIGURED
    stage_results: Dict[str, SROStageResult] = Field(default_factory=dict)
    provider_coverage: Dict[str, str] = Field(default_factory=dict)
    provider_metrics: List[ProviderSelectionMetrics] = Field(default_factory=list)
    organic_serp: SROOrganicSerpChannel = Field(default_factory=SROOrganicSerpChannel)
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)

    # Backward-compatible views
    grounding: SROGroundingAttribution = Field(default_factory=SROGroundingAttribution)
    platforms: List[SROPlatformCitation] = Field(default_factory=list)
    target_page: Optional[SROPageSnapshot] = None
    competitor_pages: List[SROPageSnapshot] = Field(default_factory=list)

    # AI Interpretation (strictly separated from measured metrics)
    synthesis_mode: str = "deterministic"  # model_router | deterministic
    synthesis_model_used: Optional[str] = None
    summary: str = ""
    recommendations: List[SRORecommendation] = Field(default_factory=list)
    content_gaps: List[str] = Field(default_factory=list)
    competitor_insights: List[str] = Field(default_factory=list)


def _host_of(url: str) -> str:
    try:
        return (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def _strip_html(html: str) -> str:
    cleaned = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    cleaned = re.sub(r"<style[\s\S]*?</style>", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


async def fetch_page_snapshot(url: str, timeout: float = 10.0) -> SROPageSnapshot:
    safe, reason = is_safe_url(url)
    if not safe:
        return SROPageSnapshot(url=url, error=f"ssrf_blocked: {reason}")
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Dristik-Intelligence-Bot/2.0"})
            if resp.status_code >= 400:
                return SROPageSnapshot(url=url, error=f"HTTP {resp.status_code}")
            html = resp.text[:500_000]
            title_m = re.search(r"<title[^>]*>([\s\S]*?)</title>", html, re.I)
            title = _strip_html(title_m.group(1)) if title_m else ""
            headings = [
                _strip_html(m.group(2))
                for m in re.finditer(r"<h([1-3])[^>]*>([\s\S]*?)</h\1>", html, re.I)
            ][:20]
            plain = _strip_html(html)
            return SROPageSnapshot(
                url=url,
                title=title[:200],
                word_count=len(plain.split()),
                headings=[h for h in headings if h],
                content_preview=plain[:3000],
            )
    except Exception as exc:
        return SROPageSnapshot(url=url, error=str(exc)[:180])


def _deterministic_synthesis(
    *,
    target_url: str,
    keyword: str,
    provider_metrics: List[ProviderSelectionMetrics],
    cross_platform_pct: Optional[float],
    target_page: Optional[SROPageSnapshot],
    competitor_pages: List[SROPageSnapshot],
) -> SROSynthesisPayload:
    completed = [m for m in provider_metrics if m.status == SROStageStatus.COMPLETED]
    selected = [m for m in completed if m.source_included or m.domain_cited]
    recs: List[SRORecommendation] = []
    gaps: List[str] = []
    insights: List[str] = []

    if completed and not selected:
        gaps.append(
            f"Target domain {_host_of(target_url)} was not cited by any of the {len(completed)} completed AI provider(s) for '{keyword}'."
        )
        recs.append(
            SRORecommendation(
                category="content",
                priority="high",
                title="Add front-loaded, self-contained answer block for target query",
                description="None of the live AI providers selected this page as a cited source.",
                action_items=[
                    f"Add an explicit H2 answering '{keyword}' in the opening 40-60 words.",
                    "Anchor claims with concrete numbers, dates, and named entity attribution.",
                ],
            )
        )
    elif cross_platform_pct is not None and cross_platform_pct < 50.0:
        missed = [m.provider_name for m in completed if not (m.source_included or m.domain_cited)]
        gaps.append(f"Excluded on {len(missed)}/{len(completed)} completed provider(s): {', '.join(missed)}.")
        recs.append(
            SRORecommendation(
                category="structure",
                priority="medium",
                title="Expand factual density and structured markup for missed AI providers",
                description="Partial cross-platform selection indicates extractability or third-party corroboration gaps.",
                action_items=[
                    "Replace pronoun-led paragraphs with explicit brand/product entity names.",
                    "Add comparison tables or FAQPage JSON-LD covering key buyer sub-questions.",
                ],
            )
        )

    for m in completed:
        if m.grounding_word_share_pct is not None and m.grounding_word_share_pct < 25.0 and m.source_included:
            gaps.append(
                f"Low {m.provider_name} grounding word share ({m.grounding_word_share_pct}% of grounding words)."
            )

    if target_page and not target_page.error and target_page.word_count < 400:
        gaps.append(f"Thin page content ({target_page.word_count} words) limits AI retrieval selection.")

    for cp in competitor_pages:
        if not cp.error and cp.word_count > 0:
            insights.append(
                f"Cited competitor {cp.url} ({cp.word_count} words, {len(cp.headings)} headings) was selected in live answers."
            )

    if completed:
        summary = (
            f"Provider-independent SRO for '{keyword}' on {_host_of(target_url)}: "
            f"selected on {len(selected)}/{len(completed)} completed AI provider(s) "
            f"({cross_platform_pct}% cross-platform selection rate)."
        )
    else:
        summary = (
            f"No live AI providers were configured for '{keyword}' on {_host_of(target_url)}; "
            "SRO selection metrics remain NOT_CONFIGURED."
        )

    return SROSynthesisPayload(
        summary=summary,
        recommendations=recs,
        content_gaps=gaps,
        competitor_insights=insights,
    )


async def _model_router_synthesis(
    *,
    target_url: str,
    keyword: str,
    provider_metrics: List[ProviderSelectionMetrics],
    target_page: Optional[SROPageSnapshot],
    competitor_pages: List[SROPageSnapshot],
    synthesis_model: Optional[str] = None,
) -> Optional[tuple[SROSynthesisPayload, str]]:
    """Model-agnostic synthesis via Dristik's ModelRouter with strict schema validation."""
    try:
        from app.core.inference.model_router import model_router
    except Exception:
        return None

    evidence_blob = {
        "target_url": target_url,
        "keyword": keyword,
        "provider_metrics": [
            {
                "provider": m.provider_id,
                "status": m.status.value,
                "domain_cited": m.domain_cited,
                "brand_mentioned": m.brand_mentioned,
                "grounding_word_share_pct": m.grounding_word_share_pct,
                "total_citations": m.total_citations,
            }
            for m in provider_metrics
        ],
        "target_page": (
            {"title": target_page.title, "word_count": target_page.word_count, "headings": target_page.headings[:10]}
            if target_page and not target_page.error
            else None
        ),
        "competitor_pages": [
            {"url": c.url, "title": c.title, "word_count": c.word_count, "headings": c.headings[:8]}
            for c in competitor_pages
            if not c.error
        ],
    }

    system_prompt = (
        "You are an evidence-grounded Selection Rate Optimization (SRO) analyst. "
        "Analyze ONLY the normalized evidence provided. Never invent SERP ranks, citations, "
        "or metrics for NOT_CONFIGURED stages. Respond ONLY with valid JSON matching: "
        '{"summary":"...","recommendations":[{"category":"content|structure|technical|strategy",'
        '"priority":"high|medium|low","title":"...","description":"...","action_items":["..."]}],'
        '"content_gaps":["..."],"competitor_insights":["..."]}.'
    )
    user_prompt = json.dumps(evidence_blob, ensure_ascii=False)[:12000]

    try:
        resp = await model_router.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_override=synthesis_model or None,
            max_tokens=900,
            temperature=0.2,
        )
        raw = resp.text if hasattr(resp, "text") else str(resp)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip()).strip()
        parsed = SROSynthesisPayload.model_validate_json(cleaned)
        used_model = str(getattr(resp, "model", None) or synthesis_model or "model_router")
        return parsed, used_model
    except Exception:
        return None


class SROEngine:
    """Provider-independent, model-agnostic Selection Rate Optimization engine."""

    async def analyze(
        self,
        *,
        target_url: str,
        keyword: str,
        country: str = "US",
        brand_name: Optional[str] = None,
        competitor_urls: Optional[List[str]] = None,
        engines: Optional[List[str]] = None,
        use_llm_synthesis: bool = False,
        synthesis_model: Optional[str] = None,
    ) -> SROAnalysisResult:
        target_host = _host_of(target_url)
        brand_low = (brand_name or "").strip().lower()

        # Resolve provider list dynamically (never requires Gemini)
        requested_ids = engines or ["perplexity", "chatgpt", "gemini", "claude"]
        adapters = []
        seen_ids: set[str] = set()
        for eid in requested_ids:
            ad = get_adapter(eid)
            if ad is not None and ad.engine_id not in seen_ids:
                seen_ids.add(ad.engine_id)
                adapters.append(ad)
        for ad in get_available_adapters():
            if ad.engine_id not in seen_ids and getattr(ad, "supports_web_search", False):
                seen_ids.add(ad.engine_id)
                adapters.append(ad)

        discovered_competitor_urls: List[str] = []
        evidence_refs: List[Dict[str, Any]] = []

        async def _evaluate_provider(ad: Any) -> ProviderSelectionMetrics:
            channel = (
                "ai_search_grounding"
                if ad.engine_id == "gemini"
                else ("consumer_ui" if "consumer" in ad.engine_id or ad.engine_id == "google_ai_mode" else "ai_citation")
            )
            if not ad.is_configured():
                return ProviderSelectionMetrics(
                    provider_id=ad.engine_id,
                    provider_name=ad.display_name,
                    channel=channel,
                    status=SROStageStatus.NOT_CONFIGURED,
                )
            try:
                res = await ad.execute_prompt({"prompt": keyword, "market": country.upper(), "enable_search": True})
                if not res.is_live or res.error:
                    return ProviderSelectionMetrics(
                        provider_id=ad.engine_id,
                        provider_name=ad.display_name,
                        channel=channel,
                        status=SROStageStatus.FAILED,
                        error=res.error or f"HTTP {res.status_code}",
                    )
                cits = list(res.citations or [])
                matched_urls = [u for u in cits if _host_of(u) == target_host or _host_of(u).endswith(f".{target_host}")]
                domain_cited = bool(matched_urls)
                brand_mentioned = bool(brand_low and brand_low in (res.raw_content or "").lower()) if brand_low else None
                meta = res.tool_use_metadata or {}

                # Segment-level grounding attribution when provider supplies groundingSupports (e.g. Gemini)
                g_share_pct: Optional[float] = None
                t_words: Optional[int] = None
                tot_words: Optional[int] = None
                snippets: List[str] = []
                obs_queries = [str(q) for q in (meta.get("web_search_queries") or []) if q]

                chunks = meta.get("grounding_chunks") or []
                supports = meta.get("grounding_supports") or []
                if chunks or supports:
                    sr = compute_selection_rate(target_url, chunks, supports)
                    g_share_pct = sr["selection_rate_pct"]
                    t_words = sr["target_grounding_words"]
                    tot_words = sr["total_grounding_words"]
                    snippets = sr["target_snippets"][:5]
                    if sr["target_url_found"]:
                        domain_cited = True
                    for ch in chunks:
                        uri = ch.get("uri", "")
                        if uri and _host_of(uri) and _host_of(uri) != target_host and uri not in discovered_competitor_urls:
                            discovered_competitor_urls.append(uri)

                for u in cits:
                    if _host_of(u) and _host_of(u) != target_host and u not in discovered_competitor_urls:
                        discovered_competitor_urls.append(u)

                evidence_refs.append({
                    "provider_id": ad.engine_id,
                    "channel": channel,
                    "testing_mode": res.testing_mode.value if hasattr(res.testing_mode, "value") else str(res.testing_mode),
                    "model_version": res.model_version,
                    "queried_at": res.queried_at,
                    "citations_count": len(cits),
                })

                return ProviderSelectionMetrics(
                    provider_id=ad.engine_id,
                    provider_name=ad.display_name,
                    channel=channel,
                    status=SROStageStatus.COMPLETED,
                    testing_mode=res.testing_mode.value if hasattr(res.testing_mode, "value") else str(res.testing_mode),
                    domain_cited=domain_cited,
                    brand_mentioned=brand_mentioned,
                    source_included=domain_cited,
                    grounding_word_share_pct=g_share_pct,
                    target_grounding_words=t_words,
                    total_grounding_words=tot_words,
                    total_citations=len(cits),
                    cited_urls=cits[:15],
                    target_snippets=snippets,
                    observed_search_queries=obs_queries,
                )
            except Exception as exc:
                return ProviderSelectionMetrics(
                    provider_id=ad.engine_id,
                    provider_name=ad.display_name,
                    channel=channel,
                    status=SROStageStatus.FAILED,
                    error=str(exc)[:180],
                )

        provider_metrics = list(await asyncio.gather(*[_evaluate_provider(ad) for ad in adapters]))

        # Stage 1 & Stage 2 explicit status tracking
        grounding_providers = [m for m in provider_metrics if m.channel == "ai_search_grounding"]
        citation_providers = [m for m in provider_metrics if m.channel != "ai_search_grounding"]

        def _rollup_status(items: List[ProviderSelectionMetrics]) -> SROStageStatus:
            if not items:
                return SROStageStatus.NOT_CONFIGURED
            comp = sum(1 for x in items if x.status == SROStageStatus.COMPLETED)
            fail = sum(1 for x in items if x.status == SROStageStatus.FAILED)
            if comp == len(items):
                return SROStageStatus.COMPLETED
            if comp > 0:
                return SROStageStatus.PARTIAL
            if fail > 0:
                return SROStageStatus.FAILED
            return SROStageStatus.NOT_CONFIGURED

        completed_all = [m for m in provider_metrics if m.status == SROStageStatus.COMPLETED]
        selected_all = [m for m in completed_all if m.source_included or m.domain_cited]
        sample_size = len(completed_all)
        cross_platform_pct = round((len(selected_all) / sample_size) * 100.0, 1) if sample_size > 0 else None
        cross_platform_rate = round(len(selected_all) / sample_size, 4) if sample_size > 0 else None

        # Stage 3: Organic SERP channel (kept strictly separate from AI grounding)
        organic_serp = SROOrganicSerpChannel(status=SROStageStatus.NOT_CONFIGURED)

        # Stage 4: Target + top-3 competitor page extraction (SSRF-guarded)
        comp_urls = list(dict.fromkeys((competitor_urls or []) + discovered_competitor_urls))[:3]
        target_page = await fetch_page_snapshot(target_url)
        competitor_pages = list(await asyncio.gather(*[fetch_page_snapshot(u) for u in comp_urls])) if comp_urls else []
        page_stage_status = (
            SROStageStatus.FAILED
            if (target_page and target_page.error)
            else SROStageStatus.COMPLETED
        )

        # Stage 5: Synthesis (ModelRouter optional + schema-validated; never overwrites measured metrics)
        synth_mode = "deterministic"
        synth_model_used: Optional[str] = None
        synth_payload: Optional[SROSynthesisPayload] = None
        if use_llm_synthesis and sample_size > 0:
            llm_out = await _model_router_synthesis(
                target_url=target_url,
                keyword=keyword,
                provider_metrics=provider_metrics,
                target_page=target_page,
                competitor_pages=competitor_pages,
                synthesis_model=synthesis_model,
            )
            if llm_out is not None:
                synth_payload, synth_model_used = llm_out
                synth_mode = "model_router"

        if synth_payload is None:
            synth_payload = _deterministic_synthesis(
                target_url=target_url,
                keyword=keyword,
                provider_metrics=provider_metrics,
                cross_platform_pct=cross_platform_pct,
                target_page=target_page,
                competitor_pages=competitor_pages,
            )

        # Build backward-compatible grounding + platforms views from measured provider_metrics
        primary_g = next(
            (m for m in provider_metrics if m.status == SROStageStatus.COMPLETED and m.grounding_word_share_pct is not None),
            next((m for m in completed_all), None),
        )
        grounding_view = (
            SROGroundingAttribution(
                status="MEASURED",
                provider_id=primary_g.provider_id,
                target_url_found=primary_g.domain_cited,
                selection_rate=(
                    round(primary_g.grounding_word_share_pct / 100.0, 4)
                    if primary_g.grounding_word_share_pct is not None
                    else cross_platform_rate
                ),
                selection_rate_pct=(
                    primary_g.grounding_word_share_pct
                    if primary_g.grounding_word_share_pct is not None
                    else cross_platform_pct
                ),
                target_grounding_words=primary_g.target_grounding_words or 0,
                total_grounding_words=primary_g.total_grounding_words or 0,
                target_snippets=primary_g.target_snippets,
                web_search_queries=primary_g.observed_search_queries,
                sources_count=primary_g.total_citations,
            )
            if primary_g
            else SROGroundingAttribution(status="NOT_CONFIGURED")
        )

        platforms_view = [
            SROPlatformCitation(
                engine_id=m.provider_id,
                engine_name=m.provider_name,
                status=(
                    "CITED"
                    if (m.status == SROStageStatus.COMPLETED and m.domain_cited)
                    else ("NOT_CITED" if m.status == SROStageStatus.COMPLETED else m.status.value)
                ),
                target_url_cited=m.domain_cited,
                total_citations=m.total_citations,
                cited_urls=m.cited_urls,
                testing_mode=m.testing_mode,
                error=m.error,
            )
            for m in provider_metrics
        ]

        # Overall score is strictly derived from measured cross-platform evidence (never from LLM)
        overall_score = cross_platform_pct if sample_size > 0 else None
        confidence = round(min(0.95, 0.45 + 0.15 * sample_size), 2) if sample_size > 0 else None
        quality = (
            "COMPLETED"
            if sample_size >= 2
            else ("PARTIAL" if sample_size == 1 else "NOT_CONFIGURED")
        )

        stage_results = {
            "grounding": SROStageResult(
                stage="grounding",
                status=_rollup_status(grounding_providers),
                provider_used=grounding_providers[0].provider_id if grounding_providers else None,
                sample_size=sum(1 for x in grounding_providers if x.status == SROStageStatus.COMPLETED),
                note="Optional native search-grounding channel (not required for SRO).",
            ),
            "cross_platform_citations": SROStageResult(
                stage="cross_platform_citations",
                status=_rollup_status(citation_providers),
                sample_size=sum(1 for x in citation_providers if x.status == SROStageStatus.COMPLETED),
            ),
            "organic_serp": SROStageResult(
                stage="organic_serp",
                status=organic_serp.status,
                note=organic_serp.note,
            ),
            "page_extraction": SROStageResult(
                stage="page_extraction",
                status=page_stage_status,
                sample_size=(0 if target_page.error else 1) + sum(1 for c in competitor_pages if not c.error),
                error=target_page.error if target_page else None,
            ),
            "synthesis": SROStageResult(
                stage="synthesis",
                status=SROStageStatus.COMPLETED,
                provider_used=synth_model_used or "deterministic",
                note="AI synthesis produces recommendations only; measured metrics are immutable.",
            ),
        }

        return SROAnalysisResult(
            target_url=target_url,
            keyword=keyword,
            country=country.upper(),
            brand_name=brand_name,
            overall_score=overall_score,
            selection_rate=cross_platform_rate,
            cross_platform_selection_rate_pct=cross_platform_pct,
            sample_size=sample_size,
            confidence=confidence,
            data_quality_state=quality,
            stage_results=stage_results,
            provider_coverage={m.provider_id: m.status.value for m in provider_metrics},
            provider_metrics=provider_metrics,
            organic_serp=organic_serp,
            evidence_refs=evidence_refs,
            grounding=grounding_view,
            platforms=platforms_view,
            target_page=target_page,
            competitor_pages=competitor_pages,
            synthesis_mode=synth_mode,
            synthesis_model_used=synth_model_used,
            summary=synth_payload.summary,
            recommendations=synth_payload.recommendations,
            content_gaps=synth_payload.content_gaps,
            competitor_insights=synth_payload.competitor_insights,
        )


sro_engine = SROEngine()

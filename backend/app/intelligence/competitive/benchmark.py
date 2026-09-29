"""
Dristik AI Competitive Benchmarking Layer
Scrapes 2 competitor homepages using the identical CrawlerService pipeline,
evaluates 5-pillar scores under the same deterministic rubric, and computes
relative ranks, peer averages, competitive moats, and critical vulnerability gaps.
"""
import re
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from app.crawl.crawler import CrawlerService
from app.evidence.store import EvidenceStore
from app.domain.models import PageEvidence, CompetitorSeoParityMatrix, CompetitorSeoParityProfile

logger = logging.getLogger("dristik.competitive_benchmark")


class CompetitorPillarScores(BaseModel):
    search_seo: int = Field(..., ge=0, le=100)
    ai_search_geo: int = Field(..., ge=0, le=100)
    experience_sxo: int = Field(..., ge=0, le=100)
    conversion_cro: int = Field(..., ge=0, le=100)
    brand_trust: int = Field(..., ge=0, le=100)
    overall_score: int = Field(..., ge=0, le=100)


class CompetitorTechSpecs(BaseModel):
    status_code: int = 200
    ttfb_ms: float = 0.0
    word_count: int = 0
    h1_count: int = 0
    h1_text: Optional[str] = None
    has_meta_description: bool = False
    meta_description_len: int = 0
    schema_types: List[str] = Field(default_factory=list)
    schema_count: int = 0
    cta_count: int = 0
    primary_cta: Optional[str] = None
    has_viewport: bool = True
    dom_elements_count: int = 0
    is_https: bool = True


class PeerBenchmarkProfile(BaseModel):
    domain: str
    brand_name: str
    is_target: bool = False
    rank: int = 1
    scores: Optional[CompetitorPillarScores] = None
    specs: CompetitorTechSpecs
    crawl_status: str = "SUCCESS"  # SUCCESS | FAILED
    error_message: Optional[str] = None


class CompetitiveMoatItem(BaseModel):
    title: str
    pillar: str
    description: str
    advantage_delta: str  # e.g. "+340ms faster", "+3 richer schema types"


class CompetitiveGapItem(BaseModel):
    title: str
    pillar: str
    description: str
    winning_competitor: str
    recommendation: str


class CompetitiveBenchmarkResult(BaseModel):
    target_domain: str
    competitor_1_domain: str
    competitor_2_domain: str
    peers: List[PeerBenchmarkProfile] = Field(default_factory=list)
    target_overall_rank: int = 1
    peer_average_score: int = 0
    target_vs_peer_avg_delta: int = 0
    competitive_moats: List[CompetitiveMoatItem] = Field(default_factory=list)
    vulnerability_gaps: List[CompetitiveGapItem] = Field(default_factory=list)
    strategic_summary: str = ""


def _clean_domain(url: str) -> str:
    raw = (url or "").strip().lower()
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    return parsed.netloc.replace("www.", "").split(":")[0]


def _evaluate_page_to_pillar_scores(ev: PageEvidence, is_https: bool = True) -> CompetitorPillarScores:
    """
    Evaluates a scraped page across the 5 Website Intelligence Pillars
    using the identical objective deterministic criteria.
    """
    # 1. Search SEO (Crawlability, title, meta, H1)
    seo_score = 100
    if not ev.title or len(ev.title) < 15:
        seo_score -= 20
    elif len(ev.title) > 70:
        seo_score -= 10

    if not ev.meta_description:
        seo_score -= 25
    elif len(ev.meta_description) < 50:
        seo_score -= 10

    if not ev.h1:
        seo_score -= 20
    elif len(ev.h1) > 2:
        seo_score -= 10

    if not is_https:
        seo_score -= 25

    if ev.status_code != 200:
        seo_score -= 40
    seo_score = max(20, min(100, seo_score))

    # 2. AI Search (GEO) (Structured Schema, FAQ blocks, answer density)
    geo_score = 40  # baseline for typical text
    schema_types = ev.schema_types or []
    if len(schema_types) >= 3:
        geo_score += 35
    elif len(schema_types) >= 1:
        geo_score += 20

    if any(st.lower() in ("faqpage", "qapage") for st in schema_types):
        geo_score += 15

    if any(st.lower() in ("organization", "corporation") for st in schema_types):
        geo_score += 10

    if ev.word_count >= 600:
        geo_score += 10
    elif ev.word_count < 200:
        geo_score -= 15
    geo_score = max(20, min(100, geo_score))

    # 3. Experience (SXO) (TTFB latency, mobile viewport, DOM bloat)
    sxo_score = 100
    if ev.ttfb_ms > 1200:
        sxo_score -= 35
    elif ev.ttfb_ms > 600:
        sxo_score -= 20
    elif ev.ttfb_ms > 300:
        sxo_score -= 10

    if not ev.viewport:
        sxo_score -= 30

    if ev.dom_elements_count > 2500:
        sxo_score -= 15
    elif ev.dom_elements_count > 1500:
        sxo_score -= 8
    sxo_score = max(20, min(100, sxo_score))

    # 4. Conversion (CRO) (CTAs, clarity, friction)
    cro_score = 50
    ctas = ev.ctas or []
    if len(ctas) >= 2:
        cro_score += 30
    elif len(ctas) == 1:
        cro_score += 15
    else:
        cro_score -= 20

    if ev.word_count >= 400:
        cro_score += 15
    elif ev.word_count < 150:
        cro_score -= 15
    cro_score = max(20, min(100, cro_score))

    # 5. Brand & Trust (SSL, Schema, Social proof signals)
    trust_score = 60
    if is_https:
        trust_score += 20
    else:
        trust_score -= 30

    if any(st.lower() in ("organization", "brand") for st in schema_types):
        trust_score += 15

    if ev.total_images > 0:
        alt_ratio = (ev.total_images - ev.images_without_alt) / max(1, ev.total_images)
        if alt_ratio > 0.8:
            trust_score += 5
    trust_score = max(20, min(100, trust_score))

    # Overall weighted average
    overall = int(round(
        (seo_score * 0.25) +
        (geo_score * 0.25) +
        (sxo_score * 0.20) +
        (cro_score * 0.20) +
        (trust_score * 0.10)
    ))

    return CompetitorPillarScores(
        search_seo=seo_score,
        ai_search_geo=geo_score,
        experience_sxo=sxo_score,
        conversion_cro=cro_score,
        brand_trust=trust_score,
        overall_score=overall
    )


def _extract_tech_specs(ev: PageEvidence, is_https: bool = True) -> CompetitorTechSpecs:
    primary_cta = ev.ctas[0] if ev.ctas else None
    h1_text = ev.h1[0] if ev.h1 else None
    return CompetitorTechSpecs(
        status_code=ev.status_code,
        ttfb_ms=round(ev.ttfb_ms, 1),
        word_count=ev.word_count,
        h1_count=len(ev.h1),
        h1_text=h1_text,
        has_meta_description=bool(ev.meta_description),
        meta_description_len=len(ev.meta_description or ""),
        schema_types=ev.schema_types or [],
        schema_count=len(ev.schema_types or []),
        cta_count=len(ev.ctas or []),
        primary_cta=primary_cta,
        has_viewport=bool(ev.viewport),
        dom_elements_count=ev.dom_elements_count,
        is_https=is_https
    )


class CompetitorBenchmarkEngine:
    def __init__(self, crawler: Optional[CrawlerService] = None):
        self.crawler = crawler or CrawlerService()

    async def _crawl_competitor_homepage(self, raw_url: str) -> Tuple[Optional[PageEvidence], bool, Optional[str]]:
        """
        Crawls a single competitor homepage and returns (PageEvidence, is_https, error).
        """
        url = raw_url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        is_https = url.startswith("https://")
        clean_host = urlparse(url).netloc.replace("www.", "")
        evidence_store = EvidenceStore(run_id=f"comp_{clean_host or 'benchmark'}")

        try:
            manifest = await self.crawler.crawl_site_and_analyze(
                target_url=url,
                evidence_store=evidence_store,
                max_pages=1
            )
            if manifest.pages:
                return manifest.pages[0], is_https, None
            return None, is_https, "No page content returned from competitor domain."
        except Exception as exc:
            logger.warning(f"Error crawling competitor '{url}': {exc}")
            return None, is_https, str(exc)

    async def benchmark_two_competitors(
        self,
        target_domain: str,
        competitor_1_url: str,
        competitor_2_url: str,
        target_evidence: Optional[PageEvidence] = None,
        target_scores: Optional[CompetitorPillarScores] = None,
    ) -> CompetitiveBenchmarkResult:
        """
        Scrapes 2 competitor homepages with the identical pipeline and calculates
        side-by-side comparative scores, ranks, moats, and gaps.
        """
        clean_target = _clean_domain(target_domain)
        clean_comp1 = _clean_domain(competitor_1_url)
        clean_comp2 = _clean_domain(competitor_2_url)

        # 1. Resolve Target Profile
        target_error = None
        if target_evidence:
            target_specs = _extract_tech_specs(target_evidence, is_https=True)
            target_pillar_scores = target_scores or _evaluate_page_to_pillar_scores(target_evidence, is_https=True)
        else:
            t_ev, t_https, t_err = await self._crawl_competitor_homepage(clean_target)
            if t_ev:
                target_specs = _extract_tech_specs(t_ev, is_https=t_https)
                target_pillar_scores = _evaluate_page_to_pillar_scores(t_ev, is_https=t_https)
            else:
                target_specs = CompetitorTechSpecs(status_code=0, ttfb_ms=0.0, word_count=0, h1_count=0)
                target_pillar_scores = None
                target_error = t_err or "Homepage was not crawled"

        target_peer = PeerBenchmarkProfile(
            domain=clean_target,
            brand_name=clean_target.split(".")[0].capitalize(),
            is_target=True,
            scores=target_pillar_scores,
            specs=target_specs,
            crawl_status="SUCCESS" if target_pillar_scores is not None else "FAILED",
            error_message=target_error,
        )

        # 2. Concurrently crawl both competitor homepages
        (ev1, https1, err1), (ev2, https2, err2) = await asyncio.gather(
            self._crawl_competitor_homepage(clean_comp1),
            self._crawl_competitor_homepage(clean_comp2)
        )

        # Process Competitor 1
        if ev1:
            comp1_scores = _evaluate_page_to_pillar_scores(ev1, is_https=https1)
            comp1_specs = _extract_tech_specs(ev1, is_https=https1)
            peer1 = PeerBenchmarkProfile(
                domain=clean_comp1,
                brand_name=clean_comp1.split(".")[0].capitalize(),
                is_target=False,
                scores=comp1_scores,
                specs=comp1_specs,
                crawl_status="SUCCESS"
            )
        else:
            comp1_scores = None
            comp1_specs = CompetitorTechSpecs(status_code=0, ttfb_ms=0.0, word_count=0, h1_count=0)
            peer1 = PeerBenchmarkProfile(
                domain=clean_comp1,
                brand_name=clean_comp1.split(".")[0].capitalize(),
                is_target=False,
                scores=comp1_scores,
                specs=comp1_specs,
                crawl_status="FAILED",
                error_message=err1 or "Unreachable"
            )

        # Process Competitor 2
        if ev2:
            comp2_scores = _evaluate_page_to_pillar_scores(ev2, is_https=https2)
            comp2_specs = _extract_tech_specs(ev2, is_https=https2)
            peer2 = PeerBenchmarkProfile(
                domain=clean_comp2,
                brand_name=clean_comp2.split(".")[0].capitalize(),
                is_target=False,
                scores=comp2_scores,
                specs=comp2_specs,
                crawl_status="SUCCESS"
            )
        else:
            comp2_scores = None
            comp2_specs = CompetitorTechSpecs(status_code=0, ttfb_ms=0.0, word_count=0, h1_count=0)
            peer2 = PeerBenchmarkProfile(
                domain=clean_comp2,
                brand_name=clean_comp2.split(".")[0].capitalize(),
                is_target=False,
                scores=comp2_scores,
                specs=comp2_specs,
                crawl_status="FAILED",
                error_message=err2 or "Unreachable"
            )

        # 3. Rank only peers whose homepage was actually scored
        all_peers = [target_peer, peer1, peer2]
        measured = [p for p in all_peers if p.scores is not None]
        measured.sort(key=lambda p: p.scores.overall_score, reverse=True)
        for idx, p in enumerate(measured):
            p.rank = idx + 1

        target_overall_rank = target_peer.rank if target_peer.scores is not None else 0
        comp_scores_list = [p.scores.overall_score for p in (peer1, peer2) if p.scores is not None]
        peer_avg = int(round(sum(comp_scores_list) / len(comp_scores_list))) if comp_scores_list else 0
        target_delta_vs_avg = (
            target_peer.scores.overall_score - peer_avg
            if target_peer.scores is not None and comp_scores_list
            else 0
        )

        # 4. Identify Empirical Competitive Moats (Where Target leads both rivals)
        moats: List[CompetitiveMoatItem] = []

        crawled_peers = [p for p in (peer1, peer2) if p.crawl_status == "SUCCESS"]
        # TTFB Speed moat
        if (
            target_peer.crawl_status == "SUCCESS"
            and target_specs.ttfb_ms > 0
            and crawled_peers
            and all(target_specs.ttfb_ms < p.specs.ttfb_ms for p in crawled_peers)
        ):
            ms_diff = int(round(min(p.specs.ttfb_ms for p in crawled_peers) - target_specs.ttfb_ms))
            if ms_diff > 50:
                moats.append(CompetitiveMoatItem(
                    title="Faster Server Response Speed (TTFB)",
                    pillar="Website Experience (SXO)",
                    description=f"{target_peer.brand_name} delivers initial byte in {target_specs.ttfb_ms:.0f}ms, outperforming peers by {ms_diff}ms.",
                    advantage_delta=f"+{ms_diff}ms faster"
                ))

        # Schema Markup moat
        if crawled_peers and target_peer.crawl_status == "SUCCESS" and all(target_specs.schema_count > p.specs.schema_count for p in crawled_peers):
            moats.append(CompetitiveMoatItem(
                title="Richer Structured Schema Markup",
                pillar="AI Search Intelligence (GEO)",
                description=f"Target declares {target_specs.schema_count} Schema.org entities ({', '.join(target_specs.schema_types[:3])}), outclassing rivals in machine readability.",
                advantage_delta=f"+{target_specs.schema_count - max(p.specs.schema_count for p in crawled_peers)} entities"
            ))

        # Pillar specific moats
        scored_rivals = [p for p in crawled_peers if p.scores is not None]
        if target_pillar_scores is not None and scored_rivals and all(target_pillar_scores.search_seo > p.scores.search_seo for p in scored_rivals):
            diff = target_pillar_scores.search_seo - max(p.scores.search_seo for p in scored_rivals)
            moats.append(CompetitiveMoatItem(
                title="Superior Organic Search Foundation",
                pillar="Search (SEO)",
                description=f"Technical on-page structure scores {target_pillar_scores.search_seo}/100, surpassing nearest competitor by {diff} points.",
                advantage_delta=f"+{diff} pts"
            ))

        if target_pillar_scores is not None and scored_rivals and all(target_pillar_scores.conversion_cro > p.scores.conversion_cro for p in scored_rivals):
            diff = target_pillar_scores.conversion_cro - max(p.scores.conversion_cro for p in scored_rivals)
            moats.append(CompetitiveMoatItem(
                title="Higher Conversion Readiness",
                pillar="Conversion Intelligence (CRO)",
                description=f"Actionable CTAs and value proposition clarity score {target_pillar_scores.conversion_cro}/100 vs crawled peers.",
                advantage_delta=f"+{diff} pts"
            ))

        # 5. Identify Priority Vulnerability Gaps (Where rivals beat Target)
        gaps: List[CompetitiveGapItem] = []

        if crawled_peers and target_peer.crawl_status == "SUCCESS":
            word_leader = max(crawled_peers, key=lambda p: p.specs.word_count)
            if word_leader.specs.word_count > (target_specs.word_count + 250):
                gaps.append(CompetitiveGapItem(
                    title="Content Depth & Topical Authority Deficit",
                    pillar="Search (SEO)",
                    description=f"{word_leader.brand_name} publishes {word_leader.specs.word_count} words on the homepage vs {target_specs.word_count} on the target.",
                    winning_competitor=word_leader.brand_name,
                    recommendation="Expand the homepage only with claims that already exist on the site.",
                ))
            schema_leader = max(crawled_peers, key=lambda p: p.specs.schema_count)
            if schema_leader.specs.schema_count > target_specs.schema_count:
                gaps.append(CompetitiveGapItem(
                    title="Schema count is lower than a crawled rival",
                    pillar="AI Search Intelligence (GEO)",
                    description=f"{schema_leader.brand_name} has {schema_leader.specs.schema_count} schema types; this crawl found {target_specs.schema_count}.",
                    winning_competitor=schema_leader.brand_name,
                    recommendation="Add only schema types that match visible page content.",
                ))
            faster = [p for p in crawled_peers if p.specs.ttfb_ms > 0 and p.specs.ttfb_ms < target_specs.ttfb_ms]
            if target_specs.ttfb_ms > 600 and faster:
                fastest = min(faster, key=lambda p: p.specs.ttfb_ms)
                gaps.append(CompetitiveGapItem(
                    title="Server Response Latency Lag",
                    pillar="Website Experience (SXO)",
                    description=f"{fastest.brand_name} responded in {fastest.specs.ttfb_ms:.0f}ms; this crawl measured {target_specs.ttfb_ms:.0f}ms.",
                    winning_competitor=fastest.brand_name,
                    recommendation="Recheck TTFB on the same URL before treating one fetch as a ranking gap.",
                ))

        if target_peer.scores is None:
            summary = f"{target_peer.brand_name} was not scored. No comparison numbers were filled in."
        elif not measured or len(measured) == 1:
            summary = (
                f"{target_peer.brand_name} scored {target_peer.scores.overall_score}/100 from the pages that were crawled. "
                "Rivals without a successful crawl have no score."
            )
        elif target_overall_rank == 1:
            summary = (
                f"{target_peer.brand_name} leads the crawled set at {target_peer.scores.overall_score}/100 "
                f"({target_delta_vs_avg:+d} vs the crawled rival average)."
            )
        else:
            leader = measured[0]
            summary = (
                f"{target_peer.brand_name} is #{target_overall_rank} of {len(measured)} crawled sites "
                f"at {target_peer.scores.overall_score}/100. {leader.brand_name} is at {leader.scores.overall_score}/100."
            )

        return CompetitiveBenchmarkResult(
            target_domain=clean_target,
            competitor_1_domain=clean_comp1,
            competitor_2_domain=clean_comp2,
            peers=[target_peer, peer1, peer2],
            target_overall_rank=target_overall_rank,
            peer_average_score=peer_avg,
            target_vs_peer_avg_delta=target_delta_vs_avg,
            competitive_moats=moats,
            vulnerability_gaps=gaps,
            strategic_summary=summary
        )


competitor_benchmark_engine = CompetitorBenchmarkEngine()


def _compute_profile_metrics(pages: List[PageEvidence], domain: str, is_target: bool = False) -> CompetitorSeoParityProfile:
    if not pages:
        return CompetitorSeoParityProfile(
            domain=domain,
            brand_name=domain.split(".")[0].title(),
            is_target=is_target,
            pages_sampled=0,
            summary_verdict="No pages crawled."
        )
    total = len(pages)
    http_200_count = sum(1 for p in pages if p.status_code == 200)
    http_200_pct = round((http_200_count / total) * 100, 1)

    title_opt_count = sum(1 for p in pages if 45 <= len(p.title or "") <= 65 and getattr(p, "title_pixel_width", 500) <= 580)
    title_opt_pct = round((title_opt_count / total) * 100, 1)

    meta_opt_count = sum(1 for p in pages if 120 <= len(p.meta_description or "") <= 165 and getattr(p, "meta_pixel_width", 800) <= 960)
    meta_opt_pct = round((meta_opt_count / total) * 100, 1)

    h1_health_count = sum(1 for p in pages if len(p.h1) == 1)
    h1_health_pct = round((h1_health_count / total) * 100, 1)

    total_words = sum(p.word_count for p in pages)
    avg_words = int(round(total_words / total))

    unique_schemas = set(st for p in pages for st in (p.schema_types or []))
    has_bc = any("breadcrumb" in st.lower() for st in unique_schemas)

    total_ttfb = sum(p.ttfb_ms for p in pages)
    avg_ttfb = round(total_ttfb / total, 1)

    modern_imgs = 0
    total_imgs = 0
    for p in pages:
        for img in getattr(p, "image_assets", []):
            total_imgs += 1
            if img.get("is_modern_format"):
                modern_imgs += 1
    modern_img_pct = round((modern_imgs / max(1, total_imgs)) * 100, 1) if total_imgs > 0 else 60.0

    tech_score = int(round(max(20, min(100, (http_200_pct * 0.6) + (40 if avg_ttfb < 600 else 20)))))
    onpage_score = int(round(max(20, min(100, (title_opt_pct * 0.35) + (meta_opt_pct * 0.35) + (h1_health_pct * 0.30)))))
    depth_score = int(round(max(20, min(100, min(100.0, (avg_words / 600.0) * 100.0)))))
    schema_score = int(round(max(20, min(100, min(80.0, len(unique_schemas) * 20.0) + (20 if has_bc else 0)))))
    overall = int(round((tech_score * 0.30) + (onpage_score * 0.30) + (depth_score * 0.20) + (schema_score * 0.20)))

    return CompetitorSeoParityProfile(
        domain=domain,
        brand_name=domain.split(".")[0].title(),
        is_target=is_target,
        pages_sampled=total,
        technical_health_score=tech_score,
        onpage_score=onpage_score,
        content_depth_score=depth_score,
        schema_score=schema_score,
        overall_seo_score=overall,
        avg_ttfb_ms=avg_ttfb,
        http_200_rate_pct=http_200_pct,
        title_optimal_pct=title_opt_pct,
        meta_optimal_pct=meta_opt_pct,
        h1_health_pct=h1_health_pct,
        avg_word_count=avg_words,
        schema_types_count=len(unique_schemas),
        has_breadcrumbs=has_bc,
        modern_image_pct=modern_img_pct,
        summary_verdict=f"Overall SEO Parity: {overall}/100 based on {total} audited pages."
    )


def build_competitor_seo_parity_matrix(
    target_pages: List[PageEvidence],
    target_domain: str,
    competitors: Optional[List[str]] = None,
    competitor_pages_map: Optional[Dict[str, List[PageEvidence]]] = None
) -> CompetitorSeoParityMatrix:
    clean_target = _clean_domain(target_domain)
    target_profile = _compute_profile_metrics(target_pages, clean_target, is_target=True)

    profiles: List[CompetitorSeoParityProfile] = [target_profile]
    comp_map = competitor_pages_map or {}

    raw_comps = list(competitors or [])
    if not raw_comps and not comp_map:
        # Default placeholder peers if user didn't enter competitors
        raw_comps = []

    for c in raw_comps:
        c_dom = _clean_domain(c)
        if c_dom and c_dom != clean_target and not any(p.domain == c_dom for p in profiles):
            c_pages = comp_map.get(c_dom, [])
            c_prof = _compute_profile_metrics(c_pages, c_dom, is_target=False)
            profiles.append(c_prof)

    for c_dom, c_pages in comp_map.items():
        if c_dom != clean_target and not any(p.domain == c_dom for p in profiles):
            profiles.append(_compute_profile_metrics(c_pages, c_dom, is_target=False))

    # Calculate ranking
    sorted_profiles = sorted(profiles, key=lambda p: p.overall_seo_score, reverse=True)
    target_rank = 1
    for idx, p in enumerate(sorted_profiles):
        if p.is_target:
            target_rank = idx + 1
            break

    peer_profiles = [p for p in profiles if not p.is_target]
    peer_avg = int(round(sum(p.overall_seo_score for p in peer_profiles) / max(1, len(peer_profiles)))) if peer_profiles else target_profile.overall_seo_score

    advantages = []
    deficits = []

    if peer_profiles:
        avg_peer_ttfb = sum(p.avg_ttfb_ms for p in peer_profiles) / len(peer_profiles)
        if target_profile.avg_ttfb_ms > 0 and target_profile.avg_ttfb_ms < avg_peer_ttfb:
            advantages.append(f"Faster server response time ({target_profile.avg_ttfb_ms:.0f}ms vs peer avg {avg_peer_ttfb:.0f}ms)")
        elif target_profile.avg_ttfb_ms > avg_peer_ttfb + 200:
            deficits.append(f"Server response latency lag ({target_profile.avg_ttfb_ms:.0f}ms vs peer avg {avg_peer_ttfb:.0f}ms)")

        avg_peer_words = sum(p.avg_word_count for p in peer_profiles) / len(peer_profiles)
        if target_profile.avg_word_count > avg_peer_words:
            advantages.append(f"Superior content depth ({target_profile.avg_word_count} avg words vs peer avg {int(avg_peer_words)})")
        elif target_profile.avg_word_count < avg_peer_words - 150:
            deficits.append(f"Content volume deficit ({target_profile.avg_word_count} avg words vs peer avg {int(avg_peer_words)})")

        max_peer_schemas = max(p.schema_types_count for p in peer_profiles)
        if target_profile.schema_types_count > max_peer_schemas:
            advantages.append(f"Richer structured Schema.org data ({target_profile.schema_types_count} types vs max peer {max_peer_schemas})")
        elif target_profile.schema_types_count < max_peer_schemas:
            deficits.append(f"Schema coverage gap ({target_profile.schema_types_count} types vs rival {max_peer_schemas})")

    takeaway = (
        f"{target_profile.brand_name} ranks #{target_rank} of {len(profiles)} in technical SEO health "
        f"({target_profile.overall_seo_score}/100 vs peer avg {peer_avg}/100)."
    ) if peer_profiles else f"{target_profile.brand_name} technical SEO health is {target_profile.overall_seo_score}/100 (Competitive Benchmark: Pending Competitor Crawl)."

    return CompetitorSeoParityMatrix(
        target_domain=clean_target,
        competitors=profiles,
        target_rank=target_rank,
        peer_avg_seo_score=peer_avg,
        top_advantages=advantages,
        critical_deficits=deficits,
        strategic_takeaway=takeaway
    )


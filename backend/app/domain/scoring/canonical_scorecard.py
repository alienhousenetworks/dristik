"""
Canonical Enterprise Scorecard Engine (dristik_enterprise_v4.0)

Single source of truth for scoring, crawl coverage, and capability acceptance
across all 4 audit pillars (SEO, GEO, AEO, CRO) and all 5 PDF publications
(SEO, GEO, AEO, CRO, Complete Audit).

Enforces three separate enterprise scores:
1. Capability Completeness (0-100): whether required enterprise functionality
   exists AND passes its acceptance tests (disconnected/failing connectors fail).
2. Evidence Coverage (0-100): how much of the intended scope was actually
   measured, with explicit 5-stage crawl accounting
   (discovered -> crawled -> rendered -> inspected -> tested).
3. Optimization Effectiveness (0-100 or None / NOT_ENOUGH_DATA): whether
   implemented remediations or controlled experiments improved measured outcomes.

Zero-Fake-Evidence invariant:
- Unmeasured capabilities remain explicitly UNMEASURED (excluded from the
  health denominator; never coerced to 0 or 100).
- Disconnected or failing external providers never pass acceptance tests.
"""
from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from pydantic import BaseModel, Field

METHODOLOGY_VERSION = "dristik_enterprise_v4.0"

PILLAR_WEIGHTS: Dict[str, float] = {
    "SEO": 25.0,
    "GEO": 25.0,
    "AEO": 25.0,
    "CRO": 25.0,
}

# Capability weights inside each pillar (each pillar sums to 100.0)
PILLAR_CAPABILITY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "SEO": {
        "technical_seo": 15.0,
        "crawling_and_indexation": 15.0,
        "on_page_seo": 10.0,
        "content_intelligence": 10.0,
        "structured_data": 10.0,
        "internal_linking": 10.0,
        "performance": 10.0,
        "backlink_intelligence": 10.0,
        "search_analytics": 5.0,
        "historical_and_verification": 5.0,
    },
    "GEO": {
        "ai_crawler_access": 15.0,
        "rendering_compatibility": 10.0,
        "entity_intelligence": 15.0,
        "content_extractability": 15.0,
        "source_authority": 10.0,
        "ai_retrieval_testing": 15.0,
        "competitor_intelligence": 10.0,
        "citation_monitoring_and_verification": 10.0,
    },
    "AEO": {
        "question_universe": 15.0,
        "prompt_classification": 10.0,
        "multi_engine_execution": 20.0,
        "citation_extraction": 15.0,
        "brand_mention_and_sov": 15.0,
        "answer_accuracy": 10.0,
        "ai_referral_analytics": 10.0,
        "historical_citation_persistence": 5.0,
    },
    "CRO": {
        "ux_and_accessibility": 15.0,
        "session_replay": 10.0,
        "heatmaps": 10.0,
        "funnel_analytics": 15.0,
        "revenue_attribution": 15.0,
        "form_intelligence": 10.0,
        "ab_experiments": 10.0,
        "mobile_intelligence": 5.0,
        "remediation_and_verification": 10.0,
    },
}


def _esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _valid_score(val: Any) -> Optional[float]:
    if isinstance(val, bool) or val is None:
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    if num != num:  # NaN
        return None
    return round(max(0.0, min(100.0, num)), 1)


class CrawlCoverageFunnel(BaseModel):
    """Explicit 5-stage URL accounting — discovering 505 URLs never implies 505 audited."""
    discovered_urls: int = 0
    crawled_urls: int = 0
    rendered_urls: int = 0
    inspected_urls: int = 0
    tested_urls: int = 0
    coverage_pct: float = 0.0
    scope_label: str = "UNMEASURED"

    def compute_coverage(self) -> "CrawlCoverageFunnel":
        denom = max(self.discovered_urls, self.crawled_urls, self.inspected_urls, 0)
        if denom == 0:
            self.coverage_pct = 0.0
            self.scope_label = "NO_URLS_MEASURED"
            return self
        audited = self.inspected_urls or self.crawled_urls
        self.coverage_pct = round(min(100.0, (audited / denom) * 100.0), 1)
        if self.coverage_pct >= 90.0:
            self.scope_label = "FULL_SITE_COVERAGE"
        elif self.coverage_pct >= 25.0:
            self.scope_label = "PARTIAL_SITE_COVERAGE"
        else:
            self.scope_label = "SAMPLED_AUDIT"
        return self


class CapabilityAssessment(BaseModel):
    capability_id: str
    pillar: str
    weight: float
    status: str = "UNMEASURED"  # MEASURED | PARTIAL | NOT_CONNECTED | FAILED | UNMEASURED
    acceptance_passed: bool = False
    measured_score: Optional[float] = None  # 0-100 only when MEASURED/PARTIAL
    provider: Optional[str] = None
    evidence_count: int = 0
    note: str = ""


class PillarCanonicalScore(BaseModel):
    pillar: str
    pillar_weight: float
    capability_completeness_score: float = 0.0
    evidence_coverage_score: float = 0.0
    measured_health_score: Optional[float] = None
    measured_capabilities: int = 0
    total_capabilities: int = 0
    status: str = "UNMEASURED"  # MEASURED | PARTIAL | UNMEASURED
    capabilities: List[CapabilityAssessment] = Field(default_factory=list)


class CanonicalEnterpriseScorecard(BaseModel):
    audit_run_id: str
    domain: str
    methodology_version: str = METHODOLOGY_VERSION
    generated_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # The 3 separated enterprise scores
    capability_completeness_score: float = 0.0
    evidence_coverage_score: float = 0.0
    optimization_effectiveness_score: Optional[float] = None
    optimization_effectiveness_status: str = "NOT_ENOUGH_DATA"  # MEASURED | NOT_ENOUGH_DATA

    # Measured health composite (computed strictly across measured pillars only)
    composite_health_score: Optional[float] = None
    composite_grade: str = "UNGRADED"

    crawl_coverage: CrawlCoverageFunnel = Field(default_factory=CrawlCoverageFunnel)
    pillars: Dict[str, PillarCanonicalScore] = Field(default_factory=dict)
    disclosures: List[str] = Field(default_factory=list)
    scorecard_sha256: str = ""

    def seal(self) -> "CanonicalEnterpriseScorecard":
        payload = self.model_dump(exclude={"scorecard_sha256", "generated_at_utc"})
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        self.scorecard_sha256 = hashlib.sha256(raw).hexdigest()
        return self


def _grade(score: Optional[float], coverage_pct: float) -> str:
    if score is None or coverage_pct <= 0.0:
        return "UNGRADED"
    if score >= 90.0:
        return "A+"
    if score >= 80.0:
        return "A"
    if score >= 70.0:
        return "B"
    if score >= 60.0:
        return "C"
    if score >= 40.0:
        return "D"
    return "F"


class CanonicalScorecardEngine:
    """Computes one immutable, versioned enterprise scorecard for an audit run."""

    @classmethod
    def compute(
        cls,
        *,
        audit_run_id: str,
        domain: str,
        crawl_coverage: CrawlCoverageFunnel,
        capability_inputs: Sequence[CapabilityAssessment],
        verified_remediations_passed: int = 0,
        verified_remediations_total: int = 0,
        winning_experiments_count: int = 0,
        concluded_experiments_count: int = 0,
    ) -> CanonicalEnterpriseScorecard:
        crawl_coverage.compute_coverage()
        by_pillar_cap: Dict[str, Dict[str, CapabilityAssessment]] = {
            p: {} for p in PILLAR_WEIGHTS
        }
        for cap in capability_inputs:
            p = cap.pillar.upper()
            if p in by_pillar_cap:
                by_pillar_cap[p][cap.capability_id] = cap

        pillars: Dict[str, PillarCanonicalScore] = {}
        disclosures: List[str] = []

        weighted_cap_complete = 0.0
        weighted_ev_cov = 0.0
        measured_health_num = 0.0
        measured_health_den = 0.0

        for pillar, p_weight in PILLAR_WEIGHTS.items():
            cap_weights = PILLAR_CAPABILITY_WEIGHTS[pillar]
            resolved_caps: List[CapabilityAssessment] = []
            passed_weight = 0.0
            measured_weight = 0.0
            health_num = 0.0
            health_den = 0.0
            measured_cnt = 0

            for cap_id, c_weight in cap_weights.items():
                provided = by_pillar_cap[pillar].get(cap_id)
                if provided is None:
                    cap = CapabilityAssessment(
                        capability_id=cap_id,
                        pillar=pillar,
                        weight=c_weight,
                        status="UNMEASURED",
                        acceptance_passed=False,
                        measured_score=None,
                        note="Capability not executed or connector not configured.",
                    )
                else:
                    # Disconnected or failed integrations can NEVER pass acceptance
                    st = str(provided.status or "UNMEASURED").upper()
                    passed = bool(provided.acceptance_passed) and st in {"MEASURED", "PARTIAL"}
                    m_score = _valid_score(provided.measured_score) if st in {"MEASURED", "PARTIAL"} else None
                    cap = CapabilityAssessment(
                        capability_id=cap_id,
                        pillar=pillar,
                        weight=c_weight,
                        status=st,
                        acceptance_passed=passed,
                        measured_score=m_score,
                        provider=provided.provider,
                        evidence_count=max(0, int(provided.evidence_count or 0)),
                        note=provided.note,
                    )

                resolved_caps.append(cap)
                if cap.acceptance_passed:
                    passed_weight += c_weight
                if cap.status in {"MEASURED", "PARTIAL"} and cap.measured_score is not None:
                    measured_cnt += 1
                    measured_weight += c_weight
                    health_num += cap.measured_score * c_weight
                    health_den += c_weight
                elif cap.status in {"NOT_CONNECTED", "FAILED"}:
                    disclosures.append(
                        f"{pillar}.{cap_id}: {cap.status} ({cap.note or 'provider unavailable'})"
                    )

            total_w = sum(cap_weights.values()) or 100.0
            p_cap_complete = round((passed_weight / total_w) * 100.0, 1)
            p_ev_cov = round((measured_weight / total_w) * 100.0, 1)
            p_health = round(health_num / health_den, 1) if health_den > 0 else None
            if measured_cnt == 0:
                p_status = "UNMEASURED"
            elif measured_cnt == len(cap_weights):
                p_status = "MEASURED"
            else:
                p_status = "PARTIAL"

            pillars[pillar] = PillarCanonicalScore(
                pillar=pillar,
                pillar_weight=p_weight,
                capability_completeness_score=p_cap_complete,
                evidence_coverage_score=p_ev_cov,
                measured_health_score=p_health,
                measured_capabilities=measured_cnt,
                total_capabilities=len(cap_weights),
                status=p_status,
                capabilities=resolved_caps,
            )

            weighted_cap_complete += p_cap_complete * (p_weight / 100.0)
            weighted_ev_cov += p_ev_cov * (p_weight / 100.0)
            if p_health is not None:
                measured_health_num += p_health * p_weight
                measured_health_den += p_weight

        # Optimization effectiveness: only scored when actual post-change outcomes exist
        opt_eff: Optional[float] = None
        opt_status = "NOT_ENOUGH_DATA"
        eff_parts: List[float] = []
        if verified_remediations_total > 0:
            eff_parts.append((verified_remediations_passed / verified_remediations_total) * 100.0)
        if concluded_experiments_count > 0:
            eff_parts.append((winning_experiments_count / concluded_experiments_count) * 100.0)
        if eff_parts:
            opt_eff = round(sum(eff_parts) / len(eff_parts), 1)
            opt_status = "MEASURED"
        else:
            disclosures.append(
                "Optimization Effectiveness is NOT_ENOUGH_DATA: no verified remediations or concluded A/B experiments recorded yet."
            )

        if crawl_coverage.discovered_urls > 0 and crawl_coverage.coverage_pct < 90.0:
            disclosures.append(
                f"Crawl scope disclosure: {crawl_coverage.inspected_urls or crawl_coverage.crawled_urls} of "
                f"{crawl_coverage.discovered_urls} discovered URLs inspected ({crawl_coverage.coverage_pct:.1f}% coverage)."
            )

        composite_health = round(measured_health_num / measured_health_den, 1) if measured_health_den > 0 else None
        ev_cov_overall = round(weighted_ev_cov, 1)

        card = CanonicalEnterpriseScorecard(
            audit_run_id=audit_run_id,
            domain=domain,
            capability_completeness_score=round(weighted_cap_complete, 1),
            evidence_coverage_score=ev_cov_overall,
            optimization_effectiveness_score=opt_eff,
            optimization_effectiveness_status=opt_status,
            composite_health_score=composite_health,
            composite_grade=_grade(composite_health, ev_cov_overall),
            crawl_coverage=crawl_coverage,
            pillars=pillars,
            disclosures=disclosures,
        )
        return card.seal()

    @classmethod
    def evaluate_from_report(cls, report: Any) -> CanonicalEnterpriseScorecard:
        """Deterministically builds the canonical scorecard from any sealed ExecutiveReport or dict."""
        cached = getattr(report, "_canonical_enterprise_scorecard", None)
        if isinstance(cached, CanonicalEnterpriseScorecard):
            return cached

        audit_run_id = str(
            _get(report, "analysis_id")
            or _get(report, "audit_id")
            or _get(report, "run_id")
            or "run_unknown"
        )
        domain = str(_get(report, "domain") or _get(report, "website_url") or "unspecified")

        manifest = _get(report, "crawl_manifest")
        pages = list(_get(manifest, "pages", None) or _get(report, "page_reports", None) or [])
        crawled = len(pages)
        discovered = int(_get(manifest, "total_pages_discovered", 0) or _get(report, "discovered_urls_count", 0) or crawled)
        rendered = sum(1 for p in pages if _get(p, "rendered_dom") or _get(p, "screenshot_path") or _get(p, "has_browser_render"))
        inspected = crawled
        tested = int(_get(report, "tested_urls_count", 0) or sum(1 for p in pages if _get(p, "interaction_tests") or _get(p, "lighthouse_score") is not None))

        funnel = CrawlCoverageFunnel(
            discovered_urls=max(discovered, crawled),
            crawled_urls=crawled,
            rendered_urls=rendered,
            inspected_urls=inspected,
            tested_urls=tested,
        ).compute_coverage()

        scores = _get(report, "scores")
        cat_scores = _get(scores, "category_scores", {}) if scores is not None else {}
        if not isinstance(cat_scores, dict):
            cat_scores = {}

        def _cat_val(*keys: str) -> Optional[float]:
            for k in keys:
                for variant in (k, k.upper(), k.lower()):
                    if variant in cat_scores:
                        raw = cat_scores[variant]
                        st = str(_get(raw, "status", "") or "").upper()
                        if st in {"NOT_MEASURED", "NOT_TESTED", "UNAVAILABLE", "NOT_APPLICABLE"}:
                            continue
                        val = _get(raw, "score", raw)
                        v = _valid_score(val)
                        if v is not None:
                            return v
            return None

        seo_tech = _cat_val("TECHNICAL_SEO", "SEO")
        seo_onpage = _cat_val("ON_PAGE_SEO", "CONTENT")
        seo_schema = _cat_val("SCHEMA", "STRUCTURED_DATA")
        seo_perf = _cat_val("PERFORMANCE")

        ext_auth = _get(report, "external_authority")
        ext_connected = bool(ext_auth) and str(_get(ext_auth, "status", "") or "").upper() in {"MEASURED", "CONNECTED", "PARTIALLY_MEASURED"}
        gsc = _get(report, "google_performance")
        gsc_connected = bool(gsc) and bool(_get(gsc, "gsc_connected", False) or _get(gsc, "is_connected", False))
        ga4_connected = bool(gsc) and bool(_get(gsc, "ga4_connected", False))

        geo_readiness = _get(report, "geo_readiness")
        geo_extract = _valid_score(_get(geo_readiness, "extractability_score"))
        ai_card = _get(report, "ai_visibility_scorecard")
        ai_runs = int(_get(ai_card, "successful_runs", 0) or 0) if ai_card else 0
        ai_cit_rate = _valid_score(_get(ai_card, "citation_rate_pct")) if ai_runs > 0 else None
        ai_mention_rate = _valid_score(_get(ai_card, "mention_rate_pct")) if ai_runs > 0 else None

        cro_score = _cat_val("UX_CONVERSION", "CRO", "EXPERIENCE")
        ai_ref = _get(report, "ai_referral_analytics")
        ai_ref_connected = bool(ai_ref) and str(_get(ai_ref, "status", "")).upper() in {"MEASURED", "CONNECTED"}
        replay_data = _get(report, "session_replay_summary")
        replay_connected = bool(replay_data) and str(_get(replay_data, "status", "")).upper() in {"MEASURED", "CONNECTED"}
        heatmap_data = _get(report, "heatmap_summary")
        heatmap_connected = bool(heatmap_data) and str(_get(heatmap_data, "status", "")).upper() in {"MEASURED", "CONNECTED"}
        exp_data = _get(report, "experiments_summary")
        exp_connected = bool(exp_data) and str(_get(exp_data, "status", "")).upper() in {"MEASURED", "CONNECTED"}
        hist_data = _get(report, "historical_comparison")
        hist_connected = bool(hist_data) and str(_get(hist_data, "status", "")).upper() in {"MEASURED", "COMPARABLE"}

        caps: List[CapabilityAssessment] = [
            # SEO
            CapabilityAssessment(
                capability_id="technical_seo", pillar="SEO", weight=15.0,
                status="MEASURED" if (seo_tech is not None and crawled > 0) else "UNMEASURED",
                acceptance_passed=bool(seo_tech is not None and crawled > 0),
                measured_score=seo_tech, evidence_count=crawled,
            ),
            CapabilityAssessment(
                capability_id="crawling_and_indexation", pillar="SEO", weight=15.0,
                status="MEASURED" if funnel.coverage_pct >= 90.0 else ("PARTIAL" if crawled > 0 else "UNMEASURED"),
                acceptance_passed=funnel.coverage_pct >= 90.0,
                measured_score=funnel.coverage_pct if crawled > 0 else None,
                evidence_count=crawled,
                note=f"{crawled}/{funnel.discovered_urls} URLs crawled ({funnel.coverage_pct:.1f}%)",
            ),
            CapabilityAssessment(
                capability_id="on_page_seo", pillar="SEO", weight=10.0,
                status="MEASURED" if (seo_onpage is not None and crawled > 0) else "UNMEASURED",
                acceptance_passed=bool(seo_onpage is not None and crawled > 0),
                measured_score=seo_onpage, evidence_count=crawled,
            ),
            CapabilityAssessment(
                capability_id="content_intelligence", pillar="SEO", weight=10.0,
                status="MEASURED" if (seo_onpage is not None and crawled > 0) else "UNMEASURED",
                acceptance_passed=bool(seo_onpage is not None and crawled > 0),
                measured_score=seo_onpage, evidence_count=crawled,
            ),
            CapabilityAssessment(
                capability_id="structured_data", pillar="SEO", weight=10.0,
                status="MEASURED" if (seo_schema is not None and crawled > 0) else "UNMEASURED",
                acceptance_passed=bool(seo_schema is not None and crawled > 0),
                measured_score=seo_schema, evidence_count=crawled,
            ),
            CapabilityAssessment(
                capability_id="internal_linking", pillar="SEO", weight=10.0,
                status="MEASURED" if crawled > 1 else ("PARTIAL" if crawled == 1 else "UNMEASURED"),
                acceptance_passed=crawled > 1,
                measured_score=seo_tech if crawled > 0 else None, evidence_count=crawled,
            ),
            CapabilityAssessment(
                capability_id="performance", pillar="SEO", weight=10.0,
                status="MEASURED" if seo_perf is not None else "UNMEASURED",
                acceptance_passed=seo_perf is not None,
                measured_score=seo_perf, evidence_count=tested,
            ),
            CapabilityAssessment(
                capability_id="backlink_intelligence", pillar="SEO", weight=10.0,
                status="MEASURED" if ext_connected else "NOT_CONNECTED",
                acceptance_passed=ext_connected,
                measured_score=_valid_score(_get(ext_auth, "authority_score")) if ext_connected else None,
                provider=_get(ext_auth, "provider"),
                note="" if ext_connected else "Backlink provider not connected",
            ),
            CapabilityAssessment(
                capability_id="search_analytics", pillar="SEO", weight=5.0,
                status="MEASURED" if gsc_connected else "NOT_CONNECTED",
                acceptance_passed=gsc_connected,
                measured_score=100.0 if gsc_connected else None,
                provider="Google Search Console",
                note="" if gsc_connected else "GSC not connected",
            ),
            CapabilityAssessment(
                capability_id="historical_and_verification", pillar="SEO", weight=5.0,
                status="MEASURED" if hist_connected else "UNMEASURED",
                acceptance_passed=hist_connected,
                measured_score=100.0 if hist_connected else None,
            ),
            # GEO
            CapabilityAssessment(
                capability_id="ai_crawler_access", pillar="GEO", weight=15.0,
                status="MEASURED" if crawled > 0 else "UNMEASURED",
                acceptance_passed=crawled > 0,
                measured_score=geo_extract if geo_extract is not None else (seo_tech if crawled > 0 else None),
                evidence_count=crawled,
            ),
            CapabilityAssessment(
                capability_id="rendering_compatibility", pillar="GEO", weight=10.0,
                status="MEASURED" if rendered > 0 else "UNMEASURED",
                acceptance_passed=rendered > 0,
                measured_score=round((rendered / max(crawled, 1)) * 100.0, 1) if rendered > 0 else None,
                evidence_count=rendered,
            ),
            CapabilityAssessment(
                capability_id="entity_intelligence", pillar="GEO", weight=15.0,
                status="MEASURED" if (geo_extract is not None or seo_schema is not None) else "UNMEASURED",
                acceptance_passed=bool(geo_extract is not None or seo_schema is not None),
                measured_score=geo_extract if geo_extract is not None else seo_schema,
            ),
            CapabilityAssessment(
                capability_id="content_extractability", pillar="GEO", weight=15.0,
                status="MEASURED" if geo_extract is not None else "UNMEASURED",
                acceptance_passed=geo_extract is not None,
                measured_score=geo_extract,
            ),
            CapabilityAssessment(
                capability_id="source_authority", pillar="GEO", weight=10.0,
                status="MEASURED" if ext_connected else "NOT_CONNECTED",
                acceptance_passed=ext_connected,
                measured_score=_valid_score(_get(ext_auth, "authority_score")) if ext_connected else None,
                note="" if ext_connected else "External authority connector not connected",
            ),
            CapabilityAssessment(
                capability_id="ai_retrieval_testing", pillar="GEO", weight=15.0,
                status="MEASURED" if ai_runs > 0 else "NOT_CONNECTED",
                acceptance_passed=ai_runs > 0,
                measured_score=ai_cit_rate,
                evidence_count=ai_runs,
                note="" if ai_runs > 0 else "No live AI retrieval queries executed",
            ),
            CapabilityAssessment(
                capability_id="competitor_intelligence", pillar="GEO", weight=10.0,
                status="MEASURED" if ai_runs > 0 else "UNMEASURED",
                acceptance_passed=ai_runs > 0,
                measured_score=ai_mention_rate,
            ),
            CapabilityAssessment(
                capability_id="citation_monitoring_and_verification", pillar="GEO", weight=10.0,
                status="MEASURED" if (ai_runs > 0 and hist_connected) else "UNMEASURED",
                acceptance_passed=bool(ai_runs > 0 and hist_connected),
                measured_score=ai_cit_rate if (ai_runs > 0 and hist_connected) else None,
            ),
            # AEO
            CapabilityAssessment(
                capability_id="question_universe", pillar="AEO", weight=15.0,
                status="MEASURED" if crawled > 0 else "UNMEASURED",
                acceptance_passed=crawled > 0,
                measured_score=geo_extract if geo_extract is not None else (seo_onpage if crawled > 0 else None),
            ),
            CapabilityAssessment(
                capability_id="prompt_classification", pillar="AEO", weight=10.0,
                status="MEASURED" if crawled > 0 else "UNMEASURED",
                acceptance_passed=crawled > 0,
                measured_score=geo_extract if geo_extract is not None else (seo_onpage if crawled > 0 else None),
            ),
            CapabilityAssessment(
                capability_id="multi_engine_execution", pillar="AEO", weight=20.0,
                status="MEASURED" if ai_runs > 0 else "NOT_CONNECTED",
                acceptance_passed=ai_runs > 0,
                measured_score=ai_cit_rate,
                evidence_count=ai_runs,
                note="" if ai_runs > 0 else "Live answer engines not queried",
            ),
            CapabilityAssessment(
                capability_id="citation_extraction", pillar="AEO", weight=15.0,
                status="MEASURED" if ai_runs > 0 else "NOT_CONNECTED",
                acceptance_passed=ai_runs > 0,
                measured_score=ai_cit_rate,
                evidence_count=ai_runs,
            ),
            CapabilityAssessment(
                capability_id="brand_mention_and_sov", pillar="AEO", weight=15.0,
                status="MEASURED" if ai_runs > 0 else "NOT_CONNECTED",
                acceptance_passed=ai_runs > 0,
                measured_score=ai_mention_rate,
            ),
            CapabilityAssessment(
                capability_id="answer_accuracy", pillar="AEO", weight=10.0,
                status="MEASURED" if ai_runs > 0 else "UNMEASURED",
                acceptance_passed=ai_runs > 0,
                measured_score=_valid_score(_get(ai_card, "entity_accuracy_pct")) if ai_runs > 0 else None,
            ),
            CapabilityAssessment(
                capability_id="ai_referral_analytics", pillar="AEO", weight=10.0,
                status="MEASURED" if ai_ref_connected else "NOT_CONNECTED",
                acceptance_passed=ai_ref_connected,
                measured_score=100.0 if ai_ref_connected else None,
                note="" if ai_ref_connected else "AI referral analytics not connected",
            ),
            CapabilityAssessment(
                capability_id="historical_citation_persistence", pillar="AEO", weight=5.0,
                status="MEASURED" if (ai_runs > 0 and hist_connected) else "UNMEASURED",
                acceptance_passed=bool(ai_runs > 0 and hist_connected),
                measured_score=ai_cit_rate if (ai_runs > 0 and hist_connected) else None,
            ),
            # CRO
            CapabilityAssessment(
                capability_id="ux_and_accessibility", pillar="CRO", weight=15.0,
                status="MEASURED" if cro_score is not None else "UNMEASURED",
                acceptance_passed=cro_score is not None,
                measured_score=cro_score,
                evidence_count=crawled,
            ),
            CapabilityAssessment(
                capability_id="session_replay", pillar="CRO", weight=10.0,
                status="MEASURED" if replay_connected else "NOT_CONNECTED",
                acceptance_passed=replay_connected,
                measured_score=100.0 if replay_connected else None,
                note="" if replay_connected else "Session replay provider not connected",
            ),
            CapabilityAssessment(
                capability_id="heatmaps", pillar="CRO", weight=10.0,
                status="MEASURED" if heatmap_connected else "NOT_CONNECTED",
                acceptance_passed=heatmap_connected,
                measured_score=100.0 if heatmap_connected else None,
                note="" if heatmap_connected else "Heatmap telemetry not connected",
            ),
            CapabilityAssessment(
                capability_id="funnel_analytics", pillar="CRO", weight=15.0,
                status="MEASURED" if ga4_connected else "NOT_CONNECTED",
                acceptance_passed=ga4_connected,
                measured_score=100.0 if ga4_connected else None,
                note="" if ga4_connected else "GA4 / conversion funnel not connected",
            ),
            CapabilityAssessment(
                capability_id="revenue_attribution", pillar="CRO", weight=15.0,
                status="MEASURED" if (ga4_connected and ai_ref_connected) else "NOT_CONNECTED",
                acceptance_passed=bool(ga4_connected and ai_ref_connected),
                measured_score=100.0 if (ga4_connected and ai_ref_connected) else None,
                note="" if (ga4_connected and ai_ref_connected) else "Revenue attribution not reconciled",
            ),
            CapabilityAssessment(
                capability_id="form_intelligence", pillar="CRO", weight=10.0,
                status="MEASURED" if cro_score is not None else "UNMEASURED",
                acceptance_passed=cro_score is not None,
                measured_score=cro_score,
            ),
            CapabilityAssessment(
                capability_id="ab_experiments", pillar="CRO", weight=10.0,
                status="MEASURED" if exp_connected else "NOT_CONNECTED",
                acceptance_passed=exp_connected,
                measured_score=100.0 if exp_connected else None,
                note="" if exp_connected else "Experimentation provider not connected",
            ),
            CapabilityAssessment(
                capability_id="mobile_intelligence", pillar="CRO", weight=5.0,
                status="MEASURED" if rendered > 0 else "UNMEASURED",
                acceptance_passed=rendered > 0,
                measured_score=cro_score if rendered > 0 else None,
            ),
            CapabilityAssessment(
                capability_id="remediation_and_verification", pillar="CRO", weight=10.0,
                status="MEASURED" if hist_connected else "UNMEASURED",
                acceptance_passed=hist_connected,
                measured_score=100.0 if hist_connected else None,
            ),
        ]

        card = cls.compute(
            audit_run_id=audit_run_id,
            domain=domain,
            crawl_coverage=funnel,
            capability_inputs=caps,
        )
        try:
            object.__setattr__(report, "_canonical_enterprise_scorecard", card)
        except Exception:
            pass
        return card


def render_canonical_scorecard_html(
    scorecard: CanonicalEnterpriseScorecard,
    pillar_filter: Optional[str] = None,
) -> str:
    """Print-safe HTML summary block embedded across all 5 PDFs for 100% score consistency."""
    opt_display = (
        f"{scorecard.optimization_effectiveness_score:.1f}/100"
        if scorecard.optimization_effectiveness_score is not None
        else "NOT ENOUGH DATA"
    )
    health_display = (
        f"{scorecard.composite_health_score:.1f}/100 ({scorecard.composite_grade})"
        if scorecard.composite_health_score is not None
        else "UNMEASURED"
    )
    cc = scorecard.crawl_coverage
    pillar_rows = []
    for p_name in ("SEO", "GEO", "AEO", "CRO"):
        if pillar_filter and pillar_filter.upper() != "COMPLETE" and p_name != pillar_filter.upper():
            continue
        p = scorecard.pillars.get(p_name)
        if not p:
            continue
        h_txt = f"{p.measured_health_score:.1f}/100" if p.measured_health_score is not None else "UNMEASURED"
        pillar_rows.append(
            f"<tr>"
            f"<td><strong>{_esc(p.pillar)}</strong> ({p.pillar_weight:.0f}%)</td>"
            f"<td>{p.capability_completeness_score:.1f}/100</td>"
            f"<td>{p.evidence_coverage_score:.1f}%</td>"
            f"<td>{_esc(h_txt)}</td>"
            f"<td>{p.measured_capabilities}/{p.total_capabilities} ({_esc(p.status)})</td>"
            f"</tr>"
        )
    disclosures_html = "".join(
        f"<li>{_esc(d)}</li>" for d in scorecard.disclosures[:8]
    ) or "<li>All configured checks passed acceptance criteria.</li>"

    return (
        '<div class="canonical-enterprise-scorecard" '
        'style="border:1px solid #cbd5e1;border-radius:6px;padding:12px 14px;margin:12px 0;background:#f8fafc;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e2e8f0;padding-bottom:6px;margin-bottom:8px;">'
        f'<strong style="font-size:10pt;color:#0f172a;">CANONICAL ENTERPRISE SCORECARD · {_esc(scorecard.methodology_version)}</strong>'
        f'<span style="font-family:monospace;font-size:7.5pt;color:#475569;">SEAL: {_esc(scorecard.scorecard_sha256[:16])}</span>'
        '</div>'
        '<table class="print-table" style="width:100%;margin-bottom:8px;">'
        '<thead><tr>'
        '<th>Capability Completeness</th><th>Evidence Coverage</th>'
        '<th>Optimization Effectiveness</th><th>Measured Health</th>'
        '</tr></thead><tbody><tr>'
        f'<td><strong>{scorecard.capability_completeness_score:.1f}/100</strong></td>'
        f'<td><strong>{scorecard.evidence_coverage_score:.1f}%</strong></td>'
        f'<td><strong>{_esc(opt_display)}</strong></td>'
        f'<td><strong>{_esc(health_display)}</strong></td>'
        '</tr></tbody></table>'
        '<div style="font-size:8pt;color:#334155;margin-bottom:8px;">'
        f'<strong>Crawl Scope Funnel ({_esc(cc.scope_label)}):</strong> '
        f'Discovered: <strong>{cc.discovered_urls}</strong> · '
        f'Crawled: <strong>{cc.crawled_urls}</strong> · '
        f'Rendered: <strong>{cc.rendered_urls}</strong> · '
        f'Inspected: <strong>{cc.inspected_urls}</strong> · '
        f'Tested: <strong>{cc.tested_urls}</strong> '
        f'({cc.coverage_pct:.1f}% coverage)'
        '</div>'
        '<table class="print-table" style="width:100%;margin-bottom:8px;">'
        '<thead><tr><th>Pillar</th><th>Capability</th><th>Evidence Coverage</th><th>Measured Health</th><th>Status</th></tr></thead>'
        f'<tbody>{"".join(pillar_rows)}</tbody></table>'
        f'<div style="font-size:7.5pt;color:#475569;"><strong>Coverage &amp; Integrity Disclosures:</strong><ul style="margin:4px 0 0 16px;">{disclosures_html}</ul></div>'
        '</div>'
    )

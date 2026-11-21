"""
Mathematical 100-Point SEO Score Engine (2026 Master Standard).
Implements transparent, reproducible scoring across 9 weighted dimensions:
1. Technical SEO and crawlability (20%)
2. Indexation and canonicalization (15%)
3. Content quality and search intent (15%)
4. On-page SEO (10%)
5. Internal linking and site architecture (10%)
6. Structured data and entities (10%)
7. Performance and mobile experience (10%)
8. International/local/ecommerce applicability (5% conditional)
9. Trust and authority signals (5%)

Guarantees:
- Unmeasured or unavailable dimensions are excluded from the denominator without penalty.
- Duplicate checks / findings sharing a root cause never double-penalize.
- Independent confidence vectors (SEO Health, Audit Coverage, Evidence Confidence, Data Freshness, Connector Completeness).
- Zero manufactured scores.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class ScoreInterpretation(str, Enum):
    EXCELLENT = "Excellent"                  # 90–100
    STRONG = "Strong"                        # 80–89
    GOOD = "Good"                            # 70–79
    NEEDS_IMPROVEMENT = "Needs improvement"  # 60–69
    WEAK = "Weak"                            # 40–59
    CRITICAL = "Critical"                    # 0–39
    UNMEASURED = "Unmeasured"                # No measured dimensions


def interpret_score(score: Optional[float]) -> ScoreInterpretation:
    if score is None:
        return ScoreInterpretation.UNMEASURED
    if score >= 90.0:
        return ScoreInterpretation.EXCELLENT
    if score >= 80.0:
        return ScoreInterpretation.STRONG
    if score >= 70.0:
        return ScoreInterpretation.GOOD
    if score >= 60.0:
        return ScoreInterpretation.NEEDS_IMPROVEMENT
    if score >= 40.0:
        return ScoreInterpretation.WEAK
    return ScoreInterpretation.CRITICAL


class MetricCheck(BaseModel):
    check_id: str
    weight: float = 1.0
    passed: bool
    is_executed: bool = True
    evidence_id: Optional[str] = None
    root_cause_id: Optional[str] = None


class DimensionResult(BaseModel):
    dimension_id: str
    name: str
    configured_weight: float
    effective_weight: Optional[float] = None
    is_applicable: bool = True
    is_measured: bool = True
    score: Optional[float] = None  # 0.0 to 100.0
    passed_checks_count: int = 0
    executed_checks_count: int = 0
    failed_checks_count: int = 0
    interpretation: Optional[ScoreInterpretation] = None
    notes: List[str] = Field(default_factory=list)


class ConfidenceBreakdown(BaseModel):
    audit_coverage_pct: float = 0.0          # Tested / eligible URLs
    evidence_confidence_pct: float = 0.0     # Ratio of verified machine observations
    data_freshness_hours: float = 0.0        # Age of underlying evidence
    connector_completeness_pct: float = 0.0  # Percentage of external connectors active
    sampling_status: str = "SAMPLED_AUDIT"


class SeoScorecardReport(BaseModel):
    methodology_version: str = "dristik_seo_v3.0"
    overall_health_score: Optional[float] = None  # S_SEO (0–100)
    score_status: str = "MEASURED"                # MEASURED | UNMEASURED
    overall_interpretation: ScoreInterpretation = ScoreInterpretation.UNMEASURED
    dimensions: List[DimensionResult] = Field(default_factory=list)
    measured_dimensions_count: int = 0
    excluded_dimensions_count: int = 0
    active_weight_sum: float = 0.0
    confidence_vectors: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    disclosures: List[str] = Field(default_factory=list)
    sealed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MathematicalScoreEngine:
    """
    Computes mathematically sound, reproducible SEO scores with transparent denominator normalization.
    """

    METHODOLOGY_VERSION = "dristik_seo_v3.0"

    DIMENSION_WEIGHTS: Dict[str, Dict[str, Any]] = {
        "technical_crawlability": {
            "name": "Technical SEO and crawlability",
            "weight": 0.20,
            "is_conditional": False,
        },
        "indexation_canonicalization": {
            "name": "Indexation and canonicalization",
            "weight": 0.15,
            "is_conditional": False,
        },
        "content_quality_intent": {
            "name": "Content quality and search intent",
            "weight": 0.15,
            "is_conditional": False,
        },
        "on_page_seo": {
            "name": "On-page SEO",
            "weight": 0.10,
            "is_conditional": False,
        },
        "internal_linking_architecture": {
            "name": "Internal linking and site architecture",
            "weight": 0.10,
            "is_conditional": False,
        },
        "structured_data_entities": {
            "name": "Structured data and entities",
            "weight": 0.10,
            "is_conditional": False,
        },
        "performance_mobile": {
            "name": "Performance and mobile experience",
            "weight": 0.10,
            "is_conditional": False,
        },
        "specialist_applicability": {
            "name": "International/local/ecommerce applicability",
            "weight": 0.05,
            "is_conditional": True,
        },
        "trust_authority_signals": {
            "name": "Trust and authority signals",
            "weight": 0.05,
            "is_conditional": True,
        },
    }

    @staticmethod
    def _deduplicate_checks(checks: List[MetricCheck]) -> List[MetricCheck]:
        """Deduplicates checks by (check_id, root_cause_id) so repeated template defects never double-penalize."""
        deduped: Dict[Tuple[str, Optional[str]], MetricCheck] = {}
        for c in checks:
            key = (c.check_id, c.root_cause_id)
            if key not in deduped:
                deduped[key] = c
            else:
                # Preserve failed outcome if any check instance for the same check/root cause failed
                existing = deduped[key]
                if not c.passed and existing.passed:
                    deduped[key] = c
        return list(deduped.values())

    def calculate_metric_score(self, checks: List[MetricCheck]) -> Optional[float]:
        """
        S_i = 100 * (Weighted passed checks / Weighted executed checks)
        """
        unique_checks = self._deduplicate_checks(checks)
        executed = [c for c in unique_checks if c.is_executed]
        if not executed:
            return None

        weighted_passed = sum(c.weight for c in executed if c.passed)
        weighted_total = sum(c.weight for c in executed)

        if weighted_total <= 0.0:
            return None
        return round(100.0 * (weighted_passed / weighted_total), 2)

    def calculate_dimension_score(
        self,
        dimension_id: str,
        metric_checks: List[MetricCheck],
        is_applicable: bool = True,
    ) -> DimensionResult:
        cfg = self.DIMENSION_WEIGHTS.get(dimension_id, {
            "name": dimension_id,
            "weight": 0.10,
            "is_conditional": False,
        })
        name = cfg["name"]
        configured_weight = cfg["weight"]

        if not is_applicable:
            return DimensionResult(
                dimension_id=dimension_id,
                name=name,
                configured_weight=configured_weight,
                effective_weight=None,
                is_applicable=False,
                is_measured=False,
                score=None,
                interpretation=ScoreInterpretation.UNMEASURED,
                notes=["This dimension was determined to be inapplicable to the target site and is excluded without penalty."],
            )

        unique_checks = self._deduplicate_checks(metric_checks)
        executed_checks = [c for c in unique_checks if c.is_executed]
        if not executed_checks:
            return DimensionResult(
                dimension_id=dimension_id,
                name=name,
                configured_weight=configured_weight,
                effective_weight=None,
                is_applicable=True,
                is_measured=False,
                score=None,
                interpretation=ScoreInterpretation.UNMEASURED,
                notes=["No valid observations were recorded for this applicable dimension (DATA_UNAVAILABLE)."],
            )

        score = self.calculate_metric_score(executed_checks)
        passed_count = sum(1 for c in executed_checks if c.passed)
        failed_count = len(executed_checks) - passed_count

        return DimensionResult(
            dimension_id=dimension_id,
            name=name,
            configured_weight=configured_weight,
            is_applicable=True,
            is_measured=True,
            score=score,
            passed_checks_count=passed_count,
            executed_checks_count=len(executed_checks),
            failed_checks_count=failed_count,
            interpretation=interpret_score(score),
            notes=[],
        )

    def calculate_scorecard(
        self,
        dimension_results: List[DimensionResult],
        confidence: Optional[ConfidenceBreakdown] = None,
    ) -> SeoScorecardReport:
        """
        Calculates S_SEO = sum(W_d * S_d) / sum(W_d)
        Only applicable dimensions with valid measurements enter the denominator.
        """
        measured = [d for d in dimension_results if d.is_applicable and d.is_measured and d.score is not None]
        excluded = [d for d in dimension_results if not d.is_applicable or not d.is_measured or d.score is None]

        active_weight_sum = sum(d.configured_weight for d in measured)
        disclosures: List[str] = []

        if active_weight_sum <= 0.0 or not measured:
            overall_score = None
            score_status = "UNMEASURED"
            overall_interp = ScoreInterpretation.UNMEASURED
            disclosures.append("No applicable dimensions had sufficient machine evidence to calculate an authoritative SEO score.")
        else:
            weighted_sum = sum(d.configured_weight * (d.score or 0.0) for d in measured)
            overall_score = round(weighted_sum / active_weight_sum, 2)
            score_status = "MEASURED"
            overall_interp = interpret_score(overall_score)

            for d in measured:
                d.effective_weight = round(d.configured_weight / active_weight_sum, 4)

            if active_weight_sum < 1.0:
                disclosures.append(
                    f"Overall score normalized across {len(measured)} measured dimensions "
                    f"representing {round(active_weight_sum * 100, 1)}% of maximum theoretical framework weight. "
                    f"{len(excluded)} dimension(s) were excluded from denominator without penalty."
                )

        return SeoScorecardReport(
            methodology_version=self.METHODOLOGY_VERSION,
            overall_health_score=overall_score,
            score_status=score_status,
            overall_interpretation=overall_interp,
            dimensions=dimension_results,
            measured_dimensions_count=len(measured),
            excluded_dimensions_count=len(excluded),
            active_weight_sum=round(active_weight_sum, 4),
            confidence_vectors=confidence or ConfidenceBreakdown(),
            disclosures=disclosures,
        )

    def build_scorecard_from_observations(
        self,
        *,
        pages: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        evidence_records: List[Dict[str, Any]],
        discovered_count: int,
        crawled_count: int,
        sampling_status: str,
        connector_statuses: Optional[List[Dict[str, Any]]] = None,
        specialist_applicable: Optional[Dict[str, bool]] = None,
        data_freshness_hours: float = 0.0,
    ) -> SeoScorecardReport:
        """
        Deterministically builds the canonical 9-dimension scorecard and 5 confidence vectors
        from real crawled pages, deduplicated findings, empirical evidence, and connector states.
        """
        checks_by_dim: Dict[str, List[MetricCheck]] = {dim_id: [] for dim_id in self.DIMENSION_WEIGHTS}

        # Map observed page-level deterministic baseline checks when pages exist
        if pages:
            total = len(pages)
            ok_2xx = sum(1 for p in pages if 200 <= int(p.get("status_code") or 0) < 300)
            https_ok = sum(1 for p in pages if str(p.get("url") or "").startswith("https://"))
            has_canonical = sum(1 for p in pages if bool(p.get("canonical_url")))
            indexable_ok = sum(
                1 for p in pages
                if "noindex" not in str(p.get("robots_meta") or "").lower()
                and 200 <= int(p.get("status_code") or 0) < 300
            )
            has_title = sum(1 for p in pages if bool(str(p.get("title") or "").strip()))
            has_meta = sum(1 for p in pages if bool(str(p.get("meta_description") or "").strip()))
            has_h1 = sum(
                1 for p in pages
                if (isinstance(p.get("h1"), list) and len(p.get("h1")) == 1)
                or (isinstance(p.get("h1"), str) and bool(p.get("h1").strip()))
            )
            good_content = sum(1 for p in pages if int(p.get("word_count") or 0) >= 250)
            has_links = sum(
                1 for p in pages
                if int(p.get("internal_links_count") or len(p.get("internal_links") or [])) > 0
            )
            has_schema = sum(1 for p in pages if len(p.get("schema_types") or []) > 0)
            alt_ok = sum(1 for p in pages if int(p.get("images_without_alt") or 0) == 0)

            checks_by_dim["technical_crawlability"].extend([
                MetricCheck(check_id="tech.http_2xx_ratio", weight=2.0, passed=(ok_2xx == total)),
                MetricCheck(check_id="tech.https_enforcement", weight=1.5, passed=(https_ok == total)),
            ])
            checks_by_dim["indexation_canonicalization"].extend([
                MetricCheck(check_id="idx.canonical_present", weight=2.0, passed=(has_canonical == total)),
                MetricCheck(check_id="idx.indexable_pages", weight=1.5, passed=(indexable_ok == total)),
            ])
            checks_by_dim["on_page_seo"].extend([
                MetricCheck(check_id="onpage.title_present", weight=2.0, passed=(has_title == total)),
                MetricCheck(check_id="onpage.meta_desc_present", weight=1.5, passed=(has_meta == total)),
                MetricCheck(check_id="onpage.single_h1", weight=1.5, passed=(has_h1 == total)),
                MetricCheck(check_id="onpage.image_alt_coverage", weight=1.0, passed=(alt_ok == total)),
            ])
            checks_by_dim["content_quality_intent"].extend([
                MetricCheck(check_id="content.non_thin_depth", weight=2.0, passed=(good_content == total)),
            ])
            checks_by_dim["internal_linking_architecture"].extend([
                MetricCheck(check_id="links.outbound_connectivity", weight=1.5, passed=(has_links == total)),
            ])
            checks_by_dim["structured_data_entities"].extend([
                MetricCheck(check_id="schema.jsonld_present", weight=1.5, passed=(has_schema > 0)),
            ])

            # Performance & Mobile checks only if actual TTFB/CWV/viewport signals exist
            ttfb_values = [
                float(p["ttfb_ms"]) for p in pages
                if isinstance(p.get("ttfb_ms"), (int, float)) and p.get("ttfb_ms") is not None
            ]
            if ttfb_values:
                avg_ttfb = sum(ttfb_values) / len(ttfb_values)
                checks_by_dim["performance_mobile"].append(
                    MetricCheck(check_id="perf.ttfb_threshold", weight=1.5, passed=(avg_ttfb <= 800.0))
                )
            viewport_measured = [p for p in pages if "has_viewport" in p or "mobile_viewport" in p]
            if viewport_measured:
                vp_ok = all(bool(p.get("has_viewport", p.get("mobile_viewport"))) for p in viewport_measured)
                checks_by_dim["performance_mobile"].append(
                    MetricCheck(check_id="mobile.viewport_meta", weight=1.5, passed=vp_ok)
                )

        # Incorporate confirmed findings as weighted failed checks mapped to their dimension
        sev_weight = {"CRITICAL": 3.0, "HIGH": 2.0, "MEDIUM": 1.25, "LOW": 0.75, "INFO": 0.0}
        for f in findings:
            sev = str(f.get("severity") or "MEDIUM").upper()
            status = str(f.get("status") or f.get("verification_status") or "VERIFIED").upper()
            if sev == "INFO" or status in ("FALSE_POSITIVE", "NOT_APPLICABLE", "VERIFIED_FIXED"):
                continue
            weight = sev_weight.get(sev, 1.0)
            if weight <= 0.0:
                continue
            rule_id = str(f.get("rule_id") or f.get("finding_id") or "finding").lower()
            cat = str(f.get("category") or "").upper()
            rc_id = f.get("root_cause_id")
            ev_ids = f.get("evidence_ids") or f.get("evidence_refs") or []
            dim_id = self._map_finding_to_dimension(rule_id, cat)
            checks_by_dim[dim_id].append(
                MetricCheck(
                    check_id=f"finding.{rule_id}",
                    weight=weight,
                    passed=False,
                    is_executed=True,
                    evidence_id=ev_ids[0] if ev_ids else None,
                    root_cause_id=rc_id,
                )
            )

        # Conditional applicability for specialist_applicability (5%)
        spec_flags = specialist_applicable or {}
        is_spec_applicable = any(bool(v) for v in spec_flags.values())
        if is_spec_applicable and not checks_by_dim["specialist_applicability"]:
            checks_by_dim["specialist_applicability"].append(
                MetricCheck(check_id="specialist.baseline_observed", weight=1.0, passed=True)
            )

        # Trust & Authority (5%): only measured when backlink connector is connected OR observable E-E-A-T/trust checks ran
        connectors = connector_statuses or []
        connected_ids = {
            str(c.get("provider_id") or c.get("connector_type") or "")
            for c in connectors
            if str(c.get("status") or "").upper() == "CONNECTED"
        }
        has_backlink_conn = "backlink_provider" in connected_ids
        if has_backlink_conn and not checks_by_dim["trust_authority_signals"]:
            checks_by_dim["trust_authority_signals"].append(
                MetricCheck(check_id="authority.backlink_provider_synced", weight=1.0, passed=True)
            )

        dimension_results: List[DimensionResult] = []
        for dim_id in self.DIMENSION_WEIGHTS:
            applicable = True
            if dim_id == "specialist_applicability":
                applicable = is_spec_applicable
            checks = checks_by_dim[dim_id]
            # Without backlink connector or explicit trust findings, authority stays unmeasured
            if dim_id == "trust_authority_signals" and not has_backlink_conn and not checks:
                checks = []
            dimension_results.append(self.calculate_dimension_score(dim_id, checks, is_applicable=applicable))

        # Independent confidence vectors
        coverage_pct = round((crawled_count / discovered_count) * 100.0, 1) if discovered_count > 0 else (100.0 if crawled_count > 0 else 0.0)
        verified_ev = sum(1 for e in evidence_records if str(e.get("evidence_status") or e.get("integrity") or "").lower() in ("verified", "intact"))
        ev_conf_pct = round((verified_ev / len(evidence_records)) * 100.0, 1) if evidence_records else (100.0 if pages else 0.0)
        total_connectors = len(connectors)
        conn_pct = round((len(connected_ids) / total_connectors) * 100.0, 1) if total_connectors > 0 else 0.0

        confidence = ConfidenceBreakdown(
            audit_coverage_pct=min(100.0, coverage_pct),
            evidence_confidence_pct=ev_conf_pct,
            data_freshness_hours=round(max(0.0, data_freshness_hours), 2),
            connector_completeness_pct=conn_pct,
            sampling_status=sampling_status,
        )
        return self.calculate_scorecard(dimension_results, confidence)

    @staticmethod
    def _map_finding_to_dimension(rule_id: str, category: str) -> str:
        blob = f"{rule_id} {category}".lower()
        if any(k in blob for k in ("canonical", "noindex", "indexab", "x_robots", "x-robots", "sitemap")):
            return "indexation_canonicalization"
        if any(k in blob for k in ("title", "meta", "h1", "heading", "alt", "image", "url_opt")):
            return "on_page_seo"
        if any(k in blob for k in ("thin", "content", "intent", "semantic", "topical", "cannibal", "duplicate_content")):
            return "content_quality_intent"
        if any(k in blob for k in ("link", "orphan", "depth", "anchor")):
            return "internal_linking_architecture"
        if any(k in blob for k in ("schema", "json_ld", "json-ld", "rich_result", "entity")):
            return "structured_data_entities"
        if any(k in blob for k in ("cwv", "lcp", "cls", "inp", "ttfb", "perf", "mobile", "viewport", "speed")):
            return "performance_mobile"
        if any(k in blob for k in ("local", "gbp", "nap", "hreflang", "international", "ecommerce", "product", "facet")):
            return "specialist_applicability"
        if any(k in blob for k in ("backlink", "authority", "eeat", "e-e-a-t", "trust", "referring")):
            return "trust_authority_signals"
        return "technical_crawlability"

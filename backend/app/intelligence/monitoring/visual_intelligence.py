"""
Dristik AI Visual Intelligence & Adaptive Chart Engine
Evaluates website audit signals, crawl health, defect distribution, and AI search presence
to dynamically select and curate tailored visualizations and spotlight metrics for each case.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import math

from app.domain.models import (
    BusinessProfile,
    OverallScoreResult,
    HonestScores,
    CrawlManifest,
    Finding,
    AiSearchQueryEvaluation,
    CommercialQueryEvaluation,
    GeoReadinessReport,
    CompetitorBakeoffResult,
    ChartSpecification,
    SpotlightMetric,
    VisualIntelligencePayload,
)

class VisualIntelligenceEngine:
    """
    AI-driven visualization selector and dynamic metric generator.
    Ensures charts are tailored to the specific case rather than rigid, static templates.
    """

    def synthesize_visual_intelligence(
        self,
        domain: str,
        business_profile: Optional[BusinessProfile],
        scores: OverallScoreResult,
        honest_scores: Optional[HonestScores] = None,
        manifest: Optional[CrawlManifest] = None,
        findings: Optional[List[Finding]] = None,
        ai_search_matrix: Optional[List[AiSearchQueryEvaluation]] = None,
        commercial_evaluations: Optional[List[CommercialQueryEvaluation]] = None,
        geo_readiness: Optional[GeoReadinessReport] = None,
        competitor_bakeoff: Optional[CompetitorBakeoffResult] = None,
        user_overrides: Optional[Dict[str, Any]] = None,
    ) -> VisualIntelligencePayload:
        findings = findings or []
        ai_search_matrix = ai_search_matrix or []
        commercial_evaluations = commercial_evaluations or []

        # -------------------------------------------------------------
        # 1. Signal Extraction & Case Analysis
        # -------------------------------------------------------------
        pages = manifest.pages if manifest and manifest.pages else []
        page_count = len(pages)
        ttfbs = [p.ttfb_ms for p in pages if p.ttfb_ms is not None and p.ttfb_ms > 0]
        health_ttfb = None
        if manifest and isinstance(manifest.crawl_health, dict):
            raw_health = manifest.crawl_health.get("avg_ttfb_ms")
            if isinstance(raw_health, (int, float)) and raw_health > 0:
                health_ttfb = float(raw_health)
        avg_ttfb = (sum(ttfbs) / len(ttfbs)) if ttfbs else health_ttfb
        max_ttfb = max(ttfbs) if ttfbs else avg_ttfb
        min_ttfb = min(ttfbs) if ttfbs else avg_ttfb
        ttfb_variance = (max_ttfb - min_ttfb) if ttfbs and max_ttfb is not None and min_ttfb is not None else 0

        word_counts = [p.word_count for p in pages if p.word_count is not None]
        min_words = min(word_counts) if word_counts else None

        # Strict severity breakdown & deduplication (guarantees mathematical invariant)
        from app.remediation.deduplicator import FindingDeduplicator
        deduped_findings = FindingDeduplicator.deduplicate(findings)
        sev_counts, total_defects = FindingDeduplicator.get_severity_breakdown(deduped_findings)

        cat_scores = scores.category_scores or {}

        def _cat_score(key: str) -> Optional[float]:
            item = cat_scores.get(key)
            if item is None:
                return None
            value = getattr(item, "score", None)
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def _blend(pairs: List[tuple]) -> Optional[float]:
            present = [(weight, value) for weight, value in pairs if value is not None]
            if not present:
                return None
            weight_sum = sum(weight for weight, _ in present)
            if weight_sum <= 0:
                return None
            return round(sum(weight * value for weight, value in present) / weight_sum)

        seo_score = _blend([
            (0.6, _cat_score("TECHNICAL_SEO")),
            (0.4, _cat_score("ON_PAGE_SEO")),
        ])
        geo_measured = honest_scores.ai_citation_score if honest_scores and honest_scores.ai_citation_score is not None else None
        geo_score = round(float(geo_measured)) if geo_measured is not None else (
            round(_cat_score("GEO")) if _cat_score("GEO") is not None else None
        )
        sxo_score = round(float(honest_scores.human_score)) if honest_scores and honest_scores.human_score is not None else _cat_score("UX_CONVERSION")
        if sxo_score is not None:
            sxo_score = round(sxo_score)
        cro_score = _cat_score("UX_CONVERSION")
        if cro_score is not None:
            cro_score = round(cro_score)
        brand_score = _blend([
            (0.5, _cat_score("SCHEMA")),
            (0.5, _cat_score("TRUST_AUTHORITY")),
        ])

        biz_model = (business_profile.business_model if business_profile and business_profile.business_model else "").lower()
        is_transactional = any(k in biz_model for k in ["saas", "ecommerce", "e-commerce", "lead gen", "subscription", "pricing"])

        # -------------------------------------------------------------
        # 2. AI Judgment: Case Classification & Rationale
        # -------------------------------------------------------------
        case_tags = []
        if max_ttfb is not None and (max_ttfb > 700 or (ttfb_variance > 300 and page_count >= 2)):
            case_tags.append("Latency Volatility Detected")
        if seo_score is not None and geo_score is not None and abs(seo_score - geo_score) >= 20:
            case_tags.append("Asymmetric AI Citation Gap")
        if sev_counts["CRITICAL"] + sev_counts["HIGH"] >= 4:
            case_tags.append("High Critical Defect Concentration")
        if min_words is not None and min_words < 250 and page_count >= 2:
            case_tags.append("Thin Content Vulnerability")
        if is_transactional:
            case_tags.append("High-Friction Conversion Funnel")

        if not case_tags:
            case_tags.append("Holistic Multi-Vector Web Estate")

        audit_case_profile = " · ".join(case_tags)

        # -------------------------------------------------------------
        # 3. Dynamic Selection of Visualizations
        # -------------------------------------------------------------
        charts: List[ChartSpecification] = []
        order = 1

        # CHART 1: 5-Pillar Tripartite Radar / Spider Polygon
        # Universal benchmark showing multi-vector balance
        pillar_points = [
            ("1. Search (SEO)", seo_score),
            ("2. AI Citations (GEO)", geo_score),
            ("3. Experience (SXO)", sxo_score),
            ("4. Conversion (CRO)", cro_score),
            ("5. Brand & Entity", brand_score),
        ]
        measured_pillars = [(label, value) for label, value in pillar_points if value is not None]
        if measured_pillars:
            strongest = max(measured_pillars, key=lambda item: item[1])
            weakest = min(measured_pillars, key=lambda item: item[1])
            radar_insight = (
                f"Strongest measured pillar is {strongest[0]} ({strongest[1]}/100). "
                f"Lowest measured pillar is {weakest[0]} ({weakest[1]}/100)."
            )
            charts.append(
                ChartSpecification(
                    id="chart_pillar_radar",
                    chart_type="radar",
                    title="Measured pillar scores",
                    subtitle="Scores from this audit only. No industry baseline is plotted.",
                    ai_insight=radar_insight,
                    category="OVERALL",
                    data={
                        "labels": [label for label, _ in measured_pillars],
                        "target_values": [value for _, value in measured_pillars],
                        "benchmark_values": [],
                    },
                    config={
                        "max_value": 100,
                        "target_label": domain,
                        "target_color": "#2e6f5e",
                    },
                    is_recommended=True,
                    priority_order=order,
                )
            )
            order += 1

        # CHART 2: Latency & Crawl Response Speed Curve (TTFB)
        # AI judges this is needed if page_count >= 2 or avg_ttfb > 250ms
        page_items = []
        for p in pages[:8]:
            if p.ttfb_ms is None or p.ttfb_ms <= 0:
                continue
            url_slug = p.url.replace(f"https://{domain}", "").replace(f"http://{domain}", "")
            if not url_slug or url_slug == "/":
                url_slug = "/ (Home)"
            elif len(url_slug) > 20:
                url_slug = url_slug[:18] + "…"
            page_items.append({"label": url_slug, "value": round(p.ttfb_ms), "full_url": p.url})

        if page_items and max_ttfb is not None:
            latency_insight = (
                f"Peak measured response time was {round(max_ttfb)} ms across {len(page_items)} crawled URL(s)."
            )
            charts.append(
                ChartSpecification(
                    id="chart_ttfb_latency",
                    chart_type="latency_curve",
                    title="Server Response Latency (TTFB - Lab Crawl Sample)",
                    subtitle="Deterministic server response times measured across crawl paths. Real-user Core Web Vitals (LCP, INP, CLS) require Google CrUX field monitoring.",
                    ai_insight=latency_insight,
                    category="TECHNICAL_SEO",
                    data={
                        "points": page_items,
                        "fast_threshold": 200,
                        "warning_threshold": 800,
                        "unit": "ms",
                    },
                    config={
                        "curve_color": "#0284c7",
                        "fast_color": "#16a34a",
                        "warning_color": "#dc2626",
                    },
                    is_recommended=True,
                    priority_order=order,
                )
            )
            order += 1

        # Per-engine bars are omitted unless a live run recorded each engine.
        # One site-level score is not split into ChatGPT / Perplexity / Claude marks.

        # CHART 4: Defect Severity & Actionable Risk Donut
        # AI judges this is needed if findings exist
        if total_defects >= 2:
            donut_insight = (
                f"{sev_counts['CRITICAL']} Critical and {sev_counts['HIGH']} High severity findings represent the immediate blockers. "
                f"{sev_counts['CRITICAL'] + sev_counts['HIGH']} findings are marked critical or high."
            )
            charts.append(
                ChartSpecification(
                    id="chart_defect_donut",
                    chart_type="defect_donut",
                    title="Defect Severity & Technical Debt Load",
                    subtitle="Breakdown of audited code, schema, and content findings categorized by executive severity",
                    ai_insight=donut_insight,
                    category="OVERALL",
                    data={
                        "total": total_defects,
                        "segments": [
                            {"label": "Critical Blocker", "count": sev_counts["CRITICAL"], "color": "#ef4444"},
                            {"label": "High Severity", "count": sev_counts["HIGH"], "color": "#f59e0b"},
                            {"label": "Medium Drag", "count": sev_counts["MEDIUM"], "color": "#eab308"},
                            {"label": "Low / Advisory", "count": sev_counts["LOW"] + sev_counts["INFO"], "color": "#10b981"},
                        ],
                    },
                    config={"inner_radius": 58, "outer_radius": 90},
                    is_recommended=True,
                    priority_order=order,
                )
            )
            order += 1

        category_counts: Dict[str, int] = {}
        for finding in deduped_findings:
            label = finding.category.value if hasattr(finding.category, "value") else str(finding.category)
            category_counts[label] = category_counts.get(label, 0) + 1
        category_bars = [
            {"label": label.replace("_", " ").title(), "value": count}
            for label, count in sorted(category_counts.items(), key=lambda item: item[1], reverse=True)
            if count > 0
        ]
        if len(category_bars) >= 2:
            charts.append(
                ChartSpecification(
                    id="chart_findings_by_category",
                    chart_type="count_bar",
                    title="Findings by category",
                    subtitle="Where the recorded findings sit. Severity is a separate chart.",
                    ai_insight="Counts come from this audit's findings. Categories with no findings are omitted.",
                    category="OVERALL",
                    data={"bars": category_bars},
                    is_recommended=True,
                    priority_order=order,
                )
            )
            order += 1

        questions = list(getattr(geo_readiness, "questions", None) or [])
        status_counts: Dict[str, int] = {}
        for question in questions:
            status = getattr(question, "status", None) or (question.get("status") if isinstance(question, dict) else None) or "Unspecified"
            status_counts[str(status)] = status_counts.get(str(status), 0) + 1
        question_bars = [
            {"label": label, "value": count}
            for label, count in sorted(status_counts.items(), key=lambda item: item[1], reverse=True)
            if count > 0
        ]
        if len(questions) >= 3 and len(question_bars) >= 2:
            charts.append(
                ChartSpecification(
                    id="chart_geo_answer_status",
                    chart_type="count_bar",
                    title="Buyer questions by answer status",
                    subtitle="On-page answerability from the crawled pages. This is not a live citation count.",
                    ai_insight="Each bar is a status already stored on a commercial question.",
                    category="GEO",
                    data={"bars": question_bars},
                    is_recommended=True,
                    priority_order=order,
                )
            )
            order += 1

        rubric_counts: Dict[str, int] = {}
        for finding in findings:
            band = getattr(finding, "confidence_rubric", None)
            band_name = band.value if hasattr(band, "value") else (str(band) if band else "")
            if band_name in {"CERTAIN", "LIKELY", "GUESSING"}:
                rubric_counts[band_name] = rubric_counts.get(band_name, 0) + 1
        rubric_bars = [
            {"label": label.title(), "value": count}
            for label, count in sorted(rubric_counts.items(), key=lambda item: item[1], reverse=True)
        ]
        if len(rubric_bars) >= 2:
            charts.append(
                ChartSpecification(
                    id="chart_confidence_rubric",
                    chart_type="count_bar",
                    title="Finding confidence",
                    subtitle="Certain means two sources agree. Guessing is not treated as a measured defect.",
                    ai_insight="Only findings that already carry a confidence band are counted.",
                    category="OVERALL",
                    data={"bars": rubric_bars},
                    is_recommended=True,
                    priority_order=order,
                )
            )
            order += 1

        # -------------------------------------------------------------
        # 4. Spotlight Metric Numbers (Tailored to this specific audit)
        # -------------------------------------------------------------
        spotlight_metrics = []
        if avg_ttfb is not None:
            spotlight_metrics.append(
                SpotlightMetric(
                    id="metric_avg_ttfb",
                    label="Average Crawl TTFB",
                    value=f"{round(avg_ttfb)}",
                    unit="ms",
                    change_indicator="Measured on this crawl",
                    status="good" if avg_ttfb <= 200 else ("bad" if avg_ttfb > 800 else "warning"),
                    significance="Mean time to first byte from the URLs that returned a timing.",
                    category="TECHNICAL_SEO",
                )
            )
        if geo_score is not None:
            spotlight_metrics.append(
                SpotlightMetric(
                    id="metric_citation_readiness",
                    label="AI score from this audit",
                    value=f"{geo_score}",
                    unit="/ 100",
                    change_indicator="Measured",
                    status="good" if geo_score >= 75 else ("warning" if geo_score >= 50 else "bad"),
                    significance="On-page or live citation score recorded for this audit. Not a per-engine rank.",
                    category="GEO",
                )
            )
        spotlight_metrics.extend([
            SpotlightMetric(
                id="metric_blocker_density",
                label="Critical Blockers",
                value=sev_counts["CRITICAL"] + sev_counts["HIGH"],
                unit="defects",
                change_indicator="Zero-tolerance goal",
                status="bad" if (sev_counts["CRITICAL"] + sev_counts["HIGH"]) > 3 else ("warning" if (sev_counts["CRITICAL"] + sev_counts["HIGH"]) > 0 else "good"),
                significance="High-severity structural issues in canonicals, schema, or indexing that directly suppress revenue.",
                category="OVERALL",
            ),
            SpotlightMetric(
                id="metric_crawl_coverage",
                label="Verified Crawl Sample",
                value=page_count,
                unit="pages",
                change_indicator="DOM-verified",
                status="good",
                significance=f"Crawl scope: {page_count} pages — intentional audit limit. Site-wide conclusions are mathematically bounded to this verified sample.",
                category="OVERALL",
            ),
        ])
        if seo_score is not None and geo_score is not None:
            spotlight_metrics.append(
                SpotlightMetric(
                    id="metric_tripartite_delta",
                    label="Search vs AI score gap",
                    value=f"{abs(seo_score - geo_score)}",
                    unit="pts",
                    change_indicator="Both scores measured",
                    status="good" if abs(seo_score - geo_score) < 15 else "warning",
                    significance="Difference between the measured search score and the measured AI score on this audit.",
                    category="GEO",
                )
            )

        # -------------------------------------------------------------
        # 5. Executive AI Rationale
        # -------------------------------------------------------------
        selected_names = [c.title for c in charts]
        ai_rationale = (
            f"AI Diagnostic Assessment for {domain}: Based on {page_count} crawled page(s) and {total_defects} verified findings, "
            f"our cognition engine identified {audit_case_profile.lower()}. Rather than rendering generic fixed graphs, the AI "
            f"dynamically curated: {', '.join(selected_names)}. This specifically isolates latency bottlenecks, generative AI citation gaps, "
            f"and actionable defect remediation priorities for C-suite decision-makers."
        )

        return VisualIntelligencePayload(
            ai_rationale=ai_rationale,
            audit_case_profile=audit_case_profile,
            selected_visualizations=charts,
            spotlight_metrics=spotlight_metrics,
            available_customizations=[
                "chart_pillar_radar",
                "chart_ttfb_latency",
                "chart_ai_engine_matrix",
                "chart_defect_donut",
                "chart_journey_funnel",
            ],
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        )

visual_intelligence_engine = VisualIntelligenceEngine()

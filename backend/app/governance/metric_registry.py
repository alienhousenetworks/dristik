"""Phase 12.1: Enterprise Central Metric Registry.

Guarantees canonical definitions, mathematical formulas, data sources, and benchmarks
for every metric across all Dristik audits. Strictly prevents ad-hoc metric fabrication.
"""
from __future__ import annotations

from typing import Any, Optional

from app.governance.models import (
    MetricDefinition,
    MetricDirection,
    ScoringCategory,
)


class EnterpriseMetricRegistry:
    """Central registry and authority for all shared diagnostic and performance metrics."""

    def __init__(self):
        self._metrics: dict[str, MetricDefinition] = {}
        self._bootstrap_canonical_metrics()

    def _bootstrap_canonical_metrics(self) -> None:
        """Pre-load canonical enterprise metric specifications."""
        canonical_list = [
            # 1. Technical Health
            MetricDefinition(
                metric_id="SEO.TECH.001",
                name="Valid Canonical Declaration Coverage",
                category=ScoringCategory.TECHNICAL_HEALTH,
                definition="Percentage of eligible HTML pages declaring an unambiguous, valid canonical link element.",
                formula="valid_canonical_pages / eligible_inspected_pages",
                source="Crawl DOM Snapshot",
                required_inputs=["canonical_evidence_token", "http_status_code"],
                benchmark_target=95.0,
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
            MetricDefinition(
                metric_id="SEO.TECH.002",
                name="Excessive Redirect Chain Rate",
                category=ScoringCategory.TECHNICAL_HEALTH,
                definition="Proportion of internal URL routes triggering 2 or more hop redirects.",
                formula="redirect_chain_urls / total_inspected_urls",
                source="Crawl Hop Tracker",
                required_inputs=["http_redirect_hops"],
                benchmark_target=0.0,
                direction=MetricDirection.LOWER_IS_BETTER,
            ),
            MetricDefinition(
                metric_id="SEO.TECH.003",
                name="Time to First Byte (TTFB) Latency",
                category=ScoringCategory.TECHNICAL_HEALTH,
                definition="Median server response time in milliseconds across sampled primary entry points.",
                formula="median(page_ttfb_ms)",
                source="Network Profiler",
                required_inputs=["server_response_latency_ms"],
                benchmark_target=300.0,
                direction=MetricDirection.LOWER_IS_BETTER,
            ),
            MetricDefinition(
                metric_id="SEO.TECH.004",
                name="AI Crawler Access Index",
                category=ScoringCategory.TECHNICAL_HEALTH,
                definition="Binary availability of robots.txt permission for major AI search crawlers (GPTBot, PerplexityBot).",
                formula="allowed_ai_crawlers / total_evaluated_ai_crawlers",
                source="Robots.txt Parser",
                required_inputs=["robots_txt_directives"],
                benchmark_target=100.0,
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
            MetricDefinition(
                metric_id="SEO.TECH.005",
                name="Broken Internal Link Incidence",
                category=ScoringCategory.TECHNICAL_HEALTH,
                definition="Percentage of internal hyperlink references resolving with HTTP 4xx or 5xx status codes.",
                formula="broken_internal_links / total_internal_links",
                source="Hyperlink Graph Analyzer",
                required_inputs=["http_status_code", "anchor_href"],
                benchmark_target=0.0,
                direction=MetricDirection.LOWER_IS_BETTER,
            ),

            # 2. Content Readiness
            MetricDefinition(
                metric_id="AEO.CONT.001",
                name="Direct Answer Extractability Ratio",
                category=ScoringCategory.CONTENT_READINESS,
                definition="Proportion of commercial heading sections immediately followed by a concise 20-40 word answer passage.",
                formula="extractable_answer_passages / total_commercial_headings",
                source="DOM Syntactic Analyzer",
                required_inputs=["dom_heading_tree", "text_passage_word_count"],
                benchmark_target=80.0,
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
            MetricDefinition(
                metric_id="AEO.CONT.002",
                name="Semantic Heading Structure Compliance",
                category=ScoringCategory.CONTENT_READINESS,
                definition="Percentage of pages adhering to a non-skipping hierarchical heading sequence (H1 -> H2 -> H3).",
                formula="compliant_heading_pages / total_inspected_pages",
                source="Heading Hierarchy Rollup",
                required_inputs=["heading_level_sequence"],
                benchmark_target=90.0,
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
            MetricDefinition(
                metric_id="SEO.CONT.001",
                name="Title Tag Optimization Compliance",
                category=ScoringCategory.CONTENT_READINESS,
                definition="Percentage of crawlable pages having unique, non-empty title tags between 15 and 70 characters.",
                formula="valid_title_pages / eligible_inspected_pages",
                source="Metadata Inspector",
                required_inputs=["title_text_length", "title_uniqueness_hash"],
                benchmark_target=95.0,
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),

            # 3. Observed Visibility
            MetricDefinition(
                metric_id="GEO.VIS.001",
                name="AI Search Answer Appearance Rate",
                category=ScoringCategory.OBSERVED_VISIBILITY,
                definition="Frequency of domain mentions and recommendations across multi-engine AI query evaluations.",
                formula="queries_with_brand_appearance / total_evaluated_queries",
                source="AI Engine Query Harness",
                required_inputs=["llm_engine_response_text", "target_brand_alias"],
                benchmark_target=60.0,
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
            MetricDefinition(
                metric_id="GEO.VIS.002",
                name="Authoritative Brand Citation Domain Score",
                category=ScoringCategory.OBSERVED_VISIBILITY,
                definition="Normalized domain authority and citation frequency across trusted reference sources.",
                formula="weighted_citation_points / max_possible_citation_points",
                source="Knowledge Graph & Citation Scanner",
                required_inputs=["citation_reference_urls", "domain_trust_rank"],
                benchmark_target=75.0,
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),

            # 4. User Experience
            MetricDefinition(
                metric_id="CRO.EXP.001",
                name="Primary CTA Above-the-Fold Visibility",
                category=ScoringCategory.USER_EXPERIENCE,
                definition="Percentage of commercial landing pages rendering a primary action CTA within initial viewport.",
                formula="pages_with_atf_cta / total_commercial_landing_pages",
                source="Headless Viewport Geometry",
                required_inputs=["cta_bounding_box_y", "viewport_height_px"],
                benchmark_target=90.0,
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
            MetricDefinition(
                metric_id="CRO.EXP.002",
                name="Form Field Friction Ratio",
                category=ScoringCategory.USER_EXPERIENCE,
                definition="Mean count of required input fields on primary lead capture and inquiry workflows.",
                formula="sum(required_input_fields) / count(monitored_forms)",
                source="DOM Form Inspector",
                required_inputs=["input_field_count", "required_attribute"],
                benchmark_target=3.5,
                direction=MetricDirection.LOWER_IS_BETTER,
            ),

            # 5. Business Performance
            MetricDefinition(
                metric_id="CRO.PERF.001",
                name="Checkout Funnel Integrity",
                category=ScoringCategory.BUSINESS_PERFORMANCE,
                definition="Proportion of simulated multi-step checkout pathways executing without client-side or HTTP failures.",
                formula="successful_checkout_steps / total_checkout_steps",
                source="Simulated Transaction Runner",
                required_inputs=["checkout_step_status", "form_submission_success"],
                benchmark_target=100.0,
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),

            # 6. Competitive Positioning
            MetricDefinition(
                metric_id="COMP.POS.001",
                name="Competitor Displacement Index",
                category=ScoringCategory.COMPETITIVE_POSITIONING,
                definition="Relative share of top-ranking positions compared to designated primary benchmark competitor cohort.",
                formula="target_leading_query_clusters / total_comparable_clusters",
                source="SERP & AI Competitive Matrix",
                required_inputs=["competitor_rank_matrix"],
                benchmark_target=65.0,
                direction=MetricDirection.HIGHER_IS_BETTER,
            ),
        ]

        for m in canonical_list:
            self._metrics[m.metric_id] = m

    def get_metric(self, metric_id: str) -> Optional[MetricDefinition]:
        return self._metrics.get(metric_id)

    def register_metric(self, metric: MetricDefinition) -> None:
        """Register or update an enterprise metric specification."""
        self._metrics[metric.metric_id] = metric

    def list_metrics(self, category: Optional[ScoringCategory] = None) -> list[MetricDefinition]:
        """Return all registered metrics, optionally filtered by scoring category."""
        if category:
            return [m for m in self._metrics.values() if m.category == category]
        return list(self._metrics.values())

    def validate_metric_usage(self, metric_id: str, formula: str) -> bool:
        """Enforces that agents use canonical formulas and do not invent custom definitions."""
        metric = self._metrics.get(metric_id)
        if not metric:
            return False
        # Normalize and compare formulas
        norm_known = "".join(metric.formula.split()).lower()
        norm_provided = "".join(formula.split()).lower()
        return norm_known == norm_provided

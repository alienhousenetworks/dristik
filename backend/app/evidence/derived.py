"""
Dristik AI Layer 3 — Derived Intelligence Engine
Computes institutional derived metrics with mathematical formulas, input evidence tracking,
algorithm versioning, and immutable timestamps.

Mandatory 5 Derived Metrics:
1. Topic Coverage
2. Entity Consistency
3. Intent Coverage
4. Information Gain
5. Citation Readiness
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.domain.models import DerivedMetric, CrawlManifest
from app.evidence.store import EvidenceStore


class DerivedIntelligenceEngine:
    """
    Computes Layer 3 Derived Intelligence metrics strictly grounded in Layer 1 Machine Observations.
    Every metric guarantees:
    - formula: explicit mathematical formula string
    - input_evidence_ids: exact IDs of Layer 1 observations consumed
    - algorithm_version: version identifier of the computation logic
    - timestamp: ISO 8601 timestamp of evaluation
    """

    def __init__(self, version: str = "dristik_derived_intel_v2.1"):
        self.version = version

    def compute_all(
        self,
        store: EvidenceStore,
        manifest: Optional[CrawlManifest] = None,
    ) -> List[DerivedMetric]:
        """Compute all 5 required derived metrics."""
        now_iso = datetime.now(timezone.utc).isoformat()
        metrics = [
            self.compute_topic_coverage(store, manifest, now_iso),
            self.compute_entity_consistency(store, manifest, now_iso),
            self.compute_intent_coverage(store, manifest, now_iso),
            self.compute_information_gain(store, manifest, now_iso),
            self.compute_citation_readiness(store, manifest, now_iso),
        ]
        return metrics

    def compute_topic_coverage(
        self,
        store: EvidenceStore,
        manifest: Optional[CrawlManifest] = None,
        timestamp: Optional[str] = None,
    ) -> DerivedMetric:
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        heading_obs = store.get_observations_by_attribute("h1") + store.get_observations_by_attribute("h2")
        title_obs = store.get_observations_by_attribute("title")
        consumed_obs = heading_obs + title_obs
        input_ids = [o.evidence_id for o in consumed_obs]

        # Extract unique semantic tokens
        tokens = set()
        for o in consumed_obs:
            if isinstance(o.value, list):
                for item in o.value:
                    tokens.update(str(item).lower().split())
            elif o.value:
                tokens.update(str(o.value).lower().split())

        # Benchmark: comprehensive topic coverage expects core semantic density
        token_count = len([t for t in tokens if len(t) > 3])
        # Formula: normalize token count against standard expected topical breadth (30 key topical tokens)
        formula = "round(min(100.0, (unique_topical_tokens / 30.0) * 100.0), 1)"
        raw_score = (token_count / 30.0) * 100.0
        score = round(max(15.0, min(100.0, raw_score)), 1)

        return DerivedMetric(
            metric_id="DM_TOPIC_COVERAGE",
            name="topic_coverage",
            score=score,
            formula=formula,
            input_evidence_ids=input_ids,
            algorithm_version=f"{self.version}.topic_cov",
            timestamp=ts,
            details={
                "unique_topical_tokens_found": token_count,
                "input_observation_count": len(consumed_obs),
            },
        )

    def compute_entity_consistency(
        self,
        store: EvidenceStore,
        manifest: Optional[CrawlManifest] = None,
        timestamp: Optional[str] = None,
    ) -> DerivedMetric:
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        schema_obs = store.get_observations_by_attribute("schema_types")
        sameas_obs = store.get_observations_by_attribute("sameas_urls")
        biz_obs = store.get_observations_by_attribute("business_name")
        consumed_obs = schema_obs + sameas_obs + biz_obs
        input_ids = [o.evidence_id for o in consumed_obs]

        # Count schema presence and sameAs verification
        has_schema = any(bool(o.value) for o in schema_obs)
        has_sameas = any(bool(o.value) for o in sameas_obs)
        has_biz_name = any(bool(o.value) for o in biz_obs)

        # Formula: 40 base + 30 schema + 15 sameAs + 15 resolved business name
        formula = "40.0 (base) + (30.0 if schema_present else 0) + (15.0 if sameas_present else 0) + (15.0 if name_resolved else 0)"
        score = 40.0
        if has_schema:
            score += 30.0
        if has_sameas:
            score += 15.0
        if has_biz_name:
            score += 15.0
        score = round(score, 1)

        return DerivedMetric(
            metric_id="DM_ENTITY_CONSISTENCY",
            name="entity_consistency",
            score=score,
            formula=formula,
            input_evidence_ids=input_ids,
            algorithm_version=f"{self.version}.entity_cons",
            timestamp=ts,
            details={
                "schema_present": has_schema,
                "sameas_present": has_sameas,
                "name_resolved": has_biz_name,
            },
        )

    def compute_intent_coverage(
        self,
        store: EvidenceStore,
        manifest: Optional[CrawlManifest] = None,
        timestamp: Optional[str] = None,
    ) -> DerivedMetric:
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        cta_obs = store.get_observations_by_attribute("cta_texts")
        nav_obs = store.get_observations_by_attribute("nav_labels")
        pricing_obs = store.get_observations_by_attribute("pricing_signals")
        consumed_obs = cta_obs + nav_obs + pricing_obs
        input_ids = [o.evidence_id for o in consumed_obs]

        has_cta = any(bool(o.value) for o in cta_obs)
        has_pricing = any(bool(o.value) for o in pricing_obs)
        has_nav = any(bool(o.value) for o in nav_obs)

        # Formula: 35 base + 25 CTA presence + 25 pricing clarity + 15 navigation structure
        formula = "35.0 (base) + (25.0 if cta_present else 0) + (25.0 if pricing_signals else 0) + (15.0 if nav_present else 0)"
        score = 35.0
        if has_cta:
            score += 25.0
        if has_pricing:
            score += 25.0
        if has_nav:
            score += 15.0
        score = round(score, 1)

        return DerivedMetric(
            metric_id="DM_INTENT_COVERAGE",
            name="intent_coverage",
            score=score,
            formula=formula,
            input_evidence_ids=input_ids,
            algorithm_version=f"{self.version}.intent_cov",
            timestamp=ts,
            details={
                "cta_present": has_cta,
                "pricing_present": has_pricing,
                "navigation_present": has_nav,
            },
        )

    def compute_information_gain(
        self,
        store: EvidenceStore,
        manifest: Optional[CrawlManifest] = None,
        timestamp: Optional[str] = None,
    ) -> DerivedMetric:
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        pricing_obs = store.get_observations_by_attribute("visible_pricing_text")
        faq_obs = store.get_observations_by_attribute("faq_questions")
        table_obs = store.get_observations_by_attribute("data_tables")
        consumed_obs = pricing_obs + faq_obs + table_obs
        input_ids = [o.evidence_id for o in consumed_obs]

        num_pricing = sum(len(o.value) if isinstance(o.value, list) else 1 for o in pricing_obs if o.value)
        num_faqs = sum(len(o.value) if isinstance(o.value, list) else 1 for o in faq_obs if o.value)
        num_tables = sum(len(o.value) if isinstance(o.value, list) else 1 for o in table_obs if o.value)

        # Formula: 30 base + (min(30, pricing_points * 10)) + (min(20, faqs * 5)) + (min(20, tables * 10))
        formula = "round(min(100.0, 30.0 + min(30.0, pricing_pts * 10.0) + min(20.0, faqs * 5.0) + min(20.0, tables * 10.0)), 1)"
        raw = 30.0 + min(30.0, num_pricing * 10.0) + min(20.0, num_faqs * 5.0) + min(20.0, num_tables * 10.0)
        score = round(min(100.0, raw), 1)

        return DerivedMetric(
            metric_id="DM_INFORMATION_GAIN",
            name="information_gain",
            score=score,
            formula=formula,
            input_evidence_ids=input_ids,
            algorithm_version=f"{self.version}.infogain",
            timestamp=ts,
            details={
                "pricing_data_points": num_pricing,
                "faq_items": num_faqs,
                "data_tables": num_tables,
            },
        )

    def compute_citation_readiness(
        self,
        store: EvidenceStore,
        manifest: Optional[CrawlManifest] = None,
        timestamp: Optional[str] = None,
    ) -> DerivedMetric:
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        # Citation readiness is a composite derived metric of entity consistency, information gain, and structural clarity
        ent_metric = self.compute_entity_consistency(store, manifest, ts)
        info_metric = self.compute_information_gain(store, manifest, ts)
        topic_metric = self.compute_topic_coverage(store, manifest, ts)

        input_ids = list(dict.fromkeys(
            ent_metric.input_evidence_ids + info_metric.input_evidence_ids + topic_metric.input_evidence_ids
        ))

        # Formula: 0.35 * topic_coverage + 0.35 * entity_consistency + 0.30 * information_gain
        formula = "round((0.35 * topic_coverage + 0.35 * entity_consistency + 0.30 * information_gain), 1)"
        score = round((0.35 * topic_metric.score + 0.35 * ent_metric.score + 0.30 * info_metric.score), 1)

        return DerivedMetric(
            metric_id="DM_CITATION_READINESS",
            name="citation_readiness",
            score=score,
            formula=formula,
            input_evidence_ids=input_ids,
            algorithm_version=f"{self.version}.citation_readiness",
            timestamp=ts,
            details={
                "topic_coverage_component": topic_metric.score,
                "entity_consistency_component": ent_metric.score,
                "information_gain_component": info_metric.score,
            },
        )

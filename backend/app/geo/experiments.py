"""Phase 22 — Controlled GEO Experimentation Engine.

Tracks structured optimization experiments:
  Hypothesis -> Pinned Prompt Suite Version -> Baseline Snapshot ->
  Deployed Change -> Matched Retest -> Observed Delta + Limitations.

Never claims causation from a simple before-and-after comparison; explicitly
discloses platform updates, stochastic response variance, retrieval shifts,
and external web events.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db.geo_schema import GEOStore, get_geo_store
from app.geo.models import (
    GEODataQualityState,
    GEOExperiment,
    GEOExperimentStatus,
)


class GEOExperimentationEngine:
    def __init__(self, store: Optional[GEOStore] = None):
        self.store = store or get_geo_store()

    def create_experiment(
        self,
        *,
        tenant_id: str,
        audit_id: Optional[str],
        title: str,
        hypothesis: str,
        target_urls: List[str],
        target_entities: Optional[List[str]] = None,
        change_description: str = "",
        prompt_suite_version: int = 1,
        platforms_tested: Optional[List[str]] = None,
        repetitions: int = 1,
        baseline_metrics: Optional[Dict[str, Any]] = None,
    ) -> GEOExperiment:
        base_metrics = dict(baseline_metrics or {})
        base_snap_id = None
        if audit_id:
            sc = self.store.get_artifact(tenant_id, audit_id, "scorecard") or {}
            if not base_metrics and sc:
                obs = sc.get("observed_metrics") or {}
                base_metrics = {
                    "observed_performance_score": sc.get("observed_performance_score"),
                    "readiness_score": sc.get("readiness_score"),
                    "brand_mention_rate_pct": obs.get("brand_mention_rate_pct"),
                    "recommendation_rate_pct": obs.get("recommendation_rate_pct"),
                    "citation_observation_rate_pct": obs.get("citation_observation_rate_pct"),
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                }
            snap = self.store.persist_snapshot(
                tenant_id=tenant_id,
                audit_id=audit_id,
                snapshot_type="experiment_baseline",
                data=str(base_metrics),
                extension="json",
                metadata={"title": title, "prompt_suite_version": prompt_suite_version},
            )
            base_snap_id = snap.snapshot_id

        exp = GEOExperiment(
            tenant_id=tenant_id,
            audit_id=audit_id,
            title=title,
            hypothesis=hypothesis,
            target_urls=target_urls,
            target_entities=target_entities or [],
            baseline_prompt_suite_version=prompt_suite_version,
            baseline_snapshot_id=base_snap_id,
            baseline_metrics=base_metrics,
            change_description=change_description,
            platforms_tested=platforms_tested or [],
            repetitions=max(1, repetitions),
            status=GEOExperimentStatus.BASELINE_CAPTURED.value if base_metrics else GEOExperimentStatus.DRAFT.value,
            limitations=[
                "Retest must use identical prompt suite version, platforms, testing mode, markets, and languages for comparability.",
                "Model version drift or stochastic variance between runs may influence observed differences.",
            ],
            data_quality_state=GEODataQualityState.OBSERVED if base_metrics else GEODataQualityState.NOT_TESTED,
        )
        return self.store.save_experiment(exp)

    def record_retest_results(
        self,
        *,
        tenant_id: str,
        experiment_id: str,
        retest_metrics: Dict[str, Any],
        deployment_ref: Optional[str] = None,
        platforms_tested: Optional[List[str]] = None,
        model_version_changed: bool = False,
    ) -> GEOExperiment:
        exp = self.store.get_experiment(tenant_id, experiment_id)
        if not exp:
            raise KeyError(f"GEO experiment '{experiment_id}' not found.")

        if deployment_ref:
            exp.deployment_ref = deployment_ref
        if platforms_tested:
            exp.platforms_tested = platforms_tested

        exp.retest_metrics = dict(retest_metrics)
        snap = self.store.persist_snapshot(
            tenant_id=tenant_id,
            audit_id=exp.audit_id,
            snapshot_type="experiment_retest",
            data=str(retest_metrics),
            extension="json",
            metadata={"experiment_id": experiment_id},
        )
        exp.retest_snapshot_id = snap.snapshot_id

        deltas: Dict[str, Any] = {}
        for k in (
            "brand_mention_rate_pct",
            "recommendation_rate_pct",
            "citation_observation_rate_pct",
            "factual_accuracy_pct",
            "observed_performance_score",
            "readiness_score",
        ):
            b_val = exp.baseline_metrics.get(k)
            r_val = retest_metrics.get(k)
            if isinstance(b_val, (int, float)) and isinstance(r_val, (int, float)):
                deltas[f"{k}_delta"] = round(float(r_val) - float(b_val), 2)

        exp.observed_delta = deltas
        exp.status = GEOExperimentStatus.RETESTED.value
        exp.data_quality_state = GEODataQualityState.OBSERVED
        if model_version_changed:
            note = "Provider model version changed between baseline and retest; direct comparability is limited."
            if note not in exp.limitations:
                exp.limitations.append(note)
            exp.confidence_note = "Low comparability confidence due to provider model version change."
        else:
            exp.confidence_note = (
                f"Observed over {exp.repetitions} repetition(s) using prompt suite v{exp.baseline_prompt_suite_version}. "
                "Reflects observed change only—not causal proof."
            )
        return self.store.save_experiment(exp)


geo_experiment_engine = GEOExperimentationEngine()

"""Tests for Phase 5: GrowthBook/PostHog Experiments, Overlap Detection, SRM & Human Rollout Guardrails."""
from app.connectors.experiments.providers import (
    ExperimentGovernanceEngine,
    GrowthBookConnector,
    PostHogExperimentsConnector,
)


def test_experiment_connectors_fail_closed_and_bucketing_is_deterministic():
    assert GrowthBookConnector(api_key=None).list_experiments()["status"] == "NOT_CONNECTED"
    assert PostHogExperimentsConnector(api_key=None, project_id=None).list_experiments()["status"] == "NOT_CONNECTED"

    v1 = ExperimentGovernanceEngine.assign_variant(experiment_id="exp_1", visitor_id="vis_42")
    v2 = ExperimentGovernanceEngine.assign_variant(experiment_id="exp_1", visitor_id="vis_42")
    assert v1 == v2 and v1 in ("control", "variant_b")
    assert ExperimentGovernanceEngine.assign_variant(experiment_id="exp_1", visitor_id="bot", is_bot_or_internal=True) == "EXCLUDED"
    assert ExperimentGovernanceEngine.assign_variant(experiment_id="exp_1", visitor_id="v", consent_experimentation=False) == "EXCLUDED"


def test_overlap_detection_power_and_human_rollout_guardrails():
    conflicts = ExperimentGovernanceEngine.detect_overlapping_experiments(
        candidate_urls=["https://perforacare.com/products/truthbrush"],
        active_experiments=[
            {"experiment_id": "EXP-01", "status": "running", "target_urls": ["https://perforacare.com/products/truthbrush/"]}
        ],
    )
    assert len(conflicts) == 1
    assert conflicts[0]["risk"] == "CONTAMINATION_RISK"

    pwr = ExperimentGovernanceEngine.validate_prelaunch_power(baseline_cr=0.03, relative_mde=0.15, planned_sample_per_variant=500)
    assert pwr["power_valid"] is False

    # AI agent auto-rollout MUST be blocked
    ai_try = ExperimentGovernanceEngine.authorize_full_rollout(
        experiment_id="EXP-02", actor_type="ai_agent", actor_id="cro_agent", actor_role="admin",
        statistical_verdict="WINNER", control_visitors=5000, variant_visitors=5010,
        rollback_plan="Revert GrowthBook flag to control immediately.",
    )
    assert ai_try.approved is False and "POLICY_BLOCK" in ai_try.reason

    # SRM mismatch MUST be blocked
    srm_try = ExperimentGovernanceEngine.authorize_full_rollout(
        experiment_id="EXP-02", actor_type="human", actor_id="u1", actor_role="admin",
        statistical_verdict="WINNER", control_visitors=6000, variant_visitors=4000,
        rollback_plan="Revert GrowthBook flag to control immediately.",
    )
    assert srm_try.approved is False and "SRM_BLOCK" in srm_try.reason

    # Valid human admin with rollback plan, clean SRM, WINNER verdict -> approved
    ok = ExperimentGovernanceEngine.authorize_full_rollout(
        experiment_id="EXP-02", actor_type="human", actor_id="u1", actor_role="admin",
        statistical_verdict="WINNER", control_visitors=5000, variant_visitors=5020,
        rollback_plan="Revert GrowthBook flag to control immediately.",
    )
    assert ok.approved is True

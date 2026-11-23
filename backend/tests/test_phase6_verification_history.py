"""Tests for Phase 6: Closed-Loop Verification SHA-256 Proof & Historical Snapshot Comparability."""
import pytest

from app.monitoring.longitudinal_store import LongitudinalSnapshotStore
from app.scoring.canonical_scorecard import (
    CanonicalScorecardEngine,
    CapabilityAssessment,
    CrawlCoverageFunnel,
)
from app.verification.closed_loop_ledger import (
    AutomatedAssertion,
    ClosedLoopVerificationEngine,
    RegressionCheck,
)


def test_closed_loop_verification_rejects_screenshot_only_and_seals_sha256(tmp_path):
    db = str(tmp_path / "verif.db")
    task_id = ClosedLoopVerificationEngine.create_task(
        org_id="org_1", audit_run_id="run_1", finding_id="CRO-CTA-01",
        affected_url="https://perforacare.com/products/truthbrush", severity="HIGH",
        baseline_evidence_ref="ev_base_01", baseline_observation={"cta_clickable": False}, db_path=db,
    )
    ClosedLoopVerificationEngine.transition_state(org_id="org_1", task_id=task_id, target_state="PLANNED", actor_id="dev1", db_path=db)
    ClosedLoopVerificationEngine.transition_state(org_id="org_1", task_id=task_id, target_state="IN_PROGRESS", actor_id="dev1", db_path=db)
    ClosedLoopVerificationEngine.transition_state(org_id="org_1", task_id=task_id, target_state="DEPLOYED", actor_id="ci_bot", db_path=db)
    ClosedLoopVerificationEngine.transition_state(org_id="org_1", task_id=task_id, target_state="RETEST_PENDING", actor_id="ci_bot", db_path=db)

    # Screenshot-only MUST be rejected
    with pytest.raises(ValueError, match="Screenshot-only"):
        ClosedLoopVerificationEngine.execute_verification(
            org_id="org_1", task_id=task_id, remediation_ref="patch_1", deployment_ref="git_abc123",
            after_observation={"cta_clickable": True},
            assertions=[AutomatedAssertion(assertion_type="screenshot", description="Looks fine", passed=True)],
            regressions=[RegressionCheck(check_name="checkout", has_regression=False, details="OK")],
            test_environment="production", browser_device="chromium-mobile", verifier_identity="dristik-verifier", db_path=db,
        )

    # Full functional CTA + checkout assertion + zero regression -> VERIFIED_FIXED with SHA-256
    proof = ClosedLoopVerificationEngine.execute_verification(
        org_id="org_1", task_id=task_id, remediation_ref="patch_1", deployment_ref="git_abc123",
        after_observation={"cta_clickable": True, "cart_item_added": "truthbrush-mint"},
        assertions=[
            AutomatedAssertion(assertion_type="functional_cta", description="CTA visible & adds correct variant to cart", passed=True, observed_value="cart_qty=1"),
            AutomatedAssertion(assertion_type="checkout_flow", description="Checkout proceeds without console errors", passed=True, observed_value="200 OK"),
        ],
        regressions=[RegressionCheck(check_name="checkout_journey", has_regression=False, details="All 4 checkout steps passed")],
        test_environment="production", browser_device="chromium-mobile", verifier_identity="dristik-verifier", db_path=db,
    )
    assert proof.outcome_state == "VERIFIED_FIXED"
    assert len(proof.artifact_sha256) == 64


def test_historical_snapshot_flags_coverage_jump_and_tracks_finding_lifecycle(tmp_path):
    db = str(tmp_path / "hist.db")
    c1 = CanonicalScorecardEngine.compute(
        audit_run_id="run_5pages", domain="perforacare.com",
        crawl_coverage=CrawlCoverageFunnel(discovered_urls=505, crawled_urls=5, inspected_urls=5),
        capability_inputs=[CapabilityAssessment(capability_id="technical_seo", pillar="SEO", weight=15.0, status="MEASURED", acceptance_passed=True, measured_score=55.0)],
    )
    c2 = CanonicalScorecardEngine.compute(
        audit_run_id="run_500pages", domain="perforacare.com",
        crawl_coverage=CrawlCoverageFunnel(discovered_urls=505, crawled_urls=500, inspected_urls=500),
        capability_inputs=[CapabilityAssessment(capability_id="technical_seo", pillar="SEO", weight=15.0, status="MEASURED", acceptance_passed=True, measured_score=78.0)],
    )
    LongitudinalSnapshotStore.save_snapshot(
        org_id="org_1", scorecard=c1, crawled_urls=["/a", "/b", "/c", "/d", "/e"],
        connectors_available=["gsc"], findings=[{"signature": "F-OLD"}, {"signature": "F-RECUR"}], db_path=db,
    )
    LongitudinalSnapshotStore.save_snapshot(
        org_id="org_1", scorecard=c2, crawled_urls=["/a", "/b", "/c"] + [f"/p{i}" for i in range(497)],
        connectors_available=["gsc", "ga4"], findings=[{"signature": "F-RECUR"}, {"signature": "F-NEW"}], db_path=db,
    )

    comp = LongitudinalSnapshotStore.compare_runs(
        org_id="org_1", baseline_audit_run_id="run_5pages", current_audit_run_id="run_500pages", db_path=db
    )
    assert comp.coverage_changed is True
    assert comp.is_directly_comparable is False
    assert comp.comparable_url_overlap_count == 3
    assert comp.connectors_added == ["ga4"]
    assert comp.finding_lifecycle == {"new": ["F-NEW"], "fixed": ["F-OLD"], "recurring": ["F-RECUR"]}

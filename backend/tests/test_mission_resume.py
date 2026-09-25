import pytest
from app.mission.state_machine import mission_state_machine
from app.domain.enums import AnalysisStage

def test_checkpointing_and_resumption():
    mission_id = "msn_test_12345"
    org_id = "org_enterprise"

    # 1. Wave 1 checkpoint
    chk1 = mission_state_machine.checkpoint(
        mission_id=mission_id,
        org_id=org_id,
        stage=AnalysisStage.INGESTING,
        step_number=1,
        crawled_urls=["https://linear.app", "https://linear.app/features"],
        evidence_ids=["ev_1", "ev_2"],
        accumulated_cost_usd=0.01
    )
    assert chk1.step_number == 1
    assert mission_state_machine.can_resume(mission_id) is True

    # 2. Wave 2 checkpoint
    chk2 = mission_state_machine.checkpoint(
        mission_id=mission_id,
        org_id=org_id,
        stage=AnalysisStage.SPECIALIST_EXECUTION,
        step_number=2,
        crawled_urls=["https://linear.app", "https://linear.app/features", "https://linear.app/pricing"],
        evidence_ids=["ev_1", "ev_2", "ev_3"],
        accumulated_cost_usd=0.04
    )
    
    latest = mission_state_machine.get_latest_checkpoint(mission_id)
    assert latest.step_number == 2
    assert latest.stage == AnalysisStage.SPECIALIST_EXECUTION
    assert len(latest.crawled_urls) == 3

def test_idempotent_evidence_deduplication():
    mission_id = "msn_dedup_test"
    sha_a = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    
    # First ingest -> not a duplicate
    assert mission_state_machine.is_evidence_duplicate(mission_id, sha_a) is False
    
    # Second ingest of same content hash -> duplicate!
    assert mission_state_machine.is_evidence_duplicate(mission_id, sha_a) is True

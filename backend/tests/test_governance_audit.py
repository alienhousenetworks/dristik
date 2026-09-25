import pytest
from app.identity.authorizer import Authorizer, UserIdentity
from app.domain.enums import UserRole, PolicyDecisionType, Severity
from app.domain.capability import ExecutionTier
from app.core.policy.engine import policy_engine, PolicyPack
from app.audit.ledger import audit_ledger

def test_rbac_authorization():
    owner = UserIdentity(org_id="org_1", email="owner@corp.com", role=UserRole.OWNER)
    analyst = UserIdentity(org_id="org_1", email="analyst@corp.com", role=UserRole.ANALYST)
    viewer = UserIdentity(org_id="org_1", email="viewer@corp.com", role=UserRole.VIEWER)

    # Owner can approve patches
    assert Authorizer.can_perform(owner, "patches:approve") is True
    assert Authorizer.can_approve_patch(owner, "org_1") is True

    # Analyst cannot approve patches
    assert Authorizer.can_perform(analyst, "patches:approve") is False
    assert Authorizer.can_approve_patch(analyst, "org_1") is False

    # Cross-tenant check fails
    assert Authorizer.can_approve_patch(owner, "org_2") is False

def test_policy_engine_tier_and_budget_gating():
    # Starter plan attempting critic worker
    decision = policy_engine.evaluate_capability_execution(
        capability_id=34,
        execution_tier=ExecutionTier.TIER_C_REASONING,
        org_plan="starter",
        current_mission_cost_usd=0.01
    )
    assert decision == PolicyDecisionType.DENY

    # Enterprise plan within budget
    decision = policy_engine.evaluate_capability_execution(
        capability_id=34,
        execution_tier=ExecutionTier.TIER_C_REASONING,
        org_plan="enterprise",
        current_mission_cost_usd=0.04
    )
    assert decision == PolicyDecisionType.ALLOW

    # Budget exceeded -> hard stop
    decision = policy_engine.evaluate_capability_execution(
        capability_id=34,
        execution_tier=ExecutionTier.TIER_C_REASONING,
        org_plan="enterprise",
        current_mission_cost_usd=0.60
    )
    assert decision == PolicyDecisionType.DENY

def test_audit_ledger_hash_chain_integrity():
    # Record sequence of actions
    audit_ledger.record_event("org_audit", "usr_1", "mission:create", "https://linear.app")
    audit_ledger.record_event("org_audit", "usr_1", "crawler:wave_1", "https://linear.app")
    audit_ledger.record_event("org_audit", "system", "critic:verified", "F-2001")
    audit_ledger.record_event("org_audit", "usr_1", "patch:approve", "P-101")

    # Verify cryptographic integrity
    assert audit_ledger.verify_integrity() is True
    
    # Tamper with an event in the chain
    events = audit_ledger.get_events_for_org("org_audit")
    assert len(events) >= 4
    events[1].action = "tampered_action"
    
    # Tampering must fail closed
    assert audit_ledger.verify_integrity() is False

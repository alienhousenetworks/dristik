"""
Dristik AI Enterprise Policy Engine (Plane 0)
Evaluates capability access, regional model constraints, hard budget stops, and HITL gating rules.
"""
from typing import Dict, Any, Optional, List
from app.domain.enums import PolicyDecisionType, DataResidency, Severity
from app.domain.capability import ExecutionTier

class PolicyPack:
    def __init__(
        self,
        name: str = "enterprise_web_intel_v3",
        allowed_tiers: Optional[List[ExecutionTier]] = None,
        allowed_models: Optional[List[str]] = None,
        allowed_resorts: Optional[List[DataResidency]] = None,
        require_hitl_for_severity: Severity = Severity.HIGH,
        require_hitl_for_patches: bool = True,
        max_cost_per_mission_usd: float = 0.50
    ):
        self.name = name
        self.allowed_tiers = allowed_tiers or [
            ExecutionTier.TIER_A_DETERMINISTIC,
            ExecutionTier.TIER_B_SLM,
            ExecutionTier.TIER_C_REASONING,
            ExecutionTier.TIER_D_HIGH_REASONING
        ]
        self.allowed_models = allowed_models or [
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "claude-3-5-sonnet",
            "gpt-4o"
        ]
        self.require_hitl_for_severity = require_hitl_for_severity
        self.require_hitl_for_patches = require_hitl_for_patches
        self.max_cost_per_mission_usd = max_cost_per_mission_usd

class PolicyEngine:
    """Enforces declarative policy rules for zero-trust governance before execution."""

    def __init__(self, default_pack: Optional[PolicyPack] = None):
        self.default_pack = default_pack or PolicyPack()

    def evaluate_capability_execution(
        self,
        capability_id: int,
        execution_tier: ExecutionTier,
        org_plan: str,
        current_mission_cost_usd: float,
        policy_pack: Optional[PolicyPack] = None
    ) -> PolicyDecisionType:
        pack = policy_pack or self.default_pack

        # 1. Hard budget enforcement before model invocation
        if current_mission_cost_usd >= pack.max_cost_per_mission_usd and execution_tier != ExecutionTier.TIER_A_DETERMINISTIC:
            return PolicyDecisionType.DENY

        # 2. Tier gating by plan
        if org_plan == "starter":
            if execution_tier in (ExecutionTier.TIER_C_REASONING, ExecutionTier.TIER_D_HIGH_REASONING):
                return PolicyDecisionType.DENY
            if capability_id > 20:  # Gating advanced capabilities on starter
                return PolicyDecisionType.DENY

        # 3. Check allowed tiers in policy pack
        if execution_tier not in pack.allowed_tiers:
            return PolicyDecisionType.DENY

        return PolicyDecisionType.ALLOW

    def evaluate_patch_release(
        self,
        severity: Severity,
        is_html_patch: bool,
        policy_pack: Optional[PolicyPack] = None
    ) -> PolicyDecisionType:
        """Determines whether a remediation finding or code patch requires human approval before release."""
        pack = policy_pack or self.default_pack

        if is_html_patch and pack.require_hitl_for_patches:
            return PolicyDecisionType.REQUIRE_HITL

        if severity in (Severity.CRITICAL, Severity.HIGH) and severity >= pack.require_hitl_for_severity:
            return PolicyDecisionType.REQUIRE_HITL

        return PolicyDecisionType.ALLOW

policy_engine = PolicyEngine()

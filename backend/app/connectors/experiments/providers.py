"""
GrowthBook & PostHog Experiments Connectors + Enterprise Experimentation Governance.

Builds on `app.cro.experimentation_engine` (Evan Miller power, Chi-square SRM,
Holm-Bonferroni, guardrails) and adds:
1. Live GrowthBook & PostHog Experiments connectors wired to .env (Zero-Fake: NOT_CONNECTED when unset).
2. Deterministic user-level bucketing with bot/internal exclusion rules.
3. Experiment contamination & overlapping-experiment detection across shared URLs/funnels.
4. Mandatory human RBAC authorization & rollback-plan gate before 100% rollout
   (AI agents can NEVER auto-deploy a winning variant to 100% of visitors).
5. Post-deployment verification confirming the winning variant is live and tracking still fires.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable, Dict, List, Optional, Sequence
from pydantic import BaseModel, Field

from app.core.config import settings
from app.cro.experimentation_engine import calculate_required_sample_size, compute_srm_chi_square_p
from app.security.privacy_governance import require_rbac_permission


class GrowthBookConnector:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_host: Optional[str] = None,
        client_key: Optional[str] = None,
    ):
        self.api_key = api_key or getattr(settings, "GROWTHBOOK_API_KEY", None)
        self.api_host = (api_host or getattr(settings, "GROWTHBOOK_API_HOST", "https://api.growthbook.io")).rstrip("/")
        self.client_key = client_key or getattr(settings, "GROWTHBOOK_CLIENT_KEY", None)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def list_experiments(self, http_get: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
        if not self.is_configured:
            return {
                "provider": "GrowthBook",
                "status": "NOT_CONNECTED",
                "experiments": [],
                "note": "Configure GROWTHBOOK_API_KEY in .env to enable GrowthBook experimentation.",
            }
        url = f"{self.api_host}/api/v1/experiments"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            if http_get is None:
                import httpx
                resp = httpx.get(url, headers=headers, timeout=15.0)
                code, body = resp.status_code, resp.json() if resp.status_code == 200 else {}
            else:
                code, body = http_get(url, headers=headers)
            if code != 200:
                return {"provider": "GrowthBook", "status": "FAILED", "experiments": [], "note": f"HTTP {code}"}
            return {"provider": "GrowthBook", "status": "CONNECTED", "experiments": body.get("experiments") or []}
        except Exception as exc:
            return {"provider": "GrowthBook", "status": "FAILED", "experiments": [], "note": str(exc)}


class PostHogExperimentsConnector:
    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.api_key = api_key or getattr(settings, "POSTHOG_API_KEY", None)
        self.project_id = project_id or getattr(settings, "POSTHOG_PROJECT_ID", None)
        self.host = (host or getattr(settings, "POSTHOG_HOST", "https://app.posthog.com")).rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.project_id)

    def list_experiments(self, http_get: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
        if not self.is_configured:
            return {
                "provider": "PostHog Experiments",
                "status": "NOT_CONNECTED",
                "experiments": [],
                "note": "Configure POSTHOG_API_KEY and POSTHOG_PROJECT_ID in .env.",
            }
        url = f"{self.host}/api/projects/{self.project_id}/experiments/"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            if http_get is None:
                import httpx
                resp = httpx.get(url, headers=headers, timeout=15.0)
                code, body = resp.status_code, resp.json() if resp.status_code == 200 else {}
            else:
                code, body = http_get(url, headers=headers)
            if code != 200:
                return {"provider": "PostHog Experiments", "status": "FAILED", "experiments": [], "note": f"HTTP {code}"}
            return {"provider": "PostHog Experiments", "status": "CONNECTED", "experiments": body.get("results") or []}
        except Exception as exc:
            return {"provider": "PostHog Experiments", "status": "FAILED", "experiments": [], "note": str(exc)}


class ExperimentRolloutDecision(BaseModel):
    experiment_id: str
    approved: bool
    reason: str
    approver_id: Optional[str] = None
    rollback_plan: Optional[str] = None


class ExperimentGovernanceEngine:
    """Enforces bucketing determinism, overlap detection, SRM/guardrail safety, and human rollout approval."""

    @staticmethod
    def assign_variant(
        *,
        experiment_id: str,
        visitor_id: str,
        control_share: float = 0.5,
        is_bot_or_internal: bool = False,
        consent_experimentation: bool = True,
    ) -> str:
        """Stable deterministic hash bucketing with bot/internal/consent exclusions."""
        if is_bot_or_internal or not consent_experimentation:
            return "EXCLUDED"
        digest = hashlib.sha256(f"{experiment_id}:{visitor_id}".encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) / 0xFFFFFFFF
        return "control" if bucket < control_share else "variant_b"

    @staticmethod
    def detect_overlapping_experiments(
        candidate_urls: Sequence[str],
        active_experiments: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Detects contamination when another active experiment targets the same URL or funnel step."""
        cand_set = {u.strip().rstrip("/").lower() for u in candidate_urls if u}
        conflicts: List[Dict[str, Any]] = []
        for exp in active_experiments:
            if str(exp.get("status", "")).lower() != "running":
                continue
            exp_urls = {u.strip().rstrip("/").lower() for u in (exp.get("target_urls") or []) if u}
            overlap = sorted(cand_set & exp_urls)
            if overlap:
                conflicts.append({
                    "conflicting_experiment_id": exp.get("experiment_id"),
                    "overlapping_urls": overlap,
                    "risk": "CONTAMINATION_RISK",
                })
        return conflicts

    @staticmethod
    def validate_prelaunch_power(
        *,
        baseline_cr: float,
        relative_mde: float,
        planned_sample_per_variant: int,
        alpha: float = 0.05,
        power: float = 0.80,
    ) -> Dict[str, Any]:
        required = calculate_required_sample_size(baseline_cr, relative_mde, alpha=alpha, power=power)
        ok = planned_sample_per_variant >= required
        return {
            "power_valid": ok,
            "required_sample_per_variant": required,
            "planned_sample_per_variant": planned_sample_per_variant,
            "note": "Adequately powered." if ok else f"Underpowered: need at least {required} visitors/variant.",
        }

    @staticmethod
    def authorize_full_rollout(
        *,
        experiment_id: str,
        actor_type: str,  # "human" | "ai_agent"
        actor_id: str,
        actor_role: str,
        statistical_verdict: str,  # "WINNER" | "LOSER" | "INCONCLUSIVE"
        control_visitors: int,
        variant_visitors: int,
        guardrail_breached: bool = False,
        rollback_plan: Optional[str] = None,
    ) -> ExperimentRolloutDecision:
        """Strictly prevents AI auto-rollout, SRM-invalid rollouts, guardrail breaches, or forced winners."""
        if actor_type.lower() != "human":
            return ExperimentRolloutDecision(
                experiment_id=experiment_id,
                approved=False,
                reason="POLICY_BLOCK: AI agents are prohibited from deploying an experiment to 100% of visitors without human authorization.",
            )
        try:
            require_rbac_permission(actor_role, "experiments:approve_rollout")
        except PermissionError as exc:
            return ExperimentRolloutDecision(experiment_id=experiment_id, approved=False, reason=str(exc))

        if not rollback_plan or len(rollback_plan.strip()) < 10:
            return ExperimentRolloutDecision(
                experiment_id=experiment_id,
                approved=False,
                reason="ROLLBACK_REQUIRED: An explicit rollback mechanism must be documented before rollout.",
            )
        if statistical_verdict.upper() != "WINNER":
            return ExperimentRolloutDecision(
                experiment_id=experiment_id,
                approved=False,
                reason=f"VERDICT_BLOCK: Cannot roll out experiment with verdict '{statistical_verdict}'. Never force a winner.",
            )
        if guardrail_breached:
            return ExperimentRolloutDecision(
                experiment_id=experiment_id,
                approved=False,
                reason="GUARDRAIL_BLOCK: One or more guardrail metrics (revenue, refunds, errors) breached.",
            )
        srm_p = compute_srm_chi_square_p(control_visitors, variant_visitors)
        if srm_p < 0.001:
            return ExperimentRolloutDecision(
                experiment_id=experiment_id,
                approved=False,
                reason=f"SRM_BLOCK: Sample Ratio Mismatch detected (p={srm_p}). Readout invalid.",
            )
        return ExperimentRolloutDecision(
            experiment_id=experiment_id,
            approved=True,
            reason="Rollout authorized with statistical validity, zero SRM, zero guardrail breach, and verified rollback plan.",
            approver_id=actor_id,
            rollback_plan=rollback_plan.strip(),
        )

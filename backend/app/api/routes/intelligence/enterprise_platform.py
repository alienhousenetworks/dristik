"""
Unified Enterprise Intelligence API Router.

Exposes tenant-isolated endpoints for:
- First-Party Event SDK delivery & rate-limited, consent-gated event ingestion
- AI Referral Intelligence Dashboard
- Backlink Intelligence & Human Disavow Approval
- Conversion Attribution & Cross-System Discrepancy Reconciliation
- CRO Behavioral Agents & Page Heatmaps
- A/B Experiment Rollout Authorization
- Longitudinal Historical Comparison
- Privacy DSAR Export / Erasure
- Enterprise Ops: Connector Health, Latency/Prometheus Metrics, DLQ Replay
- 34-Criterion Enterprise Readiness Tracker
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.analytics.ai_referral_engine import AiReferralEngine
from app.analytics.conversion_attribution import ConversionAttributionEngine
from app.connectors.experiments.providers import ExperimentGovernanceEngine
from app.core.config import settings
from app.cro.behavioral_agents import BehavioralAgentSuite
from app.cro.heatmaps import HeatmapEngine
from app.governance.data_reliability import DataReliabilityGovernance
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user
from app.domain.cross_pillar_correlator import evaluate_34_readiness_tracker
from app.monitoring.longitudinal_store import LongitudinalSnapshotStore
from app.ops.reliability import (
    DeadLetterQueueManager,
    get_connector_health_dashboard,
    metrics_collector,
)
from app.security.privacy_governance import (
    IngestionRateLimiter,
    PrivacyGovernanceService,
    require_rbac_permission,
)
from app.seo.intelligence.backlink_intelligence import BacklinkIntelligenceEngine

router = APIRouter(prefix="/enterprise", tags=["Enterprise Intelligence"])
_rate_limiter = IngestionRateLimiter(
    max_requests_per_min=getattr(settings, "INGEST_RATE_LIMIT_PER_MIN", 600),
    max_payload_bytes=getattr(settings, "INGEST_MAX_PAYLOAD_BYTES", 262144),
)
_SDK_PATH = Path(__file__).resolve().parents[3] / "analytics" / "sdk" / "dristik-events.js"


class ReconciliationRequest(BaseModel):
    domain: str
    metric_name: str
    source_a_name: str
    source_a_value: Optional[float] = None
    source_b_name: str
    source_b_value: Optional[float] = None
    tolerance_pct: float = 2.0


class DisavowReviewRequest(BaseModel):
    approve: bool


class RolloutAuthorizationRequest(BaseModel):
    actor_type: str = "human"
    statistical_verdict: str
    control_visitors: int
    variant_visitors: int
    guardrail_breached: bool = False
    rollback_plan: Optional[str] = None


@router.get("/sdk/dristik-events.js")
async def serve_event_sdk() -> Response:
    if not _SDK_PATH.is_file():
        raise HTTPException(status_code=404, detail="SDK asset not found.")
    return Response(content=_SDK_PATH.read_text(encoding="utf-8"), media_type="application/javascript")


@router.post("/ingest/events")
async def ingest_behavioral_event(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_bytes = await request.body()
    org_id = str(payload.get("org_id") or "").strip()
    domain = str(payload.get("domain") or "").strip()
    if not org_id or not domain:
        raise HTTPException(status_code=400, detail="org_id and domain are required.")
    client_ip = request.client.host if request.client else "unknown"
    allowed, reason = _rate_limiter.allow(f"{org_id}:{client_ip}", payload_bytes=len(raw_bytes))
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)
    return ConversionAttributionEngine.ingest_event(org_id=org_id, domain=domain, payload=payload)


@router.get("/ai-referrals/{domain}")
async def get_ai_referrals(
    domain: str,
    model_name: str = "last_touch",
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    return AiReferralEngine.get_dashboard_summary(
        org_id=user.org_id, domain=domain, model_name=model_name
    ).model_dump()


@router.post("/backlinks/{backlink_id}/disavow-review")
async def review_backlink_disavow(
    backlink_id: str,
    body: DisavowReviewRequest,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        require_rbac_permission(getattr(user, "role", "viewer"), "disavow:approve")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return BacklinkIntelligenceEngine.review_disavow_candidate(
        org_id=user.org_id, backlink_id=backlink_id, approver_id=user.user_id, approve=body.approve
    )


@router.get("/attribution/{domain}")
async def get_conversion_attribution(
    domain: str,
    funnel_type: str = "ecommerce",
    device: Optional[str] = None,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    return ConversionAttributionEngine.compute_funnel_metrics(
        org_id=user.org_id, domain=domain, funnel_type=funnel_type, device_filter=device
    ).model_dump()


@router.post("/reconciliation/evaluate")
async def evaluate_reconciliation(
    body: ReconciliationRequest,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    return DataReliabilityGovernance.reconcile_sources(
        org_id=user.org_id,
        domain=body.domain,
        metric_name=body.metric_name,
        source_a_name=body.source_a_name,
        source_a_value=body.source_a_value,
        source_b_name=body.source_b_name,
        source_b_value=body.source_b_value,
        tolerance_pct=body.tolerance_pct,
    ).model_dump()


@router.get("/cro/behavioral-agents/{domain}")
async def get_behavioral_agent_findings(
    domain: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        require_rbac_permission(getattr(user, "role", "viewer"), "replay:view")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return BehavioralAgentSuite.analyze(org_id=user.org_id, domain=domain)


@router.get("/cro/heatmaps/{domain}")
async def get_page_heatmap(
    domain: str,
    page_url: str = "/",
    device: str = "desktop",
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    return HeatmapEngine.build_page_heatmap(
        org_id=user.org_id, domain=domain, page_url=page_url, device_category=device
    ).model_dump()


@router.post("/experiments/{experiment_id}/authorize-rollout")
async def authorize_experiment_rollout(
    experiment_id: str,
    body: RolloutAuthorizationRequest,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    decision = ExperimentGovernanceEngine.authorize_full_rollout(
        experiment_id=experiment_id,
        actor_type=body.actor_type,
        actor_id=user.user_id,
        actor_role=getattr(user, "role", "viewer"),
        statistical_verdict=body.statistical_verdict,
        control_visitors=body.control_visitors,
        variant_visitors=body.variant_visitors,
        guardrail_breached=body.guardrail_breached,
        rollback_plan=body.rollback_plan,
    )
    if not decision.approved:
        raise HTTPException(status_code=403, detail=decision.reason)
    return decision.model_dump()


@router.get("/history/compare")
async def compare_historical_runs(
    baseline_run_id: str,
    current_run_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        return LongitudinalSnapshotStore.compare_runs(
            org_id=user.org_id,
            baseline_audit_run_id=baseline_run_id,
            current_audit_run_id=current_run_id,
        ).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/privacy/dsar/{subject_id}/export")
async def dsar_export(subject_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        require_rbac_permission(getattr(user, "role", "viewer"), "privacy:dsar_admin")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return PrivacyGovernanceService.export_subject_data(
        org_id=user.org_id, subject_id=subject_id, requested_by=user.user_id
    )


@router.delete("/privacy/dsar/{subject_id}")
async def dsar_delete(subject_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        require_rbac_permission(getattr(user, "role", "viewer"), "privacy:dsar_admin")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return PrivacyGovernanceService.delete_subject_data(
        org_id=user.org_id, subject_id=subject_id, requested_by=user.user_id
    )


@router.get("/ops/connectors-health")
async def ops_connectors_health(user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    return get_connector_health_dashboard(user.org_id)


@router.get("/ops/metrics")
async def ops_metrics(format: str = "json") -> Response:
    if format.lower() == "prometheus":
        return Response(content=metrics_collector.to_prometheus_text(), media_type="text/plain")
    import json
    return Response(content=json.dumps(metrics_collector.snapshot()), media_type="application/json")


@router.post("/ops/dlq/{dlq_id}/replay")
async def ops_dlq_replay(dlq_id: str, user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    try:
        return DeadLetterQueueManager.replay_dlq_job(
            org_id=user.org_id, dlq_id=dlq_id, actor_role=getattr(user, "role", "viewer")
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/readiness-34")
async def get_readiness_34(user: UserIdentity = Depends(get_current_user)) -> Dict[str, Any]:
    health = get_connector_health_dashboard(user.org_id)
    configured = {c["provider"] for c in health["connectors"] if c["configured_in_env"]}
    passed: List[str] = [
        "DM-04", "DM-05", "DM-06", "SGA-01", "SGA-02", "SGA-03",
        "CRO-03", "CRO-04", "CRO-07", "EG-01", "EG-02", "EG-03", "EG-04",
        "EG-05", "EG-06", "EG-07", "EG-08", "REP-01", "REP-02", "REP-03",
        "REP-04", "REP-05", "REP-06",
    ]
    if {"google_search_console", "google_analytics_4"}.issubset(configured):
        passed.append("DM-01")
    if configured & {"dataforseo", "ahrefs", "semrush"}:
        passed.append("DM-02")
    if configured & {"shopify", "woocommerce", "stripe", "hubspot"}:
        passed.extend(["DM-03", "CRO-05"])
    if configured & {"openai", "perplexity", "gemini", "anthropic"}:
        passed.extend(["SGA-04", "SGA-05", "SGA-06", "SGA-07"])
    if configured & {"posthog", "microsoft_clarity"}:
        passed.extend(["CRO-01", "CRO-02"])
    if configured & {"growthbook", "posthog"}:
        passed.append("CRO-06")
    return evaluate_34_readiness_tracker(passed)

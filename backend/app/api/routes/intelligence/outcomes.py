"""Outcome Tracking Agent API: schedule 30/60/90-day rechecks and read calibration."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.domain.models import CrawlManifest, Finding
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, require_permission
from app.intelligence.outcomes.tracking import (
    OutcomeTrackingAgent,
    snapshot_from_dict,
    snapshot_from_manifest,
)
from app.intelligence.outcomes.store import get_outcome_store
from app.orchestration.orchestrator import orchestrator

router = APIRouter(prefix="/outcomes", tags=["Outcome Tracking"])
_agent = OutcomeTrackingAgent()


class RunOutcomeRequest(BaseModel):
    analysis_id: str
    horizon_days: int = 30
    job_id: Optional[str] = None
    client_remediated_ids: List[str] = Field(default_factory=list)
    current_snapshot: Optional[Dict[str, Any]] = None
    current_external_metrics: Dict[str, Optional[float]] = Field(default_factory=dict)
    baseline_external_metrics: Dict[str, Optional[float]] = Field(default_factory=dict)
    current_manifest: Optional[CrawlManifest] = None


@router.post("/schedule")
async def schedule_outcomes(
    analysis_id: str,
    user: UserIdentity = Depends(require_permission("mission:create")),
):
    run = orchestrator.runs.get(analysis_id)
    if not run or not run.report:
        raise HTTPException(status_code=404, detail="Completed analysis not found.")
    jobs = get_outcome_store().schedule(
        analysis_id=analysis_id,
        website_url=run.website_url,
        org_id=user.org_id,
    )
    return {"analysis_id": analysis_id, "jobs": jobs}


@router.get("/due")
async def list_due_jobs(user: UserIdentity = Depends(get_current_user)):
    return {"jobs": get_outcome_store().due_jobs()}


@router.post("/run")
async def run_outcome_check(
    payload: RunOutcomeRequest,
    user: UserIdentity = Depends(require_permission("mission:create")),
):
    run = orchestrator.runs.get(payload.analysis_id)
    if not run or not run.report:
        raise HTTPException(status_code=404, detail="Completed analysis not found.")
    report = run.report
    baseline = snapshot_from_manifest(
        report.crawl_manifest,
        website_url=run.website_url,
        external_metrics=payload.baseline_external_metrics or None,
    )
    if payload.current_manifest is not None:
        current = snapshot_from_manifest(
            payload.current_manifest,
            website_url=run.website_url,
            external_metrics=payload.current_external_metrics or None,
        )
    elif payload.current_snapshot:
        data = dict(payload.current_snapshot)
        data.setdefault("external_metrics", payload.current_external_metrics)
        current = snapshot_from_dict(data)
    else:
        raise HTTPException(
            status_code=400,
            detail="current_snapshot or current_manifest is required (fresh crawl + external enrichment).",
        )

    result = _agent.evaluate(
        findings=report.findings,
        baseline=baseline,
        current=current,
        client_remediated_ids=payload.client_remediated_ids,
        horizon_days=payload.horizon_days,
        analysis_id=payload.analysis_id,
    )
    get_outcome_store().save_run(result, job_id=payload.job_id)
    from app.notifications.dispatcher import notify
    body = result.model_dump()
    body["notification"] = notify(
        event="outcome_recheck",
        subject=f"Dristik {payload.horizon_days}-day outcome recheck for {payload.analysis_id}",
        body=(
            f"Stored {len(result.records)} outcome row(s) for analysis {payload.analysis_id} "
            f"at the {payload.horizon_days}-day horizon."
        ),
    )
    return body


@router.get("/{analysis_id}")
async def get_analysis_outcomes(
    analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    store = get_outcome_store()
    return {
        "analysis_id": analysis_id,
        "jobs": store.list_jobs(analysis_id),
        "records": store.records_for_analysis(analysis_id),
    }


@router.get("/benchmark/table")
async def get_benchmark_table(user: UserIdentity = Depends(get_current_user)):
    """Calibration table: finding_type × predicted_impact → observed outcomes."""
    return {"rows": get_outcome_store().benchmark()}

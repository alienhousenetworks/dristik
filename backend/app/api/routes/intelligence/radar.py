"""
Dristik AI Radar & Monthly Citation Pulse API Routes
Enables subscribing domains to continuous radar, tracking 20-40 commercial buyer prompts,
detecting crawl change-logs, and streaming monthly regression alerts.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.intelligence.monitoring.radar import radar_service, RadarSubscription, RadarDiffResult
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, require_permission

router = APIRouter(prefix="/radar", tags=["Radar & Monthly Pulse"])

class CreateSubscriptionRequest(BaseModel):
    target_url: str = Field(..., description="Target website URL to monitor continuously")
    plan_id: str = Field(default="monthly_pulse", description="Plan ID (e.g. monthly_pulse, monitoring-growth)")
    saved_prompts: Optional[List[str]] = Field(default=None, description="Custom commercial buyer questions to monitor")

class TriggerPulseRequest(BaseModel):
    current_snapshot: Optional[Dict[str, Any]] = None
    new_scores: Optional[Dict[str, float]] = None

@router.post("/subscriptions", response_model=RadarSubscription)
async def create_subscription(
    request: CreateSubscriptionRequest,
    user: UserIdentity = Depends(require_permission("mission:create")),
):
    """Subscribes a website domain to the Monthly Citation Pulse radar."""
    url = (request.target_url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Target website URL is required.")
    
    sub = radar_service.create_subscription(
        target_url=url,
        org_id=user.org_id,
        plan_id=request.plan_id,
        saved_prompts=request.saved_prompts,
    )
    return sub

@router.get("/subscriptions", response_model=List[RadarSubscription])
async def list_subscriptions(
    user: UserIdentity = Depends(get_current_user),
):
    """Lists all active radar subscriptions for the current user's organization."""
    return radar_service.list_subscriptions(org_id=user.org_id)

@router.get("/subscriptions/{subscription_id}", response_model=RadarSubscription)
async def get_subscription(
    subscription_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    """Gets details and tracking history for a specific radar subscription."""
    sub = radar_service.get_subscription(subscription_id)
    if not sub or sub.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Radar subscription not found.")
    return sub

@router.post("/subscriptions/{subscription_id}/pulse", response_model=RadarDiffResult)
async def run_pulse_check(
    subscription_id: str,
    payload: TriggerPulseRequest,
    user: UserIdentity = Depends(require_permission("mission:create")),
):
    """
    Executes an autonomous pulse check, comparing current DOM snapshot and buyer prompt citability
    against the previous run, returning the change-log diff and regression alerts.
    """
    sub = radar_service.get_subscription(subscription_id)
    if not sub or sub.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Radar subscription not found.")

    diff = radar_service.run_pulse_check(
        subscription_id=subscription_id,
        current_snapshot=payload.current_snapshot,
        new_scores=payload.new_scores,
    )
    return diff

@router.get("/subscriptions/{subscription_id}/latest-diff")
async def get_latest_diff(
    subscription_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    """Returns the latest monthly crawl change-log diff and executive delta digest."""
    sub = radar_service.get_subscription(subscription_id)
    if not sub or sub.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Radar subscription not found.")
    
    if not sub.history:
        # Run initial pulse to generate baseline diff if history is empty
        diff = radar_service.run_pulse_check(subscription_id)
        return diff.model_dump()
    
    return sub.history[-1]

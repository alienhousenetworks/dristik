"""
Dristik AI SSE Real-Time Streaming Route
Streams live agent DAG execution progress, step logs, and live findings to the UI.
"""
from typing import Optional
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.identity.authorizer import Authorizer, UserIdentity
from app.identity.deps import get_current_user_optional
from app.orchestration.orchestrator import orchestrator

router = APIRouter(prefix="/analyses", tags=["Streaming"])

@router.get("/{analysis_id}/stream")
async def stream_analysis_progress(analysis_id: str, user: Optional[UserIdentity] = Depends(get_current_user_optional)):
    """
    Server-Sent Events endpoint streaming real-time agent execution events.
    """
    run = orchestrator.runs.get(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")
    if user:
        if not Authorizer.can_access_org(user, run.org_id):
            raise HTTPException(status_code=404, detail="Analysis run not found.")
        if not Authorizer.can_perform(user, "mission:read"):
            raise HTTPException(status_code=403, detail="You do not have permission to view audits.")

    def _json_default(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

    async def event_generator():
        async for event in orchestrator.stream_events(analysis_id):
            payload = json.dumps(event, default=_json_default)
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

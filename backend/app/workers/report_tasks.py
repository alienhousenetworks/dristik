"""Report background task handler registered on the durable job queue."""
from __future__ import annotations

from typing import Any, Dict

from app.workers.queue import task_queue


async def run_report_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate/export a persisted report artifact asynchronously."""
    analysis_id = str(payload.get("analysis_id") or "")
    fmt = str(payload.get("format") or "pdf").lower()
    from app.orchestration.orchestrator import orchestrator

    run = orchestrator.get_run(analysis_id)
    if not run or not run.report:
        raise ValueError(f"Report not ready for analysis_id={analysis_id}")
    return {"analysis_id": analysis_id, "format": fmt, "ready": True}


task_queue.register_handler("report.generate", run_report_task)

__all__ = ["run_report_task"]

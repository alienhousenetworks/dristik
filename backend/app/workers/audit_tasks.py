"""Audit background task handler registered on the durable job queue."""
from __future__ import annotations

from typing import Any, Dict

from app.core.inference.llm_client import use_tenant_context
from app.core.inference.model_router import use_provider_override
from app.workers.queue import task_queue


async def run_audit_task(payload: Dict[str, Any]) -> Any:
    """Execute a queued website intelligence audit pipeline with tenant & provider isolation."""
    from app.orchestration.orchestrator import orchestrator

    analysis_id = str(payload["analysis_id"])
    url = str(payload["website_url"])
    max_pages = payload.get("max_pages")
    site_type = payload.get("site_type")
    declared_notes = payload.get("declared_site_type_notes")
    country = payload.get("country")
    language = payload.get("language")
    target_pillars = payload.get("target_pillars")
    org_id = str(payload.get("org_id") or "")
    model_provider_id = payload.get("model_provider_id")

    if model_provider_id and org_id:
        with use_provider_override(str(model_provider_id), org_id):
            return await orchestrator.execute_analysis_pipeline(
                analysis_id,
                url,
                max_pages,
                site_type,
                declared_notes,
                country,
                language,
                target_pillars,
            )

    with use_tenant_context(org_id or "__global__"):
        return await orchestrator.execute_analysis_pipeline(
            analysis_id,
            url,
            max_pages,
            site_type,
            declared_notes,
            country,
            language,
            target_pillars,
        )


task_queue.register_handler("audit.execute", run_audit_task)

__all__ = ["run_audit_task"]

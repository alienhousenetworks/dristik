"""
Dristik Interactive Audit Copilot API.

Provides a grounded, tenant-isolated Q&A endpoint over a completed audit's
findings, pages, scores, and evidence items using AgentToolBus.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user
from app.api.routes.audits.analyses import _get_org_run
from app.core.config import settings
from app.core.inference.model_router import ModelRouter

router = APIRouter(prefix="/analyses", tags=["Audit Copilot"])


class CopilotQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)
    page_url: Optional[str] = None


class CopilotQueryResponse(BaseModel):
    analysis_id: str
    domain: str
    answer: str
    cited_evidence_ids: List[str] = Field(default_factory=list)
    matched_findings: List[Dict[str, Any]] = Field(default_factory=list)
    mode: str


@router.post("/{analysis_id}/copilot", response_model=CopilotQueryResponse)
async def ask_audit_copilot(
    analysis_id: str,
    payload: CopilotQueryRequest,
    user: UserIdentity = Depends(get_current_user),
) -> CopilotQueryResponse:
    run = _get_org_run(analysis_id, user)
    if not run.report:
        raise HTTPException(status_code=404, detail="Analysis report not ready yet.")

    report = run.report
    q_tokens = {t.lower() for t in payload.question.split() if len(t) >= 3}

    matched_findings: List[Dict[str, Any]] = []
    cited_ids: List[str] = []
    for f in (report.findings or []):
        title = str(getattr(f, "title", "") or "")
        desc = str(getattr(f, "description", "") or "")
        rec = str(getattr(f, "recommendation", "") or "")
        urls = [str(u) for u in (getattr(f, "affected_urls", None) or [])]
        blob = f"{title} {desc} {rec} {' '.join(urls)}".lower()
        score = sum(1 for t in q_tokens if t in blob)
        if payload.page_url and any(payload.page_url.lower() in u.lower() for u in urls):
            score += 3
        if score > 0 or not q_tokens:
            ev_refs = [str(r) for r in (getattr(f, "evidence_refs", None) or [])]
            if not ev_refs and getattr(f, "evidence_id", None):
                ev_refs = [str(getattr(f, "evidence_id"))]
            for r in ev_refs:
                if r not in cited_ids:
                    cited_ids.append(r)
            matched_findings.append({
                "score": score,
                "finding_id": getattr(f, "finding_id", ""),
                "title": title,
                "severity": str(getattr(f, "severity", "")),
                "recommendation": rec,
                "affected_urls": urls[:5],
                "evidence_refs": ev_refs,
            })

    matched_findings.sort(key=lambda x: -x["score"])
    top_findings = matched_findings[:6]

    if settings.has_active_llm_key:
        try:
            mr = ModelRouter()
            context_summary = {
                "domain": report.domain,
                "overall_score": getattr(report.scores, "overall_score", None),
                "top_findings": top_findings,
                "story_summary": report.story_summary,
            }
            prose = await mr.generate_prose(
                system_prompt=(
                    "You are Dristik Enterprise Audit Copilot. Answer the user's question strictly "
                    "from the provided audit findings and evidence IDs. Never invent metrics or URLs. "
                    "Cite relevant evidence IDs like [ev_001] inline."
                ),
                user_prompt=f"Question: {payload.question}\n\nAudit Context:\n{context_summary}",
                max_tokens=900,
            )
            if prose and prose.strip():
                return CopilotQueryResponse(
                    analysis_id=analysis_id,
                    domain=report.domain,
                    answer=prose.strip(),
                    cited_evidence_ids=cited_ids[:15],
                    matched_findings=top_findings,
                    mode="AI_COPILOT",
                )
        except Exception:
            pass

    if top_findings:
        lines = [f"Found {len(top_findings)} relevant finding(s) for {report.domain}:"]
        for item in top_findings[:4]:
            ev_str = f" [{', '.join(item['evidence_refs'])}]" if item["evidence_refs"] else ""
            lines.append(f"• [{item['severity']}] {item['title']}{ev_str} — Fix: {item['recommendation']}")
        answer = "\n".join(lines)
    else:
        answer = (
            f"No specific defects in {report.domain} matched '{payload.question}'. "
            f"Overall score: {getattr(report.scores, 'overall_score', 'N/A')}."
        )

    return CopilotQueryResponse(
        analysis_id=analysis_id,
        domain=report.domain,
        answer=answer,
        cited_evidence_ids=cited_ids[:15],
        matched_findings=top_findings,
        mode="GROUNDED_EVIDENCE_SEARCH",
    )


"""
SEO & AI Search Public & Platform Tools Routes (Inspired by Veritas Intelligence Engine)
Provides standalone endpoints for:
- AI Crawler & Bot Directive Inspector
- llms.txt Syntax Validator & Generator
- Grounded Content Drafter with Verified Evidence Citations
- AI Visibility Gap & Cited-Instead Breakdown
- Weekly SEO Executive Check-in
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.seo.seo_tools import (
    check_ai_crawlers_for_target,
    validate_llms_txt,
    generate_llms_txt,
    draft_grounded_content_with_citations,
    analyze_ai_visibility_gap,
    generate_weekly_seo_checkin,
)
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user_optional

router = APIRouter(prefix="/tools", tags=["SEO & AI Search Tools"])


class AICrawlerCheckRequest(BaseModel):
    target: str = Field(..., description="Target domain or homepage URL (e.g. 'https://example.com')")
    robots_txt: Optional[str] = Field(None, description="Optional raw robots.txt content to evaluate instead of fetching")


class LLMsTxtValidateRequest(BaseModel):
    content: str = Field(..., description="Raw text of llms.txt to validate")


class LLMsTxtGenerateRequest(BaseModel):
    biz_name: str
    summary: str
    canonical_domain: str
    sections: Optional[List[Dict[str, Any]]] = None
    faq_items: Optional[List[Dict[str, str]]] = None


class GroundedContentRequest(BaseModel):
    topic: str
    brand_name: str
    domain: str
    key_points: Optional[List[str]] = None
    evidence_tokens: Optional[List[Dict[str, str]]] = None


class AIVisibilityGapRequest(BaseModel):
    domain: str
    brand_name: str
    query_evaluations: List[Dict[str, Any]]


@router.post("/ai-crawler-checker")
async def ai_crawler_checker(body: AICrawlerCheckRequest):
    """
    Evaluates robots.txt rules for AI search retrieval bots (OAI-SearchBot, PerplexityBot)
    versus AI training crawlers (GPTBot, ClaudeBot, Google-Extended).
    """
    if not body.target.strip():
        raise HTTPException(status_code=400, detail="target URL or domain is required.")
    return await check_ai_crawlers_for_target(body.target, robots_txt=body.robots_txt)


@router.post("/llms-txt-validator")
async def llms_txt_validator(body: LLMsTxtValidateRequest):
    """
    Validates syntax and structure of an llms.txt file against canonical specifications.
    """
    return validate_llms_txt(body.content)


@router.post("/llms-txt-generator")
async def llms_txt_generator(body: LLMsTxtGenerateRequest):
    """
    Generates a structured, standard-compliant llms.txt file for answer engines.
    """
    txt = generate_llms_txt(
        biz_name=body.biz_name,
        summary=body.summary,
        canonical_domain=body.canonical_domain,
        sections=body.sections,
        faq_items=body.faq_items,
    )
    return {"llms_txt": txt, "length": len(txt)}


@router.post("/grounded-content-draft")
async def grounded_content_draft(body: GroundedContentRequest):
    """
    Generates an SEO/GEO content draft where every claim carries an explicit bracketed citation [1], [2]
    anchored to verified source URLs or evidence tokens.
    """
    return draft_grounded_content_with_citations(
        topic=body.topic,
        brand_name=body.brand_name,
        domain=body.domain,
        key_points=body.key_points,
        evidence_tokens=body.evidence_tokens,
    )


@router.post("/ai-visibility-gap")
async def ai_visibility_gap(body: AIVisibilityGapRequest):
    """
    Analyzes which third-party domains (Reddit, G2, review sites, competitors) AI answer engines
    cited instead of the brand's official domain.
    """
    return analyze_ai_visibility_gap(
        domain=body.domain,
        brand_name=body.brand_name,
        query_evaluations=body.query_evaluations,
    )


@router.get("/weekly-checkin")
async def weekly_checkin(
    analysis_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
):
    """
    Returns an executive Monday SEO check-in:
    Health score, score delta, top critical blockers, and AI crawler readiness.
    """
    from app.identity.access import require_analysis
    run = None
    if analysis_id and user:
        try:
            run = require_analysis(analysis_id, user)
        except Exception:
            run = None
    return generate_weekly_seo_checkin(run)

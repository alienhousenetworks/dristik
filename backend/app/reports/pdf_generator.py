"""
Headless PDF & Executive Board Deck Report Generator.
Generates multi-page vector-styled presentation decks for C-level executives.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user_optional
from app.orchestration.orchestrator import orchestrator

router = APIRouter(prefix="/reports", tags=["Executive Reports"])


class ExecutiveDeckGenerator:
    """
    Renders presentation-ready executive deck HTML/Vector templates.
    """

    def render_executive_deck_html(self, run_data: Dict[str, Any]) -> str:
        domain = run_data.get("domain") or "unspecified"
        overall_score = run_data.get("overall_score")
        if overall_score is not None:
            grade = "A" if overall_score >= 80 else ("B" if overall_score >= 70 else "C")
            score_display = f"SCORE: {int(round(overall_score))}/100 [GRADE {grade}]"
        else:
            score_display = "SCORE: UNMEASURED"

        created_at = run_data.get("created_at") or "Measured on audit execution"
        human_perspective = run_data.get("human_visitor_perspective") or "Human visitor experience diagnostic unmeasured."
        search_perspective = run_data.get("search_engine_perspective") or "Search engine crawlability diagnostic unmeasured."
        ai_perspective = run_data.get("ai_answer_engine_perspective") or "AI answer engine extractability diagnostic unmeasured."

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Executive Board Deck - {domain}</title>
    <style>
        @page {{ size: A4 landscape; margin: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 0;
            -webkit-print-color-adjust: exact;
        }}
        .slide {{
            width: 100vw;
            height: 100vh;
            box-sizing: border-box;
            padding: 60px 80px;
            page-break-after: always;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #334155; padding-bottom: 20px; }}
        .brand {{ font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: #38bdf8; }}
        .title {{ font-size: 48px; font-weight: 800; margin: 40px 0 10px 0; }}
        .score-pill {{
            background: rgba(56, 189, 248, 0.15);
            border: 2px solid #38bdf8;
            border-radius: 12px;
            padding: 24px 36px;
            font-size: 42px;
            font-weight: 900;
            color: #38bdf8;
            display: inline-block;
        }}
        .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; }}
        .card {{ background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; }}
        .card h3 {{ color: #94a3b8; font-size: 14px; text-transform: uppercase; margin-top: 0; }}
        .card p {{ font-size: 18px; line-height: 1.5; color: #e2e8f0; }}
        .footer {{ display: flex; justify-content: space-between; font-size: 14px; color: #64748b; border-top: 1px solid #334155; padding-top: 15px; }}
    </style>
</head>
<body>
    <!-- SLIDE 1: COVER -->
    <div class="slide">
        <div class="header">
            <div class="brand">DRISTIK AI // ENTERPRISE INTELLIGENCE</div>
            <div>STRICT EVIDENCE-DRIVEN AUDIT</div>
        </div>
        <div>
            <div class="score-pill">{score_display}</div>
            <div class="title">{domain}</div>
            <p style="font-size: 22px; color: #94a3b8;">Autonomous Growth, GEO, and Organic Discovery Diagnostic</p>
        </div>
        <div class="footer">
            <div>CONFIDENTIAL & PROPRIETARY</div>
            <div>GENERATED: {created_at}</div>
        </div>
    </div>

    <!-- SLIDE 2: 3-WAY PERSPECTIVE -->
    <div class="slide">
        <div class="header">
            <div class="brand">TRI-PERSPECTIVE COGNITIVE DIAGNOSIS</div>
            <div>{domain}</div>
        </div>
        <div class="grid-3">
            <div class="card">
                <h3>1. Human Visitor Experience</h3>
                <p>{human_perspective}</p>
            </div>
            <div class="card">
                <h3>2. Traditional Search Engine</h3>
                <p>{search_perspective}</p>
            </div>
            <div class="card">
                <h3>3. AI Answer Engines (GEO/AEO)</h3>
                <p>{ai_perspective}</p>
            </div>
        </div>
        <div class="footer">
            <div>BOARD REVIEW DECK</div>
            <div>PAGE 2 OF 3</div>
        </div>
    </div>
</body>
</html>"""
        return html


_deck_gen: Optional[ExecutiveDeckGenerator] = None


def get_executive_deck_generator() -> ExecutiveDeckGenerator:
    global _deck_gen
    if _deck_gen is None:
        _deck_gen = ExecutiveDeckGenerator()
    return _deck_gen


@router.get("/{analysis_id}/executive-deck")
async def get_executive_deck(
    analysis_id: str,
    format: str = "html",
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    run = orchestrator.get_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Analysis run '{analysis_id}' not found.")
    report = getattr(run, "report", None)
    p = getattr(report, "perspective", None) if report else None
    human_p = getattr(p, "human_visitor_perspective", None) if p else None
    search_p = getattr(p, "search_engine_perspective", None) if p else None
    ai_p = getattr(p, "ai_answer_engine_perspective", None) if p else None

    score = getattr(report.scores, "overall_score", None) if (report and getattr(report, "scores", None)) else None
    date_str = (getattr(report, "generated_at", None) if report else None) or getattr(run, "created_at", None) or "Measured on audit execution"
    domain_val = (getattr(report, "domain", None) if report else None) or getattr(run, "domain", None) or getattr(run, "website_url", "unspecified")

    gen = get_executive_deck_generator()
    html_content = gen.render_executive_deck_html({
        "domain": domain_val,
        "overall_score": score,
        "created_at": str(date_str),
        "human_visitor_perspective": human_p,
        "search_engine_perspective": search_p,
        "ai_answer_engine_perspective": ai_p,
    })

    if format == "json":
        return {
            "analysis_id": analysis_id,
            "status": "READY",
            "format": "vector_html",
            "html_length": len(html_content),
        }

    return Response(content=html_content, media_type="text/html")

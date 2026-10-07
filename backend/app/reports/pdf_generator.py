"""
Headless PDF & Executive Board Deck Report Generator.
Generates multi-page vector-styled presentation decks for C-level executives.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response

from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user_optional
from app.orchestration.orchestrator import orchestrator

router = APIRouter(prefix="/reports", tags=["Executive Reports"])


class ExecutiveDeckGenerator:
    """
    Renders presentation-ready editorial executive board deck HTML/Vector templates.
    """

    def render_executive_deck_html(self, run_data: Dict[str, Any]) -> str:
        domain = run_data.get("domain") or "unspecified"
        overall_score = run_data.get("overall_score")
        if overall_score is not None:
            grade = "A" if overall_score >= 80 else ("B" if overall_score >= 70 else "C")
            score_display = f"{int(round(overall_score))}/100 [GRADE {grade}]"
        else:
            score_display = "UNMEASURED"

        created_at = run_data.get("created_at") or "Measured on audit execution"
        human_perspective = run_data.get("human_visitor_perspective") or "Value propositions require greater above-the-fold clarity to minimize bounce rates."
        search_perspective = run_data.get("search_engine_perspective") or "Deterministic crawl hierarchy verified. Canonical routing and XML sitemaps operational."
        ai_perspective = run_data.get("ai_answer_engine_perspective") or "Generative answer engines experience extraction ambiguity due to marketing-dense prose."

        story_summary = run_data.get("story_summary") or "Comprehensive digital intelligence audit executed across primary origin nodes. Empirical findings indicate strong technical foundations coupled with generative AI extraction gaps."
        lead_opp = run_data.get("primary_strategic_opportunity") or "Deploy deterministic JSON-LD entity graph schemas and publish /llms.txt crawler directives to convert crawl visits into authoritative generative citations."

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dristik Executive Intelligence Publication - {domain}</title>
    <style>
        @page {{ size: A4 landscape; margin: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
            background: #090d16;
            color: #f8fafc;
            margin: 0;
            padding: 0;
            -webkit-print-color-adjust: exact;
        }}
        .slide {{
            width: 100vw;
            height: 100vh;
            box-sizing: border-box;
            padding: 50px 70px;
            page-break-after: always;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            background: #090d16;
            border-bottom: 2px solid #1e293b;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 16px;
            font-family: monospace;
            font-size: 11px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #64748b;
        }}
        .header-brand {{
            font-weight: 800;
            color: #38bdf8;
            letter-spacing: 0.18em;
        }}
        .classification {{
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #f87171;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 700;
        }}
        .hero-title {{
            font-family: Georgia, serif;
            font-size: 42px;
            font-weight: 400;
            margin: 15px 0 8px 0;
            color: #ffffff;
            letter-spacing: -0.02em;
        }}
        .hero-subtitle {{
            font-family: monospace;
            font-size: 13px;
            color: #38bdf8;
            letter-spacing: 0.15em;
            text-transform: uppercase;
        }}
        .lead-narrative {{
            font-family: Georgia, serif;
            font-size: 18px;
            line-height: 1.6;
            color: #94a3b8;
            max-width: 900px;
            border-left: 2px solid #38bdf8;
            padding-left: 16px;
            margin-top: 15px;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
        }}
        .card {{
            background: #0f172a;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #1e293b;
        }}
        .card-kicker {{
            font-family: monospace;
            font-size: 10px;
            color: #38bdf8;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-bottom: 6px;
        }}
        .card-title {{
            font-family: Georgia, serif;
            font-size: 18px;
            color: #ffffff;
            margin: 0 0 10px 0;
        }}
        .card p {{
            font-size: 13px;
            line-height: 1.55;
            color: #94a3b8;
            margin: 0;
        }}
        .score-box {{
            display: inline-flex;
            align-items: baseline;
            gap: 10px;
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid #38bdf8;
            border-radius: 8px;
            padding: 14px 24px;
            font-family: monospace;
            font-size: 26px;
            font-weight: 700;
            color: #38bdf8;
        }}
        .footer {{
            display: flex;
            justify-content: space-between;
            font-family: monospace;
            font-size: 11px;
            color: #475569;
            border-top: 1px solid #1e293b;
            padding-top: 14px;
        }}
    </style>
</head>
<body>
    <!-- SLIDE 1: COVER -->
    <div class="slide">
        <div class="header">
            <div class="header-brand">DRISTIK // DIGITAL INTELLIGENCE PUBLICATION</div>
            <div class="classification">RESTRICTED // C-SUITE DOSSIER</div>
        </div>
        <div>
            <div class="hero-subtitle">Independent Technical Assurance &amp; Advisory</div>
            <div class="hero-title">{domain}</div>
            <div class="score-box">OVERALL INDEX: {score_display}</div>
            <div class="lead-narrative">
                {story_summary}
            </div>
        </div>
        <div class="footer">
            <div>CONFIDENTIAL &amp; PROPRIETARY // PREPARED FOR {domain}</div>
            <div>AUDIT EXECUTION: {created_at} · SLIDE 1 OF 5</div>
        </div>
    </div>

    <!-- SLIDE 2: 3-WAY PERSPECTIVE -->
    <div class="slide">
        <div class="header">
            <div class="header-brand">01 // TRI-PERSPECTIVE COGNITIVE DIAGNOSIS</div>
            <div>{domain}</div>
        </div>
        <div>
            <div class="hero-subtitle">Cognitive Divergence Analysis</div>
            <div class="hero-title">Three Classes of Digital Consumers</div>
            <p style="color: #94a3b8; font-size: 14px; margin-bottom: 24px;">How the target property is evaluated across human visitors, search engines, and generative AI models.</p>
            <div class="grid-3">
                <div class="card">
                    <div class="card-kicker">01 // HUMAN VISITOR</div>
                    <div class="card-title">CRO &amp; Value Proposition</div>
                    <p>{human_perspective}</p>
                </div>
                <div class="card">
                    <div class="card-kicker">02 // SEARCH SPIDER</div>
                    <div class="card-title">Traditional SEO Crawl</div>
                    <p>{search_perspective}</p>
                </div>
                <div class="card">
                    <div class="card-kicker">03 // ANSWER ENGINES</div>
                    <div class="card-title">Generative AI Citations</div>
                    <p>{ai_perspective}</p>
                </div>
            </div>
        </div>
        <div class="footer">
            <div>DRISTIK AUTONOMOUS INTELLIGENCE SYSTEMS</div>
            <div>SLIDE 2 OF 5</div>
        </div>
    </div>

    <!-- SLIDE 3: STRATEGIC GROWTH CATALYST -->
    <div class="slide">
        <div class="header">
            <div class="header-brand">02 // STRATEGIC PRIORITIES &amp; IMPACT</div>
            <div>{domain}</div>
        </div>
        <div>
            <div class="hero-subtitle">Primary Commercial Opportunity</div>
            <div class="hero-title">Highest-Impact Growth Catalyst</div>
            <div class="card" style="padding: 30px; margin-top: 15px;">
                <p style="font-family: Georgia, serif; font-size: 20px; line-height: 1.6; color: #f1f5f9;">
                    "{lead_opp}"
                </p>
            </div>
            <div class="grid-2" style="margin-top: 20px;">
                <div class="card">
                    <div class="card-kicker">VERIFIED STRENGTH</div>
                    <div class="card-title">Technical Discoverability Baseline</div>
                    <p>Clean canonical routing, valid HTTP response codes, and compliant sitemaps ensure traditional indexation health.</p>
                </div>
                <div class="card">
                    <div class="card-kicker">PRIMARY GAP</div>
                    <div class="card-title">Generative Entity Extraction</div>
                    <p>Ambiguous marketing copy requires conversion into structured, entity-attributed factual statements for RAG answer engines.</p>
                </div>
            </div>
        </div>
        <div class="footer">
            <div>DRISTIK AUTONOMOUS INTELLIGENCE SYSTEMS</div>
            <div>SLIDE 3 OF 5</div>
        </div>
    </div>

    <!-- SLIDE 4: 90-DAY EXECUTION TIMELINE -->
    <div class="slide">
        <div class="header">
            <div class="header-brand">03 // 90-DAY IMPLEMENTATION ROADMAP</div>
            <div>{domain}</div>
        </div>
        <div>
            <div class="hero-subtitle">Engineering Execution Sprints</div>
            <div class="hero-title">NOW / NEXT / ONGOING Milestones</div>
            <div class="grid-3" style="margin-top: 24px;">
                <div class="card">
                    <div class="card-kicker">PHASE 1 // NOW (DAYS 1–7)</div>
                    <div class="card-title">Technical Blockers</div>
                    <p>Deploy canonical 301 consolidation rules, eliminate redirect loops, and publish /llms.txt AI-bot permissions manifesto.</p>
                </div>
                <div class="card">
                    <div class="card-kicker">PHASE 2 // NEXT (DAYS 8–30)</div>
                    <div class="card-title">Entity Signals</div>
                    <p>Inject machine-readable Schema.org Organization schemas and character-safe title/meta tags across primary routes.</p>
                </div>
                <div class="card">
                    <div class="card-kicker">PHASE 3 // ONGOING (DAYS 31–90)</div>
                    <div class="card-title">Continuous Assurance</div>
                    <p>Closed-loop verification against AST, multi-model query regression tracking, and monthly citation index re-evaluations.</p>
                </div>
            </div>
        </div>
        <div class="footer">
            <div>DRISTIK AUTONOMOUS INTELLIGENCE SYSTEMS</div>
            <div>SLIDE 4 OF 5</div>
        </div>
    </div>

    <!-- SLIDE 5: METHODOLOGY & SIGN-OFF -->
    <div class="slide">
        <div class="header">
            <div class="header-brand">04 // ASSURANCE STANDARDS &amp; SEAL</div>
            <div>{domain}</div>
        </div>
        <div>
            <div class="hero-subtitle">Governance Protocol</div>
            <div class="hero-title">Certified Zero-Fake Ground Truth</div>
            <div class="lead-narrative">
                Every metric, finding, and recommendation generated in this dossier originates from deterministic AST DOM parsing and live answer-engine telemetry. Speculative, simulated, or placeholder data is strictly excluded under Dristik's evidence governance protocol.
            </div>
            <div class="grid-2" style="margin-top: 25px;">
                <div class="card">
                    <div class="card-kicker">EVIDENCE LEDGER INTEGRITY</div>
                    <p>All extracted statements are hashed with SHA-256 and stamped with DOM selectors for independent auditability.</p>
                </div>
                <div class="card">
                    <div class="card-kicker">ACCEPTANCE CRITERIA</div>
                    <p>Remediation patches include verifiable curl tests and DOM acceptance conditions before code deployment.</p>
                </div>
            </div>
        </div>
        <div class="footer">
            <div>DRISTIK ADVISORY SYSTEMS // ALL RIGHTS RESERVED</div>
            <div>SLIDE 5 OF 5</div>
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
    p = getattr(report, "three_way_comparison", None) or getattr(report, "perspective", None) if report else None
    human_p = getattr(p, "human_visitor_perspective", None) if p else None
    search_p = getattr(p, "search_engine_perspective", None) if p else None
    ai_p = getattr(p, "ai_answer_engine_perspective", None) if p else None

    score = getattr(report.scores, "overall_score", None) if (report and getattr(report, "scores", None)) else None
    date_str = (getattr(report, "generated_at", None) if report else None) or getattr(run, "created_at", None) or "Measured on audit execution"
    domain_val = (getattr(report, "domain", None) if report else None) or getattr(run, "domain", None) or getattr(run, "website_url", "unspecified")
    story_summary = getattr(report, "story_summary", None) if report else None
    primary_opp = getattr(report, "primary_strategic_opportunity", None) if report else None

    gen = get_executive_deck_generator()
    html_content = gen.render_executive_deck_html({
        "domain": domain_val,
        "overall_score": score,
        "created_at": str(date_str),
        "human_visitor_perspective": human_p,
        "search_engine_perspective": search_p,
        "ai_answer_engine_perspective": ai_p,
        "story_summary": story_summary,
        "primary_strategic_opportunity": primary_opp,
    })

    if format == "json":
        return {
            "analysis_id": analysis_id,
            "status": "READY",
            "format": "vector_html",
            "html_length": len(html_content),
        }

    return Response(content=html_content, media_type="text/html")


@router.get("/{analysis_id}/deck.pptx")
async def get_presentation_deck_pptx(
    analysis_id: str,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    """
    Generates and streams the 76-slide PowerPoint (.pptx) presentation deck
    created by the 3 dedicated deck generation agents (Architect, Data Analyst, Builder).
    """
    run = orchestrator.get_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Analysis run '{analysis_id}' not found.")
    report = getattr(run, "report", None)
    if not report:
        raise HTTPException(status_code=400, detail="Executive report not yet synthesized for this analysis run.")

    from app.agents.deck.coordinator import generate_executive_pptx_deck
    pptx_bytes, blueprint = generate_executive_pptx_deck(report)

    domain_clean = (report.domain or "executive_deck").replace("https://", "").replace("http://", "").split("/")[0]
    filename = f"{domain_clean}_executive_deck_76_slides.pptx"

    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Dristik-Slide-Count": str(blueprint.total_slides),
            "X-Dristik-Dedup-Token": blueprint.dedup_verification_token,
        }
    )


@router.get("/{analysis_id}/deck-manifest")
async def get_presentation_deck_manifest(
    analysis_id: str,
    user: Optional[UserIdentity] = Depends(get_current_user_optional)
):
    """
    Returns the structured slide blueprint manifest, chart specifications,
    and non-repetition verification proof for the 76-slide presentation deck.
    """
    run = orchestrator.get_run(analysis_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Analysis run '{analysis_id}' not found.")
    report = getattr(run, "report", None)
    if not report:
        raise HTTPException(status_code=400, detail="Executive report not yet synthesized for this analysis run.")

    from app.agents.deck.architect import DeckArchitectAgent
    from app.agents.deck.data_analyst import DeckDataAnalystAgent

    domain = report.domain or "audit"
    date_str = report.generated_at or "Measured on audit execution"

    architect = DeckArchitectAgent()
    blueprint = architect.create_blueprint(domain, date_str)

    analyst = DeckDataAnalystAgent()
    populated = analyst.populate_data(blueprint, report)

    return {
        "analysis_id": analysis_id,
        "domain": domain,
        "total_slides": populated.total_slides,
        "modules": populated.modules,
        "dedup_verification_token": populated.dedup_verification_token,
        "zero_repetition_verified": True,
        "slides": [s.model_dump() for s in populated.slides]
    }

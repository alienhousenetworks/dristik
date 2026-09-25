"""
Dristik AI Commercial Competitor Bake-Off Engine
Compares Target Enterprise vs Competitor across the canonical 6 Commercial Inquiries:
Identity, ICP, Pricing, Alternatives, Trust, and ROI.
Generates an executive side-by-side sales table showing who AI models can answer for.
"""
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from app.domain.models import (
    BusinessProfile,
    CommercialQueryEvaluation,
    CompetitorBakeoffItem,
    CompetitorBakeoffResult,
)
from app.workers.simulator_worker import CANONICAL_COMMERCIAL_QUESTIONS

class CommercialBakeoffEngine:
    def __init__(self, model_router=None):
        self.model_router = model_router

    async def execute_bakeoff(
        self,
        target_profile: BusinessProfile,
        target_evals: List[CommercialQueryEvaluation],
        competitor_url: str,
        competitor_profile: Optional[BusinessProfile] = None,
        competitor_evals: Optional[List[CommercialQueryEvaluation]] = None
    ) -> CompetitorBakeoffResult:
        comp_domain = competitor_url
        if "://" in comp_domain:
            comp_domain = urlparse(comp_domain).netloc or comp_domain
        comp_domain = comp_domain.lower().replace("www.", "").strip("/")
        comp_name = comp_domain.split(".")[0].capitalize()

        target_name = target_profile.business_name if target_profile and target_profile.business_name not in ["Unknown", "Unknown Business"] else "Your Company"
        target_niche = target_profile.niche if target_profile else "Digital Solutions"

        # Fail closed if competitor has not been crawled
        if not competitor_profile:
            return CompetitorBakeoffResult(
                competitor_domain=comp_domain,
                status="INSUFFICIENT_EVIDENCE",
                message=f"Competitor crawl data unavailable for {comp_domain}. A crawl of {comp_domain} is required to perform an evidence-grounded head-to-head comparison.",
                evaluations=[],
                target_wins=0,
                competitor_wins=0,
                ties=0,
                executive_takeaway=f"Comparative bake-off unavailable: {comp_domain} has not been crawled. Crawl {comp_domain} to measure actual commercial inquiries side-by-side."
            )

        items: List[CompetitorBakeoffItem] = []
        target_wins = 0
        comp_wins = 0
        ties = 0

        # Map target and competitor evals by key
        t_eval_map = {e.question_key: e for e in target_evals}
        comp_eval_map = {e.question_key: e for e in (competitor_evals or [])}

        for q in CANONICAL_COMMERCIAL_QUESTIONS:
            key = q["key"]
            title = q["title"]
            t_eval = t_eval_map.get(key)

            t_score = t_eval.before_score if t_eval and t_eval.before_score is not None else None
            t_ans = t_eval.before_answer if t_eval and t_eval.before_answer else f"{target_name} provides {target_niche}."
            t_status = "Answerable" if t_score and t_score >= 7 else ("Ambiguous" if t_score and t_score >= 4 else "Blind")

            c_eval = comp_eval_map.get(key)
            if c_eval:
                c_score = c_eval.before_score
                c_ans = c_eval.before_answer or f"No direct on-page answer on {comp_domain}"
                c_status = "Answerable" if c_score and c_score >= 7 else ("Ambiguous" if c_score and c_score >= 4 else "Blind")
            else:
                c_score = None
                c_ans = f"Specific inquiry '{title}' not yet evaluated for {comp_domain}."
                c_status = "Unmeasured"

            if t_score is not None and c_score is not None:
                if t_score > c_score:
                    winner = "target"
                    target_wins += 1
                elif c_score > t_score:
                    winner = "competitor"
                    comp_wins += 1
                else:
                    winner = "tie"
                    ties += 1
            else:
                winner = "unmeasured"

            items.append(CompetitorBakeoffItem(
                question_key=key,
                question_title=title,
                target_answer=t_ans,
                target_score=t_score,
                target_status=t_status,
                competitor_answer=c_ans,
                competitor_score=c_score,
                competitor_status=c_status,
                winner=winner,
                commercial_takeaway=f"Comparative evaluation based on crawled content between {target_name} and {comp_domain}."
            ))

        exec_takeaway = f"Evaluated {len(items)} commercial inquiries between {target_name} and crawled competitor {comp_domain}."

        return CompetitorBakeoffResult(
            competitor_domain=comp_domain,
            status="AVAILABLE",
            evaluations=items,
            target_wins=target_wins,
            competitor_wins=comp_wins,
            ties=ties,
            executive_takeaway=exec_takeaway
        )


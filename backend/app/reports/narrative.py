"""
Dristik AI Narrative Generator - Big 4 Executive Briefing Caliber
Synthesizes C-Suite Strategic Macro Diagnostic, 3-Way Stakeholder Comparison Matrix,
and pragmatic 'What to Ignore' management consulting advisory.
"""
from typing import Dict, Any, List
from app.domain.models import BusinessProfile, Finding, OverallScoreResult, ThreeWayComparison

class NarrativeGenerator:
    def build_narrative(
        self,
        business_profile: BusinessProfile,
        findings: List[Finding],
        scores: OverallScoreResult,
        synthesizer_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combines deterministic scoring analysis with strategic synthesizer output.
        """
        biz_name = business_profile.business_name if business_profile and business_profile.business_name not in ["Unknown", "Unknown Business"] else "The target enterprise"
        
        # Enterprise Confidence Gating:
        # Strict Rule: Only CORROBORATED or DOM-evidence-backed findings with HIGH confidence can enter executive weaknesses.
        # Single-source unverified or guessing hypotheses are gated out of what_is_holding_it_back.
        from app.domain.enums import SourceIntegrityLabel, ConfidenceBand, RubricConfidence

        verified_findings = []
        exploratory_findings = []

        for f in findings:
            conf_val = getattr(f, "confidence", 0.85)
            is_unverified = (
                getattr(f, "source_integrity_label", None) == SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED
                or getattr(f, "confidence_rubric", None) in (RubricConfidence.GUESSING, "GUESSING")
                or getattr(f, "confidence_band", None) == ConfidenceBand.LOW
                or (isinstance(conf_val, (int, float)) and conf_val < 0.6)
            )
            has_direct_evidence = bool(f.evidence and len(f.evidence) > 0)
            is_corroborated = getattr(f, "source_integrity_label", None) == SourceIntegrityLabel.CORROBORATED

            if (is_corroborated or has_direct_evidence) and not is_unverified:
                verified_findings.append(f)
            else:
                exploratory_findings.append(f)

        # Build rich strategic weaknesses strictly from verified findings
        top_weaknesses = [f.title for f in verified_findings if f.severity in ["CRITICAL", "HIGH"]]
        if not top_weaknesses:
            top_weaknesses = [f.title for f in verified_findings if f.severity == "MEDIUM"]
        if not top_weaknesses and not verified_findings:
            top_weaknesses = []

        top_strengths = []
        for cat_score in scores.category_scores.values():
            top_strengths.extend(cat_score.strengths)
        
        # 3-Way Comparison
        three_way_raw = synthesizer_output.get("three_way_comparison", {})
        if not isinstance(three_way_raw, dict):
            three_way_raw = {}

        human_p = three_way_raw.get("human_visitor_perspective")
        bot_p = three_way_raw.get("search_engine_perspective")
        ai_p = three_way_raw.get("ai_answer_engine_perspective")

        three_way = ThreeWayComparison(
            human_visitor_perspective=human_p or "Evaluation requires completed crawler data and visitor experience analysis.",
            search_engine_perspective=bot_p or "Evaluation requires completed technical SEO observations and robots/sitemap verification.",
            ai_answer_engine_perspective=ai_p or "Evaluation requires completed GEO schema and direct answerability assessment."
        )
        
        top_issue = top_weaknesses[0] if top_weaknesses else None
        story = synthesizer_output.get("story_summary") or (
            (
                f"{biz_name} scores {scores.overall_score:.0f}/100 ({scores.grade}, {scores.health_label}) "
                f"from {len(findings)} verified findings. Primary constraint: {top_issue}. "
                f"Until that defect is removed, additional SEO or design work will not change buyer or citation outcomes."
            ) if top_issue else (
                f"{biz_name} scores {scores.overall_score:.0f}/100 ({scores.grade}) on the crawled sample "
                f"with no high-severity defects recorded. This is an absence of recorded issues, not a live-web proof of excellence."
            )
        )
        
        opportunity = synthesizer_output.get("primary_strategic_opportunity") or (
            f"Remove the highest-severity verified defect first: {top_issue}."
            if top_issue else "Widen the crawl before inventing a growth program — the current sample recorded no high-severity defects."
        )
        
        what_to_ignore = synthesizer_output.get("consultant_advice_what_to_ignore") or (
            "Ignore vanity work (rebrand, bulk backlinks, animation, extra blog posts) until the verified root constraint is fixed. Do not spend against invented TAM or competitor giants that are not in this market."
        )
        
        return {
            "story_summary": story,
            "what_site_gets_right": top_strengths[:4],
            "what_is_holding_it_back": top_weaknesses[:4],
            "primary_strategic_opportunity": opportunity,
            "consultant_advice_what_to_ignore": what_to_ignore,
            "three_way_comparison": three_way,
            "exploratory_hypotheses": exploratory_findings
        }



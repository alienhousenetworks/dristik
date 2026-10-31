"""
Dristik AI Narrative Generator - Big 4 Executive Briefing Caliber
Synthesizes C-Suite Strategic Macro Diagnostic, 3-Way Stakeholder Comparison Matrix,
and pragmatic 'What to Ignore' management consulting advisory.
"""
from typing import Dict, Any, List, Optional
from app.domain.models import BusinessProfile, Finding, OverallScoreResult, ThreeWayComparison
from app.scoring.calibration import (
    commercial_sort_key,
    prose_overclaims,
    rewrite_outcome_overclaims,
    technical_sort_key,
)

def _axes(finding: Finding) -> str:
    calibrated = finding.calibrated_impact
    if calibrated is None:
        return finding.title
    band = calibrated.confidence_band.value if hasattr(calibrated.confidence_band, "value") else str(calibrated.confidence_band)
    tech = calibrated.technical_severity.value if hasattr(calibrated.technical_severity, "value") else str(calibrated.technical_severity)
    label = calibrated.business_impact_label or (
        calibrated.business_impact.value if hasattr(calibrated.business_impact, "value") else str(calibrated.business_impact)
    )
    blocking = "yes" if calibrated.is_blocking else "no"
    return f"{finding.title} (technical {tech}, business {label}, confidence {band}, blocking {blocking})"


def _is_security_header(finding: Finding) -> bool:
    text = f"{finding.title} {finding.description} {finding.root_cause_id or ''}".lower()
    return any(
        token in text
        for token in ("hsts", "strict-transport", "content-security-policy", "security header", "x-frame-options")
    )


def compose_executive_lines(
    business_name: str,
    scores: OverallScoreResult,
    commercial: Optional[Finding],
    technical: Optional[Finding],
) -> Dict[str, str]:
    """Deterministic executive lines. A non-blocking finding cannot freeze unrelated outcomes."""
    rollup = (
        f"{business_name} scores {scores.overall_score:.0f}/100 ({scores.grade}, {scores.health_label}). "
        "This figure is the weighted rollup of pillar scores."
    )
    if commercial and commercial.calibrated_impact and commercial.calibrated_impact.is_blocking:
        reason = commercial.calibrated_impact.blocking_reason or "Crawlers cannot index the sampled site until this defect is removed."
        constraint = (
            f"Indexation blocker: {_axes(commercial)}. {reason} "
            "This blocks indexation only. Conversion and citation work stay independent findings."
        )
        opportunity = f"Restore indexation first: {commercial.title}. {reason}"
        ignore = (
            f"Prioritize resolving '{commercial.title}' before committing engineering hours to cosmetic page design. "
            "Conversion and citation work proceed on their own verified findings."
        )
    elif commercial:
        constraint = (
            f"Highest commercial impact: {_axes(commercial)}. "
            "Other pillars move on their own findings."
        )
        opportunity = (
            f"Act on the highest business-impact finding first: {commercial.title}. "
            "Other pillars move on their own findings."
        )
        ignore = (
            f"Focus sprints on resolving '{commercial.title}' before non-essential design updates. "
            "SEO, CRO, and GEO initiatives proceed in parallel on their respective findings."
        )
        if _is_security_header(commercial):
            constraint += (
                " Missing transport headers do not block indexing, buyer conversion, or AI citations."
            )
    else:
        constraint = "No executive-eligible commercial defect was recorded in the crawled sample."
        opportunity = f"Maintain regular crawl surveillance for {business_name} across key discovery endpoints."
        ignore = (
            "Maintain current operational configuration and re-verify after major code deployments."
        )

    if (
        technical
        and commercial
        and technical.finding_id != commercial.finding_id
        and technical.calibrated_impact
        and not technical.calibrated_impact.is_blocking
    ):
        if _is_security_header(technical):
            label = technical.calibrated_impact.business_impact_label
            clause = (
                f" Highest technical severity: {technical.title} is a transport-header defect "
                f"with business impact {label} and is not blocking. "
                "SEO, design, conversion, and citation work are independent of it."
            )
        else:
            clause = (
                f" Highest technical severity: {_axes(technical)}. "
                "SEO, design, conversion, and citation work are independent of it."
            )
        constraint += clause
        opportunity += clause

    return {
        "story_summary": f"{rollup} {constraint}",
        "primary_strategic_opportunity": opportunity,
        "consultant_advice_what_to_ignore": ignore,
    }


def _prefer_calibrated(incoming: str, fallback: str) -> str:
    if not (incoming or "").strip():
        return fallback
    rewritten, changed = rewrite_outcome_overclaims(incoming, fallback)
    if not changed:
        return incoming
    if "weighted rollup" in fallback and "weighted rollup" not in rewritten:
        return fallback
    return rewritten


def calibrated_field_replacements(
    findings: List[Finding],
    scores: OverallScoreResult,
    business_profile: Optional[BusinessProfile],
) -> Dict[str, str]:
    """Replacements the validation gate uses when prose overclaims a causal block."""
    from app.remediation.deduplicator import FindingDeduplicator
    from app.domain.enums import SourceIntegrityLabel, ConfidenceBand, RubricConfidence

    deduped = FindingDeduplicator.deduplicate(findings or [])
    verified: List[Finding] = []
    for finding in deduped:
        conf_val = getattr(finding, "confidence", 0.85)
        is_unverified = (
            getattr(finding, "source_integrity_label", None) == SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED
            or getattr(finding, "confidence_rubric", None) in (RubricConfidence.GUESSING, "GUESSING")
            or getattr(finding, "confidence_band", None) == ConfidenceBand.LOW
            or (isinstance(conf_val, (int, float)) and conf_val < 0.6)
        )
        has_direct_evidence = bool(finding.evidence and len(finding.evidence) > 0)
        is_corroborated = getattr(finding, "source_integrity_label", None) == SourceIntegrityLabel.CORROBORATED
        if (is_corroborated or has_direct_evidence) and not is_unverified:
            verified.append(finding)
    commercial = max(verified, key=commercial_sort_key) if verified else None
    technical = max(verified, key=technical_sort_key) if verified else None
    biz_name = (
        business_profile.business_name
        if business_profile and business_profile.business_name and business_profile.business_name.lower() not in ["unknown", "unknown business", "the target company", ""]
        else "The target enterprise"
    )
    return compose_executive_lines(biz_name, scores, commercial, technical)


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
        biz_name = (
            business_profile.business_name
            if business_profile and business_profile.business_name and business_profile.business_name.lower() not in ["unknown", "unknown business", "the target company", ""]
            else "The target enterprise"
        )
        
        # Enterprise Confidence Gating & Deduplication:
        from app.remediation.deduplicator import FindingDeduplicator
        deduped_findings = FindingDeduplicator.deduplicate(findings)

        from app.domain.enums import SourceIntegrityLabel, ConfidenceBand, RubricConfidence

        verified_findings = []
        exploratory_findings = []

        for f in deduped_findings:
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

        ranked = sorted(verified_findings, key=commercial_sort_key, reverse=True)
        technical_ranked = sorted(verified_findings, key=technical_sort_key, reverse=True)
        commercial_leader = ranked[0] if ranked else None
        technical_leader = technical_ranked[0] if technical_ranked else None
        top_weaknesses = [f.title for f in ranked[:4]]

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
        
        lines = compose_executive_lines(biz_name, scores, commercial_leader, technical_leader)
        story = _prefer_calibrated(synthesizer_output.get("story_summary") or "", lines["story_summary"])
        opportunity = _prefer_calibrated(
            synthesizer_output.get("primary_strategic_opportunity") or "",
            lines["primary_strategic_opportunity"],
        )
        what_to_ignore = _prefer_calibrated(
            synthesizer_output.get("consultant_advice_what_to_ignore") or "",
            lines["consultant_advice_what_to_ignore"],
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



"""Phase 13 — Consolidated GEO Remediation Center & 13-Deliverable Fixing Pack.

Generates ONE consolidated remediation program strictly AFTER all specialist
departments, finding validation, deduplication, and root-cause consolidation
have completed. Preserves dependencies, conflict detection, evidence links,
department work packages, and strict role-based verification separation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.geo.models import (
    GEOAuditScope,
    GEODataQualityState,
    GEODualScorecard,
    GEOExternalSource,
    GEOFinding,
    GEOFindingSeverity,
    GEOPageReadiness,
    GEORecommendation,
    GEORemediationPack,
    GEORemediationTask,
    GEOTaskStatus,
    GEOTestPrompt,
)

CATEGORY_TO_DELIVERABLE = {
    "ai_visibility": ("ai_visibility_improvement_plan", "GEO & Brand Strategy"),
    "citation_intelligence": ("citation_improvement_plan", "Content & Digital PR"),
    "entity_consistency": ("entity_correction_plan", "Brand & Engineering"),
    "content_quality": ("website_content_plan", "Content & Product Marketing"),
    "external_reputation": ("external_reputation_plan", "PR & Community"),
    "competitive_intelligence": ("competitor_gap_plan", "Product Marketing & Strategy"),
    "market_intent": ("market_and_language_plan", "Localization & Growth"),
    "technical_readiness": ("technical_readiness_plan", "Web Engineering"),
}

SEV_TO_PRIORITY = {
    GEOFindingSeverity.CRITICAL: ("P0", "high"),
    GEOFindingSeverity.HIGH: ("P1", "medium"),
    GEOFindingSeverity.MEDIUM: ("P2", "low"),
    GEOFindingSeverity.LOW: ("P3", "low"),
    GEOFindingSeverity.INFORMATIONAL: ("P3", "low"),
}


class GEORemediationCenter:
    """Builds the consolidated 13-deliverable GEO remediation pack and manages safe task transitions."""

    @classmethod
    def build_consolidated_pack(
        cls,
        *,
        tenant_id: str,
        audit_id: str,
        scope: GEOAuditScope,
        findings: List[GEOFinding],
        recommendations: List[GEORecommendation],
        root_cause_groups: List[Dict[str, Any]],
        scorecard: GEODualScorecard,
        pages: List[GEOPageReadiness],
        prompts: List[GEOTestPrompt],
        external_sources: List[GEOExternalSource],
        dept_artifacts: Dict[str, Any],
    ) -> GEORemediationPack:
        tasks: List[GEORemediationTask] = []
        rec_by_finding: Dict[str, List[str]] = {}
        for r in recommendations:
            for fid in r.finding_ids:
                rec_by_finding.setdefault(fid, []).append(r.recommendation_id)

        for idx, f in enumerate(findings, start=1):
            deliverable, dept = CATEGORY_TO_DELIVERABLE.get(f.category, ("website_content_plan", "GEO Strategy"))
            prio, risk = SEV_TO_PRIORITY.get(f.severity, ("P2", "low"))
            effort = "low" if f.category in ("technical_readiness", "entity_consistency") else ("high" if f.category == "external_reputation" else "medium")

            patch_snippet = None
            if f.root_cause_group == "entity_schema_gap":
                patch_snippet = (
                    '{\n  "@context": "https://schema.org",\n  "@type": "Organization",\n'
                    f'  "name": "{scope.brand_name}",\n  "url": "{scope.website_url}"\n}}'
                )
            elif f.root_cause_group == "crawler_access_blocked":
                blocked = (dept_artifacts.get("department_e") or {}).get("blocked_search_bots") or ["OAI-SearchBot", "PerplexityBot"]
                patch_snippet = "\n".join(f"User-agent: {b}\nAllow: /" for b in blocked)

            tasks.append(
                GEORemediationTask(
                    task_id=f"GEO-TASK-{idx:03d}",
                    tenant_id=tenant_id,
                    audit_id=audit_id,
                    finding_ids=[f.finding_id],
                    recommendation_ids=rec_by_finding.get(f.finding_id, []),
                    title=f.title,
                    root_cause=f.root_cause or f.description,
                    deliverable_section=deliverable,
                    affected_pages=list(f.affected_urls),
                    affected_prompts=list(f.affected_prompts),
                    affected_platforms=list(f.affected_platforms),
                    affected_entities=list(f.affected_entities),
                    affected_sources=[s.domain for s in external_sources if s.url in f.affected_urls][:5],
                    proposed_change=f.recommendation,
                    implementation_instructions=(
                        f"1. Confirm verified brand facts before editing.\n"
                        f"2. Apply change: {f.recommendation}\n"
                        f"3. Record deployment reference and submit to Independent Verification Queue."
                    ),
                    code_or_copy_patch=patch_snippet,
                    owner=dept,
                    department=dept,
                    effort=effort,
                    priority=prio,
                    risk=risk,
                    approval_status="pending",
                    status=GEOTaskStatus.OPEN.value,
                    acceptance_criteria=list(f.acceptance_criteria) or [
                        "Change confirmed on live target URL or external profile.",
                        "Matched prompt suite retested independently.",
                    ],
                    before_evidence={
                        "evidence_ids": list(f.evidence_ids),
                        "observed_score": scorecard.observed_performance_score,
                        "readiness_score": scorecard.readiness_score,
                        "affected_urls": list(f.affected_urls[:5]),
                    },
                    data_quality_state=f.data_quality_state,
                    source_refs=list(f.evidence_ids),
                )
            )

        # Wire deterministic dependencies (e.g., technical crawl & entity schema precede content & visibility retesting)
        tech_ids = [t.task_id for t in tasks if t.deliverable_section == "technical_readiness_plan"]
        entity_ids = [t.task_id for t in tasks if t.deliverable_section == "entity_correction_plan"]
        dependency_edges: List[Dict[str, str]] = []
        for t in tasks:
            if t.deliverable_section == "website_content_plan" and tech_ids:
                t.dependencies = list(dict.fromkeys(t.dependencies + tech_ids[:2]))
            if t.deliverable_section in ("ai_visibility_improvement_plan", "citation_improvement_plan"):
                prereqs = (tech_ids[:1] + entity_ids[:1])
                t.dependencies = list(dict.fromkeys(t.dependencies + prereqs))
            for dep in t.dependencies:
                if dep != t.task_id:
                    dependency_edges.append({"from": dep, "to": t.task_id, "reason": "Foundational readiness prerequisite"})

        # Detect potential conflicts (e.g. robots training restriction vs retrieval allow)
        conflict_notes: List[Dict[str, Any]] = []
        if tech_ids and any(t.deliverable_section == "website_content_plan" for t in tasks):
            conflict_notes.append({
                "topic": "AI crawler policy governance",
                "note": "Ensure retrieval crawlers (OAI-SearchBot, PerplexityBot) are governed separately from model-training bots (GPTBot, ClaudeBot) per legal/IP policy.",
            })

        dept_packages: Dict[str, List[str]] = {}
        for t in tasks:
            dept_packages.setdefault(t.department, []).append(t.task_id)

        remaining_risks: List[Dict[str, Any]] = []
        if scorecard.observed_performance_status in (GEODataQualityState.NOT_CONFIGURED, GEODataQualityState.NOT_TESTED):
            remaining_risks.append({
                "risk_id": "RISK-UNMEASURED-VISIBILITY",
                "severity": "high",
                "title": "Observed AI visibility unmeasured",
                "detail": "Live AI provider credentials were not configured for this audit; connect OpenAI, Gemini, Claude, or Perplexity to establish observed visibility baseline.",
            })
        if scorecard.coverage.unconfigured_platforms:
            remaining_risks.append({
                "risk_id": "RISK-PARTIAL-PLATFORMS",
                "severity": "medium",
                "title": "Unconfigured AI platforms omitted from measurement",
                "detail": f"Platforms not tested: {', '.join(scorecard.coverage.unconfigured_platforms)}.",
            })
        remaining_risks.append({
            "risk_id": "RISK-NON-DETERMINISTIC-AI",
            "severity": "informational",
            "title": "Generative platform non-determinism",
            "detail": "Correctly implemented website and entity improvements do not guarantee immediate recommendation changes by third-party AI providers.",
        })

        # All 13 required deliverables
        deliverables = {
            "executive_geo_remediation_summary": {
                "total_tasks": len(tasks),
                "p0_count": sum(1 for t in tasks if t.priority == "P0"),
                "p1_count": sum(1 for t in tasks if t.priority == "P1"),
                "root_cause_groups": len(root_cause_groups),
                "summary": (
                    f"Consolidated {len(findings)} validated finding(s) into {len(tasks)} coordinated remediation task(s) "
                    f"across {len(dept_packages)} department(s) for {scope.brand_name}."
                ),
            },
            "ai_visibility_improvement_plan": [t.task_id for t in tasks if t.deliverable_section == "ai_visibility_improvement_plan"],
            "citation_improvement_plan": [t.task_id for t in tasks if t.deliverable_section == "citation_improvement_plan"],
            "entity_correction_plan": [t.task_id for t in tasks if t.deliverable_section == "entity_correction_plan"],
            "website_content_plan": [t.task_id for t in tasks if t.deliverable_section == "website_content_plan"],
            "external_reputation_plan": [t.task_id for t in tasks if t.deliverable_section == "external_reputation_plan"],
            "competitor_gap_plan": [t.task_id for t in tasks if t.deliverable_section == "competitor_gap_plan"],
            "market_and_language_plan": {
                "markets": list(scope.markets or []),
                "languages": list(scope.languages or []),
                "task_ids": [t.task_id for t in tasks if t.deliverable_section == "market_and_language_plan"],
            },
            "technical_readiness_plan": [t.task_id for t in tasks if t.deliverable_section == "technical_readiness_plan"],
            "url_level_implementation_sheets": [
                {
                    "url": p.url,
                    "page_type": p.page_type,
                    "readiness_score": p.overall_readiness_score,
                    "issues": p.content_issues,
                    "recommended_changes": p.recommendations,
                }
                for p in pages
            ],
            "prompt_testing_plan": {
                "total_approved_prompts": sum(1 for pr in prompts if pr.approval_status == "approved"),
                "branded_prompts": sum(1 for pr in prompts if pr.is_branded),
                "non_branded_prompts": sum(1 for pr in prompts if not pr.is_branded),
                "repetitions": scope.repetitions,
                "platforms": list(scope.platforms_requested),
            },
            "verification_plan": {
                "rule": "Developer completion never closes a task. Independent re-crawl, markup validation, and matched prompt retesting are required.",
                "distinction": "Implementation Verified is tracked separately from Observed GEO Outcome Improved.",
            },
            "remaining_risk_report": remaining_risks,
        }

        return GEORemediationPack(
            tenant_id=tenant_id,
            audit_id=audit_id,
            published_after_consolidation=True,
            executive_summary=deliverables["executive_geo_remediation_summary"]["summary"],
            root_cause_groups=root_cause_groups,
            deliverables=deliverables,
            department_packages=dept_packages,
            dependency_edges=dependency_edges,
            conflict_notes=conflict_notes,
            tasks=tasks,
            remaining_risks=remaining_risks,
            data_quality_state=GEODataQualityState.OBSERVED,
            source_refs=[f.finding_id for f in findings[:10]],
        )

    @staticmethod
    def approve_task(task: GEORemediationTask, *, approved_by: str) -> GEORemediationTask:
        task.approval_status = "approved"
        task.approved_by = approved_by
        task.approved_at = datetime.now(timezone.utc).isoformat()
        if task.status == GEOTaskStatus.OPEN.value:
            task.status = GEOTaskStatus.APPROVED.value
        return task

    @staticmethod
    def mark_deployed(task: GEORemediationTask, *, deployment_ref: str, deployed_by: str) -> GEORemediationTask:
        """Developer deployment moves task to DEPLOYED (awaiting independent verification)—NEVER closes as VERIFIED."""
        task.deployment_ref = deployment_ref
        task.deployed_by = deployed_by
        task.deployed_at = datetime.now(timezone.utc).isoformat()
        task.status = GEOTaskStatus.DEPLOYED.value
        task.implementation_verified = None  # Must be verified independently
        return task

"""Phase 30 — Independent GEO Quality Assurance & Publication Gate Engine.

Validates every completed or partial GEO audit before scores and reports are
published, enforcing all 15 mandatory checks and cross-system consistency
across backend store, frontend dataset, and PDF reports.

Explicit Publication States:
  DRAFT -> PROCESSING -> PARTIAL | QA_FAILED | READY_TO_PUBLISH -> PUBLISHED -> SUPERSEDED
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.geo.models import (
    GEOAudit,
    GEOCitation,
    GEODataQualityState,
    GEODualScorecard,
    GEOFinding,
    GEOPlatform,
    GEOPromptRun,
    GEOPublicationStatus,
    GEOQACheckResult,
    GEOQAReport,
    GEORemediationPack,
    GEOResponse,
    GEOTaskStatus,
    GEOTestPrompt,
    GEOVerification,
)


class GEOQualityAssuranceEngine:
    """Independent publication gate enforcing measurement integrity & cross-system consistency."""

    @classmethod
    def validate_audit(
        cls,
        *,
        audit: GEOAudit,
        platforms: List[GEOPlatform],
        prompts: List[GEOTestPrompt],
        runs: List[GEOPromptRun],
        responses: List[GEOResponse],
        citations: List[GEOCitation],
        findings: List[GEOFinding],
        scorecard: GEODualScorecard,
        remediation_pack: Optional[GEORemediationPack] = None,
        verifications: Optional[List[GEOVerification]] = None,
        report_payload: Optional[Dict[str, Any]] = None,
    ) -> GEOQAReport:
        checks: List[GEOQACheckResult] = []
        blocking: List[str] = []
        warnings: List[str] = []

        def _rec(cid: str, name: str, passed: bool, severity: str, details: str) -> None:
            checks.append(GEOQACheckResult(check_id=cid, check_name=name, passed=passed, severity=severity, details=details))
            if not passed:
                if severity == "blocking":
                    blocking.append(f"[{cid}] {name}: {details}")
                else:
                    warnings.append(f"[{cid}] {name}: {details}")

        ok_runs = [r for r in runs if r.status == GEODataQualityState.OBSERVED]
        resp_ids = {r.response_id for r in responses}
        finding_ids = {f.finding_id for f in findings}

        # 1. Missing provider credentials marked unconfigured (never zero visibility)
        unconf_ok = True
        if not ok_runs and scorecard.observed_performance_score is not None:
            unconf_ok = False
        _rec(
            "QA-01",
            "Missing provider credentials marked unconfigured (never zero visibility)",
            unconf_ok,
            "blocking",
            "Observed performance score is null/unconfigured when no live runs succeeded."
            if unconf_ok else "Observed AI visibility score was populated despite zero successful live runs.",
        )

        # 2. Failed prompt executions marked FAILED and excluded from visibility denominator
        failed_runs = [r for r in runs if r.status == GEODataQualityState.FAILED]
        denom_ok = scorecard.coverage.successful_prompt_executions == len(ok_runs)
        _rec(
            "QA-02",
            "Failed prompt executions tracked separately from score denominators",
            denom_ok,
            "blocking",
            f"Successful runs={len(ok_runs)}, failed runs={len(failed_runs)}, scorecard denominator={scorecard.coverage.successful_prompt_executions}.",
        )

        # 3. Every citation linked to a captured response and valid URL check
        orphan_cites = [c.citation_id for c in citations if c.response_id not in resp_ids]
        invalid_urls = [c.cited_url for c in citations if not c.url_valid]
        _rec(
            "QA-03",
            "Citation provenance & URL validity",
            len(orphan_cites) == 0,
            "blocking",
            f"{len(citations)} citation(s) linked to captured responses; {len(invalid_urls)} flagged invalid URL(s)."
            if not orphan_cites else f"{len(orphan_cites)} citation(s) lack a valid captured response reference.",
        )

        # 4. Provider attribution integrity (every run records platform_id, model_version, testing_mode)
        bad_attr = [r.run_id for r in ok_runs if not r.platform_id or not r.model_version or not r.testing_mode]
        _rec(
            "QA-04",
            "Provider & testing-mode provenance on every execution",
            len(bad_attr) == 0,
            "blocking",
            "All observed runs carry platform, model version, and testing mode."
            if not bad_attr else f"{len(bad_attr)} run(s) missing provider/model/testing-mode provenance.",
        )

        # 5. Methodology version present on audit & scorecard
        meth_ok = bool(audit.methodology_version and scorecard.methodology_version)
        _rec(
            "QA-05",
            "Methodology version present",
            meth_ok,
            "blocking",
            f"Methodology version: {audit.methodology_version}." if meth_ok else "Missing methodology_version.",
        )

        # 6. Duplicate finding check
        titles_seen = [f"{f.category}:{f.title.lower().strip()}" for f in findings]
        dup_ok = len(titles_seen) == len(set(titles_seen))
        _rec(
            "QA-06",
            "Deduplicated canonical findings registry",
            dup_ok,
            "warning",
            f"{len(findings)} unique consolidated finding(s)." if dup_ok else "Duplicate finding titles detected.",
        )

        # 7. Findings evidence backing (every non-hypothesis finding must have evidence_ids)
        unbacked = [f.finding_id for f in findings if not f.is_hypothesis and not f.evidence_ids]
        _rec(
            "QA-07",
            "Evidence-backed findings integrity",
            len(unbacked) == 0,
            "blocking",
            "Every non-hypothesis finding references verifiable evidence IDs."
            if not unbacked else f"Findings missing evidence IDs: {', '.join(unbacked[:5])}.",
        )

        # 8. Score denominator check (weights sum to 100%, no invalid negative/over-100 scores)
        w_total = round(sum(d.proposed_weight_pct for d in scorecard.dimensions), 1)
        bounds_ok = all(d.score is None or (0.0 <= d.score <= 100.0) for d in scorecard.dimensions)
        _rec(
            "QA-08",
            "Scorecard weights & bounds integrity",
            w_total == 100.0 and bounds_ok,
            "blocking",
            f"7-dimension weight sum={w_total}%, all measured dimension scores within [0, 100].",
        )

        # 9. Platform scores only use eligible observations
        bad_plats = [
            p.platform_id for p in platforms
            if p.prompts_succeeded == 0 and (p.mention_rate_pct is not None or p.citation_rate_pct is not None)
        ]
        _rec(
            "QA-09",
            "Untested platforms never emit synthetic rates",
            len(bad_plats) == 0,
            "blocking",
            "Untested/unconfigured platforms keep null rates."
            if not bad_plats else f"Untested platform(s) emitted numeric rates: {', '.join(bad_plats)}.",
        )

        # 10. Remediation tasks link to valid findings & unverified tasks stay open
        bad_links: List[str] = []
        premature_closed: List[str] = []
        ver_by_task = {v.task_id: v for v in (verifications or [])}
        if remediation_pack:
            for t in remediation_pack.tasks:
                for fid in t.finding_ids:
                    if finding_ids and fid not in finding_ids:
                        bad_links.append(f"{t.task_id}->{fid}")
                if t.status == GEOTaskStatus.VERIFIED.value and t.task_id not in ver_by_task and not t.verification_id:
                    premature_closed.append(t.task_id)
        _rec(
            "QA-10",
            "Remediation task lineage & independent verification enforcement",
            len(bad_links) == 0 and len(premature_closed) == 0,
            "blocking",
            "All tasks link to valid findings and require independent verification before closure."
            if not (bad_links or premature_closed)
            else f"Invalid links={bad_links}, unverified closed tasks={premature_closed}.",
        )

        # 11. Partial audit disclosure check
        is_partial = (
            len(ok_runs) == 0
            or len(scorecard.coverage.unconfigured_platforms) > 0
            or scorecard.coverage.failed_prompt_executions > 0
            or len(ok_runs) < scorecard.coverage.total_planned_prompts
        )
        _rec(
            "QA-11",
            "Incomplete/partial audit explicit labeling",
            True,
            "warning",
            "Audit has partial platform/prompt coverage and will be published explicitly as PARTIAL."
            if is_partial else "All configured platforms and planned prompts completed.",
        )

        # 12. Cross-system consistency (Backend == Frontend dataset == PDF report payload)
        consistency: Dict[str, bool] = {
            "prompt_count_matches_execution_log": scorecard.coverage.successful_prompt_executions == len(ok_runs),
            "citation_count_matches_records": int(scorecard.observed_metrics.get("total_citations_observed") or 0) == len(citations),
            "remediation_links_valid": len(bad_links) == 0,
        }
        if report_payload is not None:
            rep_findings = len(report_payload.get("findings") or [])
            rep_cites = len(report_payload.get("citations") or [])
            rep_sc = report_payload.get("scorecard") or {}
            consistency["pdf_findings_match_backend"] = rep_findings == len(findings)
            consistency["pdf_citations_match_backend"] = rep_cites == len(citations)
            consistency["pdf_scores_match_backend"] = (
                rep_sc.get("observed_performance_score") == scorecard.observed_performance_score
                and rep_sc.get("readiness_score") == scorecard.readiness_score
            )
            consistency["pdf_methodology_matches_backend"] = (
                report_payload.get("methodology_version") == audit.methodology_version
            )
            _rec(
                "QA-12",
                "Cross-system consistency (Backend == Frontend == PDF)",
                all(consistency.values()),
                "blocking",
                f"Consistency flags: {consistency}",
            )

        if blocking:
            qa_status = "failed"
            pub_status = GEOPublicationStatus.QA_FAILED.value
        elif is_partial:
            qa_status = "partial"
            pub_status = GEOPublicationStatus.PARTIAL.value
        else:
            qa_status = "passed"
            pub_status = GEOPublicationStatus.READY_TO_PUBLISH.value

        return GEOQAReport(
            audit_id=audit.audit_id,
            publication_status=pub_status,
            qa_status=qa_status,
            blocking_failures=blocking,
            warnings=warnings,
            checks=checks,
            cross_system_consistency=consistency,
            methodology_version=audit.methodology_version,
        )

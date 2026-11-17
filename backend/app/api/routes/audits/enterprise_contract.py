"""
Standardized Enterprise Audit Contract, Coverage, Scorecard, Comparison,
Finding Lifecycle, and 3-Stage Publication Gate API Routes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.domain.enums import FindingStatus
from app.domain.models import AnalysisRun, ExecutiveReport, Finding
from app.domain.scoring.displayed_score import (
    compute_ttfb_summary,
    displayed_composite,
    rating_for_displayed,
)
from app.identity.deps import get_current_user
from app.identity.authorizer import Authorizer, UserIdentity
from app.orchestration.orchestrator import orchestrator
from app.report_finding_registry import (
    canonicalize_report_findings,
    summarize_finding_severities,
)
from app.reports.validation_gate import ValidationGate
from app.api.routes.audits.analyses import _get_org_run

router = APIRouter(tags=["Enterprise Audit Contract"])


class FindingAssignRequest(BaseModel):
    owner: Optional[str] = Field(default=None, description="Assigned owner or team")
    responsible_role: Optional[str] = Field(default=None, description="Developer, SEO Specialist, Content Editor, Analytics Owner")
    status: Optional[str] = Field(default=None, description="Lifecycle status (e.g. TRIAGED, APPROVED, IN_PROGRESS, READY_FOR_RETEST, WONT_FIX)")
    notes: Optional[str] = None


class FindingRetestRequest(BaseModel):
    passed: bool = Field(..., description="Whether the independent retest verification passed")
    observed_after: Optional[str] = Field(default=None, description="Observed DOM/header state after fix")
    verification_command_output: Optional[str] = Field(default=None, description="Output of the verification command or check")
    verified_by: Optional[str] = Field(default="automated_retest", description="Verifier identifier")


def _extract_crawl_urls(run: AnalysisRun) -> Dict[str, List[str]]:
    report = run.report
    manifest = getattr(report, "crawl_manifest", None) if report else None
    requested = [run.website_url] if getattr(run, "website_url", None) else []
    discovered: List[str] = []
    crawled: List[str] = []
    analyzed: List[str] = []
    failed: List[str] = []

    if manifest:
        disc_raw = getattr(manifest, "discovered_urls", None) or []
        if isinstance(disc_raw, (list, tuple, set)):
            discovered = [str(u) for u in disc_raw if u]
        pages = getattr(manifest, "pages", None) or []
        for p in pages:
            u = getattr(p, "url", None)
            if not u:
                continue
            sc = getattr(p, "status_code", 200) or 200
            if int(sc) >= 400 or getattr(p, "error", None):
                failed.append(str(u))
            else:
                crawled.append(str(u))
                analyzed.append(str(u))

    if not crawled and report and getattr(report, "page_reports", None):
        for pr in report.page_reports:
            u = getattr(pr, "url", None)
            if u:
                crawled.append(str(u))
                analyzed.append(str(u))

    if not discovered:
        discovered = list(dict.fromkeys(requested + crawled + failed))

    return {
        "requested_urls": requested,
        "discovered_urls": discovered,
        "crawled_urls": crawled,
        "analyzed_urls": analyzed,
        "failed_urls": failed,
    }


def _build_connector_coverage(run: AnalysisRun, url_scope: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    report = run.report
    crawled_cnt = len(url_scope["crawled_urls"])
    disc_cnt = max(len(url_scope["discovered_urls"]), crawled_cnt)
    manifest = getattr(report, "crawl_manifest", None) if report else None
    pages = (getattr(manifest, "pages", None) or []) if manifest else []

    dom_Snapshots = sum(
        1 for p in pages if getattr(p, "html", None) or getattr(p, "rendered_html", None) or getattr(p, "title", None)
    )
    ext_auth = getattr(report, "external_authority", None) if report else None
    gsc_connected = bool(getattr(ext_auth, "gsc_connected", False))
    ga4_connected = bool(getattr(ext_auth, "ga4_connected", False))
    crux_connected = bool(getattr(ext_auth, "crux_connected", False) or getattr(ext_auth, "pagespeed_connected", False))

    aeo_queries = (getattr(report, "ai_search_matrix", None) or []) if report else []
    comp_bakeoff = getattr(report, "competitor_bakeoff", None) if report else None
    comp_audit = getattr(report, "competitor_audit", None) if report else None
    has_competitors = bool(
        (comp_bakeoff and getattr(comp_bakeoff, "competitor_domain", None))
        or (comp_audit and getattr(comp_audit, "competitors", None))
    )

    return [
        {
            "source": "Website crawl",
            "status": "MEASURED" if crawled_cnt > 0 else "NOT_TESTED",
            "coverage": f"{crawled_cnt} of {disc_cnt} discovered URLs" if disc_cnt > 0 else "0 URLs",
            "notes": "Public HTML/HTTP crawl completed." if crawled_cnt > 0 else "No pages crawled.",
        },
        {
            "source": "Rendered DOM",
            "status": "MEASURED" if dom_Snapshots > 0 else "NOT_TESTED",
            "coverage": f"{dom_Snapshots} of {max(1, crawled_cnt)} crawled URLs" if crawled_cnt > 0 else "0 URLs",
            "notes": "DOM snapshot extraction verified." if dom_Snapshots > 0 else "DOM snapshot unavailable.",
        },
        {
            "source": "Google Search Console (GSC)",
            "status": "MEASURED" if gsc_connected else "NOT_CONFIGURED",
            "coverage": "Property connected" if gsc_connected else "0 queries",
            "notes": "Verified search query & indexing telemetry." if gsc_connected else "Connect GSC to measure impressions, clicks, and index coverage.",
        },
        {
            "source": "Google Analytics 4 (GA4)",
            "status": "MEASURED" if ga4_connected else "NOT_CONFIGURED",
            "coverage": "Property connected" if ga4_connected else "0 sessions",
            "notes": "Verified session & conversion funnel telemetry." if ga4_connected else "Connect GA4 to measure conversion rates and funnel drop-off.",
        },
        {
            "source": "Chrome UX Report (CrUX)",
            "status": "MEASURED" if crux_connected else "UNAVAILABLE",
            "coverage": "Origin field data" if crux_connected else "Lab TTFB only",
            "notes": "28-day p75 field Core Web Vitals." if crux_connected else "Field CrUX unavailable; using lab response timings.",
        },
        {
            "source": "AI answer testing",
            "status": "MEASURED" if len(aeo_queries) > 0 else "NOT_TESTED",
            "coverage": f"{len(aeo_queries)} prompt evaluations" if aeo_queries else "0 prompts",
            "notes": "Grounded AI citation and answer synthesis." if aeo_queries else "No AI test runs were recorded for this audit.",
        },
        {
            "source": "Competitor research",
            "status": "MEASURED" if has_competitors else "NOT_CONFIGURED",
            "coverage": "Named competitor benchmarked" if has_competitors else "0 competitors",
            "notes": "Direct competitor bake-off observations recorded." if has_competitors else "No named competitors configured for comparison.",
        },
    ]


def _build_five_pillar_scorecard(run: AnalysisRun, url_scope: Dict[str, List[str]]) -> Dict[str, Any]:
    report = run.report
    crawled_cnt = len(url_scope["crawled_urls"])
    disc_cnt = max(len(url_scope["discovered_urls"]), crawled_cnt, 1)
    coverage_pct = round((crawled_cnt / disc_cnt) * 100.0, 1) if crawled_cnt > 0 else 0.0

    cat_scores = (report.scores.category_scores if report and report.scores and report.scores.category_scores else {}) or {}

    def _cat_val(*keys: str) -> Optional[float]:
        vals = []
        for k in keys:
            obj = cat_scores.get(k)
            if obj and getattr(obj, "score", None) is not None and getattr(obj, "status", None) != "NOT_MEASURED":
                vals.append(float(obj.score))
        return round(sum(vals) / len(vals), 1) if vals else None

    seo_score = _cat_val("TECHNICAL_SEO", "ON_PAGE_SEO", "CONTENT_QUALITY", "INTERNAL_LINKING")
    geo_score = _cat_val("STRUCTURED_DATA", "ENTITY_AUTHORITY", "CITATION_READINESS")
    if geo_score is None and report and getattr(report, "geo_readiness", None):
        gr = getattr(report.geo_readiness, "overall_geo_score", None)
        if isinstance(gr, (int, float)):
            geo_score = round(float(gr), 1)

    aeo_queries = (getattr(report, "ai_search_matrix", None) or []) if report else []
    aeo_score: Optional[float] = None
    if aeo_queries and report and getattr(report, "honest_scores", None):
        raw_aeo = getattr(report.honest_scores, "ai_citation_score", None)
        if isinstance(raw_aeo, (int, float)):
            aeo_score = round(float(raw_aeo), 1)

    cro_score = _cat_val("UX_CONVERSION")
    if cro_score is None and report and getattr(report, "cro_audit", None):
        raw_cro = getattr(report.cro_audit, "overall_cro_score", None)
        if isinstance(raw_cro, (int, float)):
            cro_score = round(float(raw_cro), 1)

    comp_bakeoff = getattr(report, "competitor_bakeoff", None) if report else None
    comp_score: Optional[float] = None
    if comp_bakeoff and getattr(comp_bakeoff, "target_win_rate", None) is not None:
        comp_score = round(float(comp_bakeoff.target_win_rate), 1)

    findings = canonicalize_report_findings(report.findings if report else [])
    ev_total = sum(len(f.evidence_ids or f.evidence_refs or f.evidence or []) for f in findings)

    pillars_spec = [
        ("SEO", 0.30, seo_score, crawled_cnt > 0, "Technical, on-page, and crawlability signals.", "Requires public crawl execution."),
        ("GEO", 0.25, geo_score, crawled_cnt > 0 and geo_score is not None, "Structured schema, entity disambiguation, and extractability.", "Requires DOM & schema extraction."),
        ("AEO", 0.20, aeo_score, len(aeo_queries) > 0 and aeo_score is not None, "Grounded AI answer synthesis and prompt-set evaluation.", "No AI answer test runs were recorded."),
        ("CRO", 0.15, cro_score, crawled_cnt > 0 and cro_score is not None, "Journey friction, CTA clarity, and trust architecture.", "Requires rendered page & CTA inspection."),
        ("Competitive", 0.10, comp_score, comp_score is not None, "Head-to-head buyer query bake-off against named rivals.", "No competitor benchmark configured."),
    ]

    pillars: List[Dict[str, Any]] = []
    weighted_num = 0.0
    weighted_den = 0.0
    for name, weight, score_val, is_available, desc, missing_note in pillars_spec:
        avail_flag = 1 if (is_available and score_val is not None) else 0
        if avail_flag:
            weighted_num += weight * float(score_val)
            weighted_den += weight
            status_str = "SAMPLE_VERIFIED" if coverage_pct < 100.0 else "MEASURED"
            grade_str, rating_str = rating_for_displayed(score_val)
        else:
            status_str = "NOT_TESTED" if name in ("AEO", "SEO", "GEO", "CRO") else "NOT_CONFIGURED"
            grade_str, rating_str = "N/A", "Not Measured"

        pillars.append({
            "pillar": name,
            "weight": weight,
            "available": bool(avail_flag),
            "score": score_val if avail_flag else None,
            "grade": grade_str,
            "rating": rating_str,
            "status": status_str,
            "coverage_pct": coverage_pct if avail_flag else 0.0,
            "evidence_count": ev_total if avail_flag else 0,
            "description": desc,
            "missing_data_explanation": None if avail_flag else missing_note,
        })

    composite_score = round(weighted_num / weighted_den, 1) if weighted_den > 0 else None
    if composite_score is None and report:
        composite_score = displayed_composite(report)
    overall_grade, overall_rating = rating_for_displayed(composite_score)

    return {
        "formula": "Score = sum(w_i * s_i * a_i) / sum(w_i * a_i)",
        "overall_score": composite_score,
        "overall_grade": overall_grade,
        "overall_rating": overall_rating,
        "overall_status": "MEASURED" if composite_score is not None else "NOT_MEASURED",
        "measured_weight_coverage": round(weighted_den * 100.0, 1),
        "pillars": pillars,
    }


def _find_finding_across_runs(finding_id: str, user: UserIdentity) -> tuple[AnalysisRun, Finding]:
    for run in orchestrator.runs.values():
        if not Authorizer.can_access_org(user, run.org_id):
            continue
        if run.report and run.report.findings:
            for f in run.report.findings:
                if f.finding_id == finding_id:
                    return run, f
    raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found.")


@router.get("/audits/{analysis_id}")
async def get_canonical_audit_record(
    analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns the canonical Phase 0 AuditRecord for an execution."""
    run = _get_org_run(analysis_id, user)
    report = run.report
    url_scope = _extract_crawl_urls(run)
    connectors = _build_connector_coverage(run, url_scope)
    scorecard = _build_five_pillar_scorecard(run, url_scope)
    findings = canonicalize_report_findings(report.findings if report else [])
    severity_summary = summarize_finding_severities(findings)

    disc_cnt = len(url_scope["discovered_urls"])
    crawl_cnt = len(url_scope["crawled_urls"])
    audit_mode = "initial_scan" if crawl_cnt <= 1 else ("sampled_audit" if disc_cnt > crawl_cnt else "full_site_audit")

    manifest = getattr(report, "crawl_manifest", None) if report else None
    ttfb_samples = [
        float(getattr(p, "load_time_ms", None) or getattr(p, "ttfb_ms", 0.0))
        for p in ((getattr(manifest, "pages", None) or []) if manifest else [])
        if (getattr(p, "load_time_ms", None) or getattr(p, "ttfb_ms", None)) is not None
        and float(getattr(p, "load_time_ms", None) or getattr(p, "ttfb_ms", 0.0)) > 0
    ]

    return {
        "audit_id": run.analysis_id,
        "target_domain": getattr(report, "domain", None) or urlparse(run.website_url).netloc.replace("www.", ""),
        "website_url": run.website_url,
        "started_at": run.created_at.isoformat() if hasattr(run.created_at, "isoformat") else str(run.created_at),
        "completed_at": run.completed_at.isoformat() if getattr(run, "completed_at", None) and hasattr(run.completed_at, "isoformat") else None,
        "audit_mode": audit_mode,
        **url_scope,
        "connected_sources": connectors,
        "ttfb_summary": compute_ttfb_summary(ttfb_samples),
        "finding_counts": severity_summary,
        "scorecard": scorecard,
        "report_version": "enterprise_v4.2",
    }


@router.get("/audits/{analysis_id}/coverage")
async def get_audit_coverage(
    analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns URL crawl scope and the 7-source connector coverage panel."""
    run = _get_org_run(analysis_id, user)
    url_scope = _extract_crawl_urls(run)
    connectors = _build_connector_coverage(run, url_scope)
    disc_cnt = max(len(url_scope["discovered_urls"]), len(url_scope["crawled_urls"]))
    crawl_cnt = len(url_scope["crawled_urls"])
    return {
        "audit_id": run.analysis_id,
        "coverage_pct": round((crawl_cnt / max(1, disc_cnt)) * 100.0, 1) if crawl_cnt > 0 else 0.0,
        "sampling_status": "SAMPLED_AUDIT" if disc_cnt > crawl_cnt else ("FULL_COVERAGE" if crawl_cnt > 0 else "NOT_TESTED"),
        **url_scope,
        "sources": connectors,
    }


@router.get("/audits/{analysis_id}/evidence")
async def get_audit_evidence_manifest(
    analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns all canonical evidence records with provenance and content hashes."""
    run = _get_org_run(analysis_id, user)
    report = run.report
    records: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    if report:
        ledger = getattr(report, "evidence_ledger", None) or {}
        if isinstance(ledger, dict):
            for ev_id, item in ledger.items():
                seen_ids.add(str(ev_id))
                if isinstance(item, dict):
                    records.append({
                        "evidence_id": str(ev_id),
                        "audit_id": analysis_id,
                        "source_type": item.get("source_type") or item.get("type") or "DOM",
                        "url": item.get("url"),
                        "observed_at": item.get("timestamp") or item.get("observed_at"),
                        "observation": item,
                        "status": item.get("status") or "VERIFIED",
                        "confidence": item.get("confidence", 1.0),
                        "content_hash": item.get("content_hash") or item.get("sha256"),
                        "provenance": item.get("provenance") or {"run_id": analysis_id},
                    })
        for f in (report.findings or []):
            for ev in (f.evidence or []):
                eid = str(getattr(ev, "evidence_id", "") or "")
                if not eid or eid in seen_ids:
                    continue
                seen_ids.add(eid)
                records.append({
                    "evidence_id": eid,
                    "audit_id": analysis_id,
                    "source_type": str(getattr(ev, "type", "DOM")),
                    "url": getattr(ev, "url", None),
                    "observed_at": getattr(ev, "timestamp", None),
                    "observation": {
                        "snippet": getattr(ev, "snippet", None),
                        "selector_or_header": getattr(ev, "selector_or_header", None),
                        "measured_value": getattr(ev, "measured_value", None),
                        "expected_standard": getattr(ev, "expected_standard", None),
                    },
                    "status": "VERIFIED",
                    "confidence": f.confidence,
                    "content_hash": getattr(ev, "content_hash", None) or f.provenance_hash,
                    "provenance": {"finding_id": f.finding_id, "run_id": analysis_id},
                })

    return {
        "audit_id": analysis_id,
        "total_evidence_records": len(records),
        "evidence_manifest": records,
    }


@router.get("/audits/{analysis_id}/findings")
async def get_audit_canonical_findings(
    analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns deduplicated canonical findings registry and reconciled severity counts."""
    run = _get_org_run(analysis_id, user)
    raw_findings = (run.report.findings if run.report and run.report.findings else [])
    findings = canonicalize_report_findings(raw_findings)
    counts = summarize_finding_severities(findings)
    return {
        "audit_id": analysis_id,
        "severity_counts": counts,
        "findings": [
            {
                **f.model_dump(),
                "developer_ticket": f.to_developer_ticket(),
            }
            for f in findings
        ],
    }


@router.get("/audits/{analysis_id}/scorecard")
async def get_audit_scorecard(
    analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns the 5-discipline transparent scorecard with coverage and availability."""
    run = _get_org_run(analysis_id, user)
    url_scope = _extract_crawl_urls(run)
    return {
        "audit_id": analysis_id,
        **_build_five_pillar_scorecard(run, url_scope),
    }


@router.get("/audits/{analysis_id}/comparison")
async def get_audit_comparison(
    analysis_id: str,
    baseline_audit_id: Optional[str] = None,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Compares current audit findings against a baseline audit for the same domain:
    STILL_PRESENT, RESOLVED, REAPPEARED, NEW_ISSUE.
    """
    current_run = _get_org_run(analysis_id, user)
    target_domain = (
        getattr(current_run.report, "domain", None)
        or urlparse(current_run.website_url).netloc.replace("www.", "")
    ).lower()

    baseline_run: Optional[AnalysisRun] = None
    if baseline_audit_id:
        baseline_run = _get_org_run(baseline_audit_id, user)
    else:
        candidates = [
            r for r in orchestrator.runs.values()
            if r.analysis_id != analysis_id
            and Authorizer.can_access_org(user, r.org_id)
            and r.report is not None
            and (
                (getattr(r.report, "domain", None) or urlparse(r.website_url).netloc.replace("www.", "")).lower()
                == target_domain
            )
        ]
        if candidates:
            candidates.sort(key=lambda r: getattr(r, "created_at", datetime.min), reverse=True)
            baseline_run = candidates[0]

    curr_findings = canonicalize_report_findings(current_run.report.findings if current_run.report else [])
    curr_by_key = {f.deduplication_key or f"{f.category}:{f.title.lower().strip()}": f for f in curr_findings}

    if not baseline_run or not baseline_run.report:
        return {
            "audit_id": analysis_id,
            "baseline_audit_id": None,
            "status": "NO_BASELINE_AVAILABLE",
            "summary": {
                "STILL_PRESENT": 0,
                "RESOLVED": 0,
                "REAPPEARED": 0,
                "NEW_ISSUE": len(curr_findings),
            },
            "deltas": [
                {"key": k, "finding_id": f.finding_id, "title": f.title, "state": "NEW_ISSUE"}
                for k, f in curr_by_key.items()
            ],
        }

    base_findings = canonicalize_report_findings(baseline_run.report.findings or [])
    base_by_key = {f.deduplication_key or f"{f.category}:{f.title.lower().strip()}": f for f in base_findings}

    deltas: List[Dict[str, Any]] = []
    counts = {"STILL_PRESENT": 0, "RESOLVED": 0, "REAPPEARED": 0, "NEW_ISSUE": 0}

    for k, curr_f in curr_by_key.items():
        base_f = base_by_key.get(k)
        if base_f is None:
            state = "NEW_ISSUE"
        else:
            base_status = str(getattr(base_f.status, "value", base_f.status)).upper()
            if base_status in ("VERIFIED_FIXED", "RESOLVED"):
                state = "REAPPEARED"
            else:
                state = "STILL_PRESENT"
        counts[state] += 1
        deltas.append({
            "key": k,
            "finding_id": curr_f.finding_id,
            "title": curr_f.title,
            "severity": str(getattr(curr_f.severity, "value", curr_f.severity)),
            "state": state,
        })

    for k, base_f in base_by_key.items():
        if k not in curr_by_key:
            counts["RESOLVED"] += 1
            deltas.append({
                "key": k,
                "finding_id": base_f.finding_id,
                "title": base_f.title,
                "severity": str(getattr(base_f.severity, "value", base_f.severity)),
                "state": "RESOLVED",
            })

    return {
        "audit_id": analysis_id,
        "baseline_audit_id": baseline_run.analysis_id,
        "status": "COMPARED",
        "summary": counts,
        "deltas": deltas,
    }


@router.post("/audits/{analysis_id}/reports")
async def generate_audit_deliverables_manifest(
    analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns the 5 enterprise report deliverables and ticket export pack for the audit."""
    run = _get_org_run(analysis_id, user)
    if not run.report:
        raise HTTPException(status_code=404, detail="Audit report is not ready yet.")
    findings = canonicalize_report_findings(run.report.findings or [])
    tickets = [f.to_developer_ticket() for f in findings]
    checklist = [
        {
            "finding_id": f.finding_id,
            "title": f.title,
            "verification_command": f.verification_command or (t["sections"]["09_retest_procedure"][0] if t["sections"].get("09_retest_procedure") else ""),
            "expected_post_fix_result": t["sections"].get("08_acceptance_criteria", ""),
            "status": str(getattr(f.status, "value", f.status)),
        }
        for f, t in zip(findings, tickets)
    ]
    return {
        "audit_id": analysis_id,
        "deliverables": {
            "executive_audit_pdf": f"/api/v1/reports/{analysis_id}/pdf?mode=executive",
            "technical_audit_workbook": f"/api/v1/reports/{analysis_id}/pdf?mode=complete_book",
            "developer_ticket_pack_count": len(tickets),
            "verification_checklist_count": len(checklist),
            "machine_readable_audit_json": f"/api/v1/audits/{analysis_id}",
        },
        "developer_tickets": tickets,
        "verification_checklist": checklist,
    }


@router.get("/findings/{finding_id}")
async def get_finding_detail(
    finding_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns a single canonical finding and its 11-part developer ticket."""
    run, finding = _find_finding_across_runs(finding_id, user)
    return {
        "audit_id": run.analysis_id,
        "finding": finding.model_dump(),
        "developer_ticket": finding.to_developer_ticket(),
    }


@router.post("/findings/{finding_id}/assign")
async def assign_finding_lifecycle(
    finding_id: str,
    req: FindingAssignRequest,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Updates finding ownership and lifecycle state.
    Enforces hard rule: a finding cannot be marked VERIFIED_FIXED without /retest verification.
    """
    run, finding = _find_finding_across_runs(finding_id, user)
    if req.status:
        norm_status = req.status.strip().upper()
        if norm_status == "VERIFIED_FIXED":
            raise HTTPException(
                status_code=400,
                detail="Cannot set status to VERIFIED_FIXED directly. Submit a passing retest to /findings/{id}/retest.",
            )
        try:
            finding.status = FindingStatus(norm_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid FindingStatus '{req.status}'. Valid states: {[s.value for s in FindingStatus]}",
            )

    if req.owner:
        finding.owner = req.owner
    if req.responsible_role:
        finding.responsible_role = req.responsible_role
    if req.notes:
        finding.verification_notes = req.notes

    now_iso = datetime.now(timezone.utc).isoformat()
    history = list(finding.change_history or [])
    history.append({
        "timestamp": now_iso,
        "action": "ASSIGN_OR_TRIAGE",
        "status": finding.status.value if hasattr(finding.status, "value") else str(finding.status),
        "owner": finding.owner,
        "notes": req.notes,
    })
    finding.change_history = history
    return {
        "audit_id": run.analysis_id,
        "finding_id": finding.finding_id,
        "status": finding.status.value if hasattr(finding.status, "value") else str(finding.status),
        "owner": finding.owner,
        "responsible_role": finding.responsible_role,
        "change_history": finding.change_history,
    }


@router.post("/findings/{finding_id}/retest")
async def retest_finding_verification(
    finding_id: str,
    req: FindingRetestRequest,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Records independent retest verification for a finding.
    Transitions status to VERIFIED_FIXED on pass or RETEST_FAILED on fail.
    """
    run, finding = _find_finding_across_runs(finding_id, user)
    now_iso = datetime.now(timezone.utc).isoformat()
    finding.last_verified_at = now_iso
    if req.passed:
        finding.status = FindingStatus.VERIFIED_FIXED
        finding.resolution_status = "RESOLVED"
    else:
        finding.status = FindingStatus.RETEST_FAILED
        finding.resolution_status = "OPEN"

    if req.observed_after:
        finding.verification_notes = f"Observed after retest: {req.observed_after}"

    history = list(finding.change_history or [])
    history.append({
        "timestamp": now_iso,
        "action": "RETEST_VERIFICATION",
        "passed": req.passed,
        "status": finding.status.value,
        "observed_after": req.observed_after,
        "verified_by": req.verified_by,
    })
    finding.change_history = history

    return {
        "audit_id": run.analysis_id,
        "finding_id": finding.finding_id,
        "passed": req.passed,
        "status": finding.status.value,
        "last_verified_at": finding.last_verified_at,
        "change_history": finding.change_history,
    }


@router.get("/reports/{analysis_id}/validation")
async def get_report_validation_gates(
    analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Evaluates the 3-Stage Pre-Publication Quality Gate System:
    - Gate 1: Data Integrity (evidence links, finding count reconciliation, score formula)
    - Gate 2: Analytical Completeness (root cause / diagnostic gap, verification steps, scope labels)
    - Gate 3: Publication Quality (no placeholders, TOC/page structure, repairs disclosed)
    """
    run = _get_org_run(analysis_id, user)
    if not run.report:
        raise HTTPException(status_code=404, detail="Report not available for validation.")

    val_res = ValidationGate.validate_report(run.report, getattr(run.report, "crawl_manifest", None))
    qg_res = ValidationGate.evaluate_quality_gates(run.report, getattr(run.report, "crawl_manifest", None))
    gates_map = qg_res.get("gates", {})

    gate_1_passed = all(
        gates_map.get(k, {}).get("passed", True)
        for k in ("evidence_gate", "deduplication_gate", "scoring_gate", "gate_02_evidence_reference_integrity", "gate_09_score_eligibility")
    )
    gate_2_passed = all(
        gates_map.get(k, {}).get("passed", True)
        for k in ("coverage_gate", "analysis_gate", "actionability_gate", "gate_06_scope_consistency", "gate_10_recommendation_relevance")
    )
    gate_3_passed = all(
        gates_map.get(k, {}).get("passed", True)
        for k in ("consistency_gate", "reporting_gate", "rendering_gate", "gate_12_executive_summary_reconciliation")
    )

    return {
        "audit_id": analysis_id,
        "is_valid": val_res.is_valid and qg_res.get("all_passed", False),
        "certification_status": getattr(run.report, "certification_status", "NOT_CERTIFIED") or "NOT_CERTIFIED",
        "publication_status": getattr(run.report, "publication_status", "DRAFT") or "DRAFT",
        "three_stage_gates": {
            "gate_1_data_integrity": {
                "passed": gate_1_passed,
                "status": "PASS" if gate_1_passed else "FAIL",
            },
            "gate_2_analytical_completeness": {
                "passed": gate_2_passed,
                "status": "PASS" if gate_2_passed else "FAIL",
            },
            "gate_3_publication_quality": {
                "passed": gate_3_passed,
                "status": "PASS" if gate_3_passed else "FAIL",
            },
        },
        "passed_checks": val_res.passed_checks,
        "failed_checks": val_res.failed_checks,
        "failure_reasons": val_res.failure_reasons,
        "quality_gates": qg_res,
    }

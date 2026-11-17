"""
Finding reads, Browsable Evidence Viewer, and Side-by-Side 2-Audit Comparison routes.
Mounted on the `/analyses` router.
"""
from typing import Any, Dict, List, Optional
from fastapi import Depends, HTTPException, Query

from app.api.routes.audits.analyses import router
from app.crawl.audit.inventory_helper import get_canonical_crawl_inventory
from app.crawl.audit.regression_engine import AuditRegressionEngine, get_regression_engine
from app.domain.scoring.displayed_score import compute_ttfb_summary, displayed_composite
from app.identity.access import require_analysis
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, require_permission
from app.api.routes.remediation.patches import (
    AssignRemediationRequest,
    assign_finding,
    get_finding_retest_history,
)


def _extract_attr(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _enum_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)


def query_evidence_ledger(
    report: Any,
    analysis_id: str = "",
    url: Optional[str] = None,
    source_type: Optional[str] = None,
    evidence_class: Optional[str] = None,
    finding_id: Optional[str] = None,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Collects and filters evidence ledger items, inline finding evidence, and DB provenance traces
    for the Browsable Evidence Viewer.
    """
    by_id: Dict[str, Dict[str, Any]] = {}

    # 1. Report-level evidence_ledger (if dict or list)
    raw_ledger = _extract_attr(report, "evidence_ledger")
    if isinstance(raw_ledger, dict):
        for ev_id, item in raw_ledger.items():
            item_dict = item.model_dump() if hasattr(item, "model_dump") else (dict(item) if isinstance(item, dict) else {})
            ev_url = str(item_dict.get("url") or "")
            by_id[str(ev_id)] = {
                "evidence_id": str(ev_id),
                "url": ev_url,
                "source_type": str(item_dict.get("source_type") or item_dict.get("source") or "crawler_dom"),
                "evidence_class": _enum_str(item_dict.get("evidence_class"), "OBSERVED"),
                "selector": item_dict.get("selector") or item_dict.get("element"),
                "value": str(item_dict.get("text") or item_dict.get("value") or item_dict.get("snippet") or ""),
                "snippet": str(item_dict.get("snippet") or item_dict.get("text") or item_dict.get("value") or ""),
                "analyzer": item_dict.get("analyzer") or "deterministic_crawler",
                "content_sha256": item_dict.get("content_sha256") or item_dict.get("hash") or "",
                "fetched_at": item_dict.get("fetched_at") or item_dict.get("captured_at") or "",
                "raw_snapshot_id": item_dict.get("raw_snapshot_id") or "",
                "provenance_state": _enum_str(item_dict.get("provenance_state") or item_dict.get("evidence_state"), "EMPIRICALLY_VERIFIED"),
                "finding_ids": list(item_dict.get("finding_ids") or []),
                "affected_urls": [ev_url] if ev_url else [],
            }

    # 2. Findings inline evidence & evidence_refs
    findings = _extract_attr(report, "findings") or []
    for idx, f in enumerate(findings):
        f_id = str(_extract_attr(f, "finding_id") or _extract_attr(f, "id") or f"F-{idx+1}")
        f_class = _enum_str(_extract_attr(f, "evidence_class"), "OBSERVED")
        f_urls = [str(u) for u in (_extract_attr(f, "affected_urls") or []) if u]
        f_ev_list = _extract_attr(f, "evidence") or []

        for ev_idx, ev in enumerate(f_ev_list):
            ev_id = str(
                _extract_attr(ev, "evidence_id")
                or _extract_attr(ev, "id")
                or f"{f_id}-EV-{ev_idx+1}"
            )
            ev_url = str(_extract_attr(ev, "url") or (f_urls[0] if f_urls else ""))
            ev_source = str(
                _extract_attr(ev, "source_type")
                or _extract_attr(ev, "source")
                or _extract_attr(f, "evidence_source")
                or "crawler_dom"
            )
            ev_cls = _enum_str(_extract_attr(ev, "evidence_class") or f_class, "OBSERVED")
            ev_val = str(
                _extract_attr(ev, "value")
                or _extract_attr(ev, "snippet")
                or _extract_attr(ev, "excerpt")
                or _extract_attr(ev, "raw_value")
                or ""
            )
            ev_sel = _extract_attr(ev, "selector") or _extract_attr(ev, "element")
            ev_hash = _extract_attr(ev, "content_sha256") or _extract_attr(ev, "hash") or _extract_attr(f, "provenance_hash") or ""
            ev_state = _enum_str(
                _extract_attr(ev, "evidence_state")
                or _extract_attr(ev, "verification_status")
                or _extract_attr(f, "verification_status"),
                "VERIFIED",
            )

            if ev_id in by_id:
                existing = by_id[ev_id]
                if f_id not in existing["finding_ids"]:
                    existing["finding_ids"].append(f_id)
                for u in ([ev_url] if ev_url else []) + f_urls:
                    if u and u not in existing["affected_urls"]:
                        existing["affected_urls"].append(u)
                if not existing.get("url") and ev_url:
                    existing["url"] = ev_url
                if not existing.get("value") and ev_val:
                    existing["value"] = ev_val
                    existing["snippet"] = ev_val
            else:
                merged_urls = list(dict.fromkeys(([ev_url] if ev_url else []) + f_urls))
                by_id[ev_id] = {
                    "evidence_id": ev_id,
                    "url": ev_url,
                    "source_type": ev_source,
                    "evidence_class": ev_cls,
                    "selector": ev_sel,
                    "value": ev_val,
                    "snippet": ev_val,
                    "analyzer": str(_extract_attr(f, "agent_id") or "deterministic_crawler"),
                    "content_sha256": str(ev_hash),
                    "fetched_at": str(_extract_attr(f, "evidence_timestamp") or _extract_attr(f, "first_detected_at") or ""),
                    "raw_snapshot_id": "",
                    "provenance_state": ev_state,
                    "finding_ids": [f_id],
                    "affected_urls": merged_urls,
                }

        # Also link any referenced evidence IDs on the finding
        for ref_id in list(_extract_attr(f, "evidence_refs") or []) + list(_extract_attr(f, "evidence_ids") or []):
            ref_str = str(ref_id)
            if ref_str in by_id:
                if f_id not in by_id[ref_str]["finding_ids"]:
                    by_id[ref_str]["finding_ids"].append(f_id)
                for u in f_urls:
                    if u not in by_id[ref_str]["affected_urls"]:
                        by_id[ref_str]["affected_urls"].append(u)

    # 3. DB Evidence Traces (if analysis_id is stored)
    if analysis_id:
        try:
            from app.db.repository import get_audit_repository
            repo = get_audit_repository()
            traces = repo.get_evidence_trace(analysis_id)
            for t in (traces or []):
                td = t.model_dump() if hasattr(t, "model_dump") else (dict(t) if isinstance(t, dict) else {})
                ev_id = str(td.get("evidence_id") or td.get("trace_id") or "")
                if not ev_id:
                    continue
                t_url = str(td.get("url") or "")
                t_fid = str(td.get("finding_id") or "")
                if ev_id not in by_id:
                    by_id[ev_id] = {
                        "evidence_id": ev_id,
                        "url": t_url,
                        "source_type": str(td.get("source_type") or "db_trace"),
                        "evidence_class": str(td.get("evidence_class") or "OBSERVED"),
                        "selector": td.get("selector"),
                        "value": str(td.get("snippet") or td.get("raw_value") or ""),
                        "snippet": str(td.get("snippet") or td.get("raw_value") or ""),
                        "analyzer": str(td.get("agent_id") or "audit_repository"),
                        "content_sha256": str(td.get("sha256_hash") or ""),
                        "fetched_at": str(td.get("captured_at") or ""),
                        "raw_snapshot_id": str(td.get("snapshot_id") or ""),
                        "provenance_state": "VERIFIED",
                        "finding_ids": [t_fid] if t_fid else [],
                        "affected_urls": [t_url] if t_url else [],
                    }
        except Exception:
            pass

    # Apply filters
    filtered: List[Dict[str, Any]] = []
    url_q = url.strip().lower() if url else None
    src_q = source_type.strip().lower() if source_type else None
    cls_q = evidence_class.strip().lower() if evidence_class else None
    fid_q = finding_id.strip().lower() if finding_id else None
    text_q = q.strip().lower() if q else None

    for item in by_id.values():
        if url_q:
            item_urls = [item.get("url", "")] + list(item.get("affected_urls") or [])
            if not any(url_q in str(u).lower() for u in item_urls if u):
                continue
        if src_q:
            if src_q not in str(item.get("source_type") or "").lower():
                continue
        if cls_q:
            if cls_q not in str(item.get("evidence_class") or "").lower():
                continue
        if fid_q:
            fids_lower = [str(x).lower() for x in (item.get("finding_ids") or [])]
            if fid_q not in fids_lower and not any(fid_q in x for x in fids_lower):
                continue
        if text_q:
            haystack = " ".join([
                str(item.get("evidence_id") or ""),
                str(item.get("url") or ""),
                str(item.get("source_type") or ""),
                str(item.get("evidence_class") or ""),
                str(item.get("selector") or ""),
                str(item.get("value") or ""),
                str(item.get("snippet") or ""),
                " ".join(str(x) for x in (item.get("finding_ids") or [])),
                " ".join(str(x) for x in (item.get("affected_urls") or [])),
            ]).lower()
            if text_q not in haystack:
                continue
        filtered.append(item)

    linked_finding_ids = sorted({fid for item in filtered for fid in (item.get("finding_ids") or []) if fid})
    affected_urls = sorted({
        u
        for item in filtered
        for u in ([item.get("url")] + list(item.get("affected_urls") or []))
        if isinstance(u, str) and u.strip()
    })

    return {
        "analysis_id": analysis_id,
        "total": len(filtered),
        "filters": {
            "url": url,
            "source_type": source_type,
            "evidence_class": evidence_class,
            "finding_id": finding_id,
            "q": q,
        },
        "items": filtered,
        "evidence": filtered,
        "linked_finding_ids": linked_finding_ids,
        "affected_urls": affected_urls,
    }


def _report_to_regression_dict(report: Any, audit_id: str) -> Dict[str, Any]:
    scores_obj = _extract_attr(report, "scores")
    overall_score = displayed_composite(report)
    if overall_score is None and scores_obj is not None:
        overall_score = _extract_attr(scores_obj, "overall_score")
    if overall_score is None:
        overall_score = _extract_attr(report, "overall_score") or 0

    cat_scores_raw = _extract_attr(scores_obj, "category_scores") if scores_obj else (_extract_attr(report, "category_scores") or {})
    cat_scores: Dict[str, int] = {}
    if isinstance(cat_scores_raw, dict):
        for k, v in cat_scores_raw.items():
            key_str = _enum_str(k)
            val = _extract_attr(v, "score") if not isinstance(v, (int, float)) else v
            if isinstance(val, (int, float)):
                cat_scores[key_str] = int(round(float(val)))

    manifest = _extract_attr(report, "crawl_manifest")
    raw_pages = (
        _extract_attr(report, "page_reports")
        or (_extract_attr(manifest, "pages") if manifest else None)
        or _extract_attr(report, "pages")
        or []
    )
    pages_list: List[Dict[str, Any]] = []
    schema_types_set = set(_extract_attr(report, "schema_types") or [])

    for p in raw_pages:
        p_url = _extract_attr(p, "url")
        if not p_url:
            continue
        p_schemas = _extract_attr(p, "schema_types") or _extract_attr(p, "detected_schema_types") or []
        for st in p_schemas:
            if st:
                schema_types_set.add(str(st))
        pages_list.append({
            "url": str(p_url),
            "status_code": _extract_attr(p, "status_code", 200),
            "title": _extract_attr(p, "title"),
            "canonical": _extract_attr(p, "canonical_url") or _extract_attr(p, "canonical"),
            "ttfb_ms": _extract_attr(p, "ttfb_ms"),
        })

    schema_val = _extract_attr(report, "schema_validation")
    if schema_val:
        for st in (_extract_attr(schema_val, "detected_types") or _extract_attr(schema_val, "entity_types") or []):
            if st:
                schema_types_set.add(str(st))

    return {
        "audit_id": audit_id,
        "overall_score": int(round(float(overall_score or 0))),
        "overall_score_float": float(overall_score or 0.0),
        "category_scores": cat_scores,
        "pages": pages_list,
        "schema_types": sorted(schema_types_set),
    }


def _extract_ttfb_median(report: Any, reg_dict: Dict[str, Any]) -> float:
    ttfb_stats = _extract_attr(report, "ttfb_stats")
    if ttfb_stats is not None:
        med = _extract_attr(ttfb_stats, "median_ms")
        if isinstance(med, (int, float)) and med > 0:
            return round(float(med), 1)
    samples = [
        float(p["ttfb_ms"])
        for p in (reg_dict.get("pages") or [])
        if isinstance(p.get("ttfb_ms"), (int, float)) and float(p["ttfb_ms"]) > 0
    ]
    if samples:
        summary = compute_ttfb_summary(samples)
        return float(summary.get("median_ms") or 0.0)
    crawl_summary = _extract_attr(report, "crawl_summary") or {}
    if isinstance(crawl_summary, dict) and isinstance(crawl_summary.get("avg_ttfb_ms"), (int, float)):
        return round(float(crawl_summary["avg_ttfb_ms"]), 1)
    return 0.0


def _finding_identity_key(f: Any) -> str:
    for attr in ("rule_id", "deduplication_key", "finding_id", "id"):
        val = _extract_attr(f, attr)
        if val and str(val).strip():
            return str(val).strip().lower()
    cat = _enum_str(_extract_attr(f, "category"), "GENERAL")
    title = str(_extract_attr(f, "title") or _extract_attr(f, "finding_title") or "").strip().lower()
    return f"{cat}::{title}"


def _finding_summary(f: Any) -> Dict[str, Any]:
    return {
        "finding_id": str(_extract_attr(f, "finding_id") or _extract_attr(f, "id") or ""),
        "rule_id": _extract_attr(f, "rule_id"),
        "title": str(_extract_attr(f, "title") or _extract_attr(f, "finding_title") or ""),
        "category": _enum_str(_extract_attr(f, "category")),
        "severity": _enum_str(_extract_attr(f, "severity")),
        "status": _enum_str(_extract_attr(f, "status"), "OPEN"),
        "resolution_status": str(_extract_attr(f, "resolution_status") or "OPEN"),
        "affected_urls": list(_extract_attr(f, "affected_urls") or []),
        "affected_url_count": int(_extract_attr(f, "affected_url_count") or len(_extract_attr(f, "affected_urls") or [])),
    }


def _is_finding_resolved(f: Any) -> bool:
    status_str = _enum_str(_extract_attr(f, "status"), "OPEN").upper()
    res_str = str(_extract_attr(f, "resolution_status") or "OPEN").upper()
    return status_str in {"VERIFIED", "FIXED", "VERIFIED_FIXED", "RESOLVED"} or res_str in {"RESOLVED", "VERIFIED", "FIXED"}


def compare_audit_reports(
    base_report: Any,
    target_report: Any,
    base_analysis_id: str = "baseline",
    target_analysis_id: str = "target",
) -> Dict[str, Any]:
    """
    Side-by-side comparison of two audit reports using AuditRegressionEngine.compare_audits
    plus finding-level diff, coverage delta, and TTFB median delta.
    """
    base_dict = _report_to_regression_dict(base_report, base_analysis_id)
    target_dict = _report_to_regression_dict(target_report, target_analysis_id)

    reg_engine: AuditRegressionEngine = get_regression_engine()
    reg_result = reg_engine.compare_audits(current_audit=target_dict, baseline_audit=base_dict)

    # Finding-level diff
    base_findings = _extract_attr(base_report, "findings") or []
    target_findings = _extract_attr(target_report, "findings") or []

    base_map: Dict[str, Any] = {_finding_identity_key(f): f for f in base_findings}
    target_map: Dict[str, Any] = {_finding_identity_key(f): f for f in target_findings}

    resolved_findings: List[Dict[str, Any]] = []
    persisting_findings: List[Dict[str, Any]] = []
    new_findings: List[Dict[str, Any]] = []

    for key, bf in base_map.items():
        if key not in target_map:
            resolved_findings.append(_finding_summary(bf))
        else:
            tf = target_map[key]
            if _is_finding_resolved(tf):
                resolved_findings.append(_finding_summary(tf))
            else:
                persisting_findings.append(_finding_summary(tf))

    for key, tf in target_map.items():
        if key not in base_map:
            if _is_finding_resolved(tf):
                resolved_findings.append(_finding_summary(tf))
            else:
                new_findings.append(_finding_summary(tf))

    # Coverage delta
    base_inv = get_canonical_crawl_inventory(_extract_attr(base_report, "crawl_manifest"), base_report)
    target_inv = get_canonical_crawl_inventory(_extract_attr(target_report, "crawl_manifest"), target_report)
    base_cov = float(base_inv.url_coverage_pct or 0.0)
    target_cov = float(target_inv.url_coverage_pct or 0.0)
    coverage_delta = {
        "base_coverage_pct": base_cov,
        "target_coverage_pct": target_cov,
        "coverage_pct_delta": round(target_cov - base_cov, 1),
        "base_tested_pages": base_inv.tested_pages,
        "target_tested_pages": target_inv.tested_pages,
        "tested_pages_delta": target_inv.tested_pages - base_inv.tested_pages,
        "base_discovered_total": base_inv.discovered_total,
        "target_discovered_total": target_inv.discovered_total,
    }

    # TTFB median delta
    base_ttfb_median = _extract_ttfb_median(base_report, base_dict)
    target_ttfb_median = _extract_ttfb_median(target_report, target_dict)
    ttfb_median_delta = round(target_ttfb_median - base_ttfb_median, 1)

    # Score deltas
    overall_delta = round(target_dict["overall_score_float"] - base_dict["overall_score_float"], 1)
    score_deltas = {
        "base_overall_score": base_dict["overall_score_float"],
        "target_overall_score": target_dict["overall_score_float"],
        "overall_score_delta": overall_delta,
        "category_deltas": reg_result.category_deltas,
    }

    return {
        "base_analysis_id": base_analysis_id,
        "target_analysis_id": target_analysis_id,
        "overall_score_delta": reg_result.overall_score_delta,
        "score_deltas": score_deltas,
        "coverage_delta": coverage_delta,
        "base_ttfb_median_ms": base_ttfb_median,
        "target_ttfb_median_ms": target_ttfb_median,
        "ttfb_median_delta": ttfb_median_delta,
        "resolved_findings": resolved_findings,
        "new_findings": new_findings,
        "persisting_findings": persisting_findings,
        "pages_added": reg_result.pages_added,
        "pages_removed": reg_result.pages_removed,
        "schema_types_added": reg_result.schema_types_added,
        "schema_types_dropped": reg_result.schema_types_dropped,
        "alerts": [
            {
                "alert_type": a.alert_type,
                "severity": a.severity,
                "url": a.url,
                "message": a.message,
                "previous_val": a.previous_val,
                "current_val": a.current_val,
            }
            for a in reg_result.alerts
        ],
    }


@router.get("/{analysis_id}/evidence")
async def get_analysis_evidence(
    analysis_id: str,
    url: Optional[str] = Query(default=None),
    source_type: Optional[str] = Query(default=None),
    evidence_class: Optional[str] = Query(default=None),
    finding_id: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    user: UserIdentity = Depends(get_current_user),
):
    """
    Browsable Evidence Viewer endpoint supporting URL, source_type, evidence_class,
    finding_id, and free-text query filters.
    """
    run = require_analysis(analysis_id, user)
    if not run.report:
        raise HTTPException(status_code=404, detail="Analysis report not found")
    return query_evidence_ledger(
        report=run.report,
        analysis_id=analysis_id,
        url=url,
        source_type=source_type,
        evidence_class=evidence_class,
        finding_id=finding_id,
        q=q,
    )


@router.get("/{base_analysis_id}/compare/{target_analysis_id}")
async def compare_two_analyses(
    base_analysis_id: str,
    target_analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    """
    Side-by-side 2-audit comparison endpoint computing score deltas, coverage delta,
    TTFB median delta, structural drift alerts, and finding-level resolution diffs.
    """
    base_run = require_analysis(base_analysis_id, user)
    target_run = require_analysis(target_analysis_id, user)
    if not base_run.report or not target_run.report:
        raise HTTPException(status_code=404, detail="Both base and target analyses must have generated reports.")
    return compare_audit_reports(
        base_report=base_run.report,
        target_report=target_run.report,
        base_analysis_id=base_analysis_id,
        target_analysis_id=target_analysis_id,
    )


@router.post("/{analysis_id}/findings/{finding_id}/assign")
async def assign_analysis_finding(
    analysis_id: str,
    finding_id: str,
    req: AssignRemediationRequest,
    user: UserIdentity = Depends(require_permission("findings:assign")),
):
    return await assign_finding(analysis_id=analysis_id, finding_id=finding_id, req=req, user=user)


@router.get("/{analysis_id}/findings/{finding_id}/retest-history")
async def get_analysis_finding_retest_history(
    analysis_id: str,
    finding_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    return await get_finding_retest_history(analysis_id=analysis_id, finding_id=finding_id, user=user)


__all__ = ["router", "query_evidence_ledger", "compare_audit_reports"]

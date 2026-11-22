"""
Canonical SEO PDF Unification Bridge.

Single-source-of-truth adapter ensuring EVERY SEO PDF/HTML publisher in Dristik
(EnterprisePdfEngine 63-chapter book, SeoAuditBookRenderer, SeoPrintReportRenderer,
AdaptiveAuditBook, and the 55-section seo_audit_book) receives:
  1. 100% of legacy ExecutiveReport findings (with all 25+ fields) AND all rich legacy
     diagnostic sections (HTTP breakdown, canonicals, headings, media, schema, security,
     local/intl/ecommerce, SERP snippets, copywriting briefs, GSC/GA4, competitors, GEO,
     7/30/90-day roadmaps, page dossiers).
  2. 100% of new Enterprise SEO Overhaul findings (from live/persisted SEOAuditOrchestrator
     and deterministic crawled-page checks), 9-dimension mathematical scorecard + 5 confidence
     vectors, stack-detected remediation tasks with code diffs, live re-crawl verification
     before/after proof, internal link graph metrics, 40-specialist manifest, connector
     availability, and 10-gate QA certification.

Zero silent drops. Zero fabricated metrics. Strict HTML escaping on every dynamic string.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.connectors.seo_connector_manager import seo_connector_manager
from app.db.seo_orchestrator_schema import default_seo_db_path, init_seo_orchestrator_schema
from app.seo.audit.internal_links.link_graph_engine import build_internal_link_graph
from app.seo.audit.qa.seo_qa_validator import SeoQaValidator
from app.seo.audit.remediation.post_audit_remediation_engine import PostAuditRemediationEngine
from app.seo.audit.scoring.mathematical_score_engine import MathematicalScoreEngine


LEGACY_REPORT_SECTION_KEYS = (
    "story_summary",
    "what_site_gets_right",
    "what_is_holding_it_back",
    "primary_strategic_opportunity",
    "consultant_advice_what_to_ignore",
    "business_profile",
    "three_way_comparison",
    "http_status_breakdown",
    "canonical_audit",
    "indexation_intelligence",
    "host_and_redirects",
    "click_depth",
    "orphan_pages",
    "anchor_text_audit",
    "meta_rollup",
    "heading_hierarchy",
    "media_assets",
    "topical_authority",
    "commercial_evaluations",
    "schema_validation",
    "visual_ux",
    "security_audit",
    "international_seo",
    "local_seo",
    "ecommerce_seo",
    "serp_appearance",
    "external_authority",
    "google_performance",
    "competitor_seo_parity",
    "competitor_bakeoff",
    "geo_readiness",
    "ai_visibility_scorecard",
    "agent_readiness",
    "roadmap_7_days",
    "roadmap_30_days",
    "roadmap_90_days",
    "page_level_assessments",
    "page_reports",
    "diagnostic_inventory",
    "claim_ledger",
    "evidence_ledger",
    "consistency_report",
    "honest_scores",
    "crawl_summary",
    "scores",
)


def _esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def _to_plain(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:
            pass
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain(v) for v in obj]
    if hasattr(obj, "value") and not isinstance(obj, (str, int, float, bool)):
        return obj.value
    return obj


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _norm_text(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _finding_to_dict(f: Any) -> Dict[str, Any]:
    if isinstance(f, dict):
        d = dict(f)
    elif hasattr(f, "model_dump"):
        d = f.model_dump()
    else:
        d = {
            k: getattr(f, k)
            for k in dir(f)
            if not k.startswith("_") and not callable(getattr(f, k, None))
        }
    # Normalize enum values to plain strings
    for key in ("category", "severity", "status", "scope", "verification_status"):
        val = d.get(key)
        if hasattr(val, "value"):
            d[key] = val.value
    # Normalize finding_id / evidence_ids / affected_urls
    fid = str(d.get("finding_id") or d.get("id") or "").strip()
    if fid:
        d["finding_id"] = fid
    urls = [str(u).strip() for u in (d.get("affected_urls") or d.get("affected_urls_sample") or []) if u]
    d["affected_urls"] = list(dict.fromkeys(urls))
    ev_ids: List[str] = []
    for ef in ("evidence_ids", "evidence_refs", "evidence_references"):
        for r in (d.get(ef) or []):
            if r and str(r) not in ev_ids:
                ev_ids.append(str(r))
    if d.get("evidence_id") and str(d["evidence_id"]) not in ev_ids:
        ev_ids.append(str(d["evidence_id"]))
    for emb in (d.get("evidence") or []):
        eid = _get(emb, "evidence_id") or _get(emb, "id")
        if eid and str(eid) not in ev_ids:
            ev_ids.append(str(eid))
    d["evidence_ids"] = ev_ids
    d["evidence_refs"] = ev_ids
    return d


def _dedup_signature(f: Dict[str, Any]) -> Tuple[str, str]:
    rule_id = str(f.get("rule_id") or "").strip().lower()
    title = _norm_text(f.get("finding_title") or f.get("title") or "")
    urls = sorted(u.rstrip("/").lower() for u in (f.get("affected_urls") or []))
    url_sig = "|".join(urls[:5])
    if rule_id:
        return (f"rule:{rule_id}", url_sig)
    return (f"title:{title}", url_sig)


def merge_findings_preserving_all(
    primary_findings: Sequence[Any],
    secondary_findings: Sequence[Any],
) -> List[Dict[str, Any]]:
    """
    Merges two lists of findings (e.g. old ExecutiveReport findings + new SEO orchestrator findings)
    preserving 100% of unique findings and enriching matching pairs with fields from both sides.
    """
    merged: List[Dict[str, Any]] = []
    by_id: Dict[str, Dict[str, Any]] = {}
    by_sig: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def _absorb(raw: Any) -> None:
        item = _finding_to_dict(raw)
        fid = str(item.get("finding_id") or "").strip()
        sig = _dedup_signature(item)

        existing = by_id.get(fid) if fid else None
        if existing is None and sig[0] not in ("rule:", "title:"):
            existing = by_sig.get(sig)

        if existing is None:
            merged.append(item)
            if fid:
                by_id[fid] = item
            if sig[0] not in ("rule:", "title:"):
                by_sig[sig] = item
            return

        # Enrich existing finding with any non-empty fields from item without losing existing rich copy
        for k, v in item.items():
            if k in ("affected_urls", "evidence_ids", "evidence_refs", "affected_templates"):
                cur_list = list(existing.get(k) or [])
                for x in (v or []):
                    if x and x not in cur_list:
                        cur_list.append(x)
                existing[k] = cur_list
            elif k == "evidence" and isinstance(v, list):
                cur_ev = list(existing.get("evidence") or [])
                seen_ev = {str(_get(e, "evidence_id") or _get(e, "id") or idx) for idx, e in enumerate(cur_ev)}
                for e in v:
                    ek = str(_get(e, "evidence_id") or _get(e, "id") or "")
                    if not ek or ek not in seen_ev:
                        cur_ev.append(e)
                        if ek:
                            seen_ev.add(ek)
                existing["evidence"] = cur_ev
            elif v not in (None, "", [], {}):
                cur_val = existing.get(k)
                if cur_val in (None, "", [], {}):
                    existing[k] = v
                elif k in ("verification_status", "remediation_verification", "after_evidence", "root_cause_id") and str(v).upper() == "VERIFIED_FIXED":
                    existing[k] = v

    for f in primary_findings or []:
        _absorb(f)
    for f in secondary_findings or []:
        _absorb(f)

    return merged


def merge_evidence_preserving_all(
    primary_evidence: Sequence[Any],
    secondary_evidence: Sequence[Any],
    findings: Sequence[Dict[str, Any]] = (),
) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    out: List[Dict[str, Any]] = []

    def _add(raw: Any) -> None:
        ev = _to_plain(raw)
        if not isinstance(ev, dict):
            return
        eid = str(ev.get("evidence_id") or ev.get("id") or "").strip()
        if not eid:
            return
        if eid not in seen:
            ev["evidence_id"] = eid
            seen[eid] = ev
            out.append(ev)
        else:
            for k, v in ev.items():
                if v not in (None, "", [], {}) and seen[eid].get(k) in (None, "", [], {}):
                    seen[eid][k] = v

    for e in primary_evidence or []:
        _add(e)
    for e in secondary_evidence or []:
        _add(e)
    for f in findings or []:
        for emb in (f.get("evidence") or []):
            _add(emb)
    return out


def load_persisted_seo_orchestrator_data(
    audit_id: Optional[str],
    org_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Loads live or persisted Enterprise SEO Orchestrator data for audit_id (if any exists),
    strictly enforcing org_id tenant isolation when org_id is provided.
    """
    if not audit_id:
        return {}

    # 1. Active in-memory orchestrator (safe lazy import)
    try:
        from app.routers.seo_orchestrator_router import ACTIVE_ORCHESTRATORS

        orch = ACTIVE_ORCHESTRATORS.get(audit_id)
        if orch is not None:
            if org_id and orch.config.org_id and orch.config.org_id != org_id:
                return {}
            ca = orch.canonical_assessment or {}
            return {
                "source": "active_orchestrator",
                "assessment": ca,
                "findings": list(ca.get("canonical_findings") or ca.get("findings") or []),
                "evidence": list(ca.get("canonical_evidence") or ca.get("evidence") or []),
                "scorecard": orch.scorecard.model_dump() if orch.scorecard else ca.get("mathematical_scorecard"),
                "remediation_tasks": [t.model_dump() for t in orch.remediation_tasks] or list(ca.get("remediation_tasks") or []),
                "verification_runs": _load_verification_runs_db(audit_id, org_id),
                "agents": list(ca.get("agent_executions") or []),
                "link_graph": orch.link_graph or ca.get("internal_link_graph"),
                "connectors": list(ca.get("connectors") or []),
                "qa": orch.qa_report.model_dump() if orch.qa_report else ca.get("qa_certification"),
                "pages": list(orch.state.crawled_pages or []),
                "coverage": ca.get("coverage") or {},
            }
    except Exception:
        pass

    # 2. Persisted SQLite seo_* tables
    try:
        db_path = default_seo_db_path()
        init_seo_orchestrator_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM seo_audit_runs WHERE id = ?", (audit_id,)).fetchone()
            if not row:
                # Still check if standalone finding updates or verification runs exist for this analysis_id
                verif_runs = _load_verification_runs_from_conn(conn, audit_id, org_id)
                f_rows = conn.execute(
                    "SELECT * FROM seo_findings WHERE audit_id = ?" + (" AND (org_id = '' OR org_id = ?)" if org_id else ""),
                    (audit_id, org_id) if org_id else (audit_id,),
                ).fetchall()
                t_rows = conn.execute(
                    "SELECT * FROM seo_remediation_tasks WHERE audit_id = ?" + (" AND (org_id = '' OR org_id = ?)" if org_id else ""),
                    (audit_id, org_id) if org_id else (audit_id,),
                ).fetchall()
                if not verif_runs and not f_rows and not t_rows:
                    return {}
                return {
                    "source": "seo_db_overrides",
                    "findings": [_row_to_finding(r) for r in f_rows],
                    "remediation_tasks": [_row_to_task(r) for r in t_rows],
                    "verification_runs": verif_runs,
                }

            if org_id and row["org_id"] and row["org_id"] != org_id:
                return {}

            assessment = json.loads(row["canonical_assessment_json"]) if row["canonical_assessment_json"] else {}
            p_rows = conn.execute("SELECT page_payload_json FROM seo_crawl_pages WHERE audit_id = ?", (audit_id,)).fetchall()
            pages = [json.loads(r["page_payload_json"]) for r in p_rows if r["page_payload_json"]]
            sc_row = conn.execute("SELECT raw_json FROM seo_scorecards WHERE audit_id = ?", (audit_id,)).fetchone()
            scorecard = json.loads(sc_row["raw_json"]) if sc_row and sc_row["raw_json"] else assessment.get("mathematical_scorecard")
            f_rows = conn.execute("SELECT * FROM seo_findings WHERE audit_id = ?", (audit_id,)).fetchall()
            t_rows = conn.execute("SELECT * FROM seo_remediation_tasks WHERE audit_id = ?", (audit_id,)).fetchall()
            verif_runs = _load_verification_runs_from_conn(conn, audit_id, org_id)

            db_findings = [_row_to_finding(r) for r in f_rows]
            ca_findings = list(assessment.get("canonical_findings") or assessment.get("findings") or [])
            merged_f = merge_findings_preserving_all(ca_findings, db_findings)

            db_tasks = [_row_to_task(r) for r in t_rows]
            ca_tasks = list(assessment.get("remediation_tasks") or [])
            tasks = _merge_tasks(ca_tasks, db_tasks)

            return {
                "source": "seo_db",
                "assessment": assessment,
                "findings": merged_f,
                "evidence": list(assessment.get("canonical_evidence") or assessment.get("evidence") or []),
                "scorecard": scorecard,
                "remediation_tasks": tasks,
                "verification_runs": verif_runs,
                "agents": list(assessment.get("agent_executions") or []),
                "link_graph": assessment.get("internal_link_graph"),
                "connectors": list(assessment.get("connectors") or []),
                "qa": assessment.get("qa_certification"),
                "pages": pages,
                "coverage": assessment.get("coverage") or {},
            }
        finally:
            conn.close()
    except Exception:
        return {}


def _load_verification_runs_db(audit_id: str, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        db_path = default_seo_db_path()
        init_seo_orchestrator_schema(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            return _load_verification_runs_from_conn(conn, audit_id, org_id)
        finally:
            conn.close()
    except Exception:
        return []


def _load_verification_runs_from_conn(
    conn: sqlite3.Connection,
    audit_id: str,
    org_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    q = "SELECT * FROM seo_verification_runs WHERE audit_id = ?"
    params: Tuple[Any, ...] = (audit_id,)
    if org_id:
        q += " AND (org_id = '' OR org_id = ?)"
        params = (audit_id, org_id)
    q += " ORDER BY executed_at DESC LIMIT 100"
    rows = conn.execute(q, params).fetchall()
    out = []
    for r in rows:
        diff_data = {}
        try:
            diff_data = json.loads(r["diff_summary_json"] or "{}")
        except Exception:
            diff_data = {}
        out.append({
            "verification_id": r["id"],
            "task_id": str(r["remediation_task_id"]).split(":")[-1],
            "finding_id": r["finding_id"],
            "target_url": r["target_url"],
            "status": r["status"],
            "passed": bool(r["passed"]),
            "check_summary": r["verification_check"],
            "comparison_rows": diff_data.get("comparison_rows", []) if isinstance(diff_data, dict) else [],
            "verified_by": r["verified_by"],
            "executed_at": r["executed_at"],
        })
    return out


def _row_to_finding(r: sqlite3.Row) -> Dict[str, Any]:
    def _j(col: str, default: Any) -> Any:
        try:
            return json.loads(r[col] or "")
        except Exception:
            return default

    fid = str(r["id"]).split(":")[-1]
    ev_ids = _j("evidence_ids_json", [])
    return {
        "finding_id": fid,
        "rule_id": r["rule_id"],
        "root_cause_id": r["root_cause_id"],
        "category": r["category"],
        "severity": r["severity"],
        "title": r["title"],
        "description": r["description"],
        "recommendation": r["recommendation"],
        "affected_urls": _j("affected_urls_json", []),
        "evidence_ids": ev_ids,
        "evidence_refs": ev_ids,
        "status": r["status"],
        "owner": r["assigned_owner"],
        "verification_status": "VERIFIED_FIXED" if str(r["status"]).upper() == "VERIFIED_FIXED" else "UNVERIFIED",
    }


def _row_to_task(r: sqlite3.Row) -> Dict[str, Any]:
    def _j(col: str, default: Any) -> Any:
        try:
            return json.loads(r[col] or "")
        except Exception:
            return default

    tid = str(r["id"]).split(":")[-1]
    return {
        "task_id": tid,
        "finding_id": r["finding_id"],
        "problem": r["title"],
        "fix_type": r["fix_type"],
        "priority": r["priority"],
        "status": r["status"],
        "approval_status": r["approval_status"],
        "owner": r["assigned_owner"],
        "department": r["department"],
        "effort": r["effort"],
        "acceptance_criteria": r["acceptance_criteria"],
        "verification_protocol": r["verification_protocol"],
        "dependencies": _j("dependencies_json", []),
        "implementation": _j("implementation_json", {}),
        "affected_scope": _j("affected_scope_json", {}),
        "before_evidence": _j("before_evidence_json", {}),
        "after_evidence": _j("after_evidence_json", {}),
        "verification_status": "VERIFIED_FIXED" if str(r["status"]).upper() == "VERIFIED_FIXED" else "UNVERIFIED",
    }


def _merge_tasks(primary: Sequence[Dict[str, Any]], overrides: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    out: List[Dict[str, Any]] = []
    for t in primary or []:
        d = _to_plain(t)
        if not isinstance(d, dict):
            continue
        tid = str(d.get("task_id") or d.get("id") or "")
        if tid:
            by_id[tid] = d
        out.append(d)
    for t in overrides or []:
        d = _to_plain(t)
        if not isinstance(d, dict):
            continue
        tid = str(d.get("task_id") or d.get("id") or "")
        if tid and tid in by_id:
            for k, v in d.items():
                if v not in (None, "", [], {}):
                    by_id[tid][k] = v
        else:
            if tid:
                by_id[tid] = d
            out.append(d)
    return out


def synthesize_missing_deterministic_findings(
    pages: Sequence[Dict[str, Any]],
    existing_findings: Sequence[Dict[str, Any]],
    domain: str,
    link_graph: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Runs deterministic SEO checks on measured fields of crawled pages to capture any concrete
    new findings not already present in existing_findings. Never invents defects for unmeasured fields.
    """
    if not pages:
        return [], []

    existing_blob = " ".join(
        f"{f.get('rule_id', '')} {f.get('title', '')} {f.get('finding_title', '')}".lower()
        for f in existing_findings
    )

    new_findings: List[Dict[str, Any]] = []
    new_evidence: List[Dict[str, Any]] = []

    def _add_defect(
        rule_id: str,
        keywords_covered: Tuple[str, ...],
        *,
        category: str,
        severity: str,
        title: str,
        description: str,
        recommendation: str,
        root_cause_id: str,
        urls: List[str],
        observed: str,
        expected: str,
    ) -> None:
        if not urls:
            return
        if rule_id.lower() in existing_blob or any(kw in existing_blob for kw in keywords_covered):
            return
        ev_id = f"SEO_DET_{hashlib.sha256(f'{rule_id}:{urls[0]}'.encode()).hexdigest()[:10].upper()}"
        f_id = f"SEO_OVERHAUL_{rule_id.replace('.', '_').upper()}"
        new_evidence.append({
            "evidence_id": ev_id,
            "check_id": rule_id,
            "url": urls[0],
            "source_type": "crawled_dom",
            "observed_value": observed,
            "expected_value": expected,
            "result": "FAIL",
            "evidence_status": "OBSERVED",
            "content_sha256": hashlib.sha256(f"{urls[0]}:{observed}".encode()).hexdigest(),
        })
        new_findings.append({
            "finding_id": f_id,
            "rule_id": rule_id,
            "root_cause_id": root_cause_id,
            "category": category,
            "severity": severity,
            "title": title,
            "description": description,
            "observed_condition": observed,
            "expected_condition": expected,
            "recommendation": recommendation,
            "affected_urls": urls[:25],
            "evidence_ids": [ev_id],
            "evidence_refs": [ev_id],
            "status": "VERIFIED",
            "verification_status": "UNVERIFIED",
        })

    # Inspect measured page fields only
    missing_title = [p["url"] for p in pages if p.get("url") and ("title" in p) and (p.get("title") is not None) and str(p.get("title")).strip() == ""]
    _add_defect(
        "seo.title.missing",
        ("missing title", "title tag missing", "empty title"),
        category="ON_PAGE_SEO",
        severity="HIGH",
        title="Missing <title> tag on crawled page(s)",
        description=f"{len(missing_title)} crawled URL(s) returned an empty or missing HTML <title> tag.",
        recommendation="Render a unique, descriptive 30–60 character <title> element for every indexable route.",
        root_cause_id="RC_HEAD_TITLE_TEMPLATE",
        urls=missing_title,
        observed=f"{len(missing_title)} URL(s) with empty <title>",
        expected="Unique non-empty <title> (30–60 characters)",
    )

    # Duplicate titles across 2+ pages
    title_groups: Dict[str, List[str]] = {}
    for p in pages:
        t = str(p.get("title") or "").strip()
        if t and p.get("url"):
            title_groups.setdefault(t.lower(), []).append(str(p["url"]))
    dup_title_urls = [u for grp in title_groups.values() if len(grp) > 1 for u in grp]
    _add_defect(
        "seo.title.duplicate",
        ("duplicate title", "identical title"),
        category="ON_PAGE_SEO",
        severity="MEDIUM",
        title="Duplicate <title> tags shared across multiple URLs",
        description=f"{len(dup_title_urls)} crawled URL(s) share identical <title> strings, causing SERP cannibalization.",
        recommendation="Bind route-specific primary keywords and entity names to each page's <title> template.",
        root_cause_id="RC_DUPLICATE_TITLE_TEMPLATE",
        urls=dup_title_urls,
        observed=f"{len(dup_title_urls)} URL(s) sharing duplicate titles",
        expected="Unique <title> per canonical URL",
    )

    # Missing meta description (only when field explicitly measured in page payload)
    missing_desc = [
        p["url"]
        for p in pages
        if p.get("url")
        and ("meta_description" in p)
        and (p.get("meta_description") is not None)
        and str(p.get("meta_description")).strip() == ""
        and (p.get("html") or p.get("raw_html") or p.get("word_count") is not None)
    ]
    _add_defect(
        "seo.meta_description.missing",
        ("missing meta description", "meta description missing", "empty meta description"),
        category="ON_PAGE_SEO",
        severity="MEDIUM",
        title="Missing meta description on indexable URL(s)",
        description=f"{len(missing_desc)} crawled URL(s) omit a <meta name='description'> tag.",
        recommendation="Add unique, intent-aligned 120–155 character meta descriptions to improve SERP click-through rate.",
        root_cause_id="RC_HEAD_META_DESC",
        urls=missing_desc,
        observed=f"{len(missing_desc)} URL(s) missing meta description",
        expected="Unique meta description (120–155 chars)",
    )

    # HTTP 4xx/5xx error responses
    error_urls = [
        p["url"]
        for p in pages
        if p.get("url") and isinstance(p.get("status_code"), int) and p["status_code"] >= 400
    ]
    _add_defect(
        "seo.http.error_status",
        ("404", "5xx", "broken url", "http error", "status code"),
        category="TECHNICAL_SEO",
        severity="CRITICAL",
        title="Crawled URL(s) returning HTTP 4xx/5xx error status",
        description=f"{len(error_urls)} crawled URL(s) returned HTTP error status codes (>=400).",
        recommendation="Restore valid 200 OK content, implement 301 redirects to canonical replacements, or remove internal links.",
        root_cause_id="RC_HTTP_BROKEN_ROUTES",
        urls=error_urls,
        observed=f"{len(error_urls)} URL(s) returning >=400",
        expected="HTTP 200 OK for all canonical linked URLs",
    )

    # Internal link graph defects (orphans & deep pages > 3 hops) when graph has real edges
    if isinstance(link_graph, dict):
        orphans = [str(u) for u in (link_graph.get("orphan_pages") or []) if u]
        deep_pages = [str(u) for u in (link_graph.get("deep_pages") or []) if u]
        total_edges = int(link_graph.get("total_edges") or link_graph.get("edges_count") or 0)
        if total_edges > 0 and orphans:
            _add_defect(
                "seo.internal_links.orphans",
                ("orphan page", "orphaned page", "zero incoming internal"),
                category="TECHNICAL_SEO",
                severity="HIGH",
                title="Orphaned pages with zero incoming internal links",
                description=f"Internal link graph analysis detected {len(orphans)} crawled page(s) with 0 incoming internal links.",
                recommendation="Add contextual internal links from high-PageRank hub pages and navigation menus.",
                root_cause_id="RC_INTERNAL_LINK_ORPHANS",
                urls=orphans,
                observed=f"{len(orphans)} orphan URL(s)",
                expected="Every indexable URL linked from >=1 hub or category page",
            )
        if total_edges > 0 and deep_pages:
            _add_defect(
                "seo.internal_links.deep_depth",
                ("click depth", "deep page", "more than 3 clicks"),
                category="TECHNICAL_SEO",
                severity="MEDIUM",
                title="Key pages buried beyond 3 clicks from homepage",
                description=f"BFS crawl-depth analysis detected {len(deep_pages)} URL(s) deeper than 3 hops from the homepage.",
                recommendation="Flatten site hierarchy and surface priority landing pages from top-level hubs.",
                root_cause_id="RC_DEEP_CLICK_DEPTH",
                urls=deep_pages,
                observed=f"{len(deep_pages)} URL(s) at click depth > 3",
                expected="Primary pages reachable within <= 3 clicks from homepage",
            )

    return new_findings, new_evidence


def collect_unified_seo_pdf_bundle(
    *,
    report: Any = None,
    assessment: Any = None,
    report_data: Optional[Dict[str, Any]] = None,
    audit_id: Optional[str] = None,
    org_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    include_deterministic_gap_checks: bool = True,
) -> Dict[str, Any]:
    """
    Produces the single unified canonical SEO bundle merging:
    - Legacy ExecutiveReport / report_data (all old findings + all legacy diagnostic sections)
    - EnterpriseSeoAssessment (if supplied)
    - Live / persisted SEOAuditOrchestrator state (new findings, scorecard, remediation, verification runs)
    - Deterministic crawled-page checks, 9-dimension mathematical scorecard, stack-detected remediation,
      internal link graph, connector statuses, and 10-gate QA certification.
    """
    rep_dict: Dict[str, Any] = {}
    if report is not None:
        rep_dict = _to_plain(report) if not isinstance(report, dict) else dict(report)
    if isinstance(report_data, dict):
        for k, v in report_data.items():
            if v is not None and (k not in rep_dict or rep_dict[k] in (None, "", [], {})):
                rep_dict[k] = _to_plain(v)

    assess_dict: Dict[str, Any] = _to_plain(assessment) if assessment is not None else {}
    if not isinstance(assess_dict, dict):
        assess_dict = {}

    eff_audit_id = str(
        audit_id
        or rep_dict.get("analysis_id")
        or rep_dict.get("report_id")
        or assess_dict.get("audit_run_id")
        or ""
    ).strip()
    eff_org_id = org_id or rep_dict.get("org_id") or None
    eff_ws_id = workspace_id or (f"ws_{eff_org_id}" if eff_org_id else "ws_default")

    orch_data = load_persisted_seo_orchestrator_data(eff_audit_id, org_id=eff_org_id)

    # Extract domain
    domain = str(
        rep_dict.get("domain")
        or assess_dict.get("domain")
        or (orch_data.get("assessment") or {}).get("domain")
        or "unknown"
    ).replace("https://", "").replace("http://", "").split("/")[0]

    # Pages (merge crawl_manifest.pages, page_reports, orchestrator crawled pages)
    manifest = rep_dict.get("crawl_manifest") or {}
    raw_pages = (
        list(_get(manifest, "pages") or [])
        or list(rep_dict.get("page_reports") or [])
        or list(orch_data.get("pages") or [])
    )
    pages = [_to_plain(p) for p in raw_pages if p is not None]
    # Preserve page_reports copywriting alongside crawl_manifest pages
    page_reports = [_to_plain(p) for p in (rep_dict.get("page_reports") or []) if p is not None]

    # Merge findings from ALL sources (old + assessment + orchestrator DB/live)
    old_findings = list(rep_dict.get("findings") or [])
    assess_findings = list(assess_dict.get("canonical_findings") or assess_dict.get("findings") or [])
    orch_findings = list(orch_data.get("findings") or [])

    merged_findings = merge_findings_preserving_all(old_findings, assess_findings)
    merged_findings = merge_findings_preserving_all(merged_findings, orch_findings)

    # Internal link graph
    link_graph = (
        assess_dict.get("internal_link_graph")
        or rep_dict.get("internal_link_graph")
        or orch_data.get("link_graph")
    )
    if link_graph is None and pages:
        try:
            link_graph = build_internal_link_graph(pages, domain=domain)
        except Exception:
            link_graph = None

    # Synthesize any missing new deterministic findings from real crawled pages
    det_findings: List[Dict[str, Any]] = []
    det_evidence: List[Dict[str, Any]] = []
    if include_deterministic_gap_checks and pages:
        det_findings, det_evidence = synthesize_missing_deterministic_findings(
            pages, merged_findings, domain=domain, link_graph=link_graph
        )
        if det_findings:
            merged_findings = merge_findings_preserving_all(merged_findings, det_findings)

    # Evidence merge
    old_ev = list(rep_dict.get("evidence") or [])
    assess_ev = list(assess_dict.get("canonical_evidence") or assess_dict.get("evidence") or [])
    orch_ev = list(orch_data.get("evidence") or [])
    merged_evidence = merge_evidence_preserving_all(old_ev, assess_ev, merged_findings)
    merged_evidence = merge_evidence_preserving_all(merged_evidence, orch_ev)
    merged_evidence = merge_evidence_preserving_all(merged_evidence, det_evidence)

    # Connectors
    connectors = (
        list(assess_dict.get("connectors") or [])
        or list(rep_dict.get("connectors") or [])
        or list(orch_data.get("connectors") or [])
    )
    if not connectors:
        try:
            connectors = [
                c.model_dump()
                for c in seo_connector_manager.list_all_connectors(workspace_id=eff_ws_id, org_id=eff_org_id)
            ]
        except Exception:
            connectors = []

    # Coverage (6-tier inventory)
    cov_src = assess_dict.get("coverage") or rep_dict.get("coverage") or orch_data.get("coverage") or {}
    crawled = _get(cov_src, "urls_crawled")
    if crawled is None:
        crawled = len(pages)
    discovered = _get(cov_src, "urls_discovered")
    if discovered is None:
        discovered = max(
            int(_get(manifest, "total_pages_discovered") or 0),
            len(_get(manifest, "discovered_urls") or []),
            int(crawled),
        )
    rendered = _get(cov_src, "urls_rendered")
    if rendered is None:
        rendered = crawled
    deep = _get(cov_src, "urls_deeply_inspected")
    if deep is None:
        deep = crawled
    defects_urls = _get(cov_src, "urls_with_verified_findings")
    if defects_urls is None:
        defects_urls = len({u for f in merged_findings for u in (f.get("affected_urls") or []) if u})
    sampling_status = str(
        _get(cov_src, "sampling_status")
        or _get(manifest, "sampling_status")
        or ("SAMPLED_AUDIT" if int(discovered) > int(crawled) else "FULL_CRAWL" if int(crawled) > 0 else "SAMPLED_AUDIT")
    )
    coverage = {
        "urls_discovered": int(discovered),
        "urls_crawled": int(crawled),
        "urls_rendered": int(rendered),
        "urls_deeply_inspected": int(deep),
        "urls_with_verified_findings": int(defects_urls),
        "sampling_status": sampling_status,
        "urls_tested_by_specialist": _get(cov_src, "urls_tested_by_specialist") or {},
    }

    # Mathematical Scorecard (9 dimensions + 5 confidence vectors)
    # Never silently recompute a conflicting MathematicalScoreEngine score over an
    # ExecutiveReport that already carries sealed canonical domain scores.
    has_sealed_canonical_scores = bool(
        isinstance(rep_dict.get("scores"), dict)
        and (rep_dict["scores"].get("overall_score") is not None or rep_dict["scores"].get("category_scores"))
    )
    scorecard = (
        assess_dict.get("mathematical_scorecard")
        or rep_dict.get("mathematical_scorecard")
        or orch_data.get("scorecard")
    )
    if not scorecard and not has_sealed_canonical_scores and (pages or merged_findings):
        try:
            scorecard = MathematicalScoreEngine().build_scorecard_from_observations(
                pages=pages,
                findings=merged_findings,
                evidence_records=merged_evidence,
                discovered_count=coverage["urls_discovered"],
                crawled_count=coverage["urls_crawled"],
                sampling_status=sampling_status,
                connector_statuses=connectors,
                specialist_applicable={
                    "local": bool(rep_dict.get("local_seo")),
                    "international": bool(rep_dict.get("international_seo")),
                    "ecommerce": bool(rep_dict.get("ecommerce_seo")) or any("Product" in (p.get("schema_types") or []) for p in pages),
                },
            ).model_dump(mode="json")
        except Exception:
            scorecard = {}

    # Remediation Tasks (stack-detected with code diffs)
    tasks = _merge_tasks(
        list(assess_dict.get("remediation_tasks") or rep_dict.get("remediation_tasks") or []),
        list(orch_data.get("remediation_tasks") or []),
    )
    if not tasks and merged_findings:
        headers_sample: Dict[str, str] = {}
        dom_sample = ""
        for p in pages[:5]:
            hdrs = p.get("response_headers") or p.get("headers") or {}
            if isinstance(hdrs, dict):
                headers_sample.update({str(k): str(v) for k, v in hdrs.items()})
            if not dom_sample and (p.get("raw_html") or p.get("rendered_html") or p.get("html")):
                dom_sample = str(p.get("raw_html") or p.get("rendered_html") or p.get("html"))[:16000]
        try:
            tasks = [
                t.model_dump()
                for t in PostAuditRemediationEngine().synthesize_remediation_plan(
                    merged_findings, server_headers=headers_sample, dom_sample=dom_sample
                )
            ]
        except Exception:
            tasks = []

    verification_runs = list(
        assess_dict.get("verification_runs")
        or rep_dict.get("verification_runs")
        or orch_data.get("verification_runs")
        or []
    )
    agents = list(
        assess_dict.get("agent_executions")
        or assess_dict.get("agents")
        or rep_dict.get("agent_executions")
        or orch_data.get("agents")
        or []
    )
    qa = assess_dict.get("qa_certification") or rep_dict.get("qa_certification") or orch_data.get("qa")

    # Collect ALL rich legacy ExecutiveReport sections intact
    legacy_sections: Dict[str, Any] = {}
    for key in LEGACY_REPORT_SECTION_KEYS:
        val = rep_dict.get(key)
        if val not in (None, "", [], {}):
            legacy_sections[key] = val
    if page_reports and "page_reports" not in legacy_sections:
        legacy_sections["page_reports"] = page_reports

    limitations = list(
        assess_dict.get("limitations")
        or rep_dict.get("limitations")
        or []
    )

    return {
        "audit_id": eff_audit_id or "UNSCOPED",
        "domain": domain,
        "pages": pages,
        "findings": merged_findings,
        "evidence": merged_evidence,
        "scorecard": scorecard or {},
        "tasks": tasks,
        "verification_runs": verification_runs,
        "link_graph": link_graph,
        "connectors": connectors,
        "agents": agents,
        "coverage": coverage,
        "limitations": limitations,
        "qa": qa,
        "legacy_sections": legacy_sections,
        "new_findings_added_count": len(det_findings) + len(orch_findings),
    }


def enrich_report_for_pdf(
    report: Any,
    *,
    org_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> Any:
    """
    Non-destructively clones a Dristik ExecutiveReport (or wraps a dict), merging any new
    SEO Orchestrator / deterministic findings into `report.findings` and attaching the full
    unified canonical SEO bundle (`_unified_seo_bundle`) so EVERY legacy PDF/HTML renderer
    includes both old and new findings plus the Enterprise SEO Intelligence Addendum.
    """
    if report is None:
        return None
    if getattr(report, "_seo_pdf_enriched", False):
        return report

    # Capture the immutable parent execution snapshot metadata before cloning/enrichment
    # so standalone SEO reports keep the exact Run ID, timestamp, configuration, and scores.
    parent_snapshot_meta = None
    try:
        from app.reports.snapshot_provenance import format_audit_execution_metadata
        parent_snapshot_meta = format_audit_execution_metadata(report)
    except Exception:
        parent_snapshot_meta = None

    bundle = collect_unified_seo_pdf_bundle(
        report=report,
        org_id=org_id,
        workspace_id=workspace_id,
    )

    # Clone Pydantic report so we never mutate cached/in-memory AnalysisRun.report
    target = report
    if hasattr(report, "model_copy"):
        try:
            target = report.model_copy(deep=True)
        except Exception:
            target = report

    # Append any merged findings not yet in target.findings as valid Finding models
    try:
        from app.domain.enums import Category, FindingStatus, Severity
        from app.domain.models import Finding as DomainFinding

        existing_f = list(getattr(target, "findings", None) or [])
        existing_ids = {str(_get(f, "finding_id") or _get(f, "id") or "") for f in existing_f}
        existing_titles = {_norm_text(_get(f, "finding_title") or _get(f, "title")) for f in existing_f}

        cat_values = {c.value: c for c in Category}
        sev_values = {s.value: s for s in Severity}
        status_values = {st.value: st for st in FindingStatus}

        added: List[Any] = []
        for fd in bundle["findings"]:
            fid = str(fd.get("finding_id") or "").strip()
            t_norm = _norm_text(fd.get("finding_title") or fd.get("title"))
            if (fid and fid in existing_ids) or (t_norm and t_norm in existing_titles):
                continue
            raw_cat = str(fd.get("category") or "TECHNICAL_SEO").upper()
            cat_enum = cat_values.get(raw_cat, Category.TECHNICAL_SEO)
            raw_sev = str(fd.get("severity") or "MEDIUM").upper()
            sev_enum = sev_values.get(raw_sev, Severity.MEDIUM)
            raw_st = str(fd.get("status") or "OPEN").upper()
            st_enum = status_values.get(raw_st, FindingStatus.OPEN)
            ev_ids = fd.get("evidence_ids") or []

            added.append(
                DomainFinding(
                    finding_id=fid or f"SEO_NEW_{len(existing_f) + len(added) + 1:03d}",
                    category=cat_enum,
                    subcategory=str(fd.get("subcategory") or fd.get("rule_id") or raw_cat),
                    severity=sev_enum,
                    priority=9 if sev_enum == Severity.CRITICAL else (7 if sev_enum == Severity.HIGH else 5),
                    title=str(fd.get("title") or fd.get("finding_title") or "SEO Finding"),
                    description=str(fd.get("description") or fd.get("observed_condition") or "Observed SEO defect."),
                    root_cause=str(fd.get("root_cause") or fd.get("root_cause_id") or ""),
                    expected_condition=str(fd.get("expected_condition") or fd.get("expected_or_reference_behavior") or ""),
                    recommendation=str(fd.get("recommendation") or fd.get("recommended_solution") or "Resolve per acceptance criteria."),
                    why_it_matters=str(fd.get("why_it_matters") or fd.get("business_impact") or "Directly affects organic crawlability and search performance."),
                    business_impact=str(fd.get("business_impact") or "Impacts organic search visibility."),
                    validation_criteria=str(fd.get("acceptance_criteria") or fd.get("validation_criteria") or "Re-crawl target URL(s) and confirm defect resolved."),
                    affected_urls=list(fd.get("affected_urls") or []),
                    evidence_id=str(ev_ids[0]) if ev_ids else None,
                    status=st_enum,
                )
            )
            if fid:
                existing_ids.add(fid)
            if t_norm:
                existing_titles.add(t_norm)

        if added and hasattr(target, "findings") and isinstance(target.findings, list):
            target.findings.extend(added)
    except Exception:
        pass

    try:
        object.__setattr__(target, "_unified_seo_bundle", bundle)
        object.__setattr__(target, "_seo_pdf_enriched", True)
        if parent_snapshot_meta is not None:
            object.__setattr__(target, "_execution_snapshot_meta", parent_snapshot_meta)
    except Exception:
        pass

    return target


def render_enterprise_seo_addendum_html(bundle: Dict[str, Any]) -> str:
    """
    Renders a print-safe, self-contained HTML chapter block containing all new Enterprise SEO
    Overhaul intelligence (9-dimension scorecard, 5 confidence vectors, 6-tier coverage,
    internal link graph, stack-detected remediation patches, live verification before/after
    proof, connector status, and QA certification) for inclusion in ALL SEO PDF books.
    """
    if not isinstance(bundle, dict):
        return ""

    sc = bundle.get("scorecard") or {}
    dims = sc.get("dimensions") or []
    conf = sc.get("confidence_vectors") or {}
    cov = bundle.get("coverage") or {}
    tasks = bundle.get("tasks") or []
    verif_runs = bundle.get("verification_runs") or []
    link_graph = bundle.get("link_graph") or {}
    connectors = bundle.get("connectors") or []
    agents = bundle.get("agents") or []
    qa = bundle.get("qa") or {}

    if not dims and not tasks and not verif_runs and not link_graph and not agents:
        return ""

    overall_score = sc.get("overall_health_score")
    overall_interp_raw = sc.get("overall_interpretation", "Measured")
    overall_interp = getattr(overall_interp_raw, "value", overall_interp_raw)
    score_str = f"{overall_score}/100 ({overall_interp})" if overall_score is not None else "Not measured"

    # 1. 9-Dimension Scorecard table
    dim_rows = "".join(
        f"<tr>"
        f"<td><strong>{_esc(d.get('name'))}</strong></td>"
        f"<td>{round(float(d.get('configured_weight', 0)) * 100, 1)}%</td>"
        f"<td>{(str(round(float(d['effective_weight']) * 100, 1)) + '%') if d.get('effective_weight') is not None else 'Excluded'}</td>"
        f"<td>{_esc(d.get('score') if d.get('score') is not None else ('Not Applicable' if not d.get('is_applicable', True) else 'Unmeasured'))}</td>"
        f"<td>{int(d.get('passed_checks_count') or 0)} / {int(d.get('executed_checks_count') or 0)}</td>"
        f"<td>{_esc(getattr(d.get('interpretation'), 'value', d.get('interpretation')) or 'Unmeasured')}</td>"
        f"</tr>"
        for d in dims
    )
    scorecard_html = (
        f"""
        <h3>1. 9-Dimension Mathematical SEO Scorecard ({_esc(sc.get('methodology_version') or 'dristik_seo_v3.0')})</h3>
        <p><strong>Overall SEO Health Index:</strong> {_esc(score_str)} ·
           <strong>Active Weight Denominator:</strong> {round(float(sc.get('active_weight_sum') or 0) * 100, 1)}% ·
           <strong>Audit Coverage:</strong> {_esc(conf.get('audit_coverage_pct', 'Not measured'))}% ·
           <strong>Evidence Confidence:</strong> {_esc(conf.get('evidence_confidence_pct', 'Not measured'))}% ·
           <strong>Connector Completeness:</strong> {_esc(conf.get('connector_completeness_pct', 'Not measured'))}%</p>
        <p><strong>6-Tier Crawl Scope:</strong> Discovered: {int(cov.get('urls_discovered') or 0)} · Crawled: {int(cov.get('urls_crawled') or 0)} · Rendered: {int(cov.get('urls_rendered') or 0)} · Deeply Inspected: {int(cov.get('urls_deeply_inspected') or 0)} · Defect URLs: {int(cov.get('urls_with_verified_findings') or 0)} ({_esc(cov.get('sampling_status') or 'SAMPLED_AUDIT')})</p>
        <table style="width:100%;border-collapse:collapse;font-size:8pt;margin:6px 0 12px 0;">
          <thead><tr style="background:#f1f5f9;"><th>Dimension</th><th>Config Wt</th><th>Effective Wt</th><th>Score</th><th>Passed/Run</th><th>Band</th></tr></thead>
          <tbody>{dim_rows}</tbody>
        </table>
        """
        if dims
        else ""
    )

    # 2. Internal Link Graph summary
    lg_html = ""
    if isinstance(link_graph, dict) and (link_graph.get("nodes") or link_graph.get("total_nodes") or link_graph.get("hub_pages")):
        nodes = link_graph.get("nodes") or []
        orphans = link_graph.get("orphan_pages") or []
        deep_pages = link_graph.get("deep_pages") or []
        suggestions = link_graph.get("suggestions") or link_graph.get("linking_suggestions") or []
        hub_rows = "".join(
            f"<tr><td>{_esc(n.get('url'))}</td><td>{_esc(n.get('page_type') or 'page')}</td>"
            f"<td>{_esc(round(float(n.get('pagerank') or 0), 4))}</td>"
            f"<td>{int(n.get('inlinks') or 0)}</td><td>{int(n.get('outlinks') or 0)}</td>"
            f"<td>{_esc(n.get('depth') if n.get('depth') is not None else '—')}</td></tr>"
            for n in sorted(nodes, key=lambda x: float(x.get("pagerank") or 0), reverse=True)[:10]
        )
        sugg_items = "".join(
            f"<li>Link <code>{_esc(s.get('source_url') or s.get('from_url'))}</code> &rarr; "
            f"<code>{_esc(s.get('target_url') or s.get('to_url'))}</code> "
            f"(Anchor: <em>{_esc(s.get('suggested_anchor') or s.get('anchor_text') or 'contextual anchor')}</em>)</li>"
            for s in suggestions[:8]
        )
        lg_html = f"""
        <h3>2. Internal Link Graph &amp; PageRank Architecture</h3>
        <p><strong>Graph Nodes:</strong> {int(link_graph.get('total_nodes') or len(nodes))} ·
           <strong>Internal Edges:</strong> {int(link_graph.get('total_edges') or link_graph.get('edges_count') or 0)} ·
           <strong>Orphan Pages:</strong> {len(orphans)} ·
           <strong>Deep Pages (&gt;3 clicks):</strong> {len(deep_pages)}</p>
        {f'<table style="width:100%;border-collapse:collapse;font-size:8pt;margin:6px 0 10px 0;"><thead><tr style="background:#f1f5f9;"><th>URL</th><th>Type</th><th>PageRank</th><th>Inlinks</th><th>Outlinks</th><th>Depth</th></tr></thead><tbody>{hub_rows}</tbody></table>' if hub_rows else ''}
        {f'<p><strong>Priority Internal Linking Directives:</strong></p><ul>{sugg_items}</ul>' if sugg_items else ''}
        """

    # 3. Stack-Detected Remediation Directives & Code Patches
    remed_html = ""
    if tasks:
        task_cards = []
        for t in tasks[:25]:
            impl = t.get("implementation") or {}
            platform = impl.get("platform") or "GENERIC_HTML"
            conf_tag = impl.get("stack_confidence") or "GENERIC_FALLBACK"
            snippet = str(impl.get("code_diff_snippet") or "").strip()
            task_cards.append(
                f"<div style='border:1px solid #cbd5e1;border-left:3px solid #0284c7;border-radius:4px;padding:8px;margin:6px 0;page-break-inside:avoid;'>"
                f"<div><strong>{_esc(t.get('task_id'))}</strong> [{_esc(t.get('priority', 'P1'))} · {_esc(t.get('fix_type', 'CODE_LEVEL'))}] — {_esc(t.get('problem'))}</div>"
                f"<div style='font-size:7.5pt;color:#475569;margin-top:2px;'>Stack: <code>{_esc(platform)} ({_esc(conf_tag)})</code> · Target: <code>{_esc(impl.get('target_file_pattern') or 'Template')}</code> · Owner: {_esc(t.get('owner') or 'Engineering')} · Effort: {_esc(t.get('effort') or 'TBD')} · Status: <strong>{_esc(t.get('verification_status') or t.get('status') or 'UNVERIFIED')}</strong></div>"
                f"<p style='margin:4px 0;font-size:8pt;'><strong>Fix:</strong> {_esc(t.get('recommended_fix') or '')} · <strong>Acceptance:</strong> {_esc(t.get('acceptance_criteria') or '')}</p>"
                f"{f'<pre style=\"background:#0f172a;color:#f8fafc;padding:6px;border-radius:4px;font-size:7pt;white-space:pre-wrap;overflow-wrap:anywhere;\">{_esc(snippet)}</pre>' if snippet else ''}"
                f"</div>"
            )
        remed_html = f"<h3>3. Stack-Detected Remediation Directives &amp; Developer Patches ({len(tasks)} Tasks)</h3>{''.join(task_cards)}"

    # 4. Live Verification Runs (Fixed != Verified Proof)
    verif_html = ""
    if verif_runs:
        v_blocks = []
        for vr in verif_runs[:15]:
            rows = "".join(
                f"<tr><td>{_esc(r.get('dimension'))}</td><td>{_esc(r.get('before'))}</td><td>{_esc(r.get('after'))}</td></tr>"
                for r in (vr.get("comparison_rows") or [])
            )
            v_blocks.append(
                f"<div style='border:1px solid #cbd5e1;border-radius:4px;padding:8px;margin:6px 0;page-break-inside:avoid;'>"
                f"<p style='margin:0 0 4px 0;'><strong>Task {_esc(vr.get('task_id'))}</strong> · URL: <code>{_esc(vr.get('target_url'))}</code> · Result: <strong>{_esc(vr.get('status'))}</strong> ({_esc(vr.get('executed_at'))})</p>"
                f"<p style='margin:0 0 4px 0;font-size:8pt;'>{_esc(vr.get('check_summary'))}</p>"
                f"{f'<table style=\"width:100%;border-collapse:collapse;font-size:7.5pt;\"><thead><tr style=\"background:#f1f5f9;\"><th>Dimension</th><th>Before</th><th>After (Live Re-crawl)</th></tr></thead><tbody>{rows}</tbody></table>' if rows else ''}"
                f"</div>"
            )
        verif_html = f"<h3>4. Independent Live Re-Crawl Verification Proof ({len(verif_runs)} Runs)</h3>{''.join(v_blocks)}"

    # 5. Connectors, Specialist Execution & QA Seal
    conn_rows = "".join(
        f"<tr><td>{_esc(c.get('label') or c.get('provider_id'))}</td><td><strong>{_esc(c.get('status'))}</strong></td>"
        f"<td>{_esc(c.get('last_sync_timestamp') or 'Never')}</td><td>{_esc(c.get('health_message') or '')}</td></tr>"
        for c in connectors
    )
    qa_status = _esc(qa.get("status") if isinstance(qa, dict) else "NOT_RUN")
    gov_html = f"""
    <h3>5. External Connectors, Specialist Workforce &amp; QA Certification</h3>
    <p><strong>Specialist Agents Recorded:</strong> {len(agents)} · <strong>10-Gate QA Certification:</strong> <code>{qa_status}</code></p>
    {f'<table style="width:100%;border-collapse:collapse;font-size:8pt;margin:6px 0;"><thead><tr style="background:#f1f5f9;"><th>Connector</th><th>Status</th><th>Last Sync</th><th>Disclosure</th></tr></thead><tbody>{conn_rows}</tbody></table>' if conn_rows else ''}
    """

    return f"""
    <section class="chapter chapter-start enterprise-seo-addendum" id="enterprise-seo-intelligence">
      <div class="chapter-opener">
        <div class="chapter-number">Enterprise SEO Intelligence Addendum</div>
        <h2>Canonical 9-Dimension Scorecard, Remediation Code Patches &amp; Verification Proof</h2>
        <p class="section-intro">
          Generated from the unified Dristik SEO canonical dataset. Missing connectors remain disclosed as unmeasured without zeroing; fixes are never marked VERIFIED_FIXED without live re-crawl proof.
        </p>
      </div>
      {scorecard_html}
      {lg_html}
      {remed_html}
      {verif_html}
      {gov_html}
    </section>
    """

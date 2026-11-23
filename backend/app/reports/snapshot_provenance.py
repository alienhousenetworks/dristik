"""
Canonical Execution Snapshot Provenance for Dristik Reporting.

Produces one immutable metadata view (`AuditSnapshotMetadata`) from an audit
execution snapshot (`ExecutiveReport` or equivalent object/dict) so that the
Complete Master Audit Book and every standalone section report (SEO, GEO, AEO,
CRO, Crawl, Competitors) render the exact same:
- Run ID / Report Reference & Snapshot ID
- Execution date & timestamp (without blind string-slicing truncation)
- Audit configuration (policy pack, target pillars, version)
- Crawl scope (inspected vs discovered URLs)
- Composite score, grade, section scores, and finding counts
"""
from __future__ import annotations

import hashlib
import html
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.evidence_integrity import validate_score


REPORT_VERSION_DEFAULT = "v2.6 Enterprise Edition"

_DATE_FORMATS = (
    "%B %d, %Y - %H:%M UTC",
    "%B %d, %Y · %H:%M UTC",
    "%B %d, %Y - %H:%M:%S UTC",
    "%B %d, %Y %H:%M UTC",
    "%B %d, %Y",
    "%b %d, %Y - %H:%M UTC",
    "%b %d, %Y · %H:%M UTC",
    "%b %d, %Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _format_day(dt: datetime) -> str:
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def parse_audit_datetime(raw: Any) -> Tuple[str, str]:
    """Parses ISO-8601, orchestrator strftime, or datetime values into
    `(execution_date, execution_timestamp)` without string-slicing truncation.

    Example:
        "November 22, 2026 - 05:24 UTC" -> ("November 22, 2026", "November 22, 2026 · 05:24 UTC")
        "2026-11-22T05:24:00Z"          -> ("November 22, 2026", "November 22, 2026 · 05:24 UTC")
        "2026-11-22"                    -> ("November 22, 2026", "November 22, 2026")
    """
    if raw is None:
        return "Timestamp unavailable", "Timestamp unavailable"

    if isinstance(raw, datetime):
        dt = raw.astimezone(timezone.utc) if raw.tzinfo else raw
        date_part = _format_day(dt)
        return date_part, f"{date_part} · {dt.strftime('%H:%M')} UTC"

    text = str(raw).strip()
    if not text or text.lower() in {"none", "null", "timestamp unavailable"}:
        return "Timestamp unavailable", "Timestamp unavailable"

    # 1. Try ISO-8601 first (handles YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS(.fff)(Z|+00:00))
    iso_candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(iso_candidate)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        date_part = _format_day(dt)
        has_time = ("T" in text) or (":" in text)
        ts_part = f"{date_part} · {dt.strftime('%H:%M')} UTC" if has_time else date_part
        return date_part, ts_part
    except ValueError:
        pass

    # 2. Try known human/orchestrator strftime formats
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(text, fmt)
            date_part = _format_day(dt)
            has_time = "%H" in fmt
            ts_part = f"{date_part} · {dt.strftime('%H:%M')} UTC" if has_time else date_part
            return date_part, ts_part
        except ValueError:
            continue

    # 3. Never blindly slice unknown strings (prevents "November 22" -> "November 2")
    return text, text


def _extract_numeric_score(val: Any) -> Optional[float]:
    if val is None:
        return None
    status = str(_get(val, "status", "") or "").upper()
    if status in {"NOT_MEASURED", "NOT_TESTED", "UNAVAILABLE", "NOT_APPLICABLE"}:
        return None
    if hasattr(val, "score") or isinstance(val, dict):
        inner = _get(val, "score", None)
        return validate_score(inner)
    return validate_score(val)


def _resolve_category_score(cat_scores: Dict[str, Any], *candidates: str) -> Optional[float]:
    if not isinstance(cat_scores, dict):
        return None
    for candidate in candidates:
        for variant in (candidate, candidate.upper(), candidate.lower()):
            if variant in cat_scores:
                val = _extract_numeric_score(cat_scores[variant])
                if val is not None:
                    return val
    return None


def _matches_section(finding: Any, section_key: str) -> bool:
    raw_cat = _get(finding, "category", "")
    if hasattr(raw_cat, "value"):
        cat = str(raw_cat.value).upper()
    elif hasattr(raw_cat, "name"):
        cat = str(raw_cat.name).upper()
    else:
        cat = str(raw_cat or "").upper()
    title = str(_get(finding, "title", "") or _get(finding, "finding_title", "") or "").lower()
    if section_key == "crawl":
        return "TECHNICAL" in cat or "INFRASTRUCTURE" in cat or "crawl" in title or "sitemap" in title
    if section_key == "seo":
        return "SEO" in cat or "CONTENT" in cat or "title" in title or "meta" in title or "h1" in title
    if section_key == "geo":
        return "GEO" in cat or "AI" in cat or "citability" in title or "llm" in title or "perplexity" in title
    if section_key == "aeo":
        return "AEO" in cat or "SCHEMA" in cat or "STRUCTURED" in cat or "entity" in title or "faq" in title or "json-ld" in title
    if section_key == "cro":
        return "CRO" in cat or "EXPERIENCE" in cat or "CONVERSION" in cat or "cta" in title or "conversion" in title or "friction" in title
    if section_key == "competitors":
        return "COMPETIT" in cat or "bakeoff" in title or "rival" in title or "benchmark" in title
    return False


def _compute_weighted_seo_score(cat_scores: Dict[str, Any]) -> Optional[float]:
    """Single canonical weighted SEO pillar score across measured SEO sub-categories only.

    Denominator policy: unmeasured / unavailable / not-applicable categories are excluded
    from both numerator and denominator so missing connectors never become 0 or pass.
    """
    if not isinstance(cat_scores, dict):
        return None
    default_weights = {
        "TECHNICAL_SEO": 0.35,
        "ON_PAGE_SEO": 0.25,
        "CONTENT": 0.20,
        "SCHEMA": 0.20,
        "EXTERNAL_AUTHORITY": 0.15,
        "TRUST_AUTHORITY": 0.15,
    }
    measured: List[Tuple[float, float]] = []
    for key, default_w in default_weights.items():
        obj = cat_scores.get(key) or cat_scores.get(key.lower())
        if obj is None:
            continue
        score_val = _extract_numeric_score(obj)
        if score_val is None:
            continue
        raw_w = _get(obj, "weight")
        wt = float(raw_w) if isinstance(raw_w, (int, float)) and not isinstance(raw_w, bool) and float(raw_w) > 0 else default_w
        measured.append((wt, score_val))
    if not measured:
        return None
    if len(measured) == 1:
        return round(measured[0][1], 1)
    tot_w = sum(w for w, _ in measured)
    return round(sum(w * s for w, s in measured) / max(tot_w, 1e-6), 1)


def _normalize_severity_label(raw: Any) -> str:
    if raw is None:
        return "UNKNOWN"
    val = getattr(raw, "value", raw)
    text = str(val or "").strip().upper()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text or "UNKNOWN"


def _resolve_section_scores(report: Any) -> Dict[str, Optional[float]]:
    """Resolves pillar scores strictly from the single source of truth: CanonicalScorecardEngine."""
    try:
        from app.domain.scoring.canonical_scorecard import CanonicalScorecardEngine
        card = CanonicalScorecardEngine.evaluate_from_report(report)
        
        seo_p = card.pillars.get("SEO")
        geo_p = card.pillars.get("GEO")
        aeo_p = card.pillars.get("AEO")
        cro_p = card.pillars.get("CRO")

        seo = seo_p.measured_health_score if seo_p and seo_p.status in ("MEASURED", "PARTIAL") else None
        geo = geo_p.measured_health_score if geo_p and geo_p.status in ("MEASURED", "PARTIAL") else None
        aeo = aeo_p.measured_health_score if aeo_p and aeo_p.status in ("MEASURED", "PARTIAL") else None
        cro = cro_p.measured_health_score if cro_p and cro_p.status in ("MEASURED", "PARTIAL") else None
    except Exception:
        scores = _get(report, "scores")
        cat_scores = _get(scores, "category_scores") or {}
        seo = validate_score(_get(scores, "seo_score")) or _resolve_category_score(cat_scores, "TECHNICAL_SEO", "SEO")
        geo = validate_score(_get(scores, "geo_score")) or _resolve_category_score(cat_scores, "GEO")
        aeo = validate_score(_get(scores, "aeo_score")) or _resolve_category_score(cat_scores, "AEO")
        cro = validate_score(_get(scores, "cro_score")) or _resolve_category_score(cat_scores, "UX_CONVERSION", "CRO")

    # Crawl is part of SEO technical infrastructure
    crawl = seo

    # Competitors
    scores = _get(report, "scores")
    cat_scores = _get(scores, "category_scores") or {}
    comp = (
        validate_score(_get(scores, "competitor_score"))
        or _resolve_category_score(cat_scores, "COMPETITIVE_INTELLIGENCE", "COMPETITIVE")
    )
    if comp is None:
        bakeoff = _get(report, "competitor_bakeoff")
        if bakeoff is not None:
            tw = _get(bakeoff, "target_wins") or 0
            cw = _get(bakeoff, "competitor_wins") or 0
            ties = _get(bakeoff, "ties") or 0
            tot = tw + cw + ties
            if tot > 0:
                comp = validate_score(round((tw / tot) * 100.0, 1))

    return {
        "crawl": crawl,
        "seo": seo,
        "geo": geo,
        "aeo": aeo,
        "cro": cro,
        "competitors": comp,
    }


@dataclass(frozen=True)
class AuditSnapshotMetadata:
    """Immutable provenance view shared across the Master Book and every standalone report."""

    run_id: str
    report_ref: str
    snapshot_id: str
    snapshot_digest: str
    domain: str
    brand_name: str
    raw_generated_at: str
    execution_date: str
    execution_timestamp: str
    policy_pack: str
    target_pillars: Tuple[str, ...]
    configuration_summary: str
    pages_inspected: Optional[int]
    urls_discovered: Optional[int]
    crawl_scope_summary: str
    composite_score: Optional[float]
    composite_score_display: str
    composite_grade: str
    section_scores: Dict[str, Optional[float]]
    total_findings_count: int
    section_findings_counts: Dict[str, int]
    report_version: str = REPORT_VERSION_DEFAULT
    severity_counts: Dict[str, int] = None  # type: ignore[assignment]
    pages_rendered: Optional[int] = None

    def score_for_section(self, section_key: str) -> Optional[float]:
        return self.section_scores.get((section_key or "").lower().strip())

    def findings_for_section(self, section_key: str) -> int:
        return self.section_findings_counts.get((section_key or "").lower().strip(), 0)


def format_audit_execution_metadata(report: Any, *, use_cache: bool = True) -> AuditSnapshotMetadata:
    """Extracts and pins an immutable `AuditSnapshotMetadata` view for an execution snapshot."""
    if use_cache and report is not None and not isinstance(report, dict):
        cached = getattr(report, "_execution_snapshot_meta", None)
        if isinstance(cached, AuditSnapshotMetadata):
            return cached

    raw_domain = _get(report, "domain") or _get(report, "website_url") or "Target domain not recorded"
    domain = str(raw_domain).replace("https://", "").replace("http://", "").split("/")[0].strip() or "Target domain not recorded"

    profile = _get(report, "business_profile")
    brand_name = str(_get(profile, "business_name") or domain)

    raw_run_id = _get(report, "analysis_id") or _get(report, "report_id")
    if raw_run_id and str(raw_run_id).strip():
        run_id = str(raw_run_id).strip()
        report_ref = run_id[:12].upper()
    else:
        run_id = "Report reference unavailable"
        report_ref = "REFERENCE UNAVAILABLE"

    raw_ts = _get(report, "generated_at")
    raw_generated_at = str(raw_ts) if raw_ts else "Timestamp unavailable"
    execution_date, execution_timestamp = parse_audit_datetime(raw_ts)

    manifest = _get(report, "crawl_manifest")
    pages = list(_get(manifest, "pages") or _get(report, "page_reports") or [])
    pages_inspected: Optional[int] = len(pages) if (pages or manifest is not None) else None

    raw_discovered = _get(manifest, "total_pages_discovered")
    if raw_discovered is None:
        crawl_summary = _get(report, "crawl_summary")
        if isinstance(crawl_summary, dict):
            raw_discovered = crawl_summary.get("total_pages_discovered") or crawl_summary.get("discovered_urls")
    urls_discovered: Optional[int] = None
    if isinstance(raw_discovered, (int, float)) and int(raw_discovered) > 0:
        urls_discovered = int(raw_discovered)

    if pages_inspected is None:
        crawl_scope_summary = "Crawl coverage not recorded"
    elif urls_discovered and urls_discovered > pages_inspected:
        crawl_scope_summary = f"{pages_inspected} URLs inspected of {urls_discovered} discovered"
    else:
        crawl_scope_summary = f"{pages_inspected} URLs inspected"

    policy_pack = str(_get(report, "policy_pack") or "enterprise_web_intel_v4").strip()
    raw_pillars = _get(report, "target_pillars")
    if isinstance(raw_pillars, (list, tuple)) and raw_pillars:
        target_pillars = tuple(str(p).upper() for p in raw_pillars if p)
    else:
        target_pillars = ("SEO", "GEO", "AEO", "CRO")

    pillars_str = ", ".join(target_pillars)
    budget_str = f"{pages_inspected}-URL sample" if pages_inspected is not None else "Unrecorded scope"
    configuration_summary = f"{policy_pack} · Pillars: {pillars_str} · {budget_str} · {REPORT_VERSION_DEFAULT}"

    scores = _get(report, "scores")
    try:
        from app.domain.scoring.canonical_scorecard import CanonicalScorecardEngine
        card = CanonicalScorecardEngine.evaluate_from_report(report)
        composite_score = card.composite_health_score
        composite_grade = card.composite_grade
    except Exception:
        composite_score = validate_score(_get(scores, "overall_score"))
        raw_grade = _get(scores, "overall_grade") or _get(scores, "grade")
        composite_grade = str(raw_grade) if raw_grade and str(raw_grade) not in {"—", "-", "N/A"} else "NOT GRADED"

    if composite_score is not None:
        composite_score_display = f"{composite_score:.1f} / 100"
    else:
        composite_score_display = "NOT MEASURED"
        composite_grade = "NOT GRADED"

    section_scores = _resolve_section_scores(report)

    from app.report_finding_registry import canonicalize_report_findings
    raw_findings = list(_get(report, "findings") or [])
    ent_geo_f = _get(report, "_enterprise_geo_findings") or _get(report, "enterprise_geo_findings")
    if ent_geo_f and isinstance(ent_geo_f, list):
        raw_findings.extend(ent_geo_f)
    all_findings = canonicalize_report_findings(raw_findings)
    total_findings_count = len(all_findings)
    section_findings_counts = {
        key: sum(1 for f in all_findings if _matches_section(f, key))
        for key in ("crawl", "seo", "geo", "aeo", "cro", "competitors")
    }
    severity_counts: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for f in all_findings:
        sev_key = _normalize_severity_label(_get(f, "severity"))
        if sev_key in severity_counts:
            severity_counts[sev_key] += 1

    pages_rendered: Optional[int] = (
        sum(1 for p in pages if _get(p, "rendered") is True)
        if pages
        else None
    )

    digest_payload = (
        f"{run_id}|{execution_timestamp}|{domain}|{pages_inspected}|{urls_discovered}|"
        f"{composite_score}|{total_findings_count}|"
        + "|".join(f"{k}:{section_scores.get(k)}" for k in ("crawl", "seo", "geo", "aeo", "cro", "competitors"))
    )
    snapshot_digest = hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()[:16]
    sealed_id = _get(report, "sealed_evidence_snapshot_id")
    snapshot_id = str(sealed_id).strip() if sealed_id and str(sealed_id).strip() else f"SNAP_{snapshot_digest[:12].upper()}"

    meta = AuditSnapshotMetadata(
        run_id=run_id,
        report_ref=report_ref,
        snapshot_id=snapshot_id,
        snapshot_digest=snapshot_digest,
        domain=domain,
        brand_name=brand_name,
        raw_generated_at=raw_generated_at,
        execution_date=execution_date,
        execution_timestamp=execution_timestamp,
        policy_pack=policy_pack,
        target_pillars=target_pillars,
        configuration_summary=configuration_summary,
        pages_inspected=pages_inspected,
        urls_discovered=urls_discovered,
        crawl_scope_summary=crawl_scope_summary,
        composite_score=composite_score,
        composite_score_display=composite_score_display,
        composite_grade=composite_grade,
        section_scores=section_scores,
        total_findings_count=total_findings_count,
        section_findings_counts=section_findings_counts,
        report_version=REPORT_VERSION_DEFAULT,
        severity_counts=severity_counts,
        pages_rendered=pages_rendered,
    )

    if use_cache and report is not None and not isinstance(report, dict):
        try:
            object.__setattr__(report, "_execution_snapshot_meta", meta)
        except Exception:
            pass

    return meta


def format_section_scores_summary(meta: AuditSnapshotMetadata) -> str:
    """Formats aligned section scores as a compact single-line summary."""
    labels = (("seo", "SEO"), ("geo", "GEO"), ("aeo", "AEO"), ("cro", "CRO"))
    parts: List[str] = []
    for key, label in labels:
        val = meta.section_scores.get(key)
        parts.append(f"{label} {val:.1f}" if val is not None else f"{label} —")
    return " · ".join(parts)


def render_snapshot_provenance_bar(
    meta: AuditSnapshotMetadata,
    *,
    section_key: Optional[str] = None,
    section_label: Optional[str] = None,
    section_score: Optional[float] = None,
    section_findings_count: Optional[int] = None,
) -> str:
    """Renders an HTML execution snapshot provenance banner shared across master and standalone reports."""
    comp_text = (
        f"{meta.composite_score_display} · GRADE {meta.composite_grade}"
        if meta.composite_score is not None and meta.composite_grade != "NOT GRADED"
        else meta.composite_score_display
    )
    scores_line = format_section_scores_summary(meta)

    if section_key:
        sec_label_disp = section_label or section_key.upper()
        sec_count = section_findings_count if section_findings_count is not None else meta.findings_for_section(section_key)
        canonical_sec_count = meta.findings_for_section(section_key)
        if section_findings_count is not None and (sec_count > meta.total_findings_count or sec_count != canonical_sec_count):
            findings_line = f"{sec_count} {sec_label_disp} specialist findings · {meta.total_findings_count} unified executive findings"
        else:
            findings_line = f"{sec_count} issues in {sec_label_disp} ({meta.total_findings_count} total audit findings)"
        sec_val = section_score if section_score is not None else meta.score_for_section(section_key)
        sec_score_line = f"{sec_val:.1f} / 100" if sec_val is not None else "NOT MEASURED"
        extra_cell = (
            f'<div style="min-width:120px;">'
            f'<div style="font-size:9px;font-weight:700;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">{_esc(sec_label_disp)} SCORE</div>'
            f'<div style="font-size:11px;font-weight:700;color:#0f172a;margin-top:2px;">{_esc(sec_score_line)}</div>'
            f'</div>'
        )
    else:
        findings_line = f"{meta.total_findings_count} total execution findings recorded"
        extra_cell = ""

    return f"""
    <div class="execution-snapshot-provenance" data-run-id="{_esc(meta.report_ref)}" data-snapshot-id="{_esc(meta.snapshot_id)}" style="background:#f8fafc;border:1px solid #cbd5e1;border-left:4px solid #0f172a;border-radius:6px;padding:10px 14px;margin:12px 0 18px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;break-inside:avoid;">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e2e8f0;">
            <span style="font-size:9.5px;font-weight:800;letter-spacing:0.08em;color:#0f172a;text-transform:uppercase;">IMMUTABLE EXECUTION SNAPSHOT PROVENANCE</span>
            <span style="font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9.5px;color:#475569;">{_esc(meta.snapshot_id)} · SHA-256 {_esc(meta.snapshot_digest)}</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px 16px;">
            <div>
                <div style="font-size:9px;font-weight:700;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">RUN ID</div>
                <div style="font-size:11px;font-weight:700;color:#0f172a;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;margin-top:2px;">{_esc(meta.report_ref)}</div>
            </div>
            <div>
                <div style="font-size:9px;font-weight:700;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">EXECUTION TIMESTAMP</div>
                <div style="font-size:11px;font-weight:700;color:#0f172a;margin-top:2px;">{_esc(meta.execution_timestamp)}</div>
            </div>
            <div>
                <div style="font-size:9px;font-weight:700;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">CRAWL SCOPE</div>
                <div style="font-size:11px;font-weight:700;color:#0f172a;margin-top:2px;">{_esc(meta.crawl_scope_summary)}</div>
            </div>
            <div>
                <div style="font-size:9px;font-weight:700;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">COMPOSITE INDEX</div>
                <div style="font-size:11px;font-weight:700;color:#0f172a;margin-top:2px;">{_esc(comp_text)}</div>
            </div>
            {extra_cell}
            <div>
                <div style="font-size:9px;font-weight:700;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">FINDINGS SCOPE</div>
                <div style="font-size:11px;font-weight:700;color:#0f172a;margin-top:2px;">{_esc(findings_line)}</div>
            </div>
            <div style="grid-column:1 / -1;padding-top:4px;border-top:1px dashed #e2e8f0;display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;font-size:10px;color:#334155;">
                <span><strong>Configuration:</strong> {_esc(meta.configuration_summary)}</span>
                <span><strong>Section Scores:</strong> {_esc(scores_line)}</span>
            </div>
        </div>
    </div>
    """

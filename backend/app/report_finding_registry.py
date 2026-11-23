"""Canonical finding registry helpers for report assembly.

Kept dependency-light so deduplication behavior can be regression-tested without
importing the full agent orchestration/report package.
"""
from __future__ import annotations

import re
from typing import Any


def finding_value(finding: Any, key: str, default: Any = None) -> Any:
    """Read a field from a Pydantic/object finding or a dictionary."""
    if isinstance(finding, dict):
        return finding.get(key, default)
    return getattr(finding, key, default)


def canonicalize_report_findings(report: Any) -> list[Any]:
    """Return one canonical record per repeated finding identity.

    Stable finding IDs take precedence. Without an ID, only matching normalized
    titles on the same affected URL are collapsed; similar issues on different
    pages remain independent findings.
    """
    raw = list(report) if isinstance(report, (list, tuple)) else list(getattr(report, "findings", []) or [])
    canonical: list[Any] = []
    seen: set[tuple[str, tuple[str, ...], str, str, tuple[str, ...]]] = set()
    seen_ids: set[str] = set()
    for finding in raw:
        finding_id = str(finding_value(finding, "finding_id", finding_value(finding, "id", "")) or "").strip()
        if finding_id and finding_id in seen_ids:
            continue
        title = re.sub(
            r"\s+",
            " ",
            str(finding_value(finding, "title", finding_value(finding, "name", "")) or ""),
        ).strip().casefold()
        urls = finding_value(finding, "affected_urls", None) or finding_value(finding, "urls", None) or []
        if isinstance(urls, str):
            urls = [urls]
        if not urls:
            url = finding_value(finding, "url", None) or finding_value(finding, "affected_url", None)
            urls = [url] if url else []
        normalized_urls = tuple(sorted({str(url).rstrip("/").casefold() for url in urls if url}))
        root_cause = re.sub(
            r"\s+",
            " ",
            str(finding_value(finding, "root_cause_category", finding_value(finding, "root_cause", "")) or ""),
        ).strip().casefold()
        remediation = re.sub(
            r"\s+",
            " ",
            str(finding_value(finding, "how_to_fix", finding_value(finding, "remediation", "")) or ""),
        ).strip().casefold()
        evidence_refs = finding_value(finding, "evidence_refs", None) or finding_value(finding, "evidence_ids", None) or []
        if isinstance(evidence_refs, str):
            evidence_refs = [evidence_refs]
        evidence_key = tuple(sorted(str(ref) for ref in evidence_refs if ref))
        # Without a stable ID, matching wording and URL alone is not enough:
        # require a shared root cause, remediation, or evidence reference.
        has_corroborating_identity = bool(root_cause or remediation or evidence_key)
        identity = (
            title,
            normalized_urls,
            root_cause,
            remediation,
            evidence_key,
        ) if title and normalized_urls and has_corroborating_identity else (
            finding_id or str(id(finding)),
            normalized_urls,
            "",
            "",
            (),
        )
        if identity in seen:
            continue
        seen.add(identity)
        if finding_id:
            seen_ids.add(finding_id)
        canonical.append(finding)
    return canonical


def summarize_finding_severities(findings: Any) -> dict[str, int]:
    """Single canonical severity counter over deduplicated findings."""
    dummy = type("_Rep", (), {"findings": list(findings or [])})()
    deduped = canonicalize_report_findings(dummy)
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for f in deduped:
        if bool(finding_value(f, "held_from_executive", False)):
            continue
        raw_sev = finding_value(f, "severity", "MEDIUM")
        sev = str(getattr(raw_sev, "value", raw_sev) or "MEDIUM").upper()
        if "CRIT" in sev:
            counts["CRITICAL"] += 1
        elif "HIGH" in sev:
            counts["HIGH"] += 1
        elif "MED" in sev:
            counts["MEDIUM"] += 1
        elif "LOW" in sev:
            counts["LOW"] += 1
        else:
            counts["INFO"] += 1
    total = sum(counts.values())
    return {
        **counts,
        "total": total,
        "high_or_critical": counts["CRITICAL"] + counts["HIGH"],
    }


def _set_finding_value(finding: Any, key: str, value: Any) -> None:
    if isinstance(finding, dict):
        finding[key] = value
    else:
        try:
            setattr(finding, key, value)
        except Exception:
            pass


def compute_canonical_severity(finding: Any) -> str:
    """Single deterministic severity normalizer used across all 6 PDFs."""
    raw = finding_value(finding, "severity", "MEDIUM")
    text = str(getattr(raw, "value", raw) or "MEDIUM").strip().upper()
    if "CRIT" in text or text == "P0":
        return "CRITICAL"
    if "HIGH" in text or text == "P1":
        return "HIGH"
    if "MED" in text or text == "P2":
        return "MEDIUM"
    if "LOW" in text or text == "P3":
        return "LOW"
    return "INFO"


def compute_canonical_effort(finding: Any) -> str:
    """Single deterministic effort labeler used across all 6 PDFs."""
    raw_est = finding_value(finding, "estimated_effort", None)
    if isinstance(raw_est, str) and raw_est.strip():
        low = raw_est.strip().lower()
        if any(k in low for k in ("high", "large", "day", "week")):
            return "High"
        if any(k in low for k in ("med", "moderate", "2-4", "3 hour", "4 hour")):
            return "Medium"
        if any(k in low for k in ("low", "small", "quick", "min", "1 hour", "< 2")):
            return "Low"
    raw_num = finding_value(finding, "effort", 5)
    try:
        score = float(raw_num)
    except (TypeError, ValueError):
        return "Medium"
    if score <= 3:
        return "Low"
    if score <= 6:
        return "Medium"
    return "High"


def resolve_owning_chapter(finding: Any) -> str:
    """Assign each finding to exactly one owning chapter: seo | geo | aeo | cro | crawl."""
    existing = str(finding_value(finding, "owning_chapter", "") or "").strip().lower()
    if existing in {"seo", "geo", "aeo", "cro", "crawl"}:
        return existing

    rule_id = str(finding_value(finding, "rule_id", "") or "").upper()
    cat = str(getattr(finding_value(finding, "category", ""), "value", finding_value(finding, "category", "")) or "").upper()
    title = str(finding_value(finding, "title", "") or "").lower()

    if any(k in rule_id for k in ("TTFB", "STATUS_4XX", "CLICK_DEPTH", "ORPHAN", "REDIRECT", "ROBOTS", "SITEMAP")):
        return "crawl"
    if any(k in cat for k in ("AEO", "ANSWER_ENGINE")):
        return "aeo"
    if any(k in cat for k in ("GEO", "SCHEMA", "AI_VISIBILITY", "ENTITY")) or "schema" in rule_id or "json-ld" in title:
        return "geo"
    if any(k in cat for k in ("CRO", "UX", "ACCESSIBILITY", "WCAG", "CONVERSION", "CTA", "FORM")) or "WCAG" in rule_id or "CTA" in rule_id:
        return "cro"
    if any(k in title for k in ("ttfb", "orphan", "click depth", "crawl", "redirect", "404", "5xx")):
        return "crawl"
    return "seo"


CONNECTOR_VERDICT_RULES: list[tuple[tuple[str, ...], str, str, str]] = [
    (
        ("ttfb", "cls", "lcp", "inp", "cwv", "image", "dimension", "speed", "performance"),
        "YES",
        "PageSpeed/CrUX",
        "Fix is verifiable in lab/re-crawl; real-user Core Web Vitals gain requires PageSpeed/CrUX.",
    ),
    (
        ("title", "meta", "h1", "canonical", "sitemap", "orphan", "depth", "index"),
        "PARTIAL",
        "Search Console",
        "DOM/HTTP fix is verifiable on re-crawl; ranking, indexation, and CTR impact require Search Console.",
    ),
    (
        ("cta", "form", "wcag", "accessibility", "cro", "ux", "conversion", "funnel", "revenue"),
        "CANNOT CONFIRM",
        "GA4",
        "DOM fix is checkable on re-crawl; conversion and revenue impact cannot be confirmed without GA4.",
    ),
    (
        ("backlink", "authority", "link equity", "redirect"),
        "PARTIAL",
        "Backlinks",
        "HTTP status and redirect path are verifiable; external link-equity impact requires a Backlinks connector.",
    ),
    (
        ("aeo", "geo", "schema", "json-ld", "citation", "ai visibility", "llm", "bot"),
        "CANNOT CONFIRM",
        "Live AI/AEO",
        "Markup/readiness fix is verifiable on re-crawl; live AI citation and visibility lift require Live AI/AEO.",
    ),
    (
        ("nap", "local", "gbp", "bing", "phone", "address"),
        "CANNOT CONFIRM",
        "GBP/Bing",
        "On-page NAP fix is verifiable; local pack and Bing indexing effects require GBP/Bing connectors.",
    ),
]


def resolve_connector_verdict(
    finding: Any,
    active_connectors: set[str] | list[str] | None = None,
) -> dict[str, Any]:
    """Compute the deterministic connector verdict line for Block 5 of the finding card."""
    existing = finding_value(finding, "connector_effect", None)
    if isinstance(existing, dict) and existing.get("resolves_issue") and existing.get("why"):
        return existing

    active_norm = {str(c).strip().lower() for c in (active_connectors or []) if c}
    blob = " ".join([
        str(finding_value(finding, "rule_id", "") or ""),
        str(finding_value(finding, "title", "") or ""),
        str(getattr(finding_value(finding, "category", ""), "value", finding_value(finding, "category", "")) or ""),
    ]).lower()

    for keywords, default_verdict, connector_name, why in CONNECTOR_VERDICT_RULES:
        if any(k in blob for k in keywords):
            is_connected = connector_name.lower() in active_norm
            if is_connected:
                return {
                    "resolves_issue": "YES",
                    "needs_connector": None,
                    "why": f"Fix is DOM/HTTP verifiable and {connector_name} is connected for post-fix telemetry.",
                }
            return {
                "resolves_issue": default_verdict,
                "needs_connector": connector_name,
                "why": why,
            }

    return {
        "resolves_issue": "PARTIAL",
        "needs_connector": "Search Console",
        "why": "Technical fix is verifiable by re-crawl; downstream search/user impact requires connected telemetry.",
    }


def is_passed_check(finding: Any) -> bool:
    """Return True when a record represents a passed check rather than a defect."""
    status = str(getattr(finding_value(finding, "status", ""), "value", finding_value(finding, "status", "")) or "").upper()
    cls = str(getattr(finding_value(finding, "classification", ""), "value", finding_value(finding, "classification", "")) or "").upper()
    title = str(finding_value(finding, "title", "") or "").lower()
    if status in {"PASS", "PASSED", "CLEAN"} or cls in {"PASS", "PASSED", "PASSED_CHECK"}:
        return True
    if title.startswith(("passed:", "pass:", "[pass]")):
        return True
    return False


def normalize_canonical_findings(
    report: Any,
    active_connectors: set[str] | list[str] | None = None,
) -> list[Any]:
    """Return deduplicated defect-only findings with frozen canonical chapter, severity, effort & connector verdict."""
    raw_canonical = canonicalize_report_findings(report)
    normalized: list[Any] = []
    for f in raw_canonical:
        if is_passed_check(f):
            continue
        owner_ch = resolve_owning_chapter(f)
        sev = compute_canonical_severity(f)
        eff = compute_canonical_effort(f)
        verdict = resolve_connector_verdict(f, active_connectors=active_connectors)
        _set_finding_value(f, "owning_chapter", owner_ch)
        _set_finding_value(f, "estimated_effort", eff)
        _set_finding_value(f, "connector_effect", verdict)
        if not finding_value(f, "algo_trace", None):
            rule_id = str(finding_value(f, "rule_id", "") or finding_value(f, "finding_id", "RULE"))
            obs = finding_value(f, "observed_value", None) or finding_value(f, "observed_result", None) or finding_value(f, "title", "Defect observed")
            _set_finding_value(f, "algo_trace", [{
                "rule_id": rule_id,
                "input": str(finding_value(f, "evidence_subtype", "DOM/HTTP") or "DOM/HTTP"),
                "threshold": str(finding_value(f, "expected_condition", "Must satisfy audit policy") or "Must satisfy audit policy"),
                "observed": str(obs)[:120],
                "status": "FAIL",
            }])
        # Keep severity string/enum consistent on dicts
        if isinstance(f, dict):
            f["severity"] = sev
        normalized.append(f)
    return normalized


def partition_findings_for_chapter(
    canonical_findings: list[Any],
    chapter_id: str,
) -> tuple[list[Any], list[Any]]:
    """Split canonical findings into (owned_by_this_chapter, cross_references_from_other_chapters)."""
    target = (chapter_id or "").strip().lower()
    owned: list[Any] = []
    cross_refs: list[Any] = []
    for f in canonical_findings:
        owner = resolve_owning_chapter(f)
        if owner == target:
            owned.append(f)
        else:
            cross_refs.append(f)
    return owned, cross_refs


def chapter_has_defects(owned_findings: list[Any]) -> bool:
    """Single computed guard for 'no defects' banners — can never be hardcoded."""
    return len(owned_findings or []) > 0

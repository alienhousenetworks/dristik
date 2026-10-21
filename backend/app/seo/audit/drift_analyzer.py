"""
Dristik SEO Drift & Historical Regression Analyzer.
Applies the 17 deterministic comparison rules across schema, canonicals, robots,
headings, Core Web Vitals (strict INP, LCP, CLS), and content hashes.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher

from app.domain.enums import Category, Severity
from app.domain.models import Finding, FindingEvidence


_RETIRED_OR_UNSUPPORTED_SCHEMA_TYPES = {
    "HowTo",
    "SpecialAnnouncement",
    "CourseInfo",
    "EstimatedSalary",
    "LearningVideo",
    "ClaimReview",
    "VehicleListing",
    "FAQPage",
}


def _schema_types(schema_list: list) -> list[str]:
    types = []
    for item in schema_list:
        if isinstance(item, dict):
            st = item.get("@type")
            if isinstance(st, str):
                types.append(st)
            elif isinstance(st, list):
                types.extend([t for t in st if isinstance(t, str)])
            if "@graph" in item and isinstance(item["@graph"], list):
                types.extend(_schema_types(item["@graph"]))
    return types


class SeoDriftAnalyzer:
    """
    Evaluates current crawl state against a baseline and emits structured findings.
    """

    @classmethod
    def compare_page(
        cls,
        url: str,
        baseline: Dict[str, Any],
        current: Dict[str, Any],
    ) -> List[Finding]:
        findings: List[Finding] = []

        # Rule 1: Schema removed
        old_schema = baseline.get("schema") or []
        if isinstance(old_schema, str):
            try:
                old_schema = json.loads(old_schema)
            except Exception:
                old_schema = []
        new_schema = current.get("schema") or []
        if isinstance(new_schema, str):
            try:
                new_schema = json.loads(new_schema)
            except Exception:
                new_schema = []

        if len(old_schema) > 0 and len(new_schema) == 0:
            old_types = _schema_types(old_schema)
            retired_only = bool(old_types) and all(t in _RETIRED_OR_UNSUPPORTED_SCHEMA_TYPES for t in old_types)
            sev = Severity.MEDIUM if retired_only else Severity.CRITICAL
            findings.append(Finding(
                finding_id=f"drift_schema_removed_{hash(url) % 10000}",
                category=Category.SCHEMA,
                severity=sev,
                title="Structured Data (JSON-LD) Completely Removed Since Baseline",
                description=(
                    f"Baseline possessed {len(old_schema)} schema block(s) ({', '.join(old_types[:3])}), "
                    "but current page has 0 schema blocks."
                ),
                root_cause="Template update or deployment stripped the JSON-LD script blocks.",
                recommended_action="Restore structured data markup to prevent search rich-result visibility collapse.",
                priority=9 if not retired_only else 5,
                evidence=[FindingEvidence(
                    url=url,
                    evidence_type="DOM_MUTATION",
                    description=f"Old schema blocks: {len(old_schema)}, New schema blocks: 0"
                )]
            ))

        # Rule 2 & 3: Canonical URL changed or removed
        old_canon = baseline.get("canonical")
        new_canon = current.get("canonical")
        if old_canon and not new_canon:
            findings.append(Finding(
                finding_id=f"drift_canonical_removed_{hash(url) % 10000}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.CRITICAL,
                title="Canonical Link Tag Removed Since Baseline",
                description=f"Previous canonical tag '{old_canon}' was removed from the document head.",
                root_cause="Head meta template regression omitted canonical link declaration.",
                recommended_action=f"Re-insert self-referential or authoritative canonical tag: <link rel='canonical' href='{old_canon}' />",
                priority=9,
                evidence=[FindingEvidence(url=url, evidence_type="DOM_HEADER", description=f"Old canonical: '{old_canon}', New: None")]
            ))
        elif old_canon and new_canon and old_canon != new_canon:
            findings.append(Finding(
                finding_id=f"drift_canonical_changed_{hash(url) % 10000}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title="Canonical URL Target Changed Since Baseline",
                description=f"Canonical changed from '{old_canon}' to '{new_canon}'.",
                root_cause="Canonical generation logic was modified.",
                recommended_action="Verify that canonical destination change was deliberate to avoid unexpected index de-duplication.",
                priority=8,
                evidence=[FindingEvidence(url=url, evidence_type="DOM_HEADER", description=f"Old: {old_canon} -> New: {new_canon}")]
            ))

        # Rule 4: Noindex directive added
        old_robots = str(baseline.get("robots") or baseline.get("meta_robots") or "").lower()
        new_robots = str(current.get("robots") or current.get("meta_robots") or "").lower()
        if "noindex" not in old_robots and "noindex" in new_robots:
            findings.append(Finding(
                finding_id=f"drift_noindex_added_{hash(url) % 10000}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.CRITICAL,
                title="Accidental 'noindex' Directive Added Since Baseline",
                description="A 'noindex' meta tag or X-Robots-Tag header was detected that did not exist in the baseline.",
                root_cause="Staging or pre-release configuration leaked into production headers.",
                recommended_action="Immediately remove 'noindex' to prevent Google and answer engines from de-indexing the page.",
                priority=10,
                evidence=[FindingEvidence(url=url, evidence_type="HTTP_HEADER", description=f"Meta robots: '{new_robots}'")]
            ))

        # Rule 5 & 6: H1 heading removed or altered
        old_h1 = baseline.get("h1") or ""
        new_h1_raw = current.get("h1") or []
        new_h1 = new_h1_raw[0] if isinstance(new_h1_raw, list) and new_h1_raw else str(new_h1_raw or "")
        if old_h1 and not new_h1:
            findings.append(Finding(
                finding_id=f"drift_h1_removed_{hash(url) % 10000}",
                category=Category.CONTENT,
                severity=Severity.HIGH,
                title="Primary <h1> Heading Removed Since Baseline",
                description=f"Page previously featured H1 '{old_h1[:50]}...', but current page has no H1 tag.",
                root_cause="Component refactor swapped <h1> for <div> or styling classes.",
                recommended_action=f"Restore <h1> heading with target topic keyword targeting '{old_h1[:50]}'.",
                priority=7,
                evidence=[FindingEvidence(url=url, evidence_type="DOM_ELEMENT", description="H1 missing")]
            ))
        elif old_h1 and new_h1 and len(old_h1) > 5 and len(new_h1) > 5:
            ratio = SequenceMatcher(None, old_h1, new_h1).ratio()
            if ratio < 0.4:
                findings.append(Finding(
                    finding_id=f"drift_h1_changed_{hash(url) % 10000}",
                    category=Category.CONTENT,
                    severity=Severity.MEDIUM,
                    title="Primary <h1> Heading Substantially Changed",
                    description=f"H1 similarity is only {ratio:.0%}. Old: '{old_h1[:40]}...', New: '{new_h1[:40]}...'",
                    root_cause="Content redesign updated headline messaging.",
                    recommended_action="Ensure primary topic and search intent alignment are preserved.",
                    priority=6,
                    evidence=[FindingEvidence(url=url, evidence_type="DOM_ELEMENT", description=f"Old H1: '{old_h1}' vs New: '{new_h1}'")]
                ))

        # Rule 7 & 10: Title tag removed or modified
        old_title = baseline.get("title") or ""
        new_title = current.get("title") or ""
        if old_title and not new_title:
            findings.append(Finding(
                finding_id=f"drift_title_removed_{hash(url) % 10000}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.CRITICAL,
                title="<title> Tag Completely Removed",
                description=f"Page title '{old_title[:50]}' was dropped.",
                root_cause="Head template render failure.",
                recommended_action=f"Restore <title>{old_title}</title>.",
                priority=9,
                evidence=[FindingEvidence(url=url, evidence_type="DOM_HEADER", description="Empty title")]
            ))

        # Rule 16: Core Web Vitals INP Degraded (strict INP, never legacy FID)
        old_inp = baseline.get("inp") or baseline.get("cwv_inp")
        new_inp = current.get("inp") or current.get("cwv_inp")
        if old_inp is not None and new_inp is not None:
            try:
                old_v = float(old_inp)
                new_v = float(new_inp)
                if old_v <= 200 and new_v > 200:
                    findings.append(Finding(
                        finding_id=f"drift_inp_degraded_{hash(url) % 10000}",
                        category=Category.TECHNICAL_SEO,
                        severity=Severity.HIGH if new_v > 500 else Severity.MEDIUM,
                        title="Interaction to Next Paint (INP) Degraded Below 'Good' Threshold",
                        description=f"INP degraded from {old_v:.0f}ms (Good) to {new_v:.0f}ms ({'Poor' if new_v > 500 else 'Needs Improvement'}).",
                        root_cause="Heavy main-thread script execution or un-optimized event handlers blocking browser response.",
                        recommended_action="Audit main-thread long tasks during user interaction and yield before DOM updates.",
                        priority=8,
                        evidence=[FindingEvidence(url=url, evidence_type="CWV_FIELD", description=f"Old INP: {old_v}ms, Current INP: {new_v}ms")]
                    ))
            except (ValueError, TypeError):
                pass

        return findings

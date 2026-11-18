"""
Finding Deduplication & Canonical Root-Cause Registry — Enterprise Quality Standard (Phase 0.3)

Prevents issue count inflation by mapping multi-element and multi-disciplinary observations
to single canonical findings backed by granular evidence records.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from app.domain.enums import RootCauseTaxonomy, Severity, Category, FindingStatus
from app.domain.canonical_audit_model import CanonicalFinding, EvidenceRecord


class RootCauseRegistry:
    """
    Taxonomy and rule mappings that consolidate isolated page defects into unified canonical findings.
    """

    ROOT_CAUSE_CONFIG = {
        RootCauseTaxonomy.MISSING_ALT_TEXT: {
            "title_template": "Missing meaningful alternative text on {count} inspected image element(s)",
            "disciplines": ["TECHNICAL_SEO", "ACCESSIBILITY", "CRO"],
            "category": Category.ON_PAGE_SEO,
            "severity": Severity.LOW,
            "recommendation": "Provide descriptive alt attributes for all informative images; mark purely decorative graphics with alt=''.",
        },
        RootCauseTaxonomy.UNOPTIMIZED_TTFB: {
            "title_template": "Elevated server response time (TTFB latency) on {count} sampled URL(s)",
            "disciplines": ["TECHNICAL_SEO", "CORE_WEB_VITALS", "CRO"],
            "category": Category.TECHNICAL_SEO,
            "severity": Severity.HIGH,
            "recommendation": "Implement edge caching, database query optimization, or CDN proxying to bring TTFB under 800ms.",
        },
        RootCauseTaxonomy.CANONICAL_MISMATCH: {
            "title_template": "Canonical URL link divergence detected across {count} page(s)",
            "disciplines": ["TECHNICAL_SEO", "INDEXATION"],
            "category": Category.TECHNICAL_SEO,
            "severity": Severity.HIGH,
            "recommendation": "Harmonize rel=canonical declarations to point to authoritative, indexable HTTPS URLs.",
        },
        RootCauseTaxonomy.SCHEMA_SYNTAX_ERROR: {
            "title_template": "Structured data schema validation errors on {count} template(s)",
            "disciplines": ["TECHNICAL_SEO", "GEO", "AEO"],
            "category": Category.SCHEMA,
            "severity": Severity.MEDIUM,
            "recommendation": "Correct JSON-LD schema syntax and provide required Schema.org entity properties.",
        },
        RootCauseTaxonomy.ORPHAN_URL: {
            "title_template": "Orphan pages with zero internal links detected on {count} endpoint(s)",
            "disciplines": ["TECHNICAL_SEO", "INTERNAL_LINKING"],
            "category": Category.TECHNICAL_SEO,
            "severity": Severity.MEDIUM,
            "recommendation": "Add contextual internal links from relevant parent categories to restore link equity.",
        },
        RootCauseTaxonomy.MISSING_H1: {
            "title_template": "Missing or ambiguous primary H1 heading on {count} landing page(s)",
            "disciplines": ["TECHNICAL_SEO", "ACCESSIBILITY", "CRO"],
            "category": Category.ON_PAGE_SEO,
            "severity": Severity.MEDIUM,
            "recommendation": "Ensure every indexable page has exactly one prominent, descriptive H1 tag.",
        },
        RootCauseTaxonomy.CTA_FRICTION: {
            "title_template": "Conversion trigger or CTA microcopy friction on {count} interactive element(s)",
            "disciplines": ["CRO", "UX_CONVERSION"],
            "category": Category.UX_CONVERSION,
            "severity": Severity.MEDIUM,
            "recommendation": "Use specific, high-intent action copy on primary buttons rather than generic placeholders.",
        },
        RootCauseTaxonomy.FORM_ACCESSIBILITY: {
            "title_template": "Accessible form input labels missing on {count} form element(s)",
            "disciplines": ["ACCESSIBILITY", "CRO"],
            "category": Category.UX_CONVERSION,
            "severity": Severity.HIGH,
            "recommendation": "Attach explicit <label for='...'> tags to all interactive form fields.",
        },
    }

    @classmethod
    def map_diagnostic_to_root_cause(cls, rule_id: str, title: str) -> RootCauseTaxonomy:
        """Determines the canonical root-cause key from rule or finding description."""
        text = f"{rule_id} {title}".upper()
        if any(k in text for k in ("ALT", "IMG_ALT", "NON_TEXT_CONTENT")):
            return RootCauseTaxonomy.MISSING_ALT_TEXT
        if any(k in text for k in ("TTFB", "RESPONSE_TIME", "LATENCY")):
            return RootCauseTaxonomy.UNOPTIMIZED_TTFB
        if any(k in text for k in ("CANONICAL", "SELF_CANONICAL")):
            return RootCauseTaxonomy.CANONICAL_MISMATCH
        if any(k in text for k in ("SCHEMA", "JSONLD", "RICH_RESULT")):
            return RootCauseTaxonomy.SCHEMA_SYNTAX_ERROR
        if any(k in text for k in ("ORPHAN", "UNLINKED", "NO_INTERNAL_LINKS")):
            return RootCauseTaxonomy.ORPHAN_URL
        if any(k in text for k in ("H1", "HEADING_MISSING", "EMPTY_H1")):
            return RootCauseTaxonomy.MISSING_H1
        if any(k in text for k in ("CTA", "CALL_TO_ACTION", "BUTTON_COPY")):
            return RootCauseTaxonomy.CTA_FRICTION
        if any(k in text for k in ("FORM", "LABEL", "INPUT_LABEL")):
            return RootCauseTaxonomy.FORM_ACCESSIBILITY
        return RootCauseTaxonomy.GENERIC


class FindingDeduplicator:
    """
    Aggregates page-level observations into unified canonical findings.
    """

    @classmethod
    def aggregate_evidence_into_canonical_findings(
        cls,
        audit_run_id: str,
        domain_id: str,
        evidence_records: List[EvidenceRecord],
    ) -> List[CanonicalFinding]:
        """
        Groups evidence records by canonical root cause, producing exactly one finding per root cause
        with complete element evidence attached and zero duplicate executive counts.
        """
        grouped_evidence: Dict[RootCauseTaxonomy, List[EvidenceRecord]] = {}

        for rec in evidence_records:
            rc_key = RootCauseRegistry.map_diagnostic_to_root_cause(
                rec.collection_method or "",
                rec.observed_condition or rec.expected_condition or ""
            )
            grouped_evidence.setdefault(rc_key, []).append(rec)

        canonical_findings: List[CanonicalFinding] = []
        for rc_key, records in grouped_evidence.items():
            if rc_key == RootCauseTaxonomy.GENERIC:
                # Group generic by unique observed condition
                generic_subgroups: Dict[str, List[EvidenceRecord]] = {}
                for r in records:
                    generic_subgroups.setdefault(r.observed_condition or "General Observation", []).append(r)
                for gen_title, gen_recs in generic_subgroups.items():
                    canonical_findings.append(cls._build_canonical_finding(
                        audit_run_id=audit_run_id,
                        domain_id=domain_id,
                        root_cause=RootCauseTaxonomy.GENERIC,
                        records=gen_recs,
                        custom_title=f"{gen_title} ({len(gen_recs)} affected element(s))",
                    ))
            else:
                canonical_findings.append(cls._build_canonical_finding(
                    audit_run_id=audit_run_id,
                    domain_id=domain_id,
                    root_cause=rc_key,
                    records=records,
                ))

        return canonical_findings

    @classmethod
    def _build_canonical_finding(
        cls,
        audit_run_id: str,
        domain_id: str,
        root_cause: RootCauseTaxonomy,
        records: List[EvidenceRecord],
        custom_title: Optional[str] = None,
    ) -> CanonicalFinding:
        cfg = RootCauseRegistry.ROOT_CAUSE_CONFIG.get(root_cause, {
            "title_template": "{title}",
            "disciplines": ["TECHNICAL_SEO"],
            "category": Category.TECHNICAL_SEO,
            "severity": Severity.MEDIUM,
            "recommendation": "Review and remediate according to technical documentation.",
        })

        count = len(records)
        title = custom_title or cfg["title_template"].format(count=count)
        affected_urls = list(sorted({r.url for r in records if r.url}))
        evidence_ids = [r.evidence_id for r in records]

        finding_id = f"FND_{root_cause.value}_{uuid.uuid4().hex[:8]}"

        desc = (
            f"Consolidated root cause '{root_cause.value}' diagnosed across {count} affected element(s) "
            f"and {len(affected_urls)} unique URL(s)."
        )

        return CanonicalFinding(
            audit_run_id=audit_run_id,
            domain_id=domain_id,
            finding_id=finding_id,
            root_cause_key=root_cause,
            category=cfg["category"],
            title=title,
            description=desc,
            severity=cfg["severity"],
            status=FindingStatus.OPEN,
            affected_urls=affected_urls,
            evidence_ids=evidence_ids,
            evidence_records=records,
            recommendation_text=cfg["recommendation"],
            relevant_disciplines=cfg["disciplines"],
        )

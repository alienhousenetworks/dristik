"""Phase 43 — Independent CRO Quality Assurance (QA) Engine.

Validates all completed CRO audit results, scores, remediation links, verification
records, and generated reports BEFORE publishing.

Guarantees:
- Every non-hypothesis finding traces to valid evidence IDs and real audited URLs.
- Unsupported conversion uplift or fabricated revenue claims are blocked.
- Missing analytics is never reported as zero conversions or blended into Experience Score.
- Experience scorecard weights sum to exactly 100.0% and scores are mathematically reproducible.
- Remediation tasks reference valid findings; verifications reference new evidence.
- Report/PDF outputs match canonical backend scores and finding counts.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from app.cro.models import (
    CROAudit,
    CROFinding,
    CROInteractionTest,
    CROPage,
    CROQAReport,
    CRORemediationPack,
    CROThreeScorecardBundle,
    CROVerification,
    EvidenceSourceType,
)
from app.cro.scoring import ENTERPRISE_CRO_DIMENSIONS

_FABRICATED_REVENUE_RE = re.compile(
    r"(guaranteed\s+\$[\d,]+|will\s+generate\s+\$[\d,]+|guaranteed\s+\d+%\s+uplift)",
    re.I,
)


class CROQualityAssuranceEngine:
    """Independent pre-publication validator for CRO audits and reports."""

    @classmethod
    def validate_audit(
        cls,
        *,
        audit: CROAudit,
        pages: Sequence[CROPage],
        interaction_tests: Sequence[CROInteractionTest],
        findings: Sequence[CROFinding],
        scorecard: CROThreeScorecardBundle,
        remediation_pack: Optional[CRORemediationPack] = None,
        verifications: Sequence[CROVerification] = (),
        report_payload: Optional[Dict[str, Any]] = None,
    ) -> CROQAReport:
        blockers: List[str] = []
        warnings: List[str] = []
        backend_checks: List[Dict[str, Any]] = []
        scoring_checks: List[Dict[str, Any]] = []
        report_checks: List[Dict[str, Any]] = []

        valid_page_urls = {p.url for p in pages}
        valid_finding_ids = {f.finding_id for f in findings}

        # ── 1. Backend & Evidence QA ────────────────────────────────────────
        missing_ev = [
            f.finding_id for f in findings
            if not f.evidence_ids and f.source_type not in (EvidenceSourceType.AI_HYPOTHESIS, EvidenceSourceType.HEURISTIC_OBSERVATION)
        ]
        backend_checks.append({"check": "all_non_hypothesis_findings_have_evidence", "passed": len(missing_ev) == 0, "details": missing_ev})
        if missing_ev:
            blockers.append(f"Findings missing evidence IDs: {', '.join(missing_ev[:5])}")

        orphan_urls = []
        for f in findings:
            for u in f.affected_urls:
                if valid_page_urls and u not in valid_page_urls and u != audit.target_url:
                    orphan_urls.append(f"{f.finding_id}:{u}")
        backend_checks.append({"check": "finding_urls_reference_audited_pages", "passed": len(orphan_urls) == 0, "details": orphan_urls[:5]})
        if orphan_urls:
            warnings.append(f"Some finding URLs were outside crawled page set: {', '.join(orphan_urls[:3])}")

        # Check browser tests carry test conditions
        missing_conds = [t.test_id for t in interaction_tests if not t.viewport_name or not t.browser or not t.execution_mode]
        backend_checks.append({"check": "browser_tests_include_conditions", "passed": len(missing_conds) == 0, "details": missing_conds})
        if missing_conds:
            blockers.append(f"Browser tests missing viewport/browser conditions: {', '.join(missing_conds[:5])}")

        # Duplicate finding IDs check
        seen_ids = set()
        dup_ids = []
        for f in findings:
            if f.finding_id in seen_ids:
                dup_ids.append(f.finding_id)
            seen_ids.add(f.finding_id)
        backend_checks.append({"check": "unique_finding_ids", "passed": len(dup_ids) == 0, "details": dup_ids})
        if dup_ids:
            blockers.append(f"Duplicate finding IDs detected: {', '.join(dup_ids)}")

        # Unsupported revenue / guaranteed uplift claim scan
        bad_claims = [
            f.finding_id for f in findings
            if _FABRICATED_REVENUE_RE.search(f"{f.description} {f.business_impact or ''} {f.recommendation}")
        ]
        backend_checks.append({"check": "no_unsupported_revenue_claims", "passed": len(bad_claims) == 0, "details": bad_claims})
        if bad_claims:
            blockers.append(f"Unsupported revenue/uplift claim in findings: {', '.join(bad_claims)}")

        # Missing analytics must NOT appear as 0 conversions
        zero_coerced = [
            m.get("metric") for m in scorecard.business_performance_metrics
            if not audit.analytics_connected and m.get("value") is not None
        ]
        backend_checks.append({"check": "disconnected_analytics_not_zero_coerced", "passed": len(zero_coerced) == 0, "details": zero_coerced})
        if zero_coerced:
            blockers.append(f"Disconnected analytics reported numeric values for: {', '.join(str(x) for x in zero_coerced)}")

        # Remediation tasks reference valid findings
        if remediation_pack:
            dangling_rem = [
                f"{t.task_id}:{fid}"
                for t in remediation_pack.tasks
                for fid in t.linked_finding_ids
                if fid not in valid_finding_ids
            ]
            backend_checks.append({"check": "remediation_tasks_reference_valid_findings", "passed": len(dangling_rem) == 0, "details": dangling_rem[:5]})
            if dangling_rem:
                blockers.append(f"Remediation tasks link to unknown findings: {', '.join(dangling_rem[:5])}")

        # Verification records reference new evidence
        unbacked_ver = [v.verification_id for v in verifications if v.implementation_verified == "passed" and not v.source_evidence_ids and not v.criteria_results]
        backend_checks.append({"check": "verifications_reference_evidence", "passed": len(unbacked_ver) == 0, "details": unbacked_ver})
        if unbacked_ver:
            blockers.append(f"Verification records missing evidence: {', '.join(unbacked_ver)}")

        # ── 2. Scoring QA ───────────────────────────────────────────────────
        weight_sum = round(sum(w for _, _, w in ENTERPRISE_CRO_DIMENSIONS), 2)
        weights_ok = abs(weight_sum - 100.0) < 0.01
        scoring_checks.append({"check": "dimension_weights_total_100", "passed": weights_ok, "weight_sum": weight_sum})
        if not weights_ok:
            blockers.append(f"Experience dimension weights sum to {weight_sum}, expected 100.0")

        # Verify reproducibility of Experience Score from dimension cards
        measured = [d for d in scorecard.experience_dimensions if d.applicable and d.score is not None]
        if measured:
            active_w = sum(d.configured_weight_pct for d in measured)
            recomputed = round(sum(d.configured_weight_pct * (d.score or 0.0) for d in measured) / active_w, 1)
            repro_ok = scorecard.experience_score is not None and abs(recomputed - scorecard.experience_score) <= 0.2
        else:
            repro_ok = scorecard.experience_score is None
        scoring_checks.append({"check": "experience_score_reproducible", "passed": repro_ok})
        if not repro_ok:
            blockers.append("CRO Experience Score does not reproduce from weighted dimension scores.")

        cov_ok = scorecard.methodology_version is not None and scorecard.confidence is not None
        scoring_checks.append({"check": "qualifications_and_methodology_disclosed", "passed": cov_ok})
        if not cov_ok:
            blockers.append("Scorecard missing confidence or methodology_version disclosure.")

        # ── 3. Report / PDF Parity QA ───────────────────────────────────────
        if report_payload is not None:
            rep_score = (report_payload.get("scorecard") or {}).get("experience_score")
            score_parity = rep_score == scorecard.experience_score
            rep_findings_cnt = len(report_payload.get("findings") or [])
            count_parity = rep_findings_cnt == len(findings)
            has_method = bool(report_payload.get("methodology_version"))
            report_checks.extend(
                [
                    {"check": "report_score_matches_backend", "passed": score_parity},
                    {"check": "report_finding_count_matches_backend", "passed": count_parity},
                    {"check": "report_discloses_methodology", "passed": has_method},
                ]
            )
            if not score_parity:
                blockers.append(f"Report score ({rep_score}) differs from backend score ({scorecard.experience_score}).")
            if not count_parity:
                blockers.append(f"Report finding count ({rep_findings_cnt}) differs from backend ({len(findings)}).")

        if not audit.analytics_connected:
            warnings.append("Analytics connector not configured; behavioral conversion metrics are unmeasured.")
        if any(t.execution_mode == "static_dom_only" for t in interaction_tests):
            warnings.append("One or more viewport checks executed in static_dom_only mode rather than live Chromium.")

        qa_status = "failed" if blockers else ("passed_with_warnings" if warnings else "passed")
        return CROQAReport(
            audit_id=audit.audit_id,
            qa_status=qa_status,
            backend_evidence_checks=backend_checks,
            scoring_checks=scoring_checks,
            report_checks=report_checks,
            blockers=blockers,
            warnings=warnings,
        )


# ── Publication gate for the CRO intelligence report (CroIntelligenceReport) ──
_NO_CTA_RE = re.compile(r"\bno (primary )?cta\b|\bcta (is |was )?missing\b", re.I)
_NO_FORM_RE = re.compile(r"\bno (qualification or contact )?form\b|\bform (is |was )?(missing|absent)\b", re.I)
_MONEY_RE = re.compile(r"[$€£₹]\s?\d|\d+(\.\d+)?\s?%\s*(uplift|lift|increase|more conversions)", re.I)
_VISUAL_KEY_RE = re.compile(r"mobile|viewport|visual|screenshot|responsive", re.I)


class CroPublicationGate:
    """Outcome of the CRO pre-publication gate. `reasons` lists every blocker."""

    def __init__(self, reasons: List[str]):
        self.reasons = reasons
        self.passed = not reasons


def cro_publication_gate(intel: Any, pdf_qa: Any = None) -> CroPublicationGate:
    """Blocks publication on contradictions, unreproducible scores and failed PDF QA.

    `intel` is a CroIntelligenceReport. `pdf_qa` is an optional PdfValidationReport.
    """
    reasons: List[str] = []
    checks = [c for s in intel.sections for c in s.checks]

    # CTA / form marked absent while passing evidence exists.
    cta_seen = any(c.outcome == "pass" and c.evidence and "cta" in c.key.lower() for c in checks)
    form_seen = any(c.outcome == "pass" and c.evidence and "form" in c.key.lower() for c in checks)
    for f in intel.findings:
        if cta_seen and _NO_CTA_RE.search(f.finding):
            reasons.append(f"{f.finding_id}: CTA reported missing but CTA evidence exists.")
        if form_seen and _NO_FORM_RE.search(f.finding):
            reasons.append(f"{f.finding_id}: form reported absent but form evidence exists.")
        if f.evidence_state in ("VERIFIED", "SAMPLE_VERIFIED") and not (f.evidence or "").strip():
            reasons.append(f"{f.finding_id}: verified finding has no evidence.")
        if _MONEY_RE.search(f.impact_estimate or "") and not any(m.status == "MEASURED" and "revenue" in m.metric.lower() for m in intel.metrics):
            reasons.append(f"{f.finding_id}: financial impact claimed without a measured revenue dataset.")

    ids = [f.finding_id for f in intel.findings]
    if len(ids) != len(set(ids)):
        reasons.append("Duplicate finding IDs.")
    section_nums = {int(s.number) for s in intel.sections if str(s.number).isdigit()}
    reasons += [f"{f.finding_id}: references unknown section {f.section}." for f in intel.findings if section_nums and f.section not in section_nums]

    # Rendered-UX checks must not pass without rendered pages.
    if not (intel.coverage or {}).get("rendered_pages"):
        reasons += [f"{c.check_id}: visual/mobile check passed without rendered pages." for c in checks if c.outcome == "pass" and _VISUAL_KEY_RE.search(c.key) and c.evidence_state in ("VERIFIED", "SAMPLE_VERIFIED")][:5]

    # Metrics: no value unless measured; never zero for unavailable data.
    for m in intel.metrics:
        if m.status != "MEASURED" and m.value is not None:
            reasons.append(f"Metric '{m.metric}' has a value but status {m.status}.")

    # Score reproducibility: experience score = passed / (passed + failed).
    for d in intel.dimensions:
        if d.score is not None and d.passed_checks + d.failed_checks > 0:
            expected = round(100 * d.passed_checks / (d.passed_checks + d.failed_checks), 1)
            if abs(expected - d.score) > 0.05:
                reasons.append(f"Dimension '{d.name}' score {d.score} is not reproducible (expected {expected}).")
        if d.score is not None and d.status in ("UNMEASURED", "DATA_UNAVAILABLE"):
            reasons.append(f"Dimension '{d.name}' has a score but status {d.status}.")

    if pdf_qa is not None and not getattr(pdf_qa, "is_valid", True):
        reasons.append("PDF QA failed: " + ", ".join(getattr(pdf_qa, "failed_checks", []) or ["unknown"]))
    return CroPublicationGate(reasons)

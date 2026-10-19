"""Eighteen-section finding cards. Empty proof is an incomplete card, not a placeholder."""

from __future__ import annotations

from app.seo.enterprise.contracts import EnterpriseFinding, FindingCard, FindingCardSection

_HEADINGS = (
    "Finding identity",
    "Classification",
    "Plain-language explanation",
    "Expected behavior",
    "Observed behavior",
    "Scope",
    "Evidence",
    "SEO significance",
    "Root cause",
    "Affected inventory",
    "What needs to be investigated",
    "Investigation notes",
    "Code or configuration",
    "Regression risk",
    "Verification",
    "Priority and effort",
    "Ownership and status",
    "Outcome and residual risk",
)


def _identity(finding: EnterpriseFinding) -> str:
    return (
        f"Finding {finding.finding_id}. Rule {finding.rule_id} version {finding.rule_version}. "
        f"{finding.title}."
    )


def _classification(finding: EnterpriseFinding) -> str:
    return (
        f"{finding.evaluation_state}. Chapter {finding.chapter}. Category {finding.category}. "
        f"Severity {finding.severity}. Claim {finding.claim_kind}. "
        f"Issue type {finding.issue_type}. Rule class {finding.rule_class}. "
        f"{finding.severity_rationale}"
    )


def _scope(finding: EnterpriseFinding) -> str:
    return (
        f"Scope {finding.scope}. The checked sample is not automatically the whole site. "
        f"Eligible URLs in this check: {finding.eligible_count if finding.eligible_count is not None else 'not recorded'}."
    )


def _evidence(finding: EnterpriseFinding) -> str:
    joined = ", ".join(finding.evidence_ids)
    return f"Evidence IDs: {joined}. Observed at {finding.observed_at or 'the sealed audit time'}."


def _inventory(finding: EnterpriseFinding) -> str:
    shown = finding.affected_urls[:20]
    extra = finding.affected_count - len(shown)
    lines = "\n".join(shown) if shown else "No URL was stored."
    suffix = f"\n{extra} more URLs are counted but not listed here." if extra > 0 else ""
    return (
        f"Affected count {finding.affected_count}. "
        f"Eligible count {finding.eligible_count if finding.eligible_count is not None else 'not recorded'}.\n"
        f"{lines}{suffix}"
    )


def _code(finding: EnterpriseFinding) -> str:
    if not finding.code_examples:
        return (
            "No patch was generated. This phase does not write replacement copy or a configuration diff."
        )
    label = "Illustrative example. This code has not been applied." if finding.code_is_illustrative else "Stored implementation note."
    stack = f"Detected environment: {finding.stack_detected}." if finding.stack_detected else "Implementation environment: not identified from the crawl."
    body = "\n\n".join(finding.code_examples)
    return f"{label} {stack}\n\n{body}"


def _fix(finding: EnterpriseFinding) -> str:
    targets = finding.investigation_targets or finding.remediation_steps
    if not targets:
        return "No investigation target was recorded."
    lines = [f"Inspect: {targets[0]}"]
    if len(targets) > 1:
        lines.append("Further checks are in the investigation notes. They are not a patch.")
    return "\n".join(lines)


def _guide(finding: EnterpriseFinding) -> str:
    if not finding.remediation_steps:
        return "No implementation steps were recorded."
    return "\n".join(f"{index}. {step}" for index, step in enumerate(finding.remediation_steps, start=1))


def _verification(finding: EnterpriseFinding) -> str:
    tests = "\n".join(f"- {item}" for item in finding.acceptance_tests) or "- No acceptance test was recorded."
    return (
        f"Verification state: {finding.verification_status}. "
        "A commit or a deployment does not close this finding.\n"
        f"{tests}"
    )


def _outcome(finding: EnterpriseFinding) -> str:
    limits = "\n".join(f"- {item}" for item in finding.limitations) or "- None recorded beyond the sample."
    return (
        f"Status {finding.status}. Verification {finding.verification_status}. "
        "No post-fix snapshot is linked, so the live condition is unresolved.\n"
        f"{limits}"
    )


def build_finding_card(finding: EnterpriseFinding) -> FindingCard:
    bodies = [
        _identity(finding),
        _classification(finding),
        finding.simple_explanation,
        finding.expected_condition,
        finding.observed_condition,
        _scope(finding),
        _evidence(finding),
        (
            f"{finding.seo_significance}\n{finding.business_impact}".strip()
            if finding.business_impact
            else finding.seo_significance
        ),
        f"{finding.cause_label}: {finding.root_cause_hypothesis}",
        _inventory(finding),
        _fix(finding),
        _guide(finding),
        _code(finding),
        finding.regression_risk,
        _verification(finding),
        (
            f"Severity {finding.severity} comes from the versioned rule, not from an estimated traffic gain. "
            f"Effort label: {finding.estimated_effort or 'not estimated'}. "
            f"Dependencies: {', '.join(finding.dependency_ids) or 'none recorded'}."
        ),
        (
            f"Owner role: {finding.owner_role or 'not assigned'}. Status: {finding.status}. "
            "Production changes stay unapproved until a person approves them."
        ),
        _outcome(finding),
    ]
    sections = [
        FindingCardSection(number=index, heading=heading, body=body.strip())
        for index, (heading, body) in enumerate(zip(_HEADINGS, bodies), start=1)
    ]
    complete = len(sections) == 18 and all(section.body for section in sections)
    return FindingCard(
        finding_id=finding.finding_id,
        title=finding.title,
        complete=complete,
        sections=sections,
    )

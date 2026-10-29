"""Execute SEO AI specialists against a supplied evidence packet.

The default path loads each versioned prompt and does not call a model.
A missing completion is an unavailable assessment. It is not a finding.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

from pydantic import ValidationError

from app.seo.enterprise.ai_catalog import AI_AGENTS, AI_REQUIRES
from app.seo.enterprise.contracts import (
    EnterpriseFinding,
    EvidenceRecord,
    RejectedFinding,
    SEOAgentResult,
    Severity,
)
from app.seo.enterprise.prompt_store import PromptError, render_system_prompt
from app.seo.enterprise.taxonomy import CHAPTER_BY_NUMBER

_FABRICATED_IMPACT = re.compile(
    r"(\$|₹|€|£|\b\d[\d,]*\s*(visits|sessions|clicks|impressions|revenue)\b)",
    re.IGNORECASE,
)


class ModelNotRun(Exception):
    """The assessment pass loaded the prompt and did not call a model."""


Runner = Callable[[str, str, int], dict[str, Any]]


def default_ai_runner(system_prompt: str, user_payload: str, timeout_seconds: int) -> dict[str, Any]:
    """Report rendering does not call a model. Callers inject a runner to do that."""
    del system_prompt, user_payload, timeout_seconds
    raise ModelNotRun()


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []


def _passage(page: Any) -> str:
    text = _get(page, "body_text") or _get(page, "text_content") or ""
    if not isinstance(text, str):
        return ""
    return " ".join(text.split())[:2000]


def _page_slices(builder: Any) -> list[dict[str, Any]]:
    slices = []
    for page in builder.pages:
        url = _get(page, "url")
        passage = _passage(page)
        if not isinstance(url, str) or not url or not passage:
            continue
        digest = hashlib.sha256(f"{builder.audit_id}|{url}|{passage}".encode("utf-8")).hexdigest()
        word_count = _get(page, "word_count")
        slices.append({
            "url": url,
            "evidence_id": f"ev_{digest[:16]}",
            "content_hash": digest,
            "title": _get(page, "title") if isinstance(_get(page, "title"), str) else None,
            "headings": [item for item in _as_list(_get(page, "h1")) if isinstance(item, str)][:8],
            "word_count": word_count if isinstance(word_count, int) else None,
            "passage": passage,
            "page_type": _get(page, "page_type") if isinstance(_get(page, "page_type"), str) else None,
            "canonical_url": _get(page, "canonical_url") if isinstance(_get(page, "canonical_url"), str) else None,
        })
    return slices


def _queries(report: Any) -> list[dict[str, Any]] | None:
    rows = _as_list(_get(report, "query_rows"))
    performance = _get(report, "google_performance")
    search = _get(performance, "search_console")
    if not rows:
        rows = _as_list(_get(search, "queries")) or _as_list(_get(search, "rows"))
    cleaned = []
    for row in rows[:50]:
        if isinstance(row, str) and row.strip():
            cleaned.append({"query": row.strip()})
        elif isinstance(row, dict):
            query = row.get("query") or row.get("keys")
            if isinstance(query, list):
                query = query[0] if query else None
            if isinstance(query, str) and query.strip():
                item = {"query": query.strip()}
                page = row.get("page") or row.get("url")
                if isinstance(page, str):
                    item["page"] = page
                cleaned.append(item)
    return cleaned or None


def _audience(report: Any) -> str | None:
    profile = _get(report, "business_profile")
    if profile is None:
        profile = _get(report, "business")
    if isinstance(profile, str) and profile.strip():
        return profile.strip()[:1000]
    if isinstance(profile, dict):
        for key in ("audience", "icp", "description"):
            value = profile.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:1000]
    return None


def _links(builder: Any) -> list[dict[str, str]]:
    rows = []
    for page in builder.pages:
        source = _get(page, "url")
        if not isinstance(source, str):
            continue
        for item in _as_list(_get(page, "anchor_contexts")):
            if not isinstance(item, dict):
                continue
            anchor = item.get("anchor")
            href = item.get("href") or item.get("destination")
            if isinstance(anchor, str) and anchor.strip() and isinstance(href, str) and href.strip():
                rows.append({
                    "source_url": source,
                    "anchor": anchor.strip()[:200],
                    "destination": href.strip(),
                    "sentence": item.get("sentence") if isinstance(item.get("sentence"), str) else "",
                })
    return rows[:80]


def _series(report: Any) -> Any:
    series = _get(report, "historical_snapshots")
    if series:
        return series
    prior = _get(report, "prior_crawl")
    return prior or None


def _finding_slices(findings: list[EnterpriseFinding] | None) -> list[dict[str, Any]]:
    rows = []
    for finding in findings or []:
        rows.append({
            "finding_id": finding.finding_id,
            "rule_id": finding.rule_id,
            "urls": finding.affected_urls[:20],
            "observed": finding.observed_condition,
            "evidence_ids": list(finding.evidence_ids),
            "severity": finding.severity,
            "confidence": finding.confidence,
            "scope": finding.scope,
            "claim_kind": finding.claim_kind,
            "evaluation_state": finding.evaluation_state,
        })
    return rows[:40]


def _packet(builder: Any, findings: list[EnterpriseFinding] | None) -> dict[str, Any]:
    return {
        "audit_run_id": builder.audit_id,
        "host": builder.domain,
        "instruction": "Use only this packet. The host name is scope, not evidence. Do not invent observations.",
        "pages": _page_slices(builder),
        "queries": _queries(builder.report),
        "audience": _audience(builder.report),
        "links": _links(builder),
        "series": _series(builder.report),
        "findings": _finding_slices(findings),
    }


def _gate(requires: str, packet: dict[str, Any]) -> tuple[str, str] | None:
    if requires == "text" and not packet["pages"]:
        return "NOT_TESTED", "No page passage was stored, so this judgment was not run."
    if requires == "text+queries":
        if not packet["pages"]:
            return "NOT_TESTED", "No page passage was stored, so intent was not judged."
        if not packet["queries"]:
            return "DATA_UNAVAILABLE", "No query rows were stored. Search intent was not invented."
    if requires == "queries" and not packet["queries"]:
        return "DATA_UNAVAILABLE", "No query rows were stored. Demand was not invented."
    if requires == "audience":
        if not packet["audience"]:
            return "DATA_UNAVAILABLE", "No audience profile was stored. A persona was not invented from the domain."
        if not packet["pages"]:
            return "NOT_TESTED", "An audience profile was stored, but no page passage was stored."
    if requires == "links" and not packet["links"]:
        return "NOT_TESTED", "Anchor text and destination were not stored together, so link context was not judged."
    if requires == "history" and not packet["series"]:
        return "DATA_UNAVAILABLE", "No historical series was stored. A trend was not invented."
    if requires == "findings" and not packet["findings"]:
        return "NOT_TESTED", "No validated finding was available to review."
    return None


def _result(
    agent_id: str,
    version: str,
    digest: str | None,
    status: str,
    note: str,
    limitations: list[str],
    error: str | None,
    finding_ids: list[str] | None = None,
    evidence_ids: list[str] | None = None,
) -> SEOAgentResult:
    return SEOAgentResult(
        agent_id=agent_id,
        agent_version=version,
        status=status,  # type: ignore[arg-type]
        finding_ids=finding_ids or [],
        evidence_ids=evidence_ids or [],
        coverage_note=note,
        limitations=limitations,
        error_code=error,
        prompt_version=version,
        prompt_sha256=digest,
    )


def _invoke(runner: Runner, system: str, user: str, timeout: int, retries: int) -> tuple[dict[str, Any] | None, str | None, int]:
    attempts = retries + 1
    last = "MODEL_FAILED"
    calls = 0
    for _ in range(attempts):
        calls += 1
        try:
            payload = runner(system, user, timeout)
            return payload, None, calls
        except ModelNotRun:
            raise
        except TimeoutError:
            last = "TIMEOUT"
        except Exception:
            return None, "MODEL_FAILED", calls
    return None, last, calls


def _store_page_evidence(builder: Any, page: dict[str, Any]) -> None:
    evidence_id = page["evidence_id"]
    if evidence_id in builder.evidence:
        return
    builder.evidence[evidence_id] = EvidenceRecord(
        evidence_id=evidence_id,
        content_hash=page["content_hash"],
        audit_run_id=builder.audit_id,
        collected_at=str(builder.generated_at) if builder.generated_at else None,
        source="page.passage",
        url=page["url"],
        snapshot_type="derived",
        collection_method="supplied_passage",
        collector="seo.ai.runtime.v1",
        scope="PAGE_VERIFIED",
        integrity="derived",
    )


def _accept(builder: Any, agent: Any, draft: dict[str, Any], packet: dict[str, Any]) -> EnterpriseFinding | None:
    from pydantic import BaseModel, ConfigDict, Field

    class Draft(BaseModel):
        model_config = ConfigDict(extra="forbid")

        url: str
        evidence_ids: list[str] = Field(min_length=1)
        observation: str = Field(min_length=8)
        explanation: str = Field(min_length=8)
        why_it_matters: str = Field(min_length=8)
        severity: Severity
        confidence: float = Field(ge=0, le=1)
        confidence_rationale: str = Field(min_length=8)
        evaluation_state: str
        claim_kind: str
        investigation: list[str] = Field(min_length=1)
        verification_criteria: list[str] = Field(min_length=1)
        limitations: list[str] = Field(default_factory=list)

    try:
        parsed = Draft.model_validate(draft)
    except ValidationError:
        return None
    if parsed.evaluation_state != "INFERRED":
        return None
    if parsed.claim_kind not in {"judgment", "hypothesis"}:
        return None
    blob = " ".join([parsed.observation, parsed.explanation, parsed.why_it_matters, *parsed.investigation])
    if _FABRICATED_IMPACT.search(blob):
        builder.rejected.append(RejectedFinding(
            rule_id=agent.agent_id,
            title=agent.agent_id,
            reason="The judgment included a traffic, click, or revenue figure that was not in the evidence packet.",
        ))
        return None
    known_pages = {page["url"]: page for page in packet["pages"]}
    known_evidence = {page["evidence_id"] for page in packet["pages"]}
    for finding in packet["findings"]:
        known_evidence.update(finding["evidence_ids"])
    if parsed.url not in known_pages and parsed.url not in {url for finding in packet["findings"] for url in finding["urls"]}:
        builder.rejected.append(RejectedFinding(
            rule_id=agent.agent_id,
            title=agent.agent_id,
            reason="The judgment cited a URL that was not in the evidence packet.",
        ))
        return None
    if any(item not in known_evidence for item in parsed.evidence_ids):
        builder.rejected.append(RejectedFinding(
            rule_id=agent.agent_id,
            title=agent.agent_id,
            reason="The judgment cited an evidence id that was not in the evidence packet.",
        ))
        return None
    page = known_pages.get(parsed.url)
    if page is not None:
        _store_page_evidence(builder, page)
    for evidence_id in parsed.evidence_ids:
        if evidence_id not in builder.evidence:
            builder.rejected.append(RejectedFinding(
                rule_id=agent.agent_id,
                title=agent.agent_id,
                reason="The judgment cited evidence that is not stored on this audit.",
            ))
            return None
    digest = hashlib.sha256(
        f"{builder.audit_id}|{agent.agent_id}|{parsed.url}|{parsed.observation}".encode("utf-8")
    ).hexdigest()
    chapter = agent.chapters[0]
    subchapters = [CHAPTER_BY_NUMBER[chapter].subchapters[0].subchapter_id]
    finding = EnterpriseFinding(
        finding_id=f"f_{digest[:12]}",
        audit_run_id=builder.audit_id,
        rule_id=agent.agent_id,
        rule_version=agent.version,
        rule_class="heuristic",
        title=parsed.observation[:140],
        category="seo_ai",
        chapter=chapter,
        subchapters=subchapters,
        severity=parsed.severity,
        issue_type="diagnostic",
        status="open",
        scope="PAGE_VERIFIED",
        affected_urls=[parsed.url],
        affected_count=1,
        eligible_count=len(packet["pages"]) or None,
        evidence_ids=list(parsed.evidence_ids),
        observed_condition=parsed.observation,
        expected_condition="The supplied evidence would need to support the judgment before it could be treated as verified.",
        simple_explanation=parsed.explanation,
        seo_significance=parsed.why_it_matters,
        root_cause_hypothesis=(
            parsed.observation if parsed.claim_kind == "hypothesis"
            else "This is a judgment about the supplied evidence. It is not a confirmed cause."
        ),
        cause_label="plausible" if parsed.claim_kind == "hypothesis" else "unknown",
        remediation_steps=list(parsed.investigation),
        code_examples=[],
        code_is_illustrative=True,
        acceptance_tests=list(parsed.verification_criteria),
        regression_risk="No patch was generated. A later change can still affect pages outside this sample.",
        confidence=parsed.confidence,
        limitations=[
            "This is an analytical judgment, not a measured defect.",
            "The listed URL is the supplied page. It is not a sitewide certificate.",
            *parsed.limitations,
        ],
        verification_status="NOT_VERIFIABLE",
        observed_at=str(builder.generated_at) if builder.generated_at else None,
        evaluation_state="INFERRED",
        claim_kind=parsed.claim_kind,  # type: ignore[arg-type]
        business_impact=parsed.why_it_matters,
        investigation_targets=list(parsed.investigation),
        severity_rationale="Severity is the model's judgment label. It is not a traffic estimate.",
        confidence_rationale=parsed.confidence_rationale,
    )
    builder.proposed.append(finding)
    builder.mark(subchapters[0], "INFERRED", parsed.observation[:240])
    return finding


def _run_one(builder: Any, agent: Any, runner: Runner, packet: dict[str, Any]) -> SEOAgentResult:
    requires = AI_REQUIRES[agent.agent_id]
    try:
        system, version, digest = render_system_prompt(agent.agent_id)
    except PromptError as exc:
        return _result(agent.agent_id, agent.version, None, "failed", str(exc), [str(exc)], "PROMPT_MISSING")
    if digest != agent.prompt_sha256 or version != agent.prompt_version:
        return _result(
            agent.agent_id,
            version,
            digest,
            "failed",
            "The prompt file changed after the catalog was loaded. The agent did not run.",
            ["Prompt drift fails closed."],
            "PROMPT_DRIFT",
        )
    blocked = _gate(requires, packet)
    if blocked:
        code, note = blocked
        return _result(agent.agent_id, version, digest, "unavailable", note, [note], code)
    user = json.dumps(packet, default=str, sort_keys=True)
    try:
        payload, error, _calls = _invoke(runner, system, user, agent.timeout_seconds, agent.max_retries)
    except ModelNotRun:
        return _result(
            agent.agent_id,
            version,
            digest,
            "unavailable",
            "The versioned prompt was loaded. No model completion ran, so no judgment was published.",
            ["An unavailable model is not an analysis."],
            "MODEL_NOT_RUN",
        )
    if error or payload is None:
        return _result(
            agent.agent_id,
            version,
            digest,
            "unavailable",
            "The model did not return a usable completion.",
            ["The failure was not filled with an invented judgment."],
            error or "MODEL_FAILED",
        )
    if not isinstance(payload, dict):
        return _result(agent.agent_id, version, digest, "failed", "The model returned a value that is not an object.", [], "SCHEMA_REJECTED")
    if payload.get("agent_id") != agent.agent_id or payload.get("version") != version:
        return _result(
            agent.agent_id,
            version,
            digest,
            "failed",
            "The model returned a different agent id or prompt version.",
            ["The output was discarded."],
            "SCHEMA_REJECTED",
        )
    findings = payload.get("findings")
    if findings is None:
        findings = []
    if not isinstance(findings, list):
        return _result(agent.agent_id, version, digest, "failed", "Findings were not a list.", [], "SCHEMA_REJECTED")
    accepted = []
    for draft in findings:
        if not isinstance(draft, dict):
            builder.rejected.append(RejectedFinding(rule_id=agent.agent_id, title=agent.agent_id, reason="A finding was not an object."))
            continue
        # Reject undeclared patch fields before the schema fills defaults.
        if any(key in draft for key in ("code", "code_examples", "replacement_copy", "patch")):
            builder.rejected.append(RejectedFinding(
                rule_id=agent.agent_id,
                title=agent.agent_id,
                reason="The judgment included replacement copy or a patch. It was discarded.",
            ))
            continue
        finding = _accept(builder, agent, draft, packet)
        if finding is not None:
            accepted.append(finding)
    if findings and not accepted:
        return _result(
            agent.agent_id,
            version,
            digest,
            "partial",
            "The model returned findings, and none of them were grounded in the packet.",
            ["Ungrounded judgments were not published."],
            "EVIDENCE_REJECTED",
        )
    note = (
        f"{len(accepted)} grounded judgment(s)."
        if accepted
        else "The model returned no finding. That is not a pass and not a sitewide certificate."
    )
    return _result(
        agent.agent_id,
        version,
        digest,
        "partial" if payload.get("status") == "partial" else "completed",
        note,
        ["A completed AI specialist with no finding is not a sitewide pass."] if not accepted else [],
        None,
        [finding.finding_id for finding in accepted],
        sorted({evidence_id for finding in accepted for evidence_id in finding.evidence_ids}),
    )


def run_ai_phase(builder: Any, *, phase: str, findings: list[EnterpriseFinding] | None = None, runner: Runner | None = None) -> dict[str, SEOAgentResult]:
    """Run analysis agents before adjudication, or review agents after it."""
    selected = [
        agent for agent in AI_AGENTS
        if (AI_REQUIRES[agent.agent_id] == "findings") == (phase == "review")
    ]
    packet = _packet(builder, findings if phase == "review" else None)
    if phase != "review":
        packet["findings"] = []
    active = runner or default_ai_runner
    return {agent.agent_id: _run_one(builder, agent, active, packet) for agent in selected}

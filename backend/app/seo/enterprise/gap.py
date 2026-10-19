"""Gap matrix for the SEO-only specialist expansion.

Reused rows are existing agents. They are not second copies with a new id.
Deferred rows are out of this phase even if a gated agent already exists.
"""

from __future__ import annotations

from app.seo.enterprise.agents import AGENT_BY_ID, AGENT_CATALOG
from app.seo.enterprise.ai_catalog import AI_AGENTS

# Proposed id -> existing agent that already owns the responsibility.
REUSED: dict[str, str] = {
    "seo.ai.query_page_mapping.v1": "seo.keyword_mapping.v1",
    "seo.ai.evidence_critic.v1": "seo.evidence_adjudicator.v1",
    "seo.ai.scope_auditor.v1": "seo.evidence_adjudicator.v1",
    "seo.ai.template_root_cause.v1": "seo.root_cause.v1",
    "seo.ai.impact_interpreter.v1": "seo.roadmap.v1",
    "seo.ai.priority_reasoner.v1": "seo.roadmap.v1",
    "seo.ai.chapter_synthesizer.v1": "seo.report_editor.v1",
    "seo.ai.executive_analyst.v1": "seo.report_editor.v1",
}

DEFERRED_MODULES: tuple[str, ...] = (
    "GEO intelligence",
    "AEO intelligence",
    "CRO intelligence",
    "Competitor benchmarking execution",
    "Content writing",
    "Code remediation",
    "Implementation planning and deployment",
)

DEFERRED_WORK: tuple[str, ...] = (
    "Do not execute GEO, AEO, or CRO inside the SEO assessment.",
    "Do not turn the gated competitor agent into a benchmark that invents rivals.",
    "Do not add content-writing agents or replacement copy.",
    "Do not add code-fixing agents, patches, pull requests, or deployment.",
    "Do not add an implementation-planning agent in this phase.",
    "A combined report must not invent those chapters from the SEO template.",
)


def inventory() -> list[dict[str, str]]:
    rows = []
    for agent in AGENT_CATALOG:
        rows.append({
            "agent_id": agent.agent_id,
            "version": agent.version,
            "execution_mode": agent.execution_mode,
            "prompt_source": agent.prompt_source,
            "group": agent.group,
            "chapters": ",".join(str(number) for number in agent.chapters),
        })
    return rows


def gap_matrix() -> dict[str, list[str]]:
    implemented = [agent.agent_id for agent in AI_AGENTS]
    reused = [f"{proposed} -> {existing}" for proposed, existing in sorted(REUSED.items())]
    missing = [
        proposed for proposed, existing in REUSED.items()
        if existing not in AGENT_BY_ID or proposed in AGENT_BY_ID
    ]
    return {
        "implemented_ai": implemented,
        "reused": reused,
        "missing_or_duplicated": missing,
        "deferred": list(DEFERRED_MODULES),
    }

"""Build AI specialist contracts from the versioned prompt files.

A contract is not permission to invent a judgment. The runtime loads the
same file again before it asks a model to run.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.seo.enterprise.contracts import ModelPolicy, SEOAgentContract
from app.seo.enterprise.policy import SHARED_POLICY_VERSION
from app.seo.enterprise.prompt_store import PROMPTS_DIR, load_prompt_file

_INPUT = "seo.ai.input.v1"
_OUTPUT = "seo.ai.output.v1"
_MODEL = ModelPolicy(on_unavailable="unavailable")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _ints(value: str) -> list[int]:
    return [int(item) for item in _csv(value)]


@dataclass(frozen=True)
class AISpec:
    agent: SEOAgentContract
    requires: str


def load_ai_specs() -> tuple[AISpec, ...]:
    paths = sorted(PROMPTS_DIR.glob("seo.ai.*.md"))
    if not paths:
        raise RuntimeError(f"No SEO AI prompts were found in {PROMPTS_DIR}")
    specs: list[AISpec] = []
    seen: set[str] = set()
    for path in paths:
        agent_id = path.name[: -len(".md")]
        meta, body, digest = load_prompt_file(agent_id)
        if agent_id in seen:
            raise RuntimeError(f"Duplicate AI prompt: {agent_id}")
        seen.add(agent_id)
        requires = meta.get("requires") or ""
        if requires not in {"text", "text+queries", "queries", "audience", "links", "history", "findings"}:
            raise RuntimeError(f"{agent_id} has an unknown evidence gate: {requires}")
        specs.append(AISpec(
            requires=requires,
            agent=SEOAgentContract(
                agent_id=agent_id,
                version=meta["version"],
                purpose=meta["purpose"],
                group=meta["group"],  # type: ignore[arg-type]
                chapters=_ints(meta["chapters"]),
                input_schema_version=_INPUT,
                output_schema_version=_OUTPUT,
                data_permissions=_csv(meta["permissions"]),
                evidence_requirements=_csv(meta["evidence"]),
                policy_requirements=[SHARED_POLICY_VERSION],
                timeout_seconds=int(meta.get("timeout_seconds") or "60"),
                max_retries=1,
                failure_mode="unavailable",
                execution_mode="interpretive",
                dependencies=_csv(meta.get("dependencies") or ""),
                dedicated_prompt=body,
                prompt_source="versioned_file",
                prompt_version=meta["version"],
                prompt_sha256=digest,
                model_policy=_MODEL,
            ),
        ))
    return tuple(specs)


AI_SPECS: tuple[AISpec, ...] = load_ai_specs()
AI_AGENTS: tuple[SEOAgentContract, ...] = tuple(spec.agent for spec in AI_SPECS)
AI_REQUIRES: dict[str, str] = {spec.agent.agent_id: spec.requires for spec in AI_SPECS}
ROADMAP_REVIEW_DEPENDENCIES: tuple[str, ...] = ("seo.ai.confidence_reviewer.v1",)

"""Load versioned SEO AI system prompts from disk.

The catalog hash is not the execution path. Callers that run an agent
must read the file again and pass that text as the system prompt.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.seo.enterprise.policy import SHARED_POLICY, SHARED_POLICY_VERSION

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class PromptError(ValueError):
    pass


def _split_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise PromptError("Prompt file is missing front matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise PromptError("Prompt front matter is not closed")
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise PromptError(f"Prompt front matter line is not a key: {line}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    body = text[end + 5 :].strip()
    if not body:
        raise PromptError("Prompt body is empty")
    return meta, body


def prompt_path(agent_id: str) -> Path:
    return PROMPTS_DIR / f"{agent_id}.md"


def load_prompt_file(agent_id: str) -> tuple[dict[str, str], str, str]:
    """Return front matter, body, and the sha256 of the body bytes."""
    path = prompt_path(agent_id)
    if not path.is_file():
        raise PromptError(f"No versioned prompt file for {agent_id}")
    meta, body = _split_front_matter(path.read_text(encoding="utf-8"))
    if meta.get("agent_id") != agent_id:
        raise PromptError(f"{path.name} declares {meta.get('agent_id')} instead of {agent_id}")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return meta, body, digest


def render_system_prompt(agent_id: str) -> tuple[str, str, str]:
    """Return system text, prompt version, and body hash.

    The shared evidence policy is appended at execution time. It is not a
    substitute for the dedicated prompt.
    """
    meta, body, digest = load_prompt_file(agent_id)
    version = meta.get("version") or ""
    if not version:
        raise PromptError(f"{agent_id} has no prompt version")
    system = (
        f"{body}\n\n"
        f"## Shared Policy\n"
        f"Policy version: {SHARED_POLICY_VERSION}\n\n"
        f"{SHARED_POLICY}"
    )
    return system, version, digest

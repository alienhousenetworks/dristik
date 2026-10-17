"""Change-management rules for remediation.

Auto-approval of a low-risk patch is not permission to deploy it to a
customer's production site. Factual schema, pricing, and review markup
require a person. A patch never receives a hardcoded citation-score gain.
"""
from __future__ import annotations

from typing import Any


_CONSEQUENTIAL_MARKERS = (
    "aggregaterating",
    "price",
    "offers",
    "review",
    "hallucination",
    "faqpage",
)


def patch_text(patch: Any) -> str:
    parts = [
        getattr(patch, "title", ""),
        getattr(patch, "explanation", ""),
        getattr(patch, "after_snippet", ""),
        getattr(patch, "operation", ""),
    ]
    metadata = getattr(patch, "metadata_payload", None) or {}
    if isinstance(metadata, dict):
        parts.append(str(metadata.get("reason") or ""))
        if metadata.get("asserts_facts"):
            parts.append("asserts_facts")
    return " ".join(str(part) for part in parts).lower()


def patch_requires_human_approval(patch: Any) -> bool:
    risk = str(getattr(getattr(patch, "risk_level", ""), "value", getattr(patch, "risk_level", "")))
    if risk in {"HUMAN_APPROVAL", "DEVELOPER_REQUIRED"}:
        return True
    text = patch_text(patch)
    operation = str(getattr(getattr(patch, "operation", ""), "value", getattr(patch, "operation", ""))).upper()
    if operation == "UPDATE_JSONLD" and any(marker in text for marker in _CONSEQUENTIAL_MARKERS):
        return True
    if "asserts_facts" in text or "hallucination" in text:
        return True
    return False


def deployment_decision(patch: Any, *, explicit_production_authorization: bool = False) -> dict[str, Any]:
    human = patch_requires_human_approval(patch)
    return {
        "human_approval_required": human,
        "policy_authorized_low_risk": not human,
        "production_deploy_allowed": bool(explicit_production_authorization),
        "unattended_agent_deploy_allowed": False,
        "citation_score_delta": None,
        "rule": (
            "A higher audit score is not proof that AI citations increased. "
            "A successful deployment is not proof that traffic or revenue improved. "
            "No patch is assigned a fixed citation-point gain."
        ),
    }

"""
Dristik AI 70B-Hardened Prompt Compiler
Implements standardized prompt envelopes, deterministic token budgets,
semantic evidence prioritization, and zero-hallucination guardrails.
"""
import os
import json
from typing import List, Dict, Any, Optional
from app.evidence.models import Evidence
from app.inference.global_policy import GLOBAL_POLICY

GLOBAL_SYSTEM_POLICY = GLOBAL_POLICY  # backward compatibility

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

def load_prompt(prompt_name: str) -> str:
    """Loads a prompt template from the prompts directory."""
    if not prompt_name.endswith(".txt"):
        prompt_name = f"{prompt_name}.txt"
    path = os.path.join(_PROMPTS_DIR, prompt_name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


class PromptCompiler:
    def __init__(self):
        self.global_policy = GLOBAL_POLICY

    def format_evidence_slice(self, ev: Evidence) -> str:
        """Formats an evidence slice into a concise, deterministic line."""
        url_part = f" url={ev.url}" if ev.url else ""
        kind_part = f" kind={ev.source_type or 'dom'}"
        sel_part = f" sel={ev.selector}" if ev.selector else ""
        text_clean = (ev.text or "").strip().replace("\n", " ")
        if len(text_clean) > 200:
            text_clean = text_clean[:197] + "..."
        val_part = f" val={str(ev.value)[:100]}" if ev.value is not None else ""
        return f"[{ev.id}]{url_part}{kind_part}{sel_part} text=\"{text_clean}\"{val_part}"

    def build_evidence_pack(
        self,
        evidence_list: List[Evidence],
        max_tokens: int = 4000,
        allowed_kinds: Optional[List[str]] = None
    ) -> str:
        """
        Prioritizes hero, title, meta, and navigation evidence before general content,
        respecting a hard token budget (~4 chars per token).
        """
        if not evidence_list:
            return "No direct DOM evidence slices provided."

        # Filter by allowed kinds if specified
        if allowed_kinds:
            allowed_kinds_lower = [k.lower() for k in allowed_kinds]
            filtered = [
                ev for ev in evidence_list
                if any(k in (ev.source_type or "").lower() or (ev.selector and k in ev.selector.lower())
                       for k in allowed_kinds_lower)
            ]
            if filtered:
                evidence_list = filtered

        # Sort priority: meta/title/hero first, cta/nav second, schema third, general fourth
        def priority_key(ev: Evidence) -> int:
            st = (ev.source_type or "").lower()
            sel = (ev.selector or "").lower()
            if st == "external" or (ev.id or "").startswith("ext_"):
                return -1
            if any(k in st or k in sel for k in ["title", "meta", "h1", "hero", "brand", "identity"]):
                return 0
            if any(k in st or k in sel for k in ["cta", "button", "nav", "pricing"]):
                return 1
            if any(k in st or k in sel for k in ["schema", "jsonld", "faq"]):
                return 2
            return 3

        sorted_ev = sorted(evidence_list, key=priority_key)

        char_budget = max_tokens * 4
        lines = []
        current_chars = 0

        for ev in sorted_ev:
            line = self.format_evidence_slice(ev)
            line_len = len(line) + 1
            if current_chars + line_len > char_budget:
                break
            lines.append(line)
            current_chars += line_len

        return "\n".join(lines)

    def compile(
        self,
        agent_role: str,
        task_contract: str,
        evidence_list: List[Evidence],
        rubric: str = "",
        output_schema_desc: str = "",
        additional_context: Optional[str] = None,
        site_facts: Optional[Dict[str, Any]] = None,
        task_card: Optional[str] = None,
        max_claims: int = 8,
        evidence_kind_allowlist: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Compiles the strict 70B envelope:
        system = GLOBAL_POLICY + "\n\n" + TASK_CARD
        user =
          <task>...</task>
          <site_facts>{wave0_json}</site_facts>
          <evidence>...</evidence>
          <constraints>...</constraints>
        """
        # Determine Task Card (≤ 250 tokens)
        if not task_card:
            # Use task_contract or role if no explicit card
            card_text = task_contract.strip() if len(task_contract) < 800 else task_contract[:797] + "..."
            task_card = f"TASK CARD: {agent_role}\n{card_text}"
        else:
            task_card = task_card.strip()

        system_prompt = f"{self.global_policy}\n\n{task_card}"

        # Site facts JSON
        if site_facts is not None:
            site_facts_json = json.dumps(site_facts, ensure_ascii=False, indent=2)
        elif additional_context and additional_context.strip().startswith("{") and additional_context.strip().endswith("}"):
            site_facts_json = additional_context.strip()
        else:
            facts_payload = {"raw_context": additional_context or "None"}
            site_facts_json = json.dumps(facts_payload, ensure_ascii=False)

        # Evidence Pack
        evidence_block = self.build_evidence_pack(
            evidence_list,
            max_tokens=3000,
            allowed_kinds=evidence_kind_allowlist
        )

        user_prompt_sections = [
            f"<task>\n{task_contract.strip()}\n{('Output requirements: ' + output_schema_desc) if output_schema_desc else ''}\n</task>",
            f"<site_facts>\n{site_facts_json}\n</site_facts>",
            f"<evidence>\n{evidence_block}\n</evidence>",
            f"<constraints>\nmax_claims: {max_claims}\nallowed_severities: LOW|MEDIUM|HIGH|CRITICAL\nunknown_policy: null\n</constraints>"
        ]

        return {
            "system": system_prompt,
            "user": "\n\n".join(user_prompt_sections)
        }

"""
Dristik AI JSON Auto-Repair Utility
Sanitizes markdown fences, trailing commas, truncated objects, and unescaped quotes from SLM outputs.
"""
import json
import re
from typing import Any, Optional, Dict


def repair_and_parse_json(raw_text: str) -> Optional[Dict[str, Any]]:
    if not raw_text or not raw_text.strip():
        return None

    text = raw_text.strip()

    # Strip markdown code blocks ```json ... ```
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()

    parsed = _try_object(text)
    if parsed is not None:
        return parsed

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        parsed = _try_object(candidate)
        if parsed is not None:
            return parsed
        fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
        parsed = _try_object(fixed)
        if parsed is not None:
            return parsed

    # Truncated generation: start at first { and close open braces/strings.
    if first_brace != -1:
        truncated = _close_truncated_json(text[first_brace:])
        if truncated:
            parsed = _try_object(truncated)
            if parsed is not None:
                return parsed

    return None


def _try_object(text: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(text)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _close_truncated_json(candidate: str) -> Optional[str]:
    """Best-effort close of a JSON object cut off at max_tokens."""
    in_str = False
    escape = False
    stack: list[str] = []
    out: list[str] = []
    for ch in candidate:
        out.append(ch)
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack and stack[-1] == ch:
                stack.pop()
            else:
                return None
    if in_str:
        if escape:
            out.append(" ")
        out.append('"')
    closed = "".join(out).rstrip()
    closed = re.sub(r",\s*$", "", closed)
    if not stack:
        return closed
    closed += "".join(reversed(stack))
    return closed

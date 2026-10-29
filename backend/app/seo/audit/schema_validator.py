"""
Schema Validation & Deprecation Enforcement Engine for Dristik SEO.
Adapted from Claude SEO's schema validation system with zero-fake integrity rules.

Validates JSON-LD schema objects and raw markup, detects deprecated/retired Schema.org types,
catches unreplaced placeholder tokens, and verifies @context / @type conformance.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

BRACKET_PLACEHOLDERS = (
    "[Business Name]",
    "[City]",
    "[State]",
    "[Phone]",
    "[Address]",
    "[Your",
    "[INSERT",
    "[URL]",
    "[Email]",
)
BARE_PLACEHOLDER_RE = re.compile(r"\bREPLACE(?:_[A-Z]+)*\b")

DEPRECATED_SCHEMA_TYPES: Dict[str, str] = {
    "HowTo": "deprecated September 2023",
    "SpecialAnnouncement": "deprecated July 31, 2025",
    "CourseInfo": "retired June 2025",
    "EstimatedSalary": "retired June 2025",
    "LearningVideo": "retired June 2025",
    "ClaimReview": "retired June 2025; fact-check rich results discontinued",
    "VehicleListing": "retired June 2025; vehicle listing structured data discontinued",
}

SCHEMA_ORG_CONTEXTS: Set[str] = {
    "https://schema.org",
    "http://schema.org",
    "https://schema.org/",
    "http://schema.org/",
}

_ATTRS_RE = r'(?:"[^"]*"|\'[^\']*\'|[^"\'>])*'
SCRIPT_TAG_RE = re.compile(
    r"<script\b(" + _ATTRS_RE + r")>(.*?)</script\s*>", re.DOTALL | re.IGNORECASE
)
LD_JSON_TYPE_RE = re.compile(
    r"""(?:^|\s)type\s*=\s*(?:"application/ld\+json"|'application/ld\+json'|application/ld\+json(?=\s|$))""",
    re.IGNORECASE,
)

SERVER_TEMPLATE_RE = re.compile(
    r"""^(?:<\?(?:php\b|=)|<%)""", re.VERBOSE
)
COMPONENT_EXPRESSION_RE = re.compile(
    r"""^(?:\{\{|\{@html\b|\$\{|\{\s*[A-Za-z_$][\w$.]*)""", re.VERBOSE
)
COMPONENT_EXTENSIONS = (".jsx", ".tsx", ".vue", ".svelte")


def _is_schema_org_context(value: Any) -> bool:
    if isinstance(value, str):
        return value in SCHEMA_ORG_CONTEXTS
    if isinstance(value, list):
        return any(_is_schema_org_context(item) for item in value)
    if isinstance(value, dict):
        return _is_schema_org_context(value.get("@vocab"))
    return False


def _is_template_expression(block: str, filepath: str = "") -> bool:
    if SERVER_TEMPLATE_RE.match(block):
        return True
    if filepath.lower().endswith(COMPONENT_EXTENSIONS):
        return bool(COMPONENT_EXPRESSION_RE.match(block))
    return False


def validate_schema_object(
    obj: Dict[str, Any], block_num: int = 1, *, inherited_context: bool = False
) -> List[str]:
    """Validate one schema dictionary object, including members of a top-level @graph."""
    errors: List[str] = []
    prefix = f"Block {block_num}"

    # 1. Check @context
    if "@context" not in obj and not inherited_context:
        errors.append(f"{prefix}: Missing @context")
    elif "@context" in obj and not _is_schema_org_context(obj["@context"]):
        errors.append(f"{prefix}: @context should be 'https://schema.org'")

    graph = obj.get("@graph")
    has_graph = isinstance(graph, list)

    # 2. Check @type
    if "@type" not in obj and not has_graph:
        errors.append(f"{prefix}: Missing @type")

    # 3. Check for placeholder text
    placeholder_scope = {k: v for k, v in obj.items() if k != "@graph"}
    text = json.dumps(placeholder_scope, ensure_ascii=False)
    for p in BRACKET_PLACEHOLDERS:
        if p.lower() in text.lower():
            errors.append(f"{prefix}: Contains placeholder text: {p}")
    for placeholder in BARE_PLACEHOLDER_RE.findall(text):
        errors.append(f"{prefix}: Contains placeholder text: {placeholder}")

    # 4. Check for deprecated types
    schema_type = obj.get("@type", "")
    types_to_check = schema_type if isinstance(schema_type, list) else [schema_type]
    for st in types_to_check:
        if isinstance(st, str):
            clean_type = st.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
            if clean_type in DEPRECATED_SCHEMA_TYPES:
                errors.append(f"{prefix}: @type '{clean_type}' is {DEPRECATED_SCHEMA_TYPES[clean_type]}")

    # 5. Graph recursions
    if "@graph" in obj:
        if not isinstance(graph, list):
            errors.append(f"{prefix}: @graph must be a list")
        else:
            context_is_inherited = inherited_context or "@context" in obj
            for index, item in enumerate(graph, 1):
                if not isinstance(item, dict):
                    errors.append(f"{prefix}: @graph member {index} must be an object")
                    continue
                errors.extend(
                    validate_schema_object(
                        item,
                        block_num,
                        inherited_context=context_is_inherited,
                    )
                )

    return errors


def validate_jsonld(content: str, filepath: str = "") -> List[str]:
    """Extract and validate all JSON-LD blocks within raw HTML or standalone JSON."""
    errors: List[str] = []
    content_stripped = content.strip()

    # If already raw JSON object/list
    if content_stripped.startswith("{") or content_stripped.startswith("["):
        try:
            data = json.loads(content_stripped)
            if isinstance(data, list):
                for i, item in enumerate(data, 1):
                    if isinstance(item, dict):
                        errors.extend(validate_schema_object(item, i))
                    else:
                        errors.append(f"Block {i}: JSON-LD list members must be objects")
            elif isinstance(data, dict):
                errors.extend(validate_schema_object(data, 1))
            return errors
        except json.JSONDecodeError:
            pass

    # Extract <script type="application/ld+json"> blocks
    blocks: List[str] = []
    for attributes, body in SCRIPT_TAG_RE.findall(content):
        if LD_JSON_TYPE_RE.search(attributes):
            blocks.append(body)

    if not blocks:
        return []

    for i, block in enumerate(blocks, 1):
        block = block.strip()
        if _is_template_expression(block, filepath):
            continue
        try:
            data = json.loads(block)
        except json.JSONDecodeError as e:
            errors.append(f"Block {i}: Invalid JSON; {e}")
            continue

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    errors.extend(validate_schema_object(item, i))
                else:
                    errors.append(f"Block {i}: JSON-LD list members must be objects")
        elif isinstance(data, dict):
            errors.extend(validate_schema_object(data, i))
        else:
            errors.append(f"Block {i}: JSON-LD root must be an object or list")

    return errors


def get_reference_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "reference_data"


def load_schema_templates() -> Dict[str, Any]:
    """Load JSON-LD schema templates from reference data."""
    ref_file = get_reference_dir() / "templates.json"
    if ref_file.exists():
        with open(ref_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_google_updates() -> List[Dict[str, Any]]:
    """Load Google algorithm updates ledger from reference data."""
    ref_file = get_reference_dir() / "google-updates.json"
    if ref_file.exists():
        with open(ref_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("updates", [])
            elif isinstance(data, list):
                return data
    return []

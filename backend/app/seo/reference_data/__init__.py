"""
Dristik SEO Reference Data & Knowledge Repository.
Consolidates algorithm updates, schema templates, and 110+ specialized domain references.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

REF_DIR = Path(__file__).resolve().parent


def get_google_updates() -> List[Dict[str, Any]]:
    """Return the parsed Google algorithm updates ledger."""
    p = REF_DIR / "google-updates.json"
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data.get("updates", [])
            elif isinstance(data, list):
                return data
            return []
        except Exception:
            return []
    return []


def get_schema_templates() -> Dict[str, Any]:
    """Return the Schema.org JSON-LD templates dictionary."""
    p = REF_DIR / "templates.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def get_reference_document(filename: str) -> Optional[str]:
    """Load the contents of any reference markdown document by name."""
    if not filename.endswith(".md"):
        filename += ".md"
    p = REF_DIR / filename
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def list_references() -> List[str]:
    """List all reference documents in the repository."""
    return sorted([f.name for f in REF_DIR.glob("*.md")])

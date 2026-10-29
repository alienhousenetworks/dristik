"""
Dristik SEO Skills Registry.
Provides programmatic discovery and loading for all 26 SEO skills ported from Claude SEO.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

SKILLS_DIR = Path(__file__).resolve().parent


def list_skills() -> List[str]:
    """Return all available skill directory names."""
    if not SKILLS_DIR.exists():
        return []
    return sorted([
        d.name for d in SKILLS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("__")
    ])


def get_skill_manifest(skill_name: str) -> Optional[str]:
    """Read the SKILL.md file for a skill."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return None


def get_skill_references(skill_name: str) -> Dict[str, str]:
    """Return dictionary of {filename: content} for all references in a skill."""
    refs_dir = SKILLS_DIR / skill_name / "references"
    if not refs_dir.exists() or not refs_dir.is_dir():
        return {}
    res = {}
    for f in refs_dir.glob("*.md"):
        res[f.name] = f.read_text(encoding="utf-8")
    return res


def get_all_skills_summary() -> Dict[str, Dict[str, Any]]:
    """Return high-level summary of all available skills."""
    summary = {}
    for s in list_skills():
        manifest = get_skill_manifest(s)
        has_refs = (SKILLS_DIR / s / "references").is_dir()
        refs_count = len(list((SKILLS_DIR / s / "references").glob("*.md"))) if has_refs else 0
        summary[s] = {
            "has_manifest": manifest is not None,
            "manifest_length": len(manifest) if manifest else 0,
            "references_count": refs_count,
        }
    return summary

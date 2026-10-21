"""
Dristik SEO Specialist Prompts Repository.
Maintains and provides access to all 19 specialist agent prompts ported from Claude SEO.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

PROMPTS_DIR = Path(__file__).resolve().parent

PROMPT_MAP = {
    "seo.technical.v3": "seo-technical.md",
    "seo.crawl.v3": "seo-technical.md",
    "seo.indexability.v3": "seo-technical.md",
    "seo.html.v3": "seo-technical.md",
    "seo.content.v3": "seo-content.md",
    "content.eeat.v3": "seo-content.md",
    "content.quality.v3": "seo-content.md",
    "content.depth.v3": "seo-content.md",
    "schema.validation.v3": "seo-schema.md",
    "seo.performance.v3": "seo-performance.md",
    "geo.extractability.v3": "seo-geo.md",
    "geo.citation_readiness.v3": "seo-geo.md",
    "seo.agentic_readiness.v3": "seo-agentic.md",
    "seo.drift.v3": "seo-drift.md",
    "seo.ecommerce.v3": "seo-ecommerce.md",
    "seo.sxo.v3": "seo-sxo.md",
    "seo.cluster.v3": "seo-cluster.md",
    "seo.maps_intelligence.v3": "seo-maps.md",
    "seo.backlinks.v3": "seo-backlinks.md",
    "seo.local.v3": "seo-local.md",
    "seo.sitemap.v3": "seo-sitemap.md",
    "seo.visual.v3": "seo-visual.md",
    "seo.google.v3": "seo-google.md",
    "seo.flow.v3": "seo-flow.md",
    "seo.dataforseo.v3": "seo-dataforseo.md",
    "seo.image_gen.v3": "seo-image-gen.md",
}


def list_prompts() -> List[str]:
    """Return all markdown prompt identifiers and filenames in the directory."""
    if not PROMPTS_DIR.exists():
        return []
    names = {f.name for f in PROMPTS_DIR.glob("*.md")}
    stems = {f.stem for f in PROMPTS_DIR.glob("*.md")}
    return sorted(list(names | stems))


def get_prompt_text(filename_or_id: str) -> str:
    """Load the full markdown prompt for an agent ID or filename."""
    fname = PROMPT_MAP.get(filename_or_id, filename_or_id)
    if not fname.endswith(".md"):
        fname += ".md"
    fpath = PROMPTS_DIR / fname
    if not fpath.exists():
        # Fallback to direct name search
        fpath = PROMPTS_DIR / f"{filename_or_id}.md"
    if fpath.exists():
        return fpath.read_text(encoding="utf-8")
    return ""


def get_all_prompts() -> Dict[str, str]:
    """Return dictionary of {filename: content} for all prompts."""
    res = {}
    for f in PROMPTS_DIR.glob("*.md"):
        res[f.stem] = f.read_text(encoding="utf-8")
    return res

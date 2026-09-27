"""
Dristik AI Meta Analyzer
Extracts title, meta description, OpenGraph, Twitter cards, viewport, canonical, and robots directives.
"""
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from app.evidence.store import EvidenceStore

def analyze_meta_tags(
    soup: BeautifulSoup,
    url: str,
    evidence_store: EvidenceStore,
    resp_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None
    
    meta_desc_tag = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "description"})
    meta_description = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None
    
    canonical_tag = soup.find("link", attrs={"rel": lambda x: x and "canonical" in [r.lower() for r in (x if isinstance(x, list) else [x])]})
    canonical_url = canonical_tag.get("href", "").strip() if canonical_tag else None
    
    robots_meta_tag = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "robots"})
    robots_meta = robots_meta_tag.get("content", "").strip() if robots_meta_tag else None

    # Inspect X-Robots-Tag in HTTP response headers
    x_robots_tag = None
    if resp_headers:
        for k, v in resp_headers.items():
            if k.lower() == "x-robots-tag" and v:
                x_robots_tag = str(v).strip()
                break

    if x_robots_tag:
        evidence_store.add_evidence(
            source_type="header",
            analyzer="meta_analyzer",
            url=url,
            text=f"HTTP Response Header X-Robots-Tag: {x_robots_tag}",
            value={"x_robots_tag": x_robots_tag},
        )
        if "noindex" in x_robots_tag.lower():
            if not robots_meta:
                robots_meta = x_robots_tag
            elif "noindex" not in robots_meta.lower():
                robots_meta = f"{robots_meta}, {x_robots_tag}"
    
    viewport_tag = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "viewport"})
    viewport = viewport_tag.get("content", "").strip() if viewport_tag else None
    
    # OpenGraph Tags
    og_tags = {}
    for og in soup.find_all("meta", property=lambda x: x and x.startswith("og:")):
        prop = og.get("property")
        content = og.get("content")
        if prop and content:
            og_tags[prop] = content
            
    # Twitter Tags
    twitter_tags = {}
    for tw in soup.find_all("meta", attrs={"name": lambda x: x and x.startswith("twitter:")}):
        name = tw.get("name")
        content = tw.get("content")
        if name and content:
            twitter_tags[name] = content
            
    # Add Evidence
    if title:
        evidence_store.add_evidence(
            source_type="meta",
            analyzer="meta_analyzer",
            url=url,
            selector="title",
            text=title,
            value={"title": title, "length": len(title)}
        )
    else:
        evidence_store.add_evidence(
            source_type="meta",
            analyzer="meta_analyzer",
            url=url,
            selector="title",
            text="Missing Title Tag",
            value={"error": "missing_title"}
        )
        
    if meta_description:
        evidence_store.add_evidence(
            source_type="meta",
            analyzer="meta_analyzer",
            url=url,
            selector="meta[name='description']",
            text=meta_description,
            value={"description": meta_description, "length": len(meta_description)}
        )
    else:
        evidence_store.add_evidence(
            source_type="meta",
            analyzer="meta_analyzer",
            url=url,
            selector="meta[name='description']",
            text="Missing Meta Description",
            value={"error": "missing_meta_description"}
        )
        
    if canonical_url:
        evidence_store.add_evidence(
            source_type="meta",
            analyzer="meta_analyzer",
            url=url,
            selector="link[rel='canonical']",
            text=canonical_url,
            value={"canonical": canonical_url}
        )
        
    if og_tags:
        evidence_store.add_evidence(
            source_type="meta",
            analyzer="meta_analyzer",
            url=url,
            text=f"OpenGraph Tags Count: {len(og_tags)}",
            value=og_tags
        )
        
    return {
        "title": title,
        "meta_description": meta_description,
        "canonical_url": canonical_url,
        "robots_meta": robots_meta,
        "x_robots_tag": x_robots_tag,
        "viewport": viewport,
        "og_tags": og_tags,
        "twitter_tags": twitter_tags
    }

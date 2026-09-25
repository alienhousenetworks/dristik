"""
Dristik AI Link Graph & Architecture Analyzer
Extracts internal and external hyperlinks, detects anchor text distribution, and orphan risks.
"""
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List, Set
from bs4 import BeautifulSoup
from app.evidence.store import EvidenceStore
from app.crawl.analyzers.visible import collect_hrefs, heading_text


def _registrable_host(netloc: str) -> str:
    host = (netloc or "").lower().split(":")[0]
    if host.startswith("www."):
        return host[4:]
    return host


def analyze_link_graph(soup: BeautifulSoup, base_url: str, current_url: str, evidence_store: EvidenceStore) -> Dict[str, Any]:
    base_domain = _registrable_host(urlparse(base_url).netloc)
    
    internal_links: Set[str] = set()
    external_links: Set[str] = set()
    anchor_texts: List[str] = []
    
    hrefs = collect_hrefs(soup)
    # Keep anchor text from <a> tags specifically.
    for a in soup.find_all("a", href=True):
        anchor = heading_text(a)
        if anchor:
            anchor_texts.append(anchor[:50])

    for href in hrefs:
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue
            
        full_url = urljoin(current_url, href)
        parsed_target = urlparse(full_url)
        target_domain = _registrable_host(parsed_target.netloc)
        
        if target_domain == base_domain or not target_domain:
            internal_links.add(full_url)
        else:
            external_links.add(full_url)
            
    int_list = sorted(list(internal_links))
    ext_list = sorted(list(external_links))
    
    evidence_store.add_evidence(
        source_type="link_graph",
        analyzer="link_analyzer",
        url=current_url,
        text=f"Internal Links Count: {len(int_list)}, External Links Count: {len(ext_list)}",
        value={
            "internal_count": len(int_list),
            "external_count": len(ext_list),
            "sample_internal": int_list[:8],
            "sample_external": ext_list[:5],
            "anchor_samples": anchor_texts[:10]
        }
    )
    
    return {
        "internal_links": int_list,
        "external_links": ext_list,
        "internal_count": len(int_list),
        "external_count": len(ext_list),
        "anchor_texts": anchor_texts[:20]
    }

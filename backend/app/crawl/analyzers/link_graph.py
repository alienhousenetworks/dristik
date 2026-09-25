"""
Deterministic Internal Link Graph & Architecture Parser
Analyzes internal links, external links, anchor texts, depth, and orphan page risk.
"""
from typing import Dict, Any, List, Set
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

def build_link_graph(base_url: str, html_content: str, current_page_url: str) -> Dict[str, Any]:
    """
    Extracts all hyperlinks, segregates internal vs external links,
    and analyzes anchor texts.
    """
    base_domain = urlparse(base_url).netloc.lower()
    soup = BeautifulSoup(html_content, "html.parser")

    internal_links: List[str] = []
    external_links: List[str] = []
    anchor_texts: List[Dict[str, str]] = []
    empty_anchor_count = 0

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        # Resolve relative URLs
        full_url = urljoin(current_page_url, href)
        parsed_target = urlparse(full_url)
        target_domain = parsed_target.netloc.lower()

        anchor_text = a.get_text().strip()
        if not anchor_text and not a.find("img"):
            empty_anchor_count += 1

        if target_domain == base_domain or not target_domain:
            clean_internal = f"{parsed_target.scheme}://{base_domain}{parsed_target.path or '/'}"
            if parsed_target.query:
                clean_internal += f"?{parsed_target.query}"
            internal_links.append(clean_internal)
            if anchor_text:
                anchor_texts.append({"target": clean_internal, "text": anchor_text[:60]})
        else:
            external_links.append(full_url)

    unique_internals = sorted(list(set(internal_links)))
    unique_externals = sorted(list(set(external_links)))

    return {
        "total_links_found": len(internal_links) + len(external_links),
        "internal_links_count": len(internal_links),
        "unique_internal_links": unique_internals,
        "external_links_count": len(external_links),
        "unique_external_links": unique_externals,
        "empty_anchor_count": empty_anchor_count,
        "sample_anchors": anchor_texts[:20]
    }

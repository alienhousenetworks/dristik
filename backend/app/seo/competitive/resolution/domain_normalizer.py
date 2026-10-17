"""
Dristik AI Domain Normalizer & Entity Resolution.
Normalizes URLs to canonical domain identities, resolves aliases/subdomains,
and filters invalid or out-of-scope targets.
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse

GLOBAL_TECH_PLATFORMS = {
    "google.com", "youtube.com", "facebook.com", "instagram.com", "twitter.com",
    "x.com", "linkedin.com", "github.com", "apple.com", "microsoft.com",
    "amazon.com", "wikipedia.org", "medium.com", "reddit.com", "cloudflare.com"
}


def normalize_domain(raw_url_or_domain: str) -> str:
    """
    Returns a clean, canonical registrable domain (e.g., 'example.com').
    """
    if not raw_url_or_domain:
        return ""
    d = raw_url_or_domain.strip().lower()
    if not d.startswith(("http://", "https://")):
        d = f"https://{d}"
    try:
        parsed = urlparse(d)
        host = parsed.netloc or parsed.path
        host = host.split(":")[0]  # remove port
        if host.startswith("www."):
            host = host[4:]
        # Remove any lingering path/slashes
        host = host.split("/")[0].strip()
        return host
    except Exception:
        return re.sub(r"^https?://(www\.)?", "", raw_url_or_domain.strip().lower()).split("/")[0]


def extract_brand_from_domain(domain: str) -> str:
    """
    Extracts a clean, human-readable brand name from a domain.
    'tryprofound.com' -> 'Profound'
    'tailscale.com' -> 'Tailscale'
    'alien-house.com' -> 'Alien House'
    """
    clean = normalize_domain(domain)
    root = clean.split(".")[0]
    # Remove common prefixes like get-, try-, use-
    for prefix in ["get-", "try-", "use-", "the-", "get", "try", "use", "the"]:
        if root.startswith(prefix) and len(root) > len(prefix) + 2:
            root = root[len(prefix):]
            break
    # Split by hyphen or underscore
    if "-" in root or "_" in root:
        words = re.split(r"[-_]", root)
        return " ".join(w.capitalize() for w in words if w)

    # Check camelCase
    camel_words = re.findall(r"[A-Z]?[a-z0-9]+", root)
    if len(camel_words) > 1 and any(c.isupper() for c in root):
        return " ".join(w.capitalize() for w in camel_words)

    return root.capitalize()


def is_valid_competitor_domain(
    candidate_domain: str,
    target_domain: str,
    allow_tech_giants: bool = False
) -> bool:
    """
    Validates whether a domain candidate is a legitimate external competitor.
    """
    cand = normalize_domain(candidate_domain)
    target = normalize_domain(target_domain)

    if not cand or "." not in cand or len(cand) < 4:
        return False
    if cand == target:
        return False
    # Reject localhost or internal IPs
    if cand.startswith("localhost") or cand.startswith("127.") or cand.endswith(".local"):
        return False
    # Reject tech utilities unless explicitly permitted
    if not allow_tech_giants and cand in GLOBAL_TECH_PLATFORMS:
        return False
    return True

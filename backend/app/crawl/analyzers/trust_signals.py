"""
Deterministic Trust, Authority, and Security Signals Analyzer
"""
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup

def analyze_trust_signals(
    html_content: str,
    url: str,
    headers: Dict[str, str],
    discovered_urls: List[str]
) -> Dict[str, Any]:
    """
    Detects SSL/HTTPS, security headers, privacy policy, terms of service,
    contact info, social presence, and physical signals.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    is_https = url.lower().startswith("https://")

    # Security headers
    has_hsts = "strict-transport-security" in headers
    has_x_content_type = "x-content-type-options" in headers
    has_csp = "content-security-policy" in headers
    has_x_frame = "x-frame-options" in headers

    # Discover policy & trust pages in discovered URLs
    all_urls_lower = " ".join([u.lower() for u in discovered_urls])
    has_privacy_policy = bool(re.search(r"privacy", all_urls_lower)) or bool(soup.find("a", href=re.compile(r"privacy", re.I)))
    has_terms = bool(re.search(r"terms|tos|conditions", all_urls_lower)) or bool(soup.find("a", href=re.compile(r"terms|tos", re.I)))
    has_about_page = bool(re.search(r"about|company|team", all_urls_lower)) or bool(soup.find("a", href=re.compile(r"about", re.I)))
    has_contact_page = bool(re.search(r"contact|support|help", all_urls_lower)) or bool(soup.find("a", href=re.compile(r"contact", re.I)))

    # Direct contact elements in HTML
    text_content = soup.get_text()
    has_email = bool(re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text_content)) or bool(soup.find("a", href=re.compile(r"^mailto:", re.I)))
    has_phone = bool(re.search(r"\+?[0-9]{1,3}?[-. ]?\(?[0-9]{2,4}\)?[-. ]?[0-9]{3,4}[-. ]?[0-9]{3,4}", text_content)) or bool(soup.find("a", href=re.compile(r"^tel:", re.I)))

    # Social links
    social_profiles = []
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if "twitter.com" in href or "x.com" in href:
            social_profiles.append("X/Twitter")
        elif "linkedin.com" in href:
            social_profiles.append("LinkedIn")
        elif "github.com" in href:
            social_profiles.append("GitHub")
        elif "facebook.com" in href:
            social_profiles.append("Facebook")
        elif "youtube.com" in href:
            social_profiles.append("YouTube")
        elif "instagram.com" in href:
            social_profiles.append("Instagram")

    unique_socials = sorted(list(set(social_profiles)))

    return {
        "is_https": is_https,
        "has_hsts": has_hsts,
        "has_x_content_type": has_x_content_type,
        "has_csp": has_csp,
        "has_x_frame": has_x_frame,
        "has_privacy_policy": has_privacy_policy,
        "has_terms": has_terms,
        "has_about_page": has_about_page,
        "has_contact_page": has_contact_page,
        "has_email_or_mailto": has_email,
        "has_phone_or_tel": has_phone,
        "social_platforms": unique_socials,
        "social_count": len(unique_socials)
    }

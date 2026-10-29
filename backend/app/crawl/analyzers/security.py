"""
Dristik AI Security & Trust Signals Analyzer
Inspects HTTPS, HSTS, Content-Security-Policy, X-Frame-Options, and entity trust indicators.
"""
from typing import Dict, Any
from app.evidence.store import EvidenceStore

def analyze_security_headers(url: str, headers: Dict[str, str], evidence_store: EvidenceStore) -> Dict[str, Any]:
    norm_headers = {k.lower(): v for k, v in headers.items()}
    
    has_hsts = "strict-transport-security" in norm_headers
    hsts_value = norm_headers.get("strict-transport-security", "")
    
    has_csp = "content-security-policy" in norm_headers
    csp_value = norm_headers.get("content-security-policy", "")
    
    has_x_frame = "x-frame-options" in norm_headers
    x_frame_value = norm_headers.get("x-frame-options", "")
    
    has_x_content_type = norm_headers.get("x-content-type-options", "").lower() == "nosniff"
    
    is_https = url.lower().startswith("https://")
    
    # Register deterministic evidence
    evidence_store.add_evidence(
        source_type="security",
        analyzer="security_analyzer",
        url=url,
        text=f"HTTPS: {is_https}, HSTS: {has_hsts}, CSP: {has_csp}, X-Frame-Options: {has_x_frame}",
        value={
            "is_https": is_https,
            "has_hsts": has_hsts,
            "has_csp": has_csp,
            "has_x_frame": has_x_frame,
            "has_x_content_type": has_x_content_type,
            "hsts_value": hsts_value,
            "x_frame_value": x_frame_value
        }
    )
    
    return {
        "is_https": is_https,
        "has_hsts": has_hsts,
        "has_csp": has_csp,
        "has_x_frame": has_x_frame,
        "has_x_content_type": has_x_content_type,
        "hsts_value": hsts_value,
        "csp_value": csp_value[:200] if csp_value else None,
        "x_frame_value": x_frame_value
    }

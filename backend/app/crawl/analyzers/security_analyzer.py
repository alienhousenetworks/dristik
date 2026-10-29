"""
Dristik AI Deterministic Security & HTTP Header Compliance Analyzer
Evaluates enterprise transport security, header posture, and information disclosure:
- Strict-Transport-Security (HSTS) and preload readiness
- Content-Security-Policy (CSP) presence and directive rigor
- Clickjacking protection (X-Frame-Options / frame-ancestors)
- MIME-type sniffing defense (X-Content-Type-Options: nosniff)
- Referrer-Policy and Permissions-Policy
- Information disclosure leakage (Server, X-Powered-By)
"""
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from app.domain.models import SecurityAuditReport


class SecurityAnalyzer:
    @staticmethod
    def analyze_headers(
        url: str,
        response_headers: Optional[Dict[str, str]] = None,
        cookies: Optional[List[Dict[str, Any]]] = None
    ) -> SecurityAuditReport:
        headers = {k.lower(): v for k, v in (response_headers or {}).items()}
        cookies = cookies or []
        domain = urlparse(url).netloc or url

        is_https = url.lower().startswith("https://")
        hsts_header = headers.get("strict-transport-security")
        hsts_enabled = bool(hsts_header)

        csp_header = headers.get("content-security-policy")
        csp_enabled = bool(csp_header)

        xfo_header = headers.get("x-frame-options")
        xcto_header = headers.get("x-content-type-options")
        referrer_policy = headers.get("referrer-policy")
        permissions_policy = headers.get("permissions-policy")

        # Information disclosure leaks
        leaks: List[Dict[str, str]] = []
        if "server" in headers and any(c.isdigit() for c in headers["server"]):
            leaks.append({"header": "Server", "value": headers["server"], "reason": "Discloses server software version"})
        if "x-powered-by" in headers:
            leaks.append({"header": "X-Powered-By", "value": headers["x-powered-by"], "reason": "Discloses application runtime/framework"})
        if "x-aspnet-version" in headers:
            leaks.append({"header": "X-AspNet-Version", "value": headers["x-aspnet-version"], "reason": "Discloses framework version"})

        # Cookie security
        insecure_cookies: List[str] = []
        for c in cookies:
            c_name = c.get("name", "unknown")
            is_secure = c.get("secure", False)
            is_httponly = c.get("httpOnly", False)
            if is_https and not is_secure:
                insecure_cookies.append(f"{c_name}: Missing 'Secure' flag")
            if not is_httponly:
                insecure_cookies.append(f"{c_name}: Missing 'HttpOnly' flag")

        # Scoring
        score = 100.0
        findings: List[str] = []

        if not is_https:
            score -= 40.0
            findings.append("CRITICAL: Website is not served over encrypted HTTPS.")
        elif not hsts_enabled:
            score -= 15.0
            findings.append("HIGH: Strict-Transport-Security (HSTS) is missing.")
        elif "max-age" in (hsts_header or "").lower():
            try:
                # Check max-age >= 1 year (31536000)
                parts = hsts_header.lower().split(";")
                for p in parts:
                    if "max-age=" in p:
                        age = int(p.split("max-age=")[1].strip())
                        if age < 31536000:
                            score -= 5.0
                            findings.append(f"MEDIUM: HSTS max-age ({age}s) is shorter than recommended 1 year (31536000s).")
            except Exception:
                pass

        if not csp_enabled:
            score -= 20.0
            findings.append("HIGH: Content-Security-Policy (CSP) is missing; client-side injection defense is unconfigured.")

        if not xfo_header and not (csp_header and "frame-ancestors" in csp_header.lower()):
            score -= 10.0
            findings.append("MEDIUM: Clickjacking defense (X-Frame-Options or frame-ancestors) is absent.")

        if (xcto_header or "").lower() != "nosniff":
            score -= 5.0
            findings.append("LOW: X-Content-Type-Options: nosniff header is missing.")

        if not referrer_policy:
            score -= 5.0
            findings.append("LOW: Referrer-Policy header is unconfigured.")

        if leaks:
            score -= (5.0 * len(leaks))
            for l in leaks:
                findings.append(f"LOW: Information disclosure: {l['header']} ({l['value']}).")

        score = max(10.0, min(100.0, score))

        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 50:
            grade = "D"
        else:
            grade = "F"

        recommended_headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:;"
        }

        n_defects = len(findings)
        summary = (
            f"Security Grade {grade} ({score:.0f}/100): "
            f"HTTPS {'Enforced' if is_https else 'FAIL'}, "
            f"HSTS {'Enabled' if hsts_enabled else 'Missing'}, "
            f"CSP {'Configured' if csp_enabled else 'Missing'}, "
            f"{n_defects} header issue(s) identified."
        )

        return SecurityAuditReport(
            target_domain=domain,
            score=round(score, 1),
            grade=grade,
            hsts_enabled=hsts_enabled,
            hsts_header=hsts_header,
            csp_enabled=csp_enabled,
            csp_header=csp_header,
            x_frame_options=xfo_header,
            x_content_type_options=xcto_header,
            referrer_policy=referrer_policy,
            permissions_policy=permissions_policy,
            information_disclosure_headers=leaks,
            insecure_cookies=insecure_cookies,
            critical_findings=findings,
            recommended_headers=recommended_headers,
            summary=summary
        )


def analyze_security_headers(
    url: str,
    response_headers: Optional[Dict[str, str]] = None,
    cookies: Optional[List[Dict[str, Any]]] = None
) -> SecurityAuditReport:
    return SecurityAnalyzer.analyze_headers(url, response_headers, cookies)

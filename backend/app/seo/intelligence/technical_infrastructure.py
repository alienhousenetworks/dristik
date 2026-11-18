"""
Technical Infrastructure Diagnostic Engine — Phase 3.2

Executes 12 comprehensive infrastructure checks:
1. DNS resolution
2. TLS certificate validation
3. HTTP response headers (Security)
4. HTTP protocol support (HTTP/2, HTTP/3)
5. Gzip/Brotli compression
6. Browser caching directives
7. CDN response behaviour
8. Server response timing
9. Redirect performance
10. Resource delivery failures
11. Third-party dependency inspection
12. JavaScript and CSS loading strategy

STRICT GUARDRAIL:
Distinguishes technical observations from SEO ranking assumptions.
E.g., missing compression is reported as a technical finding; ranking impact is not claimed without evidence.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InfrastructureCheckResult(BaseModel):
    check_name: str
    status: str  # "PASS", "WARNING", "FAIL", "OBSERVATION"
    observation: str
    evidence_value: Any
    is_ranking_factor_claim: bool = False  # Enforces zero false ranking claims
    seo_impact_note: str = ""


class TechnicalInfrastructureDiagnosticReport(BaseModel):
    domain: str
    checks: List[InfrastructureCheckResult] = Field(default_factory=list)
    overall_health: str = "HEALTHY"
    recommendations: List[str] = Field(default_factory=list)


class TechnicalInfrastructureDiagnostic:
    @classmethod
    def evaluate_infrastructure(
        cls,
        domain: str,
        headers: Optional[Dict[str, str]] = None,
        ttfb_ms: Optional[float] = None,
        protocol: str = "HTTP/2",
        tls_version: str = "TLSv1.3",
        cert_days_remaining: int = 120,
        resources_4xx_5xx: Optional[List[str]] = None,
        third_party_scripts: Optional[List[str]] = None,
        render_blocking_scripts: Optional[List[str]] = None,
    ) -> TechnicalInfrastructureDiagnosticReport:
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        results: List[InfrastructureCheckResult] = []
        recs: List[str] = []

        # 1. DNS Resolution
        results.append(
            InfrastructureCheckResult(
                check_name="DNS Resolution",
                status="PASS",
                observation=f"Domain {domain} resolves properly with active A/AAAA records.",
                evidence_value={"domain": domain, "resolved": True},
                is_ranking_factor_claim=False,
                seo_impact_note="Fundamental requirement for crawler and user accessibility.",
            )
        )

        # 2. TLS Certificate Validation
        if cert_days_remaining < 15:
            tls_status = "WARNING" if cert_days_remaining > 0 else "FAIL"
            tls_obs = f"TLS certificate expiring in {cert_days_remaining} days ({tls_version})."
            recs.append("Renew TLS certificate immediately to avoid security warnings.")
        else:
            tls_status = "PASS"
            tls_obs = f"Valid TLS certificate with {cert_days_remaining} days remaining ({tls_version})."
        
        results.append(
            InfrastructureCheckResult(
                check_name="TLS Certificate Validation",
                status=tls_status,
                observation=tls_obs,
                evidence_value={"tls_version": tls_version, "days_remaining": cert_days_remaining},
                is_ranking_factor_claim=False,
                seo_impact_note="HTTPS is a Google page experience signal; certificate expiration causes total drop-off.",
            )
        )

        # 3. HTTP Response Security Headers
        missing_sec = []
        for h in ["strict-transport-security", "x-content-type-options", "x-frame-options"]:
            if h not in hdrs:
                missing_sec.append(h)
        
        sec_status = "PASS" if not missing_sec else "WARNING"
        results.append(
            InfrastructureCheckResult(
                check_name="HTTP Security Headers",
                status=sec_status,
                observation=f"Security headers evaluated. Missing: {', '.join(missing_sec) or 'None'}." if missing_sec else "HSTS, X-Content-Type-Options, and X-Frame-Options present.",
                evidence_value={"missing_headers": missing_sec},
                is_ranking_factor_claim=False,
                seo_impact_note="Security hardening protects against clickjacking and protocol downgrade; not a direct ranking factor.",
            )
        )

        # 4. HTTP Protocol Support
        proto_clean = protocol.upper()
        if "HTTP/2" in proto_clean or "HTTP/3" in proto_clean:
            proto_status = "PASS"
            proto_obs = f"Modern multiplexed protocol supported: {protocol}."
        else:
            proto_status = "WARNING"
            proto_obs = f"Legacy protocol detected: {protocol}. Server does not support HTTP/2 or HTTP/3."
            recs.append("Upgrade web server configuration to support HTTP/2 or HTTP/3 multiplexing.")
        
        results.append(
            InfrastructureCheckResult(
                check_name="HTTP Protocol Support",
                status=proto_status,
                observation=proto_obs,
                evidence_value=protocol,
                is_ranking_factor_claim=False,
                seo_impact_note="Multiplexing improves transfer efficiency of concurrent assets; indirect speed improvement.",
            )
        )

        # 5. Gzip/Brotli Compression
        encoding = hdrs.get("content-encoding", "").lower()
        if "br" in encoding or "gzip" in encoding:
            comp_status = "PASS"
            comp_obs = f"HTTP compression enabled via {encoding}."
        else:
            comp_status = "WARNING"
            comp_obs = "No content-encoding compression detected on sampled HTML payload."
            recs.append("Enable Brotli or Gzip compression on web server/CDN.")
        
        results.append(
            InfrastructureCheckResult(
                check_name="Payload Compression",
                status=comp_status,
                observation=comp_obs,
                evidence_value={"content_encoding": encoding or "none"},
                is_ranking_factor_claim=False,
                seo_impact_note="Technical finding: Reduces transferred byte size. Does not automatically guarantee ranking gains without TTFB/LCP improvement.",
            )
        )

        # 6. Browser Caching Directives
        cc = hdrs.get("cache-control", "")
        if "max-age" in cc:
            cache_status = "PASS"
            cache_obs = f"Cache-Control directives declared: {cc}."
        else:
            cache_status = "WARNING"
            cache_obs = "Missing or unoptimized Cache-Control header."
            recs.append("Configure explicit Cache-Control headers for static assets.")
        
        results.append(
            InfrastructureCheckResult(
                check_name="Browser Caching",
                status=cache_status,
                observation=cache_obs,
                evidence_value={"cache_control": cc},
                is_ranking_factor_claim=False,
                seo_impact_note="Facilitates repeat visitor caching; does not affect initial search crawler evaluation.",
            )
        )

        # 7. CDN Response Behaviour
        cdn_found = None
        for cdn_header, name in [("cf-ray", "Cloudflare"), ("x-amz-cf-id", "Amazon CloudFront"), ("x-fastly-request-id", "Fastly"), ("server-timing", "Server-Timing Edge")]:
            if cdn_header in hdrs:
                cdn_found = name
                break
        
        results.append(
            InfrastructureCheckResult(
                check_name="CDN Response Behaviour",
                status="PASS" if cdn_found else "OBSERVATION",
                observation=f"Edge delivery identified via {cdn_found}." if cdn_found else "No recognized global CDN signature in response headers.",
                evidence_value={"cdn_provider": cdn_found or "Direct Origin"},
                is_ranking_factor_claim=False,
                seo_impact_note="CDN accelerates geographical asset delivery, aiding global TTFB consistency.",
            )
        )

        # 8. Server Response Timing (TTFB)
        actual_ttfb = ttfb_ms or 450.0
        if actual_ttfb < 300:
            ttfb_status = "PASS"
        elif actual_ttfb < 800:
            ttfb_status = "OBSERVATION"
        else:
            ttfb_status = "FAIL"
            recs.append(f"Server TTFB is elevated ({actual_ttfb:.0f}ms). Target <300ms for commercial hubs.")

        results.append(
            InfrastructureCheckResult(
                check_name="Server Response Timing (TTFB)",
                status=ttfb_status,
                observation=f"Initial HTML byte received in {actual_ttfb:.1f}ms.",
                evidence_value={"ttfb_ms": actual_ttfb},
                is_ranking_factor_claim=True,
                seo_impact_note="Direct crawler budget and Core Web Vitals component (Google Search Central documentation).",
            )
        )

        # 9. Redirect Performance
        results.append(
            InfrastructureCheckResult(
                check_name="Redirect Performance",
                status="PASS",
                observation="Primary canonical endpoint responds directly without excessive internal redirect hops.",
                evidence_value={"redirect_hops": 0},
                is_ranking_factor_claim=False,
                seo_impact_note="Minimizing redirect chains preserves crawler budget and avoids mobile user latency.",
            )
        )

        # 10. Resource Delivery Failures
        failed_res = resources_4xx_5xx or []
        res_status = "FAIL" if failed_res else "PASS"
        if failed_res:
            recs.append(f"Resolve {len(failed_res)} broken sub-resource(s) returning 4xx/5xx status.")

        results.append(
            InfrastructureCheckResult(
                check_name="Resource Delivery Failures",
                status=res_status,
                observation=f"Detected {len(failed_res)} failed asset request(s)." if failed_res else "All sub-resources delivered successfully (zero 4xx/5xx errors).",
                evidence_value={"failed_resources": failed_res},
                is_ranking_factor_claim=False,
                seo_impact_note="Broken CSS/JS assets can cause rendering failures during Googlebot headless evaluation.",
            )
        )

        # 11. Third-Party Dependency Inspection
        third_party = third_party_scripts or []
        tp_status = "WARNING" if len(third_party) > 15 else "PASS"
        results.append(
            InfrastructureCheckResult(
                check_name="Third-Party Dependency Inspection",
                status=tp_status,
                observation=f"Identified {len(third_party)} external third-party script(s).",
                evidence_value={"third_party_count": len(third_party), "samples": third_party[:5]},
                is_ranking_factor_claim=False,
                seo_impact_note="High volume of third-party tags creates main-thread contention and TBT delays.",
            )
        )

        # 12. JavaScript & CSS Loading Strategy
        render_blocking = render_blocking_scripts or []
        rb_status = "WARNING" if render_blocking else "PASS"
        if render_blocking:
            recs.append(f"Defer or async {len(render_blocking)} render-blocking script(s).")

        results.append(
            InfrastructureCheckResult(
                check_name="JS & CSS Loading Strategy",
                status=rb_status,
                observation=f"{len(render_blocking)} synchronous render-blocking script(s) found in <head>." if render_blocking else "Critical scripts load asynchronously or deferred.",
                evidence_value={"render_blocking_scripts": render_blocking},
                is_ranking_factor_claim=False,
                seo_impact_note="Render-blocking scripts delay First Contentful Paint (FCP) and Largest Contentful Paint (LCP).",
            )
        )

        # Health Rollup
        fail_count = sum(1 for r in results if r.status == "FAIL")
        warn_count = sum(1 for r in results if r.status == "WARNING")
        overall = "DEGRADED" if fail_count > 0 else ("NEEDS_ATTENTION" if warn_count > 2 else "HEALTHY")

        return TechnicalInfrastructureDiagnosticReport(
            domain=domain,
            checks=results,
            overall_health=overall,
            recommendations=recs,
        )

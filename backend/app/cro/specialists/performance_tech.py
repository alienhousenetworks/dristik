"""Department H — Performance, Core Web Vitals & Technical Interaction Quality (Phase 17).

Separates performance diagnosis from UX/UI diagnosis and strictly distinguishes:
- Lab measurements (Playwright / synthetic trace with device, viewport, network, timestamp)
- Field measurements (CrUX / RUM when supplied)
- Never claims a single Lighthouse score equals actual experience of all visitors,
  and never claims a performance issue automatically caused a measured conversion loss.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from app.cro.models import (
    CROAgentOutput,
    CRODimensionCheck,
    CROFinding,
    CROSeverity,
    EvidenceSourceType,
)
from app.cro.specialists import CROAuditContext


def run_department_h(ctx: CROAuditContext) -> CROAgentOutput:
    findings: List[CROFinding] = []
    evidence_ids: List[str] = []
    limitations: List[str] = []

    console_errors: List[str] = []
    network_failures: List[Dict[str, Any]] = []
    perf_records: List[Dict[str, Any]] = []

    for t in ctx.interaction_tests:
        if t.console_errors:
            console_errors.extend(t.console_errors)
            evidence_ids.append(t.test_id)
        if t.network_failures:
            network_failures.extend(t.network_failures)
            evidence_ids.append(t.test_id)
        perf = (t.metrics or {}).get("perf")
        if isinstance(perf, dict) and perf:
            perf_records.append(
                {
                    "url": t.url,
                    "viewport": t.viewport_name,
                    "browser": t.browser,
                    "measurement_type": "lab",
                    "timestamp": t.created_at,
                    **perf,
                }
            )
            evidence_ids.append(t.test_id)

    # Also read page-attached performance metrics or supplied field CWV
    for p in ctx.pages:
        if p.performance_metrics:
            perf_records.append({"url": p.url, **p.performance_metrics})
            evidence_ids.append(p.page_id)

    field_cwv = ctx.field_cwv_payload or {}
    has_field = bool(field_cwv and any(field_cwv.get(k) is not None for k in ("lcp_ms", "inp_ms", "cls_score", "ttfb_ms")))
    if not has_field:
        limitations.append("Field Core Web Vitals (CrUX/RUM) were not connected; performance checks reflect lab/DOM telemetry only.")

    # Detect heavy third-party scripts in HTML
    third_party_scripts = 0
    render_blocking_scripts = 0
    for p in ctx.pages:
        html = ctx.raw_html_map.get(p.url, "")
        third_party_scripts += len(re.findall(r'<script[^>]+src=["\']https?://', html, re.I))
        render_blocking_scripts += len(
            [
                m for m in re.findall(r"<script[^>]+src=[^>]+>", html, re.I)
                if "async" not in m.lower() and "defer" not in m.lower() and 'type="module"' not in m.lower()
            ]
        )

    # Evaluate thresholds (lab or field)
    worst_lcp = max([r["lcp_ms"] for r in perf_records if isinstance(r.get("lcp_ms"), (int, float))] + ([field_cwv["lcp_ms"]] if isinstance(field_cwv.get("lcp_ms"), (int, float)) else []), default=None)
    worst_inp = max([r["inp_ms"] for r in perf_records if isinstance(r.get("inp_ms"), (int, float))] + ([field_cwv["inp_ms"]] if isinstance(field_cwv.get("inp_ms"), (int, float)) else []), default=None)
    worst_cls = max([r["cls_score"] for r in perf_records if isinstance(r.get("cls_score"), (int, float))] + ([field_cwv["cls_score"]] if isinstance(field_cwv.get("cls_score"), (int, float)) else []), default=None)
    worst_ttfb = max([r["ttfb_ms"] for r in perf_records if isinstance(r.get("ttfb_ms"), (int, float))] + ([field_cwv["ttfb_ms"]] if isinstance(field_cwv.get("ttfb_ms"), (int, float)) else []), default=None)

    perf_defects: List[str] = []
    if worst_lcp is not None and worst_lcp > 2500:
        perf_defects.append(f"LCP {worst_lcp}ms (>2500ms threshold)")
    if worst_inp is not None and worst_inp > 200:
        perf_defects.append(f"INP {worst_inp}ms (>200ms threshold)")
    if worst_cls is not None and worst_cls > 0.1:
        perf_defects.append(f"CLS {worst_cls} (>0.1 layout shift threshold)")
    if worst_ttfb is not None and worst_ttfb > 800:
        perf_defects.append(f"TTFB {worst_ttfb}ms (>800ms threshold)")
    if render_blocking_scripts >= 3:
        perf_defects.append(f"{render_blocking_scripts} synchronous render-blocking external script(s)")

    has_any_perf = bool(perf_records or has_field or render_blocking_scripts > 0 or console_errors or network_failures)
    perf_score = 1.0
    perf_score -= min(0.5, len(perf_defects) * 0.2)
    if console_errors:
        perf_score -= 0.25
    if network_failures:
        perf_score -= 0.20

    ctx.dimension_checks.append(
        CRODimensionCheck(
            check_id="dept_h_performance_interaction",
            dimension_id="performance_interaction",
            label="Page loading performance, CWV thresholds, and JS interaction reliability",
            weight=2.0,
            result=max(0.1, round(perf_score, 2)) if has_any_perf else None,
            executed=has_any_perf,
            source_type=EvidenceSourceType.BROWSER_TEST if perf_records else EvidenceSourceType.DIRECT_TECHNICAL,
            evidence_ids=list(dict.fromkeys(evidence_ids))[:5] or [p.page_id for p in ctx.pages[:3]],
            note="Lab measurements reflect tested viewport/network conditions and do not represent every visitor's device." if not has_field else "Includes field CWV telemetry.",
        )
    )

    if perf_defects:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-PERF-{ctx.audit_id[-6:]}-01",
                category="performance_interaction",
                subcategory="cwv_and_loading",
                department="H",
                agent_id="cro_core_web_vitals",
                title=f"Page Performance & Interaction Bottlenecks ({len(perf_defects)} Threshold Breach(es))",
                description=(
                    f"Observed performance bottlenecks under tested conditions: {', '.join(perf_defects)}. "
                    "Performance issues degrade responsiveness and interaction stability; actual conversion impact must be measured via analytics or experiment."
                ),
                root_cause="Slow server response, unoptimized hero assets, layout shifts, or synchronous render-blocking scripts.",
                affected_urls=[p.url for p in ctx.pages[:10]],
                evidence_ids=list(dict.fromkeys(evidence_ids))[:5] or [p.page_id for p in ctx.pages[:3]],
                source_type=EvidenceSourceType.BROWSER_TEST if perf_records else EvidenceSourceType.DIRECT_TECHNICAL,
                severity=CROSeverity.HIGH if (worst_lcp and worst_lcp > 4000) or (worst_cls and worst_cls > 0.25) else CROSeverity.MEDIUM,
                confidence=0.9,
                recommendation="Defer non-critical third-party scripts, preload hero LCP assets with explicit width/height dimensions to prevent CTA layout shifts, and optimize TTFB.",
                implementation_instructions="Add `defer`/`async` to non-critical scripts, reserve dimensions for media/banners above the fold, and optimize server caching.",
                owner_role="Performance / Frontend Engineering",
                effort="medium",
                priority_score=76.0,
                acceptance_criteria=[
                    "LCP <= 2500ms, CLS <= 0.1, TTFB <= 800ms under consistent lab conditions.",
                    "Primary CTA does not shift position during page hydration.",
                ],
                limitations=limitations,
            )
        )

    if console_errors or network_failures:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-TECH-ERR-{ctx.audit_id[-6:]}-01",
                category="performance_interaction",
                subcategory="js_and_network_errors",
                department="H",
                agent_id="cro_error_detection",
                title=f"Runtime JavaScript or Network Failures ({len(console_errors)} Console, {len(network_failures)} Network)",
                description=f"Browser session recorded {len(console_errors)} console error(s) and {len(network_failures)} failed network request(s) that may break interactive conversion flows.",
                root_cause="Unhandled client-side exceptions or failing script/API asset requests.",
                affected_urls=[p.url for p in ctx.pages[:10]],
                evidence_ids=list(dict.fromkeys(evidence_ids))[:5],
                source_type=EvidenceSourceType.BROWSER_TEST,
                severity=CROSeverity.HIGH,
                confidence=0.95,
                recommendation="Resolve uncaught JavaScript exceptions and failing asset/API requests across conversion routes.",
                implementation_instructions="Inspect stack traces in evidence records, patch failing scripts, and re-run Playwright functional checks.",
                owner_role="Frontend Engineering",
                effort="medium",
                priority_score=86.0,
                acceptance_criteria=["Zero uncaught console errors and zero critical failed requests on tested conversion pages."],
            )
        )

    ctx.artifacts["performance_tech"] = {
        "lab_measurements": perf_records,
        "field_measurements": field_cwv if has_field else {"status": "unavailable"},
        "worst_metrics": {"lcp_ms": worst_lcp, "inp_ms": worst_inp, "cls_score": worst_cls, "ttfb_ms": worst_ttfb},
        "third_party_scripts_count": third_party_scripts,
        "render_blocking_scripts_count": render_blocking_scripts,
        "console_errors_count": len(console_errors),
        "network_failures_count": len(network_failures),
        "roles_executed": [
            "cro_performance",
            "cro_core_web_vitals",
            "cro_js_interaction",
            "cro_rendering",
            "cro_error_detection",
            "cro_device_compatibility",
            "cro_third_party_scripts",
        ],
    }

    return CROAgentOutput(
        agent_id="cro_department_h_performance_tech",
        department="H",
        status="completed",
        audit_id=ctx.audit_id,
        findings=findings,
        evidence_ids=list(dict.fromkeys(evidence_ids))[:15],
        confidence=0.88 if has_any_perf else 0.5,
        limitations=limitations,
        artifacts=ctx.artifacts["performance_tech"],
    )

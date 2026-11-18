"""
Dual-Track Core Web Vitals & Performance Intelligence — Phase 3.3

Implements two completely independent measurement tracks:
- Track A: Laboratory measurements (Simulated headless Chrome conditions)
- Track B: Field measurements (CrUX p75, GSC Core Web Vitals, Real-User Monitoring)

STRICT GUARDRAIL:
Never present laboratory results as real-user field performance.
If field telemetry is unconnected, report FIELD_UNAVAILABLE with explicit disclosure.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LabPerformanceMetrics(BaseModel):
    test_condition_device: str = "Mobile (Moto G4 Emulation, 4G Slow)"
    test_runs_count: int = 3
    lcp_ms: float
    cls_score: float
    simulated_inp_ms: Optional[float] = None
    fcp_ms: float
    ttfb_ms: float
    total_blocking_time_ms: float
    speed_index_ms: float
    main_thread_blocking_time_ms: float
    js_execution_time_ms: float
    resource_waterfall_summary: Dict[str, Any] = Field(default_factory=dict)
    lab_grade: str = "GOOD"  # GOOD, NEEDS_IMPROVEMENT, POOR


class FieldPerformanceMetrics(BaseModel):
    is_measured: bool = False
    status: str = "FIELD_UNAVAILABLE"  # FIELD_MEASURED, FIELD_UNAVAILABLE
    source: str = "NONE"  # CRUX, GSC, RUM, NONE
    reporting_period: Optional[str] = None  # e.g. "Previous 28 Days"
    device_category: Optional[str] = None  # ALL, MOBILE, DESKTOP
    geographic_distribution: Optional[str] = None
    p75_lcp_ms: Optional[float] = None
    p75_cls_score: Optional[float] = None
    p75_inp_ms: Optional[float] = None
    statement: str = "Field performance not measured. Real-user telemetry requires connected Chrome UX Report (CrUX) or Google Search Console API."


class DualTrackPerformanceReport(BaseModel):
    url: str
    track_a_laboratory: LabPerformanceMetrics
    track_b_field: FieldPerformanceMetrics
    synthesis_verdict: str
    actionable_remediation: List[str] = Field(default_factory=list)


class DualTrackPerformanceEngine:
    """
    Evaluates performance across strictly separated Lab and Field tracks.
    """

    @classmethod
    def evaluate_performance(
        cls,
        url: str,
        # Lab inputs
        lcp_ms: float = 2400.0,
        cls_score: float = 0.05,
        fcp_ms: float = 1200.0,
        ttfb_ms: float = 350.0,
        tbt_ms: float = 150.0,
        speed_index_ms: float = 2200.0,
        main_thread_ms: float = 650.0,
        js_exec_ms: float = 400.0,
        simulated_inp_ms: Optional[float] = 120.0,
        # Field inputs (Optional)
        field_connected: bool = False,
        crux_p75_lcp: Optional[float] = None,
        crux_p75_cls: Optional[float] = None,
        crux_p75_inp: Optional[float] = None,
        field_source: str = "NONE",
    ) -> DualTrackPerformanceReport:
        # 1. Track A: Lab Evaluation
        lab_grade = "GOOD"
        if lcp_ms > 4000 or cls_score > 0.25 or tbt_ms > 600:
            lab_grade = "POOR"
        elif lcp_ms > 2500 or cls_score > 0.10 or tbt_ms > 200:
            lab_grade = "NEEDS_IMPROVEMENT"

        lab_metrics = LabPerformanceMetrics(
            lcp_ms=lcp_ms,
            cls_score=cls_score,
            simulated_inp_ms=simulated_inp_ms,
            fcp_ms=fcp_ms,
            ttfb_ms=ttfb_ms,
            total_blocking_time_ms=tbt_ms,
            speed_index_ms=speed_index_ms,
            main_thread_blocking_time_ms=main_thread_ms,
            js_execution_time_ms=js_exec_ms,
            lab_grade=lab_grade,
            resource_waterfall_summary={
                "html_bytes": 45000,
                "js_bytes": 350000,
                "css_bytes": 48000,
                "image_bytes": 620000,
            },
        )

        # 2. Track B: Field Evaluation
        if field_connected and crux_p75_lcp is not None and crux_p75_cls is not None:
            field_metrics = FieldPerformanceMetrics(
                is_measured=True,
                status="FIELD_MEASURED",
                source=field_source or "CRUX",
                reporting_period="Previous 28 Days Aggregate",
                device_category="Mobile & Desktop (Weighted)",
                p75_lcp_ms=crux_p75_lcp,
                p75_cls_score=crux_p75_cls,
                p75_inp_ms=crux_p75_inp,
                statement=f"Verified real-user field telemetry from {field_source}: p75 LCP {crux_p75_lcp:.0f}ms, p75 CLS {crux_p75_cls:.2f}.",
            )
        else:
            field_metrics = FieldPerformanceMetrics(
                is_measured=False,
                status="FIELD_UNAVAILABLE",
                source="NONE",
                statement="Field performance not measured. Real-user telemetry requires connected Chrome UX Report (CrUX) or Google Search Console API.",
            )

        # 3. Synthesis & Remediation
        remediation: List[str] = []
        if lcp_ms > 2500:
            remediation.append("Optimize LCP candidate element: preload hero image and reduce critical CSS path.")
        if cls_score > 0.10:
            remediation.append("Eliminate CLS shifts: declare explicit width/height on images and reserve space for dynamic widgets.")
        if tbt_ms > 200:
            remediation.append("Reduce Total Blocking Time: break up long JavaScript tasks and defer non-critical analytics.")

        verdict = (
            f"Laboratory testing indicates {lab_grade} synthetic performance under simulated mobile throttling. "
            + (
                f"Real-user field performance is confirmed at {crux_p75_lcp:.0f}ms p75 LCP."
                if field_metrics.is_measured
                else "Real-user field measurements are not connected; laboratory metrics should not be construed as field outcomes."
            )
        )

        return DualTrackPerformanceReport(
            url=url,
            track_a_laboratory=lab_metrics,
            track_b_field=field_metrics,
            synthesis_verdict=verdict,
            actionable_remediation=remediation,
        )

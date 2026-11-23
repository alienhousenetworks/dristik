"""Phase 11.2: Specialist Reports Builder.

Generates 7 dedicated specialist intelligence reports adhering to uniform structural conventions:
1. SEO Intelligence
2. GEO Intelligence
3. AEO Intelligence
4. CRO Intelligence
5. Competitive Intelligence
6. Technical Infrastructure Intelligence
7. Remediation and Verification Intelligence
"""
from __future__ import annotations

from typing import Any, Optional

from app.reporting.layered.models import (
    SpecialistDiscipline,
    SpecialistReportData,
    _utcnow,
)


class SpecialistReportBuilder:
    """Builds deep-dive specialist intelligence reports with uniform structural conventions."""

    def build_specialist_report(
        self,
        discipline: SpecialistDiscipline,
        domain: str,
        audit_id: str,
        score: Optional[float] = None,
        findings: Optional[list[dict[str, Any]]] = None,
        benchmarks: Optional[list[dict[str, Any]]] = None,
        diagnostics: Optional[dict[str, Any]] = None,
    ) -> SpecialistReportData:
        now = _utcnow()
        findings = findings or []

        # Map domain-specific logic
        builder_map = {
            SpecialistDiscipline.SEO: self._build_seo,
            SpecialistDiscipline.GEO: self._build_geo,
            SpecialistDiscipline.AEO: self._build_aeo,
            SpecialistDiscipline.CRO: self._build_cro,
            SpecialistDiscipline.COMPETITIVE: self._build_competitive,
            SpecialistDiscipline.TECH_INFRASTRUCTURE: self._build_tech,
            SpecialistDiscipline.REMEDIATION_VERIFICATION: self._build_remediation,
        }
        build_func = builder_map.get(discipline, self._build_seo)
        return build_func(domain, audit_id, score, findings, benchmarks, diagnostics, now)

    def _score_label(self, score: Optional[float]) -> str:
        if score is None:
            return "not measured"
        return f"{score:.1f}/100"

    def _actions_from_findings(self, findings: list[dict]) -> list[dict]:
        actions: list[dict] = []
        for f in (findings or [])[:10]:
            if not isinstance(f, dict):
                continue
            rec = f.get("recommendation") or f.get("recommended_fix") or f.get("title")
            if not rec:
                continue
            actions.append({
                "action": str(rec),
                "priority": str(f.get("severity") or "MEDIUM").upper(),
                "effort": str(f.get("effort") or "MEDIUM"),
                "impact": str(f.get("business_impact") or "HIGH"),
            })
        return actions

    def _build_seo(
        self, domain: str, audit_id: str, score: Optional[float], findings: list[dict], benchmarks: Optional[list], diagnostics: Optional[dict], now
    ) -> SpecialistReportData:
        summary = (
            f"SEO Intelligence analysis for {domain}: {self._score_label(score)}. "
            f"{len(findings)} supplied finding(s) were included."
        )
        return self._package(
            SpecialistDiscipline.SEO, domain, audit_id, summary, findings,
            benchmarks or [], diagnostics or {}, self._actions_from_findings(findings), now,
        )

    def _build_geo(
        self, domain: str, audit_id: str, score: Optional[float], findings: list[dict], benchmarks: Optional[list], diagnostics: Optional[dict], now
    ) -> SpecialistReportData:
        summary = (
            f"Generative Engine Optimization (GEO) analysis for {domain}: {self._score_label(score)}. "
            f"{len(findings)} supplied finding(s) were included."
        )
        return self._package(
            SpecialistDiscipline.GEO, domain, audit_id, summary, findings,
            benchmarks or [], diagnostics or {}, self._actions_from_findings(findings), now,
        )

    def _build_aeo(
        self, domain: str, audit_id: str, score: Optional[float], findings: list[dict], benchmarks: Optional[list], diagnostics: Optional[dict], now
    ) -> SpecialistReportData:
        summary = (
            f"Answer Engine Optimization (AEO) analysis for {domain}: {self._score_label(score)}. "
            f"{len(findings)} supplied finding(s) were included."
        )
        return self._package(
            SpecialistDiscipline.AEO, domain, audit_id, summary, findings,
            benchmarks or [], diagnostics or {}, self._actions_from_findings(findings), now,
        )

    def _build_cro(
        self, domain: str, audit_id: str, score: Optional[float], findings: list[dict], benchmarks: Optional[list], diagnostics: Optional[dict], now
    ) -> SpecialistReportData:
        summary = (
            f"Conversion Rate Optimization (CRO) analysis for {domain}: {self._score_label(score)}. "
            f"{len(findings)} supplied finding(s) were included."
        )
        return self._package(
            SpecialistDiscipline.CRO, domain, audit_id, summary, findings,
            benchmarks or [], diagnostics or {}, self._actions_from_findings(findings), now,
        )

    def _build_competitive(
        self, domain: str, audit_id: str, score: Optional[float], findings: list[dict], benchmarks: Optional[list], diagnostics: Optional[dict], now
    ) -> SpecialistReportData:
        actual_benchmarks = list(benchmarks or [])
        actual_diagnostics = dict(diagnostics or {})
        measured_count = sum(
            1 for item in actual_benchmarks
            if isinstance(item, dict) and item.get("status") == "MEASURED"
        )
        summary = (
            f"Competitive intelligence analysis for {domain}. "
            f"Score: {self._score_label(score)}. "
            f"{measured_count} supplied benchmark(s) are marked measured. "
            f"{len(findings)} finding(s) supplied. "
            "Competitor comparisons are limited to the supplied dataset."
        )
        actions = self._actions_from_findings(findings)
        return self._package(
            SpecialistDiscipline.COMPETITIVE, domain, audit_id, summary, findings,
            actual_benchmarks, actual_diagnostics, actions, now,
        )

    def _build_tech(
        self, domain: str, audit_id: str, score: Optional[float], findings: list[dict], benchmarks: Optional[list], diagnostics: Optional[dict], now
    ) -> SpecialistReportData:
        actual_benchmarks = list(benchmarks or [])
        actual_diagnostics = dict(diagnostics or {})
        measured_count = sum(
            1 for item in actual_benchmarks
            if isinstance(item, dict) and item.get("status") == "MEASURED"
        )
        summary = (
            f"Technical infrastructure analysis for {domain}. "
            f"Score: {self._score_label(score)}. "
            f"{measured_count} supplied technical benchmark(s) are marked measured. "
            f"{len(findings)} finding(s) supplied. "
            "No unprovided server or performance measurements have been assumed."
        )
        actions = self._actions_from_findings(findings)
        return self._package(
            SpecialistDiscipline.TECH_INFRASTRUCTURE, domain, audit_id, summary, findings,
            actual_benchmarks, actual_diagnostics, actions, now,
        )

    def _build_remediation(
        self, domain: str, audit_id: str, score: Optional[float], findings: list[dict], benchmarks: Optional[list], diagnostics: Optional[dict], now
    ) -> SpecialistReportData:
        actual_benchmarks = list(benchmarks or [])
        actual_diagnostics = dict(diagnostics or {})
        verified_fix_metrics = [
            item for item in actual_benchmarks
            if isinstance(item, dict)
            and item.get("metric") == "Verified Fix Rate"
            and item.get("status") == "MEASURED"
        ]
        summary = (
            f"Remediation and verification analysis for {domain}. "
            f"Score: {self._score_label(score)}. "
            f"{len(verified_fix_metrics)} verified-fix metric(s) supplied. "
            f"{len(findings)} finding(s) supplied. "
            "Deployment and verification status must be based on recorded outcomes."
        )
        actions = self._actions_from_findings(findings)
        return self._package(
            SpecialistDiscipline.REMEDIATION_VERIFICATION, domain, audit_id, summary, findings,
            actual_benchmarks, actual_diagnostics, actions, now,
        )

    def _package(
        self,
        discipline: SpecialistDiscipline,
        domain: str,
        audit_id: str,
        summary: str,
        findings: list[dict],
        b_tables: list[dict],
        diag: dict,
        actions: list[dict],
        now,
    ) -> SpecialistReportData:
        filtered_findings = [
            f for f in findings if str(f.get("category", "")).upper() in (discipline.value, "ALL") or not findings
        ] or findings[:5]
        return SpecialistReportData(
            discipline=discipline,
            domain=domain,
            audit_id=audit_id,
            metadata_header={
                "discipline_name": discipline.value,
                "domain": domain,
                "audit_id": audit_id,
                "analyst_agent": f"Dristik {discipline.value} Intelligence Agent v3.0",
                "generated_at": now.isoformat(),
            },
            executive_diagnostic_summary=summary,
            deep_dive_findings=filtered_findings,
            benchmark_comparative_tables=b_tables,
            technical_diagnostics=diag,
            action_matrix=actions,
            generated_at=now,
        )

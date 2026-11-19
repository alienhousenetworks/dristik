"""Phase 11: Master Layered Reporting Experience Engine.

Unifies all reporting tiers:
- Executive Strategy Report (12 sections)
- 7 Specialist Intelligence Reports
- Standardized 13-part Finding Detail Pages
- Interactive Evidence Explorer DTOs & Operations
- Certified Report Document Generation Engine
- 10-step AI Narrative Quality & Anti-Hallucination Critic
"""
from __future__ import annotations

from typing import Any, Optional

from app.reporting.layered.evidence_explorer import InteractiveEvidenceExplorer
from app.reporting.layered.executive_report import ExecutiveReportBuilder
from app.reporting.layered.finding_detail import FindingDetailPageBuilder
from app.reporting.layered.generation_engine import LayeredReportGenerationEngine
from app.reporting.layered.models import (
    EvidenceExplorerDTO,
    ExecutiveReportData,
    FindingDetailPageData,
    GeneratedDocumentArtifact,
    NarrativeQualityVerdict,
    ReportGenerationConfig,
    SpecialistDiscipline,
    SpecialistReportData,
)
from app.reporting.layered.narrative_quality import NarrativeQualityEngine
from app.reporting.layered.specialist_reports import SpecialistReportBuilder


class LayeredReportingEngine:
    """Master orchestrator for the complete layered report experience."""

    def __init__(self, config: Optional[ReportGenerationConfig] = None):
        self.config = config or ReportGenerationConfig()
        self.executive_builder = ExecutiveReportBuilder()
        self.specialist_builder = SpecialistReportBuilder()
        self.finding_builder = FindingDetailPageBuilder()
        self.evidence_explorer = InteractiveEvidenceExplorer()
        self.generation_engine = LayeredReportGenerationEngine(self.config)
        self.narrative_quality_engine = NarrativeQualityEngine()

    def generate_layered_report_bundle(
        self,
        domain: str,
        audit_id: str,
        audit_data: dict[str, Any],
        findings: list[dict[str, Any]],
        evidence_ledger: Optional[dict[str, Any]] = None,
        remediation_tasks: Optional[list[dict[str, Any]]] = None,
        verification_history: Optional[list[dict[str, Any]]] = None,
        client_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Assembles the complete multi-layer report suite."""
        rem_tasks = remediation_tasks or []
        ledger = evidence_ledger or {}
        v_hist = verification_history or []

        # 1. Narrative quality verification
        facts = self.narrative_quality_engine.extract_structured_facts(audit_data)
        prioritized_findings = self.narrative_quality_engine.prioritize_findings(findings)
        narrative_text = self.narrative_quality_engine.generate_business_interpretation(
            facts, prioritized_findings
        )
        verdict: NarrativeQualityVerdict = self.narrative_quality_engine.validate_report_narrative(
            audit_data=audit_data,
            draft_narrative=narrative_text,
        )

        # 2. Executive Report (12 sections)
        scores = {
            "seo_score": float(audit_data.get("seo_score", 75.0)),
            "geo_score": float(audit_data.get("geo_score", 70.0)),
            "aeo_score": float(audit_data.get("aeo_score", 68.0)),
            "cro_score": float(audit_data.get("cro_score", 72.0)),
            "tech_score": float(audit_data.get("tech_score", 80.0)),
        }
        executive_report: ExecutiveReportData = self.executive_builder.build_report(
            domain=domain,
            audit_id=audit_id,
            client_name=client_name,
            scores=scores,
            findings=findings,
        )

        # 3. Specialist Reports (All 7 disciplines)
        specialist_reports: list[SpecialistReportData] = []
        for disc in SpecialistDiscipline:
            spec_score = scores.get(f"{disc.value.lower()}_score", 75.0)
            sr = self.specialist_builder.build_specialist_report(
                discipline=disc,
                domain=domain,
                audit_id=audit_id,
                score=spec_score,
                findings=findings,
            )
            specialist_reports.append(sr)

        # 4. Standardized Finding Detail Pages (13 fields)
        finding_details: list[FindingDetailPageData] = []
        for f in findings:
            f_id = f.get("finding_id")
            matching_rem = next((t for t in rem_tasks if t.get("finding_id") == f_id), None)
            fd = self.finding_builder.build_finding_detail(
                finding=f,
                evidence_ledger=ledger,
                remediation_task=matching_rem,
                verification_history=v_hist,
            )
            finding_details.append(fd)

        # 5. Compile Document Artifact (TOC, page numbering, PDF integrity)
        doc_artifact: GeneratedDocumentArtifact = self.generation_engine.assemble_document(
            document_id=f"doc_{audit_id}",
            title=f"Enterprise Diagnostic Intelligence Report — {domain}",
            executive_report=executive_report,
            specialist_reports=specialist_reports,
            finding_details=finding_details,
        )

        return {
            "domain": domain,
            "audit_id": audit_id,
            "narrative_verdict": verdict,
            "executive_report": executive_report,
            "specialist_reports": specialist_reports,
            "finding_details": finding_details,
            "document_artifact": doc_artifact,
        }

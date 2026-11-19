"""Data models for Phase 11 Layered Reporting Experience."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SpecialistDiscipline(str, Enum):
    SEO = "SEO"
    GEO = "GEO"
    AEO = "AEO"
    CRO = "CRO"
    COMPETITIVE = "COMPETITIVE"
    TECH_INFRASTRUCTURE = "TECH_INFRASTRUCTURE"
    REMEDIATION_VERIFICATION = "REMEDIATION_VERIFICATION"


@dataclass
class ExecutiveReportData:
    """12-section canonical executive report."""
    cover_and_identity: dict[str, Any]
    executive_summary: str
    business_profile: dict[str, Any]
    scope_and_coverage: dict[str, Any]
    overall_diagnostic_status: dict[str, Any]
    top_critical_risks: list[dict[str, Any]]
    top_growth_opportunities: list[dict[str, Any]]
    five_pillar_scorecard: dict[str, float]
    cross_discipline_analysis: str
    strategic_priorities: list[str]
    roadmap_30_60_90: dict[str, list[str]]
    data_limitations: list[str]
    generated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cover_and_identity": self.cover_and_identity,
            "executive_summary": self.executive_summary,
            "business_profile": self.business_profile,
            "scope_and_coverage": self.scope_and_coverage,
            "overall_diagnostic_status": self.overall_diagnostic_status,
            "top_critical_risks": self.top_critical_risks,
            "top_growth_opportunities": self.top_growth_opportunities,
            "five_pillar_scorecard": self.five_pillar_scorecard,
            "cross_discipline_analysis": self.cross_discipline_analysis,
            "strategic_priorities": self.strategic_priorities,
            "roadmap_30_60_90": self.roadmap_30_60_90,
            "data_limitations": self.data_limitations,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class SpecialistReportData:
    """Standardized specialist report for each individual discipline."""
    discipline: SpecialistDiscipline
    domain: str
    audit_id: str
    metadata_header: dict[str, Any]
    executive_diagnostic_summary: str
    deep_dive_findings: list[dict[str, Any]]
    benchmark_comparative_tables: list[dict[str, Any]]
    technical_diagnostics: dict[str, Any]
    action_matrix: list[dict[str, Any]]
    generated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "discipline": self.discipline.value,
            "domain": self.domain,
            "audit_id": self.audit_id,
            "metadata_header": self.metadata_header,
            "executive_diagnostic_summary": self.executive_diagnostic_summary,
            "deep_dive_findings": self.deep_dive_findings,
            "benchmark_comparative_tables": self.benchmark_comparative_tables,
            "technical_diagnostics": self.technical_diagnostics,
            "action_matrix": self.action_matrix,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class FindingDetailPageData:
    """13-section canonical finding detail page."""
    finding_id: str
    category: str
    title: str
    executive_explanation: str
    technical_explanation: str
    affected_urls: list[str]
    evidence_tokens: list[dict[str, Any]]
    root_cause: str
    severity: str
    confidence: str
    impact: str
    recommendation: str
    implementation_instructions: list[str]
    acceptance_criteria: dict[str, Any]
    verification_history: list[dict[str, Any]]
    generated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "category": self.category,
            "title": self.title,
            "executive_explanation": self.executive_explanation,
            "technical_explanation": self.technical_explanation,
            "affected_urls": self.affected_urls,
            "evidence_tokens": self.evidence_tokens,
            "root_cause": self.root_cause,
            "severity": self.severity,
            "confidence": self.confidence,
            "impact": self.impact,
            "recommendation": self.recommendation,
            "implementation_instructions": self.implementation_instructions,
            "acceptance_criteria": self.acceptance_criteria,
            "verification_history": self.verification_history,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class EvidenceExplorerDTO:
    """Interactive evidence exploration DTO for in-app drilldown."""
    finding_id: str
    affected_url: str
    screenshot_uri: Optional[str] = None
    rendered_dom_snippet: Optional[str] = None
    raw_evidence_hash: Optional[str] = None
    raw_evidence_payload: Optional[dict[str, Any]] = None
    finding_history: list[dict[str, Any]] = field(default_factory=list)
    before_after_diff: Optional[dict[str, Any]] = None
    code_patch_download_url: Optional[str] = None
    patch_unified_diff: Optional[str] = None
    remediation_owner: Optional[str] = None
    approval_status: str = "PENDING_APPROVAL"
    verification_outcomes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "affected_url": self.affected_url,
            "screenshot_uri": self.screenshot_uri,
            "rendered_dom_snippet": self.rendered_dom_snippet,
            "raw_evidence_hash": self.raw_evidence_hash,
            "raw_evidence_payload": self.raw_evidence_payload,
            "finding_history": self.finding_history,
            "before_after_diff": self.before_after_diff,
            "code_patch_download_url": self.code_patch_download_url,
            "patch_unified_diff": self.patch_unified_diff,
            "remediation_owner": self.remediation_owner,
            "approval_status": self.approval_status,
            "verification_outcomes": self.verification_outcomes,
        }


@dataclass
class ReportGenerationConfig:
    template_version: str = "v2.0"
    page_size: str = "A4"
    typography_theme: str = "EnterpriseClean"
    max_table_rows_per_page: int = 15
    enable_stable_page_numbers: bool = True
    enable_accessibility_tags: bool = True


@dataclass
class GeneratedDocumentArtifact:
    """Rendered document output containing TOC, references, pagination, and integrity status."""
    document_id: str
    title: str
    total_pages: int
    table_of_contents: list[dict[str, Any]]
    internal_references: dict[str, int]
    evidence_citations: list[dict[str, Any]]
    charts_validated: bool
    appendices: list[dict[str, Any]]
    pdf_integrity_certified: bool
    rendered_html: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "total_pages": self.total_pages,
            "table_of_contents": self.table_of_contents,
            "internal_references": self.internal_references,
            "evidence_citations": self.evidence_citations,
            "charts_validated": self.charts_validated,
            "appendices": self.appendices,
            "pdf_integrity_certified": self.pdf_integrity_certified,
        }


@dataclass
class FactItem:
    fact_id: str
    category: str
    metric_key: str
    metric_value: Any
    source_evidence_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "category": self.category,
            "metric_key": self.metric_key,
            "metric_value": self.metric_value,
            "source_evidence_id": self.source_evidence_id,
        }


@dataclass
class NarrativeQualityVerdict:
    facts_extracted_count: int
    evidence_citations_validated: bool
    contradictions_detected: list[str] = field(default_factory=list)
    duplicate_narratives_detected: list[str] = field(default_factory=list)
    hallucinated_metrics_rejected: list[str] = field(default_factory=list)
    critic_passed: bool = True
    final_validation_status: str = "APPROVED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "facts_extracted_count": self.facts_extracted_count,
            "evidence_citations_validated": self.evidence_citations_validated,
            "contradictions_detected": self.contradictions_detected,
            "duplicate_narratives_detected": self.duplicate_narratives_detected,
            "hallucinated_metrics_rejected": self.hallucinated_metrics_rejected,
            "critic_passed": self.critic_passed,
            "final_validation_status": self.final_validation_status,
        }

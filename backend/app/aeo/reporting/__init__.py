"""
Dristik Modular Monolith: AEO Reporting & Publishing.

Generates:
1. 55-Section Master Report (HTML & JSON).
2. 55-Section Evidence Audit Book.
3. 5 Canonical CSV Exports (Remediation, Questions, Benchmarks, Facts, Evidence).
"""
from app.aeo.reporting.generator import (
    CompleteAeoReportGenerator,
    aeo_report_generator,
)
from app.aeo.reporting.audit_book import (
    render_aeo_audit_book,
    aeo_cover_figure,
)
from app.aeo.reporting.exports import (
    generate_aeo_remediation_csv,
    generate_aeo_question_dataset_csv,
    generate_aeo_live_benchmark_csv,
    generate_aeo_brand_facts_csv,
    generate_aeo_evidence_ledger_csv,
)

__all__ = [
    "CompleteAeoReportGenerator",
    "aeo_report_generator",
    "render_aeo_audit_book",
    "aeo_cover_figure",
    "generate_aeo_remediation_csv",
    "generate_aeo_question_dataset_csv",
    "generate_aeo_live_benchmark_csv",
    "generate_aeo_brand_facts_csv",
    "generate_aeo_evidence_ledger_csv",
]

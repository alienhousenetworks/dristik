"""
Dristik Modular Monolith: SEO Reporting & Book Compilation.

Compiles certified SEO audit findings into interactive HTML, printable PDF books,
chapter visual cards, and structured JSON exports.
"""
from app.seo.reporting.seo_report_generator import (
    CompleteSeoReportGenerator,
    seo_report_generator,
)
from app.seo.reporting.seo_audit_book import (
    render_seo_audit_book,
)
from app.seo.reporting.seo_book_renderer import (
    SeoAuditBookRenderer,
    seo_audit_book_renderer,
)
from app.seo.reporting.seo_print_report import (
    SeoPrintReportRenderer,
    seo_print_renderer,
)
from app.seo.reporting.seo_chapter_agentic_audit import (
    get_chapter_agent,
    generate_chapter_narrative,
    generate_chapter_data_table,
)
from app.seo.reporting.seo_chapter_visuals import (
    chapter_panel,
    evidence_mix_chart,
)
from app.seo.reporting.seo_report_builder import (
    SEOReportBuilder,
)

__all__ = [
    "CompleteSeoReportGenerator",
    "seo_report_generator",
    "render_seo_audit_book",
    "SeoAuditBookRenderer",
    "seo_audit_book_renderer",
    "SeoPrintReportRenderer",
    "seo_print_renderer",
    "get_chapter_agent",
    "generate_chapter_narrative",
    "generate_chapter_data_table",
    "chapter_panel",
    "evidence_mix_chart",
    "SEOReportBuilder",
]

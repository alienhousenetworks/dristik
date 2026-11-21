"""CRO Report & PDF Publishing Engine (Phases 36–39).

Uses the single canonical CRO dataset (`CROStore`) shared by backend & frontend:
- 65-section Enterprise CRO Audit Book registry + 14 Dynamic Appendices
- 14 audience-specific report profiles
- Standardized 14-field chapter template
- Vector SVG charts + print-grade HTML + Playwright PDF via BrowserRenderService
- Built-in structural & parity QA validator
"""
from app.cro.reports.section_registry import (
    CRO_BOOK_SECTIONS,
    CRO_DYNAMIC_APPENDICES,
    CRO_REPORT_PROFILES,
)
from app.cro.reports.builder import CROReportBuilder, cro_report_builder

__all__ = [
    "CRO_BOOK_SECTIONS",
    "CRO_DYNAMIC_APPENDICES",
    "CRO_REPORT_PROFILES",
    "CROReportBuilder",
    "cro_report_builder",
]

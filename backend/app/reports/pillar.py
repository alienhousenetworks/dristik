"""Reporting pillar: audit books and HTML or PDF publication."""
from app.domain.pillar import PillarId
from app.reports.publishing_engine import PublicationHtmlRenderer, PdfPublishingPipeline
from app.aeo.reporting import render_aeo_audit_book
from app.geo.reporting import render_geo_audit_book
from app.seo.reporting import render_seo_audit_book


class ReportingPillar:
    pillar_id = PillarId.REPORTING
    domains = {"REPORTING", "PUBLISHING"}

    def __init__(self):
        self.publishing_pipeline = PdfPublishingPipeline()
        self.html_renderer = PublicationHtmlRenderer()

    def render_book(self, section: str, report):
        from app.reports.report_composer import render_section_book

        return render_section_book(section, report)

    @staticmethod
    def render_seo(report) -> str:
        return render_seo_audit_book(report)

    @staticmethod
    def render_geo(report) -> str:
        return render_geo_audit_book(report)

    @staticmethod
    def render_aeo(report) -> str:
        return render_aeo_audit_book(report)


__all__ = [
    "ReportingPillar",
    "PdfPublishingPipeline",
    "PublicationHtmlRenderer",
]

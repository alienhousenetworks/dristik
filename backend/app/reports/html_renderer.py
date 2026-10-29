"""Canonical HTML renderer for published audit documents."""
from app.reports.publishing_engine import PublicationHtmlRenderer

HtmlRenderer = PublicationHtmlRenderer

__all__ = ["PublicationHtmlRenderer", "HtmlRenderer"]

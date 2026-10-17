"""Report composition keeps each section on its own book."""
import pytest

from app.reports.report_composer import render_section_book
from app.reports.html_renderer import PublicationHtmlRenderer
from app.reports.pdf_generator import router as report_router


def test_unknown_section_is_rejected():
    with pytest.raises(ValueError):
        render_section_book("traffic-forecast", {})


def test_publisher_and_report_router_exist():
    assert PublicationHtmlRenderer.render is not None
    assert report_router is not None

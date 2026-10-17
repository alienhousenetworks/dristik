"""Reporting package."""
import sys
from app.aeo.reporting import aeo_report_generator
from app.geo.reporting import geo_report_generator
from app.cro.reporting import cro_report_generator
from app.seo.reporting import seo_report_generator

# Register submodules for legacy tests
from app.aeo.reporting import generator as aeo_gen
from app.geo.reporting import geo_report_generator as geo_gen
from app.cro import reporting as cro_gen
from app.seo.reporting import seo_report_generator as seo_gen

sys.modules["app.reports.aeo_report_generator"] = aeo_gen
sys.modules["app.reports.geo_report_generator"] = geo_gen
sys.modules["app.reports.cro_report_generator"] = cro_gen
sys.modules["app.reports.seo_report_generator"] = seo_gen

__all__ = [
    "aeo_report_generator",
    "geo_report_generator",
    "cro_report_generator",
    "seo_report_generator",
]

"""Crawl reads are part of an analysis run.

The mounted analyses router starts the crawl and returns the stored pages.
"""
from app.api.routes.audits.analyses import router

__all__ = ["router"]

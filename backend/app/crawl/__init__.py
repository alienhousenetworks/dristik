"""Acquisition: crawler, browser render, analyzers, embeddings, discovery, and audit ledger."""
import sys
from app.crawl.crawler import CrawlerService
from app.crawl.pillar import CrawlingPillar, CrawlIngestionService
from app.crawl.browser import BrowserRenderService
from app.crawl import audit
from app.crawl.audit import (
    consistency_engine,
    diagnostic_inventory,
    inventory_helper,
    ledger,
    manifest,
    page_analysis,
    regression_engine,
    snapshots,
)

sys.modules["app.audit"] = audit
sys.modules["app.audit.consistency_engine"] = consistency_engine
sys.modules["app.audit.diagnostic_inventory"] = diagnostic_inventory
sys.modules["app.audit.inventory_helper"] = inventory_helper
sys.modules["app.audit.ledger"] = ledger
sys.modules["app.audit.manifest"] = manifest
sys.modules["app.audit.page_analysis"] = page_analysis
sys.modules["app.audit.regression_engine"] = regression_engine
sys.modules["app.audit.snapshots"] = snapshots

__all__ = [
    "CrawlerService",
    "CrawlingPillar",
    "CrawlIngestionService",
    "BrowserRenderService",
    "audit",
]

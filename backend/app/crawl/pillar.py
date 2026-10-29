"""Crawling pillar: ingestion, sitemaps, robots, and browser rendering."""
from __future__ import annotations

from typing import Optional

from app.crawl.browser import BrowserRenderService
from app.crawl.crawler import CrawlerService
from app.crawl.sitemap import SitemapParser
from app.domain.pillar import PillarId
from app.evidence.store import EvidenceStore


class CrawlIngestionService:
    def __init__(self, crawler: Optional[CrawlerService] = None):
        self.crawler = crawler or CrawlerService()
        self.sitemap_parser = SitemapParser()

    async def crawl_site(self, target_url: str, evidence_store: EvidenceStore):
        return await self.crawler.crawl_site_and_analyze(target_url, evidence_store)

    async def crawl_page(self, target_url: str, evidence_store: EvidenceStore):
        return await self.crawler.crawl_and_analyze(target_url, evidence_store)


class CrawlingPillar:
    pillar_id = PillarId.CRAWLING
    domains = {"CRAWLING", "DISCOVERY"}

    def __init__(self, crawler_service: Optional[CrawlerService] = None):
        self.crawler_service = crawler_service or CrawlerService()
        self.ingestion = CrawlIngestionService(self.crawler_service)
        self.browser = BrowserRenderService


__all__ = ["CrawlingPillar", "CrawlIngestionService", "BrowserRenderService"]

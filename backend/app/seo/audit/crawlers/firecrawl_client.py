from typing import Dict, Any
from app.seo.audit.crawlers.base import BaseCrawler

class FirecrawlClient(BaseCrawler):
    async def fetch_page(self, url: str) -> Dict[str, Any]:
        return {"url": url, "markdown": "# Scraped via Firecrawl"}

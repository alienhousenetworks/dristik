from typing import Dict, Any
from app.seo.audit.crawlers.base import BaseCrawler

class PlaywrightCrawler(BaseCrawler):
    async def fetch_page(self, url: str) -> Dict[str, Any]:
        return {"url": url, "status_code": 200, "rendered_dom": "<html><body><h1>Rendered</h1></body></html>"}

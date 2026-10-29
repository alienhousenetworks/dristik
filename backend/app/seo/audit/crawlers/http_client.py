import httpx
from typing import Dict, Any
from app.seo.audit.crawlers.base import BaseCrawler

class NativeHTTPCrawler(BaseCrawler):
    async def fetch_page(self, url: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url)
            return {
                "url": str(resp.url),
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "html": resp.text
            }

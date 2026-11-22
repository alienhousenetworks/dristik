"""Crawl background task handler registered on the durable job queue."""
from __future__ import annotations

from typing import Any, Dict

from app.crawl.crawler import CrawlerService
from app.workers.queue import task_queue


async def run_crawl_task(payload: Dict[str, Any]) -> Any:
    """Execute a queued site crawl through CrawlerService."""
    url = str(payload["website_url"])
    max_pages = int(payload.get("max_pages") or 5)
    crawler = CrawlerService()
    return await crawler.crawl_website(url, max_pages=max_pages)


task_queue.register_handler("crawl.execute", run_crawl_task)

__all__ = ["CrawlerService", "run_crawl_task"]

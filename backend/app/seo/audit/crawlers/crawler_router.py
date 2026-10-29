from app.seo.audit.crawlers.http_client import NativeHTTPCrawler
from app.seo.audit.crawlers.playwright_client import PlaywrightCrawler

class CrawlerRouter:
    def __init__(self):
        self.http = NativeHTTPCrawler()
        self.playwright = PlaywrightCrawler()

    def get_crawler(self, needs_rendering: bool = False):
        return self.playwright if needs_rendering else self.http

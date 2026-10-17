class CrawlScope:
    def __init__(self, root_domain: str, max_depth: int = 3, max_pages: int = 50):
        self.root_domain = root_domain
        self.max_depth = max_depth
        self.max_pages = max_pages

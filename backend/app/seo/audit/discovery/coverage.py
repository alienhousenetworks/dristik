def calculate_crawl_coverage(discovered: int, crawled: int) -> float:
    return round((crawled / max(discovered, 1)) * 100, 1)

def calculate_crawl_coverage(crawled: int, discovered: int) -> float:
    """Calculates crawl coverage percentage, ensuring non-zero crawled count on a valid denominator never rounds to 0.0%."""
    if discovered <= 0 or crawled <= 0:
        return 0.0
    raw = (crawled / float(discovered)) * 100.0
    rounded = round(raw, 1)
    return max(0.1, rounded) if rounded == 0.0 else min(100.0, rounded)


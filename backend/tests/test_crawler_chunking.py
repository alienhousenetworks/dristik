import pytest
from app.domain.models import PageEvidence
from app.crawl.crawler import CrawlerService

def test_crawler_chunk_page_content():
    crawler = CrawlerService()
    page = PageEvidence(
        url="https://example.com/test",
        title="Test Page Title",
        meta_description="Test meta description for indexing",
        h1=["Welcome to Dristik AI"],
        h2=["Feature One", "Feature Two"],
        h3=["Sub-detail"],
        body_text="Here is the detailed body content explaining the platform capabilities.",
        word_count=50
    )
    chunks = crawler._chunk_page_content(page)
    assert len(chunks) >= 1
    assert "Title: Test Page Title" in chunks[0]
    assert "H1: Welcome to Dristik AI" in chunks[0]
    assert "H2: Feature One, Feature Two" in chunks[0]
    assert "Here is the detailed body content" in chunks[0]

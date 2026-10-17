"""ORM page repository."""
from typing import List, Optional

from app.db.models.crawl_page import CrawlPage
from app.db.session import Session


class PageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_audit(self, audit_id: str) -> List[CrawlPage]:
        return self.db.query(CrawlPage).filter(CrawlPage.audit_id == audit_id).all()

    def get(self, page_id: str) -> Optional[CrawlPage]:
        return self.db.query(CrawlPage).filter(CrawlPage.id == page_id).first()

    def create(self, page: CrawlPage) -> CrawlPage:
        self.db.add(page)
        self.db.commit()
        self.db.refresh(page)
        return page

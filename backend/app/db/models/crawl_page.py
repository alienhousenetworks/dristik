# from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from datetime import datetime, timezone
from app.db.base import Base, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON

class CrawlPage(Base):
    __tablename__ = "crawl_pages"
    id = Column(String(64), primary_key=True, index=True)
    audit_id = Column(String(64), ForeignKey("audit_runs.id"), nullable=False, index=True)
    url = Column(String(2048), nullable=False, index=True)
    status_code = Column(Integer, nullable=True)
    title = Column(String(512), nullable=True)
    meta_description = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True)
    depth = Column(Integer, default=0)
    crawled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

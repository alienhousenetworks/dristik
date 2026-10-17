# from sqlalchemy import Column, String, Integer, Float, DateTime, JSON
from datetime import datetime, timezone
from app.db.base import Base, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON

class AuditRun(Base):
    __tablename__ = "audit_runs"
    id = Column(String(64), primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    status = Column(String(50), default="queued") # queued, running, completed, failed
    stage = Column(String(50), default="discovery")
    tier = Column(String(50), default="enterprise")
    total_score = Column(Float, default=0.0)
    pages_crawled = Column(Integer, default=0)
    findings_count = Column(Integer, default=0)
    triggered_by = Column(String(64), nullable=True)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

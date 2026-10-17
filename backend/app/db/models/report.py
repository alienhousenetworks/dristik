# from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from datetime import datetime, timezone
from app.db.base import Base, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON

class Report(Base):
    __tablename__ = "reports"
    id = Column(String(64), primary_key=True, index=True)
    audit_id = Column(String(64), ForeignKey("audit_runs.id"), nullable=False, unique=True)
    format = Column(String(20), default="html") # html, pdf, json
    file_path = Column(String(1024), nullable=True)
    summary_markdown = Column(Text, nullable=True)
    scorecard_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from datetime import datetime, timezone
from app.db.base import Base, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String(64), primary_key=True, index=True)
    audit_id = Column(String(64), ForeignKey("audit_runs.id"), nullable=False, index=True)
    url = Column(String(2048), nullable=True)
    evidence_type = Column(String(50), nullable=False)
    data = Column(JSON, default=dict)
    provenance_state = Column(String(50), default="RAW_TELEMETRY")
    content_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

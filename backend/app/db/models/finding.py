# from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
from datetime import datetime, timezone
from app.db.base import Base, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON

class Finding(Base):
    __tablename__ = "findings"
    id = Column(String(64), primary_key=True, index=True)
    audit_id = Column(String(64), ForeignKey("audit_runs.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False) # technical, content, authority, cro, geo, aeo
    severity = Column(String(20), default="MEDIUM") # CRITICAL, HIGH, MEDIUM, LOW, INFO
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    evidence_ids = Column(JSON, default=list)
    remediation_status = Column(String(50), default="OPEN")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

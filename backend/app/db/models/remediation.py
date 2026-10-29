# from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from datetime import datetime, timezone
from app.db.base import Base, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON

class Remediation(Base):
    __tablename__ = "remediations"
    id = Column(String(64), primary_key=True, index=True)
    audit_id = Column(String(64), ForeignKey("audit_runs.id"), nullable=False)
    finding_id = Column(String(64), ForeignKey("findings.id"), nullable=False)
    patch_type = Column(String(50), default="code_diff")
    patch_payload = Column(Text, nullable=True)
    status = Column(String(50), default="PENDING") # PENDING, APPROVED, REJECTED, APPLIED
    approved_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

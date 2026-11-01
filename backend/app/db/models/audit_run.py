from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id = Column(String(64), primary_key=True, index=True)
    domain_id = Column(String(64), ForeignKey("domains.id", ondelete="CASCADE"), nullable=True, index=True)
    domain = Column(String(255), nullable=True, index=True)
    triggered_by = Column(String(64), nullable=True)
    status = Column(String(50), default="queued", nullable=False)
    stage = Column(String(50), default="discovery", nullable=False)
    tier = Column(String(50), default="enterprise", nullable=True)
    pages_crawled = Column(Integer, default=0, nullable=False)
    findings_count = Column(Integer, default=0, nullable=False)
    overall_score = Column(Integer, nullable=True)
    total_score = Column(Float, default=0.0, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    evidence_coverage = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    config = Column(JSON, default=dict, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    domain_rel = relationship("Domain", back_populates="audit_runs")
    evidence_nodes = relationship("EvidenceNode", back_populates="audit_run", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="audit_run", cascade="all, delete-orphan")

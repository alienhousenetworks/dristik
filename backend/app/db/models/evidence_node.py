from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, DateTime, ForeignKey, Text, JSON


class EvidenceNode(Base):
    __tablename__ = "evidence_nodes"

    id = Column(String(64), primary_key=True, index=True)
    audit_run_id = Column(String(64), ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    node_type = Column(String(50), nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    storage_uri = Column(Text, nullable=False)
    node_metadata = Column("metadata", JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    audit_run = relationship("AuditRun", back_populates="evidence_nodes")

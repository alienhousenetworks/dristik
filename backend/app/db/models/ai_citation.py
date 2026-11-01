from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.db.base import Base, Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON


class AICitation(Base):
    __tablename__ = "ai_citations"

    id = Column(String(64), primary_key=True, index=True)
    domain_id = Column(String(64), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False, index=True)
    query = Column(Text, nullable=False)
    engine = Column(String(50), nullable=False)
    is_cited = Column(Boolean, default=False, nullable=False)
    citation_rank = Column(Integer, nullable=True)
    cited_url = Column(Text, nullable=True)
    extracted_snippet = Column(Text, nullable=True)
    competitor_citations = Column(JSON, default=list, nullable=True)
    queried_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    domain = relationship("Domain", back_populates="ai_citations")

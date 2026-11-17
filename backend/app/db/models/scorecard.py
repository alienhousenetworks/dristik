# from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from datetime import datetime, timezone
from app.db.base import Base, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON

class Scorecard(Base):
    __tablename__ = "scorecards"
    id = Column(String(64), primary_key=True, index=True)
    audit_id = Column(String(64), ForeignKey("audit_runs.id"), nullable=False, unique=True)
    overall_score = Column(Float, default=0.0)
    technical_score = Column(Float, default=0.0)
    content_score = Column(Float, default=0.0)
    geo_score = Column(Float, default=0.0)
    geo_readiness_score = Column(Float, nullable=True)
    observed_ai_visibility_score = Column(Float, nullable=True)
    aeo_readiness_score = Column(Float, nullable=True)
    authority_score = Column(Float, default=0.0)
    ux_score = Column(Float, default=0.0)
    conversion_score = Column(Float, default=0.0)
    pillar_breakdowns = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

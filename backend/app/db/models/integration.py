# from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean
from datetime import datetime, timezone
from app.db.base import Base, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON

class Integration(Base):
    __tablename__ = "integrations"
    id = Column(String(64), primary_key=True, index=True)
    org_id = Column(String(64), ForeignKey("organizations.id"), nullable=False)
    provider = Column(String(50), nullable=False) # google_search_console, ga4, github, wordpress
    credentials_encrypted = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

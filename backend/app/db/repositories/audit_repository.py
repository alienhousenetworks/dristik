from typing import Optional, List
from app.db.session import Session
from app.db.models.audit_run import AuditRun

class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, audit_id: str) -> Optional[AuditRun]:
        return self.db.query(AuditRun).filter(AuditRun.id == audit_id).first()

    def list(self, limit: int = 50, offset: int = 0) -> List[AuditRun]:
        return self.db.query(AuditRun).order_by(AuditRun.created_at.desc()).offset(offset).limit(limit).all()

    def create(self, audit: AuditRun) -> AuditRun:
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return audit

    def update_status(self, audit_id: str, status: str, stage: Optional[str] = None) -> Optional[AuditRun]:
        audit = self.get(audit_id)
        if audit:
            audit.status = status
            if stage:
                audit.stage = stage
            self.db.commit()
            self.db.refresh(audit)
        return audit

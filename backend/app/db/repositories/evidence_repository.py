from typing import List
from app.db.session import Session
from app.db.models.evidence import Evidence

class EvidenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_audit(self, audit_id: str, limit: int = 100) -> List[Evidence]:
        return self.db.query(Evidence).filter(Evidence.audit_id == audit_id).limit(limit).all()

    def create(self, evidence: Evidence) -> Evidence:
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

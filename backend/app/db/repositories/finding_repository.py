from typing import List, Optional
from app.db.session import Session
from app.db.models.finding import Finding

class FindingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_audit(self, audit_id: str, category: Optional[str] = None) -> List[Finding]:
        query = self.db.query(Finding).filter(Finding.audit_id == audit_id)
        if category:
            query = query.filter(Finding.category == category)
        return query.all()

    def create(self, finding: Finding) -> Finding:
        self.db.add(finding)
        self.db.commit()
        self.db.refresh(finding)
        return finding

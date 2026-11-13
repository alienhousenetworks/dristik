from typing import Optional, List
from app.db.session import Session
from app.db.models.audit_run import AuditRun
from app.db.models.domain import Domain
from app.db.models.workspace import Workspace


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, audit_id: str, org_id: str, workspace_id: Optional[str] = None) -> Optional[AuditRun]:
        if not org_id:
            return None
        q = (
            self.db.query(AuditRun)
            .join(Domain, AuditRun.domain_id == Domain.id)
            .join(Workspace, Domain.workspace_id == Workspace.id)
            .filter(AuditRun.id == audit_id, Workspace.org_id == org_id)
        )
        if workspace_id:
            q = q.filter(Workspace.id == workspace_id)
        return q.first()

    def list(self, org_id: str, workspace_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[AuditRun]:
        if not org_id:
            return []
        q = (
            self.db.query(AuditRun)
            .join(Domain, AuditRun.domain_id == Domain.id)
            .join(Workspace, Domain.workspace_id == Workspace.id)
            .filter(Workspace.org_id == org_id)
        )
        if workspace_id:
            q = q.filter(Workspace.id == workspace_id)
        return q.order_by(AuditRun.created_at.desc()).offset(offset).limit(limit).all()

    def create(self, audit: AuditRun) -> AuditRun:
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return audit

    def update_status(
        self,
        audit_id: str,
        org_id: str,
        status: str,
        stage: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> Optional[AuditRun]:
        audit = self.get(audit_id, org_id=org_id, workspace_id=workspace_id)
        if audit:
            audit.status = status
            if stage:
                audit.stage = stage
            self.db.commit()
            self.db.refresh(audit)
        return audit

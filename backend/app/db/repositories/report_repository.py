from typing import Optional
from app.db.session import Session
from app.db.models.report import Report

class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_audit(self, audit_id: str) -> Optional[Report]:
        return self.db.query(Report).filter(Report.audit_id == audit_id).first()

    def create_or_update(self, report: Report) -> Report:
        existing = self.get_by_audit(report.audit_id)
        if existing:
            existing.summary_markdown = report.summary_markdown
            existing.file_path = report.file_path
            existing.scorecard_data = report.scorecard_data
            self.db.commit()
            self.db.refresh(existing)
            return existing
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

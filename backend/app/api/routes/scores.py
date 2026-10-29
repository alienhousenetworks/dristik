"""Score reads are part of an analysis run.

GET /analyses/{analysis_id}/score-explanation returns the stored explanation.
This module does not publish a placeholder score.
"""
from app.api.routes.audits.analyses import router

__all__ = ["router"]

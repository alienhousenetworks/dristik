"""Analysis routes."""
from app.api.routes.audits.analyses import router as analyses_router
from app.api.routes.audits.public_grader import router as public_grader_router
from app.api.routes.audits.stream import router as stream_router

router = analyses_router

__all__ = ["analyses_router", "public_grader_router", "router", "stream_router"]

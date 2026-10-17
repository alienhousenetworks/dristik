"""Live routes are the mounted routers."""
import importlib.util

from app.api.v1.endpoints.scores import router as live_scores
from app.api.v1.router import LIVE_ROUTERS
from app.api.routes.audits.analyses import router as analyses_router


def test_live_scores_are_the_analyses_router():
    assert analyses_router in LIVE_ROUTERS
    assert live_scores is analyses_router
    assert importlib.util.find_spec("app.api.v1.scores") is None

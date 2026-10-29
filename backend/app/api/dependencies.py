"""Dependencies for the live HTTP routes.

Session identity comes from the cookie helpers in app.identity.deps.
The database session comes from app.db.session.
"""
from app.db.session import get_db
from app.identity.deps import (
    get_current_user,
    get_current_user_optional,
    read_session_token,
    require_permission,
)

__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "get_db",
    "read_session_token",
    "require_permission",
]

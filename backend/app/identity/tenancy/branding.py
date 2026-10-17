"""White-label branding for an organization."""
from app.identity.tenancy.white_label import (
    get_white_label_config,
    router,
    update_white_label_config,
)

__all__ = ["get_white_label_config", "router", "update_white_label_config"]

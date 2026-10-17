"""Organization isolation.

A run in another organization is not found. Domain access stays on TenantManager.
"""
from app.identity.access import require_analysis
from app.identity.tenancy.manager import TenantManager

__all__ = ["TenantManager", "require_analysis"]

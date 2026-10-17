"""Compatibility shim for migrated tenancy packages (transferred to app.identity.tenancy)."""
import sys
__path__ = []

from app.identity.tenancy import agency, branding, isolation, manager, models, tenant_context, white_label

sys.modules["app.tenancy"] = sys.modules[__name__]
sys.modules["app.tenancy.agency"] = agency
sys.modules["app.tenancy.branding"] = branding
sys.modules["app.tenancy.isolation"] = isolation
sys.modules["app.tenancy.manager"] = manager
sys.modules["app.tenancy.models"] = models
sys.modules["app.tenancy.tenant_context"] = tenant_context
sys.modules["app.tenancy.white_label"] = white_label

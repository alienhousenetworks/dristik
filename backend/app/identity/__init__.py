"""Identity, Authentication, Authorization & Multi-Tenant Isolation."""
import sys
from app.identity import tenancy
from app.identity.tenancy import agency, branding, isolation, manager, models, tenant_context, white_label

sys.modules["app.tenancy"] = tenancy
sys.modules["app.tenancy.agency"] = agency
sys.modules["app.tenancy.branding"] = branding
sys.modules["app.tenancy.isolation"] = isolation
sys.modules["app.tenancy.manager"] = manager
sys.modules["app.tenancy.models"] = models
sys.modules["app.tenancy.tenant_context"] = tenant_context
sys.modules["app.tenancy.white_label"] = white_label

__all__ = ["tenancy"]

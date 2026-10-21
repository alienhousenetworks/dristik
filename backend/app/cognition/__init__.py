"""Backward-compatibility bridge for app.cognition -> app.orchestration.cognition."""
import sys
from app.orchestration import cognition as _cog

# Re-export module symbols
for attr in dir(_cog):
    if not attr.startswith("__"):
        globals()[attr] = getattr(_cog, attr)

sys.modules["app.cognition"] = _cog

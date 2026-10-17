"""Compatibility re-export from app.domain.capabilities."""
import sys
import types

__path__ = []

from app.domain.capabilities import *  # noqa: F401, F403
import app.domain.capabilities as _caps

registry_mod = types.ModuleType("app.capabilities.registry")
for attr in dir(_caps):
    if not attr.startswith("__"):
        setattr(registry_mod, attr, getattr(_caps, attr))

sys.modules["app.capabilities"] = sys.modules[__name__]
sys.modules["app.capabilities.registry"] = registry_mod

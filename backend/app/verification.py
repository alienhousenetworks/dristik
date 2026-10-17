"""Compatibility re-export from app.remediation."""
from __future__ import annotations

import sys
from app.remediation import verifier, verification_loop
from app.remediation.verifier import VerificationEngine, verification_engine

__path__: list[str] = []

sys.modules["app.verification.verifier"] = verifier
sys.modules["app.verification.verification_loop"] = verification_loop

__all__ = ["VerificationEngine", "verification_engine"]

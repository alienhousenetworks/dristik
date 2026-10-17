"""Syntax and safety gate for generated patches.

PatchValidator is the live checker. There is no separate AST rewrite step.
"""
from app.remediation.validator import PatchValidationResult, PatchValidator

AstValidator = PatchValidator

__all__ = ["AstValidator", "PatchValidationResult", "PatchValidator"]

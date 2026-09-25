"""
Dristik AI Remediation & Code Patch Validator
Ensures generated code patches are syntactically valid, Schema.org compliant,
free of malicious scripts, and safe for production staging.
"""
import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.domain.models import CodePatch

class PatchValidationResult(BaseModel):
    is_valid: bool
    syntax_valid: bool
    schema_valid: bool
    security_clean: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class PatchValidator:
    """
    Validates patches before they are presented to human operators or staging pipelines.
    """

    def validate_patch(self, patch: CodePatch) -> PatchValidationResult:
        errors = []
        warnings = []
        syntax_ok = True
        schema_ok = True
        security_ok = True

        snippet = patch.after_snippet

        # 1. Security Validation: Check for hostile script injection or external payloads
        if any(bad in snippet.lower() for bad in ["javascript:void", "eval(", "document.cookie", "<script src=\"http://", "base64,"]):
            security_ok = False
            errors.append("Hostile script or unsafe evaluation pattern detected in generated code patch.")

        # 2. JSON-LD Schema Validation
        if "application/ld+json" in snippet or "{" in snippet and "}" in snippet:
            # Extract json block
            json_match = re.search(r'<script\s+type="application/ld\+json">([\s\S]*?)</script>', snippet)
            json_text = json_match.group(1).strip() if json_match else (snippet.strip() if snippet.strip().startswith("{") else None)

            if json_text:
                try:
                    parsed = json.loads(json_text)
                    # Check Schema.org context and type
                    if "@context" not in parsed:
                        schema_ok = False
                        errors.append("Schema markup missing '@context': 'https://schema.org'.")
                    if "@type" not in parsed:
                        schema_ok = False
                        errors.append("Schema markup missing '@type' declaration.")
                except json.JSONDecodeError as je:
                    syntax_ok = False
                    errors.append(f"Invalid JSON-LD syntax: {str(je)}")

        # 3. HTML Tag Balancing (for meta / link snippets)
        if "<meta" in snippet or "<link" in snippet or "<h1" in snippet:
            open_tags = len(re.findall(r'<[a-zA-Z0-9]+', snippet))
            close_tags = len(re.findall(r'</[a-zA-Z0-9]+>', snippet)) + len(re.findall(r'<meta|<link|<img', snippet))
            if open_tags > close_tags + 2:
                warnings.append("Potential unclosed HTML tags in generated snippet.")

        is_valid = syntax_ok and schema_ok and security_ok and len(errors) == 0

        return PatchValidationResult(
            is_valid=is_valid,
            syntax_valid=syntax_ok,
            schema_valid=schema_ok,
            security_clean=security_ok,
            errors=errors,
            warnings=warnings
        )

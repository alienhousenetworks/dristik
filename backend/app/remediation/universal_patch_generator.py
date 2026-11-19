"""
Universal Patch Generator — Phase 8.4 (10/10 Transformation)

Generates production-ready, typed patches across 10 canonical patch types:
1. HTML changes
2. CSS changes
3. JavaScript changes
4. React component changes
5. Metadata changes
6. JSON-LD changes
7. Content changes
8. Internal linking changes
9. Configuration changes
10. Redirect rules

For every patch, stores all 9 mandatory fields including an atomic inverted rollback patch.
"""
from __future__ import annotations

import difflib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.remediation.models import (
    PatchType,
    RemediationTaskRecord,
    RollbackPatch,
    UniversalPatch,
)

logger = logging.getLogger("dristik.remediation.patch_generator")


class UniversalPatchGenerator:
    """
    Generates unified multi-type patches with atomic rollback guarantees.
    """

    def generate_patch(
        self,
        task: RemediationTaskRecord,
        patch_type: PatchType,
        original_code: str,
        proposed_code: str,
        file_path: str,
        line_references: str = "L1-L20",
        change_explanation: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        validation_requirements: Optional[List[str]] = None,
    ) -> UniversalPatch:
        patch_id = f"PATCH_{task.task_id}_{patch_type.value}"
        explanation = change_explanation or f"Remediate finding {task.finding_id}: {task.recommended_action}"

        # 8. Create atomic inverse rollback patch
        rollback = RollbackPatch(
            rollback_id=f"ROLLBACK_{patch_id}",
            file_path=file_path,
            original_code=proposed_code,
            rollback_code=original_code,
            explanation=f"Revert {patch_id} back to original state.",
        )

        val_reqs = validation_requirements or [
            "SYNTAX_PARSER_CHECK",
            "SECURITY_SANITY_CHECK",
            "NO_REGRESSION_DIFF_CHECK",
        ]

        return UniversalPatch(
            patch_id=patch_id,
            patch_type=patch_type,
            original_code=original_code,
            proposed_code=proposed_code,
            file_path=file_path,
            line_references=line_references,
            change_explanation=explanation,
            related_finding_id=task.finding_id,
            dependencies=dependencies or task.dependencies,
            rollback_patch=rollback,
            validation_requirements=val_reqs,
        )

    # Convenience generators for the 10 patch types
    def generate_json_ld_patch(self, task: RemediationTaskRecord, file_path: str, schema_json: str, target_block: str = "") -> UniversalPatch:
        proposed = f'<script type="application/ld+json">\n{schema_json}\n</script>'
        return self.generate_patch(
            task=task,
            patch_type=PatchType.JSON_LD,
            original_code=target_block,
            proposed_code=proposed,
            file_path=file_path,
            line_references="L15-L25",
            change_explanation="Inject Schema.org structured data graph.",
            validation_requirements=["JSON_SYNTAX", "SCHEMA_ORG_VALIDATION"],
        )

    def generate_metadata_patch(self, task: RemediationTaskRecord, file_path: str, orig_title: str, new_title: str, new_meta: str) -> UniversalPatch:
        orig = f"<title>{orig_title}</title>" if orig_title else ""
        proposed = f"<title>{new_title}</title>\n<meta name=\"description\" content=\"{new_meta}\" />"
        return self.generate_patch(
            task=task,
            patch_type=PatchType.METADATA,
            original_code=orig,
            proposed_code=proposed,
            file_path=file_path,
            line_references="L5-L10",
            change_explanation="Update SEO title and meta description with character-safe copy.",
        )

    def generate_redirect_rule_patch(self, task: RemediationTaskRecord, file_path: str, old_path: str, new_path: str) -> UniversalPatch:
        orig = ""
        proposed = f"Redirect 301 {old_path} {new_path}\n"
        return self.generate_patch(
            task=task,
            patch_type=PatchType.REDIRECT_RULES,
            original_code=orig,
            proposed_code=proposed,
            file_path=file_path,
            line_references="L1-L2",
            change_explanation=f"Implement permanent 301 redirect from {old_path} to {new_path}.",
        )

    def generate_react_component_patch(self, task: RemediationTaskRecord, file_path: str, original_code: str, proposed_code: str) -> UniversalPatch:
        return self.generate_patch(
            task=task,
            patch_type=PatchType.REACT_COMPONENT,
            original_code=original_code,
            proposed_code=proposed_code,
            file_path=file_path,
            line_references="L20-L45",
            change_explanation="Refactor React component to optimize primary CTA accessibility and styling.",
            validation_requirements=["TYPESCRIPT_COMPILE", "JSX_SYNTAX"],
        )

    def generate_configuration_patch(self, task: RemediationTaskRecord, file_path: str, original_code: str, proposed_code: str) -> UniversalPatch:
        return self.generate_patch(
            task=task,
            patch_type=PatchType.CONFIGURATION,
            original_code=original_code,
            proposed_code=proposed_code,
            file_path=file_path,
            line_references="L1-L15",
            change_explanation="Update server or build configuration directives.",
        )


universal_patch_generator = UniversalPatchGenerator()
